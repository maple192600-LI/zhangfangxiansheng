"""Agent API — CRUD + 聊天 SSE + 会话管理 + 文件上传"""
import logging
import os
import random
import string
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from db.tables import Agent, AIConfig, Skill
from agents.workspace import init_workspace, safe_path, list_files, get_agent_root
from agents.runtime import run_turn
from agents import session_store
from agents import memory_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


def _gen_agent_code() -> str:
    """生成唯一 agent 编码 ag_xxxxxx"""
    chars = string.ascii_lowercase + string.digits
    return "ag_" + "".join(random.choices(chars, k=6))


def _agent_to_dict(a: Agent) -> dict:
    return {
        "id": a.id,
        "agent_code": a.agent_code,
        "display_name": a.display_name,
        "role_prompt": a.role_prompt,
        "ai_config_id": a.ai_config_id,
        "workspace_path": a.workspace_path,
        "llm_timeout": a.llm_timeout,
        "llm_max_tokens": a.llm_max_tokens,
        "status": a.status,
        "sort_order": a.sort_order,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        "ai_config": {
            "id": a.ai_config.id,
            "provider": a.ai_config.provider,
            "display_name": a.ai_config.display_name,
            "model_name": a.ai_config.model_name,
        } if a.ai_config else None,
    }


# ── Agent CRUD ──

@router.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    """列出所有 active 的 agent"""
    rows = (
        db.query(Agent)
        .filter(Agent.status == "active")
        .order_by(Agent.sort_order.desc(), Agent.created_at.desc())
        .all()
    )
    return success([_agent_to_dict(a) for a in rows])


@router.post("/agents")
async def create_agent(request: Request, db: Session = Depends(get_db)):
    """新建 agent"""
    body = await request.json()
    display_name = (body.get("display_name") or "").strip()
    if not display_name:
        return error(1001, "请填写智能体名称")

    ai_config_id = body.get("ai_config_id")
    if not ai_config_id:
        return error(1001, "请选择 AI 配置")

    # 检查 AI 配置存在
    ai_cfg = db.query(AIConfig).filter(AIConfig.id == ai_config_id, AIConfig.status == "active").first()
    if not ai_cfg:
        return error(4001, "所选 AI 配置不存在或已停用")

    agent_code = _gen_agent_code()
    while db.query(Agent).filter(Agent.agent_code == agent_code).first():
        agent_code = _gen_agent_code()

    role_prompt = (body.get("role_prompt") or "").strip()
    workspace_path = init_workspace(agent_code)

    agent = Agent(
        agent_code=agent_code,
        display_name=display_name,
        role_prompt=role_prompt,
        ai_config_id=ai_config_id,
        workspace_path=workspace_path,
        permission_json="{}",
        status="active",
        sort_order=0,
        created_by="admin",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return success(_agent_to_dict(agent))


@router.get("/agents/{agent_id}")
def get_agent(agent_id: int, db: Session = Depends(get_db)):
    """获取 agent 详情"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")
    return success(_agent_to_dict(agent))


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: int, request: Request, db: Session = Depends(get_db)):
    """更新 agent 设置"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")

    body = await request.json()
    if "display_name" in body:
        name = (body["display_name"] or "").strip()
        if not name:
            return error(1001, "名称不能为空")
        agent.display_name = name
    if "role_prompt" in body:
        agent.role_prompt = body["role_prompt"] or ""
    if "ai_config_id" in body:
        ai_cfg = db.query(AIConfig).filter(AIConfig.id == body["ai_config_id"]).first()
        if not ai_cfg:
            return error(4001, "AI 配置不存在")
        agent.ai_config_id = body["ai_config_id"]
    if "llm_timeout" in body:
        val = body["llm_timeout"]
        if not isinstance(val, int) or val < 10 or val > 3600:
            return error(1001, "超时时间范围: 10~3600 秒")
        agent.llm_timeout = val
    if "llm_max_tokens" in body:
        val = body["llm_max_tokens"]
        if not isinstance(val, int) or val < 1024 or val > 524288:
            return error(1001, "最大 token 范围: 1024~524288")
        agent.llm_max_tokens = val

    db.commit()
    db.refresh(agent)
    return success(_agent_to_dict(agent))


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    """软删除 agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")
    agent.status = "deleted"
    db.commit()
    return success(None, "已删除")


# ── 会话管理 ──

@router.get("/agents/{agent_id}/sessions")
def list_sessions(agent_id: int, db: Session = Depends(get_db)):
    """列出 agent 的会话"""
    sessions = session_store.list_sessions(db, agent_id)
    return success(sessions)


@router.post("/agents/{agent_id}/sessions")
async def create_session(agent_id: int, request: Request, db: Session = Depends(get_db)):
    """创建新会话"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")
    body = {}
    try:
        body = await request.json() or {}
    except Exception:
        pass
    result = session_store.create_session(db, agent_id, title=body.get("title"))
    return success(result)


