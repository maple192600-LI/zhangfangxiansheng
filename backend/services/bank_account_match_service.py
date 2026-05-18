"""银行对账单账户归属匹配服务

根据身份线索和主数据（banks / entities / accounts / account_aliases），
将银行对账单匹配到法人单位和银行账户。

匹配结果三态：matched / ambiguous / unmatched

契约锚点：docs/14_BANK_IMPORT_GENERALIZATION.md
"""
from typing import Optional

from sqlalchemy.orm import Session

from db.tables import Account, AccountAlias, Bank, Entity


def match_account_attribution(
    db: Session,
    identity_hints: dict,
    selected_account_code: Optional[str] = None,
) -> dict:
    hints = identity_hints.get("identity_hints", identity_hints)
    bank_hint = identity_hints.get("bank_hint", "")

    if selected_account_code:
        return _by_selected(db, selected_account_code)

    account_number = (hints.get("account_number") or "").strip()
    last_four = (hints.get("account_last_four") or "").strip()
    entity_hint = (hints.get("entity_name") or hints.get("account_name") or "").strip()
    bank_name = (hints.get("bank_name") or bank_hint or "").strip()

    has_account = bool(account_number)
    has_last_four = bool(last_four) and not has_account
    has_entity = bool(entity_hint)

    if not has_account and not has_last_four and not has_entity:
        return _unmatched(hints, "NO_IDENTITY_HINTS", "没有可用的身份线索")

    if has_account:
        return _by_account_number(db, account_number, bank_name, entity_hint, hints)

    if has_last_four:
        return _by_last_four(db, last_four, bank_name, entity_hint, hints)

    return _by_entity(db, entity_hint, bank_name, hints)


# ── Scenario A: user selected ──

def _by_selected(db: Session, account_code: str) -> dict:
    acc = db.query(Account).filter(
        Account.account_code == account_code,
        Account.status == "enabled",
    ).first()
    if not acc:
        return _unmatched({}, None, f"账户编码 {account_code} 不存在")
    ent = db.query(Entity).filter(Entity.id == acc.entity_id).first()
    return _ok(acc, ent, "user_selected", 1.0, {})


# ── Scenario B: full account number ──

def _by_account_number(db: Session, account_number: str, bank_name: str,
                       entity_hint: str, hints: dict) -> dict:
    candidates = db.query(Account).filter(
        Account.account_number == account_number,
        Account.status == "enabled",
    ).all()

    if bank_name and candidates:
        pre_count = len(candidates)
        candidates = _bank_filter(db, candidates, bank_name)
        if not candidates and pre_count > 0:
            return _unmatched(hints, "BANK_ACCOUNT_CONFLICT",
                              f"账号 {account_number} 匹配到账户但银行过滤后无结果")

    if len(candidates) == 1:
        acc = candidates[0]
        ent = db.query(Entity).filter(Entity.id == acc.entity_id).first()
        if entity_hint:
            conflict = _check_conflict(db, acc, entity_hint)
            if conflict:
                return conflict
        return _ok(acc, ent, "account_number_exact", 0.95, hints)

    if len(candidates) > 1:
        return _ambig(candidates, db, "MULTIPLE_ACCOUNT_MATCHES",
                      f"账号 {account_number} 匹配到 {len(candidates)} 个账户", hints)

    return _unmatched(hints, "ACCOUNT_HINT_NOT_FOUND",
                      f"账号 {account_number} 未匹配到账户")


# ── Scenario C: last four digits ──

