"""Agent Loop — 流式事件循环

单轮对话 → 多次 tool 调用 → 返回最终回复
yield SSE 事件：text / tool_start / tool_end / done / error

- 多 tool_call 批量执行
- 错误恢复（保存到历史而非静默丢弃）
- 上下文压缩（ContextEngine 三段保护）
- 记忆自动注入（MemoryManager + DBMemoryProvider）
- Scrubber 清洗 LLM 输出中的 <memory-context> 标签
- 技能匹配与 XML 注入（SkillRegistry + PromptBuilder）
- Session 并发锁
"""
import json
import logging
import time
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from db.tables import Agent
from agents.provider import stream_chat
from core.security import decrypt_key
from agents.tool_registry import ToolContext, execute_tool, get_tools_for_llm
from agents.permission import get_permission, is_tool_allowed, needs_confirm, get_confirm_message
from agents.session_store import load_recent_messages, save_message, update_session_summary
from agents.context import context_engine
from agents.session_lock import get_session_lock
from agents.skill_registry import skill_registry
from agents.skill_executor import format_skill_instruction
from agents.prompt_builder import prompt_builder
from agents.memory_manager import MemoryManager
from agents.db_memory_provider import DBMemoryProvider
from agents.curator import Curator
from agents import sse_helper as sse
from agents.context import _build_summary_prompt, _build_messages_text
import agents.tools  # 触发工具注册

MAX_TURNS = 40

# ── 工具确认等待注册表 ────────────────────────────────────
import asyncio

_confirm_events: dict[str, asyncio.Event] = {}
_confirm_results: dict[str, dict] = {}


def register_confirm_wait(tc_id: str) -> asyncio.Event:
    """注册一个确认等待事件"""
    event = asyncio.Event()
    _confirm_events[tc_id] = event
    return event


def resolve_confirm(tc_id: str, approved: bool, reason: str = "") -> None:
    """解除确认等待"""
    _confirm_results[tc_id] = {"approved": approved, "reason": reason}
    evt = _confirm_events.get(tc_id)
    if evt:
        evt.set()


def _cleanup_confirm(tc_id: str) -> None:
    _confirm_events.pop(tc_id, None)
    _confirm_results.pop(tc_id, None)


async def _create_memory_manager(agent: Agent, db: Session) -> MemoryManager:
    """为 agent 创建 MemoryManager 实例"""
    provider = DBMemoryProvider()
    await provider.initialize(agent.agent_code, agent_id=agent.id, db=db)
    return MemoryManager(provider)


async def run_turn(
    agent: Agent,
    session_id: int,
    user_text: str,
    db: Session,
) -> AsyncGenerator[str, None]:
    """运行一轮对话，yield SSE 格式的事件字符串"""
    lock = get_session_lock(session_id)
    # asyncio 协作式调度，locked() 和 async with 之间不会被中断，无竞态条件
    if lock.locked():
        yield sse.sse_error("该会话正在处理中，请等待完成后再发送消息")
        return

    async with lock:
        try:
            async for event in _run_turn_inner(agent, session_id, user_text, db):
                yield event
        finally:
            from agents.session_lock import cleanup_lock
            cleanup_lock(session_id)


