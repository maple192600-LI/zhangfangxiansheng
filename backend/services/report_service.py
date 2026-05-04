"""报表服务 — 日报/日记账/余额表/收支明细"""
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from core import artifact_runtime
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
    eq = db.query(Entity).filter(Entity.status == "enabled")
    if entity_id:
        eq = eq.filter(Entity.id == entity_id)
    entities = eq.all()
    entity_map = {e.id: e for e in entities}

    # 一次性查出所有相关账户
    account_q = db.query(Account).filter(
        Account.status == "enabled",
        Account.include_in_daily_report == True,
    )
    if entity_id:
        account_q = account_q.filter(Account.entity_id == entity_id)
    accounts = account_q.all()

    # 按 entity 分组
    accounts_by_entity = defaultdict(list)
    for a in accounts:
        accounts_by_entity[a.entity_id].append(a)

    # 批量查询期间收支
    account_codes = [a.account_code for a in accounts]
    sum_rows = {}
    if account_codes:
        sums = (
            db.query(
                FundEvent.account_code,
                func.coalesce(func.sum(FundEvent.amount_in), 0),
                func.coalesce(func.sum(FundEvent.amount_out), 0),
            )
            .filter(
                FundEvent.account_code.in_(account_codes),
                FundEvent.state == "正常",
                FundEvent.business_date >= start_date,
                FundEvent.business_date <= end_date,
            )
            .group_by(FundEvent.account_code)
            .all()
        )
        for row in sums:
            sum_rows[row[0]] = (float(row[1]), float(row[2]))

    # 批量查期初余额
    opening_map = {}
    for a in accounts:
        opening_map[a.account_code] = get_opening_balance(db, a.id, start_date)

    results = []
    for ent_id, ent in entity_map.items():
        ent_accounts = accounts_by_entity.get(ent_id, [])
        opening = sum(opening_map.get(a.account_code, 0.0) for a in ent_accounts)
        income = sum(sum_rows.get(a.account_code, (0, 0))[0] for a in ent_accounts)
        expense = sum(sum_rows.get(a.account_code, (0, 0))[1] for a in ent_accounts)
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
    aq = db.query(Account).filter(
        Account.status == "enabled",
        Account.include_in_daily_report == True,
    )
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
                func.coalesce(func.sum(FundEvent.amount_in), 0),
                func.coalesce(func.sum(FundEvent.amount_out), 0),
            )
            .filter(
                FundEvent.account_code == acct.account_code,
                FundEvent.state == "正常",
                FundEvent.business_date >= start_date,
                FundEvent.business_date <= end_date,
            )
            .group_by(FundEvent.business_date)
            .order_by(FundEvent.business_date.asc())
            .all()
        )

        rows = []
        current_balance = opening
        total_income = 0.0
        total_expense = 0.0
        for dr in daily_rows:
            day_income = float(dr[1])
            day_expense = float(dr[2])
            prev = current_balance
            current_balance = current_balance + day_income - day_expense
            total_income += day_income
            total_expense += day_expense
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
                "account_code": acct.account_code or "",
                "account_name": acct.account_alias or "",
                "account_bank": acct.branch_name or "",
                "entity_name": acct.entity.short_name if acct.entity else "",
                "opening_balance": round(opening, 2),
                "total_income": round(total_income, 2),
                "total_expense": round(total_expense, 2),
                "ending_balance": round(opening + total_income - total_expense, 2),
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
    entity_map = {e.id: e for e in entities}

    account_q = db.query(Account).filter(
        Account.status == "enabled",
        Account.include_in_daily_report == True,
    )
    if entity_id:
        account_q = account_q.filter(Account.entity_id == entity_id)
    accounts = account_q.all()

    accounts_by_entity = defaultdict(list)
    for a in accounts:
        accounts_by_entity[a.entity_id].append(a)

    # 批量查收支
    account_codes = [a.account_code for a in accounts]
    sum_rows = {}
    if account_codes:
        sums = (
            db.query(
                FundEvent.account_code,
                func.coalesce(func.sum(FundEvent.amount_in), 0),
                func.coalesce(func.sum(FundEvent.amount_out), 0),
            )
            .filter(
                FundEvent.account_code.in_(account_codes),
                FundEvent.state == "正常",
                FundEvent.business_date >= start_date,
                FundEvent.business_date <= end_date,
            )
            .group_by(FundEvent.account_code)
            .all()
        )
        for row in sums:
            sum_rows[row[0]] = (float(row[1]), float(row[2]))

    opening_map = {}
    for a in accounts:
        opening_map[a.account_code] = get_opening_balance(db, a.id, start_date)

    rows = []
    for ent_id, ent in entity_map.items():
        ent_accounts = accounts_by_entity.get(ent_id, [])
        if not ent_accounts:
            continue

        ent_income = 0.0
        ent_expense = 0.0
        ent_opening = 0.0

        for acct in ent_accounts:
            opening = opening_map.get(acct.account_code, 0.0)
            inc, exp = sum_rows.get(acct.account_code, (0.0, 0.0))
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
        FundEvent.state == "正常",
        FundEvent.business_date >= start_date,
        FundEvent.business_date <= end_date,
    )
    if direction == "income":
        q = q.filter(FundEvent.amount_in > 0)
    else:
        q = q.filter(FundEvent.amount_out > 0)

    if entity_id:
        q = q.filter(FundEvent.entity.has(Entity.id == entity_id))

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
    amount = float(ev.amount_in) if direction == "income" and ev.amount_in else (
        float(ev.amount_out) if direction == "expense" and ev.amount_out else 0
    )
    return {
        "id": ev.id,
        "business_date": str(ev.business_date) if ev.business_date else None,
        "entity_name": ev.entity_name,
        "account_name": ev.account_name,
        "summary_text": ev.summary,
        "counterparty_name": ev.counterparty,
        "amount": round(amount, 2),
        "rolling_balance": float(ev.rolling_balance) if ev.rolling_balance else None,
    }