def _by_last_four(db: Session, last_four: str, bank_name: str,
                  entity_hint: str, hints: dict) -> dict:
    candidates = db.query(Account).filter(
        Account.account_last_four == last_four,
        Account.status == "enabled",
    ).all()

    if bank_name and candidates:
        pre_count = len(candidates)
        candidates = _bank_filter(db, candidates, bank_name)
        if not candidates and pre_count > 0:
            return _unmatched(hints, "BANK_ACCOUNT_CONFLICT",
                              f"后四位 {last_four} 匹配到账户但银行过滤后无结果")

    if len(candidates) == 1:
        acc = candidates[0]
        ent = db.query(Entity).filter(Entity.id == acc.entity_id).first()
        if entity_hint:
            conflict = _check_conflict(db, acc, entity_hint)
            if conflict:
                return conflict
        return _ok(acc, ent, "account_last_four", 0.85, hints)

    if len(candidates) > 1:
        return _ambig(candidates, db, "MULTIPLE_ACCOUNT_MATCHES",
                      f"后四位 {last_four} 匹配到 {len(candidates)} 个账户", hints)

    if entity_hint:
        return _by_entity(db, entity_hint, bank_name, hints)

    return _unmatched(hints, "NO_ACCOUNT_MATCH", f"后四位 {last_four} 未匹配到账户")


# ── Scenario D: entity name only ──

def _by_entity(db: Session, name_hint: str, bank_name: str, hints: dict) -> dict:
    # Strategy 1: try AccountAlias
    alias_accounts = _find_accounts_by_alias(db, name_hint)
    if alias_accounts:
        candidates = alias_accounts
        if bank_name:
            pre_count = len(candidates)
            candidates = _bank_filter(db, candidates, bank_name)
            if not candidates and pre_count > 0:
                return _unmatched(hints, "BANK_ACCOUNT_CONFLICT",
                                  f"别名 '{name_hint}' 匹配到账户但银行过滤后无结果")
        if len(candidates) == 1:
            acc = candidates[0]
            ent = db.query(Entity).filter(Entity.id == acc.entity_id).first()
            return _ok(acc, ent, "alias_match", 0.80, hints)
        if len(candidates) > 1:
            return _ambig(candidates, db, "MULTIPLE_ACCOUNT_MATCHES",
                          f"别名 '{name_hint}' 匹配到 {len(candidates)} 个账户", hints)

    # Strategy 2: entity matching
    entity = _find_entity(db, name_hint)
    if not entity:
        return _unmatched(hints, "NO_ACCOUNT_MATCH", f"单位/户名 '{name_hint}' 未匹配到法人实体")

    accounts = db.query(Account).filter(
        Account.entity_id == entity.id,
        Account.status == "enabled",
    ).all()

    online = [a for a in accounts
              if a.has_online_banking or a.input_method in ("online", "网银")]
    if online:
        accounts = online

    if bank_name and accounts:
        pre_count = len(accounts)
        accounts = _bank_filter(db, accounts, bank_name)
        if not accounts and pre_count > 0:
            return _unmatched(hints, "BANK_ACCOUNT_CONFLICT",
                              f"实体 '{entity.short_name}' 的账户银行过滤后无结果")

    if len(accounts) == 1:
        return _ok(accounts[0], entity, "entity_name_match", 0.75, hints)

    if len(accounts) > 1:
        return _ambig(accounts, db, "MULTIPLE_ACCOUNT_MATCHES",
                      f"实体 '{entity.short_name}' 下有 {len(accounts)} 个网银账户", hints)

    return _unmatched(hints, "NO_ACCOUNT_MATCH", f"实体 '{entity.short_name}' 下无可用账户")


# ── helpers ──

def _find_entity(db: Session, hint: str) -> Optional[Entity]:
    h = hint.strip()
    if not h:
        return None
    for field in [Entity.entity_code, Entity.short_name, Entity.name]:
        e = db.query(Entity).filter(field == h, Entity.status == "enabled").first()
        if e:
            return e
    rows = db.query(Entity).filter(Entity.name.contains(h), Entity.status == "enabled").all()
    if len(rows) == 1:
        return rows[0]
    return None


