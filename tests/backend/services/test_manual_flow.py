from db.tables import FundEvent, ImportBatch
from services import manual_flow_service


def test_quick_entry_save_creates_valid_manual_event(db_session, chart_of_accounts):
    result = manual_flow_service.quick_entry_save(db_session, [{
        "entity_match_key": "E001",
        "account_match_key": "A001",
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
    assert event.entity_code == chart_of_accounts["entity"].entity_code
    assert event.account_code == chart_of_accounts["account"].account_code


def test_quick_entry_save_keeps_unmatched_rows_abnormal(db_session, chart_of_accounts):
    result = manual_flow_service.quick_entry_save(db_session, [{
        "entity_match_key": "UNKNOWN",
        "account_match_key": "A001",
        "business_date": "2026-04-24",
        "summary_text": "manual receipt",
        "income_amount": "88.00",
        "expense_amount": "",
    }])
    event = db_session.query(FundEvent).one()

    assert result["inserted_rows"] == 1
    assert event.state == "待确认"
    assert event.entity_code == "UNKNOWN"


def test_preview_manual_confirms_quick_entry_batch(db_session, chart_of_accounts):
    saved = manual_flow_service.quick_entry_save(db_session, [{
        "entity_match_key": "E001",
        "account_match_key": "A001",
        "business_date": "2026-04-24",
        "summary_text": "manual expense",
        "counterparty_name": "Supplier A",
        "income_amount": "",
        "expense_amount": "20.00",
    }])

    result = manual_flow_service.preview_manual(db_session, saved["batch_code"])
    batch = db_session.query(ImportBatch).filter(ImportBatch.batch_code == saved["batch_code"]).one()

    assert result["valid_count"] == 1
    assert result["abnormal_count"] == 0
    assert batch.status == "previewed"