# ── 主要账户余额表 ──────────────────────────────

def major_balance(
    db: Session,
    start_date: date,
    end_date: date,
    entity_id: Optional[int] = None,
) -> List[Dict]:
    """主要账户余额表 — 只显示银行存款类型的账户"""
    eq = db.query(Entity).filter(Entity.status == "enabled")
    if entity_id:
        eq = eq.filter(Entity.id == entity_id)
    entities = eq.all()
    entity_map = {e.id: e for e in entities}

    account_q = db.query(Account).filter(
        Account.status == "enabled",
        Account.instrument_type == "银行存款",
    )
    if entity_id:
        account_q = account_q.filter(Account.entity_id == entity_id)
    accounts = account_q.all()

    accounts_by_entity = defaultdict(list)
    for a in accounts:
        accounts_by_entity[a.entity_id].append(a)

    account_codes = [a.account_code for a in accounts]
    sum_rows = {}
    if account_codes:
        sums = (
            db.query(
                FundEvent.account_code,
                func.coalesce(func.sum(FundEvent.amount_in), 0),
                func.coalesce(func.sum(FundEvent.amount_out), 0),
            )
            .filter(
                FundEvent.account_code.in_(account_codes),
                FundEvent.state == "正常",
                FundEvent.business_date >= start_date,
                FundEvent.business_date <= end_date,
            )
            .group_by(FundEvent.account_code)
            .all()
        )
        for row in sums:
            sum_rows[row[0]] = (float(row[1]), float(row[2]))

    opening_map = {}
    for a in accounts:
        opening_map[a.account_code] = get_opening_balance(db, a.id, start_date)

    rows = []
    for ent_id, ent in entity_map.items():
        ent_accounts = accounts_by_entity.get(ent_id, [])
        if not ent_accounts:
            continue

        ent_income = 0.0
        ent_expense = 0.0
        ent_opening = 0.0

        for acct in ent_accounts:
            opening = opening_map.get(acct.account_code, 0.0)
            inc, exp = sum_rows.get(acct.account_code, (0.0, 0.0))
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


# ── 月末盘点表 ──────────────────────────────

def month_check(
    db: Session,
    year: int,
    month: int,
    entity_id: Optional[int] = None,
) -> List[Dict]:
    """月末盘点表 — 指定年月的账户余额"""
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return account_balance(db, start, end, entity_id)


# ── 资金周报 ──────────────────────────────

def week_report(
    db: Session,
    start_date: date,
    end_date: date,
    entity_id: Optional[int] = None,
) -> List[Dict]:
    """资金周报 — 按单位汇总（逻辑同日报，只是周期不同）"""
    return daily_report(db, start_date, end_date, entity_id)


# ── 资金月报 ──────────────────────────────

def month_report(
    db: Session,
    year: int,
    month: int,
    entity_id: Optional[int] = None,
) -> List[Dict]:
    """资金月报 — 指定年月按单位汇总"""
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return daily_report(db, start, end, entity_id)


# ── 资金年报 ──────────────────────────────

def year_report(
    db: Session,
    year: int,
    entity_id: Optional[int] = None,
) -> List[Dict]:
    """资金年报 — 指定年份按单位汇总"""
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    return daily_report(db, start, end, entity_id)


def generate_report(db: Session, rule_artifact_id: int, ctx: Dict):
    """Run an approved RuleArtifact and return a filled workbook."""
    return artifact_runtime.run_rule(db, rule_artifact_id, ctx)
