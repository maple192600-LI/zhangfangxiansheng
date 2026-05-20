import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from services import agent_init


def test_init_agent_workspaces_creates_runtime_root(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_init, "AGENTS_DIR", str(tmp_path / "agents"))

    result = agent_init.init_agent_workspaces()

    assert result is True
    assert (tmp_path / "agents").is_dir()
    assert list((tmp_path / "agents").iterdir()) == []
