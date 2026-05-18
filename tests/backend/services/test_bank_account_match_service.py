from datetime import date, datetime

import pytest

from db.tables import Account, Bank, Division, Entity
from services.bank_account_match_service import match_account_attribution


@pytest.fixture()
def test_data(db_session):
    return _seed(db_session)


def _seed(db):
    now = datetime.now()
    div = Division(division_code="DV1", name="Division 1",
                   status="enabled", created_at=now, updated_at=now)
    db.add(div)
    db.flush()

    e1 = Entity(division_id=div.id, entity_code="E001",
                name="测试建筑有限公司", short_name="TestCo1",
                status="enabled", created_at=now, updated_at=now)
    e2 = Entity(division_id=div.id, entity_code="E002",
                name="测试实业发展有限公司", short_name="TestCo2",
                status="enabled", created_at=now, updated_at=now)
    db.add_all([e1, e2])
    db.flush()

    boc = Bank(bank_code="BOC", bank_name="中国银行", short_name="中行",
               status="enabled", created_at=now, updated_at=now)
    icbc = Bank(bank_code="ICBC", bank_name="中国工商银行", short_name="工行",
                status="enabled", created_at=now, updated_at=now)
    db.add_all([boc, icbc])
    db.flush()

    a1 = Account(
        entity_id=e1.id, bank_id=boc.id,
        account_code="A001", account_alias="中行基本户",
        bank_name="中国银行", branch_name="中国银行北京分行",
        account_number="6217001234567890", account_last_four="7890",
        account_type="基本户", instrument_type="银行存款",
        input_method="online", has_online_banking=True,
        status="enabled", currency="CNY",
        initial_balance=0, balance_date=date(2026, 1, 1),
        created_at=now, updated_at=now,
    )
    a2 = Account(
        entity_id=e1.id, bank_id=icbc.id,
        account_code="A002", account_alias="工行一般户",
        bank_name="中国工商银行", branch_name="中国工商银行上海支行",
        account_number="6222021234567891", account_last_four="7891",
        account_type="一般户", instrument_type="银行存款",
        input_method="manual", has_online_banking=False,
        status="enabled", currency="CNY",
        initial_balance=0, balance_date=date(2026, 1, 1),
        created_at=now, updated_at=now,
    )
    a3 = Account(
        entity_id=e2.id, bank_id=boc.id,
        account_code="A003", account_alias="中行基本户",
        bank_name="中国银行", branch_name="中国银行深圳分行",
        account_number="6217009876543210", account_last_four="3210",
        account_type="基本户", instrument_type="银行存款",
        input_method="online", has_online_banking=True,
        status="enabled", currency="CNY",
        initial_balance=0, balance_date=date(2026, 1, 1),
        created_at=now, updated_at=now,
    )
    a4 = Account(
        entity_id=e2.id, bank_id=boc.id,
        account_code="A004", account_alias="中行手工户",
        bank_name="中国银行", branch_name="中国银行深圳分行",
        account_number="6217009876540001", account_last_four="0001",
        account_type="一般户", instrument_type="银行存款",
        input_method="manual", has_online_banking=False,
        status="enabled", currency="CNY",
        initial_balance=0, balance_date=date(2026, 1, 1),
        created_at=now, updated_at=now,
    )
    a5 = Account(
        entity_id=e2.id, bank_id=icbc.id,
        account_code="A005", account_alias="工行基本户",
        bank_name="中国工商银行", branch_name="中国工商银行广州支行",
        account_number="6222020000321012", account_last_four="3210",
        account_type="基本户", instrument_type="银行存款",
        input_method="online", has_online_banking=True,
        status="enabled", currency="CNY",
        initial_balance=0, balance_date=date(2026, 1, 1),
        created_at=now, updated_at=now,
    )
    db.add_all([a1, a2, a3, a4, a5])
    db.commit()
    return {
        "entities": [e1, e2], "banks": [boc, icbc],
        "accounts": [a1, a2, a3, a4, a5],
    }


def _hints(account_number="", account_last_four="", account_name="",
           entity_name="", bank_name="", branch_name=""):
    return {
        "bank_hint": bank_name,
        "identity_hints": {
            "account_number": account_number,
            "account_last_four": account_last_four,
            "account_name": account_name,
            "entity_name": entity_name,
            "bank_name": bank_name,
            "branch_name": branch_name,
            "filename_hint": "",
        },
    }


# ── 1. 账号+单位一致 → matched ──

def test_account_number_entity_consistent(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(account_number="6217001234567890", entity_name="TestCo1"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A001"
    assert r["entity_code"] == "E001"
    assert r["confidence"] == 0.95


# ── 2. 账号+单位冲突 → ENTITY_ACCOUNT_CONFLICT ──

def test_account_number_entity_conflict(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(account_number="6217001234567890", entity_name="TestCo2"),
    )
    assert r["status"] == "ambiguous"
    assert r["error_code"] == "ENTITY_ACCOUNT_CONFLICT"
    assert len(r["candidates"]) == 2


# ── 3. 只有完整账号 → matched ──

def test_account_number_only(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(account_number="6217001234567890"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A001"
    assert r["match_reason"] == "account_number_exact"


# ── 4. 后四位+银行唯一 → matched ──

def test_last_four_bank_unique(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(account_last_four="3210", bank_name="中国银行"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A003"
    assert r["match_reason"] == "account_last_four"


# ── 5. 后四位+多候选 → ambiguous ──

def test_last_four_multiple(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(account_last_four="3210"),
    )
    assert r["status"] == "ambiguous"
    assert r["error_code"] == "MULTIPLE_ACCOUNT_MATCHES"
    assert len(r["candidates"]) == 2


# ── 6. 只有单位+唯一网银 → matched ──

def test_entity_name_unique_online(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(entity_name="TestCo1"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A001"
    assert r["entity_code"] == "E001"
    assert r["match_reason"] == "entity_name_match"


# ── 7. 只有单位+多个网银 → ambiguous ──

def test_entity_name_multiple_online(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(entity_name="TestCo2"),
    )
    assert r["status"] == "ambiguous"
    assert r["error_code"] == "MULTIPLE_ACCOUNT_MATCHES"
    assert len(r["candidates"]) == 2


# ── 8. 无线索 → NO_IDENTITY_HINTS ──

def test_no_identity_hints(db_session, test_data):
    r = match_account_attribution(db_session, _hints())
    assert r["status"] == "unmatched"
    assert r["error_code"] == "NO_IDENTITY_HINTS"


# ── 9. selected_account_code 存在 → matched ──

def test_selected_account_exists(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(),
        selected_account_code="A001",
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A001"
    assert r["confidence"] == 1.0
    assert r["match_reason"] == "user_selected"


# ── 10. selected_account_code 不存在 → unmatched ──

def test_selected_account_not_found(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(),
        selected_account_code="NONEXISTENT",
    )
    assert r["status"] == "unmatched"


# ── entity_code 精确匹配 ──

def test_entity_code_exact_match(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(entity_name="E001"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A001"


# ── 银行约束过滤 ──

def test_entity_name_with_bank_constraint(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(entity_name="TestCo2", bank_name="中国银行"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A003"


# ── 无匹配实体 ──

def test_entity_name_no_match(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(entity_name="不存在的公司"),
    )
    assert r["status"] == "unmatched"
    assert r["error_code"] == "NO_ACCOUNT_MATCH"


# ── 账号匹配到但实体无可用账户（不会出现，但验证 fallback）──

def test_account_number_no_match_falls_to_entity(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(account_number="9999999999999999", entity_name="TestCo1"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A001"
    assert r["match_reason"] == "entity_name_match"