def _resolve_bank(db: Session, bank_hint: str) -> Optional[Bank]:
    """Resolve bank hint against banks master data.

    Exact match on bank_name / short_name / bank_code, then contains match
    (unique only). Returns None if ambiguous or not found.
    """
    h = bank_hint.strip()
    if not h:
        return None
    bank = db.query(Bank).filter(
        (Bank.bank_name == h) | (Bank.short_name == h) | (Bank.bank_code == h),
        Bank.status == "enabled",
    ).first()
    if bank:
        return bank
    candidates = db.query(Bank).filter(
        (Bank.bank_name.contains(h)) | (Bank.short_name.contains(h)),
        Bank.status == "enabled",
    ).all()
    if len(candidates) == 1:
        return candidates[0]
    return None


def _bank_filter(db: Session, accounts: list, bank_hint: str) -> list:
    """Filter accounts by resolved bank. Returns original list if bank
    cannot be resolved. Returns empty list if bank resolved but no
    accounts match — caller must treat this as BANK_ACCOUNT_CONFLICT."""
    bank = _resolve_bank(db, bank_hint)
    if not bank:
        return accounts
    return [a for a in accounts if a.bank_id == bank.id]


def _find_accounts_by_alias(db: Session, hint: str) -> list:
    """Find enabled accounts whose AccountAlias.alias_text matches hint."""
    h = hint.strip()
    if not h:
        return []
    aliases = db.query(AccountAlias).filter(
        AccountAlias.alias_text == h,
    ).all()
    if not aliases:
        return []
    account_ids = [a.account_id for a in aliases]
    return db.query(Account).filter(
        Account.id.in_(account_ids),
        Account.status == "enabled",
    ).all()


def _check_conflict(db: Session, account: Account, entity_hint: str) -> Optional[dict]:
    acc_ent = db.query(Entity).filter(Entity.id == account.entity_id).first()
    if not acc_ent:
        return None
    hint_ent = _find_entity(db, entity_hint)
    if not hint_ent:
        return None
    if acc_ent.id != hint_ent.id:
        return {
            "status": "ambiguous",
            "entity_code": "", "entity_name": "",
            "account_code": "", "account_name": "",
            "confidence": 0.0,
            "match_reason": "entity_account_conflict",
            "candidates": [
                {"account_code": account.account_code, "account_name": account.account_alias,
                 "entity_code": acc_ent.entity_code, "entity_name": acc_ent.short_name},
                {"entity_code": hint_ent.entity_code, "entity_name": hint_ent.short_name,
                 "account_code": None, "account_name": None},
            ],
            "raw_hints": {},
            "error_code": "ENTITY_ACCOUNT_CONFLICT",
        }
    return None


def _ok(acc: Account, ent: Optional[Entity], reason: str, confidence: float,
        hints: dict) -> dict:
    return {
        "status": "matched",
        "entity_code": ent.entity_code if ent else "",
        "entity_name": ent.short_name if ent else "",
        "account_code": acc.account_code,
        "account_name": acc.account_alias,
        "confidence": confidence,
        "match_reason": reason,
        "candidates": [],
        "raw_hints": hints,
        "error_code": None,
    }


def _ambig(accounts: list, db: Session, error_code: str, reason: str,
           hints: dict) -> dict:
    cands = []
    for a in accounts:
        ent = db.query(Entity).filter(Entity.id == a.entity_id).first()
        cands.append({
            "account_code": a.account_code,
            "account_name": a.account_alias,
            "entity_code": ent.entity_code if ent else "",
            "entity_name": ent.short_name if ent else "",
        })
    return {
        "status": "ambiguous",
        "entity_code": "", "entity_name": "",
        "account_code": "", "account_name": "",
        "confidence": 0.0,
        "match_reason": reason,
        "candidates": cands,
        "raw_hints": hints,
        "error_code": error_code,
    }


def _unmatched(hints: dict, error_code: Optional[str], reason: str) -> dict:
    return {
        "status": "unmatched",
        "entity_code": "", "entity_name": "",
        "account_code": "", "account_name": "",
        "confidence": 0.0,
        "match_reason": reason,
        "candidates": [],
        "raw_hints": hints,
        "error_code": error_code,
    }
