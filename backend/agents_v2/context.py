"""上下文引擎 — 压缩 + 组装 + 会话摘要管理

合并自 compaction.py + context_engine.py
设计参考 pi-mono compaction + OpenClaw ContextEngine 接口
"""
import json
from dataclasses import dataclass, field
from typing import Optional


# --- 压缩核心 ---

TOKEN_RATIO = 3
DEFAULT_MAX_CONTEXT = 128_000
DEFAULT_RESERVE = 8_192
DEFAULT_KEEP_RECENT = 20


@dataclass(frozen=True)
class CompactResult:
    messages: tuple[dict, ...]
    summary: str
    removed_count: int
    kept_count: int


def estimate_tokens(messages: list[dict]) -> int:
    """粗估 token 数：chars / 3"""
    total_chars = sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)
    return total_chars // TOKEN_RATIO


def should_compact(
    messages: list[dict],
    max_context: int = DEFAULT_MAX_CONTEXT,
    reserve: int = DEFAULT_RESERVE,
) -> bool:
    return estimate_tokens(messages) > (max_context - reserve)


def compact_messages(
    messages: list[dict],
    existing_summary: str = "",
    keep_recent: int = DEFAULT_KEEP_RECENT,
    max_context: int = DEFAULT_MAX_CONTEXT,
) -> CompactResult:
    """压缩消息列表：保留 system + 最近 N 条，早期消息替换为摘要占位"""
    if not messages:
        return CompactResult(
            messages=tuple(messages),
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

    if len(conversation) <= keep_recent:
        return CompactResult(
            messages=tuple(messages),
            summary=existing_summary,
            removed_count=0,
            kept_count=len(messages),
        )

    removed = conversation[:-keep_recent]
    kept = conversation[-keep_recent:]

    parts = []
    if existing_summary:
        parts.append(f"之前的对话摘要：\n{existing_summary}")
    parts.append(f"[已压缩 {len(removed)} 条早期消息，请根据上下文继续]")
    summary_text = "\n".join(parts)

    result = system_msgs + [{"role": "user", "content": summary_text}] + kept
    return CompactResult(
        messages=tuple(result),
        summary=existing_summary,
        removed_count=len(removed),
        kept_count=len(kept) + len(system_msgs) + 1,
    )


# --- ContextEngine ---

class ContextEngine:
    """可插拔上下文引擎 — ingest / assemble / compact 生命周期"""

    def __init__(
        self,
        max_context: int = DEFAULT_MAX_CONTEXT,
        reserve: int = DEFAULT_RESERVE,
    ):
        self.max_context = max_context
        self.reserve = reserve
        self._summaries: dict[int, str] = {}

    def estimate_session_tokens(self, messages: list[dict]) -> int:
        return estimate_tokens(messages)

    def needs_compaction(self, messages: list[dict]) -> bool:
        return should_compact(messages, self.max_context, self.reserve)

    def assemble(
        self,
        messages: list[dict],
        memory_text: Optional[str] = None,
        skill_hints: Optional[str] = None,
    ) -> list[dict]:
        """组装上下文：注入记忆摘要和技能提示到 system prompt 之后"""
        if not messages:
            return messages

        result = [messages[0]]

        if memory_text:
            result.append({"role": "system", "content": f"## 相关记忆\n{memory_text}"})
        if skill_hints:
            result.append({"role": "system", "content": f"## 可用技能\n{skill_hints}"})

        result.extend(messages[1:])
        return result

    def compact(self, session_id: int, messages: list[dict], keep_recent: int = 20) -> CompactResult:
        existing = self._summaries.get(session_id, "")
        return compact_messages(messages, existing, keep_recent, self.max_context)

    def update_summary(self, session_id: int, summary: str) -> None:
        self._summaries[session_id] = summary

    def get_summary(self, session_id: int) -> str:
        return self._summaries.get(session_id, "")

    def cleanup_session(self, session_id: int) -> None:
        self._summaries.pop(session_id, None)


# 全局单例
context_engine = ContextEngine()
