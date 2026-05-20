"""test_base_queries · §P5 · 6 函数单测

opening_balance / closing_balance / rolling_balance_of /
list_events / account_field / entity_field
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from fund.primitives.base_queries import (
    account_field,
    closing_balance,
    entity_field,
    list_events,
    opening_balance,
    rolling_balance_of,
)


# ──────────────────────────────────────────
# opening_balance / closing_balance
# ──────────────────────────────────────────
def test_opening_balance_no_events_equals_initial(primitives_db, seed_events):
    # A001 initial = 100000，无事件
    assert opening_balance("A001", date(2026, 4, 10)) == Decimal("100000")


def test_opening_balance_with_prior_events(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1000, 0)
    seed_events("A001", date(2026, 4, 21), 0, 500)
    # as_of=2026-04-22 → 包含全部
    bal = opening_balance("A001", date(2026, 4, 22))
    assert bal == Decimal("100500")  # 100000 + 1000 - 500


def test_opening_balance_excludes_as_of_day(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1000, 0)
    seed_events("A001", date(2026, 4, 21), 500, 0)
    # as_of=2026-04-21 → 仅包含 < 21
    bal = opening_balance("A001", date(2026, 4, 21))
    assert bal == Decimal("101000")  # 100000 + 1000


def test_opening_balance_ignores_abnormal_state(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1000, 0, state="正常")
    seed_events("A001", date(2026, 4, 20), 50000, 0, state="异常")
    bal = opening_balance("A001", date(2026, 4, 22))
    assert bal == Decimal("101000")


def test_opening_balance_missing_account_raises(primitives_db):
    with pytest.raises(KeyError):
        opening_balance("A999", date(2026, 4, 1))


def test_closing_balance_equals_opening_next_day(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 21), 1000, 0)
    c = closing_balance("A001", date(2026, 4, 21))
    o_next = opening_balance("A001", date(2026, 4, 22))
    assert c == o_next


# ──────────────────────────────────────────
# rolling_balance_of
# ──────────────────────────────────────────
def test_rolling_balance_uses_db_column_when_set(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1000, 0, rolling_balance=999999)
    # 取事件 id
    from sqlalchemy import text
    with primitives_db.begin() as conn:
        eid = conn.execute(
            text("SELECT id FROM fund_events ORDER BY id DESC LIMIT 1")
        ).scalar()
    assert rolling_balance_of(eid) == Decimal("999999")


def test_rolling_balance_dynamic_when_null(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 1000, 0, rolling_balance=None)
    seed_events("A001", date(2026, 4, 21), 0, 300, rolling_balance=None)
    from sqlalchemy import text
    with primitives_db.begin() as conn:
        ids = [
            row[0]
            for row in conn.execute(
                text("SELECT id FROM fund_events ORDER BY id ASC")
            ).all()
        ]
    # 第 1 条：100000 + 1000 = 101000
    assert rolling_balance_of(ids[0]) == Decimal("101000")
    # 第 2 条：101000 - 300 = 100700
    assert rolling_balance_of(ids[1]) == Decimal("100700")


def test_rolling_balance_event_not_found(primitives_db):
    with pytest.raises(KeyError):
        rolling_balance_of(99999999)


# ──────────────────────────────────────────
# list_events
# ──────────────────────────────────────────
def test_list_events_unknown_filter_raises(primitives_db):
    with pytest.raises(ValueError, match="未知 filter 键"):
        list(list_events({"oops": 1}))


def test_list_events_by_account_code(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 100, 0)
    seed_events("A002", date(2026, 4, 20), 200, 0)
    rows = list(list_events({"account_code": "A001"}))
    assert all(r["account_code"] == "A001" for r in rows)
    assert len(rows) == 1


def test_list_events_by_date_range(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 19), 100, 0)
    seed_events("A001", date(2026, 4, 20), 200, 0)
    seed_events("A001", date(2026, 4, 25), 300, 0)
    rows = list(list_events({
        "start_date": date(2026, 4, 20),
        "end_date": date(2026, 4, 22),
    }))
    assert len(rows) == 1
    assert rows[0]["amount_in"] == Decimal("200")


def test_list_events_state_in_filter(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 20), 100, 0, state="正常")
    seed_events("A001", date(2026, 4, 20), 200, 0, state="异常")
    rows = list(list_events({"state_in": ["异常"]}))
    assert len(rows) == 1
    assert rows[0]["amount_in"] == Decimal("200")


def test_list_events_order_desc(primitives_db, seed_events):
    seed_events("A001", date(2026, 4, 19), 10, 0)
    seed_events("A001", date(2026, 4, 20), 20, 0)
    seed_events("A001", date(2026, 4, 21), 30, 0)
    asc = list(list_events({"account_code": "A001", "order": "asc"}))
    desc = list(list_events({"account_code": "A001", "order": "desc"}))
    assert [r["amount_in"] for r in asc] == [Decimal("10"), Decimal("20"), Decimal("30")]
    assert [r["amount_in"] for r in desc] == [Decimal("30"), Decimal("20"), Decimal("10")]


# ──────────────────────────────────────────
# account_field
# ──────────────────────────────────────────
def test_account_field_real_field(primitives_db):
    assert account_field("A001", "bank_name") == "工商银行"
    assert account_field("A001", "account_last_four") == "1234"


def test_account_field_virtual_entity_code(primitives_db):
    assert account_field("A001", "entity_code") == "E001"


def test_account_field_virtual_entity_name(primitives_db):
    assert account_field("A001", "entity_name") == "示例科技有限公司"


def test_account_field_virtual_division_name(primitives_db):
    assert account_field("A001", "division_name") == "总部板块"
    assert account_field("A003", "division_name") == "南方板块"


def test_account_field_virtual_account_name(primitives_db):
    # 兼容当前结构：account_name 对外暴露 = account_alias
    assert account_field("A001", "account_name") == "工行主户"


def test_account_field_missing_account_raises(primitives_db):
    with pytest.raises(KeyError):
        account_field("A999", "bank_name")


def test_account_field_unknown_field_raises(primitives_db):
    with pytest.raises(ValueError, match="白名单"):
        account_field("A001", "evil_field")


# ──────────────────────────────────────────
# entity_field
# ──────────────────────────────────────────
def test_entity_field_real(primitives_db):
    assert entity_field("E001", "name") == "示例科技有限公司"
    assert entity_field("E001", "short_name") == "示例"
    assert entity_field("E001", "status") == "enabled"


def test_entity_field_virtual_division_name(primitives_db):
    assert entity_field("E001", "division_name") == "总部板块"


def test_entity_field_virtual_entity_name(primitives_db):
    assert entity_field("E001", "entity_name") == "示例科技有限公司"


def test_entity_field_missing_entity_raises(primitives_db):
    with pytest.raises(KeyError):
        entity_field("E999", "name")


def test_entity_field_unknown_field_raises(primitives_db):
    with pytest.raises(ValueError, match="白名单"):
        entity_field("E001", "evil_col")