async def _run_turn_inner(
    agent: Agent,
    session_id: int,
    user_text: str,
    db: Session,
) -> AsyncGenerator[str, None]:
    """核心对话循环（已获取 session 锁）"""
    save_message(db, session_id, "user", content=user_text)

    # Curator 技能生命周期检查（后台执行，不阻塞主流程）
    try:
        curator = Curator(agent.agent_code)
        result = curator.maybe_run()
        if result and (result.get("stale", 0) > 0 or result.get("archived", 0) > 0):
            logger.info("Curator %s: stale=%d archived=%d", agent.agent_code, result.get("stale", 0), result.get("archived", 0))
    except Exception as e:
        logger.warning("Curator failed for %s: %s", agent.agent_code, e)

    history = load_recent_messages(db, session_id)
    # 用户消息已在上方 save_message 写入 DB，load_recent_messages 会加载它
    # 如果因 limit 截断导致未包含，则追加
    if not history or history[-1].get("role") != "user" or history[-1].get("content") != user_text:
        history.append({"role": "user", "content": user_text})

    # 记忆预加载
    memory_mgr = await _create_memory_manager(agent, db)
    await memory_mgr.prefetch_with_query(str(session_id), user_text)
    memory_block = memory_mgr.build_system_prompt()

    # 技能匹配
    skill_registry.startup_scan(agent_code=agent.agent_code)
    skill_registry.hot_reload()
    matched_skills = skill_registry.trigger(user_text)

    # 构建 skill_hints
    if matched_skills:
        skill_hints = _build_skill_hints(matched_skills)
    else:
        skill_hints = skill_registry.l1_summary_text()

    # System prompt（通过 PromptBuilder 组装）
    system_prompt = prompt_builder.build(
        agent,
        memory_hints=memory_block,
        skill_hints=skill_hints,
    )

    ai_config = agent.ai_config
    if not ai_config:
        yield sse.sse_error("该 agent 未配置 AI 模型，请先在设置中选择 AI 配置")
        return

    perm = get_permission(agent.permission_json)
    tools = get_tools_for_llm(perm)
    messages = _format_messages(system_prompt, history)
    messages = _validate_message_sequence(messages)

    api_key_plain = decrypt_key(ai_config.api_key_local)

    # 检查点 1：循环前压缩
    if context_engine.needs_compaction(messages):
        await memory_mgr.on_pre_compress_all(messages)
        try:
            llm_summary = await asyncio.wait_for(
                _generate_llm_summary(ai_config, messages, api_key_plain),
                timeout=20,
            )
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning("LLM summary timed out or failed: %s, using keyword fallback", e)
            llm_summary = None
        result = context_engine.compact(session_id, messages, llm_summary=llm_summary)
        if result.removed_count > 0:
            messages = _validate_message_sequence(list(result.messages))

    # 创建 Scrubber
    scrubber = memory_mgr.create_scrubber()
    turn = 0
    started_at = time.time()
    accumulated_text = ""
    _last_tool_signatures: list[str] = []  # 循环检测：记录最近工具调用签名

    while turn < MAX_TURNS:
        turn += 1
        full_text = ""
        tool_calls: list[dict] = []
        reasoning_content = ""

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
                raw_text = chunk.get("text", "")
                clean_text = scrubber.scrub(raw_text)
                full_text += raw_text
                if clean_text:
                    yield sse.sse_text(clean_text)

            elif chunk["type"] == "tool_call":
                tool_calls.append(chunk.get("tool_call"))

            elif chunk["type"] == "done":
                stop_reason = chunk.get("stop_reason", "end_turn")
                reasoning_content = chunk.get("reasoning_content", "")
                break

            elif chunk["type"] == "error":
                error_msg = chunk.get("error", "AI 调用失败")
                save_message(
                    db, session_id, "assistant",
                    content=f"[错误] {error_msg}",
                    reasoning_content=reasoning_content or None,
                )
                yield sse.sse_error(error_msg)
                return

        # flush scrubber 残余
        remaining = scrubber.flush()
        if remaining:
            yield sse.sse_text(remaining)

        if not full_text and not tool_calls:
            yield sse.sse_done("end_turn")
            save_message(
                db, session_id, "assistant", content="",
                reasoning_content=reasoning_content or None,
            )
            return

        # length 截断续写
        if stop_reason in ("length", "max_tokens") and full_text and not tool_calls:
            accumulated_text += full_text
            yield sse.sse_text("\n")
            assistant_piece = {"role": "assistant", "content": full_text}
            if reasoning_content:
                assistant_piece["reasoning_content"] = reasoning_content
            messages.append(assistant_piece)
            messages.append({"role": "user", "content": "请继续"})
            continue

        # 有 tool_calls → 执行工具（即使有文本也算工具轮）
        if tool_calls:
            # 1) 构建 ONE assistant 消息，包含所有 tool_calls
            openai_tool_calls = []
            for tc in tool_calls:
                tc_id = tc.get("id", f"call_{tc.get('name', 'unknown')}")
                tc_args = tc.get("arguments", {})
                if isinstance(tc_args, dict):
                    tc_args = json.dumps(tc_args, ensure_ascii=False)
                openai_tool_calls.append({
                    "id": tc_id,
                    "type": "function",
                    "function": {"name": tc.get("name", ""), "arguments": tc_args},
                })

            assistant_msg = {
                "role": "assistant",
                "content": full_text or None,
                "tool_calls": openai_tool_calls,
            }
            if reasoning_content:
                assistant_msg["reasoning_content"] = reasoning_content
            messages.append(assistant_msg)

            # 保存 assistant 消息到 DB（所有 tool_calls 合并为一条记录）
            save_message(
                db, session_id, "assistant",
                content=full_text or "",
                tool_call_json=json.dumps(openai_tool_calls, ensure_ascii=False),
                reasoning_content=reasoning_content or None,
            )

            # 2) 逐个执行工具，追加 tool result 消息
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("arguments", {})
                tc_id = tc.get("id", f"call_{tool_name}")

                if not is_tool_allowed(perm, tool_name):
                    result = {"ok": False, "error": f"工具 '{tool_name}' 未被允许"}
                elif needs_confirm(perm, tool_name):
                    confirm_msg = get_confirm_message(tool_name, tool_args)
                    yield sse.sse_confirm_request(tool_name, tool_args, confirm_msg, tc_id)
                    confirm_evt = register_confirm_wait(tc_id)
                    try:
                        await asyncio.wait_for(confirm_evt.wait(), timeout=60)
                    except asyncio.TimeoutError:
                        result = {"ok": False, "error": "用户确认超时，操作已取消"}
                    else:
                        cr = _confirm_results.get(tc_id, {})
                        if cr.get("approved"):
                            yield sse.sse_tool_start(tool_name, tool_args)
                            ctx = ToolContext(
                                agent_id=agent.id,
                                agent_code=agent.agent_code,
                                session_id=session_id,
                                db=db,
                            )
                            result = await execute_tool(tool_name, tool_args, ctx)
                            yield sse.sse_tool_end(tool_name, result)
                        else:
                            result = {"ok": False, "error": f"用户拒绝: {cr.get('reason', '用户取消了操作')}"}
                    finally:
                        _cleanup_confirm(tc_id)
                else:
                    yield sse.sse_tool_start(tool_name, tool_args)
                    ctx = ToolContext(
                        agent_id=agent.id,
                        agent_code=agent.agent_code,
                        session_id=session_id,
                        db=db,
                    )
                    result = await execute_tool(tool_name, tool_args, ctx)

                    # ask_user 特殊处理：暂停等待用户回复
                    if tool_name == "ask_user" and result.get("ok") and result.get("_ask_user"):
                        question = result.get("question", "")
                        yield sse.sse_ask_user(question, tc_id)
                        ask_evt = register_confirm_wait(tc_id)
                        try:
                            await asyncio.wait_for(ask_evt.wait(), timeout=300)
                        except asyncio.TimeoutError:
                            result = {"ok": False, "error": "用户回复超时，请重新提问"}
                        else:
                            cr = _confirm_results.get(tc_id, {})
                            user_reply = cr.get("reason", "") or cr.get("reply", "")
                            if user_reply:
                                result = {"ok": True, "reply": user_reply}
                            else:
                                result = {"ok": False, "error": "用户未提供回复"}
                        finally:
                            _cleanup_confirm(tc_id)

                    yield sse.sse_tool_end(tool_name, result)

                result_json = json.dumps(result, ensure_ascii=False)
                save_message(
                    db, session_id, "tool",
                    tool_result_json=result_json,
                    tool_call_json=json.dumps({"tool_call_id": tc_id}, ensure_ascii=False),
                )

                tool_msg_content = _build_tool_result_content(result, tool_name)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": tool_msg_content,
                })

            # 循环检测：相同工具调用签名连续出现 3 次 → 强制终止
            sig = "+".join(f"{tc.get('name','')}({json.dumps(tc.get('arguments',{}), sort_keys=True)})" for tc in tool_calls)
            _last_tool_signatures.append(sig)
            if len(_last_tool_signatures) >= 4:
                recent = _last_tool_signatures[-4:]
                if recent[0] == recent[1] == recent[2] == recent[3]:
                    logger.warning("Loop detected: same tool calls repeated 4 times: %s", sig[:200])
                    accumulated_text += "\n\n[检测到重复操作，已自动停止。请尝试换个方式描述需求。]"
                    duration = int((time.time() - started_at) * 1000)
                    save_message(db, session_id, "assistant", content=accumulated_text, duration_ms=duration)
                    yield sse.sse_done("loop_detected")
                    return

            # 检查点 2：工具执行后压缩
            if context_engine.needs_compaction(messages):
                await memory_mgr.on_pre_compress_all(messages)
                try:
                    llm_summary2 = await asyncio.wait_for(
                        _generate_llm_summary(ai_config, messages, api_key_plain),
                        timeout=20,
                    )
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning("Checkpoint 2 LLM summary failed: %s, using fallback", e)
                    llm_summary2 = None
                compact_result = context_engine.compact(session_id, messages, llm_summary=llm_summary2)
                if compact_result.removed_count > 0:
                    messages = _validate_message_sequence(list(compact_result.messages))
            continue

        # 有文本但无 tool_call → 本轮结束
        accumulated_text += full_text
        duration = int((time.time() - started_at) * 1000)
        save_message(
            db, session_id, "assistant",
            content=accumulated_text,
            duration_ms=duration,
            reasoning_content=reasoning_content or None,
        )
        await memory_mgr.sync_all(str(session_id), messages)
        # 持久化摘要到 session
        summary = context_engine.get_summary(session_id)
        if summary:
            update_session_summary(db, session_id, summary)
        yield sse.sse_done("end_turn")
        return

    yield sse.sse_done("max_turns_reached")


