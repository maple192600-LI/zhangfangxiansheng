"""test_aggregations · §P6 · 6 函数单测

sum_field / count_rows / aggregate / net_change / max_date / min_date

**核心验证**：默认 filters 未显式给 state → 仅算 state='正常'。
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from fund.primitives.aggregations import (
    aggregate,
    count_rows,
    max_date,
    min_date,
    net_change,
    sum_field,
)


# ──────────────────────────────────────────
# sum_field
# ──────────────────────────────────────────
def test_sum_field_amount_in_default_state_normal(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1000, 0, state="正常")
    seed_events("A001", date(2026, 4, 21), 500, 0, state="正常")
    seed_events("A001", date(2026, 4, 22), 99999, 0, state="异常")
    total = sum_field("amount_in", {"account_code": "A001"})
    assert total == Decimal("1500")


def test_sum_field_amount_out_default_normal_only(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 0, 200, state="正常")
    seed_events("A001", date(2026, 4, 21), 0, 5000, state="异常")
    total = sum_field("amount_out", {})
    assert total == Decimal("200")


def test_sum_field_explicit_state_in_overrides_default(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1000, 0, state="正常")
    seed_events("A001", date(2026, 4, 21), 500, 0, state="异常")
    total = sum_field(
        "amount_in",
        {"state_in": ["正常", "异常"]},
    )
    assert total == Decimal("1500")


def test_sum_field_invalid_field_raises(primitives_db):
    with pytest.raises(ValueError, match="sum_field 只支持"):
        sum_field("rolling_balance", {})  # type: ignore[arg-type]


def test_sum_field_unknown_filter_raises(primitives_db):
    with pytest.raises(ValueError, match="未知键"):
        sum_field("amount_in", {"oops": 1})


def test_sum_field_empty_returns_zero(primitives_db):
    assert sum_field("amount_in", {"account_code": "NO_SUCH"}) == Decimal("0")


# ──────────────────────────────────────────
# count_rows
# ──────────────────────────────────────────
def test_count_rows_default_state_normal(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1, 0, state="正常")
    seed_events("A001", date(2026, 4, 21), 1, 0, state="正常")
    seed_events("A001", date(2026, 4, 22), 1, 0, state="异常")
    assert count_rows({}) == 2


def test_count_rows_state_in_explicit(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1, 0, state="正常")
    seed_events("A001", date(2026, 4, 21), 1, 0, state="异常")
    seed_events("A001", date(2026, 4, 22), 1, 0, state="待确认")
    assert count_rows({"state_in": ["正常", "异常", "待确认"]}) == 3


def test_count_rows_by_account(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1, 0)
    seed_events("A002", date(2026, 4, 20), 1, 0)
    assert count_rows({"account_code": "A001"}) == 1


# ──────────────────────────────────────────
# aggregate
# ──────────────────────────────────────────
def test_aggregate_max(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 100, 0)
    seed_events("A001", date(2026, 4, 21), 500, 0)
    assert aggregate("amount_in", "max", {}) == Decimal("500")


def test_aggregate_min(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 100, 0)
    seed_events("A001", date(2026, 4, 21), 500, 0)
    assert aggregate("amount_in", "min", {}) == Decimal("100")


def test_aggregate_avg(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 100, 0)
    seed_events("A001", date(2026, 4, 21), 200, 0)
    assert aggregate("amount_in", "avg", {}) == Decimal("150")


def test_aggregate_sum_equals_sum_field(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 100, 0)
    seed_events("A001", date(2026, 4, 21), 200, 0)
    assert aggregate("amount_in", "sum", {}) == sum_field("amount_in", {})


def test_aggregate_rolling_balance_allowed(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1, 0, rolling_balance=100001)
    seed_events("A001", date(2026, 4, 21), 1, 0, rolling_balance=100002)
    assert aggregate("rolling_balance", "max", {}) == Decimal("100002")


def test_aggregate_invalid_field_raises(primitives_db):
    with pytest.raises(ValueError, match="aggregate 仅支持"):
        aggregate("summary", "sum", {})


def test_aggregate_invalid_op_raises(primitives_db):
    with pytest.raises(ValueError, match="op 仅支持"):
        aggregate("amount_in", "median", {})  # type: ignore[arg-type]


def test_aggregate_empty_returns_zero(primitives_db):
    assert aggregate("amount_in", "sum", {"account_code": "NOPE"}) == Decimal("0")


# ──────────────────────────────────────────
# net_change
# ──────────────────────────────────────────
def test_net_change_positive(primitives_db, seed_events):
    # DB CHECK ck_fund_events_amount_mutex：in/out 不可同时 >0 → 拆两行
    seed_events("A001", date(2026, 4, 20), 1000, 0)
    seed_events("A001", date(2026, 4, 21), 500, 0)
    seed_events("A001", date(2026, 4, 21), 0, 200)
    net = net_change("A001", date(2026, 4, 20), date(2026, 4, 21))
    assert net == Decimal("1300")  # (1000+500) - 200


def test_net_change_negative(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 100, 0)
    seed_events("A001", date(2026, 4, 20), 0, 1000)
    net = net_change("A001", date(2026, 4, 20), date(2026, 4, 20))
    assert net == Decimal("-900")


def test_net_change_ignores_out_of_range(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 19), 1000, 0)  # 区间外
    seed_events("A001", date(2026, 4, 20), 500, 0)
    net = net_change("A001", date(2026, 4, 20), date(2026, 4, 20))
    assert net == Decimal("500")


# ──────────────────────────────────────────
# max_date / min_date
# ──────────────────────────────────────────
def test_max_date_basic(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1, 0)
    seed_events("A001", date(2026, 4, 25), 1, 0)
    seed_events("A001", date(2026, 4, 22), 1, 0)
    assert max_date({"account_code": "A001"}) == date(2026, 4, 25)


def test_min_date_basic(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1, 0)
    seed_events("A001", date(2026, 4, 25), 1, 0)
    seed_events("A001", date(2026, 4, 22), 1, 0)
    assert min_date({"account_code": "A001"}) == date(2026, 4, 20)


def test_min_date_ignores_abnormal(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 18), 1, 0, state="异常")
    seed_events("A001", date(2026, 4, 20), 1, 0, state="正常")
    assert min_date({"account_code": "A001"}) == date(2026, 4, 20)


def test_max_date_none_when_empty(primitives_db):
    assert max_date({"account_code": "NO_SUCH"}) is None
    assert min_date({"account_code": "NO_SUCH"}) is None
