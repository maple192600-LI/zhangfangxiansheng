"""看板数据服务"""
from datetime import date, timedelta
from typing import Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from db.tables import FundEvent, Account, Entity


def get_metrics(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
    """看板指标：总收入/总支出/总余额 + 各账户余额"""
    q = db.query(FundEvent).filter(FundEvent.state == "正常")
    if start_date:
        q = q.filter(FundEvent.business_date >= start_date)
    if end_date:
        q = q.filter(FundEvent.business_date <= end_date)

    total_income = q.with_entities(func.coalesce(func.sum(FundEvent.amount_in), 0)).scalar() or 0
    total_expense = q.with_entities(func.coalesce(func.sum(FundEvent.amount_out), 0)).scalar() or 0

    # 各账户余额
    accounts = (
        db.query(Account, Entity.name.label("entity_name"))
        .join(Entity, Account.entity_id == Entity.id)
        .filter(Account.status == "enabled")
        .all()
    )
    account_list = [
        {
            "account_name": acc.account_alias,
            "entity_name": ename,
            "balance": float(acc.initial_balance or 0),
        }
        for acc, ename in accounts
    ]

    return {
        "total_income": float(total_income),
        "total_expense": float(total_expense),
        "net_change": float(total_income - total_expense),
        "accounts": account_list,
    }


def get_trends(db: Session, days: int = 30) -> Dict:
    """收支趋势（按日汇总）"""
    end = date.today()
    start = end - timedelta(days=days)

    rows = (
        db.query(
            FundEvent.business_date,
            func.coalesce(func.sum(FundEvent.amount_in), 0).label("income"),
            func.coalesce(func.sum(FundEvent.amount_out), 0).label("expense"),
        )
        .filter(FundEvent.business_date >= start, FundEvent.business_date <= end)
        .filter(FundEvent.state == "正常")
        .group_by(FundEvent.business_date)
        .order_by(FundEvent.business_date)
        .all()
    )

    # 补全缺失日期
    date_map = {r.business_date: r for r in rows}
    dates = []
    income_data = []
    expense_data = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        r = date_map.get(current)
        income_data.append(float(r.income) if r else 0)
        expense_data.append(float(r.expense) if r else 0)
        current += timedelta(days=1)

    return {
        "dates": dates,
        "income": income_data,
        "expense": expense_data,
    }


def get_composition(db: Session) -> Dict:
    """账户余额分布（饼图）"""
    accounts = (
        db.query(Account, Entity.name.label("entity_name"))
        .join(Entity, Account.entity_id == Entity.id)
        .filter(Account.status == "enabled")
        .filter(Account.initial_balance > 0)
        .all()
    )

    items = [
        {
            "name": f"{ename} - {acc.account_alias}",
            "value": float(acc.initial_balance or 0),
        }
        for acc, ename in accounts
    ]

    return {"items": items}
