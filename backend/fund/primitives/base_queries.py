"""base_queries · §P5 · 6 个基础数据表查询基元

契约锚点：docs/30_contracts/25_primitives_whitelist.md §P5

| 函数                | 职责                                   |
|---------------------|----------------------------------------|
| opening_balance     | 期初 = initial_balance + Σ(in-out) <as_of |
| closing_balance     | 期末 = opening(as_of + 1 day)          |
| rolling_balance_of  | 某行的滚动余额（按 date,id 累积）      |
| list_events         | 按 filters 迭代 CanonicalRow           |
| account_field       | 取 accounts 白名单字段 + 联表虚字段    |
| entity_field        | 取 entities 白名单字段 + 联表虚字段    |
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Iterator, Optional

from database import SessionLocal
from db.tables import Account, Division, Entity, FundEvent

from .canonical import CANONICAL_FIELDS, CanonicalRow


# accounts 表字段白名单（实体字段 + 联表虚字段）
_ALLOWED_ACCOUNT_FIELDS: frozenset[str] = frozenset({
    "entity_id", "bank_id", "account_code", "account_alias", "bank_name",
    "branch_name", "account_number", "account_last_four", "account_type",
    "instrument_type", "input_method", "has_online_banking",
    "include_in_daily_report", "allow_manual_entry", "currency",
    "initial_balance", "balance_date", "status", "notes",
})
_ACCOUNT_VIRTUAL_FIELDS: frozenset[str] = frozenset({
    "entity_code", "entity_name", "division_name", "account_name",
})

_ALLOWED_ENTITY_FIELDS: frozenset[str] = frozenset({
    "division_id", "entity_code", "name", "short_name", "status",
})
_ENTITY_VIRTUAL_FIELDS: frozenset[str] = frozenset({"division_name", "entity_name"})

# list_events filters 合法键
_LIST_FILTER_KEYS: frozenset[str] = frozenset({
    "account_code", "entity_code", "start_date", "end_date",
    "state", "state_in", "source", "source_in", "order",
})


def _event_to_canonical(ev: FundEvent) -> CanonicalRow:
    return CanonicalRow(  # type: ignore[typeddict-item]
        business_date=ev.business_date,
        entity_code=ev.entity_code,
        entity_name=ev.entity_name,
        account_code=ev.account_code,
        account_name=ev.account_name,
        summary=ev.summary,
        counterparty=ev.counterparty,
        amount_in=Decimal(str(ev.amount_in)) if ev.amount_in is not None else Decimal("0"),
        amount_out=Decimal(str(ev.amount_out)) if ev.amount_out is not None else Decimal("0"),
        rolling_balance=Decimal(str(ev.rolling_balance)) if ev.rolling_balance is not None else None,
        state=ev.state,
        source=ev.source,
    )


def opening_balance(account_code: str, as_of: date) -> Decimal:
    """期初余额 = accounts.initial_balance + Σ(amount_in - amount_out)
    WHERE account_code=X AND business_date < as_of AND state='正常'。
    """
    with SessionLocal() as s:
        acc = s.query(Account).filter(Account.account_code == account_code).first()
        if acc is None:
            raise KeyError(f"account_code={account_code!r} 不存在")
        initial = (
            Decimal(str(acc.initial_balance))
            if acc.initial_balance is not None
            else Decimal("0")
        )
        events = (
            s.query(FundEvent)
            .filter(
                FundEvent.account_code == account_code,
                FundEvent.business_date < as_of,
                FundEvent.state == "正常",
            )
            .all()
        )
        net = Decimal("0")
        for e in events:
            amt_in = Decimal(str(e.amount_in)) if e.amount_in is not None else Decimal("0")
            amt_out = Decimal(str(e.amount_out)) if e.amount_out is not None else Decimal("0")
            net += amt_in - amt_out
        return initial + net


def closing_balance(account_code: str, as_of: date) -> Decimal:
    """期末余额 = opening_balance(as_of + 1 day)；包含 as_of 当日。"""
    return opening_balance(account_code, as_of + timedelta(days=1))


def rolling_balance_of(event_id: int) -> Decimal:
    """某行的滚动余额。

    DB rolling_balance 列非空 → 直接返回。
    否则按 (business_date ASC, id ASC) 从 initial 累积到当前行（含）。
    """
    with SessionLocal() as s:
        ev = s.query(FundEvent).filter(FundEvent.id == event_id).first()
        if ev is None:
            raise KeyError(f"event_id={event_id} 不存在")
        if ev.rolling_balance is not None:
            return Decimal(str(ev.rolling_balance))
        acc = s.query(Account).filter(Account.account_code == ev.account_code).first()
        if acc is None:
            raise KeyError(f"account_code={ev.account_code!r} 不存在")
        initial = (
            Decimal(str(acc.initial_balance))
            if acc.initial_balance is not None
            else Decimal("0")
        )
        prior = (
            s.query(FundEvent)
            .filter(
                FundEvent.account_code == ev.account_code,
                FundEvent.state == "正常",
            )
            .all()
        )
        prior.sort(key=lambda e: (e.business_date, e.id))
        net = Decimal("0")
        for e in prior:
            if e.business_date > ev.business_date:
                continue
            if e.business_date == ev.business_date and e.id > ev.id:
                continue
            amt_in = Decimal(str(e.amount_in)) if e.amount_in is not None else Decimal("0")
            amt_out = Decimal(str(e.amount_out)) if e.amount_out is not None else Decimal("0")
            net += amt_in - amt_out
        return initial + net


def list_events(filters: dict) -> Iterator[CanonicalRow]:
    """按 filters 迭代 fund_events；每行 yield CanonicalRow。

    合法 filter 键：
      - account_code / entity_code: str
      - start_date / end_date:      date（闭区间）
      - state / state_in:           str | iterable[str]
      - source / source_in:         str | iterable[str]
      - order:                      'asc'（默认）/ 'desc'
    非法键 → ValueError。
    默认按 (business_date, id) 升序；不过滤 state。
    """
    unknown = set(filters) - _LIST_FILTER_KEYS
    if unknown:
        raise ValueError(
            f"list_events 未知 filter 键：{sorted(unknown)}；"
            f"允许：{sorted(_LIST_FILTER_KEYS)}"
        )
    with SessionLocal() as s:
        q = s.query(FundEvent)
        if filters.get("account_code"):
            q = q.filter(FundEvent.account_code == filters["account_code"])
        if filters.get("entity_code"):
            q = q.filter(FundEvent.entity_code == filters["entity_code"])
        if filters.get("start_date") is not None:
            q = q.filter(FundEvent.business_date >= filters["start_date"])
        if filters.get("end_date") is not None:
            q = q.filter(FundEvent.business_date <= filters["end_date"])
        if filters.get("state"):
            q = q.filter(FundEvent.state == filters["state"])
        if filters.get("state_in"):
            q = q.filter(FundEvent.state.in_(list(filters["state_in"])))
        if filters.get("source"):
            q = q.filter(FundEvent.source == filters["source"])
        if filters.get("source_in"):
            q = q.filter(FundEvent.source.in_(list(filters["source_in"])))
        order = filters.get("order", "asc")
        if order == "desc":
            q = q.order_by(FundEvent.business_date.desc(), FundEvent.id.desc())
        else:
            q = q.order_by(FundEvent.business_date.asc(), FundEvent.id.asc())
        events = q.all()
    for ev in events:
        yield _event_to_canonical(ev)


def account_field(account_code: str, field: str) -> Any:
    """取 accounts 任意字段（白名单 + 联表虚字段）。

    联表虚字段：entity_code / entity_name / division_name / account_name
    """
    with SessionLocal() as s:
        acc = s.query(Account).filter(Account.account_code == account_code).first()
        if acc is None:
            raise KeyError(f"account_code={account_code!r} 不存在")
        if field in _ALLOWED_ACCOUNT_FIELDS:
            return getattr(acc, field)
        if field in _ACCOUNT_VIRTUAL_FIELDS:
            if field == "account_name":
                # 兼容：account_name 在 current canonical schema 中不同于 account_alias
                return acc.account_alias
            ent = s.query(Entity).filter(Entity.id == acc.entity_id).first()
            if ent is None:
                return None
            if field == "entity_code":
                return ent.entity_code
            if field == "entity_name":
                return ent.name
            if field == "division_name":
                if ent.division_id is None:
                    return None
                div = s.query(Division).filter(Division.id == ent.division_id).first()
                return div.name if div else None
        raise ValueError(
            f"字段 {field!r} 不在 accounts 白名单；"
            f"允许：{sorted(_ALLOWED_ACCOUNT_FIELDS | _ACCOUNT_VIRTUAL_FIELDS)}"
        )


def entity_field(entity_code: str, field: str) -> Any:
    """取 entities 任意字段（白名单 + 联表虚字段）。

    联表虚字段：division_name / entity_name
    """
    with SessionLocal() as s:
        ent = s.query(Entity).filter(Entity.entity_code == entity_code).first()
        if ent is None:
            raise KeyError(f"entity_code={entity_code!r} 不存在")
        if field in _ALLOWED_ENTITY_FIELDS:
            return getattr(ent, field)
        if field in _ENTITY_VIRTUAL_FIELDS:
            if field == "entity_name":
                return ent.name
            if field == "division_name":
                if ent.division_id is None:
                    return None
                div = s.query(Division).filter(Division.id == ent.division_id).first()
                return div.name if div else None
        raise ValueError(
            f"字段 {field!r} 不在 entities 白名单；"
            f"允许：{sorted(_ALLOWED_ENTITY_FIELDS | _ENTITY_VIRTUAL_FIELDS)}"
        )


# 维持 CANONICAL_FIELDS 在 pkg 的 re-export（给 artifact 兜底用）
__all__ = [
    "opening_balance", "closing_balance", "rolling_balance_of",
    "list_events", "account_field", "entity_field",
    "CANONICAL_FIELDS",
]
