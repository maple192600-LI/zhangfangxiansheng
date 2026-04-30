"""Agent Loop — generator 流式事件循环

单轮对话 → 多次 tool 调用 → 返回最终回复
yield 事件：TextChunk / ToolStart / ToolEnd / TurnDone

V2 改造：
- 多 tool_call 批量执行
- 错误恢复（保存到历史而非静默丢弃）
- 上下文压缩（ContextEngine）
- 记忆自动注入
- Session 并发锁
- 技能匹配与注入
"""
import json
import time
from typing import AsyncGenerator, Optional

from sqlalchemy.orm import Session

from db.tables import AgentV2
from agents_v2.provider import stream_chat
from core.security import decrypt_key
from agents_v2.tool_registry import ToolContext, execute_tool, get_tools_for_llm
from agents_v2.permission import get_permission, is_tool_allowed
from agents_v2.session_store import load_recent_messages, save_message
from agents_v2.memory_store import search_memory
from agents_v2.context_engine import context_engine
from agents_v2.session_lock import get_session_lock
from agents_v2.skill_registry import skill_registry
from agents_v2.skill_executor import format_skill_instruction, get_skill_run_path
from agents_v2.compaction import estimate_tokens
from agents_v2 import sse_helper as sse
import agents_v2.tools  # 触发工具注册

MAX_TURNS = 40


async def run_turn(
    agent: AgentV2,
    session_id: int,
    user_text: str,
    db: Session,
) -> AsyncGenerator[str, None]:
    """运行一轮对话，yield SSE 格式的事件字符串"""
    # 并发控制
    lock = get_session_lock(session_id)
    if lock.locked():
        yield sse.sse_error("该会话正在处理中，请等待完成后再发送消息")
        return

    async with lock:
        async for event in _run_turn_inner(agent, session_id, user_text, db):
            yield event


async def _run_turn_inner(
    agent: AgentV2,
    session_id: int,
    user_text: str,
    db: Session,
) -> AsyncGenerator[str, None]:
    """核心对话循环（已获取 session 锁）"""
    # 保存用户消息
    save_message(db, session_id, "user", content=user_text)

    # 加载历史
    history = load_recent_messages(db, session_id)
    history.append({"role": "user", "content": user_text})

    # 记忆自动注入：根据用户输入检索相关记忆
    memory_hints = _get_memory_hints(db, agent.id, user_text)

    # 技能匹配：扫描并加载触发技能
    skill_registry.startup_scan(agent_code=agent.agent_code)
    matched_skills = skill_registry.trigger(user_text)
    skill_hints = _build_skill_hints(matched_skills)

    # 构建 system prompt（含记忆+技能）
    system_prompt = _build_system_prompt(agent, memory_hints, skill_hints)

    # AI 配置检查
    ai_config = agent.ai_config
    if not ai_config:
        yield sse.sse_error("该 agent 未配置 AI 模型，请先在设置中选择 AI 配置")
        return

    # 权限 + 工具列表
    perm = get_permission(agent.permission_json)
    tools = get_tools_for_llm(perm)

    # 构建 LLM 消息列表
    messages = _format_messages(system_prompt, history)

    # 上下文压缩检查
    if context_engine.needs_compaction(messages):
        result = context_engine.compact(session_id, messages)
        if result.removed_count > 0:
            messages = result.messages

    turn = 0
    started_at = time.time()
    accumulated_text = ""

    while turn < MAX_TURNS:
        turn += 1
        full_text = ""
        tool_calls: list[dict] = []  # 收集所有 tool_call
        reasoning_content = ""

        api_key_plain = decrypt_key(ai_config.api_key_local)
        stop_reason = "end_turn"

        async for chunk in stream_chat(
            provider=ai_config.provider,
            api_key=api_key_plain,
            base_url=ai_config.base_url,
            model_name=ai_config.model_name,
            messages=messages,
            tools=tools if tools else None,
            timeout=getattr(agent, "llm_timeout", 300),
            max_tokens=getattr(agent, "llm_max_tokens", 16384),
        ):
            if chunk["type"] == "text":
                full_text += chunk.get("text", "")
                yield sse.sse_text(chunk.get("text", ""))

            elif chunk["type"] == "tool_call":
                tool_calls.append(chunk.get("tool_call"))

            elif chunk["type"] == "done":
                stop_reason = chunk.get("stop_reason", "end_turn")
                reasoning_content = chunk.get("reasoning_content", "")
                break

            elif chunk["type"] == "error":
                error_msg = chunk.get("error", "AI 调用失败")
                # 保存错误到会话历史
                save_message(
                    db, session_id, "assistant",
                    content=f"[错误] {error_msg}",
                    reasoning_content=reasoning_content or None,
                )
                yield sse.sse_error(error_msg)
                return

        # 无输出且无 tool call
        if not full_text and not tool_calls:
            yield sse.sse_done("end_turn")
            save_message(
                db, session_id, "assistant", content="",
                reasoning_content=reasoning_content or None,
            )
            return

        # length 截断续写
        if stop_reason == "length" and full_text and not tool_calls:
            accumulated_text += full_text
            yield sse.sse_text("\n")
            assistant_piece = {"role": "assistant", "content": full_text}
            if reasoning_content:
                assistant_piece["reasoning_content"] = reasoning_content
            messages.append(assistant_piece)
            messages.append({"role": "user", "content": "请继续"})
            continue

        # 有文本但无 tool call → 本轮结束
        if full_text and not tool_calls:
            accumulated_text += full_text
            duration = int((time.time() - started_at) * 1000)
            save_message(
                db, session_id, "assistant",
                content=accumulated_text,
                duration_ms=duration,
                reasoning_content=reasoning_content or None,
            )
            yield sse.sse_done("end_turn")
            return

        # 批量执行所有 tool_calls
        if tool_calls:
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("arguments", {})

                if not is_tool_allowed(perm, tool_name):
                    result = {"ok": False, "error": f"工具 '{tool_name}' 未被允许"}
                else:
                    yield sse.sse_tool_start(tool_name, tool_args)
                    ctx = ToolContext(
                        agent_id=agent.id,
                        agent_code=agent.agent_code,
                        session_id=session_id,
                        db=db,
                    )
                    result = await execute_tool(tool_name, tool_args, ctx)
                    yield sse.sse_tool_end(tool_name, result)

                # 保存到历史
                tc_json = json.dumps(tc, ensure_ascii=False)
                result_json = json.dumps(result, ensure_ascii=False)
                tc_id = tc.get("id", f"call_{tool_name}")

                save_message(
                    db, session_id, "assistant",
                    content=full_text,
                    tool_call_json=tc_json,
                    reasoning_content=reasoning_content or None,
                )
                save_message(
                    db, session_id, "tool",
                    tool_result_json=result_json,
                )

                # 追加到 LLM 上下文
                tc_args = tc.get("arguments", {})
                if isinstance(tc_args, dict):
                    tc_args = json.dumps(tc_args, ensure_ascii=False)
                assistant_msg = {
                    "role": "assistant",
                    "content": full_text or None,
                    "tool_calls": [{
                        "id": tc_id,
                        "type": "function",
                        "function": {"name": tool_name, "arguments": tc_args},
                    }],
                }
                if reasoning_content:
                    assistant_msg["reasoning_content"] = reasoning_content
                messages.append(assistant_msg)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            # 批量执行完后检查上下文压缩
            if context_engine.needs_compaction(messages):
                compact_result = context_engine.compact(session_id, messages)
                if compact_result.removed_count > 0:
                    messages = compact_result.messages
            continue

    # 达到 MAX_TURNS
    yield sse.sse_done("max_turns_reached")


