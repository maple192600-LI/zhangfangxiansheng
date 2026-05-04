"""Agent 工作空间目录读取

GET /api/agent-workspaces — 读取 agents/ 目录下实际的 agent 工作空间
"""
import os

from fastapi import APIRouter

from config import BASE_DIR
from core.response import success

router = APIRouter()

AGENTS_DIR = os.path.join(BASE_DIR, "agents")


@router.get("/agent-workspaces")
def get_agent_workspaces():
    """读取 agents/ 目录下每个 agent 子目录的文件列表和文件数量"""
    if not os.path.isdir(AGENTS_DIR):
        return success([])

    result = []
    for name in sorted(os.listdir(AGENTS_DIR)):
        agent_path = os.path.join(AGENTS_DIR, name)
        if not os.path.isdir(agent_path):
            continue
        files = []
        for root, dirs, filenames in os.walk(agent_path):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fn in filenames:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, agent_path).replace("\\", "/")
                files.append(rel)
        result.append({
            "dir_name": name,
            "file_count": len(files),
            "files": sorted(files),
        })
    return success(result)
