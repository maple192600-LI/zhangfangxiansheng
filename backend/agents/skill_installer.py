"""技能安装编排器

安装流程：
  1. 来源验证（目录/zip/URL）
  2. 安全扫描（skill_scanner）
  3. manifest 验证（SKILL.md 格式）
  4. 依赖检查 → 可选自动安装
  5. 文件复制到目标目录
  6. 注册到 SkillRegistry + DB
  7. 依赖安装

卸载流程：
  1. 检查是否有其他技能依赖
  2. 删除文件
  3. 从 registry + DB 移除
"""
import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Optional, Union

from config import AGENTS_ROOT

logger = logging.getLogger(__name__)


def install_from_dir(
    source_dir: str,
    agent_code: str = "system",
    auto_install_deps: bool = True,
    skip_scan: bool = False,
    trust_level: str = "community",
) -> dict:
    """从本地目录安装技能

    支持格式自动检测：
      - 有 SKILL.md → 直接使用
      - 有 run.py 但无 SKILL.md → 自动生成 SKILL.md
      - 有 manifest.yaml → 转换为 SKILL.md
    """
    # 0. 格式自动检测
    source_dir = _ensure_skill_md(source_dir)
    if isinstance(source_dir, dict):
        return source_dir  # 返回了错误

    # 1. 验证 SKILL.md 存在
    skill_md = os.path.join(source_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return {"ok": False, "error": f"SKILL.md 不存在: {source_dir}"}

    # 2. 解析 manifest
    from agents.skill_registry import load_skill_l1, parse_frontmatter
    meta = load_skill_l1(source_dir)
    if not meta:
        return {"ok": False, "error": "SKILL.md 解析失败"}

    # 3. 安全扫描（根据信任级别）
    from agents.skill_scanner import TrustLevel, scan_skill_dir, format_report
    tl = TrustLevel(trust_level) if trust_level in [e.value for e in TrustLevel] else TrustLevel.COMMUNITY
    scan_result = None
    if not skip_scan:
        scan_result = scan_skill_dir(source_dir, trust_level=tl)
        if not scan_result.safe:
            return {
                "ok": False,
                "error": "安全扫描未通过",
                "scan_report": format_report(scan_result),
            }

    # 4. 确定目标目录
    skill_dirname = meta.name or meta.code
    target_dir = os.path.join(AGENTS_ROOT, agent_code, "skills", skill_dirname)

    # 4.5 用户定制保护：如果目标已存在且用户修改过，跳过覆盖
    if os.path.isdir(target_dir):
        if _is_user_customized(target_dir):
            return {
                "ok": False,
                "error": f"技能 '{skill_dirname}' 已被用户定制修改，跳过覆盖以保护用户更改",
                "target_dir": target_dir,
                "suggestion": "如需强制覆盖，请先备份后删除技能目录",
            }
        logger.info("技能已存在，覆盖更新: %s", target_dir)

    # 5. 复制文件
    os.makedirs(target_dir, exist_ok=True)
    for item in os.listdir(source_dir):
        s = os.path.join(source_dir, item)
        d = os.path.join(target_dir, item)
        if os.path.isdir(s):
            if os.path.isdir(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

    # 5.5 记录 content_hash 到 .meta.json
    from agents.skill_scanner import compute_content_hash
    content_hash = compute_content_hash(target_dir)
    meta_file = os.path.join(target_dir, ".meta.json")
    meta_data = {"source": "installed", "lifecycle": "active", "trust_level": tl.value}
    if content_hash:
        meta_data["content_hash"] = content_hash
    meta_data["installed_at"] = datetime.now().isoformat()
    meta_data["last_used_at"] = datetime.now().isoformat()
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, ensure_ascii=False, indent=2)

    # 6. 依赖检查
    from agents.skill_deps import check_dependencies, install_dependencies
    dep_result = check_dependencies(meta.dependencies)

    dep_install_result = None
    if not dep_result.all_met and auto_install_deps:
        pip_missing = [s.name for s in dep_result.missing if s.dep_type == "pip"]
        if pip_missing:
            dep_install_result = install_dependencies(meta.dependencies)

    # 7. 重新加载 registry
    from agents.skill_registry import skill_registry
    skill_registry.startup_scan(agent_code=agent_code if agent_code != "system" else None)

    return {
        "ok": True,
        "skill_code": meta.code,
        "name": meta.name,
        "version": meta.version,
        "target_dir": target_dir,
        "trust_level": tl.value,
        "scan_passed": scan_result.safe if scan_result else True,
        "content_hash": content_hash,
        "deps": {
            "all_met": dep_result.all_met,
            "missing": [s.name for s in dep_result.missing],
        },
        "deps_installed": dep_install_result,
    }


def _ensure_skill_md(source_dir: str) -> Union[str, dict]:
    """格式自动检测：确保源目录有 SKILL.md

    返回：source_dir（成功）或 error dict（失败）
    """
    skill_md = os.path.join(source_dir, "SKILL.md")
    if os.path.isfile(skill_md):
        return source_dir

    # 有 manifest.yaml → 转换
    manifest_yaml = os.path.join(source_dir, "manifest.yaml")
    if os.path.isfile(manifest_yaml):
        _convert_manifest_to_skill_md(source_dir, manifest_yaml)
        return source_dir

    # 有 run.py → 自动生成 SKILL.md
    run_py = os.path.join(source_dir, "run.py")
    if os.path.isfile(run_py):
        _generate_skill_md_from_run_py(source_dir, run_py)
        return source_dir

    return {"ok": False, "error": f"无法识别的技能格式: {source_dir}（缺少 SKILL.md、manifest.yaml 或 run.py）"}


def _convert_manifest_to_skill_md(source_dir: str, manifest_path: str) -> None:
    """将 manifest.yaml 转换为 SKILL.md"""
    import yaml
    from agents.skill_creator import generate_skill_md

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    dir_name = os.path.basename(source_dir)
    skill_md = generate_skill_md(
        name=data.get("code", dir_name),
        display_name=data.get("display_name", data.get("name", dir_name)),
        description=data.get("description", ""),
        when_to_use=data.get("when_to_use", ""),
        version=data.get("version", "1.0.0"),
        execution_mode="code" if os.path.isfile(os.path.join(source_dir, "run.py")) else "instruction",
        allowed_tools=data.get("allowed_tools", ["skill_run"]),
        arguments=data.get("arguments", {}),
        workflow="## 工作流程\n\n此技能通过确定性代码执行，参见 run.py。" if os.path.isfile(os.path.join(source_dir, "run.py")) else data.get("workflow", ""),
        rules=data.get("rules", "- 遵循 SKILL.md 中的说明"),
        triggers=data.get("triggers", []),
    )

    with open(os.path.join(source_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_md)


def _generate_skill_md_from_run_py(source_dir: str, run_py_path: str) -> None:
    """从 run.py 自动生成最小 SKILL.md"""
    from agents.skill_creator import generate_skill_md
    dir_name = os.path.basename(source_dir)

    with open(run_py_path, "r", encoding="utf-8") as f:
        run_content = f.read()

    # 尝试从 run.py docstring 提取描述
    import ast
    description = f"自动包装的 Python 技能（{dir_name}）"
    try:
        tree = ast.parse(run_content)
        docstring = ast.get_docstring(tree)
        if docstring:
            description = docstring.split("\n")[0][:100]
    except Exception:
        pass

    skill_md = generate_skill_md(
        name=dir_name,
        display_name=dir_name.replace("_", " ").replace("-", " "),
        description=description,
        when_to_use=f"当用户需要{description}时",
        execution_mode="code",
        allowed_tools=["skill_run"],
        arguments={},
        workflow="## 工作流程\n\n此技能通过确定性代码执行，参见 run.py。",
        rules="- run.py 必须有 run(params) 入口函数",
    )

    with open(os.path.join(source_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_md)


def _is_user_customized(target_dir: str) -> bool:
    """检查技能是否被用户定制修改（对比 content_hash）"""
    meta_file = os.path.join(target_dir, ".meta.json")
    if not os.path.isfile(meta_file):
        return False
    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return False

    recorded_hash = meta.get("content_hash")
    if not recorded_hash:
        return False

    from agents.skill_scanner import compute_content_hash
    current_hash = compute_content_hash(target_dir)
    return current_hash != recorded_hash


def install_from_zip(
    zip_path: str,
    agent_code: str = "system",
    auto_install_deps: bool = True,
) -> dict:
    """从 zip 文件安装技能"""
    if not os.path.isfile(zip_path):
        return {"ok": False, "error": f"文件不存在: {zip_path}"}

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # 查找 zip 内包含 SKILL.md 的目录
            skill_dirs = set()
            for name in zf.namelist():
                if name.endswith("SKILL.md"):
                    parts = name.rsplit("/", 1)
                    if len(parts) == 2:
                        skill_dirs.add(parts[0])
                    else:
                        skill_dirs.add(".")

            if not skill_dirs:
                return {"ok": False, "error": "zip 中未找到 SKILL.md"}

            # 解压到临时目录
            tmp_dir = tempfile.mkdtemp(prefix="zf_skill_")
            zf.extractall(tmp_dir)

            # 安装第一个找到的技能
            source = os.path.join(tmp_dir, skill_dirs.pop()) if skill_dirs else tmp_dir
            result = install_from_dir(source, agent_code, auto_install_deps)

            # 清理临时目录
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return result

    except zipfile.BadZipFile:
        return {"ok": False, "error": "无效的 zip 文件"}
    except Exception as e:
        return {"ok": False, "error": f"安装失败: {e}"}


def uninstall_skill(
    skill_code: str,
    agent_code: str = None,
    registry=None,
    db=None,
) -> dict:
    """卸载技能

    检查是否被其他技能依赖，删除文件，从 registry 移除。
    """
    from agents.skill_registry import skill_registry as _reg
    reg = registry or _reg

    skill = reg.get_skill(skill_code)
    if not skill:
        return {"ok": False, "error": f"技能未注册: {skill_code}"}

    # 检查是否有其他技能依赖它
    for other in reg.list_skills():
        if other.code == skill_code:
            continue
        dep_skills = other.dependencies.get("skills", [])
        if skill_code in dep_skills or skill.name in dep_skills:
            return {
                "ok": False,
                "error": f"技能 {other.name} 依赖 {skill_code}，请先卸载 {other.name}",
            }

    # 删除文件
    if os.path.isdir(skill.skill_dir):
        shutil.rmtree(skill.skill_dir)

    # 从 registry 移除
    if skill_code in reg._skills:
        del reg._skills[skill_code]

    # 从 DB 移除
    if db:
        try:
            from db.tables import Skill
            row = db.query(Skill).filter(Skill.skill_code == skill_code).first()
            if row:
                db.delete(row)
                db.commit()
        except Exception as e:
            logger.warning(f"DB 删除技能记录失败: {e}")

    return {
        "ok": True,
        "skill_code": skill_code,
        "message": f"技能 {skill.name or skill_code} 已卸载",
    }


def list_available_skills(agent_code: str = None) -> list[dict]:
    """列出所有已安装技能及其依赖状态"""
    from agents.skill_registry import skill_registry
    from agents.skill_deps import check_dependencies

    reg = skill_registry
    if not reg._loaded:
        reg.startup_scan(agent_code=agent_code)

    results = []
    for skill in reg.list_skills():
        dep_result = check_dependencies(skill.dependencies, registry=reg)
        results.append({
            "code": skill.code,
            "name": skill.name,
            "description": skill.description,
            "version": skill.version,
            "status": "active",
            "deps_all_met": dep_result.all_met,
            "deps_missing": [s.name for s in dep_result.missing],
            "skill_dir": skill.skill_dir,
        })
    return results
