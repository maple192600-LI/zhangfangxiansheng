import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from database import Base
from db.tables import AgentConfig, AIConfig
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


def test_ai_parse_headers_prefers_parser_assistant_bound_ai(monkeypatch):
    db = _session()
    default_ai = _add_ai(db, "default-ai", is_default=True)
    bound_ai = _add_ai(db, "bound-ai", is_default=False)
    db.add(AgentConfig(
        agent_code="parser_assistant",
        agent_name="解析助手",
        agent_type="parser",
        workspace_dir="agents/parser-assistant",
        ai_config_id=bound_ai.id,
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    ))
    db.commit()

    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "content": '{"mapping": {"日期": "business_date", "收入": "income_amount", "摘要": "summary_text"}, "template_name": "测试模板"}',
        }

    monkeypatch.setattr(bank_import_service, "chat", fake_chat)
    monkeypatch.setattr(bank_import_service, "decrypt_key", lambda value: value)

    result = bank_import_service.ai_parse_headers(db, ["日期", "收入", "摘要"], [["2026-04-24", "10", "收款"]])

    assert result["ok"] is True
    assert captured["provider"] == "bound-ai"
    assert captured["api_key"] == "bound-ai-key"
    assert captured["model_name"] == "bound-ai-model"
    assert captured["provider"] != default_ai.provider


def test_ai_parse_headers_falls_back_to_default_ai_without_binding(monkeypatch):
    db = _session()
    _add_ai(db, "default-ai", is_default=True)
    db.commit()

    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "content": '{"mapping": {"日期": "business_date", "收入": "income_amount", "摘要": "summary_text"}, "template_name": "测试模板"}',
        }

    monkeypatch.setattr(bank_import_service, "chat", fake_chat)
    monkeypatch.setattr(bank_import_service, "decrypt_key", lambda value: value)

    result = bank_import_service.ai_parse_headers(db, ["日期", "收入", "摘要"], [])

    assert result["ok"] is True
    assert captured["provider"] == "default-ai"


def test_ai_parse_headers_extracts_json_from_wrapped_content(monkeypatch):
    db = _session()
    _add_ai(db, "default-ai", is_default=True)
    db.commit()

    monkeypatch.setattr(bank_import_service, "decrypt_key", lambda value: value)
    monkeypatch.setattr(bank_import_service, "chat", lambda **_kwargs: {
        "ok": True,
        "content": '可以，结果如下：{"mapping": {"日期": "business_date", "收入": "income_amount", "摘要": "summary_text"}, "template_name": "测试模板"}',
    })

    result = bank_import_service.ai_parse_headers(db, ["日期", "收入", "摘要"], [])

    assert result["ok"] is True
    assert result["mapping"]["日期"] == "business_date"


def test_ai_parse_headers_returns_error_code_for_unparseable_json(monkeypatch):
    db = _session()
    _add_ai(db, "default-ai", is_default=True)
    db.commit()

    monkeypatch.setattr(bank_import_service, "decrypt_key", lambda value: value)
    monkeypatch.setattr(bank_import_service, "chat", lambda **_kwargs: {
        "ok": True,
        "content": "完全不是 JSON",
    })

    result = bank_import_service.ai_parse_headers(db, ["日期", "收入", "摘要"], [])

    assert result["ok"] is False
    assert result["error_code"] == "AI_JSON_PARSE_FAILED"


def test_ai_parse_headers_masks_sample_rows_before_prompt(monkeypatch):
    db = _session()
    _add_ai(db, "default-ai", is_default=True)
    db.commit()

    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "content": '{"mapping": {"交易日期": "business_date", "对方账号": "counterpart_account", "收入金额": "income_amount", "摘要": "summary_text"}, "template_name": "测试模板"}',
        }

    monkeypatch.setattr(bank_import_service, "decrypt_key", lambda value: value)
    monkeypatch.setattr(bank_import_service, "chat", fake_chat)

    result = bank_import_service.ai_parse_headers(
        db,
        ["交易日期", "对方账号", "收入金额", "摘要"],
        [["2026-04-24", "6222021234567890123", "128934.55", "张三付款"]],
    )

    prompt = captured["messages"][0]["content"]
    assert result["ok"] is True
    assert "6222021234567890123" not in prompt
    assert "128934.55" not in prompt
    assert "***************0123" in prompt
    assert "约十万级" in prompt
