"""aggregations · §P6 · 6 个聚合运算基元

契约锚点：docs/30_contracts/25_primitives_whitelist.md §P6

| 函数        | 职责                              |
|-------------|-----------------------------------|
| sum_field   | 分列累加 amount_in / amount_out   |
| count_rows  | 行数                              |
| aggregate   | 通用 sum/max/min/avg              |
| net_change  | 期末 - 期初 的净变动              |
| max_date    | 期内最大 business_date            |
| min_date    | 期内最小 business_date            |

**语义说明**：若 filters 未显式给 state / state_in，默认仅计算 state='正常' 的行。
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import func

from database import SessionLocal
from db.tables import FundEvent


_AMOUNT_FIELDS: frozenset[str] = frozenset({"amount_in", "amount_out"})
_AGG_NUMERIC_FIELDS: frozenset[str] = frozenset({
    "amount_in", "amount_out", "rolling_balance",
})
_AGG_OPS: frozenset[str] = frozenset({"sum", "max", "min", "avg"})

_AGG_FILTER_KEYS: frozenset[str] = frozenset({
    "account_code", "entity_code", "start_date", "end_date",
    "state", "state_in", "source", "source_in",
})


def _apply_filters(q, filters: dict):
    """共用过滤器；默认把 state 限制到 '正常'。"""
    unknown = set(filters) - _AGG_FILTER_KEYS
    if unknown:
        raise ValueError(
            f"聚合 filter 未知键：{sorted(unknown)}；"
            f"允许：{sorted(_AGG_FILTER_KEYS)}"
        )
    if filters.get("account_code"):
        q = q.filter(FundEvent.account_code == filters["account_code"])
    if filters.get("entity_code"):
        q = q.filter(FundEvent.entity_code == filters["entity_code"])
    if filters.get("start_date") is not None:
        q = q.filter(FundEvent.business_date >= filters["start_date"])
    if filters.get("end_date") is not None:
        q = q.filter(FundEvent.business_date <= filters["end_date"])
    explicit_state = False
    if filters.get("state"):
        q = q.filter(FundEvent.state == filters["state"])
        explicit_state = True
    if filters.get("state_in"):
        q = q.filter(FundEvent.state.in_(list(filters["state_in"])))
        explicit_state = True
    if filters.get("source"):
        q = q.filter(FundEvent.source == filters["source"])
    if filters.get("source_in"):
        q = q.filter(FundEvent.source.in_(list(filters["source_in"])))
    if not explicit_state:
        q = q.filter(FundEvent.state == "正常")
    return q


def sum_field(field: Literal["amount_in", "amount_out"], filters: dict) -> Decimal:
    """Σ(field) WHERE filters。"""
    if field not in _AMOUNT_FIELDS:
        raise ValueError(
            f"sum_field 只支持 {sorted(_AMOUNT_FIELDS)}；got {field!r}"
        )
    with SessionLocal() as s:
        col = getattr(FundEvent, field)
        q = s.query(func.sum(col))
        q = _apply_filters(q, filters)
        total = q.scalar()
        return Decimal(str(total)) if total is not None else Decimal("0")


def count_rows(filters: dict) -> int:
    with SessionLocal() as s:
        q = s.query(func.count(FundEvent.id))
        q = _apply_filters(q, filters)
        return int(q.scalar() or 0)


def aggregate(
    field: str,
    op: Literal["sum", "max", "min", "avg"],
    filters: dict,
) -> Decimal:
    """通用聚合。field 限于 {amount_in, amount_out, rolling_balance}；op 限于 4 种。"""
    if field not in _AGG_NUMERIC_FIELDS:
        raise ValueError(
            f"aggregate 仅支持 {sorted(_AGG_NUMERIC_FIELDS)}；got {field!r}"
        )
    if op not in _AGG_OPS:
        raise ValueError(f"op 仅支持 {sorted(_AGG_OPS)}；got {op!r}")
    with SessionLocal() as s:
        col = getattr(FundEvent, field)
        fn = {"sum": func.sum, "max": func.max, "min": func.min, "avg": func.avg}[op]
        q = s.query(fn(col))
        q = _apply_filters(q, filters)
        val = q.scalar()
        if val is None:
            return Decimal("0")
        return Decimal(str(val))


def net_change(account_code: str, start: date, end: date) -> Decimal:
    """期间净变动 = Σ amount_in - Σ amount_out WHERE business_date∈[start,end]。"""
    filters = {
        "account_code": account_code,
        "start_date": start,
        "end_date": end,
    }
    inflow = sum_field("amount_in", filters)
    outflow = sum_field("amount_out", filters)
    return inflow - outflow


def max_date(filters: dict) -> Optional[date]:
    with SessionLocal() as s:
        q = s.query(func.max(FundEvent.business_date))
        q = _apply_filters(q, filters)
        return q.scalar()


def min_date(filters: dict) -> Optional[date]:
    with SessionLocal() as s:
        q = s.query(func.min(FundEvent.business_date))
        q = _apply_filters(q, filters)
        return q.scalar()
