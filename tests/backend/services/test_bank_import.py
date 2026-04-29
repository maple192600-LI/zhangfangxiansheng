import json
from datetime import datetime

import pytest

from conftest import make_xlsx
from db.tables import AgentConfig, AIConfig, FundEvent, ParserTemplate
from services import bank_import_service


def _add_template(db):
    template = ParserTemplate(
        template_name="Bank Template",
        template_type="bank",
        file_format="xlsx",
        header_row=0,
        skip_rows=0,
        sample_headers=json.dumps(["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"]),
        mapping_json=json.dumps({
            "Date": "business_date",
            "EntityId": "_entity_id",
            "AccountId": "_account_id",
            "Summary": "summary_text",
            "Income": "income_amount",
            "Expense": "expense_amount",
        }),
        created_by="test",
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


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


def test_commit_creates_fund_events(db_session, chart_of_accounts, tmp_path, monkeypatch):
    template = _add_template(db_session)
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    file_data = make_xlsx([
        ["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"],
        ["2026-04-24", str(entity.id), str(account.id), "bank receipt", "120.50", ""],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    upload = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")
    preview = bank_import_service.preview(db_session, upload["batch_code"], template_id=template.id)
    result = bank_import_service.commit(db_session, upload["batch_code"], preview["parsed_rows"])
    event = db_session.query(FundEvent).filter(FundEvent.batch_id == upload["batch_id"]).one()

    assert result["committed_count"] == 1
    assert result["abnormal_count"] == 0
    assert event.parse_status == "valid"
    assert event.direction == "income"
    assert float(event.income_amount) == 120.50


def test_commit_invalid_batch_raises(db_session):
    with pytest.raises(ValueError):
        bank_import_service.commit(db_session, "MISSING_BATCH", [])


def test_ai_parse_respects_agent_binding(db_session, monkeypatch):
    default_ai = _add_ai(db_session, "default-provider", is_default=True)
    bound_ai = _add_ai(db_session, "bound-provider")
    db_session.add(AgentConfig(
        agent_code="parser_assistant",
        agent_name="Parser Assistant",
        agent_type="parser",
        workspace_dir="agents/parser-assistant",
        ai_config_id=bound_ai.id,
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    ))
    db_session.commit()
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "content": json.dumps({
                "mapping": {"Date": "business_date", "Income": "income_amount", "Summary": "summary_text"},
                "template_name": "AI Template",
            }),
        }

    monkeypatch.setattr(bank_import_service, "chat", fake_chat)
    monkeypatch.setattr(bank_import_service, "decrypt_key", lambda value: value)

    result = bank_import_service.ai_parse_headers(
        db_session,
        ["Date", "Income", "Summary"],
        [["2026-04-24", "300.00", "receipt"]],
    )

    assert result["ok"] is True
    assert captured["provider"] == bound_ai.provider
    assert captured["provider"] != default_ai.provider
    assert captured["api_key"] == "bound-provider-key"
