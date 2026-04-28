"""记忆持久化管理"""
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from db.tables import AgentMemory


def save_memory(
    db: Session,
    agent_id: int,
    key: str,
    content: str,
    scope: str = "agent",
    source: Optional[str] = None,
) -> dict:
    """保存一条记忆（同 key 覆盖）"""
    existing = db.query(AgentMemory).filter(
        AgentMemory.agent_id == agent_id,
        AgentMemory.key == key,
    ).first()
    if existing:
        existing.content = content
        existing.scope = scope
        existing.source = source
        existing.last_used_at = datetime.now()
        db.commit()
        db.refresh(existing)
        return _to_dict(existing)

    mem = AgentMemory(
        agent_id=agent_id,
        key=key,
        content=content,
        scope=scope,
        source=source,
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return _to_dict(mem)


def search_memory(db: Session, agent_id: int, query: str, limit: int = 10) -> list[dict]:
    """搜索记忆（简单关键词匹配）"""
    rows = (
        db.query(AgentMemory)
        .filter(
            AgentMemory.agent_id == agent_id,
            AgentMemory.key.contains(query) | AgentMemory.content.contains(query),
        )
        .order_by(AgentMemory.last_used_at.desc())
        .limit(limit)
        .all()
    )
    return [_to_dict(r) for r in rows]


def list_memories(db: Session, agent_id: int) -> list[dict]:
    """列出所有记忆"""
    rows = (
        db.query(AgentMemory)
        .filter(AgentMemory.agent_id == agent_id)
        .order_by(AgentMemory.last_used_at.desc())
        .all()
    )
    return [_to_dict(r) for r in rows]


def _to_dict(m: AgentMemory) -> dict:
    return {
        "id": m.id,
        "agent_id": m.agent_id,
        "key": m.key,
        "content": m.content,
        "scope": m.scope,
        "confidence": float(m.confidence) if m.confidence else 1.0,
        "source": m.source,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "last_used_at": m.last_used_at.isoformat() if m.last_used_at else None,
    }
