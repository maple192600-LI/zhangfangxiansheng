"""银行流水导入服务层

上传 → ParserArtifact 匹配 → 解析预览。
最终提交由 import_preview_service 统一完成。
"""
import os
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core import artifact_runtime
from core.parser_engine import detect_format, detect_header_row, read_file_from_bytes
from db.tables import FundEvent, ImportBatch, ParserArtifact
from config import DATA_DIR
from services import log_service
from services.bank_statement_identity_service import extract_identity_hints
from services.bank_account_match_service import match_account_attribution, resolve_bank_from_hints
from services.source_file_service import (
    create_source_file_for_upload,
    update_source_file_status,
    resolve_source_file_status,
)
from services.account_resolution_audit_service import record_account_resolution_attempt


# ──────────────────────────────────────────
# 上传
# ──────────────────────────────────────────

def _fix_filename(filename: str) -> str:
    """修复 multipart 上传中文文件名编码问题。

    浏览器发送 UTF-8 编码的 filename，但 HTTP multipart 头部按 latin-1 解码，
    导致中文变成乱码。通过反向操作恢复：encode('latin-1') → decode('utf-8')。
    """
    if not filename:
        return filename
    # 纯 ASCII 不需要修复
    try:
        filename.encode("ascii")
        return filename
    except UnicodeEncodeError:
        pass
    # 尝试 latin-1 → UTF-8 反向修复
    try:
        raw_bytes = filename.encode("latin-1")
        decoded = raw_bytes.decode("utf-8")
        # 如果解码成功且包含中文字符，说明修复成功
        if any("一" <= c <= "鿿" for c in decoded):
            return decoded
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return filename


