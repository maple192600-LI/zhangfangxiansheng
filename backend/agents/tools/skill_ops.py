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


@register_tool(read_only=False)
def skill_save(
    skill_code: str,
    display_name: str,
    description: str,
    run_py: str = "",
    workflow_md: str = "",
    execution_mode: str = "code",
    triggers: list = None,
    ctx: ToolContext = None,
    **kwargs,
) -> dict:
    """将当前工作代码保存为可复用技能。

    这是技能创建的核心方式：Agent 在对话中开发了可用的代码或流程后，
    调用此工具将其固化为技能，后续可自动触发复用。

    参数：
    - skill_code: 技能编码（kebab-case，如 parse_boc）
    - display_name: 显示名称（如 "中国银行流水解析"）
    - description: 一句话描述
    - run_py: Python 代码内容（code/hybrid 模式必需）
    - workflow_md: 工作流程描述（instruction/hybrid 模式必需）
    - execution_mode: code（纯代码）/ instruction（纯指令）/ hybrid（两者都有）
    - triggers: 触发关键词列表
    - 其他 kwargs 将作为 skill 的 arguments 定义
    """
    from agents.workspace import get_agent_root
    from agents.skill_creator import generate_skill_md

    skill_dir = os.path.join(get_agent_root(ctx.agent_code), "skills", skill_code)
    if os.path.isdir(skill_dir):
        # 已存在 — 创建新版本
        import shutil
        backup_dir = skill_dir + "_bak"
        if os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.copytree(skill_dir, backup_dir)

    os.makedirs(os.path.join(skill_dir, "tests"), exist_ok=True)

    # 确定 allowed_tools
    allowed_tools = ["file_parse", "db_query_business", "memory_save", "memory_search", "skill_step_report"]
    if run_py:
        allowed_tools.append("skill_run")

    # 确定 arguments
    arguments = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            arguments[key] = {"description": value, "required": True}

    # 生成 SKILL.md
    skill_md = generate_skill_md(
        name=skill_code,
        display_name=display_name,
        description=description,
        when_to_use=f"当用户需要{description}时",
        version="1.0.0",
        execution_mode=execution_mode,
        allowed_tools=allowed_tools,
        arguments=arguments,
        workflow=workflow_md or f"## 工作流程\n\n此技能通过确定性代码执行，参见 run.py。",
        rules="- 遵循 run.py 中的逻辑",
        triggers=triggers or [display_name],
    )

    with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_md)

    # 写 run.py（如果有）
    if run_py:
        with open(os.path.join(skill_dir, "run.py"), "w", encoding="utf-8") as f:
            f.write(run_py)

    # 初始化 experience.json
    exp_file = os.path.join(skill_dir, "experience.json")
    if not os.path.isfile(exp_file):
        import json as _json
        with open(exp_file, "w", encoding="utf-8") as f:
            _json.dump({
                "stats": {"total_runs": 0, "successes": 0, "total_ms": 0},
                "learned_aliases": {},
                "corrections": [],
            }, f, ensure_ascii=False, indent=2)

    # 初始化 .meta.json
    meta_file = os.path.join(skill_dir, ".meta.json")
    import json as _json
    with open(meta_file, "w", encoding="utf-8") as f:
        _json.dump({
            "source": "agent_created",
            "lifecycle": "active",
            "created_at": datetime.now().isoformat(),
            "last_used_at": datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)

    # 入库
    from db.tables import Skill
    existing = ctx.db.query(Skill).filter(Skill.skill_code == skill_code).first()
    if existing:
        existing.display_name = display_name
        existing.description = description
        existing.source_path = skill_dir
        existing.updated_at = datetime.now()
    else:
        ctx.db.add(Skill(
            skill_code=skill_code,
            display_name=display_name,
            description=description,
            owner_agent_id=ctx.agent_id,
            source_path=skill_dir,
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ))
    ctx.db.commit()

    # 重新加载 registry
    from agents.skill_registry import skill_registry
    skill_registry.startup_scan(agent_code=ctx.agent_code)

    return {
        "ok": True,
        "skill_code": skill_code,
        "path": skill_dir,
        "mode": execution_mode,
        "has_run_py": bool(run_py),
        "message": f"技能 '{display_name}' 已保存（{execution_mode}模式）",
    }


@register_tool(read_only=False)
def skill_learn(
    skill_code: str,
    correction_type: str,
    wrong_value: str,
    correct_value: str,
    ctx: ToolContext = None,
) -> dict:
    """将用户修正反馈记录到技能经验中，实现技能自进化。

    当用户说"这个不对，应该是..."时调用此工具。

    correction_type:
    - "alias": 列名/字段别名映射修正
    - "summary": 摘要生成规则修正
    - "direction": 收支方向修正
    - "mapping": 字段映射修正
    """
    from agents.skill_registry import skill_registry
    from agents.skill_executor import record_correction, record_alias

    skill = skill_registry.get_skill(skill_code)
    if not skill:
        return {"ok": False, "error": f"技能未注册: {skill_code}"}

    if correction_type == "alias":
        record_alias(skill.skill_dir, wrong_value, correct_value)
    else:
        record_correction(skill.skill_dir, correction_type, wrong_value, correct_value)

    return {
        "ok": True,
        "skill": skill_code,
        "type": correction_type,
        "message": f"已记录修正: {wrong_value} → {correct_value}",
    }


@register_tool(read_only=False)
def skill_upgrade(
    skill_code: str,
    run_py: str = None,
    workflow_md: str = None,
    new_triggers: list = None,
    ctx: ToolContext = None,
) -> dict:
    """升级现有技能的代码或指令（保留旧版本到 .archive/）。

    用于技能迭代：修复 bug、增加功能、适应新格式等。
    """
    from agents.skill_registry import skill_registry

    skill = skill_registry.get_skill(skill_code)
    if not skill:
        return {"ok": False, "error": f"技能未注册: {skill_code}"}

    skill_dir = skill.skill_dir

    # 备份当前版本
    import shutil
    from datetime import datetime as _dt
    archive_dir = os.path.join(os.path.dirname(skill_dir), ".archive")
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{os.path.basename(skill_dir)}_v{skill.version}_{timestamp}"
    shutil.copytree(skill_dir, os.path.join(archive_dir, backup_name))

    # 更新 run.py
    if run_py:
        with open(os.path.join(skill_dir, "run.py"), "w", encoding="utf-8") as f:
            f.write(run_py)

    # 更新 SKILL.md body
    if workflow_md:
        from agents.skill_registry import parse_frontmatter
        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()
        meta, _ = parse_frontmatter(content)
        # 更新版本号
        old_ver = meta.get("version", "1.0.0")
        parts = old_ver.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        new_ver = ".".join(parts)
        meta["version"] = new_ver

        if new_triggers:
            meta["triggers"] = new_triggers

        # 重建 SKILL.md
        import yaml
        frontmatter = yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()
        new_content = f"---\n{frontmatter}\n---\n\n{workflow_md}"
        with open(skill_md_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    # 重新加载
    skill_registry.hot_reload(force=True)

    return {
        "ok": True,
        "skill_code": skill_code,
        "backup": backup_name,
        "message": f"技能 {skill_code} 已升级，旧版本已备份为 {backup_name}",
    }

