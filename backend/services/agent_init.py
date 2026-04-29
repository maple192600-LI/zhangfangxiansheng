"""Agent workspace bootstrap — V2 only."""
import os

from config import BASE_DIR

AGENTS_DIR = os.path.join(BASE_DIR, "agents")


def init_agent_workspaces():
    """确保 agents 目录存在，供 agent-workspaces API 读取。"""
    os.makedirs(AGENTS_DIR, exist_ok=True)
    return True
