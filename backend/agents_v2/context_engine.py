"""可插拔上下文引擎

生命周期：ingest → assemble → compact → after_turn
负责消息的接收、上下文组装、压缩和回合后维护。

设计参考 OpenClaw ContextEngine 接口 + pi-mono compaction 模式。
"""
from typing import Optional

from agents_v2.compaction import (
    CompactResult,
    compact_messages,
    should_compact,
    estimate_tokens,
    DEFAULT_MAX_CONTEXT,
    DEFAULT_RESERVE,
)


class ContextEngine:
    """上下文引擎 — 管理 LLM 上下文窗口"""

    def __init__(
        self,
        max_context: int = DEFAULT_MAX_CONTEXT,
        reserve: int = DEFAULT_RESERVE,
    ):
        self.max_context = max_context
        self.reserve = reserve

        # 会话级状态
        self._summaries: dict[int, str] = {}

    def estimate_session_tokens(self, messages: list[dict]) -> int:
        """估算当前消息列表的 token 数"""
        return estimate_tokens(messages)

    def needs_compaction(self, messages: list[dict]) -> bool:
        """判断是否需要压缩"""
        return should_compact(messages, self.max_context, self.reserve)

    def assemble(
        self,
        messages: list[dict],
        memory_text: Optional[str] = None,
        skill_hints: Optional[str] = None,
    ) -> list[dict]:
        """组装上下文：注入记忆摘要和技能提示

        在 system prompt 后插入动态内容，不影响原始消息结构。
        """
        if not messages:
            return messages

        result = [messages[0]]  # system prompt

        # 注入记忆摘要
        if memory_text:
            result.append({
                "role": "system",
                "content": f"## 相关记忆\n{memory_text}",
            })

        # 注入技能提示
        if skill_hints:
            result.append({
                "role": "system",
                "content": f"## 可用技能\n{skill_hints}",
            })

        result.extend(messages[1:])
        return result

    def compact(
        self,
        session_id: int,
        messages: list[dict],
        keep_recent: int = 20,
    ) -> CompactResult:
        """压缩上下文

        1. 获取该会话已有的摘要
        2. 截断早期消息，保留摘要占位 + 最近消息
        3. 返回压缩结果
        """
        existing = self._summaries.get(session_id, "")
        result = compact_messages(
            messages,
            existing_summary=existing,
            keep_recent=keep_recent,
            max_context=self.max_context,
        )
        return result

    def update_summary(self, session_id: int, summary: str) -> None:
        """更新会话摘要（由 runtime 调用 LLM 生成后写入）"""
        self._summaries[session_id] = summary

    def get_summary(self, session_id: int) -> str:
        """获取当前摘要"""
        return self._summaries.get(session_id, "")

    def cleanup_session(self, session_id: int) -> None:
        """会话结束后清理状态"""
        self._summaries.pop(session_id, None)


# 全局单例
context_engine = ContextEngine()
