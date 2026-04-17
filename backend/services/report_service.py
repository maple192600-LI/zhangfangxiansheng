"""报表服务 — 日报/日记账/余额表/收支明细"""
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from db.tables import FundEvent, Account, Entity
from services.base_data_service import get_opening_balance, _parse_date
from services import log_service


# ── 资金日报 ──────────────────────────────

def daily_report(
    db: Session,
    start_date: date,
    end_date: date,
    entity_id: Optional[int] = None,
) -> List[Dict]:
    """按法人汇总：期初/收入/支出/净变动/期末"""
    # 获取所有实体
    eq = db.query(Entity).filter(Entity.status == "enabled")
    if entity_id:
        eq = eq.filter(Entity.id == entity_id)
    entities = eq.all()

    results = []
    for ent in entities:
        # 该实体下所有账户
        accounts = db.query(Account).filter(
            Account.entity_id == ent.id,
            Account.status == "enabled",
        ).all()

        opening = 0.0
        income = 0.0
        expense = 0.0

        for acct in accounts:
            opening += get_opening_balance(db, acct.id, start_date)
            row = (
                db.query(
                    func.coalesce(func.sum(FundEvent.income_amount), 0),
                    func.coalesce(func.sum(FundEvent.expense_amount), 0),
                )
                .filter(
                    FundEvent.account_id == acct.id,
                    FundEvent.parse_status == "valid",
                    FundEvent.business_date >= start_date,
                    FundEvent.business_date <= end_date,
                )
                .first()
            )
            income += float(row[0]) if row else 0
            expense += float(row[1]) if row else 0

        ending = opening + income - expense
        results.append({
            "entity_id": ent.id,
            "entity_name": ent.short_name,
            "opening_balance": round(opening, 2),
            "total_income": round(income, 2),
            "total_expense": round(expense, 2),
            "net_change": round(income - expense, 2),
            "ending_balance": round(ending, 2),
        })

    return results


# ── 现金日记账 ──────────────────────────────

def cash_journal(
    db: Session,
    start_date: date,
    end_date: date,
    account_id: Optional[int] = None,
) -> List[Dict]:
    """按账户分块，每块按日：上日余额/收入/支出/本日余额"""
    aq = db.query(Account).filter(Account.status == "enabled")
    if account_id:
        aq = aq.filter(Account.id == account_id)
    accounts = aq.options(joinedload(Account.entity)).all()

    blocks = []
    for acct in accounts:
        opening = get_opening_balance(db, acct.id, start_date)

        # 按日聚合
        daily_rows = (
            db.query(
                FundEvent.business_date,
                func.coalesce(func.sum(FundEvent.income_amount), 0),
                func.coalesce(func.sum(FundEvent.expense_amount), 0),
            )
            .filter(
                FundEvent.account_id == acct.id,
                FundEvent.parse_status == "valid",
                FundEvent.business_date >= start_date,
                FundEvent.business_date <= end_date,
            )
            .group_by(FundEvent.business_date)
            .order_by(FundEvent.business_date.asc())
            .all()
        )

        rows = []
        current_balance = opening
        for dr in daily_rows:
            day_income = float(dr[1])
            day_expense = float(dr[2])
            prev = current_balance
            current_balance = current_balance + day_income - day_expense
            rows.append({
                "business_date": str(dr[0]),
                "prev_balance": round(prev, 2),
                "income": round(day_income, 2),
                "expense": round(day_expense, 2),
                "day_balance": round(current_balance, 2),
            })

        if rows:
            blocks.append({
                "account_id": acct.id,
                "account_name": f"{acct.account_code} {acct.account_alias}",
                "entity_name": acct.entity.short_name if acct.entity else "",
                "rows": rows,
            })

    return blocks


# ── 账户余额表 ──────────────────────────────

