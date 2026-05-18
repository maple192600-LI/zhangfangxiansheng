from datetime import date, datetime

import pytest

from db.tables import Account, AccountAlias, Bank, Division, Entity
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
    db.flush()

    al1 = AccountAlias(account_id=a1.id, alias_text="测试公司基本户", alias_type="自动")
    al2 = AccountAlias(account_id=a3.id, alias_text="测试公司基本户", alias_type="自动")
    db.add_all([al1, al2])
    db.commit()
    return {
        "entities": [e1, e2], "banks": [boc, icbc],
        "accounts": [a1, a2, a3, a4, a5],
        "aliases": [al1, al2],
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


def _hints_with_candidates(entity_name="", bank_text_candidates=None, **kw):
    base = _hints(entity_name=entity_name, **kw)
    base["bank_text_candidates"] = bank_text_candidates or []
    return base


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


# ── 完整账号不存在时，不 fallback 到实体 ──

def test_account_number_no_match_does_not_fallback_to_entity(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(account_number="9999999999999999", entity_name="TestCo1"),
    )
    assert r["status"] == "unmatched"
    assert r["error_code"] == "ACCOUNT_HINT_NOT_FOUND"


# ── 银行强过滤后为空，不 fallback ──

def test_bank_filter_eliminated_returns_conflict(db_session, test_data):
    now = datetime.now()
    custom = Bank(bank_code="CUST", bank_name="自定义测试银行",
                  short_name="自测行", status="enabled",
                  created_at=now, updated_at=now)
    db_session.add(custom)
    db_session.flush()

    r = match_account_attribution(
        db_session,
        _hints(entity_name="TestCo1", bank_name="自测行"),
    )
    assert r["status"] == "unmatched"
    assert r["error_code"] == "BANK_ACCOUNT_CONFLICT"


# ── DB 银行归一化：short_name 精确匹配 ──

def test_bank_short_name_resolved_from_db(db_session, test_data):
    now = datetime.now()
    custom = Bank(bank_code="CUST", bank_name="自定义测试银行",
                  short_name="自测行", status="enabled",
                  created_at=now, updated_at=now)
    db_session.add(custom)
    db_session.commit()

    r = match_account_attribution(
        db_session,
        _hints(entity_name="TestCo1", bank_name="自测行"),
    )
    assert r["status"] == "unmatched"
    assert r["error_code"] == "BANK_ACCOUNT_CONFLICT"


# ── 新增银行主数据不改代码即可参与匹配 ──

def test_new_bank_data_no_code_change(db_session, test_data):
    now = datetime.now()
    e = test_data["entities"][0]
    new_bank = Bank(bank_code="NEWB", bank_name="新银行",
                    short_name="新行", status="enabled",
                    created_at=now, updated_at=now)
    db_session.add(new_bank)
    db_session.flush()

    new_acc = Account(
        entity_id=e.id, bank_id=new_bank.id,
        account_code="A010", account_alias="新行账户",
        bank_name="新银行", branch_name="新银行分行",
        account_number="1234567890123456", account_last_four="3456",
        account_type="基本户", instrument_type="银行存款",
        input_method="online", has_online_banking=True,
        status="enabled", currency="CNY",
        initial_balance=0, balance_date=date(2026, 1, 1),
        created_at=now, updated_at=now,
    )
    db_session.add(new_acc)
    db_session.commit()

    r = match_account_attribution(
        db_session,
        _hints(entity_name="TestCo1", bank_name="新行"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A010"
    assert r["match_reason"] == "entity_name_match"


# ── AccountAlias 精确匹配唯一账户 ──

def test_alias_unique_match(db_session, test_data):
    db_session.query(AccountAlias).delete()
    db_session.flush()

    a1 = test_data["accounts"][0]
    db_session.add(AccountAlias(
        account_id=a1.id, alias_text="唯一别名", alias_type="手动",
    ))
    db_session.commit()

    r = match_account_attribution(
        db_session,
        _hints(entity_name="唯一别名"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A001"
    assert r["match_reason"] == "alias_match"


# ── AccountAlias 多账户命中 → ambiguous ──

def test_alias_multiple_match(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(entity_name="测试公司基本户"),
    )
    assert r["status"] == "ambiguous"
    assert r["error_code"] == "MULTIPLE_ACCOUNT_MATCHES"
    assert len(r["candidates"]) == 2


# ── _BANK_NAMES 不存在于 backend ──

def test_no_bank_names_in_services():
    import services.bank_account_match_service as mod
    assert not hasattr(mod, "_BANK_NAMES")


# ── 银行 contains 匹配唯一时也可解析 ──

def test_bank_contains_unique_match(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints(entity_name="TestCo2", bank_name="中国工商"),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A005"


# ── 短名通过候选识别（DB short_name）──

def test_short_name_resolved_from_candidates(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints_with_candidates(
            entity_name="TestCo1",
            bank_text_candidates=["工行流水"],
        ),
    )
    # "工行流水" contains ICBC short_name "工行" → resolves ICBC
    # TestCo1 online accounts: A001 (BOC) → bank filter removes it → BANK_ACCOUNT_CONFLICT
    assert r["status"] == "unmatched"
    assert r["error_code"] == "BANK_ACCOUNT_CONFLICT"


# ── bank_code 通过候选识别 ──

def test_bank_code_resolved_from_candidates(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints_with_candidates(
            entity_name="TestCo2",
            bank_text_candidates=["ICBC_statement.xlsx"],
        ),
    )
    # "ICBC_statement.xlsx" contains ICBC bank_code "ICBC" → resolves ICBC
    # TestCo2 online: A003 (BOC), A005 (ICBC) → filter keeps A005
    assert r["status"] == "matched"
    assert r["account_code"] == "A005"


# ── 自定义银行短名通过候选识别 ──

def test_custom_bank_short_name_from_candidates(db_session, test_data):
    now = datetime.now()
    e = test_data["entities"][0]
    custom = Bank(bank_code="MYB", bank_name="我的测试银行",
                  short_name="我行", status="enabled",
                  created_at=now, updated_at=now)
    db_session.add(custom)
    db_session.flush()

    new_acc = Account(
        entity_id=e.id, bank_id=custom.id,
        account_code="A020", account_alias="我行账户",
        bank_name="我的测试银行", branch_name="我行支行",
        account_number="1111222233334444", account_last_four="4444",
        account_type="基本户", instrument_type="银行存款",
        input_method="online", has_online_banking=True,
        status="enabled", currency="CNY",
        initial_balance=0, balance_date=date(2026, 1, 1),
        created_at=now, updated_at=now,
    )
    db_session.add(new_acc)
    db_session.commit()

    r = match_account_attribution(
        db_session,
        _hints_with_candidates(
            entity_name="TestCo1",
            bank_text_candidates=["我行流水"],
        ),
    )
    assert r["status"] == "matched"
    assert r["account_code"] == "A020"


# ── 候选命中多个银行时不猜测 ──

def test_candidates_hit_multiple_banks_no_guess(db_session, test_data):
    r = match_account_attribution(
        db_session,
        _hints_with_candidates(
            entity_name="TestCo2",
            bank_text_candidates=["中行工行联合流水"],
        ),
    )
    # "中行工行联合流水" contains both "中行" (BOC) and "工行" (ICBC) → ambiguous bank
    # Bank not resolved → no bank filter → all online accounts kept → ambiguous
    assert r["status"] == "ambiguous"
    assert r["error_code"] == "MULTIPLE_ACCOUNT_MATCHES"
