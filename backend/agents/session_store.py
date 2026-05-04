"""会话历史管理"""
import json
import os
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from db.tables import AgentSession, AgentMessage


def create_session(db: Session, agent_id: int, title: Optional[str] = None) -> dict:
    """创建新会话"""
    session = AgentSession(
        agent_id=agent_id,
        title=title or "新会话",
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_to_dict(session)


def list_sessions(db: Session, agent_id: int) -> list[dict]:
    """列出 agent 的所有会话"""
    rows = (
        db.query(AgentSession)
        .filter(AgentSession.agent_id == agent_id, AgentSession.status == "active")
        .order_by(AgentSession.last_active_at.desc())
        .all()
    )
    return [_session_to_dict(s) for s in rows]


def get_session(db: Session, session_id: int) -> Optional[dict]:
    """获取会话详情"""
    s = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    return _session_to_dict(s) if s else None


def get_or_create_session(db: Session, agent_id: int, session_id: Optional[int] = None) -> dict:
    """获取指定会话，不存在则创建"""
    if session_id:
        s = db.query(AgentSession).filter(
            AgentSession.id == session_id,
            AgentSession.agent_id == agent_id,
            AgentSession.status == "active",
        ).first()
        if s:
            return _session_to_dict(s)
    return create_session(db, agent_id)


def load_recent_messages(db: Session, session_id: int, limit: int = 50) -> list[dict]:
    """加载最近 N 条消息，用于 LLM 上下文"""
    rows = (
        db.query(AgentMessage)
        .filter(AgentMessage.session_id == session_id)
        .order_by(AgentMessage.id.desc())
        .limit(limit)
        .all()
    )
    # 倒序后需要翻转
    rows = list(reversed(rows))
    result = []
    for r in rows:
        # 跳过错误消息（以 [错误] 开头的 assistant 消息），避免污染 LLM 上下文
        if r.role == "assistant" and r.content and r.content.startswith("[错误]"):
            continue
        # 跳过完全空的 assistant 消息（无 content、无 tool_call、无 reasoning）
        if r.role == "assistant" and not r.content and not r.tool_call_json and not r.reasoning_content:
            continue
        msg = {"role": r.role}
        if r.content:
            msg["content"] = r.content
        if r.reasoning_content is not None:
            msg["reasoning_content"] = r.reasoning_content
        if r.tool_result_json:
            msg["tool_result"] = json.loads(r.tool_result_json)

        if r.role == "tool":
            # tool 消息：只提取 tool_call_id，不设置 tool_calls
            if r.tool_call_json:
                try:
                    tc_info = json.loads(r.tool_call_json)
                    if "tool_call_id" in tc_info:
                        msg["tool_call_id"] = tc_info["tool_call_id"]
                except (json.JSONDecodeError, TypeError):
                    pass
        elif r.tool_call_json:
            # assistant 消息：设置 tool_calls
            raw = json.loads(r.tool_call_json)
            msg["tool_calls"] = [raw] if isinstance(raw, dict) else raw

        result.append(msg)
    return result


def save_message(
    db: Session,
    session_id: int,
    role: str,
    content: Optional[str] = None,
    tool_call_json: Optional[str] = None,
    tool_result_json: Optional[str] = None,
    duration_ms: Optional[int] = None,
    reasoning_content: Optional[str] = None,
) -> dict:
    """保存一条消息"""
    msg = AgentMessage(
        session_id=session_id,
        role=role,
        content=content,
        reasoning_content=reasoning_content,
        tool_call_json=tool_call_json,
        tool_result_json=tool_result_json,
        duration_ms=duration_ms,
    )
    db.add(msg)
    # 更新会话活跃时间
    db.query(AgentSession).filter(AgentSession.id == session_id).update(
        {"last_active_at": datetime.now()}
    )
    db.commit()
    db.refresh(msg)
    return _message_to_dict(msg)


def _session_to_dict(s: AgentSession) -> dict:
    return {
        "id": s.id,
        "agent_id": s.agent_id,
        "title": s.title,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
    }


def _message_to_dict(m: AgentMessage) -> dict:
    return {
        "id": m.id,
        "session_id": m.session_id,
        "role": m.role,
        "content": m.content,
        "tool_call_json": m.tool_call_json,
        "tool_result_json": m.tool_result_json,
        "duration_ms": m.duration_ms,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
