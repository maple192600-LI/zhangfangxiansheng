"""Agent Loop — generator 流式事件循环

单轮对话 → 多次 tool 调用 → 返回最终回复
yield 事件：TextChunk / ToolStart / ToolEnd / TurnDone
"""
import json
import time
from typing import Any, AsyncGenerator, Optional

from sqlalchemy.orm import Session

from db.tables import AgentV2
from agents_v2.provider import stream_chat
from core.security import decrypt_key
from agents_v2.tool_registry import ToolContext, execute_tool, get_tools_for_llm
from agents_v2.permission import get_permission, is_tool_allowed, needs_confirm
from agents_v2.session_store import load_recent_messages, save_message
from agents_v2 import sse_helper as sse
import agents_v2.tools  # 触发工具注册

MAX_TURNS = 20


async def run_turn(
    agent: AgentV2,
    session_id: int,
    user_text: str,
    db: Session,
) -> AsyncGenerator[str, None]:
    """运行一轮对话，yield SSE 格式的事件字符串

    流程：
    1. 加载历史消息 + 用户消息
    2. 构建 system prompt + tools
    3. 调用 LLM 流式
    4. 如果 LLM 请求 tool call → 执行 → 回到 3
    5. 直到 LLM 不再调工具 或 达到 MAX_TURNS
    """
    # 保存用户消息
    save_message(db, session_id, "user", content=user_text)

    # 加载历史
    history = load_recent_messages(db, session_id)
    # 追加当前用户消息
    history.append({"role": "user", "content": user_text})

    # 构建 system prompt
    system_prompt = _build_system_prompt(agent)

    # 获取 AI 配置
    ai_config = agent.ai_config
    if not ai_config:
        yield sse.sse_error("该 agent 未配置 AI 模型，请先在设置中选择 AI 配置")
        return

    # 权限
    perm = get_permission(agent.permission_json)

    # 构建 LLM 工具列表
    tools = get_tools_for_llm(perm)

    # 构建 LLM 消息列表（含 system）
    messages = _format_messages(system_prompt, history)

    turn = 0
    started_at = time.time()

    while turn < MAX_TURNS:
        turn += 1
        full_text = ""
        last_tool_call: Optional[dict] = None
        reasoning_content = ""

        # 流式调用 LLM
        api_key_plain = decrypt_key(ai_config.api_key_local)
        async for chunk in stream_chat(
            provider=ai_config.provider,
            api_key=api_key_plain,
            base_url=ai_config.base_url,
            model_name=ai_config.model_name,
            messages=messages,
            tools=tools if tools else None,
            timeout=getattr(agent, "llm_timeout", 300),
            max_tokens=getattr(agent, "llm_max_tokens", 4096),
        ):
            if chunk["type"] == "text":
                full_text += chunk.get("text", "")
                yield sse.sse_text(chunk.get("text", ""))

            elif chunk["type"] == "tool_call":
                last_tool_call = chunk.get("tool_call")

            elif chunk["type"] == "done":
                reasoning_content = chunk.get("reasoning_content", "")
                break

            elif chunk["type"] == "error":
                yield sse.sse_error(chunk.get("error", "AI 调用失败"))
                # 保存错误消息
                save_message(db, session_id, "assistant", content=full_text or f"[错误] {chunk.get('error', '')}")
                return

        # 如果没产生文本且没 tool call，结束
        if not full_text and not last_tool_call:
            yield sse.sse_done("end_turn")
            save_message(db, session_id, "assistant", content="", reasoning_content=reasoning_content or None)
            return

        # 如果有文本但没 tool call，本轮结束
        if full_text and not last_tool_call:
            duration = int((time.time() - started_at) * 1000)
            save_message(db, session_id, "assistant", content=full_text, duration_ms=duration, reasoning_content=reasoning_content or None)
            yield sse.sse_done("end_turn")
            return

        # 处理 tool call
        if last_tool_call:
            tool_name = last_tool_call.get("name", "")
            tool_args = last_tool_call.get("arguments", {})

            # 权限检查
            if not is_tool_allowed(perm, tool_name):
                result = {"ok": False, "error": f"工具 '{tool_name}' 未被允许，请联系管理员配置权限"}
            else:
                # 执行工具
                yield sse.sse_tool_start(tool_name, tool_args)

                ctx = ToolContext(
                    agent_id=agent.id,
                    agent_code=agent.agent_code,
                    session_id=session_id,
                    db=db,
                )
                result = await execute_tool(tool_name, tool_args, ctx)
                yield sse.sse_tool_end(tool_name, result)

            # 记录 assistant + tool 消息到历史
            tool_call_json = json.dumps(last_tool_call, ensure_ascii=False)
            tool_result_json = json.dumps(result, ensure_ascii=False)
            tool_call_id = last_tool_call.get("id", f"call_{tool_name}")

            save_message(db, session_id, "assistant", content=full_text, tool_call_json=tool_call_json, reasoning_content=reasoning_content or None)
            save_message(db, session_id, "tool", tool_result_json=tool_result_json)

            # 追加到 LLM 上下文（OpenAI 标准格式）
            tc_args = last_tool_call.get("arguments", {})
            if isinstance(tc_args, dict):
                tc_args = json.dumps(tc_args, ensure_ascii=False)
            assistant_msg = {
                "role": "assistant",
                "content": full_text or None,
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": tc_args},
                }],
            }
            if reasoning_content:
                assistant_msg["reasoning_content"] = reasoning_content
            messages.append(assistant_msg)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    # 达到 MAX_TURNS
    save_message(db, session_id, "assistant", content="[已达到最大工具调用次数限制]")
    yield sse.sse_done("max_turns_reached")


