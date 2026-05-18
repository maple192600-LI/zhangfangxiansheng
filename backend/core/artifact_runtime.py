"""Artifact Runtime — deterministic execution of approved artifacts.

ParserArtifact: deterministic parsing of bank/manual Excel files into CANONICAL_12 rows.
RuleArtifact: deterministic template filling from approved rules.

Implementation status:
    run_parser  — implemented (ParserArtifact deterministic runtime).
    run_rule    — contract placeholder only (Phase H1).
"""
from __future__ import annotations

import json
import multiprocessing
import time
import traceback
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator, Optional

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
from sqlalchemy.orm import Session

from core.artifact_ast_guard import PrimitivesViolationError
from core import artifact_sandbox
from core.runtime_guard import no_ai_runtime
from db.tables import ParserArtifact


# ── Structured exception hierarchy ──

class ArtifactRuntimeError(RuntimeError):
    """Base for all artifact runtime errors."""


class ArtifactNotFoundError(ArtifactRuntimeError):
    """Artifact ID does not exist."""


class ArtifactNotActiveError(ArtifactRuntimeError):
    """Artifact exists but status != 'active'."""


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


_SAFE_BUILTINS = {
    k: v for k, v in __builtins__.items()
    if k not in ("open", "eval", "exec", "compile", "breakpoint",
                  "memoryview", "globals", "locals", "vars", "dir")
} if isinstance(__builtins__, dict) else {
    k: getattr(__builtins__, k)
    for k in dir(__builtins__)
    if k not in ("open", "eval", "exec", "compile", "breakpoint",
                 "memoryview", "globals", "locals", "vars", "dir")
    and not k.startswith("__")
}

_POLL_INTERVAL = 0.05


def _worker_main(conn, code_str, file_path, ctx_json, max_output_rows):
    """Worker process: load workbook, exec parser, send rows back via pipe."""
    try:
        from openpyxl import load_workbook as _load_wb
        wb = _load_wb(file_path, data_only=True)
        try:
            ns = {"__builtins__": _SAFE_BUILTINS}
            ctx = json.loads(ctx_json) if ctx_json else {}
            code_obj = compile(code_str, "<parser_artifact_worker>", "exec")

            with no_ai_runtime():
                exec(code_obj, ns)
                parse_fn = ns.get("parse")
                if parse_fn is None or not callable(parse_fn):
                    conn.send(("error", "artifact code must define a callable 'parse(wb, ctx)' function"))
                    conn.close()
                    return
                gen = parse_fn(wb, ctx)
                iterator = iter(gen)
                count = 0
                while count < max_output_rows:
                    try:
                        row = next(iterator)
                    except StopIteration:
                        break
                    if not isinstance(row, dict):
                        conn.send(("error", f"row {count}: expected dict, got {type(row).__name__}"))
                        conn.close()
                        return
                    conn.send(("row", _serialize_row(row)))
                    count += 1
        except ArtifactRuntimeError as e:
            conn.send(("runtime_error", {"artifact_id": e.artifact_id, "msg": str(e), "type": type(e).__name__}))
        except Exception as e:
            conn.send(("error", f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))
        finally:
            wb.close()
    except Exception as e:
        conn.send(("error", f"worker setup error: {type(e).__name__}: {e}\n{traceback.format_exc()}"))
    conn.close()


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Make row JSON-serializable for cross-process transfer."""
    out = dict(row)
    for key in ("amount_in", "amount_out", "rolling_balance"):
        v = out.get(key)
        if isinstance(v, Decimal):
            out[key] = str(v)
    bd = out.get("business_date")
    if isinstance(bd, datetime):
        out["business_date"] = bd.isoformat()
    elif isinstance(bd, date) and not isinstance(bd, datetime):
        out["business_date"] = bd.isoformat()
    return out


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
        Yields dicts, each conforming to CANONICAL_12 schema (C1).

    Raises:
        ArtifactNotFoundError    — artifact_id does not exist
        ArtifactNotActiveError   — artifact exists but status != 'active'
        PrimitivesViolationError — AST scan finds disallowed imports
        ArtifactExecutionError   — artifact code raises during execution
        SandboxTimeoutError      — execution exceeds configured timeout
    """
    if ctx is None:
        ctx = {}

    from core.artifact_ast_guard import validate_artifact_code

    artifact = db.query(ParserArtifact).filter(ParserArtifact.id == artifact_id).first()
    if artifact is None:
        raise ArtifactNotFoundError(f"ParserArtifact id={artifact_id} 不存在")
    if artifact.status != "active":
        raise ArtifactNotActiveError(
            f"ParserArtifact id={artifact_id} status={artifact.status!r}，需要 'active'"
        )

    validate_artifact_code(artifact.code, artifact.id)

    sandbox = artifact_sandbox.get_default_sandbox_config()

    ctx_json = json.dumps(ctx)

    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(
        target=_worker_main,
        args=(child_conn, artifact.code, file_path, ctx_json, sandbox.max_output_rows),
    )
    proc.start()
    child_conn.close()

    rows: list[dict[str, Any]] = []
    timed_out = False
    try:
        deadline = time.monotonic() + sandbox.timeout_seconds

        while True:
            # Drain all available messages from pipe
            while True:
                try:
                    if not parent_conn.poll(_POLL_INTERVAL):
                        break
                    msg_type, payload = parent_conn.recv()
                except (EOFError, BrokenPipeError, OSError):
                    break

                if msg_type == "row":
                    rows.append(payload)
                elif msg_type == "error":
                    _join_worker(proc)
                    raise ArtifactExecutionError(artifact.id, payload)
                elif msg_type == "runtime_error":
                    _join_worker(proc)
                    raise _reconstruct_runtime_error(payload)

            # Worker finished — drain any remaining messages then exit loop
            if not proc.is_alive():
                proc.join(timeout=0)
                # Final drain after worker exited
                while True:
                    try:
                        if not parent_conn.poll(0.01):
                            break
                        msg_type, payload = parent_conn.recv()
                    except (EOFError, BrokenPipeError, OSError):
                        break
                    if msg_type == "row":
                        rows.append(payload)
                    elif msg_type == "error":
                        raise ArtifactExecutionError(artifact.id, payload)
                    elif msg_type == "runtime_error":
                        raise _reconstruct_runtime_error(payload)
                break

            # Check timeout — but only if worker is not producing output
            if time.monotonic() >= deadline:
                timed_out = True
                proc.terminate()
                proc.join(timeout=5)
                raise SandboxTimeoutError(artifact.id, sandbox.timeout_seconds)
    finally:
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)
        parent_conn.close()

    if proc.exitcode != 0 and proc.exitcode is not None and not timed_out:
        if not rows:
            raise ArtifactExecutionError(
                artifact.id,
                f"worker process exited with code {proc.exitcode}"
            )

    for i, row in enumerate(rows):
        yield _coerce_row(artifact.id, row, i)


