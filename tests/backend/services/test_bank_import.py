import json
from datetime import datetime

import pytest

from helpers import make_xlsx
from core import ai_parse_utils
from db.tables import Agent, AIConfig, FundEvent, ParserTemplate
from services import bank_import_service


def _add_template(db, account_code="A001"):
    template = ParserTemplate(
        template_name="Bank Template",
        template_type="bank",
        file_format="xlsx",
        header_row=0,
        skip_rows=0,
        sample_headers=json.dumps(["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"]),
        mapping_json=json.dumps({
            "Date": "business_date",
            "Summary": "summary_text",
            "Income": "income_amount",
            "Expense": "expense_amount",
        }),
        account_code=account_code,
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


def _add_agent(db, ai_config_id):
    agent = Agent(
        agent_code="parser_assistant",
        display_name="Parser Assistant",
        role_prompt="",
        workspace_path="agents/parser-assistant",
        ai_config_id=ai_config_id,
        permission_json="{}",
        status="active",
        sort_order=100,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(agent)
    db.flush()
    return agent


def test_commit_creates_fund_events(db_session, chart_of_accounts, tmp_path, monkeypatch):
    account = chart_of_accounts["account"]
    template = _add_template(db_session, account.account_code)
    file_data = make_xlsx([
        ["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"],
        ["2026-04-24", "", "", "bank receipt", "120.50", ""],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    upload = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")
    bank_import_service.preview(db_session, upload["batch_code"], template_id=template.id)
    result = bank_import_service.commit_by_mapping(db_session, upload["batch_code"], template_id=template.id)
    event = db_session.query(FundEvent).filter(FundEvent.batch_id == upload["batch_id"]).one()

    assert result["inserted_rows"] == 1
    assert event.state == "正常"
    assert float(event.amount_in) == 120.50
    assert float(event.amount_out) == 0


def test_commit_invalid_batch_raises(db_session):
    with pytest.raises(ValueError):
        bank_import_service.commit_by_mapping(db_session, "MISSING_BATCH", account_code="A001", mapping={})


def test_ai_parse_respects_agent_binding(db_session, monkeypatch):
    default_ai = _add_ai(db_session, "default-provider", is_default=True)
    bound_ai = _add_ai(db_session, "bound-provider")
    _add_agent(db_session, bound_ai.id)
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

    monkeypatch.setattr(ai_parse_utils, "chat", fake_chat)
    monkeypatch.setattr(ai_parse_utils, "decrypt_key", lambda value: value)

    result = bank_import_service.ai_parse_headers(
        db_session,
        ["Date", "Income", "Summary"],
        [["2026-04-24", "300.00", "receipt"]],
    )

    assert result["ok"] is True
    assert captured["provider"] == bound_ai.provider
    assert captured["provider"] != default_ai.provider
    assert captured["api_key"] == "bound-provider-key"
