"""test_value_parsers · §P2 · 5 函数单测

parse_date / parse_amount / parse_text / parse_counterparty / normalize_whitespace
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from fund.primitives.value_parsers import (
    normalize_whitespace,
    parse_amount,
    parse_counterparty,
    parse_date,
    parse_text,
)


# ──────────────────────────────────────────
# parse_date · 验证清单：≥ 5 种格式
# ──────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("2026-04-23",     date(2026, 4, 23)),   # fmt 1: ISO
    ("2026/4/23",      date(2026, 4, 23)),   # fmt 1: 斜线
    ("2026.4.23",      date(2026, 4, 23)),   # fmt 1: 点
    ("20260423",       date(2026, 4, 23)),   # fmt 2: 紧凑
    ("2026年4月23日",  date(2026, 4, 23)),   # fmt 3: 中文
    ("2026年4月23",    date(2026, 4, 23)),   # fmt 3 no 日
])
def test_parse_date_with_year(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw,default_year,expected", [
    ("4月23日",  2026, date(2026, 4, 23)),  # fmt 4: 中文短
    ("04-23",    2026, date(2026, 4, 23)),  # fmt 5: 短 ISO
    ("4/23",     2026, date(2026, 4, 23)),  # fmt 5: 短斜线
])
def test_parse_date_short_needs_default_year(raw, default_year, expected):
    assert parse_date(raw, default_year=default_year) == expected


def test_parse_date_short_without_year_returns_none():
    assert parse_date("4-23") is None


def test_parse_date_from_datetime():
    assert parse_date(datetime(2026, 4, 23, 10, 30)) == date(2026, 4, 23)


def test_parse_date_from_date():
    assert parse_date(date(2026, 4, 23)) == date(2026, 4, 23)


def test_parse_date_from_excel_serial():
    # Excel 1900 系统（1899-12-30 基准）：2026-04-23 = 46135
    d = parse_date(46135)
    assert d == date(2026, 4, 23)


def test_parse_date_none_and_empty():
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("   ") is None


def test_parse_date_invalid_string():
    assert parse_date("not-a-date") is None
    assert parse_date("2026-99-99") is None
    assert parse_date("20260230") is None  # 2月30日


def test_parse_date_bool_returns_none():
    assert parse_date(True) is None
    assert parse_date(False) is None


# ──────────────────────────────────────────
# parse_amount · 验证清单：千分位 / 括号 / 中文大写
# ──────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("1234.56",      Decimal("1234.56")),
    ("1,234.56",     Decimal("1234.56")),   # 千分位
    ("¥1,234.56",    Decimal("1234.56")),   # 人民币符号
    ("￥1,234.56",   Decimal("1234.56")),   # 全角
    ("$1234.56",     Decimal("1234.56")),
    ("1234元",       Decimal("1234")),
    ("(1234.56)",    Decimal("-1234.56")),  # 括号负
    ("（1,234.56）", Decimal("-1234.56")),  # 全角括号
    ("-1234.56",     Decimal("-1234.56")),
    ("−1234.56",     Decimal("-1234.56")),  # Unicode 负号
])
def test_parse_amount_various(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("一千二百三十四",   Decimal("1234")),
    ("一万二千",         Decimal("12000")),
    ("壹佰贰拾",         Decimal("120")),
    ("十",               Decimal("10")),
    ("十一",             Decimal("11")),
    ("二十三",           Decimal("23")),
    ("一百点五",         Decimal("100.5")),
    ("一亿两千万",       Decimal("120000000")),
])
def test_parse_amount_chinese_numerals(raw, expected):
    assert parse_amount(raw) == expected


def test_parse_amount_from_native_types():
    assert parse_amount(1234) == Decimal("1234")
    assert parse_amount(1234.5) == Decimal("1234.5")
    assert parse_amount(Decimal("1234.56")) == Decimal("1234.56")


def test_parse_amount_default_on_none_or_empty():
    assert parse_amount(None) == Decimal("0")
    assert parse_amount("") == Decimal("0")
    assert parse_amount("   ") == Decimal("0")


def test_parse_amount_default_on_garbage():
    assert parse_amount("not a number") == Decimal("0")
    assert parse_amount("abc123xyz") == Decimal("0")


def test_parse_amount_custom_default():
    assert parse_amount("", default=Decimal("-1")) == Decimal("-1")


def test_parse_amount_bool_returns_default():
    assert parse_amount(True) == Decimal("0")
    assert parse_amount(False) == Decimal("0")


def test_parse_amount_ambiguous_returns_default():
    # "-(100)" 是会计学里少见的双重否定；primitive 不强制支持，
    # 只保证回退到 default（§P2 契约：解析失败 → default）
    assert parse_amount("-(100)") == Decimal("0")


# ──────────────────────────────────────────
# parse_text
# ──────────────────────────────────────────
def test_parse_text_strips_and_normalizes():
    assert parse_text("  hello  world  ") == "hello world"


def test_parse_text_full_to_half_width():
    # 全角数字字母
    assert parse_text("ＡＢＣ１２３") == "ABC123"


def test_parse_text_full_width_space():
    # 全角空格 → 半角空格 → 压缩
    assert parse_text("A　B") == "A B"


def test_parse_text_none_empty():
    assert parse_text(None) == ""
    assert parse_text("") == ""
    assert parse_text("   ") == ""


def test_parse_text_truncates_at_max_len():
    long = "a" * 1000
    assert parse_text(long, max_len=10) == "a" * 10


def test_parse_text_non_string_input():
    assert parse_text(12345) == "12345"


# ──────────────────────────────────────────
# parse_counterparty
# ──────────────────────────────────────────
def test_parse_counterparty_strips_account_suffix():
    assert parse_counterparty("深圳XX科技 账号:6222021234567890") == "深圳XX科技"


def test_parse_counterparty_strips_account_colon_style():
    assert parse_counterparty("XX贸易 账户：6222-02-1234-5678") == "XX贸易"


def test_parse_counterparty_strips_card_suffix():
    assert parse_counterparty("张三 卡号 6222***1234") == "张三"


def test_parse_counterparty_no_suffix_unchanged():
    assert parse_counterparty("纯公司名称") == "纯公司名称"


def test_parse_counterparty_none():
    assert parse_counterparty(None) == ""


def test_parse_counterparty_truncates():
    long = "公司名称" * 100
    assert len(parse_counterparty(long, max_len=20)) == 20


# ──────────────────────────────────────────
# normalize_whitespace
# ──────────────────────────────────────────
def test_normalize_whitespace_basic():
    assert normalize_whitespace("a   b") == "a b"


def test_normalize_whitespace_various_whitespace():
    assert normalize_whitespace("a\t\nb\r c") == "a b c"


def test_normalize_whitespace_strip_ends():
    assert normalize_whitespace("   hello   ") == "hello"


def test_normalize_whitespace_none_empty():
    assert normalize_whitespace(None) == ""
    assert normalize_whitespace("") == ""
    assert normalize_whitespace("   ") == ""


def test_normalize_whitespace_non_str():
    assert normalize_whitespace(123) == "123"
