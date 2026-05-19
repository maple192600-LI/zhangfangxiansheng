"""Parser context service — builds master data context for rule center."""
from typing import Any, Dict

from sqlalchemy.orm import Session

from db.tables import Account, AccountAlias, Bank, Entity


def build_bank_parser_context(db: Session) -> Dict[str, Any]:
    """Build a controlled summary of master data for parser generation.

    Only includes structural information (codes, names, aliases).
    Does NOT include account numbers or full entity details.
    """
    entities = db.query(Entity).filter(Entity.status == "enabled").all()
    banks = db.query(Bank).filter(Bank.status == "enabled").all()
    accounts = db.query(Account).filter(Account.status == "enabled").all()

    entity_list = []
    for e in entities:
        entity_list.append({
            "entity_code": e.entity_code,
            "name": e.name,
            "short_name": e.short_name,
        })

    bank_list = []
    for b in banks:
        bank_list.append({
            "id": b.id,
            "bank_name": b.bank_name,
            "short_name": b.short_name,
        })

    account_list = []
    for a in accounts:
        aliases = db.query(AccountAlias).filter(AccountAlias.account_id == a.id).all()
        account_list.append({
            "entity_id": a.entity_id,
            "account_code": a.account_code,
            "account_alias": a.account_alias,
            "account_type": a.account_type,
            "instrument_type": a.instrument_type,
            "account_last_four": a.account_last_four,
            "has_online_banking": a.has_online_banking,
            "bank_id": a.bank_id,
            "aliases": [al.alias_text for al in aliases],
        })

    return {
        "entities": entity_list,
        "banks": bank_list,
        "accounts": account_list,
    }
