import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from services import agent_init


def test_init_agent_workspaces_marks_v1_reserved_files(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_init, "AGENTS_DIR", str(tmp_path / "agents"))

    agent_init.init_agent_workspaces()

    for rel in (
        "master/AGENT.md",
        "master/TOOLS.md",
        "parser-assistant/AGENT.md",
        "parser-assistant/TOOLS.md",
    ):
        content = (tmp_path / "agents" / rel).read_text(encoding="utf-8")
        assert content.startswith("# [V1 预留骨架 · V2 启用]")
        assert "当前 V1 阶段仅展示 Agent 目录结构" in content