def account_balance(
    db: Session,
    start_date: date,
    end_date: date,
    entity_id: Optional[int] = None,
) -> List[Dict]:
    """entity → account 层级：期初/本期收入/本期支出/期末"""
    eq = db.query(Entity).filter(Entity.status == "enabled")
    if entity_id:
        eq = eq.filter(Entity.id == entity_id)
    entities = eq.all()

    rows = []
    for ent in entities:
        accounts = db.query(Account).filter(
            Account.entity_id == ent.id,
            Account.status == "enabled",
        ).all()

        if not accounts:
            continue

        ent_income = 0.0
        ent_expense = 0.0
        ent_opening = 0.0

        for acct in accounts:
            opening = get_opening_balance(db, acct.id, start_date)
            row = (
                db.query(
                    func.coalesce(func.sum(FundEvent.income_amount), 0),
                    func.coalesce(func.sum(FundEvent.expense_amount), 0),
                )
                .filter(
                    FundEvent.account_id == acct.id,
                    FundEvent.parse_status == "valid",
                    FundEvent.business_date >= start_date,
                    FundEvent.business_date <= end_date,
                )
                .first()
            )

            inc = float(row[0]) if row else 0
            exp = float(row[1]) if row else 0
            ending = opening + inc - exp

            ent_opening += opening
            ent_income += inc
            ent_expense += exp

            rows.append({
                "entity_id": ent.id,
                "entity_name": ent.short_name,
                "account_id": acct.id,
                "account_name": f"{acct.account_code} {acct.account_alias}",
                "opening_balance": round(opening, 2),
                "period_income": round(inc, 2),
                "period_expense": round(exp, 2),
                "ending_balance": round(ending, 2),
                "is_subtotal": False,
            })

        # 法人小计行
        rows.append({
            "entity_id": ent.id,
            "entity_name": f"{ent.short_name} 小计",
            "account_id": None,
            "account_name": None,
            "opening_balance": round(ent_opening, 2),
            "period_income": round(ent_income, 2),
            "period_expense": round(ent_expense, 2),
            "ending_balance": round(ent_opening + ent_income - ent_expense, 2),
            "is_subtotal": True,
        })

    return rows


# ── 收入明细 ──────────────────────────────

def income_list(
    db: Session,
    start_date: date,
    end_date: date,
    entity_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict:
    return _direction_list(db, start_date, end_date, "income", entity_id, page, page_size)


# ── 支出明细 ──────────────────────────────

def expense_list(
    db: Session,
    start_date: date,
    end_date: date,
    entity_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict:
    return _direction_list(db, start_date, end_date, "expense", entity_id, page, page_size)


def _direction_list(
    db: Session,
    start_date: date,
    end_date: date,
    direction: str,
    entity_id: Optional[int],
    page: int,
    page_size: int,
) -> Dict:
    q = db.query(FundEvent).options(
        joinedload(FundEvent.entity),
        joinedload(FundEvent.account),
    ).filter(
        FundEvent.parse_status == "valid",
        FundEvent.direction == direction,
        FundEvent.business_date >= start_date,
        FundEvent.business_date <= end_date,
    )

    if entity_id:
        q = q.filter(FundEvent.entity_id == entity_id)

    total = q.count()
    total_pages = math.ceil(total / page_size) if page_size else 1
    items = (
        q.order_by(FundEvent.business_date.asc(), FundEvent.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_direction_row(ev, direction) for ev in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def _direction_row(ev: FundEvent, direction: str) -> Dict:
    amount = float(ev.income_amount) if direction == "income" and ev.income_amount else (
        float(ev.expense_amount) if direction == "expense" and ev.expense_amount else 0
    )
    return {
        "id": ev.id,
        "business_date": str(ev.business_date) if ev.business_date else None,
        "entity_name": ev.entity.short_name if ev.entity else None,
        "account_name": ev.account.account_alias if ev.account else None,
        "summary_text": ev.summary_text,
        "counterparty_name": ev.counterparty_name,
        "amount": round(amount, 2),
        "rolling_balance": float(ev.rolling_balance) if ev.rolling_balance else None,
    }
