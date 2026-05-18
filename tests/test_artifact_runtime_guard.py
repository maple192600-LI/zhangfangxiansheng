"""Tests for artifact runtime guard rails.

Verifies:
- run_rule still raises NotImplementedError
- artifact_runtime does not import FundAgent or fund_skill_run
- artifact_ast_guard is importable and functional
- artifact_sandbox config is defined
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── run_rule still NotImplementedError ──

def test_run_rule_still_not_implemented():
    from core.artifact_runtime import run_rule
    with pytest.raises(NotImplementedError, match="Phase H1"):
        run_rule(None, 1, {})


# ── No FundAgent dependency ──

def test_artifact_runtime_no_fundagent_import():
    import core.artifact_runtime as mod
    src = open(mod.__file__, encoding="utf-8").read()
    assert "FundAgent" not in src
    assert "fund_skill_run" not in src
    assert "agents.fund" not in src


def test_artifact_ast_guard_no_fundagent_import():
    import core.artifact_ast_guard as mod
    src = open(mod.__file__, encoding="utf-8").read()
    assert "FundAgent" not in src
    assert "fund_skill_run" not in src


def test_artifact_sandbox_no_fundagent_import():
    import core.artifact_sandbox as mod
    src = open(mod.__file__, encoding="utf-8").read()
    assert "FundAgent" not in src
    assert "fund_skill_run" not in src


# ── AST guard module available ──

def test_validate_artifact_code_callable():
    from core.artifact_ast_guard import validate_artifact_code
    assert callable(validate_artifact_code)


def test_explain_sandbox_policy_returns_dict():
    from core.artifact_ast_guard import explain_sandbox_policy
    policy = explain_sandbox_policy()
    assert isinstance(policy, dict)
    assert "allowed_module_prefixes" in policy
    assert "blocked_import_modules" in policy
    assert "blocked_builtins" in policy
    assert "timeout_seconds" in policy


# ── Sandbox config ──

def test_sandbox_config_defaults():
    from core.artifact_sandbox import get_default_sandbox_config
    cfg = get_default_sandbox_config()
    assert cfg.timeout_seconds == 60
    assert cfg.max_output_rows == 50_000
    assert "fund.primitives." in cfg.allowed_module_prefixes
    assert "os" in cfg.blocked_import_modules


# ── Runtime Schema exists ──

def test_parser_runtime_schema():
    from db.schemas import ParserRuntimeInput, ParserRuntimeResult, ParserRuntimeRow
    row = ParserRuntimeRow(business_date="2026-01-01", entity_code="E001", account_code="A001")
    assert row.state == "正常"
    inp = ParserRuntimeInput(artifact_id=1, file_path="/tmp/x.xlsx")
    assert inp.ctx == {}
    res = ParserRuntimeResult(rows=[row], row_count=1)
    assert res.row_count == 1


def test_rule_runtime_schema():
    from db.schemas import RuleRuntimeInput, RuleRuntimeResult
    inp = RuleRuntimeInput(artifact_id=1, template_path="/tmp/tpl.xlsx")
    assert inp.ctx == {}
    res = RuleRuntimeResult(output_path="/tmp/out.xlsx", placeholder_filled=18)
    assert res.placeholder_filled == 18


# ── no_ai_runtime still works ──

def test_no_ai_runtime_still_blocks():
    import urllib.request
    from core.runtime_guard import RuntimeAICallBlocked, no_ai_runtime
    with no_ai_runtime():
        with pytest.raises(RuntimeAICallBlocked):
            urllib.request.urlopen("http://example.com")
