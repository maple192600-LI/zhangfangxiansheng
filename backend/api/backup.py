"""备份恢复 API"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text, inspect as sa_inspect
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import backup_service as svc
from services import log_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backups", tags=["backup"])


@router.get("")
def list_backups():
    try:
        data = svc.list_backups()
        return success(data)
    except Exception as e:
        logger.error("获取备份列表失败: %s", str(e), exc_info=True)
        return error(5000, "获取备份列表失败")


@router.post("/create")
def create_backup(db: Session = Depends(get_db)):
    try:
        data = svc.create_backup(db)
        log_service.write_log(db, action="backup_create", module="backup", detail={
            "filename": data.get("filename"),
            "size_mb": data.get("size_mb"),
        })
        return success(data)
    except Exception as e:
        logger.error("创建备份失败: %s", str(e), exc_info=True)
        return error(5000, "创建备份失败，请查看操作日志")


class RestoreRequest(BaseModel):
    filename: str


@router.post("/restore")
def restore_backup(req: RestoreRequest, db: Session = Depends(get_db)):
    try:
        data = svc.restore_backup(req.filename)
        log_service.write_log(db, action="backup_restore", module="backup", detail={
            "restored_from": req.filename,
        })
        return success(data)
    except ValueError as e:
        return error(2001, str(e))
    except Exception as e:
        logger.error("恢复备份失败: %s", str(e), exc_info=True)
        return error(5000, "恢复备份失败，请查看操作日志")


# ── 数据清理 ──


@router.get("/cleanup/preview")
def cleanup_preview(db: Session = Depends(get_db)):
    """预览可清理的残留数据"""
    result = {}

    # 1. deleted agents 及其关联数据
    deleted_agents = db.execute(text(
        'SELECT id, agent_code, display_name, created_at FROM agents_v2 WHERE status = "deleted"'
    )).fetchall()
    agent_items = []
    for a in deleted_agents:
        sessions = db.execute(text('SELECT COUNT(*) FROM agent_sessions WHERE agent_id = :id'), {"id": a[0]}).scalar()
        msgs = db.execute(text(
            'SELECT COUNT(*) FROM agent_messages m JOIN agent_sessions s ON m.session_id = s.id WHERE s.agent_id = :id'
        ), {"id": a[0]}).scalar()
        mems = db.execute(text('SELECT COUNT(*) FROM agent_memories WHERE agent_id = :id'), {"id": a[0]}).scalar()
        skills = db.execute(text('SELECT COUNT(*) FROM skills_v2 WHERE owner_agent_id = :id'), {"id": a[0]}).scalar()
        agent_items.append({
            "id": a[0], "agent_code": a[1], "display_name": a[2],
            "created_at": str(a[3]), "sessions": sessions, "messages": msgs,
            "memories": mems, "skills": skills,
        })
    result["deleted_agents"] = agent_items

    # 2. deleted sessions（属于 active agent 的）
    del_sessions = db.execute(text(
        'SELECT s.id, s.agent_id, s.title, s.created_at, a.display_name '
        'FROM agent_sessions s JOIN agents_v2 a ON s.agent_id = a.id '
        'WHERE s.status = "deleted"'
    )).fetchall()
    session_items = []
    for s in del_sessions:
        msg_count = db.execute(text('SELECT COUNT(*) FROM agent_messages WHERE session_id = :id'), {"id": s[0]}).scalar()
        session_items.append({
            "id": s[0], "agent_id": s[1], "title": s[2],
            "created_at": str(s[3]), "agent_name": s[4], "messages": msg_count,
        })
    result["deleted_sessions"] = session_items

    # 3. draft skills
    draft_skills = db.execute(text(
        'SELECT id, skill_code, display_name, owner_agent_id, created_at '
        'FROM skills_v2 WHERE status = "draft"'
    )).fetchall()
    result["draft_skills"] = [
        {"id": s[0], "skill_code": s[1], "display_name": s[2],
         "owner_agent_id": s[3], "created_at": str(s[4])}
        for s in draft_skills
    ]

    # 4. 汇总计数
    total_agents = len(agent_items)
    total_sessions = len(session_items)
    total_skills = len(draft_skills)
    total_msgs = sum(a["messages"] for a in agent_items) + sum(s["messages"] for s in session_items)
    total_mems = sum(a["memories"] for a in agent_items)

    result["summary"] = {
        "deleted_agents": total_agents,
        "deleted_sessions": total_sessions,
        "draft_skills": total_skills,
        "linked_messages": total_msgs,
        "linked_memories": total_mems,
    }
    return success(result)


@router.post("/cleanup/execute")
def cleanup_execute(db: Session = Depends(get_db)):
    """执行数据清理——级联硬删除所有 deleted 状态的 agent/session 及关联数据"""
    counts = {"agents": 0, "sessions": 0, "messages": 0, "memories": 0, "skills": 0, "draft_skills": 0}

    # 1. 清理 deleted agents 的关联数据，再删除 agent
    deleted_agents = db.execute(text('SELECT id FROM agents_v2 WHERE status = "deleted"')).fetchall()
    for (agent_id,) in deleted_agents:
        # 获取该 agent 的所有 session（含 deleted）
        session_ids = [r[0] for r in db.execute(
            text('SELECT id FROM agent_sessions WHERE agent_id = :id'), {"id": agent_id}
        ).fetchall()]
        if session_ids:
            placeholders = ",".join(str(sid) for sid in session_ids)
            msg_count = db.execute(text(f'DELETE FROM agent_messages WHERE session_id IN ({placeholders})')).rowcount
            counts["messages"] += msg_count
            db.execute(text(f'DELETE FROM agent_sessions WHERE id IN ({placeholders})'))
            counts["sessions"] += len(session_ids)

        mem_count = db.execute(text('DELETE FROM agent_memories WHERE agent_id = :id'), {"id": agent_id}).rowcount
        counts["memories"] += mem_count

        skill_count = db.execute(text('DELETE FROM skills_v2 WHERE owner_agent_id = :id'), {"id": agent_id}).rowcount
        counts["skills"] += skill_count

        db.execute(text('DELETE FROM agents_v2 WHERE id = :id'), {"id": agent_id})
        counts["agents"] += 1

    # 2. 清理 active agent 下 deleted sessions
    del_sessions = db.execute(text(
        'SELECT id FROM agent_sessions WHERE status = "deleted"'
    )).fetchall()
    for (session_id,) in del_sessions:
        msg_count = db.execute(text('DELETE FROM agent_messages WHERE session_id = :id'), {"id": session_id}).rowcount
        counts["messages"] += msg_count
        db.execute(text('DELETE FROM agent_sessions WHERE id = :id'), {"id": session_id})
        counts["sessions"] += 1

    # 3. 清理 draft skills（无 owner 的或属于已删除 agent 的）
    db.execute(text(
        'DELETE FROM skills_v2 WHERE status = "draft" AND '
        '(owner_agent_id IS NULL OR owner_agent_id IN (SELECT id FROM agents_v2 WHERE status = "deleted"))'
    ))
    # 再清理属于 active agent 的 draft skills（开发阶段的迭代残留）
    draft_left = db.execute(text('SELECT id FROM skills_v2 WHERE status = "draft"')).fetchall()
    for (sid,) in draft_left:
        db.execute(text('DELETE FROM skills_v2 WHERE id = :id'), {"id": sid})
        counts["draft_skills"] += 1

    db.commit()

    log_service.write_log(db, action="data_cleanup", module="system", detail=counts)
    logger.info("数据清理完成: %s", counts)
    return success(counts, "清理完成")
