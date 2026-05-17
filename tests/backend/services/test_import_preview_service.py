from datetime import date, datetime
from unittest.mock import patch

from conftest import add_import_batch, make_xlsx
from db.tables import FundEvent
from services import import_preview_service, manual_flow_service


def _make_event(db, batch, entity_code=None, entity_name="", account_code=None, account_name=""):
    ev = FundEvent(
        batch_id=batch.id,
        business_date=date(2026, 4, 24),
        entity_code=entity_code,
        entity_name=entity_name,
        account_code=account_code,
        account_name=account_name,
        summary="test",
        counterparty="",
        amount_in=10,
        amount_out=0,
        state="待确认",
        source="手工录入",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(ev)
    db.commit()
    return ev


def test_get_preview_manual_excel_returns_unified_schema(db_session, chart_of_accounts, tmp_path, monkeypatch):
    chart_of_accounts["entity"]
    chart_of_accounts["account"]

    batch = add_import_batch(db_session, batch_code="M-EXCEL-001", source_type="manual_excel", source_name="manual.xlsx")

    monkeypatch.setattr(manual_flow_service, "DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    file_data = make_xlsx([
        ["日期", "摘要", "收入", "支出"],
        ["2026-04-24", "test row", "100.00", ""],
    ])
    (upload_dir / f"{batch.batch_code}_manual.xlsx").write_bytes(file_data)

    with patch.object(manual_flow_service, "_build_column_mapping", return_value={
        "日期": "business_date", "摘要": "summary_text", "收入": "income_amount", "支出": "expense_amount",
    }):
        result = import_preview_service.get_preview(db_session, batch.batch_code)

    assert result["total_count"] >= 1
    all_rows = result["parsed_rows"] + result["abnormal_rows"]
    assert len(all_rows) >= 1

    row = all_rows[0]
    assert "entity_code" in row
    assert "entity_name" in row
    assert "account_code" in row
    assert "account_name" in row
    assert "entity_match_key" not in row
    assert "_entity_name" not in row
    assert "_entity_id" not in row


def test_update_row_entity_short_name_saves_canonical_code(db_session, chart_of_accounts):
    entity = chart_of_accounts["entity"]

    batch = add_import_batch(db_session, batch_code="M-EDIT-001", source_type="manual_quick")
    _make_event(db_session, batch, entity_code=None, entity_name="placeholder")

    short_name = entity.short_name
    import_preview_service.update_row(db_session, batch.batch_code, 1, {"entity_code": short_name})

    ev = db_session.query(FundEvent).one()
    assert ev.entity_code == entity.entity_code
    assert ev.entity_name == entity.short_name


def test_update_row_account_alias_saves_canonical_code(db_session, chart_of_accounts):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]

    batch = add_import_batch(db_session, batch_code="M-EDIT-002", source_type="manual_quick")
    _make_event(db_session, batch, entity_code=entity.entity_code, entity_name=entity.short_name,
                account_code=None, account_name="placeholder")

    alias = account.account_alias
    import_preview_service.update_row(db_session, batch.batch_code, 1, {"account_code": alias})

    ev = db_session.query(FundEvent).one()
    assert ev.account_code == account.account_code
    assert ev.account_name == account.account_alias


def test_update_row_unmatched_saves_none_and_preserves_input(db_session, chart_of_accounts):
    batch = add_import_batch(db_session, batch_code="M-EDIT-003", source_type="manual_quick")
    _make_event(db_session, batch, entity_code=None, entity_name="")

    result = import_preview_service.update_row(db_session, batch.batch_code, 1, {"entity_code": "NO_SUCH_ENTITY"})

    ev = db_session.query(FundEvent).one()
    assert ev.entity_code is None
    assert ev.entity_name == "NO_SUCH_ENTITY"
    assert result["row"]["_errors"]
