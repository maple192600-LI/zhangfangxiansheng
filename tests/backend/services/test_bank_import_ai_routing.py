import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from database import Base
from db.tables import Agent, AIConfig
from core import ai_parse_utils
from services import bank_import_service


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _add_ai(db, provider, is_default=False):
    cfg = AIConfig(
        provider=provider,
        display_name=provider,
        api_key_local=f"{provider}-key",
        base_url=None,
        model_name=f"{provider}-model",
        is_default=is_default,
        status="active",
        created_at=datetime.now(),
    )
    db.add(cfg)
    db.flush()
    return cfg


def _add_agent(db, ai_config_id, code="parser_assistant", name="解析助手", sort_order=100):
    agent = Agent(
        agent_code=code,
        display_name=name,
        role_prompt="",
        ai_config_id=ai_config_id,
        workspace_path=f"agents/{code}",
        permission_json="{}",
        status="active",
        sort_order=sort_order,
        created_by="test",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(agent)
    db.flush()
    return agent


def test_ai_parse_headers_prefers_parser_assistant_bound_ai(monkeypatch):
    db = _session()
    default_ai = _add_ai(db, "default-ai", is_default=True)
    bound_ai = _add_ai(db, "bound-ai", is_default=False)
    _add_agent(db, bound_ai.id)
    db.commit()

    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "content": '{"mapping": {"日期": "business_date", "收入": "income_amount", "摘要": "summary_text"}, "template_name": "测试模板"}',
        }

    monkeypatch.setattr(ai_parse_utils, "chat", fake_chat)
    monkeypatch.setattr(ai_parse_utils, "decrypt_key", lambda value: value)

    result = bank_import_service.ai_parse_headers(db, ["日期", "收入", "摘要"], [["2026-04-24", "10", "收款"]])

    assert result["ok"] is True
    assert captured["provider"] == "bound-ai"
    assert captured["api_key"] == "bound-ai-key"
    assert captured["model_name"] == "bound-ai-model"
    assert captured["provider"] != default_ai.provider


def test_ai_parse_headers_uses_active_agent_bound_to_default_ai(monkeypatch):
    db = _session()
    default_ai = _add_ai(db, "default-ai", is_default=True)
    _add_agent(db, default_ai.id)
    db.commit()

    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "content": '{"mapping": {"日期": "business_date", "收入": "income_amount", "摘要": "summary_text"}, "template_name": "测试模板"}',
        }

    monkeypatch.setattr(ai_parse_utils, "chat", fake_chat)
    monkeypatch.setattr(ai_parse_utils, "decrypt_key", lambda value: value)

    result = bank_import_service.ai_parse_headers(db, ["日期", "收入", "摘要"], [])

    assert result["ok"] is True
    assert captured["provider"] == "default-ai"


def test_ai_parse_headers_extracts_json_from_wrapped_content(monkeypatch):
    db = _session()
    default_ai = _add_ai(db, "default-ai", is_default=True)
    _add_agent(db, default_ai.id)
    db.commit()

    monkeypatch.setattr(ai_parse_utils, "decrypt_key", lambda value: value)
    monkeypatch.setattr(ai_parse_utils, "chat", lambda **_kwargs: {
        "ok": True,
        "content": '可以，结果如下：{"mapping": {"日期": "business_date", "收入": "income_amount", "摘要": "summary_text"}, "template_name": "测试模板"}',
    })

    result = bank_import_service.ai_parse_headers(db, ["日期", "收入", "摘要"], [])

    assert result["ok"] is True
    assert result["mapping"]["日期"] == "business_date"


def test_ai_parse_headers_returns_error_code_for_unparseable_json(monkeypatch):
    db = _session()
    default_ai = _add_ai(db, "default-ai", is_default=True)
    _add_agent(db, default_ai.id)
    db.commit()

    monkeypatch.setattr(ai_parse_utils, "decrypt_key", lambda value: value)
    monkeypatch.setattr(ai_parse_utils, "chat", lambda **_kwargs: {
        "ok": True,
        "content": "完全不是 JSON",
    })

    result = bank_import_service.ai_parse_headers(db, ["日期", "收入", "摘要"], [])

    assert result["ok"] is False
    assert result["error_code"] == "AI_JSON_PARSE_FAILED"


def test_ai_parse_headers_masks_sample_rows_before_prompt(monkeypatch):
    db = _session()
    default_ai = _add_ai(db, "default-ai", is_default=True)
    _add_agent(db, default_ai.id)
    db.commit()

    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "content": '{"mapping": {"交易日期": "business_date", "对方账号": "counterpart_account", "收入金额": "income_amount", "摘要": "summary_text"}, "template_name": "测试模板"}',
        }

    monkeypatch.setattr(ai_parse_utils, "decrypt_key", lambda value: value)
    monkeypatch.setattr(ai_parse_utils, "chat", fake_chat)

    result = bank_import_service.ai_parse_headers(
        db,
        ["交易日期", "对方账号", "收入金额", "摘要"],
        [["2026-04-24", "6222021234567890123", "128934.55", "张三付款"]],
    )

    prompt = captured["messages"][1]["content"]
    assert result["ok"] is True
    assert "6222021234567890123" not in prompt
    assert "128934.55" not in prompt
    assert "***************0123" in prompt
    assert "约十万级" in prompt
