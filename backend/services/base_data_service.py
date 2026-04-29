"""基础数据服务 — 查询 + 滚动余额重建"""
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from db.tables import FundEvent, Account, Entity
from db.schemas import BaseDataRowOut, RebuildResult
from services import log_service


# ── 基础数据查询 ──────────────────────────────

def query_base_data(
    db: Session,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    entity_id: Optional[int] = None,
    account_id: Optional[int] = None,
    direction: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict:
    q = db.query(FundEvent).options(
        joinedload(FundEvent.entity),
        joinedload(FundEvent.account),
    ).filter(FundEvent.state == "正常")

    if date_from:
        q = q.filter(FundEvent.business_date >= _parse_date(date_from))
    if date_to:
        q = q.filter(FundEvent.business_date <= _parse_date(date_to))
    if entity_id:
        q = q.filter(FundEvent.entity.has(Entity.id == entity_id))
    if account_id:
        q = q.filter(FundEvent.account.has(Account.id == account_id))
    if direction:
        if direction == "income":
            q = q.filter(FundEvent.amount_in > 0)
        elif direction == "expense":
            q = q.filter(FundEvent.amount_out > 0)
    if keyword:
        escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        kw = f"%{escaped}%"
        q = q.filter(
            (FundEvent.summary.like(kw, escape="\\")) |
            (FundEvent.counterparty.like(kw, escape="\\"))
        )

    total = q.count()
    total_pages = math.ceil(total / page_size) if page_size else 1
    items = (
        q.order_by(FundEvent.business_date.asc(), FundEvent.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_event_to_row(ev) for ev in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def _event_to_row(ev: FundEvent) -> Dict:
    return {
        "id": ev.id,
        "business_date": str(ev.business_date) if ev.business_date else None,
        "entity_id": ev.entity.id if ev.entity else None,
        "entity_code": ev.entity_code,
        "entity_name": ev.entity_name,
        "account_id": ev.account.id if ev.account else None,
        "account_name": ev.account_name,
        "account_code": ev.account_code,
        "direction": "income" if ev.amount_in and ev.amount_in > 0 else ("expense" if ev.amount_out and ev.amount_out > 0 else "unknown"),
        "income_amount": float(ev.amount_in) if ev.amount_in else None,
        "expense_amount": float(ev.amount_out) if ev.amount_out else None,
        "rolling_balance": float(ev.rolling_balance) if ev.rolling_balance else None,
        "counterparty_name": ev.counterparty,
        "summary_text": ev.summary,
        "abnormal_code": None if ev.state == "正常" else ev.state,
        "parse_status": ev.state,
        "source_type": ev.source,
    }


# ── 滚动余额重建 ──────────────────────────────

def rebuild_rolling_balance(db: Session, account_id: Optional[int] = None) -> Dict:
    q = db.query(Account).filter(Account.status == "enabled")
    if account_id:
        q = q.filter(Account.id == account_id)

    accounts = q.all()
    total_events = 0

    for acct in accounts:
        events = (
            db.query(FundEvent)
            .filter(
                FundEvent.account_code == acct.account_code,
                FundEvent.state == "正常",
            )
            .order_by(FundEvent.business_date.asc(), FundEvent.id.asc())
            .all()
        )

        balance = float(acct.initial_balance or 0)
        for ev in events:
            inc = float(ev.amount_in or 0)
            exp = float(ev.amount_out or 0)
            balance = balance + inc - exp
            ev.rolling_balance = Decimal(str(round(balance, 2)))

            total_events += 1

    db.commit()

    log_service.write_log(db, action="report_rebuild", module="base_data", detail={
        "affected_accounts": len(accounts), "updated_events": total_events,
    })
    return {
        "affected_accounts": len(accounts),
        "updated_events": total_events,
    }


# ── 辅助函数 ──────────────────────────────

def get_opening_balance(db: Session, account_id: int, start_date: date) -> float:
    """获取某账户在某日期之前的期初余额"""
    acct = db.query(Account).filter(Account.id == account_id).first()
    if not acct:
        return 0.0

    base = float(acct.initial_balance or 0)

    # 如果 start_date <= balance_date，直接用 initial_balance
    if acct.balance_date and start_date <= acct.balance_date:
        return base

    # 否则找到 start_date 之前的最后一个 event 的 rolling_balance
    last_ev = (
        db.query(FundEvent)
        .filter(
            FundEvent.account_code == acct.account_code,
            FundEvent.state == "正常",
            FundEvent.business_date < start_date,
        )
        .order_by(FundEvent.business_date.desc(), FundEvent.id.desc())
        .first()
    )

    if last_ev and last_ev.rolling_balance is not None:
        return float(last_ev.rolling_balance)

    return base


def get_account_summary(
    db: Session,
    account_id: int,
    start_date: date,
    end_date: date,
) -> Dict:
    """单账户区间汇总：期初/收入/支出/期末"""
    opening = get_opening_balance(db, account_id, start_date)

    row = (
        db.query(
            func.coalesce(func.sum(FundEvent.amount_in), 0),
            func.coalesce(func.sum(FundEvent.amount_out), 0),
        )
        .filter(
            FundEvent.account_code == db.query(Account.account_code).filter(Account.id == account_id).scalar_subquery(),
            FundEvent.state == "正常",
            FundEvent.business_date >= start_date,
            FundEvent.business_date <= end_date,
        )
        .first()
    )

    income = float(row[0]) if row else 0
    expense = float(row[1]) if row else 0
    ending = opening + income - expense

    return {
        "opening_balance": round(opening, 2),
        "total_income": round(income, 2),
        "total_expense": round(expense, 2),
        "ending_balance": round(ending, 2),
    }


def _parse_date(s: str) -> date:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(s[:10] if len(s) > 8 else s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {s}")
