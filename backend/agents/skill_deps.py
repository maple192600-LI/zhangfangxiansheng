"""技能依赖管理器

职责：
  1. 检查 pip 包是否已安装（含版本规格）
  2. 检查系统命令是否可用
  3. 检查其他技能依赖
  4. 安装缺失的 pip 包
  5. 生成依赖状态报告

依赖声明格式（SKILL.md frontmatter）：
  dependencies:
    pip:
      - "pdfplumber>=0.10"
      - "xlrd==1.2.0"
    system:
      - "tesseract"
    skills:
      - "fund_parser_bank"
"""
import importlib
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DepStatus:
    name: str
    dep_type: str  # pip / system / skill
    installed: bool
    version: str = ""
    required_spec: str = ""
    error: str = ""


@dataclass
class DepCheckResult:
    all_met: bool
    statuses: list[DepStatus] = field(default_factory=list)

    @property
    def missing(self) -> list[DepStatus]:
        return [s for s in self.statuses if not s.installed]

    @property
    def summary(self) -> str:
        if self.all_met:
            return f"依赖检查通过（{len(self.statuses)} 项）"
        missing_names = [s.name for s in self.missing]
        return f"缺少 {len(self.missing)} 项依赖: {', '.join(missing_names)}"


def check_pip_package(spec: str) -> DepStatus:
    """检查单个 pip 包是否满足版本规格

    spec 格式示例: "pdfplumber", "xlrd==1.2.0", "openpyxl>=3.0"
    """
    match = re.match(r'^([a-zA-Z0-9_-]+)\s*(.*)', spec.strip())
    if not match:
        return DepStatus(name=spec, dep_type="pip", installed=False, error="无法解析包名")

    pkg_name = match.group(1).replace("-", "_")
    version_spec = match.group(2).strip()

    try:
        mod = importlib.import_module(pkg_name)
        installed_ver = getattr(mod, "__version__", "unknown")
        met = _version_satisfies(installed_ver, version_spec)
        return DepStatus(
            name=pkg_name,
            dep_type="pip",
            installed=met,
            version=installed_ver,
            required_spec=version_spec,
        )
    except ImportError:
        return DepStatus(name=pkg_name, dep_type="pip", installed=False, required_spec=version_spec)


def check_system_command(cmd: str) -> DepStatus:
    """检查系统命令是否可用"""
    import shutil
    found = shutil.which(cmd) is not None
    return DepStatus(name=cmd, dep_type="system", installed=found)


def check_skill_dep(skill_name: str, registry=None) -> DepStatus:
    """检查技能依赖是否已注册"""
    if registry is not None:
        meta = registry.get_skill(skill_name.replace("-", "_"))
        if meta:
            return DepStatus(name=skill_name, dep_type="skill", installed=True)
    # fallback: 检查文件系统
    from config import AGENTS_ROOT
    import os
    for base in ["system", ""]:
        check_dir = os.path.join(AGENTS_ROOT, base, "skills", skill_name) if base else os.path.join(AGENTS_ROOT, "skills", skill_name)
        if os.path.isdir(check_dir) and os.path.isfile(os.path.join(check_dir, "SKILL.md")):
            return DepStatus(name=skill_name, dep_type="skill", installed=True)
    return DepStatus(name=skill_name, dep_type="skill", installed=False)


def check_dependencies(dependencies: dict, registry=None) -> DepCheckResult:
    """检查所有依赖

    dependencies 格式: {"pip": [...], "system": [...], "skills": [...]}
    """
    statuses: list[DepStatus] = []

    for spec in dependencies.get("pip", []):
        statuses.append(check_pip_package(spec))

    for cmd in dependencies.get("system", []):
        statuses.append(check_system_command(cmd))

    for skill_name in dependencies.get("skills", []):
        statuses.append(check_skill_dep(skill_name, registry))

    return DepCheckResult(
        all_met=all(s.installed for s in statuses),
        statuses=statuses,
    )


def install_pip_packages(specs: list[str]) -> dict:
    """安装 pip 包列表，返回安装结果"""
    results = []
    for spec in specs:
        match = re.match(r'^([a-zA-Z0-9_-]+)', spec.strip())
        pkg_name = match.group(1) if match else spec

        try:
            cmd = [sys.executable, "-m", "pip", "install", spec, "--quiet"]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode == 0:
                results.append({"package": pkg_name, "installed": True})
                logger.info(f"pip install {spec} 成功")
            else:
                results.append({"package": pkg_name, "installed": False, "error": proc.stderr[:200]})
                logger.warning(f"pip install {spec} 失败: {proc.stderr[:200]}")
        except subprocess.TimeoutExpired:
            results.append({"package": pkg_name, "installed": False, "error": "安装超时（120s）"})
        except Exception as e:
            results.append({"package": pkg_name, "installed": False, "error": str(e)})

    return {"results": results, "all_ok": all(r["installed"] for r in results)}


def install_dependencies(dependencies: dict) -> dict:
    """安装所有可自动安装的依赖（目前仅 pip）"""
    pip_specs = dependencies.get("pip", [])
    if not pip_specs:
        return {"ok": True, "message": "无需安装", "results": []}

    result = install_pip_packages(pip_specs)

    system_missing = []
    for cmd in dependencies.get("system", []):
        if not check_system_command(cmd).installed:
            system_missing.append(cmd)

    parts = []
    if result["all_ok"]:
        parts.append(f"pip 依赖安装完成（{len(pip_specs)} 个包）")
    else:
        failed = [r["package"] for r in result["results"] if not r["installed"]]
        parts.append(f"部分 pip 安装失败: {', '.join(failed)}")

    if system_missing:
        parts.append(f"系统依赖需手动安装: {', '.join(system_missing)}")

    return {
        "ok": result["all_ok"] and not system_missing,
        "message": "; ".join(parts),
        "results": result["results"],
        "system_missing": system_missing,
    }


def _version_satisfies(installed: str, spec: str) -> bool:
    """检查安装版本是否满足版本规格

    支持: ==X.Y.Z, >=X.Y.Z, >X.Y.Z, <=X.Y.Z, <X.Y.Z, ~=X.Y.Z
    空规格视为满足
    """
    if not spec or installed == "unknown":
        return True

    from packaging.version import Version, InvalidVersion
    try:
        v = Version(installed)
    except InvalidVersion:
        return True

    for op, cmp_fn in [
        ("==", lambda a, b: a == b),
        (">=", lambda a, b: a >= b),
        ("<=", lambda a, b: a <= b),
        (">", lambda a, b: a > b),
        ("<", lambda a, b: a < b),
        ("~=", lambda a, b: a >= b),
    ]:
        if spec.startswith(op):
            try:
                target = Version(spec[len(op):].strip())
                return cmp_fn(v, target)
            except InvalidVersion:
                return True

    return True
