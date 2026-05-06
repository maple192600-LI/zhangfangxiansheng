"""技能操作工具"""
import json
import os
from datetime import datetime

from agents.tool_registry import register_tool, ToolContext
from agents.workspace import safe_path


@register_tool(read_only=True)
def skill_list(ctx: ToolContext = None) -> dict:
    """列出当前 agent 可用的所有技能及其状态。

    返回格式：{"skills": [{"skill_code": "...", "display_name": "...", "description": "...", "status": "verified|draft"}], "count": N}
    """
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
    """运行一个技能。skill_code 为技能编码（如 "fund_parser_bank"），其他参数传给技能的 run(params)。

    注意：对于基于 SKILL.md 的技能，通常不需要调用此工具，技能的指令会直接注入到上下文中由 LLM 执行。
    此工具主要用于兼容旧格式（有 run.py 的）技能。
    """
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


@register_tool(read_only=False)
def skill_install(
    source_path: str,
    agent_code: str = "system",
    auto_install_deps: bool = True,
    ctx: ToolContext = None,
) -> dict:
    """安装一个技能。source_path 可以是包含 SKILL.md 的目录路径或 zip 文件路径。
    agent_code 指定安装到哪个 agent（默认 system 全局可用）。
    auto_install_deps 为 True 时自动安装 pip 依赖。"""
    from agents.workspace import safe_path

    abs_path = safe_path(ctx.agent_code, source_path) if not os.path.isabs(source_path) else source_path
    if not abs_path:
        abs_path = source_path

    if not os.path.exists(abs_path):
        return {"ok": False, "error": f"路径不存在: {source_path}"}

    from agents.skill_installer import install_from_dir, install_from_zip

    if abs_path.endswith(".zip"):
        return install_from_zip(abs_path, agent_code, auto_install_deps)
    return install_from_dir(abs_path, agent_code, auto_install_deps)


@register_tool(read_only=True)
def skill_check_deps(skill_code: str, ctx: ToolContext = None) -> dict:
    """检查技能的依赖是否已满足。返回缺失的依赖列表和安装建议。"""
    from agents.skill_registry import skill_registry
    from agents.skill_deps import check_dependencies

    skill = skill_registry.get_skill(skill_code)
    if not skill:
        return {"ok": False, "error": f"技能未注册: {skill_code}"}

    if not skill.dependencies:
        return {"ok": True, "all_met": True, "message": "该技能无依赖声明"}

    result = check_dependencies(skill.dependencies, registry=skill_registry)
    return {
        "ok": True,
        "all_met": result.all_met,
        "summary": result.summary,
        "missing": [
            {"name": s.name, "type": s.dep_type, "required_spec": s.required_spec}
            for s in result.missing
        ],
        "installed": [
            {"name": s.name, "type": s.dep_type, "version": s.version}
            for s in result.statuses if s.installed
        ],
    }


@register_tool(read_only=False, toolset="database")
def fund_skill_run(skill_name: str, payload: dict = None, ctx: ToolContext = None) -> dict:
    """运行 Fund Agent 的确定性财务技能（直接执行 Python 代码，不经过 LLM）。

    可用技能：
    - parser.bank: 解析银行流水文件。payload 需含 file_path, account_code, template_id
    - parser.manual: 解析手工流水。payload 需含 records（流水记录列表）
    - rule.template_fill: 填充报表模板。payload 需含 template_id, data
    - rule.maintain: 维护规则。payload 需含 rule_id, changes
    - template.inference: 推断模板结构。payload 需含 file_path
    """
    from agents.fund.harness import FundAgent

    allowed = {"parser.bank", "parser.manual", "rule.template_fill", "rule.maintain", "template.inference"}
    if skill_name not in allowed:
        return {"ok": False, "error": f"未知的 Fund 技能: {skill_name}，可用: {', '.join(sorted(allowed))}"}

    try:
        agent = FundAgent(ctx.db)
        result = agent.run_skill(skill_name, payload or {})
        return {"ok": True, "result": result.payload}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@register_tool(read_only=True)
def skill_step_report(
    skill_code: str,
    step_number: int,
    step_name: str,
    result: str = "",
    ctx: ToolContext = None,
) -> dict:
    """技能步骤完成报告。每完成一个技能步骤后必须调用此工具汇报进度。

    这是技能执行跟踪机制的一部分，确保技能步骤被完整执行。
    """
    from agents.skill_registry import skill_registry

    skill = skill_registry.get_skill(skill_code)
    if not skill:
        return {"ok": False, "error": f"技能未注册: {skill_code}"}

    return {
        "ok": True,
        "skill": skill_code,
        "step": step_number,
        "step_name": step_name,
        "result": result[:500],
        "message": f"步骤 {step_number}（{step_name}）已确认完成",
    }
