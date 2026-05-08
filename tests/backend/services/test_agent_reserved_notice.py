import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from services import agent_init


def test_init_agent_workspaces_only_creates_workspace_root(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_init, "AGENTS_DIR", str(tmp_path / "agents"))

    agent_init.init_agent_workspaces()

    agents_dir = tmp_path / "agents"
    assert agents_dir.is_dir()
    assert list(agents_dir.iterdir()) == []
