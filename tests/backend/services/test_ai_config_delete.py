import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from database import Base
from db.tables import Agent, AIConfig
from services import ai_config_service


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _ai(db, provider, is_default=False):
    cfg = AIConfig(
        provider=provider,
        display_name=provider,
        api_key_local="key",
        model_name="model",
        is_default=is_default,
        status="active",
        created_at=datetime.now(),
    )
    db.add(cfg)
    db.flush()
    return cfg


def _agent(db, ai_config_id=None):
    agent = Agent(
        agent_code="parser_assistant",
        display_name="解析助手",
        role_prompt="",
        workspace_path="agents/parser-assistant",
        ai_config_id=ai_config_id,
        permission_json="{}",
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(agent)
    db.flush()
    return agent


def test_delete_ai_config_removes_unreferenced_non_default_config():
    db = _session()
    cfg = _ai(db, "zhipu")
    db.commit()

    result = ai_config_service.delete_ai_config(db, cfg.id)

    assert result == {"deleted_id": cfg.id}
    assert db.query(AIConfig).filter(AIConfig.id == cfg.id).first() is None


def test_delete_ai_config_rejects_default_config():
    db = _session()
    cfg = _ai(db, "zhipu", is_default=True)
    db.commit()

    with pytest.raises(ValueError, match="默认"):
        ai_config_service.delete_ai_config(db, cfg.id)


def test_delete_ai_config_rejects_agent_reference():
    db = _session()
    cfg = _ai(db, "zhipu")
    _agent(db, cfg.id)
    db.commit()

    with pytest.raises(ai_config_service.AIConfigInUseError) as exc:
        ai_config_service.delete_ai_config(db, cfg.id)

    assert exc.value.references == ["解析助手"]
    assert db.query(AIConfig).filter(AIConfig.id == cfg.id).first() is not None


def test_delete_ai_config_ignores_deleted_agent_reference():
    db = _session()
    cfg = _ai(db, "zhipu")
    agent = _agent(db, cfg.id)
    agent.status = "deleted"
    db.commit()

    result = ai_config_service.delete_ai_config(db, cfg.id)

    assert result == {"deleted_id": cfg.id}
    assert db.query(AIConfig).filter(AIConfig.id == cfg.id).first() is None
