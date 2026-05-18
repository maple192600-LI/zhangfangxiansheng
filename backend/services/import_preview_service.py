"""统一导入预览服务 — 网银/手工快速录入/手工Excel 共用预览、编辑、校验、提交流程"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core import artifact_runtime
from db.tables import Account, Entity, FundEvent, ImportBatch, ParserArtifact
from services import bank_import_service as bank_svc
from services import manual_flow_service as manual_svc
from services import log_service

logger = logging.getLogger(__name__)

# 可编辑字段白名单（前端字段名 → ORM 字段名）
FIELD_MAP = {
    "entity_code": "entity_code",
    "entity_name": "entity_name",
    "account_code": "account_code",
    "account_name": "account_name",
    "business_date": "business_date",
    "summary_text": "summary",
    "counterparty_name": "counterparty",
    "income_amount": "amount_in",
    "expense_amount": "amount_out",
    "rolling_balance": "rolling_balance",
}


def _resolve_entity_for_input(db: Session, value: str):
    result = manual_svc._match_entity(db, value)
    if not result:
        return None, str(value).strip()
    entity = db.query(Entity).filter(Entity.id == result[0]).first()
    return entity.entity_code, entity.short_name or entity.name


def _resolve_account_for_input(db: Session, value: str, entity_id: int = None):
    result = manual_svc._match_account(db, value, entity_id)
    if not result:
        return None, str(value).strip()
    account = db.query(Account).filter(Account.id == result[0]).first()
    return account.account_code, account.account_alias


def get_preview(db: Session, batch_code: str) -> Dict[str, Any]:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")

    source_type = batch.source_type

    if source_type == "manual_quick":
        return _build_preview(db, batch)

    if source_type in ("manual_excel", "manual_file"):
        existing = db.query(FundEvent).filter(FundEvent.batch_id == batch.id).count()
        if existing == 0:
            manual_svc._preview_from_excel_file(db, batch)
        return _build_preview(db, batch)

    if source_type == "bank":
        return _build_bank_preview(db, batch)

    raise ValueError(f"不支持的批次类型: {source_type}")


def _build_preview(db: Session, batch: ImportBatch) -> Dict[str, Any]:
    events = db.query(FundEvent).filter(FundEvent.batch_id == batch.id).order_by(FundEvent.id).all()
    if not events and batch.source_type == "manual_quick":
        return {
            "batch_code": batch.batch_code,
            "source_type": batch.source_type,
            "source_name": batch.source_name,
            "status": batch.status,
            "total_count": 0,
            "valid_count": 0,
            "abnormal_count": 0,
            "parsed_rows": [],
            "abnormal_rows": [],
        }

    valid_rows = []
    abnormal_rows = []
    for i, ev in enumerate(events):
        row = _event_to_preview_dict(ev)
        row["_row_no"] = i + 1
        errors = manual_svc._validate_fund_event(ev)
        row["_errors"] = errors
        row["abnormal_code"] = ",".join(errors) if errors else None
        if errors:
            abnormal_rows.append(row)
        else:
            valid_rows.append(row)

    batch.status = "previewed"
    db.commit()

    return {
        "batch_code": batch.batch_code,
        "source_type": batch.source_type,
        "source_name": batch.source_name,
        "status": batch.status,
        "total_count": len(events),
        "valid_count": len(valid_rows),
        "abnormal_count": len(abnormal_rows),
        "parsed_rows": valid_rows,
        "abnormal_rows": abnormal_rows,
    }


def _build_bank_preview(db: Session, batch: ImportBatch) -> Dict[str, Any]:
    existing = db.query(FundEvent).filter(FundEvent.batch_id == batch.id).count()
    if existing > 0:
        return _build_preview(db, batch)

    file_path = bank_svc._find_uploaded_file(batch.batch_code, batch.source_name or "")
    if not file_path:
        return _bank_unavailable_preview(batch, "原始文件未找到")

    context = bank_svc.build_bank_import_context(db, file_path, batch.source_name or "")
    parser_match = context["parser_match"]

    if not parser_match.get("matched"):
        return _bank_unavailable_preview(
            batch, f"缺少解析规则: {parser_match.get('reason', '未知原因')}", context,
        )

    try:
        ctx = {
            "batch_code": batch.batch_code,
            "bank_resolution": context["bank_resolution"],
            "account_attribution": context["account_attribution"],
        }
        rows = list(artifact_runtime.run_parser(
            db, parser_match["parser_artifact_id"], file_path, ctx,
        ))
        for row in rows:
            row.setdefault("state", "待确认")
            db.add(FundEvent(
                **row, batch_id=batch.id,
                parser_artifact_id=parser_match["parser_artifact_id"],
            ))
        batch.status = "previewed"
        db.commit()
        return _build_preview(db, batch)
    except Exception as e:
        logger.error("网银解析失败: %s", e, exc_info=True)
        return _bank_unavailable_preview(batch, f"解析失败: {e}", context)


def _bank_unavailable_preview(
    batch: ImportBatch, reason: str, context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "batch_code": batch.batch_code,
        "source_type": batch.source_type,
        "source_name": batch.source_name,
        "status": batch.status,
        "total_count": 0,
        "valid_count": 0,
        "abnormal_count": 0,
        "parsed_rows": [],
        "abnormal_rows": [],
        "parser_status": "unavailable",
        "parser_message": reason,
    }
    if context:
        result["identity_hints"] = context.get("identity_hints")
        result["bank_resolution"] = context.get("bank_resolution")
        result["account_attribution"] = context.get("account_attribution")
        result["parser_match"] = context.get("parser_match")
    return result


def update_row(db: Session, batch_code: str, row_no: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")

    events = db.query(FundEvent).filter(FundEvent.batch_id == batch.id).order_by(FundEvent.id).all()
    if row_no < 1 or row_no > len(events):
        raise ValueError(f"行号 {row_no} 超出范围")

    ev = events[row_no - 1]

    for front_field, value in updates.items():
        orm_field = FIELD_MAP.get(front_field)
        if not orm_field:
            continue

        if orm_field == "business_date":
            if value is None or str(value).strip() == "":
                setattr(ev, orm_field, None)
            else:
                try:
                    setattr(ev, orm_field, datetime.strptime(str(value)[:10].replace("/", "-"), "%Y-%m-%d").date())
                except (ValueError, IndexError):
                    setattr(ev, orm_field, None)
        elif orm_field in ("amount_in", "amount_out", "rolling_balance"):
            if value is None or str(value).strip() == "":
                setattr(ev, orm_field, 0 if orm_field != "rolling_balance" else None)
            else:
                try:
                    setattr(ev, orm_field, float(value))
                except (ValueError, TypeError):
                    setattr(ev, orm_field, 0 if orm_field != "rolling_balance" else None)
        elif orm_field == "entity_code":
            code = str(value).strip() if value else ""
            if code:
                canonical_code, display_name = _resolve_entity_for_input(db, code)
                setattr(ev, "entity_code", canonical_code)
                setattr(ev, "entity_name", display_name)
            else:
                setattr(ev, "entity_code", None)
                setattr(ev, "entity_name", "")
        elif orm_field == "account_code":
            code = str(value).strip() if value else ""
            entity_id = None
            if ev.entity_code:
                ent = db.query(Entity).filter(Entity.entity_code == ev.entity_code).first()
                if ent:
                    entity_id = ent.id
            if code:
                canonical_code, display_name = _resolve_account_for_input(db, code, entity_id)
                setattr(ev, "account_code", canonical_code)
                setattr(ev, "account_name", display_name)
            else:
                setattr(ev, "account_code", None)
                setattr(ev, "account_name", "")
        else:
            setattr(ev, orm_field, value)

    errors = manual_svc._validate_fund_event(ev)
    db.commit()

    row = _event_to_preview_dict(ev)
    row["_row_no"] = row_no
    row["_errors"] = errors
    row["abnormal_code"] = ",".join(errors) if errors else None

    return {"row": row, "errors": errors}


def validate_all(db: Session, batch_code: str) -> Dict[str, Any]:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")

    events = db.query(FundEvent).filter(FundEvent.batch_id == batch.id).order_by(FundEvent.id).all()
    valid = 0
    abnormal = 0
    error_summary = []
    for i, ev in enumerate(events):
        errors = manual_svc._validate_fund_event(ev)
        if errors:
            abnormal += 1
            error_summary.append({"row_no": i + 1, "errors": errors})
        else:
            valid += 1

    return {
        "batch_code": batch_code,
        "total_count": len(events),
        "valid_count": valid,
        "abnormal_count": abnormal,
        "error_summary": error_summary,
    }


def commit(db: Session, batch_code: str) -> Dict[str, Any]:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")

    events = db.query(FundEvent).filter(FundEvent.batch_id == batch.id).all()
    if not events:
        raise ValueError("没有可提交的预览数据")

    abnormal = 0
    for ev in events:
        errors = manual_svc._validate_fund_event(ev)
        if errors:
            abnormal += 1

    if abnormal > 0:
        raise ValueError(f"存在 {abnormal} 条异常行，请先处理后再提交")

    committed = 0
    for ev in events:
        if ev.state != "正常":
            ev.state = "正常"
            committed += 1

    batch.status = "committed"
    batch.updated_at = datetime.now()
    db.commit()

    log_service.write_log(
        db,
        action="import_preview_commit",
        module="import_preview",
        detail={"batch_code": batch_code, "committed_rows": committed, "source_type": batch.source_type},
        batch_id=batch.id,
    )

    return {
        "batch_code": batch_code,
        "committed_count": len(events),
    }


def _event_to_preview_dict(ev: FundEvent) -> Dict:
    return {
        "entity_code": ev.entity_code or "",
        "entity_name": ev.entity_name or "",
        "account_code": ev.account_code or "",
        "account_name": ev.account_name or "",
        "business_date": str(ev.business_date) if ev.business_date else "",
        "summary_text": ev.summary or "",
        "counterparty_name": ev.counterparty or "",
        "income_amount": float(ev.amount_in) if ev.amount_in else None,
        "expense_amount": float(ev.amount_out) if ev.amount_out else None,
        "rolling_balance": float(ev.rolling_balance) if ev.rolling_balance else None,
        "parse_status": ev.state,
    }
