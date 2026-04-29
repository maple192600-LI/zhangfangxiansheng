"""Exception center service for pending fund events."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from db.tables import FundEvent
from services import log_service

PENDING_STATES = ("待确认", "异常")
EDITABLE_FIELDS = {
    "business_date",
    "entity_code",
    "entity_name",
    "account_code",
    "account_name",
    "summary",
    "counterparty",
    "amount_in",
    "amount_out",
    "rolling_balance",
    "source",
}


def query_pending_events(
    db: Session,
    state: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    q = db.query(FundEvent).filter(FundEvent.state.in_(PENDING_STATES))
    if state:
        if state not in PENDING_STATES:
            raise ValueError("状态只能是待确认或异常")
        q = q.filter(FundEvent.state == state)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.filter((FundEvent.summary.like(kw)) | (FundEvent.counterparty.like(kw)))

    q = q.order_by(FundEvent.business_date.desc(), FundEvent.id.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_event_out(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "summary": {
            "pending_count": db.query(FundEvent).filter(FundEvent.state == "待确认").count(),
            "abnormal_count": db.query(FundEvent).filter(FundEvent.state == "异常").count(),
        },
    }


def resolve_event(
    db: Session,
    event_id: int,
    fixes: Optional[Dict[str, Any]] = None,
    note: Optional[str] = None,
    operator: str = "admin",
) -> Dict[str, Any]:
    event = _get_event(db, event_id)
    if event.state not in PENDING_STATES:
        raise ValueError("只有待确认或异常流水可以标记正常")

    before = _event_out(event)
    _apply_fixes(event, fixes or {})
    _validate_amounts(event)
    event.state = "正常"
    event.updated_at = datetime.now()

    log_service.write_log(
        db,
        action="event_resolve",
        module="exception_center",
        batch_id=event.batch_id,
        detail={
            "event_id": event.id,
            "operator": operator,
            "note": note or "",
            "before_state": before["state"],
            "fixes": {k: v for k, v in (fixes or {}).items() if k in EDITABLE_FIELDS},
        },
    )
    db.commit()
    db.refresh(event)
    return _event_out(event)


def void_event(
    db: Session,
    event_id: int,
    reason: Optional[str] = None,
    operator: str = "admin",
) -> Dict[str, Any]:
    event = _get_event(db, event_id)
    if event.state == "已作废":
        raise ValueError("该流水已作废")

    before_state = event.state
    event.state = "已作废"
    event.updated_at = datetime.now()
    log_service.write_log(
        db,
        action="event_void",
        module="exception_center",
        batch_id=event.batch_id,
        detail={
            "event_id": event.id,
            "operator": operator,
            "reason": reason or "",
            "before_state": before_state,
        },
    )
    db.commit()
    db.refresh(event)
    return _event_out(event)


def _get_event(db: Session, event_id: int) -> FundEvent:
    event = db.query(FundEvent).filter(FundEvent.id == event_id).first()
    if not event:
        raise LookupError("流水不存在")
    return event


def _apply_fixes(event: FundEvent, fixes: Dict[str, Any]) -> None:
    for key, value in fixes.items():
        if key not in EDITABLE_FIELDS:
            continue
        if value is None or value == "":
            if key in {"summary", "counterparty", "rolling_balance"}:
                setattr(event, key, None)
            continue
        if key == "business_date" and isinstance(value, str):
            value = date.fromisoformat(value)
        if key in {"amount_in", "amount_out", "rolling_balance"}:
            value = Decimal(str(value))
        setattr(event, key, value)


def _validate_amounts(event: FundEvent) -> None:
    amount_in = Decimal(str(event.amount_in or 0))
    amount_out = Decimal(str(event.amount_out or 0))
    if amount_in < 0 or amount_out < 0:
        raise ValueError("收入和支出不能为负数")
    if amount_in > 0 and amount_out > 0:
        raise ValueError("同一行不能同时有收入和支出")


def _event_out(event: FundEvent) -> Dict[str, Any]:
    return {
        "id": event.id,
        "business_date": event.business_date.isoformat() if event.business_date else "",
        "entity_code": event.entity_code,
        "entity_name": event.entity_name,
        "account_code": event.account_code,
        "account_name": event.account_name,
        "summary": event.summary or "",
        "counterparty": event.counterparty or "",
        "amount_in": float(event.amount_in or 0),
        "amount_out": float(event.amount_out or 0),
        "rolling_balance": float(event.rolling_balance) if event.rolling_balance is not None else None,
        "state": event.state,
        "source": event.source,
        "batch_id": event.batch_id,
        "parser_artifact_id": event.parser_artifact_id,
        "created_at": event.created_at.strftime("%Y-%m-%d %H:%M:%S") if event.created_at else "",
        "updated_at": event.updated_at.strftime("%Y-%m-%d %H:%M:%S") if event.updated_at else "",
    }
