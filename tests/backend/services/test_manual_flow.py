from db.tables import FundEvent, ImportBatch
from services import manual_flow_service


def test_quick_entry_save_creates_valid_manual_event(db_session, chart_of_accounts):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    result = manual_flow_service.quick_entry_save(db_session, [{
        "entity_match_key": entity.entity_code,
        "account_match_key": account.account_code,
        "business_date": "2026-04-24",
        "summary_text": "manual receipt",
        "counterparty_name": "Customer A",
        "income_amount": "88.00",
        "expense_amount": "",
    }])
    event = db_session.query(FundEvent).one()

    assert result["inserted_rows"] == 1
    assert event.source == "手工录入"
    assert event.state == "正常"
    assert event.entity_code == entity.entity_code
    assert event.account_code == account.account_code
    assert event.amount_in == 88.0
    assert event.amount_out == 0


def test_quick_entry_save_keeps_unmatched_rows_pending(db_session, chart_of_accounts):
    account = chart_of_accounts["account"]
    result = manual_flow_service.quick_entry_save(db_session, [{
        "entity_match_key": "UNKNOWN",
        "account_match_key": account.account_code,
        "business_date": "2026-04-24",
        "summary_text": "manual receipt",
        "income_amount": "88.00",
        "expense_amount": "",
    }])
    event = db_session.query(FundEvent).one()

    assert result["inserted_rows"] == 1
    assert event.state == "待确认"
    assert event.entity_code == "UNKNOWN"


def test_commit_manual_with_parser_artifact(db_session, chart_of_accounts, tmp_path, monkeypatch):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    from datetime import date
    from unittest.mock import patch

    from db.tables import ParserArtifact
    from datetime import datetime

    artifact = ParserArtifact(
        name="Test Manual Parser",
        kind="manual",
        account_code=None,
        version=1,
        status="active",
        code="def parse(ws): return []",
        primitives_imports=[],
        sample_check_log={},
        confidence=0.9,
        created_by="test",
        created_at=datetime.now(),
    )
    db_session.add(artifact)
    db_session.commit()
    db_session.refresh(artifact)

    monkeypatch.setattr(manual_flow_service, "DATA_DIR", str(tmp_path))

    from conftest import make_xlsx
    file_data = make_xlsx([
        ["日期", "摘要", "收入", "支出"],
        ["2026-04-24", "test", "20.00", ""],
    ])
    uploaded = manual_flow_service.upload_workbook(
        db_session, file_data, "manual.xlsx", "manual_multi_subject_basic",
    )

    canonical_rows = [
        {
            "business_date": date(2026, 4, 24),
            "entity_code": entity.entity_code,
            "entity_name": entity.short_name,
            "account_code": account.account_code,
            "account_name": account.account_alias,
            "summary": "test",
            "counterparty": "",
            "amount_in": 20,
            "amount_out": 0,
            "rolling_balance": None,
            "state": "正常",
            "source": "手工录入",
        },
    ]

    with patch.object(manual_flow_service.artifact_runtime, "run_parser", return_value=iter(canonical_rows)):
        result = manual_flow_service.commit_manual(
            db_session, uploaded["batch_code"], parser_artifact_id=artifact.id,
        )

    batch = db_session.query(ImportBatch).filter(
        ImportBatch.batch_code == uploaded["batch_code"],
    ).one()

    assert result["inserted_rows"] == 1
    assert batch.status == "committed"
