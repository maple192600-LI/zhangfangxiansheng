"""SourceFile 服务 — 文件处理记录管理

每次上传到系统的文件都会创建一条 SourceFile 记录，
跟踪文件状态、hash、parser 匹配、处理结果。
"""
import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from db.tables import ImportBatch, SourceFile


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def create_source_file_for_upload(
    db: Session,
    batch: ImportBatch,
    file_path: str,
    original_filename: str,
    file_bytes: bytes,
    context: Optional[dict] = None,
) -> SourceFile:
    file_hash = compute_file_hash(file_bytes)
    sf = SourceFile(
        batch_id=batch.id,
        original_filename=original_filename,
        storage_path=file_path,
        file_hash=file_hash,
        file_size=len(file_bytes),
        status="uploaded",
    )
    if context:
        sf.format_fingerprint = context.get("format_fingerprint")
        parser_match = context.get("parser_match", {})
        if parser_match.get("matched"):
            sf.parser_artifact_id = parser_match.get("parser_artifact_id")
    db.add(sf)
    db.flush()
    return sf


def update_source_file_status(
    db: Session,
    source_file: SourceFile,
    status: str,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    parser_artifact_id: Optional[int] = None,
    format_fingerprint: Optional[str] = None,
    clear_error: bool = False,
) -> SourceFile:
    source_file.status = status
    source_file.updated_at = datetime.now()
    if clear_error:
        source_file.error_code = None
        source_file.error_message = None
    else:
        if error_code is not None:
            source_file.error_code = error_code
        if error_message is not None:
            source_file.error_message = error_message
    if parser_artifact_id is not None:
        source_file.parser_artifact_id = parser_artifact_id
    if format_fingerprint is not None:
        source_file.format_fingerprint = format_fingerprint
    db.flush()
    return source_file


def get_source_files_for_batch(db: Session, batch_id: int) -> list:
    return db.query(SourceFile).filter(SourceFile.batch_id == batch_id).all()


def get_first_source_file_for_batch(db: Session, batch_id: int) -> Optional[SourceFile]:
    return db.query(SourceFile).filter(SourceFile.batch_id == batch_id).first()


def resolve_source_file_status(
    parser_matched: bool,
    account_status: str,
    parse_error: bool = False,
) -> str:
    if parse_error:
        return "failed"
    if not parser_matched:
        return "needs_rule"
    if account_status == "matched":
        return "ready"
    if account_status in ("ambiguous", "conflict"):
        return "needs_account"
    if account_status == "unmatched":
        return "needs_account"
    return "parsed"
