"""test_master_match · §P4 · 4 函数单测

match_entity / match_account / register_alias / get_account_by_code
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from fund.primitives.master_match import (
    get_account_by_code,
    match_account,
    match_entity,
    register_alias,
)


# ──────────────────────────────────────────
# match_entity
# ──────────────────────────────────────────
def test_match_entity_alias_library_hit(primitives_db):
    ent = match_entity("某个客户昵称", {"某个客户昵称": "E001"})
    assert ent is not None
    assert ent.entity_code == "E001"


def test_match_entity_similarity_by_name(primitives_db):
    # hint 完全等于 name → 相似度 1.0
    ent = match_entity("示例科技有限公司", {})
    assert ent is not None
    assert ent.entity_code == "E001"


def test_match_entity_similarity_by_short_name(primitives_db):
    ent = match_entity("示例", {})
    assert ent is not None
    assert ent.entity_code == "E001"


def test_match_entity_no_match_returns_none(primitives_db):
    assert match_entity("完全不沾边的名字XYZ", {}) is None


def test_match_entity_empty_hint_returns_none(primitives_db):
    assert match_entity("", {}) is None
    assert match_entity("   ", {}) is None


def test_match_entity_alias_library_priority_over_similarity(primitives_db):
    # alias_library 指向 E002，但 hint 本身更像 E001 的 name
    ent = match_entity("示例科技有限公司", {"示例科技有限公司": "E002"})
    assert ent is not None
    assert ent.entity_code == "E002"


# ──────────────────────────────────────────
# match_account
# ──────────────────────────────────────────
def test_match_account_alias_library_hit(primitives_db):
    acc = match_account("任意外部名", {"任意外部名": "A001"})
    assert acc is not None
    assert acc.account_code == "A001"


def test_match_account_last_four_digits_match(primitives_db):
    # hint 含 4 位以上数字 → 取末 4 位精确匹配
    acc = match_account("张三 卡号 ****1234", {})
    assert acc is not None
    assert acc.account_last_four == "1234"
    assert acc.account_code == "A001"


def test_match_account_similarity_by_alias(primitives_db):
    # 完全等于 account_alias → 相似度 1.0
    acc = match_account("建行副户", {})
    assert acc is not None
    assert acc.account_code == "A002"


def test_match_account_no_match_returns_none(primitives_db):
    assert match_account("完全陌生XYZ", {}) is None


def test_match_account_empty_hint_returns_none(primitives_db):
    assert match_account("", {}) is None


def test_match_account_threshold_strict(primitives_db):
    # 提高 threshold 到 0.99，短 hint 无法达到
    assert match_account("工行", {}, threshold=0.99) is None


# ──────────────────────────────────────────
# register_alias & account_aliases 联动
# ──────────────────────────────────────────
def test_register_alias_then_match_via_alias_table(primitives_db):
    register_alias("A001", "客户X的备注", 0.9)
    acc = match_account("客户X的备注", {})
    assert acc is not None
    assert acc.account_code == "A001"


def test_register_alias_low_confidence_silent(primitives_db):
    register_alias("A002", "低置信别名", 0.5)
    # 不写入 → match_account 走不到 alias 表命中
    acc = match_account("低置信别名", {})
    assert acc is None


def test_register_alias_unknown_code_silent(primitives_db):
    # 不抛错，静默不写
    register_alias("A999", "xx", 0.9)


def test_register_alias_duplicate_silent(primitives_db):
    register_alias("A001", "重复别名", 0.9)
    register_alias("A001", "重复别名", 0.9)  # 第二次不抛、不重复写

    engine = primitives_db
    with engine.begin() as conn:
        cnt = conn.execute(
            text(
                "SELECT COUNT(*) FROM account_aliases "
                "WHERE alias_text='重复别名'"
            )
        ).scalar()
    assert cnt == 1


def test_register_alias_empty_args_silent(primitives_db):
    register_alias("", "x", 0.9)
    register_alias("A001", "", 0.9)
    # 不抛错，不写


# ──────────────────────────────────────────
# get_account_by_code
# ──────────────────────────────────────────
def test_get_account_by_code_found(primitives_db):
    acc = get_account_by_code("A001")
    assert acc.account_code == "A001"
    assert acc.account_alias == "工行主户"


def test_get_account_by_code_missing_raises(primitives_db):
    with pytest.raises(KeyError):
        get_account_by_code("A999")


def test_get_account_by_code_empty_raises(primitives_db):
    with pytest.raises(KeyError):
        get_account_by_code("")
