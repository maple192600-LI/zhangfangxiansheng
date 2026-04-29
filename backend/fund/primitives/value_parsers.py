"""value_parsers · §P2 · 5 个单元格取值 / 归一化基元

契约锚点：docs/30_contracts/25_primitives_whitelist.md §P2

| 函数                 | 职责                                       |
|----------------------|--------------------------------------------|
| parse_date           | 5+ 中文日期格式 + Excel serial / datetime  |
| parse_amount         | 千分位 / 货币符号 / 括号负号 / 中文大写    |
| parse_text           | strip + 全半角归一化 + 截断                |
| parse_counterparty   | parse_text + 去尾部"账号 xxx"              |
| normalize_whitespace | 压缩连续空白                               |
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional


# ───────────────────────────────────────
# 金额清洗
# ───────────────────────────────────────
_AMOUNT_CURRENCY_CHARS = re.compile(r"[¥￥$€£\uFFE5,\s元圆]")
_PAREN_NEG = re.compile(r"^\s*[\(（](?P<num>[^)）]+)[\)）]\s*$")

_ZH_DIGITS: dict[str, int] = {
    "零": 0, "〇": 0, "一": 1, "壹": 1, "二": 2, "贰": 2, "两": 2,
    "三": 3, "叁": 3, "四": 4, "肆": 4, "五": 5, "伍": 5,
    "六": 6, "陆": 6, "七": 7, "柒": 7, "八": 8, "捌": 8,
    "九": 9, "玖": 9,
}
_ZH_UNITS_SMALL: dict[str, int] = {
    "十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000,
}
_ZH_DECIMAL_MARK = "点"

# ───────────────────────────────────────
# 日期格式优先级
# ───────────────────────────────────────
_DATE_PATTERNS = [
    (re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$"), ("Y", "M", "D")),
    (re.compile(r"^(\d{4})(\d{2})(\d{2})$"), ("Y", "M", "D")),
    (re.compile(r"^(\d{4})年(\d{1,2})月(\d{1,2})日?$"), ("Y", "M", "D")),
    (re.compile(r"^(\d{1,2})月(\d{1,2})日?$"), ("M", "D")),
    (re.compile(r"^(\d{1,2})[-/.](\d{1,2})$"), ("M", "D")),
]


def parse_date(raw, default_year: Optional[int] = None) -> Optional[date]:
    """解析日期；不可解析返回 None。

    支持：
    - ISO: 2026-04-23 / 2026/4/23 / 2026.4.23
    - 紧凑: 20260423
    - 中文: 2026年4月23日 / 4月23日（需 default_year）
    - 短: 4-23 / 4/23（需 default_year）
    - datetime / date 原生
    - Excel serial (int/float)
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, bool):  # bool 是 int 的子类，必须在 int 前拦截
        return None
    if isinstance(raw, (int, float)):
        try:
            base = datetime(1899, 12, 30)
            return (base + timedelta(days=float(raw))).date()
        except (ValueError, OverflowError):
            return None
    s = str(raw).strip()
    if not s:
        return None
    for pattern, order in _DATE_PATTERNS:
        m = pattern.match(s)
        if not m:
            continue
        parts = dict(zip(order, m.groups()))
        try:
            y = int(parts["Y"]) if "Y" in parts else default_year
            mo = int(parts["M"])
            d = int(parts["D"])
            if y is None:
                return None
            return date(y, mo, d)
        except (ValueError, KeyError):
            continue
    return None


