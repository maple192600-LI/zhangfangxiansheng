"""Tests for artifact runtime contract.

Verifies:
- run_parser / run_rule raise NotImplementedError (not ValueError)
- Structured exception hierarchy
- Runtime guard behavior
"""
import sys
from pathlib import Path

import pytest

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


# ── Stub behavior ──

def test_run_parser_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="ParserArtifact runtime"):
        run_parser(None, 1, "/tmp/test.xlsx")


def test_run_rule_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="RuleArtifact runtime"):
        run_rule(None, 1, {})


def test_run_parser_does_not_raise_value_error():
    """Must be NotImplementedError, not ValueError."""
    with pytest.raises(NotImplementedError):
        run_parser(None, 1, "/tmp/test.xlsx")


def test_run_rule_does_not_raise_value_error():
    with pytest.raises(NotImplementedError):
        run_rule(None, 1, {})


# ── Exception hierarchy ──

def test_exception_hierarchy_base():
    assert issubclass(ArtifactNotFoundError, ArtifactRuntimeError)
    assert issubclass(ArtifactNotActiveError, ArtifactRuntimeError)
    assert issubclass(PrimitivesViolationError, ArtifactRuntimeError)
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
    """runtime_guard.no_ai_runtime must block urllib.request.urlopen."""
    import urllib.request
    from core.runtime_guard import RuntimeAICallBlocked, no_ai_runtime

    with no_ai_runtime():
        with pytest.raises(RuntimeAICallBlocked):
            urllib.request.urlopen("http://example.com")


def test_no_ai_runtime_restores_after_exit():
    """After exiting context, urlopen should be restored."""
    import urllib.request
    from core.runtime_guard import no_ai_runtime

    original = urllib.request.urlopen
    with no_ai_runtime():
        pass
    assert urllib.request.urlopen is original
