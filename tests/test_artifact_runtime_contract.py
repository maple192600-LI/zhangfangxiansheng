"""Tests for artifact runtime contract.

These are RUNTIME MECHANISM tests — they verify that the deterministic executor
can load, validate, exec, and coerce artifact code. They do NOT verify bank
generalization or account matching. Hardcoded entity/account codes in test
parser code are test fixtures, not a claim of bank-specific capability.
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.artifact_runtime import (
    ArtifactExecutionError,
    ArtifactNotActiveError,
    ArtifactNotFoundError,
    ArtifactRuntimeError,
    PrimitivesViolationError,
    SandboxTimeoutError,
    run_parser,
    run_rule,
)
from db.tables import Base, ParserArtifact

SIMPLE_PARSER_CODE = '''
from fund.primitives.canonical import emit_row

def parse(wb, ctx):
    yield emit_row(
        business_date=None,
        entity_code="E001",
        entity_name="TestEntity",
        account_code="A001",
        account_name="TestAccount",
        summary="test row",
        counterparty=None,
        amount_in=100,
        amount_out=0,
        rolling_balance=None,
        source="网银导入",
    )
'''

NO_PARSE_CODE = 'x = 42'

CRASH_PARSER_CODE = '''
def parse(wb, ctx):
    raise RuntimeError("boom")
'''

IMPORT_OS_CODE = '''
import os

def parse(wb, ctx):
    yield {}
'''

LIST_PARSER_CODE = '''
from fund.primitives.canonical import emit_row

def parse(wb, ctx):
    return [emit_row(
        business_date=None,
        entity_code="E002",
        entity_name="ListEntity",
        account_code="A002",
        account_name="ListAccount",
        summary="list row",
        counterparty=None,
        amount_in=200,
        amount_out=0,
        rolling_balance=None,
        source="网银导入",
    )]
'''

# Demonstrates the correct pattern: parser takes account from ctx, not hardcoded.
CTX_PARSER_CODE = '''
from fund.primitives.canonical import emit_row

def parse(wb, ctx):
    entity_code = ctx.get("entity_code", "")
    entity_name = ctx.get("entity_name", "")
    account_code = ctx.get("account_code", "")
    account_name = ctx.get("account_name", "")
    sheet = wb.active
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        yield emit_row(
            business_date=None,
            entity_code=entity_code,
            entity_name=entity_name,
            account_code=account_code,
            account_name=account_name,
            summary=str(row[0]) if row[0] else "",
            counterparty=None,
            amount_in=0,
            amount_out=0,
            rolling_balance=None,
            source="网银导入",
        )
'''


@pytest.fixture(scope="module")
def db_engine():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        engine = create_engine(f"sqlite:///{db_path}")
        @event.listens_for(engine, "connect")
        def _fk(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
        Base.metadata.create_all(engine)
        yield engine
        engine.dispose()


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    with Session() as s:
        yield s
        s.rollback()


@pytest.fixture
def xlsx_file():
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "摘要", "收入", "支出", "余额"])
    ws.append(["2026-05-01", "test", 100, 0, 100])
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


_counter = 0

def _next_id():
    global _counter
    _counter += 1
    return _counter


def _make_artifact(db, code=SIMPLE_PARSER_CODE, status="active"):
    art = ParserArtifact(
        name=f"test_parser_{_next_id()}",
        kind="bank",
        version=1,
        code=code,
        primitives_imports="[]",
        status=status,
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    return art


# ── run_parser: active artifact returns rows ──

def test_run_parser_active_artifact_returns_rows(db_session, xlsx_file):
    art = _make_artifact(db_session)
    rows = list(run_parser(db_session, art.id, xlsx_file))
    assert len(rows) >= 1
    row = rows[0]
    assert row["entity_code"] == "E001"
    assert row["account_code"] == "A001"
    assert row["source"] == "网银导入"


# ── run_parser: list return (not just generator) ──

def test_run_parser_list_return(db_session, xlsx_file):
    art = _make_artifact(db_session, code=LIST_PARSER_CODE)
    rows = list(run_parser(db_session, art.id, xlsx_file))
    assert len(rows) == 1
    assert rows[0]["entity_code"] == "E002"


# ── run_parser: artifact not found ──

def test_run_parser_artifact_not_found(db_session, xlsx_file):
    with pytest.raises(ArtifactNotFoundError):
        list(run_parser(db_session, -1, xlsx_file))


# ── run_parser: artifact not active ──

def test_run_parser_artifact_not_active(db_session, xlsx_file):
    art = _make_artifact(db_session, status="draft")
    with pytest.raises(ArtifactNotActiveError):
        list(run_parser(db_session, art.id, xlsx_file))


# ── run_parser: artifact imports os → AST guard rejects ──

def test_run_parser_ast_guard_rejects_os(db_session, xlsx_file):
    art = _make_artifact(db_session, code=IMPORT_OS_CODE)
    with pytest.raises(PrimitivesViolationError):
        list(run_parser(db_session, art.id, xlsx_file))


# ── run_parser: artifact missing parse function ──

def test_run_parser_no_parse_function(db_session, xlsx_file):
    art = _make_artifact(db_session, code=NO_PARSE_CODE)
    with pytest.raises(ArtifactExecutionError, match="parse"):
        list(run_parser(db_session, art.id, xlsx_file))


# ── run_parser: parse crashes → ArtifactExecutionError ──

def test_run_parser_crash_wrapped_as_execution_error(db_session, xlsx_file):
    art = _make_artifact(db_session, code=CRASH_PARSER_CODE)
    with pytest.raises(ArtifactExecutionError, match="boom"):
        list(run_parser(db_session, art.id, xlsx_file))


# ── run_rule: still NotImplementedError ──

def test_run_rule_still_not_implemented():
    with pytest.raises(NotImplementedError, match="Phase H1"):
        run_rule(None, 1, {})


# ── Exception hierarchy ──

def test_exception_hierarchy_base():
    assert issubclass(ArtifactNotFoundError, ArtifactRuntimeError)
    assert issubclass(ArtifactNotActiveError, ArtifactRuntimeError)
    assert issubclass(PrimitivesViolationError, RuntimeError)
    assert issubclass(SandboxTimeoutError, ArtifactRuntimeError)
    assert issubclass(ArtifactExecutionError, ArtifactRuntimeError)


def test_primitives_violation_carries_disallowed():
    exc = PrimitivesViolationError(artifact_id=42, disallowed=["os", "subprocess"])
    assert exc.artifact_id == 42
    assert exc.disallowed == ["os", "subprocess"]
    assert "os" in str(exc)


def test_sandbox_timeout_carries_seconds():
    exc = SandboxTimeoutError(artifact_id=7, timeout_seconds=60)
    assert exc.artifact_id == 7
    assert exc.timeout_seconds == 60
    assert "60" in str(exc)


def test_execution_error_carries_detail():
    exc = ArtifactExecutionError(artifact_id=99, detail="division by zero")
    assert exc.artifact_id == 99
    assert exc.detail == "division by zero"
    assert "division by zero" in str(exc)


# ── Runtime guard ──

def test_no_ai_runtime_blocks_urlopen():
    import urllib.request
    from core.runtime_guard import RuntimeAICallBlocked, no_ai_runtime

    with no_ai_runtime():
        with pytest.raises(RuntimeAICallBlocked):
            urllib.request.urlopen("http://example.com")


def test_no_ai_runtime_restores_after_exit():
    import urllib.request
    from core.runtime_guard import no_ai_runtime

    original = urllib.request.urlopen
    with no_ai_runtime():
        pass
    assert urllib.request.urlopen is original


# ── ctx-based parser: account from ctx, not hardcoded ──

def test_run_parser_uses_ctx_for_account(db_session, xlsx_file):
    art = _make_artifact(db_session, code=CTX_PARSER_CODE)
    ctx_a = {"entity_code": "ENT_A", "entity_name": "Unit A",
             "account_code": "ACC_A", "account_name": "Account A"}
    rows_a = list(run_parser(db_session, art.id, xlsx_file, ctx_a))
    assert len(rows_a) >= 1
    assert rows_a[0]["entity_code"] == "ENT_A"
    assert rows_a[0]["account_code"] == "ACC_A"

    ctx_b = {"entity_code": "ENT_B", "entity_name": "Unit B",
             "account_code": "ACC_B", "account_name": "Account B"}
    rows_b = list(run_parser(db_session, art.id, xlsx_file, ctx_b))
    assert len(rows_b) >= 1
    assert rows_b[0]["entity_code"] == "ENT_B"
    assert rows_b[0]["account_code"] == "ACC_B"

    # Same parser, same file, different ctx → different account归属
    assert rows_a[0]["account_code"] != rows_b[0]["account_code"]
