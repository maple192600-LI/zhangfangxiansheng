"""记忆持久化管理


- 保留原有 save/search/list 接口
- 新增 get_relevant: 根据关键词自动检索
- 新增 auto_search_and_format: 检索并格式化为可注入文本
"""
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
    """搜索记忆（关键词匹配）"""
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


def get_relevant(db: Session, agent_id: int, query: str, limit: int = 5) -> list[dict]:
    """根据查询自动检索相关记忆

    使用多关键词拆分搜索，提高召回率。
    """
    keywords = [w for w in query.split() if len(w) > 1]
    if not keywords:
        return []

    rows = (
        db.query(AgentMemory)
        .filter(AgentMemory.agent_id == agent_id)
        .order_by(AgentMemory.last_used_at.desc())
        .limit(50)
        .all()
    )

    scored = []
    for row in rows:
        score = 0
        text = f"{row.key} {row.content}".lower()
        for kw in keywords:
            if kw.lower() in text:
                score += 1
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_to_dict(r) for _, r in scored[:limit]]


def auto_search_and_format(db: Session, agent_id: int, user_text: str) -> str:
    """自动检索相关记忆并格式化为可注入 system prompt 的文本"""
    memories = get_relevant(db, agent_id, user_text, limit=5)
    if not memories:
        return ""

    lines = []
    for m in memories:
        key = m.get("key", "")
        content = m.get("content", "")[:150]
        lines.append(f"- [{key}]: {content}")
    return "\n".join(lines)


def flush_from_context(db: Session, agent_id: int, messages: list[dict]) -> int:
    """从上下文消息中提取重要信息保存为记忆（压缩前调用）

    保存条件：assistant 消息中包含明确的结论、决策或数据总结。
    返回保存的记忆条数。
    """
    saved = 0
    for msg in messages[-20:]:
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        if not content or len(content) < 50:
            continue

        # 检测是否包含重要结论标记
        conclusion_markers = ["总结", "结论", "结果", "注意", "关键", "规则", "发现", "确定"]
        has_conclusion = any(m in content for m in conclusion_markers)
        if not has_conclusion:
            continue

        # 用前 50 字符作为 key
        key = f"auto_{content[:30].replace(' ', '_')}"
        save_memory(db, agent_id, key, content[:500], scope="auto", source="context_flush")
        saved += 1

    return saved


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
