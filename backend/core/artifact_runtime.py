"""Artifact Runtime — deterministic execution of approved artifacts.

ParserArtifact: deterministic parsing of bank/manual Excel files into CANONICAL_12 rows.
RuleArtifact: deterministic template filling from approved rules.

Contract status: run_parser and run_rule are contract placeholders.
Full implementation is a separate task (Phase E / Phase H).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator, Optional

from openpyxl.workbook.workbook import Workbook
from sqlalchemy.orm import Session


# ── Structured exception hierarchy ──

class ArtifactRuntimeError(RuntimeError):
    """Base for all artifact runtime errors."""


class ArtifactNotFoundError(ArtifactRuntimeError):
    """Artifact ID does not exist."""


class ArtifactNotActiveError(ArtifactRuntimeError):
    """Artifact exists but status != 'active'."""


class PrimitivesViolationError(ArtifactRuntimeError):
    """Artifact code imports modules outside the primitives whitelist."""

    def __init__(self, artifact_id: int, disallowed: list[str]) -> None:
        self.artifact_id = artifact_id
        self.disallowed = disallowed
        super().__init__(
            f"Artifact {artifact_id} imports disallowed modules: {disallowed}"
        )


class SandboxTimeoutError(ArtifactRuntimeError):
    """Artifact execution exceeded the time limit."""

    def __init__(self, artifact_id: int, timeout_seconds: int) -> None:
        self.artifact_id = artifact_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Artifact {artifact_id} execution timed out after {timeout_seconds}s"
        )


class ArtifactExecutionError(ArtifactRuntimeError):
    """Artifact code raised an error during execution."""

    def __init__(self, artifact_id: int, detail: str) -> None:
        self.artifact_id = artifact_id
        self.detail = detail
        super().__init__(f"Artifact {artifact_id} execution failed: {detail}")


# ── Execution contracts ──

def run_parser(
    db: Session,
    artifact_id: int,
    file_path: str,
    ctx: Optional[dict[str, Any]] = None,
) -> Iterator[dict[str, Any]]:
    """Execute an active ParserArtifact against an Excel file.

    Input contract:
        db          — SQLAlchemy Session (read/write)
        artifact_id — int, references a ParserArtifact with status='active'
        file_path   — str, absolute path to the Excel file to parse
        ctx         — optional dict with account_code, entity_code, etc.

    Output contract:
        Yields dicts, each conforming to CANONICAL_12 schema (§C1):
            business_date, entity_code, entity_name, account_code, account_name,
            summary, counterparty, amount_in, amount_out, rolling_balance,
            state, source

    Preconditions:
        - artifact.status == 'active'
        - artifact.code passes AST whitelist scan (artifact_ast_guard.validate_artifact_code)
        - file_path points to a readable .xlsx/.xls file

    Runtime constraints:
        - Execution runs inside core.runtime_guard.no_ai_runtime()
        - No LLM / network calls allowed (§C8)
        - Single execution timeout: 60 seconds (artifact_sandbox.DEFAULT_TIMEOUT_SECONDS)
        - Only active artifacts may execute
        - Output rows must conform to db.schemas.ParserRuntimeRow
        - Errors must be returned as structured ArtifactRuntimeError subclasses

    Implementation status:
        Contract placeholder only. Phase E1 will deliver the first working executor.

    Raises:
        ArtifactNotFoundError    — artifact_id does not exist
        ArtifactNotActiveError   — artifact exists but status != 'active'
        PrimitivesViolationError — AST scan finds disallowed imports
        SandboxTimeoutError      — execution exceeds time limit
        ArtifactExecutionError   — artifact code raises during execution
    """
    raise NotImplementedError(
        "ParserArtifact runtime 尚未实现。"
        "完整执行器将在后续 Phase E1 中交付。"
    )


def run_rule(
    db: Session,
    artifact_id: int,
    ctx: dict[str, Any],
) -> Workbook:
    """Execute an active RuleArtifact to fill a report template.

    Input contract:
        db          — SQLAlchemy Session (read/write)
        artifact_id — int, references a RuleArtifact with status='active'
        ctx         — dict with keys:
            period_start   — str (YYYY-MM-DD)
            period_end     — str (YYYY-MM-DD)
            account_code   — str
            template_path  — str, path to the .xlsx template

    Output contract:
        Returns an openpyxl Workbook with all placeholders filled.

    Preconditions:
        - artifact.status == 'active'
        - artifact.placeholder_bindings covers all §TEMPLATE_18 placeholders
        - artifact.code passes AST whitelist scan (artifact_ast_guard.validate_artifact_code)

    Runtime constraints:
        - Same as run_parser (no_ai_runtime, 60s timeout, §C8)
        - Only active artifacts may execute

    Implementation status:
        Contract placeholder only. Phase H1 will deliver the first working executor.

    Raises:
        ArtifactNotFoundError    — artifact_id does not exist
        ArtifactNotActiveError   — artifact exists but status != 'active'
        PrimitivesViolationError — AST scan finds disallowed imports
        SandboxTimeoutError      — execution exceeds time limit
        ArtifactExecutionError   — artifact code raises during execution
    """
    raise NotImplementedError(
        "RuleArtifact runtime 尚未实现。"
        "完整执行器将在后续 Phase H1 中交付。"
    )
