"""Tests for parser training service and hardcoding guard."""
import os
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import make_xlsx, seed_chart_of_accounts
from db.tables import ImportBatch, ParserArtifact
from services import parser_training_service
from core.artifact_runtime import run_parser_trial


def _add_parser_artifact(db, name="Test Bank Parser", bank_id=None, format_key=None, status="active"):
    artifact = ParserArtifact(
        name=name, kind="bank", account_code=None,
        bank_id=bank_id, format_key=format_key,
        match_rules={}, version=1, status=status,
        code="def parse(wb, ctx): return []",
        primitives_imports=[], sample_check_log={},
        confidence=0.9, created_by="test", created_at=datetime.now(),
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def _make_sample_xlsx():
    return make_xlsx([
        ["日期", "摘要", "收入", "支出", "余额"],
        ["2026-04-24", "测试收入", "1000.00", "", "10000.00"],
        ["2026-04-25", "测试支出", "", "500.00", "9500.00"],
    ])


# ── parser_context_service ──


def test_build_bank_parser_context(db_session):
    seed_chart_of_accounts(db_session)
    from services.parser_context_service import build_bank_parser_context
    ctx = build_bank_parser_context(db_session)
    assert "entities" in ctx
    assert "banks" in ctx
    assert "accounts" in ctx
    assert len(ctx["entities"]) >= 1
    assert len(ctx["banks"]) >= 1
    assert len(ctx["accounts"]) >= 1


# ── create_training_job ──


def test_create_training_job_success(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    seed_chart_of_accounts(db_session)

    file_data = _make_sample_xlsx()
    result = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    assert result["job_id"].startswith("pt_")
    assert result["filename"] == "test.xlsx"
    assert result["format"] == "xlsx"
    assert result["row_count"] == 2
    assert len(result["headers"]) == 5
    assert "context" in result


def test_create_training_job_rejects_unknown_format(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="不支持"):
        parser_training_service.create_training_job(db_session, b"data", "test.pdf")


# ── run_candidate trial ──


def test_run_candidate_success(db_session, tmp_path):
    file_data = _make_sample_xlsx()
    file_path = tmp_path / "sample.xlsx"
    file_path.write_bytes(file_data)

    code = '''
def parse(wb, ctx):
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            rows.append({
                "business_date": str(row[0]),
                "summary": str(row[1] or ""),
                "amount_in": float(row[2] or 0),
                "amount_out": float(row[3] or 0),
                "rolling_balance": float(row[4] or 0),
                "entity_code": "",
                "entity_name": "",
                "account_code": "",
                "account_name": "",
                "counterparty": "",
                "state": "正常",
                "source": "网银导入",
            })
    return rows
'''
    result = parser_training_service.run_candidate(str(file_path), code)
    assert result["status"] == "trial_success"
    assert result["row_count"] == 2
    assert result["rows"][0]["summary"] == "测试收入"


def test_run_candidate_syntax_error(db_session, tmp_path):
    file_data = _make_sample_xlsx()
    file_path = tmp_path / "sample.xlsx"
    file_path.write_bytes(file_data)

    from core.artifact_ast_guard import PrimitivesViolationError
    with pytest.raises(PrimitivesViolationError):
        parser_training_service.run_candidate(str(file_path), "def broken(")


def test_run_candidate_does_not_modify_artifacts(db_session, tmp_path):
    file_data = _make_sample_xlsx()
    file_path = tmp_path / "sample.xlsx"
    file_path.write_bytes(file_data)

    code = "def parse(wb, ctx): return []"
    count_before = db_session.query(ParserArtifact).count()
    parser_training_service.run_candidate(str(file_path), code)
    count_after = db_session.query(ParserArtifact).count()
    assert count_before == count_after


# ── save_parser ──


def test_save_parser_creates_active(db_session):
    code = "def parse(wb, ctx): return []"
    result = parser_training_service.save_parser(
        db_session,
        name="test_save_parser",
        code=code,
        bank_id=None,
        format_key="fp_abc",
        match_rules={},
        sample_check_log={"tested": True},
        confidence=0.85,
        primitives_imports=[],
    )
    assert result["status"] == "active"
    assert result["name"] == "test_save_parser"
    assert result["format_key"] == "fp_abc"


def test_save_parser_retires_old_active(db_session):
    old = _add_parser_artifact(db_session, name="test_retire_v1", format_key="fp_xyz")
    assert old.status == "active"

    result = parser_training_service.save_parser(
        db_session, name="test_retire_v2",
        code="def parse(wb, ctx): return []",
        bank_id=None, format_key="fp_xyz",
        match_rules={}, sample_check_log={}, confidence=None, primitives_imports=[],
    )
    assert result["status"] == "active"

    db_session.refresh(old)
    assert old.status == "retired"


# ── hardcoding guard tool ──


def test_agent_tool_rejects_hardcoded_account():
    from agents.tools.artifact_ops import artifact_create_parser_draft
    from agents.tool_registry import ToolContext

    ctx = ToolContext(agent_id=1, agent_code="test", session_id=1, db=None)
    result = artifact_create_parser_draft(
        name="bad", code='DEFAULT_ACCOUNT_CODE = "A001"',
        ctx=ctx,
    )
    assert result["ok"] is False
    assert "硬编码" in result["error"]


def test_agent_tool_accepts_clean_code():
    from agents.tools.artifact_ops import artifact_create_parser_draft
    from agents.tool_registry import ToolContext

    ctx = ToolContext(agent_id=1, agent_code="test", session_id=1, db=None)
    code = "from datetime import datetime\ndef parse(wb, ctx): return []"
    result = artifact_create_parser_draft(name="clean", code=code, ctx=ctx)
    assert result["ok"] is True


# ── hardcoding guard CLI ──


def test_hardcoding_guard_passes():
    import sys
    guards_dir = str(Path(__file__).resolve().parents[3] / "tools" / "guards")
    if guards_dir not in sys.path:
        sys.path.insert(0, guards_dir)
    from check_parser_hardcoding import check_parser_files
    violations = check_parser_files()
    assert len(violations) == 0


# ── run_parser_trial direct ──


def test_run_parser_trial_returns_rows_and_no_error(tmp_path):
    file_data = _make_sample_xlsx()
    fp = tmp_path / "t.xlsx"
    fp.write_bytes(file_data)

    code = '''
def parse(wb, ctx):
    ws = wb.active
    return [
        {"business_date": "2026-01-01", "entity_code": "", "entity_name": "",
         "account_code": "", "account_name": "", "summary": "test",
         "counterparty": "", "amount_in": 100, "amount_out": 0,
         "rolling_balance": None, "state": "正常", "source": "网银导入"}
    ]
'''
    rows, err = run_parser_trial(code, str(fp))
    assert err is None
    assert len(rows) == 1
    assert rows[0]["summary"] == "test"
