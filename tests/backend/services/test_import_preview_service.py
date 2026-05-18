from datetime import date, datetime
from unittest.mock import patch, MagicMock

from conftest import add_import_batch, make_xlsx
from db.tables import FundEvent, ParserArtifact, SourceFile
from services import import_preview_service, manual_flow_service
from services import bank_import_service as bank_svc
from services.source_file_service import create_source_file_for_upload, update_source_file_status


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


def _add_parser_artifact(db, name="Test Parser", bank_id=None, format_key=None):
    artifact = ParserArtifact(
        name=name,
        kind="bank",
        account_code=None,
        bank_id=bank_id,
        format_key=format_key,
        match_rules={},
        version=1,
        status="active",
        code="def parse(wb, ctx): return []",
        primitives_imports=[],
        sample_check_log={},
        confidence=0.9,
        created_by="test",
        created_at=datetime.now(),
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


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


# ── bank preview tests ──


def test_bank_preview_uses_build_context_not_old_match(db_session, chart_of_accounts, tmp_path, monkeypatch):
    """_build_bank_preview 不再引用 _match_active_parser_artifact"""
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]

    batch = add_import_batch(db_session, batch_code="BANK-PV-001", source_type="bank", source_name="bank.xlsx")

    monkeypatch.setattr(bank_svc, "DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    file_data = make_xlsx([
        ["Date", "Summary", "Income"],
        ["2026-04-24", "test", "100"],
    ])
    (upload_dir / f"{batch.batch_code}_bank.xlsx").write_bytes(file_data)

    # Ensure old function doesn't exist — _build_bank_preview should still work
    assert not hasattr(bank_svc, "_match_active_parser_artifact")

    # No parser → unavailable, but should not crash
    result = import_preview_service.get_preview(db_session, batch.batch_code)
    assert result["parser_status"] == "unavailable"
    assert "bank_resolution" in result


def test_bank_preview_with_parser_creates_fund_events(db_session, chart_of_accounts, tmp_path, monkeypatch):
    """bank 批次 parser matched 时写入 FundEvent 并返回预览"""
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    artifact = _add_parser_artifact(db_session)

    batch = add_import_batch(db_session, batch_code="BANK-PV-002", source_type="bank", source_name="bank.xlsx")

    monkeypatch.setattr(bank_svc, "DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    file_data = make_xlsx([
        ["Date", "Summary", "Income"],
        ["2026-04-24", "test", "100"],
    ])
    (upload_dir / f"{batch.batch_code}_bank.xlsx").write_bytes(file_data)

    canonical_rows = [{
        "business_date": date(2026, 4, 24),
        "entity_code": entity.entity_code,
        "entity_name": entity.short_name,
        "account_code": account.account_code,
        "account_name": account.account_alias,
        "summary": "test row",
        "counterparty": "",
        "amount_in": 100.0,
        "amount_out": 0,
        "rolling_balance": None,
        "state": "正常",
        "source": "网银导入",
    }]

    with patch.object(bank_svc.artifact_runtime, "run_parser", return_value=iter(canonical_rows)):
        result = import_preview_service.get_preview(db_session, batch.batch_code)

    assert result["total_count"] == 1
    events = db_session.query(FundEvent).filter(FundEvent.batch_id == batch.id).all()
    assert len(events) == 1
    assert events[0].parser_artifact_id == artifact.id


def test_bank_preview_no_parser_returns_context(db_session, chart_of_accounts, tmp_path, monkeypatch):
    """parser_match none/conflict 时返回 parser_status=unavailable 且带 context"""
    batch = add_import_batch(db_session, batch_code="BANK-PV-003", source_type="bank", source_name="bank.xlsx")

    monkeypatch.setattr(bank_svc, "DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    file_data = make_xlsx([
        ["Date", "Summary", "Income"],
        ["2026-04-24", "test", "100"],
    ])
    (upload_dir / f"{batch.batch_code}_bank.xlsx").write_bytes(file_data)

    result = import_preview_service.get_preview(db_session, batch.batch_code)
    assert result["parser_status"] == "unavailable"
    assert "bank_resolution" in result
    assert "account_attribution" in result
    assert "parser_match" in result
    assert result["parser_match"]["matched"] is False