async def _generate_llm_summary(ai_config, messages: list[dict], api_key_plain: str) -> str | None:
    """调用 LLM 生成对话摘要（压缩前调用）

    失败时静默返回 None，降级到关键词提取。
    """
    try:
        messages_text = _build_messages_text(messages, max_chars=6000)
        if len(messages_text) < 100:
            return None

        summary_prompt = _build_summary_prompt(messages_text)
        summary_messages = [
            {"role": "system", "content": "你是一个对话摘要助手。请将对话历史压缩为简洁的结构化摘要。"},
            {"role": "user", "content": summary_prompt},
        ]

        full_text = ""
        async for chunk in stream_chat(
            provider=ai_config.provider,
            api_key=api_key_plain,
            base_url=ai_config.base_url,
            model_name=ai_config.model_name,
            messages=summary_messages,
            tools=None,
            max_tokens=1000,
            timeout=30,
        ):
            if chunk["type"] == "text":
                full_text += chunk.get("text", "")
            elif chunk["type"] == "error":
                logger.warning("LLM summary generation failed: %s", chunk.get("error"))
                return None

        return full_text.strip() if full_text else None
    except Exception as e:
        logger.warning("LLM summary generation exception: %s", e)
        return None


def _pop_next_tool_call_id(messages: list[dict]) -> str:
    """从最后一条 assistant 消息的 tool_calls 中按顺序取出下一个 tool_call_id

    用于 DB 历史重建时，tool 消息没有存储 tool_call_id 的情况。
    """
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            tcs = msg["tool_calls"]
            # 用 _pending_pop 标记追踪已消费的 tool_call_id
            pop_idx = msg.get("_pending_pop", 0)
            if pop_idx < len(tcs):
                msg["_pending_pop"] = pop_idx + 1
                return tcs[pop_idx].get("id", f"call_{pop_idx}")
    return "call_unknown"