def _get_memory_hints(db: Session, agent_id: int, user_text: str) -> str:
    """检索相关记忆并格式化为文本"""
    try:
        memories = search_memory(db, agent_id, user_text, limit=5)
        if not memories:
            return ""
        lines = []
        for m in memories:
            key = m.get("key", "")
            content = m.get("content", "")[:150]
            lines.append(f"- [{key}]: {content}")
        return "\n".join(lines)
    except Exception:
        return ""


def _build_skill_hints(skills: list) -> str:
    """构建技能提示文本"""
    if not skills:
        return skill_registry.l1_summary_text()

    parts = ["以下技能已激活："]
    for skill in skills:
        instruction = format_skill_instruction(skill)
        parts.append(instruction)
    return "\n".join(parts)


def _build_system_prompt(
    agent: AgentV2,
    memory_hints: str = "",
    skill_hints: str = "",
) -> str:
    """构建 system prompt（含记忆注入和技能提示）"""
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
    parts.append("- 你可以使用 memory_search 工具搜索历史记忆")

    if memory_hints:
        parts.append("\n## 相关记忆")
        parts.append(memory_hints)

    if skill_hints:
        parts.append("\n## 可用技能")
        parts.append(skill_hints)

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
    pending_tool_call_id: str | None = None

    has_thinking = any(
        m.get("role") == "assistant" and "reasoning_content" in m
        for m in history
    )

    for msg in history:
        role = msg.get("role", "user")
        if role == "tool":
            if pending_tool_call_id is None:
                continue
            tc_id = msg.get("tool_call_id") or pending_tool_call_id
            content = msg.get("content", msg.get("tool_result", ""))
            result.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
            })
            pending_tool_call_id = None
        elif msg.get("tool_calls"):
            raw_calls = msg["tool_calls"]
            if isinstance(raw_calls, dict):
                raw_calls = [raw_calls]
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
            rc = msg.get("reasoning_content")
            if rc is not None:
                assistant_msg["reasoning_content"] = rc
            elif has_thinking:
                assistant_msg["reasoning_content"] = ""
            result.append(assistant_msg)
        else:
            content = msg.get("content", "")
            reasoning = msg.get("reasoning_content")
            if content:
                assistant_msg = {"role": role, "content": content}
                if role == "assistant":
                    if reasoning is not None:
                        assistant_msg["reasoning_content"] = reasoning
                    elif has_thinking:
                        assistant_msg["reasoning_content"] = ""
                result.append(assistant_msg)
            elif role == "assistant" and reasoning is not None:
                result.append({"role": "assistant", "content": None, "reasoning_content": reasoning})
            elif role == "assistant" and has_thinking:
                result.append({"role": "assistant", "content": None, "reasoning_content": ""})
    return result
