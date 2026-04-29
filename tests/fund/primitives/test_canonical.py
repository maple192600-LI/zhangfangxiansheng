"""test_canonical · §P3 · 4 函数单测

normalize_row / emit_row / mark_row_state / derive_source
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from fund.primitives.canonical import (
    CANONICAL_FIELDS,
    derive_source,
    emit_row,
    mark_row_state,
    normalize_row,
)


# ──────────────────────────────────────────
# CANONICAL_FIELDS 契约
# ──────────────────────────────────────────
def test_canonical_12_order_frozen():
    """§C1 · 12 列顺序冻结（契约级别）。"""
    assert CANONICAL_FIELDS == (
        "business_date", "entity_code", "entity_name",
        "account_code", "account_name",
        "summary", "counterparty",
        "amount_in", "amount_out", "rolling_balance",
        "state", "source",
    )
    assert len(CANONICAL_FIELDS) == 12


# ──────────────────────────────────────────
# emit_row · 验证清单：少列即抛
# ──────────────────────────────────────────
def _full_kwargs(**overrides):
    base = dict(
        business_date=date(2026, 4, 23),
        entity_code="E001",
        entity_name="示例科技",
        account_code="A001",
        account_name="工行主户",
        summary="工资",
        counterparty="公司A",
        amount_in=Decimal("5000"),
        amount_out=Decimal("0"),
        rolling_balance=Decimal("105000"),
        state="正常",
        source="网银导入",
    )
    base.update(overrides)
    return base


def test_emit_row_full_fields_ok():
    row = emit_row(**_full_kwargs())
    assert row["amount_in"] == Decimal("5000")
    assert row["state"] == "正常"
    assert row["source"] == "网银导入"


def test_emit_row_missing_required_raises():
    # 缺少 account_code（非可缺省）
    with pytest.raises(ValueError, match="缺少 CANONICAL_12"):
        kw = _full_kwargs()
        del kw["account_code"]
        emit_row(**kw)


def test_emit_row_missing_source_raises():
    with pytest.raises(ValueError, match="缺少 CANONICAL_12"):
        kw = _full_kwargs()
        del kw["source"]
        emit_row(**kw)


def test_emit_row_extra_column_raises():
    with pytest.raises(ValueError, match="多余列"):
        emit_row(evil_col="x", **_full_kwargs())


def test_emit_row_optional_defaults():
    row = emit_row(
        entity_code="E001", entity_name="示例",
        account_code="A001", account_name="主户",
        source="网银导入",
    )
    # summary/counterparty/rolling_balance/business_date = None
    assert row["summary"] is None
    assert row["counterparty"] is None
    assert row["rolling_balance"] is None
    assert row["business_date"] is None
    assert row["state"] == "正常"
    assert row["amount_in"] == Decimal("0")
    assert row["amount_out"] == Decimal("0")


def test_emit_row_amount_coerces_to_decimal():
    row = emit_row(**_full_kwargs(amount_in=5000, amount_out=0.0))
    assert row["amount_in"] == Decimal("5000")
    assert isinstance(row["amount_in"], Decimal)
    assert isinstance(row["amount_out"], Decimal)


def test_emit_row_state_enum_invalid():
    with pytest.raises(ValueError, match="state 非法"):
        emit_row(**_full_kwargs(state="随便"))


def test_emit_row_source_enum_invalid():
    with pytest.raises(ValueError, match="source 非法"):
        emit_row(**_full_kwargs(source="邮件"))


def test_emit_row_negative_amount_raises():
    with pytest.raises(ValueError, match="amount 不得为负"):
        emit_row(**_full_kwargs(amount_in=Decimal("-1")))


def test_emit_row_mutex_sets_state_exception():
    """金额互斥不抛，自动标 '异常' 给 Agent 救赎机会。"""
    row = emit_row(**_full_kwargs(
        amount_in=Decimal("100"), amount_out=Decimal("50"), state="正常",
    ))
    assert row["state"] == "异常"


def test_emit_row_rolling_balance_coerce():
    row = emit_row(**_full_kwargs(rolling_balance=1234.5))
    assert row["rolling_balance"] == Decimal("1234.5")


# ──────────────────────────────────────────
# normalize_row
# ──────────────────────────────────────────
def test_normalize_row_from_dict():
    raw = {
        "business_date": date(2026, 4, 23),
        "entity_code": "E001", "entity_name": "示例",
        "account_code": "A001", "account_name": "主户",
        "summary": "转账", "counterparty": None,
        "amount_in": 100, "amount_out": 0,
        "rolling_balance": None,
        "state": "正常", "source": "网银导入",
    }
    row = normalize_row(raw)
    assert row["amount_in"] == Decimal("100")


def test_normalize_row_missing_source_raises():
    raw = {
        "entity_code": "E001", "entity_name": "示例",
        "account_code": "A001", "account_name": "主户",
    }
    with pytest.raises(ValueError, match="source 必填"):
        normalize_row(raw)


def test_normalize_row_fills_zero_amount():
    raw = {
        "entity_code": "E001", "entity_name": "示例",
        "account_code": "A001", "account_name": "主户",
        "source": "手工录入",
    }
    row = normalize_row(raw)
    assert row["amount_in"] == Decimal("0")
    assert row["amount_out"] == Decimal("0")


# ──────────────────────────────────────────
# mark_row_state
# ──────────────────────────────────────────
def test_mark_row_state_updates():
    row = emit_row(**_full_kwargs())
    new = mark_row_state(row, "待确认")
    assert new["state"] == "待确认"
    assert row["state"] == "正常"  # 原对象不变


def test_mark_row_state_mutex_forces_exception():
    row = emit_row(**_full_kwargs(
        amount_in=Decimal("1"), amount_out=Decimal("1"), state="正常",
    ))
    # 已被 emit_row 标为异常
    assert row["state"] == "异常"
    # 尝试覆盖为 '正常' 仍被强制为 '异常'
    new = mark_row_state(row, "正常")
    assert new["state"] == "异常"


def test_mark_row_state_invalid_raises():
    row = emit_row(**_full_kwargs())
    with pytest.raises(ValueError, match="state 非法"):
        mark_row_state(row, "奇怪")


# ──────────────────────────────────────────
# derive_source
# ──────────────────────────────────────────
@pytest.mark.parametrize("im,expected", [
    ("online_bank",     "网银导入"),
    ("bank",            "网银导入"),
    ("manual",          "手工录入"),
    ("cash",            "现金录入"),
    ("bill",            "票据录入"),
    ("receipt",         "票据录入"),
    ("finance_company", "财务公司单据"),
    ("Online_Bank",     "网银导入"),  # case-insensitive
    (" MANUAL ",        "手工录入"),  # 前后空白
])
def test_derive_source_valid(im, expected):
    assert derive_source(im) == expected


def test_derive_source_empty_raises():
    with pytest.raises(ValueError, match="不可为空"):
        derive_source("")


def test_derive_source_unknown_raises():
    with pytest.raises(ValueError, match="未知 input_method"):
        derive_source("telegram")