def _build_system_prompt(agent: AgentV2) -> str:
    """构建 system prompt"""
    parts = [
        f"你是「{agent.display_name}」，一个 AI 智能体。",
    ]
    if agent.role_prompt:
        parts.append(f"\n## 岗位职责\n{agent.role_prompt}")

    parts.append("\n## 行为准则")
    parts.append("- 用中文回答")
    parts.append("- 如果需要操作文件或执行命令，使用提供的工具")
    parts.append("- 如果不确定，使用 ask_user 工具向用户确认")
    parts.append("- 回答要简洁专业")

    parts.append("\n## 技能创建指南")
    parts.append("当用户要求你学习新技能时，按以下步骤操作：")
    parts.append("1. 用 openpyxl_read 或 fs_read 读取用户上传的样本文件，分析表头和数据结构")
    parts.append("2. 识别关键字段映射（日期、收入、支出、摘要、对方户名等）")
    parts.append("3. 用 skill_create 工具创建技能，参数说明：")
    parts.append("   - skill_code: 英文小写+下划线，如 parse_bank_xxx")
    parts.append("   - display_name: 中文名称，如 'XX银行流水解析'")
    parts.append("   - description: 简短描述技能功能")
    parts.append("   - run_py: Python 代码字符串，必须包含 run(params) 函数")
    parts.append("4. run(params) 函数规范：")
    parts.append("   - params 是字典，通常包含 file_path")
    parts.append("   - 返回 {'ok': True, 'rows': [...], 'count': N} 格式")
    parts.append("   - 使用 openpyxl 读取 Excel，处理日期和金额格式")
    parts.append("5. 创建后用 skill_test 测试，验证是否能正确解析样本文件")
    parts.append("6. 告知用户技能已创建并通过测试")
    return "\n".join(parts)


def _format_messages(system_prompt: str, history: list[dict]) -> list[dict]:
    """格式化消息为 OpenAI 兼容格式（含标准 tool_calls 结构和 reasoning_content）"""
    result: list[dict] = [{"role": "system", "content": system_prompt}]
    # 追踪 tool_call_id，确保 tool 消息和 assistant 消息配对
    pending_tool_call_id: str | None = None

    for msg in history:
        role = msg.get("role", "user")
        if role == "tool":
            # OpenAI 要求 tool 消息携带 tool_call_id
            tc_id = msg.get("tool_call_id") or pending_tool_call_id or "call_0"
            content = msg.get("content", msg.get("tool_result", ""))
            result.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
            })
            pending_tool_call_id = None
        elif msg.get("tool_calls"):
            raw_calls = msg["tool_calls"]
            # 如果是单个 tool_call dict（非列表），包装为列表
            if isinstance(raw_calls, dict):
                raw_calls = [raw_calls]
            # 转为 OpenAI 标准 tool_calls 格式
            openai_calls = []
            for i, tc in enumerate(raw_calls):
                tc_id = tc.get("id", f"call_{i}")
                name = tc.get("name", tc.get("function", {}).get("name", ""))
                args = tc.get("arguments", tc.get("function", {}).get("arguments", {}))
                if isinstance(args, dict):
                    args = json.dumps(args, ensure_ascii=False)
                openai_calls.append({
                    "id": tc_id,
                    "type": "function",
                    "function": {"name": name, "arguments": args},
                })
                pending_tool_call_id = tc_id
            assistant_msg = {
                "role": "assistant",
                "content": msg.get("content", "") or None,
                "tool_calls": openai_calls,
            }
            if msg.get("reasoning_content"):
                assistant_msg["reasoning_content"] = msg["reasoning_content"]
            result.append(assistant_msg)
        else:
            content = msg.get("content", "")
            reasoning = msg.get("reasoning_content")
            if content:
                assistant_msg = {"role": role, "content": content}
                if role == "assistant" and reasoning:
                    assistant_msg["reasoning_content"] = reasoning
                result.append(assistant_msg)
            elif reasoning and role == "assistant":
                # 只有 reasoning 没有 content 的情况
                result.append({"role": "assistant", "content": None, "reasoning_content": reasoning})
    return result