def upload_file(db: Session, file_data: bytes, filename: str) -> Dict[str, Any]:
    filename = _fix_filename(filename)
    fmt = detect_format(filename)
    if fmt == "unknown":
        raise ValueError("不支持的文件格式，仅支持 xls/xlsx/csv")

    # 读取原始行
    rows = read_file_from_bytes(file_data, filename, fmt)
    if len(rows) < 2:
        raise ValueError("文件内容为空或行数不足")

    # 检测表头
    header_idx = detect_header_row(rows)
    headers = [h.strip() for h in rows[header_idx] if h and h.strip()]
    sample_rows = [
        [str(c).strip() if c else "" for c in row[:len(headers)]]
        for row in rows[header_idx + 1:header_idx + 6]
        if any(c and str(c).strip() for c in row)
    ]

    # 保存文件（先保存，identity extraction 需要 file_path）
    os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
    batch_code = f"BANK_{date.today().strftime('%Y%m%d')}_{uuid.uuid4().hex[:4].upper()}"
    file_path = os.path.join(DATA_DIR, "uploads", f"{batch_code}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_data)

    # 身份线索提取 + 银行解析 + 账户归属 + parser 匹配
    context = build_bank_import_context(db, file_path, filename)
    identity_hints = context["identity_hints"]
    bank_resolution = context["bank_resolution"]
    account_attribution = context["account_attribution"]
    format_key = context["format_fingerprint"]
    parser_match = context["parser_match"]

    # 创建批次
    batch = ImportBatch(
        batch_code=batch_code,
        source_type="bank",
        source_name=filename,
        status="uploaded",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # 创建 SourceFile 记录
    source_file = create_source_file_for_upload(
        db, batch, file_path, filename, file_data, context=context,
    )

    # 更新 SourceFile 状态
    sf_status = resolve_source_file_status(
        parser_matched=parser_match.get("matched", False),
        account_status=account_attribution.get("status", "unmatched"),
    )
    update_source_file_status(
        db, source_file, status=sf_status,
        parser_artifact_id=parser_match.get("parser_artifact_id"),
        format_fingerprint=format_key,
    )

    # 记录账户归属判断和证据
    record_account_resolution_attempt(
        db, source_file, account_attribution,
        identity_hints=identity_hints,
        bank_resolution=bank_resolution,
    )
    db.commit()

    result: Dict[str, Any] = {
        "batch_code": batch_code,
        "batch_id": batch.id,
        "file_name": filename,
        "detected_format": fmt,
        "row_count": len(rows) - header_idx - 1,
        "headers": headers,
        "sample_rows": sample_rows,
        "header_row": header_idx,
        "identity_hints": identity_hints,
        "bank_resolution": bank_resolution,
        "account_attribution": account_attribution,
        "format_fingerprint": format_key,
        "parser_match": parser_match,
        "source_file_id": source_file.id,
        "source_file_status": source_file.status,
    }

    log_service.write_log(db, action="batch_upload", module="bank_import", detail={
        "batch_code": batch_code, "filename": filename, "rows": len(rows) - header_idx - 1,
        "source_file_id": source_file.id, "source_file_status": sf_status,
    }, batch_id=batch.id)
    return result


# ──────────────────────────────────────────
# 预览
# ──────────────────────────────────────────

def preview(
    db: Session,
    batch_code: str,
    parser_artifact_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not parser_artifact_id:
        raise ValueError("缺少 ParserArtifact，请先匹配或创建解析器")

    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")

    filename = batch.source_name or ""
    file_path = _find_uploaded_file(batch_code, filename)
    if not file_path:
        raise ValueError("原始文件未找到")

    # Re-extract identity hints for ctx enrichment
    identity_hints = extract_identity_hints(file_path, filename)
    bank_resolution = resolve_bank_from_hints(db, identity_hints)
    account_attribution = match_account_attribution(db, identity_hints)

    ctx = {
        "batch_code": batch_code,
        "bank_resolution": bank_resolution,
        "account_attribution": account_attribution,
    }

    try:
        rows = list(
            artifact_runtime.run_parser(db, parser_artifact_id, file_path, ctx),
        )
    except artifact_runtime.ArtifactRuntimeError as e:
        raise ValueError(str(e))
    result = _preview_from_canonical_rows(batch_code, rows)
    batch.status = "previewed"
    db.commit()
    return result


# ──────────────────────────────────────────
# 确认提交
# ──────────────────────────────────────────

def commit(db: Session, batch_code: str, parser_artifact_id: int) -> Dict[str, Any]:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")
    file_path = _find_uploaded_file(batch_code, batch.source_name or "")
    if not file_path:
        raise ValueError("原始上传文件未找到")

    db.query(FundEvent).filter(FundEvent.batch_id == batch.id).delete()
    rows = list(
        artifact_runtime.run_parser(
            db,
            parser_artifact_id,
            file_path,
            {"batch_code": batch_code},
        )
    )
    for row in rows:
        db.add(FundEvent(**row, batch_id=batch.id, parser_artifact_id=parser_artifact_id))
    batch.status = "committed"
    batch.updated_at = datetime.now()
    db.commit()

    log_service.write_log(
        db,
        action="batch_commit",
        module="bank_import",
        detail={
            "batch_code": batch_code,
            "parser_artifact_id": parser_artifact_id,
            "inserted_rows": len(rows),
        },
        batch_id=batch.id,
    )
    return {
        "batch_code": batch_code,
        "parser_artifact_id": parser_artifact_id,
        "inserted_rows": len(rows),
    }


# ──────────────────────────────────────────
# 内部辅助
# ──────────────────────────────────────────

def _match_bank_format_parser_artifact(
    db: Session,
    bank_resolution: Dict[str, Any],
    format_key: str,
) -> Dict[str, Any]:
    """Match parser by bank/format priority. Returns structured result."""
    bank_id = bank_resolution.get("bank_id")
    bank_status = bank_resolution.get("status", "unresolved")

    base_q = db.query(ParserArtifact).filter(
        ParserArtifact.kind == "bank",
        ParserArtifact.status == "active",
    )

    # Level 1: bank_id + format_key
    if bank_id is not None:
        arts = base_q.filter(
            ParserArtifact.bank_id == bank_id,
            ParserArtifact.format_key == format_key,
        ).all()
        if len(arts) == 1:
            return _parser_match_out(arts[0], "bank_format", bank_id, format_key)
        if len(arts) > 1:
            return _parser_conflict(arts, bank_id, format_key)

    # Level 2: bank_id + format_key IS NULL (bank default)
    if bank_id is not None:
        arts = base_q.filter(
            ParserArtifact.bank_id == bank_id,
            ParserArtifact.format_key.is_(None),
        ).all()
        if len(arts) == 1:
            return _parser_match_out(arts[0], "bank_default", bank_id, None)
        if len(arts) > 1:
            return _parser_conflict(arts, bank_id, None)

    # Level 3: bank_id IS NULL + format_key (format default)
    if format_key and format_key != "unknown":
        arts = base_q.filter(
            ParserArtifact.bank_id.is_(None),
            ParserArtifact.format_key == format_key,
        ).all()
        if len(arts) == 1:
            return _parser_match_out(arts[0], "format_default", None, format_key)
        if len(arts) > 1:
            return _parser_conflict(arts, None, format_key)

    # Level 4: global default (bank_id IS NULL + format_key IS NULL + account_code IS NULL)
    arts = base_q.filter(
        ParserArtifact.bank_id.is_(None),
        ParserArtifact.format_key.is_(None),
        ParserArtifact.account_code.is_(None),
    ).all()
    if len(arts) == 1:
        return _parser_match_out(arts[0], "global_default", None, None)
    if len(arts) > 1:
        return _parser_conflict(arts, None, None)

    reason = "no matching parser"
    if bank_status == "ambiguous":
        reason = "银行歧义，无法按 bank_id 匹配 parser"
    return {
        "matched": False,
        "parser_artifact_id": None, "name": None,
        "bank_id": None, "format_key": None,
        "match_level": "none",
        "reason": reason,
    }


def _parser_match_out(
    artifact: ParserArtifact,
    match_level: str,
    bank_id: Optional[int],
    format_key: Optional[str],
) -> Dict[str, Any]:
    return {
        "matched": True,
        "parser_artifact_id": artifact.id,
        "name": artifact.name,
        "bank_id": bank_id,
        "format_key": format_key,
        "match_level": match_level,
        "reason": f"matched via {match_level}",
    }


def _parser_conflict(
    artifacts: list,
    bank_id: Optional[int],
    format_key: Optional[str],
) -> Dict[str, Any]:
    return {
        "matched": False,
        "parser_artifact_id": None,
        "name": None,
        "bank_id": bank_id,
        "format_key": format_key,
        "match_level": "conflict",
        "reason": f"{len(artifacts)} 个同级 active parser 冲突",
    }


def build_bank_import_context(db: Session, file_path: str, filename: str) -> Dict[str, Any]:
    """Build full import context for a bank file: identity, bank resolution,
    account attribution, parser match. Reusable by upload_file and import_preview."""
    identity_hints = extract_identity_hints(file_path, filename)
    bank_resolution = resolve_bank_from_hints(db, identity_hints)
    account_attribution = match_account_attribution(db, identity_hints)
    format_key = identity_hints.get("format_fingerprint", "unknown")
    parser_match = _match_bank_format_parser_artifact(db, bank_resolution, format_key)
    return {
        "identity_hints": identity_hints,
        "bank_resolution": bank_resolution,
        "account_attribution": account_attribution,
        "format_fingerprint": format_key,
        "parser_match": parser_match,
    }


def _find_uploaded_file(batch_code: str, source_name: str) -> Optional[str]:
    upload_dir = os.path.join(DATA_DIR, "uploads")
    if not os.path.isdir(upload_dir):
        return None
    for filename in os.listdir(upload_dir):
        if filename.startswith(batch_code + "_") and os.path.isfile(os.path.join(upload_dir, filename)):
            return os.path.join(upload_dir, filename)
    return None


def _display_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _preview_from_canonical_rows(batch_code: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_rows = []
    abnormal_rows = []
    for row in rows:
        preview_row = {
            "business_date": _display_scalar(row.get("business_date")),
            "entity_code": _display_scalar(row.get("entity_code")),
            "entity_name": _display_scalar(row.get("entity_name")),
            "account_code": _display_scalar(row.get("account_code")),
            "account_name": _display_scalar(row.get("account_name")),
            "summary_text": _display_scalar(row.get("summary")),
            "counterparty_name": _display_scalar(row.get("counterparty")),
            "income_amount": _display_scalar(row.get("amount_in")),
            "expense_amount": _display_scalar(row.get("amount_out")),
            "balance": _display_scalar(row.get("rolling_balance")),
            "state": _display_scalar(row.get("state")),
            "source": _display_scalar(row.get("source")),
            "_errors": [],
        }
        errors = []
        if not row.get("business_date") or not row.get("account_code"):
            errors.append("CORE_FIELD_MISSING")
        if row.get("state") != "正常":
            errors.append("ROW_STATE_NOT_NORMAL")
        if errors:
            preview_row["_errors"] = errors
            abnormal_rows.append(preview_row)
        else:
            valid_rows.append(preview_row)
    return {
        "batch_code": batch_code,
        "total_count": len(rows),
        "valid_count": len(valid_rows),
        "abnormal_count": len(abnormal_rows),
        "parsed_rows": valid_rows,
        "abnormal_rows": abnormal_rows,
    }
