"""Tests for source_file_service and account_resolution_audit_service.

Verifies SourceFile creation, status resolution, and account resolution
evidence persistence during the bank import upload flow.
"""
from datetime import date, datetime

import pytest
from conftest import make_xlsx
from db.tables import (
    AccountResolutionAttempt,
    AccountResolutionEvidence,
    Bank,
    Division,
    Entity,
    FundEvent,
    ImportBatch,
    ParserArtifact,
    SourceFile,
)
from services import bank_import_service
from services.source_file_service import (
    compute_file_hash,
    create_source_file_for_upload,
    get_source_files_for_batch,
    resolve_source_file_status,
    update_source_file_status,
)
from services.account_resolution_audit_service import record_account_resolution_attempt


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


# ── SourceFile service unit tests ──


def test_compute_file_hash_deterministic():
    data = b"hello world"
    h1 = compute_file_hash(data)
    h2 = compute_file_hash(data)
    assert h1 == h2
    assert len(h1) == 64


def test_create_source_file_for_upload(db_session):
    batch = ImportBatch(
        batch_code="TEST001",
        source_type="bank",
        source_name="test.xlsx",
        status="uploaded",
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    sf = create_source_file_for_upload(
        db_session, batch, "/uploads/test.xlsx", "test.xlsx", b"file content",
    )
    db_session.commit()
    db_session.refresh(sf)

    assert sf.batch_id == batch.id
    assert sf.original_filename == "test.xlsx"
    assert sf.storage_path == "/uploads/test.xlsx"
    assert sf.file_hash == compute_file_hash(b"file content")
    assert sf.file_size == 12
    assert sf.status == "uploaded"


def test_update_source_file_status(db_session):
    batch = ImportBatch(
        batch_code="TEST002",
        source_type="bank",
        source_name="test.xlsx",
        status="uploaded",
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    sf = create_source_file_for_upload(
        db_session, batch, "/uploads/test.xlsx", "test.xlsx", b"data",
    )
    db_session.commit()

    update_source_file_status(
        db_session, sf, status="ready",
        parser_artifact_id=1, format_fingerprint="fp_abc123",
    )
    db_session.commit()
    db_session.refresh(sf)

    assert sf.status == "ready"
    assert sf.parser_artifact_id == 1
    assert sf.format_fingerprint == "fp_abc123"


def test_update_source_file_status_clear_error(db_session):
    batch = ImportBatch(
        batch_code="TEST_CLEAR",
        source_type="bank",
        source_name="test.xlsx",
        status="uploaded",
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    sf = create_source_file_for_upload(
        db_session, batch, "/uploads/test.xlsx", "test.xlsx", b"data",
    )
    db_session.commit()

    update_source_file_status(
        db_session, sf, status="failed",
        error_code="PARSER_RUNTIME_FAILED", error_message="some error",
    )
    db_session.commit()
    db_session.refresh(sf)
    assert sf.error_code == "PARSER_RUNTIME_FAILED"
    assert sf.error_message == "some error"

    update_source_file_status(db_session, sf, status="parsed", clear_error=True)
    db_session.commit()
    db_session.refresh(sf)

    assert sf.status == "parsed"
    assert sf.error_code is None
    assert sf.error_message is None


def test_get_source_files_for_batch(db_session):
    batch = ImportBatch(
        batch_code="TEST003",
        source_type="bank",
        source_name="test.xlsx",
        status="uploaded",
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    create_source_file_for_upload(db_session, batch, "/uploads/a.xlsx", "a.xlsx", b"a")
    create_source_file_for_upload(db_session, batch, "/uploads/b.xlsx", "b.xlsx", b"b")
    db_session.commit()

    sfs = get_source_files_for_batch(db_session, batch.id)
    assert len(sfs) == 2


def test_resolve_source_file_status_mapping():
    assert resolve_source_file_status(True, "matched") == "ready"
    assert resolve_source_file_status(True, "ambiguous") == "needs_account"
    assert resolve_source_file_status(True, "unmatched") == "needs_account"
    assert resolve_source_file_status(True, "conflict") == "needs_account"
    assert resolve_source_file_status(False, "unmatched") == "needs_rule"
    assert resolve_source_file_status(False, "matched") == "needs_rule"
    assert resolve_source_file_status(True, "matched", parse_error=True) == "failed"


# ── Account resolution audit tests ──


def test_record_matched_attempt(db_session):
    batch = ImportBatch(
        batch_code="TEST004",
        source_type="bank",
        source_name="test.xlsx",
        status="uploaded",
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    sf = create_source_file_for_upload(
        db_session, batch, "/uploads/test.xlsx", "test.xlsx", b"data",
    )
    db_session.commit()

    attempt = record_account_resolution_attempt(
        db_session, sf,
        account_attribution={
            "status": "matched",
            "entity_code": "E001",
            "entity_name": "Entity A",
            "account_code": "A001",
            "account_name": "Main Account",
            "confidence": 0.95,
            "match_reason": "account_number_exact",
            "candidates": [],
            "raw_hints": {"account_number": "6222021234567890"},
            "error_code": None,
        },
        identity_hints={
            "identity_hints": {
                "account_number": "6222021234567890",
                "account_last_four": "7890",
                "account_name": "Test Holder",
                "entity_name": "Test Corp",
                "bank_name": "工商银行",
                "filename_hint": "7890",
            },
        },
    )
    db_session.commit()
    db_session.refresh(attempt)

    assert attempt.status == "matched"
    assert attempt.recommended_entity_code == "E001"
    assert attempt.recommended_account_code == "A001"
    assert float(attempt.confidence) == 0.95
    assert attempt.match_reason == "account_number_exact"

    evidence = db_session.query(AccountResolutionEvidence).filter(
        AccountResolutionEvidence.attempt_id == attempt.id,
    ).all()
    evidence_types = {e.evidence_type for e in evidence}
    assert "account_number" in evidence_types
    # account_last_four is only generated when no account_number present
    assert "account_name" in evidence_types
    assert "entity_name" in evidence_types
    assert "bank" in evidence_types
    assert "filename" in evidence_types
    assert "parser_hint" in evidence_types


def test_record_unmatched_attempt(db_session):
    batch = ImportBatch(
        batch_code="TEST005",
        source_type="bank",
        source_name="test.xlsx",
        status="uploaded",
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    sf = create_source_file_for_upload(
        db_session, batch, "/uploads/test.xlsx", "test.xlsx", b"data",
    )
    db_session.commit()

    attempt = record_account_resolution_attempt(
        db_session, sf,
        account_attribution={
            "status": "unmatched",
            "entity_code": "",
            "entity_name": "",
            "account_code": "",
            "account_name": "",
            "confidence": 0.0,
            "match_reason": "没有可用的身份线索",
            "candidates": [],
            "raw_hints": {},
            "error_code": "NO_IDENTITY_HINTS",
        },
    )
    db_session.commit()
    db_session.refresh(attempt)

    assert attempt.status == "unmatched"
    assert attempt.error_code == "NO_IDENTITY_HINTS"

    evidence = db_session.query(AccountResolutionEvidence).filter(
        AccountResolutionEvidence.attempt_id == attempt.id,
    ).all()
    evidence_types = {e.evidence_type for e in evidence}
    assert "parser_hint" in evidence_types


# ── Integration: upload creates SourceFile + resolution ──


def test_bank_upload_creates_source_file(db_session, chart_of_accounts, tmp_path, monkeypatch):
    _add_parser_artifact(db_session)
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    file_data = make_xlsx([
        ["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"],
        ["2026-04-24", str(entity.id), str(account.id), "bank receipt", "120.50", ""],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    result = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")

    assert "source_file_id" in result
    assert "source_file_status" in result
    assert result["source_file_id"] is not None

    sf = db_session.query(SourceFile).filter(SourceFile.id == result["source_file_id"]).one()
    assert sf.original_filename == "bank.xlsx"
    assert sf.file_hash == compute_file_hash(file_data)
    assert sf.file_size == len(file_data)
    assert sf.status in ("ready", "needs_account", "parsed")


def test_bank_upload_records_resolution_attempt(db_session, chart_of_accounts, tmp_path, monkeypatch):
    _add_parser_artifact(db_session)
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    file_data = make_xlsx([
        ["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"],
        ["2026-04-24", str(entity.id), str(account.id), "bank receipt", "120.50", ""],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    result = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")

    sf = db_session.query(SourceFile).filter(SourceFile.id == result["source_file_id"]).one()
    attempts = db_session.query(AccountResolutionAttempt).filter(
        AccountResolutionAttempt.source_file_id == sf.id,
    ).all()
    assert len(attempts) >= 1

    evidence = db_session.query(AccountResolutionEvidence).filter(
        AccountResolutionEvidence.attempt_id == attempts[0].id,
    ).all()
    assert len(evidence) >= 1


def test_bank_upload_no_parser_sets_needs_rule(db_session, chart_of_accounts, tmp_path, monkeypatch):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    file_data = make_xlsx([
        ["Date", "Summary", "Income"],
        ["2026-04-24", "test", "100"],
    ])
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    result = bank_import_service.upload_file(db_session, file_data, "bank.xlsx")

    sf = db_session.query(SourceFile).filter(SourceFile.id == result["source_file_id"]).one()
    assert sf.status == "needs_rule"
    assert sf.parser_artifact_id is None
