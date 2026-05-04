"""上下文引擎 — 压缩 + 组装 + 会话摘要管理

三段保护：head(前3) + middle(摘要) + tail(后6)
中文 token 估算：中文 2x + 英文 0.5x
双检查点：循环前 + 工具执行后
"""
import json
from dataclasses import dataclass
from typing import Optional


# ── Token 估算 ───────────────────────────────────────────

def estimate_tokens(messages: list[dict]) -> int:
    """中英混合 token 估算：中文 1 字 ≈ 2 token，其他 ≈ 0.5 token"""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        if not content:
            # 估算非内容字段的开销
            raw = json.dumps(msg, ensure_ascii=False)
            total += len(raw) // 3
            continue
        chinese = sum(1 for c in content if '一' <= c <= '鿿')
        other = len(content) - chinese
        total += chinese * 2 + int(other * 0.5)
    return total


# ── 压缩核心 ─────────────────────────────────────────────

DEFAULT_MAX_CONTEXT = 128_000
DEFAULT_RESERVE = 8_192
PROTECT_FIRST = 3
PROTECT_LAST = 6
THRESHOLD = 0.8


@dataclass(frozen=True)
class CompactResult:
    messages: tuple[dict, ...]
    summary: str
    removed_count: int
    kept_count: int


def _extract_insights(messages: list[dict]) -> str:
    """从即将被压缩的消息中提取关键信息"""
    markers = ["总结", "结论", "确定", "注意", "关键", "规则", "发现"]
    insights = []
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        if not content or len(content) < 20:
            continue
        if any(m in content for m in markers):
            insights.append(content[:200])
    return "\n".join(insights)


def compact_messages(
    messages: list[dict],
    existing_summary: str = "",
    protect_first: int = PROTECT_FIRST,
    protect_last: int = PROTECT_LAST,
    max_context: int = DEFAULT_MAX_CONTEXT,
) -> CompactResult:
    """三段压缩：head + summary + tail"""
    if not messages:
        return CompactResult(
            messages=tuple(messages),
            summary=existing_summary,
            removed_count=0,
            kept_count=0,
        )

    system_msgs: list[dict] = []
    conversation: list[dict] = []

    for msg in messages:
        if msg.get("role") == "system":
            system_msgs.append(msg)
        else:
            conversation.append(msg)

    # 消息不足以压缩
    min_needed = protect_first + protect_last
    if len(conversation) <= min_needed:
        return CompactResult(
            messages=tuple(messages),
            summary=existing_summary,
            removed_count=0,
            kept_count=len(messages),
        )

    head = conversation[:protect_first]
    tail = conversation[-protect_last:]
    middle = conversation[protect_first:-protect_last]

    if not middle:
        return CompactResult(
            messages=tuple(messages),
            summary=existing_summary,
            removed_count=0,
            kept_count=len(messages),
        )

    # 压缩前提取关键信息
    insights = _extract_insights(middle)

    # 构建摘要
    parts = []
    if existing_summary:
        parts.append(f"之前的对话摘要：\n{existing_summary}")
    if insights:
        parts.append(f"关键信息：\n{insights}")
    parts.append(f"[已压缩 {len(middle)} 条早期消息，请根据上下文继续]")
    summary_text = "\n".join(parts)

    result = system_msgs + head + [{"role": "user", "content": summary_text}] + tail
    return CompactResult(
        messages=tuple(result),
        summary=existing_summary,
        removed_count=len(middle),
        kept_count=len(result),
    )


# ── ContextEngine ────────────────────────────────────────

class ContextEngine:
    """可插拔上下文引擎 — ingest / assemble / compact 生命周期"""

    def __init__(
        self,
        max_context: int = DEFAULT_MAX_CONTEXT,
        reserve: int = DEFAULT_RESERVE,
        protect_first: int = PROTECT_FIRST,
        protect_last: int = PROTECT_LAST,
    ):
        self.max_context = max_context
        self.reserve = reserve
        self.protect_first = protect_first
        self.protect_last = protect_last
        self._summaries: dict[int, str] = {}
        self.last_prompt_tokens: int = 0

    def estimate_session_tokens(self, messages: list[dict]) -> int:
        return estimate_tokens(messages)

    def needs_compaction(self, messages: list[dict]) -> bool:
        tokens = estimate_tokens(messages)
        self.last_prompt_tokens = tokens
        return tokens >= int((self.max_context - self.reserve) * THRESHOLD)

    def assemble(
        self,
        messages: list[dict],
        memory_text: Optional[str] = None,
        skill_hints: Optional[str] = None,
    ) -> list[dict]:
        """注入记忆摘要和技能提示到 system prompt 之后"""
        if not messages:
            return messages

        result = [messages[0]]

        if memory_text:
            result.append({"role": "system", "content": f"## 相关记忆\n{memory_text}"})
        if skill_hints:
            result.append({"role": "system", "content": f"## 可用技能\n{skill_hints}"})

        result.extend(messages[1:])
        return result

    def compact(self, session_id: int, messages: list[dict]) -> CompactResult:
        existing = self._summaries.get(session_id, "")
        return compact_messages(
            messages, existing,
            self.protect_first, self.protect_last, self.max_context,
        )

    def update_summary(self, session_id: int, summary: str) -> None:
        self._summaries[session_id] = summary

    def get_summary(self, session_id: int) -> str:
        return self._summaries.get(session_id, "")

    def cleanup_session(self, session_id: int) -> None:
        self._summaries.pop(session_id, None)


# 全局单例
context_engine = ContextEngine()
