"""Shared Fund Agent skill builders used by runtime tests and harness."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CASH_JOURNAL_PLACEHOLDERS_18 = [
    "报表标题",
    "开始期间",
    "结束期间",
    "板块",
    "核算方式",
    "开户行",
    "账户信息",
    "银行编号",
    "月",
    "日",
    "月初余额",
    "摘要",
    "收入",
    "支出",
    "余额",
    "本月收入小计",
    "本月支出小计",
    "月末余额",
]


@dataclass
class SampleCheckLog:
    placeholder_bound: int = 0
    placeholder_unbound: int = 0
    placeholder_extra: int = 0

    def model_dump(self) -> dict[str, int]:
        return {
            "placeholder_bound": self.placeholder_bound,
            "placeholder_unbound": self.placeholder_unbound,
            "placeholder_extra": self.placeholder_extra,
        }


def parser_imports() -> list[str]:
    return [
        "fund.primitives.sheet_ops",
        "fund.primitives.value_parsers",
        "fund.primitives.canonical",
        "fund.primitives.base_queries",
    ]


def rule_imports() -> list[str]:
    return [
        "fund.primitives.template_fill",
        "fund.primitives.base_queries",
        "fund.primitives.aggregations",
    ]


def build_parser_code(*, kind: str, default_account_code: str) -> str:
    source_method = "bank" if kind == "bank" else "manual"
    return f'''from decimal import Decimal

from fund.primitives.sheet_ops import read_sheet, detect_header_row, extract_headers, iter_data_rows, is_empty_row
from fund.primitives.value_parsers import parse_date, parse_amount, parse_text, parse_counterparty
from fund.primitives.canonical import emit_row, derive_source
from fund.primitives.base_queries import account_field


HEADER_CANDIDATES = {{
    "business_date": ["日期", "交易日期", "记账日期", "入账日期", "Date", "date"],
    "entity_code": ["单位编码", "主体编码", "EntityId", "entity_code"],
    "entity_name": ["单位", "主体", "公司", "Entity", "entity_name"],
    "account_code": ["账户编码", "账号编码", "AccountId", "account_code"],
    "account_name": ["账户", "银行账户", "账号", "Account", "account_name"],
    "summary": ["摘要", "用途", "交易摘要", "备注", "Summary", "summary"],
    "counterparty": ["对方", "对方户名", "对方账户", "Counterparty", "counterparty"],
    "amount_in": ["收入", "收方金额", "贷方金额", "入账金额", "Income", "amount_in"],
    "amount_out": ["支出", "付方金额", "借方金额", "出账金额", "Expense", "amount_out"],
    "amount": ["金额", "发生额", "交易金额", "Amount", "amount"],
    "direction": ["方向", "收支方向", "借贷方向", "Direction", "direction"],
    "rolling_balance": ["余额", "账户余额", "Balance", "rolling_balance"],
}}
DEFAULT_ACCOUNT_CODE = {default_account_code!r}
SOURCE_METHOD = {source_method!r}


def _pick(headers, field):
    direct = {{str(name).strip().lower(): col for name, col in headers.items()}}
    for candidate in HEADER_CANDIDATES[field]:
        key = candidate.strip().lower()
        if key in direct:
            return direct[key]
    for name, col in headers.items():
        lname = str(name).strip().lower()
        for candidate in HEADER_CANDIDATES[field]:
            c = candidate.strip().lower()
            if c and (c in lname or lname in c):
                return col
    return None


def _value(row, col):
    return row.get(col) if col is not None else None


def _split_amount(row, mapping):
    amount_in = parse_amount(_value(row, mapping.get("amount_in")))
    amount_out = parse_amount(_value(row, mapping.get("amount_out")))
    if amount_in or amount_out:
        return max(amount_in, Decimal("0")), max(amount_out, Decimal("0"))
    amount = parse_amount(_value(row, mapping.get("amount")))
    direction = parse_text(_value(row, mapping.get("direction"))).lower()
    if amount < 0:
        return Decimal("0"), -amount
    if "支" in direction or "付" in direction or "借" in direction or "out" in direction or "debit" in direction:
        return Decimal("0"), amount
    return amount, Decimal("0")


def parse(wb, ctx):
    sheet = read_sheet(wb, index=ctx.get("sheet_index", 0))
    header_row = detect_header_row(sheet)
    headers = extract_headers(sheet, header_row)
    mapping = {{field: _pick(headers, field) for field in HEADER_CANDIDATES}}
    default_account = ctx.get("account_code") or DEFAULT_ACCOUNT_CODE

    for raw in iter_data_rows(sheet, header_row + 1):
        if is_empty_row(raw):
            continue
        account_code = parse_text(_value(raw, mapping.get("account_code"))) or default_account
        entity_code = parse_text(_value(raw, mapping.get("entity_code")))
        entity_name = parse_text(_value(raw, mapping.get("entity_name")))
        account_name = parse_text(_value(raw, mapping.get("account_name")))
        if account_code:
            try:
                if not entity_code:
                    entity_code = account_field(account_code, "entity_code")
                if not entity_name:
                    entity_name = account_field(account_code, "entity_name")
                if not account_name:
                    account_name = account_field(account_code, "account_name")
            except KeyError:
                if not entity_code:
                    entity_code = account_code
                if not entity_name:
                    entity_name = entity_code
                if not account_name:
                    account_name = account_code
        amount_in, amount_out = _split_amount(raw, mapping)
        yield emit_row(
            business_date=parse_date(_value(raw, mapping.get("business_date"))),
            entity_code=entity_code,
            entity_name=entity_name,
            account_code=account_code,
            account_name=account_name,
            summary=parse_text(_value(raw, mapping.get("summary"))),
            counterparty=parse_counterparty(_value(raw, mapping.get("counterparty"))),
            amount_in=amount_in,
            amount_out=amount_out,
            rolling_balance=parse_amount(_value(raw, mapping.get("rolling_balance"))) if mapping.get("rolling_balance") else None,
            source=derive_source(SOURCE_METHOD),
        )
'''


def build_cash_rule(template_id: int | None, placeholders: list[str]) -> tuple[dict[str, Any], dict[str, Any], SampleCheckLog]:
    bindings: dict[str, Any] = {
        "报表标题": {"primitive": "const", "value": "现金日记账"},
        "开始期间": {"primitive": "date_range_start"},
        "结束期间": {"primitive": "date_range_end"},
        "板块": {"primitive": "entity_field", "params": {"field": "division_name"}},
        "核算方式": {"primitive": "const", "value": "收付实现制"},
        "开户行": {"primitive": "account_field", "params": {"field": "bank_name"}},
        "账户信息": {"primitive": "account_field", "params": {"field": "account_name"}},
        "银行编号": {"primitive": "account_field", "params": {"field": "account_last_four"}},
        "月初余额": {"primitive": "opening_balance"},
        "本月收入小计": {"primitive": "sum_field", "params": {"field": "amount_in"}},
        "本月支出小计": {"primitive": "sum_field", "params": {"field": "amount_out"}},
        "月末余额": {"primitive": "closing_balance"},
    }
    for placeholder in placeholders:
        bindings.setdefault(placeholder, {"primitive": "const", "value": placeholder})
    return bindings, {}, SampleCheckLog(placeholder_bound=len(bindings))
