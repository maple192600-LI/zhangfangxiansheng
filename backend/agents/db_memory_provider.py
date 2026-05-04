"""DB MemoryProvider — 基于 SQLAlchemy / AgentMemory 表

实现 MemoryProvider ABC 的 5 阶段生命周期。
封装 memory_store.py 的 CRUD 操作，增加冻结快照和注入检测。
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from agents.memory_provider import MemoryProvider, scan_memory_value

logger = logging.getLogger(__name__)

_MEMORY_MARKERS = ["总结", "结论", "确定", "注意", "关键", "规则", "发现", "偏好"]


class DBMemoryProvider(MemoryProvider):
    """基于 AgentMemory 表的记忆提供者"""

    def __init__(self):
        super().__init__()
        self._db: Optional[Session] = None
        self._agent_id: int = 0

    async def initialize(self, agent_code: str, **kwargs) -> None:
        self._agent_code = agent_code
        self._agent_id = kwargs.get("agent_id", 0)
        self._db = kwargs.get("db")

    def system_prompt_block(self) -> str:
        if not self._frozen_snapshot:
            return ""
        lines = []
        for item in self._frozen_snapshot:
            key = item.get("key", "")
            content = item.get("content", "")[:150]
            lines.append(f"- [{key}]: {content}")
        return "<memory-context>\n" + "\n".join(lines) + "\n</memory-context>"

    async def prefetch(self, session_id: str) -> list[dict]:
        if not self._db or not self._agent_id:
            return []
        from agents.memory_store import list_memories
        try:
            rows = list_memories(self._db, self._agent_id)
            self._frozen_snapshot = rows[:20]
        except Exception as e:
            logger.warning("Memory prefetch failed: %s", e)
            self._frozen_snapshot = []
        return self._frozen_snapshot or []

    async def prefetch_with_query(self, session_id: str, query: str) -> list[dict]:
        """带查询关键词的预加载 — 无条件加载全部，用 query 做相关性排序"""
        if not self._db or not self._agent_id:
            return []
        from agents.memory_store import list_memories
        try:
            all_rows = list_memories(self._db, self._agent_id)
            if query:
                scored = []
                query_lower = query.lower()
                for r in all_rows:
                    text = f"{r.get('key', '')} {r.get('content', '')}".lower()
                    score = 0
                    for word in query_lower.split():
                        if word in text:
                            score += 1
                    if score > 0:
                        scored.append((score, r))
                    else:
                        scored.append((0, r))
                scored.sort(key=lambda x: x[0], reverse=True)
                self._frozen_snapshot = [r for _, r in scored[:20]]
            else:
                self._frozen_snapshot = all_rows[:20]
        except Exception as e:
            logger.warning("Memory prefetch_with_query failed: %s", e)
            self._frozen_snapshot = []
        return self._frozen_snapshot or []

    async def sync_turn(self, session_id: str, messages: list[dict]) -> None:
        if len(messages) < 2 or not self._db:
            return
        last_assistant = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                last_assistant = msg.get("content", "") or ""
                break
        if not last_assistant or len(last_assistant) < 50:
            return
        if not any(m in last_assistant for m in _MEMORY_MARKERS):
            return
        key = f"auto_{last_assistant[:30].replace(' ', '_')}"
        await safe_write(self._db, self._agent_id, key, last_assistant[:500])

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        if not self._db or not self._agent_id:
            return []
        from agents.memory_store import search_memory as _search
        return _search(self._db, self._agent_id, query, limit=limit)

    async def on_session_switch(self, old_sid: str, new_sid: str) -> None:
        self._frozen_snapshot = None

    async def on_pre_compress(self, messages: list[dict]) -> str:
        from agents.memory_store import flush_from_context
        if not self._db or not self._agent_id:
            return ""
        try:
            flush_from_context(self._db, self._agent_id, messages)
        except Exception:
            pass
        return ""

    async def shutdown(self) -> None:
        self._db = None
        self._frozen_snapshot = None


async def safe_write(db: Session, agent_id: int, key: str, content: str) -> dict:
    """安全写入记忆（含注入检测）"""
    threat = scan_memory_value(content)
    if threat:
        logger.warning("Memory write blocked: threat=%s, key=%s", threat, key)
        return {"ok": False, "error": f"内容包含可疑模式: {threat}"}
    from agents.memory_store import save_memory
    return save_memory(db, agent_id, key, content, scope="auto", source="sync_turn")