def _build_tool_result_content(result: dict, tool_name: str):
    """构建工具结果消息内容。所有结果统一返回 JSON 字符串。"""
    if tool_name == "file_parse" and result.get("format") == "image":
        # 图片结果：只保留元数据，不传 base64（太大且多数 API 不支持 vision in tool result）
        safe_result = {k: v for k, v in result.items() if k not in ("base64_data", "data_uri")}
        return json.dumps(safe_result, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)


def _build_skill_hints(skills: list) -> str:
    """构建技能提示文本"""
    if not skills:
        return skill_registry.l1_summary_text()
    parts = ["以下技能已激活："]
    for skill in skills:
        instruction = format_skill_instruction(skill)
        parts.append(instruction)
    return "\n".join(parts)


def _format_messages(system_prompt: str, history: list[dict]) -> list[dict]:
    """格式化消息为 OpenAI 兼容格式（含标准 tool_calls 结构和 reasoning_content）

    关键：DB 中多个连续的 assistant+tool_calls 记录必须合并为一条 assistant 消息，
    否则违反 OpenAI API "不能有连续两条 assistant 消息"的约束。
    """
    result: list[dict] = [{"role": "system", "content": system_prompt}]

    has_thinking = any(
        m.get("role") == "assistant" and "reasoning_content" in m
        for m in history
    )

    for msg in history:
        role = msg.get("role", "user")
        if role == "tool":
            content = msg.get("content", msg.get("tool_result", ""))
            # tool 消息需要 tool_call_id
            # DB 中 tool 消息没有存 tool_call_id，从最后一个 assistant 的 tool_calls 队列中按顺序取
            tc_id = msg.get("tool_call_id", "")
            if not tc_id:
                tc_id = _pop_next_tool_call_id(result)
            result.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
            })
        elif msg.get("tool_calls"):
            # 如果上一条 result 也是 assistant+tool_calls，合并而非新增
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

            prev = result[-1] if result else None
            if prev and prev.get("role") == "assistant" and prev.get("tool_calls"):
                # 合并到上一条 assistant 消息
                prev["tool_calls"].extend(openai_calls)
            else:
                assistant_msg = {
                    "role": "assistant",
                    "content": None,
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
                result.append({"role": "assistant", "content": reasoning[:200]})
            elif role == "assistant" and has_thinking:
                result.append({"role": "assistant", "content": "（思考中）"})
    return result


def _validate_message_sequence(messages: list[dict]) -> list[dict]:
    """修复消息序列，确保 assistant+tool_calls 和 tool 消息正确配对。

    参考 openclaw 的 repairToolUseResultPairing：
    1. 移除开头的孤立 tool 消息
    2. 为缺失的 tool result 插入合成错误结果
    3. 丢弃重复的 tool result
    4. 移除无 content 无 tool_calls 的空 assistant 消息
    5. 末尾 assistant+tool_calls 无 tool result → 清理
    """
    if not messages:
        return messages

    result: list[dict] = []
    seen_tool_ids: set[str] = set()

    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg.get("role")

        if role == "assistant" and msg.get("tool_calls"):
            # 收集这个 assistant 的所有 tool_call_ids
            tool_calls = msg["tool_calls"]
            call_ids = []
            for tc in tool_calls:
                tc_id = tc.get("id", "")
                if tc_id:
                    call_ids.append(tc_id)

            result.append(msg)

            # 向后查找匹配的 tool result
            matched_ids = set()
            j = i + 1
            while j < len(messages) and messages[j].get("role") == "tool":
                tool_msg = messages[j]
                tc_id = tool_msg.get("tool_call_id", "")
                if tc_id in call_ids and tc_id not in matched_ids:
                    result.append(tool_msg)
                    matched_ids.add(tc_id)
                    seen_tool_ids.add(tc_id)
                # 重复的或不匹配的 tool 消息直接跳过
                j += 1

            # 为缺失的 tool result 插入合成错误
            for cid in call_ids:
                if cid not in matched_ids:
                    result.append({
                        "role": "tool",
                        "tool_call_id": cid,
                        "content": "[消息修复] 缺少工具结果，已插入合成结果",
                    })
                    seen_tool_ids.add(cid)

            i = j

        elif role == "tool":
            # 孤立的 tool 消息（前面没有 assistant+tool_calls）→ 跳过
            i += 1
            continue

        elif role == "assistant":
            # 无 tool_calls 的 assistant 消息
            content = msg.get("content")
            if not content:
                # 空 assistant 消息 → 跳过
                i += 1
                continue
            result.append(msg)
            i += 1

        else:
            result.append(msg)
            i += 1

    # 末尾 assistant+tool_calls 但无后续 tool result（已被上面的循环处理）
    # 额外检查：如果最后一条是 assistant 带 tool_calls，已在上面处理过

    # 确保 user 消息不在开头 system 之后连续出现多次
    while len(result) > 1 and result[0].get("role") == "system" and result[1].get("role") == "user":
        break  # 正常情况

    return result