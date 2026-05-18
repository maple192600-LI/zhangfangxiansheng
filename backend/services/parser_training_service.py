"""Parser training service — manages training jobs, trial runs, and save."""
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from core.artifact_runtime import run_parser_trial
from core.parser_engine import detect_format, detect_header_row, read_file_from_bytes
from db.tables import ParserArtifact
from services import artifact_service
from services.parser_context_service import build_bank_parser_context


_UPLOAD_DIR_NAME = "parser_training_samples"


def _upload_dir() -> str:
    from config import DATA_DIR
    d = os.path.join(DATA_DIR, _UPLOAD_DIR_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def create_training_job(db: Session, file_data: bytes, filename: str) -> Dict[str, Any]:
    """Create a training job from uploaded sample file."""
    fmt = detect_format(filename)
    if fmt == "unknown":
        raise ValueError("不支持的文件格式，仅支持 xls/xlsx/csv")

    rows = read_file_from_bytes(file_data, filename, fmt)
    if len(rows) < 2:
        raise ValueError("文件内容为空或行数不足")

    header_idx = detect_header_row(rows)
    headers = [h.strip() for h in rows[header_idx] if h and h.strip()]
    sample_rows = [
        [str(c).strip() if c else "" for c in row[:len(headers)]]
        for row in rows[header_idx + 1:header_idx + 6]
        if any(c and str(c).strip() for c in row)
    ]

    job_id = f"pt_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(_upload_dir(), f"{job_id}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_data)

    from services.bank_statement_identity_service import extract_identity_hints
    identity_hints = extract_identity_hints(file_path, filename)
    format_fingerprint = identity_hints.get("format_fingerprint", "unknown")
    bank_text_candidates = identity_hints.get("bank_text_candidates", [])

    context = build_bank_parser_context(db)

    return {
        "job_id": job_id,
        "filename": filename,
        "file_path": file_path,
        "format": fmt,
        "row_count": len(rows) - header_idx - 1,
        "headers": headers,
        "sample_rows": sample_rows,
        "identity_hints": identity_hints,
        "format_fingerprint": format_fingerprint,
        "bank_text_candidates": bank_text_candidates,
        "context": context,
        "status": "sample_uploaded",
        "candidate_code": None,
        "trial_result": None,
        "trial_error": None,
    }


def run_candidate(file_path: str, code: str) -> Dict[str, Any]:
    """Trial-run candidate parser code and return results."""
    rows, error_msg = run_parser_trial(code, file_path)

    if error_msg:
        return {
            "status": "trial_failed",
            "rows": [],
            "row_count": 0,
            "error": error_msg,
        }

    return {
        "status": "trial_success",
        "rows": rows,
        "row_count": len(rows),
        "error": None,
    }


def save_parser(
    db: Session,
    name: str,
    code: str,
    bank_id: Optional[int],
    format_key: Optional[str],
    match_rules: Dict,
    sample_check_log: Dict,
    confidence: Optional[float],
    primitives_imports: list,
) -> Dict[str, Any]:
    """Save candidate as draft ParserArtifact and approve to active."""
    from db.schemas import ParserArtifactDraftCreate

    draft_data = ParserArtifactDraftCreate(
        name=name,
        kind="bank",
        bank_id=bank_id,
        format_key=format_key,
        match_rules=match_rules,
        code=code,
        primitives_imports=primitives_imports,
        sample_check_log=sample_check_log,
        confidence=confidence,
        created_by="rule_center",
    )
    draft = artifact_service.create_parser_draft(db, draft_data)
    result = artifact_service.approve_parser_artifact(db, draft["id"], approver="rule_center")
    return result
