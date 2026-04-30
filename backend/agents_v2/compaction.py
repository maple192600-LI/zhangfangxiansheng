"""上下文压缩引擎

借鉴 pi-mono 的增量摘要模式：
1. 保留 system prompt + 最近 20 条消息
2. 较早消息用 LLM 生成摘要（增量合并已有摘要）
3. 压缩前先 Flush 记忆（由调用方在 compact 前执行）

不依赖 LLM — 纯 token 估算 + 消息截断。
摘要生成可选，由 runtime 调用 provider 完成。
"""
import json
from dataclasses import dataclass, field


@dataclass
class CompactResult:
    messages: list[dict]
    summary: str
    removed_count: int
    kept_count: int


# 中文约 2 字符/token，混合内容用 chars/3 估算
TOKEN_RATIO = 3
DEFAULT_MAX_CONTEXT = 128_000
DEFAULT_RESERVE = 8_192
DEFAULT_KEEP_RECENT = 20


def estimate_tokens(messages: list[dict]) -> int:
    """粗估消息列表的 token 数"""
    total_chars = sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)
    return total_chars // TOKEN_RATIO


def should_compact(
    messages: list[dict],
    max_context: int = DEFAULT_MAX_CONTEXT,
    reserve: int = DEFAULT_RESERVE,
) -> bool:
    """判断是否需要压缩"""
    return estimate_tokens(messages) > (max_context - reserve)


def compact_messages(
    messages: list[dict],
    existing_summary: str = "",
    keep_recent: int = DEFAULT_KEEP_RECENT,
    max_context: int = DEFAULT_MAX_CONTEXT,
) -> CompactResult:
    """压缩消息列表

    策略：
    - 保留 system prompt（第一条）
    - 保留最近 keep_recent 条消息
    - 较早消息截断，生成占位摘要消息
    - 如果有 existing_summary，保留在摘要消息中
    """
    if not messages:
        return CompactResult(
            messages=messages,
            summary=existing_summary,
            removed_count=0,
            kept_count=len(messages),
        )

    system_msgs: list[dict] = []
    conversation: list[dict] = []

    for msg in messages:
        if msg.get("role") == "system":
            system_msgs.append(msg)
        else:
            conversation.append(msg)

    # 如果对话消息不够多，不需要截断
    if len(conversation) <= keep_recent:
        return CompactResult(
            messages=messages,
            summary=existing_summary,
            removed_count=0,
            kept_count=len(messages),
        )

    removed = conversation[:-keep_recent]
    kept = conversation[-keep_recent:]

    summary_parts = []
    if existing_summary:
        summary_parts.append(f"之前的对话摘要：\n{existing_summary}")
    summary_parts.append(
        f"[已压缩 {len(removed)} 条早期消息，请根据上下文继续]"
    )
    summary_text = "\n".join(summary_parts)

    summary_msg = {
        "role": "user",
        "content": summary_text,
    }

    result = system_msgs + [summary_msg] + kept
    return CompactResult(
        messages=result,
        summary=existing_summary,
        removed_count=len(removed),
        kept_count=len(kept) + len(system_msgs) + 1,
    )


def build_summary_prompt(removed_messages: list[dict]) -> str:
    """构建用于 LLM 生成摘要的 prompt（由 runtime 调用）"""
    content_parts = []
    for msg in removed_messages[-30:]:
        role = msg.get("role", "user")
        text = msg.get("content", "")
        if text:
            content_parts.append(f"[{role}]: {text[:200]}")

    return (
        "请将以下对话历史压缩为简洁的摘要，保留关键信息和决策：\n\n"
        + "\n".join(content_parts)
    )
