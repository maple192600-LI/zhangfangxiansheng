"""工作区文件系统隔离

每个 agent 有独立的工作区目录：agents/{agent_code}/
AGENTS_ROOT 在项目根级别（非 backend/data/agents/）。
"""
import os
import tempfile
from pathlib import Path

from config import AGENTS_ROOT


def get_agent_root(agent_code: str) -> str:
    """获取 agent 工作区根目录"""
    return os.path.join(AGENTS_ROOT, agent_code)


def get_skills_dir(agent_code: str | None = None) -> str:
    """获取技能目录"""
    if agent_code:
        return os.path.join(get_agent_root(agent_code), "skills")
    return os.path.join(AGENTS_ROOT, "system", "skills")


def init_workspace(agent_code: str) -> str:
    """初始化 agent 工作区目录结构"""
    root = get_agent_root(agent_code)
    dirs = [
        os.path.join(root, "workspace", "inbox"),
        os.path.join(root, "workspace", "outputs"),
        os.path.join(root, "workspace", "tmp"),
        os.path.join(root, "skills"),
        os.path.join(root, "memory"),
        os.path.join(root, "sessions"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    return root


def safe_path(agent_code: str, relative_path: str) -> str | None:
    """安全解析路径，确保在 agent 工作区内

    返回绝对路径，若路径越界返回 None
    """
    root = Path(get_agent_root(agent_code)).resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
        return str(target)
    except ValueError:
        return None


def list_files(agent_code: str, sub_dir: str = "workspace") -> list[dict]:
    """列出工作区内指定子目录的文件树"""
    root = Path(get_agent_root(agent_code)) / sub_dir
    if not root.exists():
        return []
    result = []
    for entry in sorted(root.rglob("*")):
        rel = entry.relative_to(root)
        result.append({
            "name": entry.name,
            "path": f"{sub_dir}/{rel}".replace("\\", "/"),
            "is_dir": entry.is_dir(),
            "size": entry.stat().st_size if entry.is_file() else 0,
        })
    return result


def read_file(agent_code: str, relative_path: str) -> str | None:
    """读取工作区内文件内容"""
    abs_path = safe_path(agent_code, relative_path)
    if abs_path and os.path.isfile(abs_path):
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return None


def atomic_write(agent_code: str, relative_path: str, content: str) -> dict:
    """原子写入文件到工作区"""
    abs_path = safe_path(agent_code, relative_path)
    if abs_path is None:
        return {"ok": False, "error": f"路径越界: {relative_path}"}
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(abs_path), prefix=".tmp_", suffix=".atom")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, abs_path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return {"ok": True, "path": abs_path}


def write_file(agent_code: str, relative_path: str, content: str) -> str | None:
    """写入文件到工作区"""
    abs_path = safe_path(agent_code, relative_path)
    if abs_path:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return abs_path
    return None
