"""canonical · §P3 · 4 个 12 列 canonical 行产出基元

契约锚点：docs/30_contracts/25_primitives_whitelist.md §P3 + §C1 CANONICAL_12

| 函数           | 职责                                   |
|----------------|----------------------------------------|
| normalize_row  | 字段字典 → canonical 12 列             |
| emit_row       | 便捷构造器；12 列校验；金额互斥自动异常 |
| mark_row_state | 设置 state；互斥冲突强制覆盖为 '异常'  |
| derive_source  | input_method → source 枚举映射         |
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional, TypedDict


StateLiteral = Literal["正常", "待确认", "异常", "已作废"]
SourceLiteral = Literal[
    "网银导入", "手工录入", "现金录入", "票据录入", "财务公司单据"
]

_ALLOWED_STATES: frozenset[str] = frozenset({"正常", "待确认", "异常", "已作废"})
_ALLOWED_SOURCES: frozenset[str] = frozenset(
    {"网银导入", "手工录入", "现金录入", "票据录入", "财务公司单据"}
)

# §C1 · CANONICAL_12 · 列序冻结
CANONICAL_FIELDS: tuple[str, ...] = (
    "business_date",
    "entity_code",
    "entity_name",
    "account_code",
    "account_name",
    "summary",
    "counterparty",
    "amount_in",
    "amount_out",
    "rolling_balance",
    "state",
    "source",
)

_OPTIONAL_DEFAULTS: dict[str, object] = {
    "summary": None,
    "counterparty": None,
    "rolling_balance": None,
    "business_date": None,
    "state": "正常",
    "amount_in": Decimal("0"),
    "amount_out": Decimal("0"),
}


class CanonicalRow(TypedDict, total=True):
    business_date: Optional[date]
    entity_code: Optional[str]
    entity_name: Optional[str]
    account_code: Optional[str]
    account_name: Optional[str]
    summary: Optional[str]
    counterparty: Optional[str]
    amount_in: Decimal
    amount_out: Decimal
    rolling_balance: Optional[Decimal]
    state: str
    source: str


def emit_row(**fields) -> CanonicalRow:
    """构造 12 列 canonical 行。

    语义：
    - 允许缺省：summary/counterparty/rolling_balance/business_date/state/amount_in/amount_out
    - 必须提供：entity_code/entity_name/account_code/account_name/source
    - 多余列 → ValueError（CANONICAL_12 冻结，元数据由 Runtime 附加）
    - state/source 值校验
    - amount < 0 → ValueError
    - amount_in>0 且 amount_out>0 → 自动标 state='异常'（不抛；给 Agent 一次救赎）
    - amount/rolling_balance 自动转 Decimal
    """
    # 补缺省
    for f in CANONICAL_FIELDS:
        if f not in fields and f in _OPTIONAL_DEFAULTS:
            fields[f] = _OPTIONAL_DEFAULTS[f]
    # 再查必需
    missing = [f for f in CANONICAL_FIELDS if f not in fields]
    if missing:
        raise ValueError(
            f"emit_row 缺少 CANONICAL_12 列：{missing}；"
            f"必须 12 列全集（可缺省：{sorted(_OPTIONAL_DEFAULTS)}）"
        )
    # 多余列
    extra = [k for k in fields if k not in CANONICAL_FIELDS]
    if extra:
        raise ValueError(
            f"emit_row 多余列：{extra}；CANONICAL_12 冻结，元数据列由 Runtime 附加"
        )
    # 金额 → Decimal
    for amt in ("amount_in", "amount_out"):
        v = fields[amt]
        if v is None:
            fields[amt] = Decimal("0")
        elif not isinstance(v, Decimal):
            fields[amt] = Decimal(str(v))
    # 滚动余额
    rb = fields.get("rolling_balance")
    if rb is not None and not isinstance(rb, Decimal):
        fields["rolling_balance"] = Decimal(str(rb))
    # 枚举校验
    if fields["state"] not in _ALLOWED_STATES:
        raise ValueError(
            f"state 非法：{fields['state']!r} ∉ {sorted(_ALLOWED_STATES)}"
        )
    if fields["source"] not in _ALLOWED_SOURCES:
        raise ValueError(
            f"source 非法：{fields['source']!r} ∉ {sorted(_ALLOWED_SOURCES)}"
        )
    # 金额非负
    if fields["amount_in"] < 0 or fields["amount_out"] < 0:
        raise ValueError(
            f"amount 不得为负；amount_in={fields['amount_in']}, amount_out={fields['amount_out']}"
        )
    # 金额互斥 → 自动 '异常'
    if fields["amount_in"] > 0 and fields["amount_out"] > 0:
        fields["state"] = "异常"
    return CanonicalRow(**fields)  # type: ignore[typeddict-item]


def normalize_row(raw: dict) -> CanonicalRow:
    """字段字典 → CanonicalRow。

    把 raw dict 的 12 个 key 映射出来；缺字段填默认；source 必填。

    语义：
    - 仅透传 raw 中实际存在的 key；缺的交给 emit_row 按 _OPTIONAL_DEFAULTS 填
      （避免把 None 显式传入覆盖默认值，比如 state=None 不应覆盖默认的 '正常'）
    - source 缺或为 None → 立刻 ValueError（比 emit_row 更友好的早期报错）
    """
    if raw.get("source") is None:
        raise ValueError("normalize_row 要求 source 必填")
    fields: dict = {f: raw[f] for f in CANONICAL_FIELDS if f in raw}
    return emit_row(**fields)


def mark_row_state(row: CanonicalRow, state: StateLiteral) -> CanonicalRow:
    """返回浅拷贝并设置新 state；金额互斥时强制标 '异常'（覆盖入参）。"""
    if state not in _ALLOWED_STATES:
        raise ValueError(f"state 非法：{state!r}")
    new_row: CanonicalRow = dict(row)  # type: ignore[assignment]
    if row["amount_in"] > 0 and row["amount_out"] > 0:
        new_row["state"] = "异常"
    else:
        new_row["state"] = state
    return new_row


_INPUT_METHOD_TO_SOURCE: dict[str, SourceLiteral] = {
    "online_bank": "网银导入",
    "online-bank": "网银导入",
    "bank": "网银导入",
    "manual": "手工录入",
    "cash": "现金录入",
    "bill": "票据录入",
    "receipt": "票据录入",
    "finance_company": "财务公司单据",
    "finance-company": "财务公司单据",
}


def derive_source(input_method: str) -> SourceLiteral:
    """根据账户 input_method 字段映射 source 枚举。

    未知 input_method → ValueError（§C1 source 是枚举，不可自由值）。
    """
    if not input_method:
        raise ValueError("input_method 不可为空")
    key = str(input_method).strip().lower()
    if key not in _INPUT_METHOD_TO_SOURCE:
        raise ValueError(
            f"未知 input_method={input_method!r}；允许：{sorted(_INPUT_METHOD_TO_SOURCE)}"
        )
    return _INPUT_METHOD_TO_SOURCE[key]