def _join_worker(proc: multiprocessing.Process) -> None:
    """Wait for worker process to finish after it reported an error."""
    proc.join(timeout=5)
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=5)


def _reconstruct_runtime_error(payload: dict) -> ArtifactRuntimeError:
    """Reconstruct a runtime error from worker-serialized payload."""
    error_type = payload.get("type", "ArtifactRuntimeError")
    msg = payload.get("msg", "")
    artifact_id = payload.get("artifact_id", 0)
    if error_type == "SandboxTimeoutError":
        return SandboxTimeoutError(artifact_id, 60)
    return ArtifactExecutionError(artifact_id, msg)


def _coerce_row(artifact_id: int, row: dict[str, Any], index: int) -> dict[str, Any]:
    out = dict(row)
    for key in ("amount_in", "amount_out", "rolling_balance"):
        v = out.get(key)
        if v is not None and not isinstance(v, Decimal):
            try:
                out[key] = Decimal(str(v))
            except Exception:
                pass
    bd = out.get("business_date")
    if isinstance(bd, datetime):
        out["business_date"] = bd.date()
    elif isinstance(bd, str) and bd:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
            try:
                out["business_date"] = datetime.strptime(bd, fmt).date()
                break
            except ValueError:
                continue
    return out


def run_rule(
    db: Session,
    artifact_id: int,
    ctx: dict[str, Any],
) -> Workbook:
    """Execute an active RuleArtifact to fill a report template.

    Implementation status:
        Contract placeholder only. Phase H1 will deliver the first working executor.

    Raises:
        NotImplementedError always.
    """
    raise NotImplementedError(
        "RuleArtifact runtime 尚未实现。"
        "完整执行器将在后续 Phase H1 中交付。"
    )