# ── 聊天 SSE ──

@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: int, request: Request, db: Session = Depends(get_db)):
    """发送消息并流式返回 AI 回复（SSE）"""
    body = await request.json()
    user_text = (body.get("content") or "").strip()
    if not user_text:
        return error(1001, "消息内容不能为空")

    # 获取会话
    session = session_store.get_session(db, session_id)
    if not session:
        return error(2001, "会话不存在")

    # 获取 agent
    agent = db.query(Agent).filter(Agent.id == session["agent_id"]).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")

    async def event_stream():
        async for chunk in run_turn(agent, session_id, user_text, db):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── 消息历史 ──

@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: int, db: Session = Depends(get_db)):
    """获取会话消息历史"""
    from db.tables import AgentMessage
    rows = (
        db.query(AgentMessage)
        .filter(AgentMessage.session_id == session_id)
        .order_by(AgentMessage.id.asc())
        .all()
    )
    messages = []
    for m in rows:
        messages.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "tool_call_json": m.tool_call_json,
            "tool_result_json": m.tool_result_json,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return success(messages)


# ── AI 配置列表（新建 agent 时用） ──

@router.get("/ai-configs")
def list_ai_configs(db: Session = Depends(get_db)):
    """列出可用的 AI 配置"""
    rows = db.query(AIConfig).filter(AIConfig.status == "active").all()
    result = []
    for c in rows:
        result.append({
            "id": c.id,
            "provider": c.provider,
            "display_name": c.display_name,
            "model_name": c.model_name,
            "base_url": c.base_url,
        })
    return success(result)


# ── 文件管理 ──

@router.get("/agents/{agent_id}/files")
def list_agent_files(agent_id: int, sub_dir: str = "workspace", db: Session = Depends(get_db)):
    """列出 agent 工作区文件"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")
    files = list_files(agent.agent_code, sub_dir)
    return success(files)


@router.post("/agents/{agent_id}/files/upload")
async def upload_agent_file(agent_id: int, file: UploadFile = File(...), sub_dir: str = "inbox", db: Session = Depends(get_db)):
    """上传文件到 agent 工作区"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")

    filename = file.filename or "unknown"
    # 安全路径检查
    rel_dir = f"workspace/{sub_dir}"
    abs_dir = safe_path(agent.agent_code, rel_dir)
    if not abs_dir:
        return error(3001, "无效的目标目录")

    os.makedirs(abs_dir, exist_ok=True)
    # 安全文件名
    safe_name = os.path.basename(filename)
    abs_path = os.path.join(abs_dir, safe_name)

    content = await file.read()
    # 限制文件大小 20MB
    if len(content) > 20 * 1024 * 1024:
        return error(3002, "文件大小不能超过 20MB")

    with open(abs_path, "wb") as f:
        f.write(content)

    return success({
        "filename": safe_name,
        "size": len(content),
        "path": f"{rel_dir}/{safe_name}",
    })


# ── 技能管理 ──

# ── 记忆管理 ──

@router.get("/agents/{agent_id}/memories")
def list_agent_memories(agent_id: int, db: Session = Depends(get_db)):
    """列出 agent 的所有记忆"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")
    memories = memory_store.list_memories(db, agent_id)
    return success(memories)


@router.post("/agents/{agent_id}/memories")
async def save_agent_memory(agent_id: int, request: Request, db: Session = Depends(get_db)):
    """保存一条记忆"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")
    body = await request.json()
    key = (body.get("key") or "").strip()
    content = (body.get("content") or "").strip()
    if not key or not content:
        return error(1001, "标题和内容不能为空")
    result = memory_store.save_memory(db, agent_id, key, content, source="user")
    return success(result)


@router.delete("/agents/{agent_id}/memories/{memory_id}")
def delete_agent_memory(agent_id: int, memory_id: int, db: Session = Depends(get_db)):
    """删除一条记忆"""
    from db.tables import AgentMemory
    mem = db.query(AgentMemory).filter(
        AgentMemory.id == memory_id, AgentMemory.agent_id == agent_id
    ).first()
    if not mem:
        return error(2001, "记忆不存在")
    db.delete(mem)
    db.commit()
    return success(None, "已删除")


