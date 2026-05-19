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

    header_idx = detect_header_row(rows)
    headers = [h.strip() for h in rows[header_idx] if h and h.strip()]
    sample_rows = [
        [str(c).strip() if c else "" for c in row[:len(headers)]]
        for row in rows[header_idx + 1:header_idx + 6]
        if any(c and str(c).strip() for c in row)
    ]

    job_code = f"pt_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(_upload_dir(), f"{job_code}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_data)

    file_hash = hashlib.sha256(file_data).hexdigest()

    from services.bank_statement_identity_service import extract_identity_hints_from_rows
    identity_hints = extract_identity_hints_from_rows(rows, filename)
    format_fingerprint = identity_hints.get("format_fingerprint", "unknown")

    context = build_bank_parser_context(db)

    job = ParserTrainingJob(
        job_code=job_code,
        original_filename=filename,
        sample_file_path=file_path,
        file_hash=file_hash,
        format=fmt,
        format_fingerprint=format_fingerprint,
        identity_hints_json=json.dumps(identity_hints, ensure_ascii=False),
        context_snapshot_json=json.dumps(context, ensure_ascii=False),
        headers_json=json.dumps(headers, ensure_ascii=False),
        sample_rows_json=json.dumps(sample_rows, ensure_ascii=False),
        row_count=len(rows) - header_idx - 1,
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


def get_job(db: Session, job_code: str) -> Optional[Dict[str, Any]]:
    """Get a training job by job_code."""
    job = db.query(ParserTrainingJob).filter(ParserTrainingJob.job_code == job_code).first()
    if not job:
        return None
    return _job_to_response(job)


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
        job.trial_status = "failed"
        job.trial_result_json = json.dumps(
            {"status": "trial_failed", "error": str(exc), "rows": [], "row_count": 0},
            ensure_ascii=False,
        )
        job.status = "trial_failed"
        db.commit()
        return {"status": "trial_failed", "rows": [], "row_count": 0, "error": str(exc)}

    if error_msg:
        job.trial_status = "failed"
        job.trial_result_json = json.dumps(
            {"status": "trial_failed", "error": error_msg, "rows": [], "row_count": 0},
            ensure_ascii=False,
        )
        job.status = "trial_failed"
        db.commit()
        return {"status": "trial_failed", "rows": [], "row_count": 0, "error": error_msg}

    result = {"status": "trial_success", "rows": rows, "row_count": len(rows), "error": None}
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
    bank_id = identity_hints.get("bank_id")
    format_key = job.format_fingerprint

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
    return {
        "job_code": job.job_code,
        "filename": job.original_filename,
        "format": job.format,
        "row_count": job.row_count,
        "headers": json.loads(job.headers_json) if job.headers_json else [],
        "sample_rows": json.loads(job.sample_rows_json) if job.sample_rows_json else [],
        "identity_hints": json.loads(job.identity_hints_json) if job.identity_hints_json else {},
        "format_fingerprint": job.format_fingerprint,
        "context": json.loads(job.context_snapshot_json) if job.context_snapshot_json else {},
        "status": job.status,
        "trial_status": job.trial_status,
        "candidate_code": job.candidate_code,
        "trial_result": json.loads(job.trial_result_json) if job.trial_result_json else None,
        "parser_artifact_id": job.parser_artifact_id,
        "agent_id": job.agent_id,
        "agent_session_id": job.agent_session_id,
    }
