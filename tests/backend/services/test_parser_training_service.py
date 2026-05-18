"""Tests for parser training service — job_code driven, no file_path exposure."""
import json
import os
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import make_xlsx, seed_chart_of_accounts
from db.tables import ImportBatch, ParserArtifact, ParserTrainingJob
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


def _seed_db(db):
    seed_chart_of_accounts(db)


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


def test_create_training_job_persists(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    result = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    assert result["job_code"].startswith("pt_")
    assert result["filename"] == "test.xlsx"
    assert result["format"] == "xlsx"
    assert result["row_count"] == 2
    assert len(result["headers"]) == 5
    assert "context" in result
    assert "file_path" not in result

    job = db_session.query(ParserTrainingJob).filter(
        ParserTrainingJob.job_code == result["job_code"]
    ).first()
    assert job is not None
    assert job.status == "sample_uploaded"
    assert job.trial_status == "pending"


def test_create_training_job_rejects_unknown_format(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="不支持"):
        parser_training_service.create_training_job(db_session, b"data", "test.pdf")


# ── get_job ──


def test_get_job_returns_persisted_data(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job_code = created["job_code"]

    result = parser_training_service.get_job(db_session, job_code)
    assert result is not None
    assert result["job_code"] == job_code
    assert result["filename"] == "test.xlsx"
    assert "file_path" not in result


def test_get_job_returns_none_for_unknown(db_session):
    result = parser_training_service.get_job(db_session, "pt_nonexist")
    assert result is None


# ── update_candidate_code ──


def test_update_candidate_code_writes_to_job(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    code = "def parse(wb, ctx): return []"
    result = parser_training_service.update_candidate_code(db_session, created["job_code"], code)
    assert result["ok"] is True
    assert result["status"] == "candidate_ready"

    job = db_session.query(ParserTrainingJob).filter(
        ParserTrainingJob.job_code == created["job_code"]
    ).first()
    assert job.candidate_code == code
    assert job.status == "candidate_ready"


def test_update_candidate_code_rejects_hardcoded_account(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    result = parser_training_service.update_candidate_code(
        db_session, created["job_code"],
        'DEFAULT_ACCOUNT_CODE = "A001"',
    )
    assert result["ok"] is False
    assert "硬编码" in result["error"]


def test_update_candidate_code_rejects_unknown_job(db_session):
    result = parser_training_service.update_candidate_code(
        db_session, "pt_nonexist", "def parse(wb, ctx): return []",
    )
    assert result["ok"] is False
    assert "不存在" in result["error"]


# ── run_candidate ──


def test_run_candidate_success(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job_code = created["job_code"]

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
    parser_training_service.update_candidate_code(db_session, job_code, code)
    result = parser_training_service.run_candidate(db_session, job_code)

    assert result["status"] == "trial_success"
    assert result["row_count"] == 2
    assert result["rows"][0]["summary"] == "测试收入"

    job = db_session.query(ParserTrainingJob).filter(
        ParserTrainingJob.job_code == job_code
    ).first()
    assert job.trial_status == "success"
    assert job.status == "trial_success"


def test_run_candidate_no_code(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    result = parser_training_service.run_candidate(db_session, created["job_code"])
    assert result["status"] == "error"
    assert "候选规则为空" in result["error"]


def test_run_candidate_syntax_error(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job_code = created["job_code"]

    # Bypass guard to write bad code directly for trial test
    job = db_session.query(ParserTrainingJob).filter(
        ParserTrainingJob.job_code == job_code
    ).first()
    job.candidate_code = "def broken("
    job.status = "candidate_ready"
    db_session.commit()

    result = parser_training_service.run_candidate(db_session, job_code)
    assert result["status"] == "trial_failed"

    db_session.refresh(job)
    assert job.trial_status == "failed"


def test_run_candidate_does_not_modify_artifacts(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    code = "def parse(wb, ctx): return []"
    parser_training_service.update_candidate_code(db_session, created["job_code"], code)

    count_before = db_session.query(ParserArtifact).count()
    parser_training_service.run_candidate(db_session, created["job_code"])
    count_after = db_session.query(ParserArtifact).count()
    assert count_before == count_after


# ── save_parser ──


def test_save_parser_creates_active(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job_code = created["job_code"]

    code = "def parse(wb, ctx): return []"
    parser_training_service.update_candidate_code(db_session, job_code, code)
    parser_training_service.run_candidate(db_session, job_code)

    result = parser_training_service.save_parser(db_session, job_code, "test_save_parser")
    assert result["status"] == "active"
    assert result["name"] == "test_save_parser"


def test_save_parser_rejects_no_candidate(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    with pytest.raises(ValueError, match="候选规则为空"):
        parser_training_service.save_parser(db_session, created["job_code"], "bad")


def test_save_parser_rejects_no_trial(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    code = "def parse(wb, ctx): return []"
    parser_training_service.update_candidate_code(db_session, created["job_code"], code)

    with pytest.raises(ValueError, match="未通过试运行"):
        parser_training_service.save_parser(db_session, created["job_code"], "bad")


def test_save_parser_retires_old_active(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job_code = created["job_code"]

    code = "def parse(wb, ctx): return []"
    parser_training_service.update_candidate_code(db_session, job_code, code)
    parser_training_service.run_candidate(db_session, job_code)

    result = parser_training_service.save_parser(db_session, job_code, "test_retire_v2")
    assert result["status"] == "active"

    job = db_session.query(ParserTrainingJob).filter(
        ParserTrainingJob.job_code == job_code
    ).first()
    assert job.status == "active_parser_saved"


# ── Agent tool: parser_training_update_candidate ──


def test_agent_tool_writes_to_job(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    from agents.tools.artifact_ops import parser_training_update_candidate
    from agents.tool_registry import ToolContext

    ctx = ToolContext(agent_id=1, agent_code="test", session_id=1, db=db_session)
    result = parser_training_update_candidate(
        job_code=created["job_code"],
        code="def parse(wb, ctx): return []",
        ctx=ctx,
    )
    assert result["ok"] is True


def test_agent_tool_rejects_hardcoded_account(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    from agents.tools.artifact_ops import parser_training_update_candidate
    from agents.tool_registry import ToolContext

    ctx = ToolContext(agent_id=1, agent_code="test", session_id=1, db=db_session)
    result = parser_training_update_candidate(
        job_code=created["job_code"],
        code='DEFAULT_ACCOUNT_CODE = "A001"',
        ctx=ctx,
    )
    assert result["ok"] is False
    assert "硬编码" in result["error"]


def test_agent_tool_no_db_returns_error():
    from agents.tools.artifact_ops import parser_training_update_candidate
    from agents.tool_registry import ToolContext

    ctx = ToolContext(agent_id=1, agent_code="test", session_id=1, db=None)
    result = parser_training_update_candidate(
        job_code="pt_test",
        code="def parse(wb, ctx): return []",
        ctx=ctx,
    )
    assert result["ok"] is False


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


# ── 12C: agents endpoint + agent-session validation + starter prompt ──


def test_list_active_agents_returns_active(db_session):
    """GET /parser-training/agents returns only active agents."""
    from db.tables import Agent
    active = Agent(
        agent_code="A_TEST_1", display_name="测试智能体1",
        status="active", ai_config_id=None, workspace_path="/tmp/a1",
    )
    inactive = Agent(
        agent_code="A_TEST_2", display_name="测试智能体2",
        status="inactive", ai_config_id=None, workspace_path="/tmp/a2",
    )
    db_session.add_all([active, inactive])
    db_session.commit()

    from api.parser_training import list_active_agents
    result = list_active_agents(db=db_session)
    data = result["data"]
    assert len(data) == 1
    assert data[0]["display_name"] == "测试智能体1"
    assert data[0]["agent_code"] == "A_TEST_1"


def test_list_active_agents_returns_empty_when_none(db_session):
    """GET /parser-training/agents returns empty array when no active agents."""
    from api.parser_training import list_active_agents
    result = list_active_agents(db=db_session)
    data = result["data"]
    assert data == []


def test_agent_session_requires_explicit_agent_id(db_session, tmp_path, monkeypatch):
    """POST agent-session with non-existent agent returns error."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    from api.parser_training import create_agent_session, AgentSessionBody
    body = AgentSessionBody(agent_id=99999)
    result = create_agent_session(created["job_code"], body, db=db_session)
    assert result["code"] != 0


def test_agent_session_rejects_inactive_agent(db_session, tmp_path, monkeypatch):
    """POST agent-session with inactive agent returns error."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    from db.tables import Agent
    inactive = Agent(
        agent_code="A_INACTIVE", display_name="未启用智能体",
        status="inactive", ai_config_id=None, workspace_path="/tmp/ai",
    )
    db_session.add(inactive)
    db_session.commit()

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    from api.parser_training import create_agent_session, AgentSessionBody
    body = AgentSessionBody(agent_id=inactive.id)
    result = create_agent_session(created["job_code"], body, db=db_session)
    assert result["code"] != 0


def test_starter_prompt_contains_required_terms(db_session, tmp_path, monkeypatch):
    """Starter prompt includes parser_training_update_candidate and job_code."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job = parser_training_service.get_job(db_session, created["job_code"])

    from api.parser_training import _build_starter_prompt
    prompt = _build_starter_prompt(job)

    assert "parser_training_update_candidate" in prompt
    assert created["job_code"] in prompt
    assert "用户选中的现有智能体" in prompt


def test_starter_prompt_no_rule_agent(db_session, tmp_path, monkeypatch):
    """Starter prompt must NOT contain '规则智能体'."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job = parser_training_service.get_job(db_session, created["job_code"])

    from api.parser_training import _build_starter_prompt
    prompt = _build_starter_prompt(job)

    assert "规则智能体" not in prompt
    assert "用户最终审核的是解析结果表格，不是代码" in prompt
