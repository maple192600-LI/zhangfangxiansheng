"""master_match · §P4 · 4 个单位/账户匹配基元

契约锚点：docs/30_contracts/25_primitives_whitelist.md §P4

| 函数                | 职责                                   |
|---------------------|----------------------------------------|
| match_entity        | 别名库/相似度匹配 Entity               |
| match_account       | 别名/后四位/相似度匹配 Account         |
| register_alias      | 落库 account_aliases（置信度 ≥ 0.85）  |
| get_account_by_code | 按 account_code 精确查找               |
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Optional

from database import SessionLocal
from db.tables import Account, AccountAlias, Entity


def _similar(a: str, b: str) -> float:
    """[0,1] 相似度（difflib 比率）。"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _norm(s: str) -> str:
    return (s or "").strip()


def match_entity(hint: str, alias_library: dict) -> Optional[Entity]:
    """按 hint 匹配 Entity。

    alias_library: {alias_text: entity_code}
    优先级：alias_library → 全表 name / short_name 相似度（> 0.85 才取）
    """
    key = _norm(hint)
    if not key:
        return None
    with SessionLocal() as s:
        if key in alias_library:
            code = alias_library[key]
            ent = s.query(Entity).filter(Entity.entity_code == code).first()
            if ent is not None:
                s.expunge(ent)
            return ent
        candidates = s.query(Entity).all()
        best: Optional[Entity] = None
        best_score = 0.85
        for ent in candidates:
            score = max(
                _similar(key, ent.name),
                _similar(key, ent.short_name or ""),
            )
            if score > best_score:
                best_score = score
                best = ent
        if best is not None:
            s.expunge(best)
        return best


def match_account(
    hint: str, alias_library: dict, threshold: float = 0.85
) -> Optional[Account]:
    """按 hint 匹配 Account。

    alias_library: {alias_text: account_code}
    优先级：alias_library → account_aliases 表 → 后四位精确 → 名称/银行名相似度
    """
    key = _norm(hint)
    if not key:
        return None
    with SessionLocal() as s:
        # 1) alias_library
        if key in alias_library:
            code = alias_library[key]
            acc = s.query(Account).filter(Account.account_code == code).first()
            if acc is not None:
                s.expunge(acc)
            return acc
        # 2) account_aliases
        alias_row = (
            s.query(AccountAlias)
            .filter(AccountAlias.alias_text == key)
            .first()
        )
        if alias_row is not None:
            acc = s.query(Account).filter(Account.id == alias_row.account_id).first()
            if acc is not None:
                s.expunge(acc)
            return acc
        # 3) 后四位精确
        digits = "".join(ch for ch in key if ch.isdigit())
        if len(digits) >= 4:
            last4 = digits[-4:]
            acc = (
                s.query(Account).filter(Account.account_last_four == last4).first()
            )
            if acc is not None:
                s.expunge(acc)
                return acc
        # 4) 名称相似度
        candidates = s.query(Account).all()
        best: Optional[Account] = None
        best_score = threshold
        for acc in candidates:
            score = max(
                _similar(key, acc.account_alias or ""),
                _similar(key, acc.bank_name or ""),
            )
            if score > best_score:
                best_score = score
                best = acc
        if best is not None:
            s.expunge(best)
        return best


def register_alias(
    code: str, alias: str, confidence: float, alias_type: str = "自动"
) -> None:
    """把成功匹配到的新别名写入 account_aliases 表。

    - 仅支持 account 别名
    - confidence < 0.85 → 静默不写（避免污染）
    - 已有同 alias_text → 不重复写
    - code 对应 account 不存在 → 静默不写
    """
    code_s = _norm(code)
    alias_s = _norm(alias)
    if not code_s or not alias_s:
        return
    if confidence < 0.85:
        return
    with SessionLocal() as s:
        acc = s.query(Account).filter(Account.account_code == code_s).first()
        if acc is None:
            return
        existing = (
            s.query(AccountAlias)
            .filter(
                AccountAlias.account_id == acc.id,
                AccountAlias.alias_text == alias_s,
            )
            .first()
        )
        if existing is not None:
            return
        s.add(
            AccountAlias(
                account_id=acc.id,
                alias_text=alias_s,
                alias_type=alias_type,
            )
        )
        s.commit()


def get_account_by_code(code: str) -> Account:
    """按 account_code 精确查询；不存在 → KeyError。"""
    code_s = _norm(code)
    if not code_s:
        raise KeyError("account_code 不可为空")
    with SessionLocal() as s:
        acc = s.query(Account).filter(Account.account_code == code_s).first()
        if acc is None:
            raise KeyError(f"account_code={code_s!r} 不存在")
        s.expunge(acc)
        return acc
