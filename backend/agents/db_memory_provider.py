"""DB MemoryProvider — 基于 SQLAlchemy / AgentMemory 表

实现 MemoryProvider ABC 的 5 阶段生命周期。
封装 memory_store.py 的 CRUD 操作，增加冻结快照和注入检测。
"""
import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from agents.memory_provider import MemoryProvider, scan_memory_value

logger = logging.getLogger(__name__)

_MEMORY_MARKERS = ["总结", "结论", "规则", "偏好", "业务规则", "注意事项"]


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
        return "\n".join(lines)

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
        """带查询关键词的预加载 — 用 query 做 SQL 预过滤 + Python 精排"""
        if not self._db or not self._agent_id:
            return []
        try:
            from db.tables import AgentMemory
            base_q = (
                self._db.query(AgentMemory)
                .filter(AgentMemory.agent_id == self._agent_id)
            )

            if query:
                query_lower = query.lower()
                # 构建查询关键词集合：原始词 + 中文 2-gram
                query_segs = set()
                for word in query_lower.split():
                    if len(word) >= 2:
                        query_segs.add(word)
                chinese = re.sub(r"[a-z0-9\s]", "", query_lower)
                for i in range(len(chinese) - 1):
                    query_segs.add(chinese[i:i + 2])

                # SQL 层：用 LIKE 做初步过滤（任意 segment 匹配即保留）
                from sqlalchemy import or_
                like_filters = []
                for seg in list(query_segs)[:10]:
                    like_filters.append(AgentMemory.content.ilike(f"%{seg}%"))
                    like_filters.append(AgentMemory.key.ilike(f"%{seg}%"))
                if like_filters:
                    filtered_rows = (
                        base_q.filter(or_(*like_filters))
                        .order_by(AgentMemory.last_used_at.desc())
                        .limit(40)
                        .all()
                    )
                else:
                    filtered_rows = (
                        base_q.order_by(AgentMemory.last_used_at.desc())
                        .limit(40)
                        .all()
                    )

                # Python 层：精确评分排序
                from agents.memory_store import _to_dict
                rows_dict = [_to_dict(r) for r in filtered_rows]
                scored = []
                for r in rows_dict:
                    text = f"{r.get('key', '')} {r.get('content', '')}".lower()
                    score = sum(1 for seg in query_segs if seg in text)
                    scored.append((score, r))
                scored.sort(key=lambda x: x[0], reverse=True)
                self._frozen_snapshot = [r for _, r in scored[:20]]
            else:
                from agents.memory_store import _to_dict
                rows = base_q.order_by(AgentMemory.last_used_at.desc()).limit(20).all()
                self._frozen_snapshot = [_to_dict(r) for r in rows]
        except Exception as e:
            logger.warning("Memory prefetch_with_query failed: %s", e)
            self._frozen_snapshot = []
        return self._frozen_snapshot or []

    async def sync_turn(self, session_id: str, messages: list[dict]) -> None:
        """自动保存回合记忆 — 只在明确有业务价值时保存

        条件（全部满足）：
        1. 有 assistant 回复且内容 >= 100 字
        2. 内容包含强标记词（规则、偏好、业务规则等）
        3. 内容有明确的结构化信息（有冒号或列表）
        """
        if len(messages) < 2 or not self._db:
            return
        last_assistant = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                last_assistant = msg.get("content", "") or ""
                break
        if not last_assistant or len(last_assistant) < 100:
            return
        if not any(m in last_assistant for m in _MEMORY_MARKERS):
            return
        # 要求有结构化信息（冒号、列表标记等）
        has_structure = any(c in last_assistant for c in [":", "：", "\n-", "1.", "•"])
        if not has_structure:
            return
        content_hash = hash(last_assistant[:500]) & 0xFFFF
        key = f"auto_{last_assistant[:20].replace(' ', '_')}_{content_hash}"
        await safe_write(self._db, self._agent_id, key, last_assistant[:500])

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        if not self._db or not self._agent_id:
            return []
        from agents.memory_store import search_memory as _search
        return _search(self._db, self._agent_id, query, limit=limit)

    async def list_all(self) -> list[dict]:
        """列出所有记忆"""
        if not self._db or not self._agent_id:
            return []
        from agents.memory_store import list_memories
        return list_memories(self._db, self._agent_id)

    async def save(self, key: str, content: str, scope: str = "user", source: Optional[str] = None) -> dict:
        """保存一条记忆"""
        return await safe_write(self._db, self._agent_id, key, content, scope=scope, source=source)

    async def delete(self, memory_id: int) -> bool:
        """删除一条记忆"""
        if not self._db or not self._agent_id:
            return False
        from db.tables import AgentMemory
        mem = self._db.query(AgentMemory).filter(
            AgentMemory.id == memory_id, AgentMemory.agent_id == self._agent_id
        ).first()
        if not mem:
            return False
        self._db.delete(mem)
        self._db.commit()
        return True

    async def update(self, memory_id: int, key: str, content: str) -> dict | None:
        """更新一条记忆"""
        if not self._db or not self._agent_id:
            return None
        from db.tables import AgentMemory
        mem = self._db.query(AgentMemory).filter(
            AgentMemory.id == memory_id, AgentMemory.agent_id == self._agent_id
        ).first()
        if not mem:
            return None
        if key:
            mem.key = key
        if content:
            mem.content = content
        self._db.commit()
        self._db.refresh(mem)
        return {"id": mem.id, "key": mem.key, "content": mem.content}

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


async def safe_write(
    db: Session,
    agent_id: int,
    key: str,
    content: str,
    scope: str = "auto",
    source: Optional[str] = None,
) -> dict:
    """安全写入记忆（含注入检测）"""
    threat = scan_memory_value(content)
    if threat:
        logger.warning("Memory write blocked: threat=%s, key=%s", threat, key)
        return {"ok": False, "error": f"内容包含可疑模式: {threat}"}
    from agents.memory_store import save_memory
    return save_memory(db, agent_id, key, content, scope=scope, source=source or "sync_turn")
