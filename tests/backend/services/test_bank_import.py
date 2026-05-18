from datetime import date, datetime
from unittest.mock import patch

import pytest

from conftest import make_xlsx
from db.tables import Bank, FundEvent, ParserArtifact
from services import bank_import_service


def _add_parser_artifact(db):
    artifact = ParserArtifact(
        name="Test Bank Parser",
        kind="bank",
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
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def test_upload_returns_parser_match(db_session, chart_of_accounts, tmp_path, monkeypatch):
    artifact = _add_parser_artifact(db_session)
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    file_data = make_xlsx([
        ["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"],
        ["2026-04-24", str(entity.id), str(account.id), "bank receipt", "120.50", ""],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    result = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")

    assert "parser_match" in result
    assert result["parser_match"]["matched"] is True
    assert result["parser_match"]["parser_artifact_id"] == artifact.id
    assert result["parser_match"]["match_level"] == "global_default"
    assert "identity_hints" in result
    assert "bank_resolution" in result
    assert "account_attribution" in result
    assert "format_fingerprint" in result


def test_preview_requires_parser_artifact_id(db_session):
    with pytest.raises(ValueError, match="缺少 ParserArtifact"):
        bank_import_service.preview(db_session, "MISSING_BATCH", parser_artifact_id=None)


def test_commit_with_parser_artifact(db_session, chart_of_accounts, tmp_path, monkeypatch):
    artifact = _add_parser_artifact(db_session)
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    file_data = make_xlsx([
        ["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"],
        ["2026-04-24", str(entity.id), str(account.id), "bank receipt", "120.50", ""],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    upload = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")

    canonical_rows = [
        {
            "business_date": date(2026, 4, 24),
            "entity_code": "E001",
            "entity_name": "Entity 001 Ltd",
            "account_code": "A001",
            "account_name": "Main Account",
            "summary": "bank receipt",
            "counterparty": "",
            "amount_in": 120.50,
            "amount_out": 0,
            "rolling_balance": None,
            "state": "正常",
            "source": "网银导入",
        },
    ]

    with patch.object(bank_import_service.artifact_runtime, "run_parser", return_value=iter(canonical_rows)):
        result = bank_import_service.commit(
            db_session, upload["batch_code"], artifact.id,
        )

    assert result["inserted_rows"] == 1
    assert result["parser_artifact_id"] == artifact.id
    event = db_session.query(FundEvent).filter(FundEvent.batch_id == upload["batch_id"]).one()
    assert event.parser_artifact_id == artifact.id


def test_commit_invalid_batch_raises(db_session):
    with pytest.raises(ValueError):
        bank_import_service.commit(db_session, "MISSING_BATCH", parser_artifact_id=1)


def _add_bank_parser(db, name, bank_id=None, format_key=None):
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


def test_upload_matches_bank_format_parser(db_session, chart_of_accounts, tmp_path, monkeypatch):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    bank = chart_of_accounts["bank"]

    # Bank+format specific parser AND a global default
    _add_bank_parser(db_session, "BOC_Format1", bank_id=bank.id, format_key="fp_test1234")
    global_parser = _add_bank_parser(db_session, "Global_Default")

    file_data = make_xlsx([
        ["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"],
        ["2026-04-24", str(entity.id), str(account.id), "bank receipt", "120.50", ""],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    result = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")

    # format_fingerprint won't match "fp_test1234", falls to global_default
    assert result["parser_match"]["matched"] is True
    assert result["parser_match"]["match_level"] == "global_default"
    assert result["parser_match"]["parser_artifact_id"] == global_parser.id


def test_same_format_matches_same_parser(db_session, chart_of_accounts, tmp_path, monkeypatch):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]

    file_data1 = make_xlsx([
        ["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"],
        ["2026-04-24", str(entity.id), str(account.id), "receipt1", "100", ""],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    r1 = bank_import_service.upload_file(db_session, file_data1, "bank1.xlsx")
    fp = r1["format_fingerprint"]

    # Create a parser matching this format only (format_default level)
    parser = _add_bank_parser(db_session, "Format_Matched", format_key=fp)

    # Second upload with same format → should match format_default
    file_data2 = make_xlsx([
        ["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"],
        ["2026-04-25", str(entity.id), str(account.id), "receipt2", "200", ""],
    ])
    r2 = bank_import_service.upload_file(db_session, file_data2, "bank2.xlsx")

    assert r2["parser_match"]["matched"] is True
    assert r2["parser_match"]["match_level"] == "format_default"
    assert r2["parser_match"]["parser_artifact_id"] == parser.id


def test_upload_parser_conflict(db_session, chart_of_accounts, tmp_path, monkeypatch):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]

    # Two global default parsers → conflict
    _add_bank_parser(db_session, "Global1")
    _add_bank_parser(db_session, "Global2")

    file_data = make_xlsx([
        ["Date", "Summary", "Income"],
        ["2026-04-24", "test", "100"],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    result = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")

    assert result["parser_match"]["matched"] is False
    assert result["parser_match"]["match_level"] == "conflict"


def test_upload_no_parser_still_succeeds(db_session, chart_of_accounts, tmp_path, monkeypatch):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]

    file_data = make_xlsx([
        ["Date", "Summary", "Income"],
        ["2026-04-24", "test", "100"],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    result = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")

    assert result["parser_match"]["matched"] is False
    assert result["parser_match"]["match_level"] == "none"
    assert result["batch_code"] is not None
