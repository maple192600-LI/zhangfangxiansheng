"""上下文引擎 — 语义压缩 + 会话摘要管理

压缩策略：
  1. 短期：head(前3) + LLM摘要 + tail(后6) 三段保护
  2. 长期：摘要持久化到 AgentSession.context_summary
  3. 降级：当 LLM 摘要不可用时，回退到关键词提取

中文 token 估算：中文 2x + 英文 0.5x
双检查点：循环前 + 工具执行后
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ── Token 估算 ───────────────────────────────────────────

def _is_cjk(c: str) -> bool:
    """判断字符是否为 CJK 统一汉字（含扩展区）或全角字符"""
    cp = ord(c)
    return (
        (0x4E00 <= cp <= 0x9FFF) or     # CJK Unified Ideographs
        (0x3400 <= cp <= 0x4DBF) or     # CJK Unified Ideographs Extension A
        (0x20000 <= cp <= 0x2A6DF) or   # CJK Unified Ideographs Extension B
        (0x2A700 <= cp <= 0x2B73F) or   # CJK Unified Ideographs Extension C
        (0x2B740 <= cp <= 0x2B81F) or   # CJK Unified Ideographs Extension D
        (0xF900 <= cp <= 0xFAFF) or     # CJK Compatibility Ideographs
        (0xFF00 <= cp <= 0xFFEF) or     # Fullwidth Forms
        (0x3000 <= cp <= 0x303F)        # CJK Symbols and Punctuation
    )


def estimate_tokens(messages: list[dict]) -> int:
    """中英混合 token 估算：CJK/全角 ≈ 2 token，其他 ≈ 0.5 token"""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        if not content:
            raw = json.dumps(msg, ensure_ascii=False)
            total += len(raw) // 3
            continue
        cjk = sum(1 for c in content if _is_cjk(c))
        other = len(content) - cjk
        total += cjk * 2 + int(other * 0.5)
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


def _extract_key_facts(messages: list[dict]) -> str:
    """从即将被压缩的消息中提取关键信息（降级方案）

    当 LLM 摘要不可用时使用。
    """
    markers = ["总结", "结论", "规则", "偏好", "业务规则", "注意事项", "结果", "决定"]
    insights = []
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        if not content or len(content) < 30:
            continue
        if any(m in content for m in markers):
            insights.append(content[:300])
    return "\n".join(insights)


def _build_messages_text(messages: list[dict], max_chars: int = 6000) -> str:
    """将消息列表格式化为文本，用于 LLM 摘要输入"""
    parts = []
    total = 0
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content or not isinstance(content, str):
            continue
        line = f"[{role}]: {content[:500]}"
        if total + len(line) > max_chars:
            break
        parts.append(line)
        total += len(line)
    return "\n".join(parts)


def _build_summary_prompt(messages_text: str) -> str:
    """构建 LLM 摘要请求的 prompt"""
    return f"""请将以下对话历史压缩为一段结构化摘要。保留以下信息：
1. 用户的核心需求和意图
2. 已完成的关键操作和结果
3. 重要的数据（账户、金额、文件名等）
4. 待办或未完成的任务
5. 做出的决策或确认

用中文回答，控制在 500 字以内。

---
对话历史：
{messages_text}"""


def compact_messages(
    messages: list[dict],
    existing_summary: str = "",
    protect_first: int = PROTECT_FIRST,
    protect_last: int = PROTECT_LAST,
    max_context: int = DEFAULT_MAX_CONTEXT,
    llm_summary: Optional[str] = None,
) -> CompactResult:
    """三段压缩：head + summary + tail

    llm_summary: 由外部 LLM 生成的摘要。为 None 时使用关键词提取降级。
    """
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

    # 构建摘要
    parts = []
    if existing_summary:
        parts.append(f"之前的对话摘要：\n{existing_summary}")

    if llm_summary:
        parts.append(f"最近对话摘要：\n{llm_summary}")
    else:
        key_facts = _extract_key_facts(middle)
        if key_facts:
            parts.append(f"关键信息：\n{key_facts}")

    parts.append(f"[已压缩 {len(middle)} 条消息]")
    summary_text = "\n".join(parts)

    result = system_msgs + head + [{"role": "user", "content": summary_text}] + tail
    return CompactResult(
        messages=tuple(result),
        summary=llm_summary or existing_summary,
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

    def compact(
        self,
        session_id: int,
        messages: list[dict],
        llm_summary: Optional[str] = None,
    ) -> CompactResult:
        existing = self._summaries.get(session_id, "")
        result = compact_messages(
            messages, existing,
            self.protect_first, self.protect_last, self.max_context,
            llm_summary=llm_summary,
        )
        if result.summary and result.summary != existing:
            self._summaries[session_id] = result.summary
        return result

    def update_summary(self, session_id: int, summary: str) -> None:
        self._summaries[session_id] = summary

    def get_summary(self, session_id: int) -> str:
        return self._summaries.get(session_id, "")

    def cleanup_session(self, session_id: int) -> None:
        self._summaries.pop(session_id, None)


# 全局单例
context_engine = ContextEngine()
