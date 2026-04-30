"""技能操作工具"""
import json
import os
from datetime import datetime

from agents.tool_registry import register_tool, ToolContext
from agents.workspace import safe_path


@register_tool(read_only=True)
def skill_list(ctx: ToolContext = None) -> dict:
    """列出当前 agent 可用的所有技能。"""
    from db.tables import Skill

    db = ctx.db
    rows = db.query(Skill).filter(
        (Skill.owner_agent_id == ctx.agent_id) | (Skill.owner_agent_id.is_(None)),
        Skill.status.in_(["verified", "draft"]),
    ).all()

    skills = []
    for s in rows:
        skills.append({
            "skill_code": s.skill_code,
            "display_name": s.display_name,
            "description": s.description,
            "status": s.status,
            "verified_at": s.verified_at.isoformat() if s.verified_at else None,
        })
    return {"skills": skills, "count": len(skills)}


@register_tool(read_only=True)
def skill_run(skill_code: str, ctx: ToolContext = None, **kwargs) -> dict:
    """运行一个技能。skill_code 为技能编码，其他参数传给技能的 run(params)。"""
    from agents.skill_loader import get_skill_path, run_skill

    # 查找 skill 路径
    agent_code = ctx.agent_code
    skill_path = get_skill_path(agent_code, skill_code)

    if not os.path.isdir(skill_path):
        return {"ok": False, "error": f"技能不存在: {skill_code}"}

    # 构建参数
    params = dict(kwargs)

    # 注入 agent 工作区路径
    from agents.workspace import get_agent_root
    params["_agent_root"] = get_agent_root(agent_code)

    # 如果有 file_path，转为绝对路径
    if "file_path" in params:
        abs_path = safe_path(agent_code, params["file_path"])
        if abs_path:
            params["file_path"] = abs_path
        else:
            return {"ok": False, "error": f"文件路径越界: {params['file_path']}"}

    result = run_skill(skill_path, params)
    return result


@register_tool(read_only=False)
def skill_test(skill_code: str, ctx: ToolContext = None, **kwargs) -> dict:
    """测试一个技能。运行技能并比对 expected.json。"""
    from agents.skill_loader import get_skill_path, test_skill

    skill_path = get_skill_path(ctx.agent_code, skill_code)
    if not os.path.isdir(skill_path):
        return {"ok": False, "error": f"技能不存在: {skill_code}"}

    params = dict(kwargs)
    return test_skill(skill_path, params)


@register_tool(read_only=False)
def skill_create(
    skill_code: str,
    display_name: str,
    description: str,
    run_py: str,
    ctx: ToolContext = None,
    manifest_yaml: str = None,
) -> dict:
    """创建新技能。写入 run.py 和 manifest.yaml 到 skill 目录。"""
    from agents.workspace import get_agent_root

    skill_dir = os.path.join(get_agent_root(ctx.agent_code), "skills", skill_code)
    if os.path.isdir(skill_dir):
        return {"ok": False, "error": f"技能已存在: {skill_code}"}

    os.makedirs(os.path.join(skill_dir, "tests"), exist_ok=True)

    # 写 run.py
    run_path = os.path.join(skill_dir, "run.py")
    with open(run_path, "w", encoding="utf-8") as f:
        f.write(run_py)

    # 写 manifest.yaml
    if manifest_yaml:
        manifest_path = os.path.join(skill_dir, "manifest.yaml")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest_yaml)

    # 入库
    from db.tables import Skill
    import yaml

    manifest = {}
    if manifest_yaml:
        try:
            manifest = yaml.safe_load(manifest_yaml) or {}
        except Exception:
            pass

    skill = Skill(
        skill_code=skill_code,
        display_name=display_name,
        description=description,
        owner_agent_id=ctx.agent_id,
        manifest_json=json.dumps(manifest, ensure_ascii=False),
        source_path=skill_dir,
        status="draft",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    ctx.db.add(skill)
    ctx.db.commit()

    return {"ok": True, "skill_code": skill_code, "path": skill_dir}
