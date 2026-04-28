"""工作区文件系统隔离

每个 agent 有独立的工作区目录：data/agents/{agent_code}/
"""
import os
from pathlib import Path
from config import DATA_DIR

AGENTS_ROOT = os.path.join(DATA_DIR, "agents")


def get_agent_root(agent_code: str) -> str:
    """获取 agent 工作区根目录"""
    return os.path.join(AGENTS_ROOT, agent_code)


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
            "path": str(rel).replace("\\", "/"),
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


def write_file(agent_code: str, relative_path: str, content: str) -> str | None:
    """写入文件到工作区"""
    abs_path = safe_path(agent_code, relative_path)
    if abs_path:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return abs_path
    return None