def _zh_int_to_decimal(s: str) -> Decimal:
    """中文整数串 → Decimal；递归拆 '亿' '万'。"""
    if not s:
        return Decimal(0)
    for yi_char in ("亿", "億"):
        if yi_char in s:
            left, _, right = s.partition(yi_char)
            return (
                _zh_int_to_decimal(left) * Decimal(100_000_000)
                + _zh_int_to_decimal(right)
            )
    for wan_char in ("万", "萬"):
        if wan_char in s:
            left, _, right = s.partition(wan_char)
            return _zh_int_to_decimal(left) * Decimal(10_000) + _zh_int_to_decimal(right)
    total = Decimal(0)
    current = 0
    for ch in s:
        if ch in _ZH_DIGITS:
            current = _ZH_DIGITS[ch]
        elif ch in _ZH_UNITS_SMALL:
            unit = _ZH_UNITS_SMALL[ch]
            total += Decimal((current if current > 0 else 1) * unit)
            current = 0
        else:
            raise ValueError(f"未知字符 {ch!r}")
    total += Decimal(current)
    return total


def _parse_zh_numeral(s: str) -> Optional[Decimal]:
    """中文大写 → Decimal；解析失败返回 None。"""
    if not s:
        return None
    if _ZH_DECIMAL_MARK in s:
        int_part, _, dec_part = s.partition(_ZH_DECIMAL_MARK)
    else:
        int_part, dec_part = s, ""
    try:
        int_val = _zh_int_to_decimal(int_part)
    except ValueError:
        return None
    dec_val = Decimal(0)
    if dec_part:
        for i, ch in enumerate(dec_part, start=1):
            if ch not in _ZH_DIGITS:
                return None
            dec_val += Decimal(_ZH_DIGITS[ch]) / (Decimal(10) ** i)
    return int_val + dec_val


def parse_amount(raw, default: Decimal = Decimal("0")) -> Decimal:
    """解析金额；不可解析返回 default（不抛）。"""
    if raw is None or raw == "":
        return default
    if isinstance(raw, bool):
        return default
    if isinstance(raw, (int, float)):
        try:
            return Decimal(str(raw))
        except InvalidOperation:
            return default
    if isinstance(raw, Decimal):
        return raw
    s = str(raw).strip()
    if not s:
        return default
    paren = _PAREN_NEG.match(s)
    is_negative = False
    if paren:
        s = paren.group("num").strip()
        is_negative = True
    if s.startswith(("-", "−", "－")):
        is_negative = not is_negative
        s = s[1:].strip()
    cleaned = _AMOUNT_CURRENCY_CHARS.sub("", s)
    try:
        val = Decimal(cleaned)
    except InvalidOperation:
        zh_val = _parse_zh_numeral(s)
        if zh_val is None:
            return default
        val = zh_val
    return -val if is_negative else val


def normalize_whitespace(s) -> str:
    """压缩连续空白为单个空格；首尾 strip。None → ''。"""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip())


# ───────────────────────────────────────
# 全半角归一化表
# ───────────────────────────────────────
_FULL_WIDTH_CHARS = (
    "０１２３４５６７８９"
    "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"
    "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
    "！＂＃＄％＆＇（）＊＋，－．／：；＜＝＞？＠"
)
_FULL_WIDTH_MAP = {ord(c): ord(c) - 0xFEE0 for c in _FULL_WIDTH_CHARS}
_FULL_WIDTH_MAP[0x3000] = ord(" ")  # 全角空格


def parse_text(raw, max_len: int = 500) -> str:
    """文本归一化：strip + 全半角 + 压空白 + 截断。"""
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    s = s.translate(_FULL_WIDTH_MAP)
    s = normalize_whitespace(s)
    if len(s) > max_len:
        s = s[:max_len]
    return s


_ACCOUNT_SUFFIX = re.compile(r"\s*(账号|账户|卡号|户号)\s*[:：]?\s*[\d\-*Xx]+\s*$")


def parse_counterparty(raw, max_len: int = 200) -> str:
    """parse_text + 剥离尾部"账号/账户/卡号/户号 xxx"（可能多级）。"""
    text = parse_text(raw, max_len=max_len)
    if not text:
        return ""
    while True:
        new_text = _ACCOUNT_SUFFIX.sub("", text).rstrip()
        if new_text == text:
            break
        text = new_text
    if len(text) > max_len:
        text = text[:max_len]
    return text
