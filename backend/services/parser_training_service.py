"""Parser training service — persistent training jobs, trial runs, and save."""
import hashlib
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from core.artifact_runtime import run_parser_trial
from core.parser_engine import detect_format, detect_header_row, read_file_from_bytes
from db.tables import ParserArtifact, ParserTrainingJob
from services import artifact_service
from services.parser_context_service import build_bank_parser_context

_UPLOAD_DIR_NAME = "parser_training_samples"
_MAX_CONTEXT_SAMPLE_ROWS = 80

_BLOCKED_CODE_PATTERNS = [
    "DEFAULT_ACCOUNT_CODE",
    "DEFAULT_ENTITY_CODE",
    "default_account",
    "default_entity",
]


def _upload_dir() -> str:
    from config import DATA_DIR
    d = os.path.join(DATA_DIR, _UPLOAD_DIR_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def _check_hardcoding(code: str) -> Optional[str]:
    """Check code for hardcoded account/entity patterns. Returns error or None."""
    code_upper = code.upper()
    for pat in _BLOCKED_CODE_PATTERNS:
        if pat.upper() in code_upper:
            return f"parser 代码中不允许硬编码默认账户/单位: 发现 '{pat}'"
    return None


def create_training_job(db: Session, file_data: bytes, filename: str) -> Dict[str, Any]:
    """Create a persistent training job from uploaded sample file."""
    fmt = detect_format(filename)
    if fmt == "unknown":
        raise ValueError("不支持的文件格式，仅支持 xls/xlsx/csv")

    try:
        rows = read_file_from_bytes(file_data, filename, fmt)
    except Exception as exc:
        raise ValueError(f"样本文件读取失败，请确认文件未损坏或另存为 xlsx 后重试") from exc
    if len(rows) < 2:
        raise ValueError("文件内容为空或行数不足")

    file_summary = _build_training_file_summary(rows, filename)

    job_code = f"pt_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(_upload_dir(), f"{job_code}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_data)

    file_hash = hashlib.sha256(file_data).hexdigest()

    context = build_bank_parser_context(db)

    job = ParserTrainingJob(
        job_code=job_code,
        original_filename=filename,
        sample_file_path=file_path,
        file_hash=file_hash,
        format=fmt,
        format_fingerprint=file_summary["format_fingerprint"],
        identity_hints_json=json.dumps(file_summary["identity_hints"], ensure_ascii=False),
        context_snapshot_json=json.dumps(context, ensure_ascii=False),
        headers_json=json.dumps(file_summary["headers"], ensure_ascii=False),
        sample_rows_json=json.dumps(file_summary["sample_rows"], ensure_ascii=False),
        row_count=file_summary["row_count"],
        candidate_code=None,
        candidate_notes=None,
        trial_result_json=None,
        trial_status="pending",
        status="sample_uploaded",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return _job_to_response(job)


def _build_training_file_summary(rows: list[list[Any]], filename: str) -> Dict[str, Any]:
    """Build the file context used by both the UI and the agent starter prompt.

    The context is based on the detected header row plus representative data rows
    distributed across the whole file. This avoids teaching the agent from only
    the first few transactions while keeping the prompt bounded.
    """
    header_idx = detect_header_row(rows)
    headers = [str(h).strip() for h in rows[header_idx] if h and str(h).strip()]
    width = len(headers)
    data_rows = [
        row
        for row in rows[header_idx + 1:]
        if any(c and str(c).strip() for c in row)
    ]
    sample_rows = [
        _format_sample_row(data_rows[i], width)
        for i in _distributed_sample_indices(len(data_rows), _MAX_CONTEXT_SAMPLE_ROWS)
    ]

    from services.bank_statement_identity_service import extract_identity_hints_from_rows
    identity_hints = extract_identity_hints_from_rows(rows, filename)
    identity_hints.update({
        "detected_header_row": header_idx + 1,
        "data_row_count": len(data_rows),
        "sample_row_count": len(sample_rows),
        "sample_strategy": "distributed_across_detected_body",
    })

    return {
        "headers": headers,
        "sample_rows": sample_rows,
        "row_count": len(data_rows),
        "identity_hints": identity_hints,
        "format_fingerprint": identity_hints.get("format_fingerprint", "unknown"),
    }


def _distributed_sample_indices(total: int, limit: int) -> list[int]:
    if total <= 0:
        return []
    if total <= limit:
        return list(range(total))
    if limit <= 1:
        return [0]

    indices = {
        round(i * (total - 1) / (limit - 1))
        for i in range(limit)
    }
    return sorted(indices)


def _format_sample_row(row: list[Any], width: int) -> list[str]:
    cells = [str(c).strip() if c is not None else "" for c in row[:width]]
    if len(cells) < width:
        cells.extend([""] * (width - len(cells)))
    return cells


def get_job(db: Session, job_code: str) -> Optional[Dict[str, Any]]:
    """Get a training job by job_code."""
    job = db.query(ParserTrainingJob).filter(ParserTrainingJob.job_code == job_code).first()
    if not job:
        return None
    return _job_to_response(job)


def _clean_error_for_user(raw_error: str) -> tuple[str, str]:
    """Split a raw error into (user_message, technical_detail).

    User message is always a short Chinese business prompt.
    Technical detail preserves the original error for debugging.
    """
    technical_indicators = ("Traceback", "openpyxl", "InvalidFileException",
                            "worker setup error", "File \"", "SyntaxError",
                            "IndentationError", "NameError", "TypeError",
                            "ValueError", "AttributeError", "KeyError",
                            "IndexError", "ZeroDivisionError", "ImportError",
                            "expected dict", "got list",
                            "must be a standard result object",
                            "parser returned validation errors",
                            "artifact code must define",
                            "运行进程异常退出", "退出码",
                            "worker process exited", "exit code")

    is_technical = any(indicator in raw_error for indicator in technical_indicators)

    if is_technical:
        if "worker setup error" in raw_error or "openpyxl" in raw_error:
            user_msg = "样本文件读取失败，无法生成识别结果。请重新上传样本，或继续让智能体调整识别方案。"
        elif ("expected dict" in raw_error or "got list" in raw_error
              or "standard result object" in raw_error
              or "parser returned validation errors" in raw_error):
            user_msg = "这版识别方案还没有生成可审核的流水结果表，请继续告诉智能体识别结果哪里不对，让它重新调整。"
        elif ("运行进程异常退出" in raw_error or "退出码" in raw_error
              or "worker process exited" in raw_error or "exit code" in raw_error):
            user_msg = "这版识别方案运行失败，请继续告诉智能体识别结果哪里不对，让它重新调整。"
        else:
            user_msg = "这版识别方案还没有成功生成结果，请继续告诉智能体样本哪里识别错了。"
        return user_msg, raw_error

    return raw_error, ""


def run_candidate(db: Session, job_code: str) -> Dict[str, Any]:
    """Trial-run candidate parser code from the job's saved candidate_code."""
    job = db.query(ParserTrainingJob).filter(ParserTrainingJob.job_code == job_code).first()
    if not job:
        return {"status": "error", "error": f"训练任务 {job_code} 不存在"}

    if not job.candidate_code:
        return {"status": "error", "error": "候选规则为空，请先让智能体生成候选规则"}

    # Verify sample file is in controlled directory
    upload_dir = _upload_dir()
    if not os.path.abspath(job.sample_file_path).startswith(os.path.abspath(upload_dir)):
        return {"status": "error", "error": "样本文件路径不在受控目录"}

    try:
        rows, error_msg = run_parser_trial(job.candidate_code, job.sample_file_path)
    except Exception as exc:
        raw_error = str(exc)
        user_msg, tech_detail = _clean_error_for_user(raw_error)
        job.trial_status = "failed"
        job.trial_result_json = json.dumps(
            {"status": "trial_failed", "error": user_msg,
             "technical_error": tech_detail or raw_error,
             "rows": [], "row_count": 0},
            ensure_ascii=False,
        )
        job.status = "trial_failed"
        db.commit()
        return {"status": "trial_failed", "rows": [], "row_count": 0,
                "error": user_msg, "technical_error": tech_detail or raw_error}

    if error_msg:
        user_msg, tech_detail = _clean_error_for_user(error_msg)
        job.trial_status = "failed"
        job.trial_result_json = json.dumps(
            {"status": "trial_failed", "error": user_msg,
             "technical_error": tech_detail or error_msg,
             "rows": [], "row_count": 0},
            ensure_ascii=False,
        )
        job.status = "trial_failed"
        db.commit()
        return {"status": "trial_failed", "rows": [], "row_count": 0,
                "error": user_msg, "technical_error": tech_detail or error_msg}

    if not rows:
        result = {
            "status": "trial_failed",
            "rows": [],
            "row_count": 0,
            "error": "这版识别方案没有识别出任何流水，请继续告诉智能体样本哪里识别错了。",
            "technical_error": "parser returned zero rows",
        }
        job.trial_status = "failed"
        job.trial_result_json = json.dumps(result, ensure_ascii=False)
        job.status = "trial_failed"
        db.commit()
        return result

    result = {"status": "trial_success", "rows": rows, "row_count": len(rows),
              "error": None, "technical_error": None}
    job.trial_status = "success"
    job.trial_result_json = json.dumps(result, ensure_ascii=False, default=str)
    job.status = "trial_success"
    db.commit()
    return result


def save_parser(db: Session, job_code: str, name: str) -> Dict[str, Any]:
    """Save candidate code from the training job as active ParserArtifact."""
    job = db.query(ParserTrainingJob).filter(ParserTrainingJob.job_code == job_code).first()
    if not job:
        raise ValueError(f"训练任务 {job_code} 不存在")

    if not job.candidate_code:
        raise ValueError("候选规则为空，无法保存")

    if job.trial_status != "success":
        raise ValueError("候选规则未通过试运行，无法保存。请先试运行并确认结果正确。")

    hardcoding_err = _check_hardcoding(job.candidate_code)
    if hardcoding_err:
        raise ValueError(f"候选规则包含硬编码违规: {hardcoding_err}")

    from core.artifact_ast_guard import validate_artifact_code
    try:
        validate_artifact_code(job.candidate_code, artifact_id=0)
    except Exception as e:
        raise ValueError(f"AST 安全检查失败: {e}")

    from db.schemas import ParserArtifactDraftCreate

    identity_hints = json.loads(job.identity_hints_json) if job.identity_hints_json else {}
    bank_id = _resolve_parser_bank_id(db, identity_hints)
    format_key = _normalize_parser_format_key(job.format_fingerprint)

    draft_data = ParserArtifactDraftCreate(
        name=name,
        kind="bank",
        bank_id=bank_id,
        format_key=format_key,
        match_rules={},
        code=job.candidate_code,
        primitives_imports=[],
        sample_check_log={"job_code": job_code, "trial_status": job.trial_status},
        confidence=0.8,
        created_by="rule_center",
    )
    draft = artifact_service.create_parser_draft(db, draft_data)
    result = artifact_service.approve_parser_artifact(db, draft["id"], approver="rule_center")

    job.status = "active_parser_saved"
    job.parser_artifact_id = draft["id"]
    db.commit()

    return result


def _resolve_parser_bank_id(db: Session, identity_hints: dict[str, Any]) -> Optional[int]:
    """Resolve parser ownership to a bank when the sample contains a unique bank hint."""
    from services.bank_account_match_service import resolve_bank_from_hints

    bank_resolution = resolve_bank_from_hints(db, identity_hints)
    if bank_resolution.get("status") == "matched":
        return bank_resolution.get("bank_id")
    return None


def _normalize_parser_format_key(format_key: Optional[str]) -> Optional[str]:
    if not format_key or format_key == "unknown":
        return None
    return format_key


def update_candidate_code(db: Session, job_code: str, code: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """Agent tool entry: write candidate code into the training job."""
    job = db.query(ParserTrainingJob).filter(ParserTrainingJob.job_code == job_code).first()
    if not job:
        return {"ok": False, "error": f"训练任务 {job_code} 不存在"}

    hardcoding_err = _check_hardcoding(code)
    if hardcoding_err:
        return {"ok": False, "error": hardcoding_err}

    from core.artifact_ast_guard import validate_artifact_code
    try:
        validate_artifact_code(code, artifact_id=0)
    except Exception as e:
        return {"ok": False, "error": f"AST 安全检查失败: {e}"}

    job.candidate_code = code
    job.candidate_notes = notes
    job.trial_status = "pending"
    job.trial_result_json = None
    job.status = "candidate_ready"
    db.commit()

    return {"ok": True, "job_code": job_code, "status": "candidate_ready"}


def _job_to_response(job: ParserTrainingJob) -> Dict[str, Any]:
    trial_result = _normalize_trial_result_for_response(job.trial_result_json)
    status = job.status
    trial_status = job.trial_status
    headers = json.loads(job.headers_json) if job.headers_json else []
    sample_rows = json.loads(job.sample_rows_json) if job.sample_rows_json else []
    identity_hints = json.loads(job.identity_hints_json) if job.identity_hints_json else {}
    row_count = job.row_count

    refreshed_summary = _try_build_summary_from_sample_file(job)
    if refreshed_summary:
        headers = refreshed_summary["headers"]
        sample_rows = refreshed_summary["sample_rows"]
        identity_hints = refreshed_summary["identity_hints"]
        row_count = refreshed_summary["row_count"]

    if trial_result and trial_result.get("status") == "trial_failed":
        if status == "trial_success":
            status = "trial_failed"
        if trial_status == "success":
            trial_status = "failed"
    return {
        "job_code": job.job_code,
        "filename": job.original_filename,
        "format": job.format,
        "row_count": row_count,
        "headers": headers,
        "sample_rows": sample_rows,
        "identity_hints": identity_hints,
        "format_fingerprint": job.format_fingerprint,
        "context": json.loads(job.context_snapshot_json) if job.context_snapshot_json else {},
        "status": status,
        "trial_status": trial_status,
        "candidate_code": job.candidate_code,
        "trial_result": trial_result,
        "parser_artifact_id": job.parser_artifact_id,
        "agent_id": job.agent_id,
        "agent_session_id": job.agent_session_id,
    }


def _try_build_summary_from_sample_file(job: ParserTrainingJob) -> Optional[Dict[str, Any]]:
    """Refresh sample context for old jobs that stored only a tiny row slice."""
    if not job.sample_file_path or not os.path.exists(job.sample_file_path):
        return None
    try:
        with open(job.sample_file_path, "rb") as f:
            file_data = f.read()
        fmt = job.format or detect_format(job.original_filename)
        rows = read_file_from_bytes(file_data, job.original_filename, fmt)
        return _build_training_file_summary(rows, job.original_filename)
    except Exception:
        return None


def _normalize_trial_result_for_response(raw_json: Optional[str]) -> Optional[Dict[str, Any]]:
    """Clean trial_result_json before returning to frontend.

    Ensures old raw Traceback/error messages are converted to user-friendly
    Chinese prompts, with technical details moved to technical_error field.
    """
    if not raw_json:
        return None
    try:
        result = json.loads(raw_json)
    except Exception:
        return {
            "status": "trial_failed",
            "error": "历史识别结果读取失败，请重新生成识别结果。",
            "technical_error": raw_json,
            "rows": [],
            "row_count": 0,
        }

    # Fix stale trial_success with 0 rows (pre-13E false success)
    rows = result.get("rows") or []
    if result.get("status") == "trial_success" and len(rows) == 0:
        result["status"] = "trial_failed"
        result["error"] = "这版识别方案没有识别出任何流水，请继续告诉智能体样本哪里识别错了。"
        result["technical_error"] = result.get("technical_error") or "parser returned zero rows"

    err = result.get("error")
    if isinstance(err, str) and err:
        user_msg, technical = _clean_error_for_user(err)
        result["error"] = user_msg
        if technical and not result.get("technical_error"):
            result["technical_error"] = technical

    return result
