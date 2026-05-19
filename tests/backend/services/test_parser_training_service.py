"""Tests for parser training service — job_code driven, no file_path exposure."""
import json
import os
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import make_xlsx, make_xls, seed_chart_of_accounts
from db.tables import ImportBatch, ParserArtifact, ParserTrainingJob
from services import parser_training_service, artifact_service
from core.artifact_runtime import run_parser_trial
from api import parser_training as parser_training_api


def _add_parser_artifact(db, name="Test Bank Parser", bank_id=None, format_key=None, account_code=None, status="active"):
    artifact = ParserArtifact(
        name=name, kind="bank", account_code=account_code,
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


def _make_large_sample_xlsx(row_count=100):
    rows = [
        ["银行导出文件", "", "", "", ""],
        ["", "", "", "", ""],
        ["日期", "摘要", "收入", "支出", "余额"],
    ]
    for i in range(1, row_count + 1):
        rows.append([
            f"2026-04-{(i % 28) + 1:02d}",
            f"交易{i:03d}",
            str(i * 10 if i % 2 else ""),
            str(i * 5 if not i % 2 else ""),
            str(10000 + i),
        ])
    return make_xlsx(rows)


_WORKING_PARSE_CODE = '''
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
                "entity_code": "", "entity_name": "",
                "account_code": "", "account_name": "",
                "counterparty": "", "state": "正常", "source": "网银导入",
            })
    return rows
'''


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


def test_create_training_job_uses_representative_rows_not_first_five(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_large_sample_xlsx(100)
    result = parser_training_service.create_training_job(db_session, file_data, "large.xlsx")

    assert result["row_count"] == 100
    assert result["identity_hints"]["detected_header_row"] == 3
    assert result["identity_hints"]["sample_strategy"] == "distributed_across_detected_body"
    assert len(result["sample_rows"]) == 80
    summaries = [row[1] for row in result["sample_rows"]]
    assert "交易001" in summaries
    assert "交易100" in summaries
    assert len(summaries) > 5


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

    parser_training_service.update_candidate_code(db_session, job_code, _WORKING_PARSE_CODE)
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

    parser_training_service.update_candidate_code(db_session, job_code, _WORKING_PARSE_CODE)
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


def test_starter_prompt_uses_detected_header_and_representative_samples(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_large_sample_xlsx(100)
    created = parser_training_service.create_training_job(db_session, file_data, "large.xlsx")
    job = parser_training_service.get_job(db_session, created["job_code"])

    from api.parser_training import _build_starter_prompt
    prompt = _build_starter_prompt(job)

    assert "前5行样本" not in prompt
    assert "代表性正文样本" in prompt
    assert "不是固定前几行" in prompt
    assert "系统自动检测到的表头行: 第 3 行" in prompt
    assert "第80行:" in prompt


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
    assert "用户不审核代码" in prompt


# ── 12D: agent permission + toolset ──


def test_default_permission_includes_parser_training_tool():
    """Default permission allows parser_training_update_candidate."""
    from agents.permission import DEFAULT_PERMISSION
    assert "parser_training_update_candidate" in DEFAULT_PERMISSION["allowed_tools"]


def test_get_permission_default_includes_parser_training_tool():
    """get_permission('{}') includes parser_training_update_candidate."""
    from agents.permission import get_permission
    perm = get_permission("{}")
    assert "parser_training_update_candidate" in perm["allowed_tools"]


def test_get_tools_for_llm_includes_parser_training_tool():
    """LLM tool list includes parser_training_update_candidate under default permission."""
    from agents.permission import DEFAULT_PERMISSION
    from agents.tool_registry import get_tools_for_llm
    tools = get_tools_for_llm(DEFAULT_PERMISSION)
    tool_names = [t["function"]["name"] for t in tools]
    assert "parser_training_update_candidate" in tool_names


def test_parser_training_tool_in_correct_toolset():
    """parser_training_update_candidate is in 'parser_training' toolset, not 'database'."""
    from agents.tool_registry import TOOLSETS, _TOOLS
    assert "parser_training_update_candidate" in TOOLSETS.get("parser_training", [])
    assert "parser_training_update_candidate" not in TOOLSETS.get("database", [])
    td = _TOOLS.get("parser_training_update_candidate")
    assert td is not None
    assert td.toolset == "parser_training"


def test_disabled_parser_training_toolset_removes_tool():
    """disabled_toolsets=['parser_training'] removes parser_training_update_candidate."""
    from agents.permission import DEFAULT_PERMISSION
    from agents.tool_registry import get_tools_for_llm
    perm = DEFAULT_PERMISSION.copy()
    perm["disabled_toolsets"] = ["parser_training"]
    tools = get_tools_for_llm(perm)
    tool_names = [t["function"]["name"] for t in tools]
    assert "parser_training_update_candidate" not in tool_names


# ── 12G: parser lifecycle (activate/retire/delete) ──


def test_activate_parser_sets_active(db_session):
    artifact_service.activate_parser_artifact(db_session, _make_retired_parser(db_session).id)
    row = db_session.query(ParserArtifact).first()
    assert row.status == "active"
    assert row.approved_by == "rule_center"


def test_activate_retires_same_bank_format(db_session):
    old = _add_parser_artifact(db_session, name="old", bank_id=1, format_key="fmt_a", status="active")
    new = _add_parser_artifact(db_session, name="new", bank_id=1, format_key="fmt_a", status="retired")
    artifact_service.activate_parser_artifact(db_session, new.id)

    db_session.refresh(old)
    db_session.refresh(new)
    assert old.status == "retired"
    assert new.status == "active"


def test_retire_parser_sets_retired(db_session):
    p = _add_parser_artifact(db_session, name="active_p", status="active")
    artifact_service.retire_parser_artifact(db_session, p.id)
    db_session.refresh(p)
    assert p.status == "retired"


def test_delete_active_parser_raises(db_session):
    p = _add_parser_artifact(db_session, name="active_p", status="active")
    with pytest.raises(ValueError, match="请先停用"):
        artifact_service.delete_parser_artifact(db_session, p.id)


def test_delete_retired_parser(db_session):
    p = _add_parser_artifact(db_session, name="retired_p", status="retired")
    pid = p.id
    artifact_service.delete_parser_artifact(db_session, p.id)
    assert db_session.query(ParserArtifact).filter(ParserArtifact.id == pid).first() is None


def test_delete_draft_parser(db_session):
    p = _add_parser_artifact(db_session, name="draft_p", status="draft")
    pid = p.id
    artifact_service.delete_parser_artifact(db_session, p.id)
    assert db_session.query(ParserArtifact).filter(ParserArtifact.id == pid).first() is None


def _make_retired_parser(db):
    p = ParserArtifact(
        name="test_retired", kind="bank", account_code=None,
        bank_id=None, format_key=None, match_rules={}, version=1,
        status="retired", code="def parse(wb, ctx): return []",
        primitives_imports=[], sample_check_log={},
        confidence=0.9, created_by="test", created_at=datetime.now(),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ── 12H: retire identity levels + API layer tests ──


def test_activate_retires_format_only_default(db_session):
    """activate bank_id=None + format_key='fmt_x' retires old active with same."""
    old = _add_parser_artifact(db_session, name="old", bank_id=None, format_key="fmt_x", status="active")
    new = _add_parser_artifact(db_session, name="new", bank_id=None, format_key="fmt_x", status="retired")
    artifact_service.activate_parser_artifact(db_session, new.id)

    db_session.refresh(old)
    db_session.refresh(new)
    assert old.status == "retired"
    assert new.status == "active"


def test_activate_retires_global_default(db_session):
    """activate bank_id=None + format_key=None + account_code=None retires old global active."""
    old = _add_parser_artifact(db_session, name="old_global", bank_id=None, format_key=None, status="active")
    new = _add_parser_artifact(db_session, name="new_global", bank_id=None, format_key=None, status="retired")
    artifact_service.activate_parser_artifact(db_session, new.id)

    db_session.refresh(old)
    db_session.refresh(new)
    assert old.status == "retired"
    assert new.status == "active"


def test_approve_retires_format_only_default(db_session):
    """approve bank_id=None + format_key='fmt_x' uses same retire logic."""
    old = _add_parser_artifact(db_session, name="old", bank_id=None, format_key="fmt_x", status="active")
    new = _add_parser_artifact(db_session, name="new", bank_id=None, format_key="fmt_x", status="draft")
    artifact_service.approve_parser_artifact(db_session, new.id, "tester")

    db_session.refresh(old)
    db_session.refresh(new)
    assert old.status == "retired"
    assert new.status == "active"


def test_approve_does_not_retire_different_format_key(db_session):
    """approve format_key='a' should not retire active with format_key='b'."""
    other = _add_parser_artifact(db_session, name="other", bank_id=None, format_key="fmt_b", status="active")
    new = _add_parser_artifact(db_session, name="new", bank_id=None, format_key="fmt_a", status="draft")
    artifact_service.approve_parser_artifact(db_session, new.id, "tester")

    db_session.refresh(other)
    assert other.status == "active"


def test_approve_does_not_retire_different_bank_id(db_session):
    """approve bank_id=1 should not retire active with bank_id=2."""
    other = _add_parser_artifact(db_session, name="other", bank_id=2, format_key="fmt_a", status="active")
    new = _add_parser_artifact(db_session, name="new", bank_id=1, format_key="fmt_a", status="draft")
    artifact_service.approve_parser_artifact(db_session, new.id, "tester")

    db_session.refresh(other)
    assert other.status == "active"


# ── 12H: API layer tests ──


def test_api_get_parser_detail_returns_code(db_session):
    p = _add_parser_artifact(db_session, name="api_test", status="active")
    result = artifact_service.get_parser_artifact(db_session, p.id)
    assert result is not None
    assert result["status"] == "active"
    assert "code" in result


def test_api_activate_returns_active(db_session):
    p = _add_parser_artifact(db_session, name="api_activate", status="retired")
    result = artifact_service.activate_parser_artifact(db_session, p.id)
    assert result["status"] == "active"


def test_api_retire_returns_retired(db_session):
    p = _add_parser_artifact(db_session, name="api_retire", status="active")
    result = artifact_service.retire_parser_artifact(db_session, p.id)
    assert result["status"] == "retired"


def test_api_delete_retired_succeeds(db_session):
    p = _add_parser_artifact(db_session, name="api_delete", status="retired")
    pid = p.id
    artifact_service.delete_parser_artifact(db_session, p.id)
    assert db_session.query(ParserArtifact).filter(ParserArtifact.id == pid).first() is None


def test_api_delete_active_returns_error(db_session):
    p = _add_parser_artifact(db_session, name="api_no_delete", status="active")
    with pytest.raises(ValueError, match="请先停用"):
        artifact_service.delete_parser_artifact(db_session, p.id)


# ── 12I: account-bound parser regression + API wrapper tests ──


def test_activate_retires_account_bound_bank_parser(db_session):
    old = _add_parser_artifact(db_session, name="old_account", bank_id=None, format_key=None, account_code="A001", status="active")
    new = _add_parser_artifact(db_session, name="new_account", bank_id=None, format_key=None, account_code="A001", status="retired")
    artifact_service.activate_parser_artifact(db_session, new.id)
    db_session.refresh(old)
    db_session.refresh(new)
    assert old.status == "retired"
    assert new.status == "active"


def test_approve_retires_account_bound_bank_parser(db_session):
    old = _add_parser_artifact(db_session, name="old_account", bank_id=None, format_key=None, account_code="A002", status="active")
    new = _add_parser_artifact(db_session, name="new_account", bank_id=None, format_key=None, account_code="A002", status="draft")
    artifact_service.approve_parser_artifact(db_session, new.id, "tester")
    db_session.refresh(old)
    db_session.refresh(new)
    assert old.status == "retired"
    assert new.status == "active"


# ── 12I: real API wrapper tests ──


def test_api_wrapper_get_parser_detail(db_session):
    p = _add_parser_artifact(db_session, name="wrapper_detail", status="active")
    result = parser_training_api.get_parser_detail(p.id, db=db_session)
    assert result["code"] == 0
    assert result["data"]["status"] == "active"
    assert "code" in result["data"]


def test_api_wrapper_activate_parser(db_session):
    p = _add_parser_artifact(db_session, name="wrapper_activate", status="retired")
    result = parser_training_api.activate_parser(p.id, db=db_session)
    assert result["code"] == 0
    assert result["data"]["status"] == "active"


def test_api_wrapper_retire_parser(db_session):
    p = _add_parser_artifact(db_session, name="wrapper_retire", status="active")
    result = parser_training_api.retire_parser(p.id, db=db_session)
    assert result["code"] == 0
    assert result["data"]["status"] == "retired"


def test_api_wrapper_delete_retired_parser(db_session):
    p = _add_parser_artifact(db_session, name="wrapper_delete", status="retired")
    pid = p.id
    result = parser_training_api.delete_parser(pid, db=db_session)
    assert result["code"] == 0
    assert result["data"]["deleted"] == pid


def test_api_wrapper_delete_active_parser_returns_error(db_session):
    p = _add_parser_artifact(db_session, name="wrapper_no_delete", status="active")
    result = parser_training_api.delete_parser(p.id, db=db_session)
    assert result["code"] != 0
    assert "停用" in result["message"]


# ── 13A: .xls upload + error handling ──


def test_create_training_job_xls_success(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = make_xls([
        ["日期", "摘要", "收入", "支出", "余额"],
        ["2026-04-24", "测试收入", "1000.00", "", "10000.00"],
        ["2026-04-25", "测试支出", "", "500.00", "9500.00"],
    ])
    result = parser_training_service.create_training_job(db_session, file_data, "中行银行流水.xls")

    assert result["job_code"].startswith("pt_")
    assert result["filename"] == "中行银行流水.xls"
    assert result["format"] == "xls"
    assert result["row_count"] == 2
    assert len(result["headers"]) == 5
    assert "identity_hints" in result


def test_create_training_job_xlsx_still_works(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    result = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    assert result["job_code"].startswith("pt_")
    assert result["format"] == "xlsx"
    assert result["row_count"] == 2


def test_corrupted_file_returns_business_error(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    with pytest.raises(ValueError, match="样本文件读取失败"):
        parser_training_service.create_training_job(db_session, b"not a real file", "bad.xlsx")


def test_api_create_job_corrupted_file_returns_error(db_session, tmp_path, monkeypatch):
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    with pytest.raises(ValueError, match="样本文件读取失败"):
        parser_training_service.create_training_job(db_session, b"corrupted junk data", "corrupt.xlsx")


def test_extract_identity_hints_from_rows():
    from services.bank_statement_identity_service import extract_identity_hints_from_rows
    rows = [
        ["中国银行流水明细", "", "", "", ""],
        ["账号：1234567890123456", "", "", "", ""],
        ["日期", "摘要", "收入", "支出", "余额"],
        ["2026-04-24", "测试", "1000", "", "10000"],
    ]
    result = extract_identity_hints_from_rows(rows, "中行银行流水.xls")
    assert "银行" in result["bank_hint"]
    assert result["identity_hints"]["account_number"] != "" or result["identity_hints"]["bank_name"] != ""
    assert "format_fingerprint" in result


# ── 13C: agent session saved to job + get_job returns session info ──


def test_agent_session_saves_relation_to_job(db_session, tmp_path, monkeypatch):
    """Creating agent session saves agent_id and agent_session_id to the job."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    from db.tables import Agent
    agent = Agent(
        agent_code="A_13C", display_name="13C测试智能体",
        status="active", ai_config_id=None, workspace_path="/tmp/a13c",
    )
    db_session.add(agent)
    db_session.commit()

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    from api.parser_training import create_agent_session, AgentSessionBody
    body = AgentSessionBody(agent_id=agent.id)
    result = create_agent_session(created["job_code"], body, db=db_session)
    assert result["code"] == 0

    # Verify job has agent_id and agent_session_id
    job = db_session.query(ParserTrainingJob).filter(
        ParserTrainingJob.job_code == created["job_code"]
    ).first()
    assert job.agent_id == agent.id
    assert job.agent_session_id is not None


def test_get_job_returns_session_info(db_session, tmp_path, monkeypatch):
    """get_job returns agent_id and agent_session_id in response."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    from db.tables import Agent
    agent = Agent(
        agent_code="A_INFO", display_name="Info测试智能体",
        status="active", ai_config_id=None, workspace_path="/tmp/ainfo",
    )
    db_session.add(agent)
    db_session.commit()

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    # Before session: null
    job_data = parser_training_service.get_job(db_session, created["job_code"])
    assert job_data["agent_id"] is None
    assert job_data["agent_session_id"] is None

    # Create session
    from api.parser_training import create_agent_session, AgentSessionBody
    body = AgentSessionBody(agent_id=agent.id)
    create_agent_session(created["job_code"], body, db=db_session)

    # After session: populated
    job_data = parser_training_service.get_job(db_session, created["job_code"])
    assert job_data["agent_id"] == agent.id
    assert job_data["agent_session_id"] is not None


def test_agent_session_response_no_starter_prompt(db_session, tmp_path, monkeypatch):
    """create_agent_session response does NOT include starter_prompt."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    from db.tables import Agent
    agent = Agent(
        agent_code="A_NOPROMPT", display_name="NoPrompt智能体",
        status="active", ai_config_id=None, workspace_path="/tmp/anp",
    )
    db_session.add(agent)
    db_session.commit()

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")

    from api.parser_training import create_agent_session, AgentSessionBody
    body = AgentSessionBody(agent_id=agent.id)
    result = create_agent_session(created["job_code"], body, db=db_session)
    assert "starter_prompt" not in result["data"]


# ── 13D: .xls run_candidate end-to-end ──


def test_run_candidate_xls_success(db_session, tmp_path, monkeypatch):
    """run_candidate works with .xls sample files, returning parsed rows."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = make_xls([
        ["日期", "摘要", "收入", "支出", "余额"],
        ["2026-04-24", "测试收入", "1000.00", "", "10000.00"],
        ["2026-04-25", "测试支出", "", "500.00", "9500.00"],
    ])
    created = parser_training_service.create_training_job(db_session, file_data, "中行银行流水.xls")
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


def test_run_parser_trial_xls_direct(tmp_path):
    """run_parser_trial directly works with .xls files."""
    file_data = make_xls([
        ["日期", "摘要", "收入", "支出", "余额"],
        ["2026-04-24", "测试收入", "1000.00", "", "10000.00"],
        ["2026-04-25", "测试支出", "", "500.00", "9500.00"],
    ])
    fp = tmp_path / "t.xls"
    fp.write_bytes(file_data)

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
                "entity_code": "", "entity_name": "",
                "account_code": "", "account_name": "",
                "counterparty": "", "state": "正常", "source": "网银导入",
            })
    return rows
'''
    rows, err = run_parser_trial(code, str(fp))
    assert err is None
    assert len(rows) == 2
    assert rows[0]["summary"] == "测试收入"
    assert float(rows[0]["amount_in"]) == 1000.0


def test_run_candidate_error_no_technical_leak(db_session, tmp_path, monkeypatch):
    """run_candidate error field must not contain Traceback/openpyxl/worker setup."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job_code = created["job_code"]

    # Bypass guard to write bad code directly
    job = db_session.query(ParserTrainingJob).filter(
        ParserTrainingJob.job_code == job_code
    ).first()
    job.candidate_code = "def broken("
    job.status = "candidate_ready"
    db_session.commit()

    result = parser_training_service.run_candidate(db_session, job_code)
    assert result["status"] == "trial_failed"

    # Main error must be user-friendly Chinese
    assert "Traceback" not in result["error"]
    assert "openpyxl" not in result["error"]
    assert "InvalidFileException" not in result["error"]
    assert "worker setup error" not in result["error"]
    assert 'File "' not in result["error"]

    # Technical error should preserve original
    assert result.get("technical_error") is not None


# ── 13E: stale trial result cleanup + empty rows + worker crash ──


def test_get_job_cleans_old_raw_traceback(db_session, tmp_path, monkeypatch):
    """get_job cleans old raw Traceback from trial_result_json."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job_code = created["job_code"]

    # Simulate old pre-13D failure result stored in DB
    job = db_session.query(ParserTrainingJob).filter(
        ParserTrainingJob.job_code == job_code
    ).first()
    job.trial_result_json = json.dumps({
        "status": "trial_failed",
        "error": "worker setup error: InvalidFileException: openpyxl does not support the old .xls file format\nTraceback (most recent call last):\n  File \"x.py\", line 83",
        "rows": [],
        "row_count": 0,
    }, ensure_ascii=False)
    job.trial_status = "failed"
    job.status = "trial_failed"
    db_session.commit()

    result = parser_training_service.get_job(db_session, job_code)
    trial = result["trial_result"]
    assert trial is not None

    # Main error must be user-friendly Chinese
    assert "Traceback" not in trial["error"]
    assert "openpyxl" not in trial["error"]
    assert "InvalidFileException" not in trial["error"]
    assert "worker setup error" not in trial["error"]

    # Technical detail preserved
    assert trial.get("technical_error") is not None
    assert "openpyxl" in trial["technical_error"]


def test_get_job_cleans_stale_zero_row_success(db_session):
    """trial_success + 0 rows (pre-13E false success) must be converted to trial_failed."""
    # Directly create a job record without seed data (not needed for get_job)
    job = ParserTrainingJob(
        job_code="pt_stale_test",
        original_filename="test.xlsx",
        sample_file_path="/tmp/fake.xlsx",
        file_hash="abc123",
        format="xlsx",
        format_fingerprint="unknown",
        identity_hints_json="{}",
        context_snapshot_json="{}",
        headers_json="[]",
        sample_rows_json="[]",
        row_count=0,
        candidate_code=None,
        candidate_notes=None,
        trial_result_json=json.dumps({
            "status": "trial_success",
            "error": None,
            "rows": [],
            "row_count": 0,
        }, ensure_ascii=False),
        trial_status="success",
        status="trial_success",
    )
    db_session.add(job)
    db_session.commit()

    result = parser_training_service.get_job(db_session, "pt_stale_test")
    trial = result["trial_result"]
    assert trial["status"] == "trial_failed"
    assert "识别" in trial["error"] or "流水" in trial["error"]
    assert trial["row_count"] == 0
    # Top-level status must also be corrected
    assert result["status"] == "trial_failed"
    assert result["trial_status"] == "failed"


def test_run_parser_trial_syntax_error_returns_error(tmp_path):
    """Syntax error in parser code returns error via service, not success."""
    # Cannot pass broken syntax directly to run_parser_trial because
    # AST guard rejects it first. Test through run_candidate instead.
    pass


def test_run_parser_trial_no_rows_no_error_is_failure(tmp_path):
    """Worker returning zero rows without explicit error must not be success."""
    file_data = _make_sample_xlsx()
    fp = tmp_path / "t.xlsx"
    fp.write_bytes(file_data)

    code = "def parse(wb, ctx): return []"
    rows, err = run_parser_trial(code, str(fp))
    assert err is not None
    assert len(rows) == 0


def test_run_parser_trial_accepts_rows_errors_tuple_when_no_errors(tmp_path):
    """Agent-generated parsers sometimes return (rows, errors); accept it when errors is empty."""
    file_data = _make_sample_xlsx()
    fp = tmp_path / "t.xlsx"
    fp.write_bytes(file_data)

    code = '''
def parse(wb, ctx):
    return ([{
        "business_date": "2026-01-01",
        "summary": "tuple ok",
        "amount_in": 1,
        "amount_out": 0,
        "rolling_balance": 1,
        "entity_code": "",
        "entity_name": "",
        "account_code": "",
        "account_name": "",
        "counterparty": "",
        "state": "正常",
        "source": "网银导入",
    }], [])
'''
    rows, err = run_parser_trial(code, str(fp))
    assert err is None
    assert len(rows) == 1
    assert rows[0]["summary"] == "tuple ok"


def test_run_parser_trial_tuple_errors_is_user_repairable_failure(tmp_path):
    """(rows, errors) with parser errors must fail without the misleading got-list error."""
    file_data = _make_sample_xlsx()
    fp = tmp_path / "t.xlsx"
    fp.write_bytes(file_data)

    code = "def parse(wb, ctx): return [], ['未找到表头行']"
    rows, err = run_parser_trial(code, str(fp))
    assert rows == []
    assert err is not None
    assert "parser returned validation errors" in err
    assert "expected dict" not in err


def test_run_candidate_list_row_error_is_cleaned_for_user(db_session, tmp_path, monkeypatch):
    """A parser returning list rows must not leak row 0/got list as the main UI error."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "DATA_DIR", str(tmp_path))
    _seed_db(db_session)

    file_data = _make_sample_xlsx()
    created = parser_training_service.create_training_job(db_session, file_data, "test.xlsx")
    job_code = created["job_code"]

    code = "def parse(wb, ctx): return [[1, 2, 3]]"
    parser_training_service.update_candidate_code(db_session, job_code, code)
    result = parser_training_service.run_candidate(db_session, job_code)

    assert result["status"] == "trial_failed"
    assert result["rows"] == []
    assert "expected dict" not in result["error"]
    assert "got list" not in result["error"]
    assert "识别方案" in result["error"]
    assert "standard result object" in result["technical_error"]


def test_runtime_exit_error_is_cleaned_for_user():
    """Worker process failures must not become the main user-facing message."""
    user_msg, technical = parser_training_service._clean_error_for_user("识别方案运行进程异常退出，退出码 1")

    assert "退出码" not in user_msg
    assert "识别方案运行失败" in user_msg
    assert "退出码 1" in technical
