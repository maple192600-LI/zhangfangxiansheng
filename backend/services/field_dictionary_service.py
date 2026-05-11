"""Field dictionary and alias library service.

Migrated from legacy memory.get_field_dictionary / get_alias_library.
Provides canonical field definitions and alias normalization.
"""
from __future__ import annotations

import json
import os
from typing import Any


def get_field_dictionary() -> dict[str, dict[str, Any]]:
    """Load field dictionary from seed data or return defaults."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "data", "seed", "field_dictionary.json"
    )
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return _default_field_dictionary()


def get_alias_library() -> dict[str, Any]:
    """Load alias library from seed data."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "data", "seed", "alias_library.json"
    )
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def normalize_field_name(raw_name: str) -> str | None:
    """Normalize a raw column name to a canonical field key.

    Returns None if no match found.
    """
    field_dict = get_field_dictionary()
    raw_lower = raw_name.strip().lower()

    for field_key, field_info in field_dict.items():
        if field_key.lower() == raw_lower:
            return field_key
        cn_name = field_info.get("cn_name", "")
        if cn_name and cn_name == raw_name:
            return field_key
        for alias in field_info.get("aliases", []):
            if alias == raw_name:
                return field_key

    return None


def _default_field_dictionary() -> dict[str, dict[str, Any]]:
    return {
        "business_date": {
            "cn_name": "日期",
            "type": "DATE",
            "aliases": ["日期", "交易日期", "记账日期"],
        },
        "entity_code": {
            "cn_name": "单位编码",
            "type": "VARCHAR",
            "aliases": ["单位编码", "主体编码"],
        },
        "entity_name": {
            "cn_name": "单位名称",
            "type": "VARCHAR",
            "aliases": ["单位", "单位名称", "主体"],
        },
        "account_code": {
            "cn_name": "账户编码",
            "type": "VARCHAR",
            "aliases": ["账户编码", "账号"],
        },
        "account_name": {
            "cn_name": "账户名称",
            "type": "VARCHAR",
            "aliases": ["账户", "账户名称"],
        },
        "summary": {
            "cn_name": "摘要",
            "type": "TEXT",
            "aliases": ["摘要", "用途", "备注"],
        },
        "counterparty": {
            "cn_name": "对方",
            "type": "TEXT",
            "aliases": ["对方", "对方户名", "往来单位"],
        },
        "amount_in": {
            "cn_name": "收入",
            "type": "NUMERIC",
            "aliases": ["收入", "贷方", "进账"],
        },
        "amount_out": {
            "cn_name": "支出",
            "type": "NUMERIC",
            "aliases": ["支出", "借方", "出账"],
        },
        "rolling_balance": {
            "cn_name": "余额",
            "type": "NUMERIC",
            "aliases": ["余额", "账户余额"],
        },
    }