def test_bank_commit_does_not_call_bank_svc_commit(db_session, chart_of_accounts):
    """bank 批次 commit 不调用 bank_svc.commit()"""
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]

    batch = add_import_batch(db_session, batch_code="BANK-CM-001", source_type="bank", status="previewed")
    ev = FundEvent(
        batch_id=batch.id,
        business_date=date(2026, 4, 24),
        entity_code=entity.entity_code,
        entity_name=entity.short_name,
        account_code=account.account_code,
        account_name=account.account_alias,
        summary="test",
        counterparty="",
        amount_in=100,
        amount_out=0,
        state="待确认",
        source="网银导入",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(ev)
    db_session.commit()

    # bank_svc.commit should not exist or be callable for this path
    with patch.object(bank_svc, "commit", side_effect=AssertionError("should not call bank_svc.commit")):
        result = import_preview_service.commit(db_session, batch.batch_code)

    assert result["committed_count"] == 1
    ev_after = db_session.query(FundEvent).one()
    assert ev_after.state == "正常"
    assert ev_after.entity_code == entity.entity_code


def test_bank_commit_rejects_abnormal_rows(db_session, chart_of_accounts):
    """bank 批次 commit 拒绝异常行"""
    entity = chart_of_accounts["entity"]

    batch = add_import_batch(db_session, batch_code="BANK-CM-002", source_type="bank", status="previewed")
    ev = FundEvent(
        batch_id=batch.id,
        business_date=date(2026, 4, 24),
        entity_code=entity.entity_code,
        entity_name=entity.short_name,
        account_code=None,  # missing → abnormal
        account_name="",
        summary="test",
        counterparty="",
        amount_in=100,
        amount_out=0,
        state="待确认",
        source="网银导入",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(ev)
    db_session.commit()

    try:
        import_preview_service.commit(db_session, batch.batch_code)
        assert False, "should have raised"
    except ValueError as e:
        assert "异常行" in str(e)


def test_bank_commit_preserves_user_edits(db_session, chart_of_accounts):
    """bank 批次 commit 保留用户编辑后的数据"""
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]

    batch = add_import_batch(db_session, batch_code="BANK-CM-003", source_type="bank", status="previewed")
    ev = FundEvent(
        batch_id=batch.id,
        business_date=date(2026, 4, 24),
        entity_code=entity.entity_code,
        entity_name="用户编辑后的单位名",
        account_code=account.account_code,
        account_name=account.account_alias,
        summary="用户编辑后的摘要",
        counterparty="某对手方",
        amount_in=999.99,
        amount_out=0,
        state="待确认",
        source="网银导入",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(ev)
    db_session.commit()

    result = import_preview_service.commit(db_session, batch.batch_code)
    assert result["committed_count"] == 1

    ev_after = db_session.query(FundEvent).one()
    assert ev_after.state == "正常"
    assert ev_after.entity_name == "用户编辑后的单位名"
    assert ev_after.summary == "用户编辑后的摘要"
    assert float(ev_after.amount_in) == 999.99


# ── SourceFile status write-back tests ──


def _add_source_file(db, batch, status="ready", error_code=None, error_message=None):
    sf = create_source_file_for_upload(db, batch, "/uploads/test.xlsx", "test.xlsx", b"data")
    if status != "uploaded":
        update_source_file_status(db, sf, status=status, error_code=error_code, error_message=error_message)
        db.commit()
    return sf


def test_bank_preview_success_updates_source_file_to_parsed(db_session, chart_of_accounts, tmp_path, monkeypatch):
    """parser 成功时 ready → parsed"""
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    _add_parser_artifact(db_session)

    batch = add_import_batch(db_session, batch_code="BANK-SF-001", source_type="bank", source_name="bank.xlsx")
    sf = _add_source_file(db_session, batch, status="ready")

    monkeypatch.setattr(bank_svc, "DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    file_data = make_xlsx([
        ["Date", "Summary", "Income"],
        ["2026-04-24", "test", "100"],
    ])
    (upload_dir / f"{batch.batch_code}_bank.xlsx").write_bytes(file_data)

    canonical_rows = [{
        "business_date": date(2026, 4, 24),
        "entity_code": entity.entity_code,
        "entity_name": entity.short_name,
        "account_code": account.account_code,
        "account_name": account.account_alias,
        "summary": "test row",
        "counterparty": "",
        "amount_in": 100.0,
        "amount_out": 0,
        "rolling_balance": None,
        "state": "正常",
        "source": "网银导入",
    }]

    with patch.object(bank_svc.artifact_runtime, "run_parser", return_value=iter(canonical_rows)):
        result = import_preview_service.get_preview(db_session, batch.batch_code)

    assert result["total_count"] == 1
    db_session.refresh(sf)
    assert sf.status == "parsed"
    assert sf.error_code is None


def test_bank_preview_parser_failure_updates_source_file_failed(db_session, chart_of_accounts, tmp_path, monkeypatch):
    """parser runtime 抛错时 → failed + PARSER_RUNTIME_FAILED"""
    _add_parser_artifact(db_session)

    batch = add_import_batch(db_session, batch_code="BANK-SF-002", source_type="bank", source_name="bank.xlsx")
    sf = _add_source_file(db_session, batch, status="ready")

    monkeypatch.setattr(bank_svc, "DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    file_data = make_xlsx([["Date", "Summary"], ["2026-04-24", "test"]])
    (upload_dir / f"{batch.batch_code}_bank.xlsx").write_bytes(file_data)

    with patch.object(bank_svc.artifact_runtime, "run_parser", side_effect=Exception("boom")):
        result = import_preview_service.get_preview(db_session, batch.batch_code)

    assert result["parser_status"] == "unavailable"
    db_session.refresh(sf)
    assert sf.status == "failed"
    assert sf.error_code == "PARSER_RUNTIME_FAILED"


def test_bank_preview_no_parser_keeps_needs_rule_with_error(db_session, chart_of_accounts, tmp_path, monkeypatch):
    """无 parser 时 → needs_rule + PARSER_NOT_FOUND"""
    batch = add_import_batch(db_session, batch_code="BANK-SF-003", source_type="bank", source_name="bank.xlsx")
    sf = _add_source_file(db_session, batch, status="uploaded")
    update_source_file_status(db_session, sf, status="needs_rule")
    db_session.commit()

    monkeypatch.setattr(bank_svc, "DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    file_data = make_xlsx([["Date", "Summary"], ["2026-04-24", "test"]])
    (upload_dir / f"{batch.batch_code}_bank.xlsx").write_bytes(file_data)

    result = import_preview_service.get_preview(db_session, batch.batch_code)

    assert result["parser_status"] == "unavailable"
    db_session.refresh(sf)
    assert sf.status == "needs_rule"
    assert sf.error_code == "PARSER_NOT_FOUND"
