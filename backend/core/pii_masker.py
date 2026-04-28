"""PII masking helpers for AI prompts."""
import math
import re
from typing import Sequence


def mask_account(value: object) -> str:
    text = str(value or "")
    digits = re.sub(r"\D", "", text)
    if len(digits) <= 4:
        return text
    return "*" * (len(digits) - 4) + digits[-4:]


def mask_name(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[0] + "某某"


def mask_amount(value: object) -> str:
    text = str(value or "").replace(",", "").replace("，", "").strip()
    try:
        amount = abs(float(text))
    except ValueError:
        return text
    if amount == 0:
        return "0"

    levels = [
        (100_000_000, "亿级"),
        (10_000_000, "千万级"),
        (1_000_000, "百万级"),
        (100_000, "十万级"),
        (10_000, "万级"),
        (1_000, "千级"),
        (100, "百级"),
        (10, "十级"),
    ]
    for threshold, label in levels:
        if amount >= threshold:
            return f"约{label}"
    return f"约{math.floor(amount)}元"


def mask_row(row: Sequence[object], headers: Sequence[str]) -> list[str]:
    masked: list[str] = []
    for idx, value in enumerate(row):
        header = headers[idx] if idx < len(headers) else ""
        masked.append(_mask_cell(value, header))
    return masked


def _mask_cell(value: object, header: str) -> str:
    header_text = str(header or "")
    if any(key in header_text for key in ("账号", "账户", "卡号")):
        return mask_account(value)
    if any(key in header_text for key in ("户名", "姓名", "名称", "对方")):
        return mask_name(value)
    if any(key in header_text for key in ("金额", "收入", "支出", "余额")):
        return mask_amount(value)
    return str(value or "")
