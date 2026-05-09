from datetime import date, datetime
from unittest.mock import patch

import pytest

from conftest import make_xlsx
from db.tables import FundEvent, ParserArtifact
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
    assert result["parser_match"] is not None
    assert result["parser_match"]["matched"] is True
    assert result["parser_match"]["parser_artifact_id"] == artifact.id


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