@router.delete("/agents/{agent_id}/sessions/{session_id}")
def delete_agent_session(agent_id: int, session_id: int, db: Session = Depends(get_db)):
    """软删除会话"""
    from db.tables import AgentSession
    session = db.query(AgentSession).filter(
        AgentSession.id == session_id, AgentSession.agent_id == agent_id
    ).first()
    if not session:
        return error(2001, "会话不存在")
    session.status = "deleted"
    db.commit()
    return success(None, "已删除")


# ── 技能管理 ──

@router.get("/agents/{agent_id}/skills")
def list_agent_skills(agent_id: int, db: Session = Depends(get_db)):
    """列出 agent 的技能"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")

    rows = db.query(Skill).filter(
        (Skill.owner_agent_id == agent_id) | (Skill.owner_agent_id.is_(None)),
        Skill.status.in_(["verified", "draft"]),
    ).all()

    skills = []
    for s in rows:
        skills.append({
            "id": s.id,
            "skill_code": s.skill_code,
            "display_name": s.display_name,
            "description": s.description,
            "status": s.status,
            "is_global": s.owner_agent_id is None,
            "verified_at": s.verified_at.isoformat() if s.verified_at else None,
        })
    return success(skills)


@router.get("/agents/{agent_id}/skills/{skill_code}")
def get_skill_detail(agent_id: int, skill_code: str, db: Session = Depends(get_db)):
    """获取技能详情（含源码）"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")

    skill = db.query(Skill).filter(
        Skill.skill_code == skill_code,
        (Skill.owner_agent_id == agent_id) | (Skill.owner_agent_id.is_(None)),
    ).first()
    if not skill:
        return error(2001, "技能不存在")

    result = {
        "id": skill.id,
        "skill_code": skill.skill_code,
        "display_name": skill.display_name,
        "description": skill.description,
        "status": skill.status,
        "is_global": skill.owner_agent_id is None,
        "verified_at": skill.verified_at.isoformat() if skill.verified_at else None,
        "test_pass_count": skill.test_pass_count,
        "test_fail_count": skill.test_fail_count,
    }

    # 读取源码
    from agents.skill_loader import get_skill_path
    import os
    skill_path = get_skill_path(agent.agent_code, skill_code)
    if os.path.isdir(skill_path):
        run_py = os.path.join(skill_path, "run.py")
        if os.path.isfile(run_py):
            with open(run_py, "r", encoding="utf-8", errors="replace") as f:
                result["run_py"] = f.read()
        manifest_path = os.path.join(skill_path, "manifest.yaml")
        if os.path.isfile(manifest_path):
            with open(manifest_path, "r", encoding="utf-8", errors="replace") as f:
                result["manifest"] = f.read()

    return success(result)


@router.post("/agents/{agent_id}/skill-run")
async def run_agent_skill(agent_id: int, request: Request, db: Session = Depends(get_db)):
    """手动运行一个技能"""
    from agents.tool_registry import ToolContext
    from agents.tools.skill_ops import skill_run

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")

    body = await request.json()
    skill_code = body.get("skill_code", "")
    if not skill_code:
        return error(1001, "请指定技能编码")

    ctx = ToolContext(agent_id=agent_id, agent_code=agent.agent_code, session_id=0, db=db)
    kwargs = {k: v for k, v in body.items() if k not in ("skill_code",)}
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: skill_run(skill_code, ctx=ctx, **kwargs))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error(5000, f"技能执行失败: {e}")
    return success(result)


@router.post("/agents/{agent_id}/skill-test")
async def test_agent_skill(agent_id: int, request: Request, db: Session = Depends(get_db)):
    """手动测试一个技能"""
    from agents.tool_registry import ToolContext
    from agents.tools.skill_ops import skill_test

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status == "deleted":
        return error(2001, "智能体不存在")

    body = await request.json()
    skill_code = body.get("skill_code", "")
    if not skill_code:
        return error(1001, "请指定技能编码")

    ctx = ToolContext(agent_id=agent_id, agent_code=agent.agent_code, session_id=0, db=db)
    kwargs = {k: v for k, v in body.items() if k not in ("skill_code",)}
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: skill_test(skill_code, ctx=ctx, **kwargs))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error(5000, f"技能测试失败: {e}")
    return success(result)
