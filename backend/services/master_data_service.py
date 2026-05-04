"""主数据 CRUD 服务层

板块 / 法人 / 账户 / 别名 的全部业务逻辑。
"""
import json
import logging
import math
import os
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from db.tables import (
    Account, AccountAlias, Division, Entity, FundEvent,
)
from db.schemas import (
    AccountCreate, AccountTreeNode, AccountUpdate, AliasCreate,
    DivisionCreate, DivisionUpdate, EntityCreate, EntityTreeGroup,
    EntityUpdate, InitialBalanceSet, PaginatedData,
)
from core.parser_engine import read_file_from_bytes, detect_format

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────
# 自动编码配置与生成
# ──────────────────────────────────────────
CODE_CONFIG = {
    "division": {"prefix": "HZ", "digits": 4, "field": "division_code"},
    "entity":   {"prefix": "DW", "digits": 4, "field": "entity_code"},
    "bank":     {"prefix": "YH", "digits": 4, "field": "bank_code"},
    "account":  {"prefix": "ZH", "digits": 4, "field": "account_code"},
}


def _next_code(db: Session, model_class, code_field: str, prefix: str, digits: int) -> str:
    """查询当前最大编号，返回 prefix + 递增序号。允许断码（跳过已删除的）。"""
    pattern = f"{prefix}%"
    # 查找所有匹配前缀的编码，取最大序号
    rows = db.query(getattr(model_class, code_field)).filter(
        getattr(model_class, code_field).like(pattern)
    ).all()
    max_seq = 0
    for (code,) in rows:
        num_part = code[len(prefix):]
        if num_part.isdigit():
            seq = int(num_part)
            if seq > max_seq:
                max_seq = seq
    next_seq = max_seq + 1
    return f"{prefix}{str(next_seq).zfill(digits)}"


# ──────────────────────────────────────────
# 板块
# ──────────────────────────────────────────

def list_divisions(db: Session, status: Optional[str] = None) -> List[Division]:
    q = db.query(Division)
    if status:
        q = q.filter(Division.status == status)
    return q.order_by(Division.sort_order, Division.id).all()


def create_division(db: Session, data: DivisionCreate) -> Division:
    existing = db.query(Division).filter(Division.name == data.name).first()
    if existing:
        raise ValueError(f"板块名称已存在: {data.name}")
    cfg = CODE_CONFIG["division"]
    code = data.division_code or _next_code(db, Division, cfg["field"], cfg["prefix"], cfg["digits"])
    dump = data.model_dump()
    dump["division_code"] = code
    if "division_code" in dump and dump.get("division_code"):
        dup = db.query(Division).filter(Division.division_code == dump["division_code"]).first()
        if dup:
            raise ValueError(f"核算组织编码已存在: {dump['division_code']}")
    obj = Division(**dump)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_division(db: Session, division_id: int, data: DivisionUpdate) -> Division:
    obj = db.query(Division).filter(Division.id == division_id).first()
    if not obj:
        raise ValueError("板块不存在")
    if data.name is not None:
        dup = db.query(Division).filter(
            Division.name == data.name, Division.id != division_id
        ).first()
        if dup:
            raise ValueError(f"板块名称已存在: {data.name}")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def toggle_division_status(db: Session, division_id: int, status: str) -> Division:
    obj = db.query(Division).filter(Division.id == division_id).first()
    if not obj:
        raise ValueError("板块不存在")
    obj.status = status
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def get_division_usage(db: Session, division_id: int) -> Dict[str, Any]:
    """查询核算组织下关联的单位列表"""
    obj = db.query(Division).filter(Division.id == division_id).first()
    if not obj:
        raise ValueError("板块不存在")
    units = db.query(Entity).filter(Entity.division_id == division_id).all()
    return {
        "unit_count": len(units),
        "units": [{"id": u.id, "entity_code": u.entity_code, "name": u.name, "short_name": u.short_name} for u in units],
    }


def delete_division(db: Session, division_id: int, force: bool = False) -> None:
    """删除核算组织。严格递进：名下有单位时拒绝删除。"""
    obj = db.query(Division).filter(Division.id == division_id).first()
    if not obj:
        raise ValueError("核算组织不存在")
    linked_entities = db.query(Entity).filter(Entity.division_id == division_id).all()
    if linked_entities:
        names = "、".join(e.short_name or e.name for e in linked_entities[:5])
        raise ValueError(f"该核算组织下存在 {len(linked_entities)} 个单位（{names}），请先删除所有单位后再删除核算组织")
    db.execute(Division.__table__.delete().where(Division.id == division_id))
    db.commit()


# ──────────────────────────────────────────
# 法人
# ──────────────────────────────────────────

def list_entities(
    db: Session,
    division_id: Optional[int] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedData:
    q = db.query(Entity)
    if division_id is not None:
        q = q.filter(Entity.division_id == division_id)
    if status:
        q = q.filter(Entity.status == status)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(or_(Entity.name.like(kw), Entity.entity_code.like(kw)))
    total = q.count()
    total_pages = math.ceil(total / page_size) if page_size else 1
    items = (
        q.order_by(Entity.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # 批量查 division_name
    div_ids = list({e.division_id for e in items if e.division_id})
    div_map = {}
    if div_ids:
        for d in db.query(Division).filter(Division.id.in_(div_ids)).all():
            div_map[d.id] = d.name
    return PaginatedData(
        items=[_entity_to_dict(e, division_name=div_map.get(e.division_id)) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def create_entity(db: Session, data: EntityCreate) -> Entity:
    cfg = CODE_CONFIG["entity"]
    code = data.entity_code or _next_code(db, Entity, cfg["field"], cfg["prefix"], cfg["digits"])
    # 唯一性校验
    existing = db.query(Entity).filter(Entity.entity_code == code).first()
    if existing:
        raise ValueError(f"单位编码已存在: {code}")
    dump = data.model_dump()
    dump["entity_code"] = code
    obj = Entity(**dump)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_entity(db: Session, entity_id: int, data: EntityUpdate) -> Entity:
    obj = db.query(Entity).filter(Entity.id == entity_id).first()
    if not obj:
        raise ValueError("单位不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def toggle_entity_status(db: Session, entity_id: int, status: str) -> Entity:
    obj = db.query(Entity).filter(Entity.id == entity_id).first()
    if not obj:
        raise ValueError("单位不存在")
    obj.status = status
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def get_entity_usage(db: Session, entity_id: int) -> Dict[str, Any]:
    """查询单位下关联的账户列表"""
    obj = db.query(Entity).filter(Entity.id == entity_id).first()
    if not obj:
        raise ValueError("单位不存在")
    accounts = db.query(Account).filter(Account.entity_id == entity_id).all()
    return {
        "account_count": len(accounts),
        "accounts": [{"id": a.id, "account_code": a.account_code, "account_alias": a.account_alias, "account_type": a.account_type} for a in accounts],
    }


def delete_entity(db: Session, entity_id: int) -> None:
    """删除单位。严格递进：名下有银行账户时拒绝删除。"""
    obj = db.query(Entity).filter(Entity.id == entity_id).first()
    if not obj:
        raise ValueError("单位不存在")
    linked_accounts = db.query(Account).filter(Account.entity_id == entity_id).all()
    if linked_accounts:
        codes = "、".join(f"{a.account_code}({a.bank_name or a.account_type})" for a in linked_accounts[:5])
        raise ValueError(f"该单位下存在 {len(linked_accounts)} 个银行账户（{codes}），请先到「银行账户」中删除所有账户后再删除单位")
    db.execute(Entity.__table__.delete().where(Entity.id == entity_id))
    db.commit()


# ──────────────────────────────────────────
# 账户
# ──────────────────────────────────────────

def list_accounts(
    db: Session,
    entity_id: Optional[int] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    account_type: Optional[str] = None,
    instrument_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedData:
    q = db.query(Account).options(joinedload(Account.entity))
    if entity_id is not None:
        q = q.filter(Account.entity_id == entity_id)
    if status:
        q = q.filter(Account.status == status)
    if account_type:
        q = q.filter(Account.account_type == account_type)
    if instrument_type:
        q = q.filter(Account.instrument_type == instrument_type)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(or_(
            Account.account_alias.like(kw),
            Account.account_code.like(kw),
            Account.bank_name.like(kw),
            Account.account_number.like(kw),
        ))
    total = q.count()
    total_pages = math.ceil(total / page_size) if page_size else 1
    items = (
        q.order_by(Account.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedData(
        items=[_account_to_dict(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_accounts_tree(db: Session) -> List[EntityTreeGroup]:
    entities = (
        db.query(Entity)
        .filter(Entity.status == "enabled")
        .order_by(Entity.id)
        .all()
    )
    result: List[EntityTreeGroup] = []
    for ent in entities:
        accounts = (
            db.query(Account)
            .outerjoin(AccountAlias)
            .filter(Account.entity_id == ent.id)
            .order_by(Account.id)
            .all()
        )
        account_nodes = []
        for acc in accounts:
            aliases = (
                db.query(AccountAlias)
                .filter(AccountAlias.account_id == acc.id)
                .all()
            )
            account_nodes.append(AccountTreeNode(
                id=acc.id,
                account_code=acc.account_code,
                account_alias=acc.account_alias,
                account_type=acc.account_type,
                status=acc.status,
                aliases=aliases,
            ))
        result.append(EntityTreeGroup(
            entity_id=ent.id,
            entity_name=ent.short_name,
            accounts=account_nodes,
        ))
    return result


def create_account(db: Session, data: AccountCreate) -> Account:
    cfg = CODE_CONFIG["account"]
    code = data.account_code or _next_code(db, Account, cfg["field"], cfg["prefix"], cfg["digits"])
    existing = db.query(Account).filter(Account.account_code == code).first()
    if existing:
        raise ValueError(f"账户编码已存在: {code}")
    dump = data.model_dump()
    dump["account_code"] = code
    # 自动填充 account_alias
    if not dump.get("account_alias"):
        dump["account_alias"] = dump.get("account_type", code)
    obj = Account(**dump)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_account(db: Session, account_id: int, data: AccountUpdate) -> Account:
    obj = db.query(Account).filter(Account.id == account_id).first()
    if not obj:
        raise ValueError("账户不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def set_initial_balance(
    db: Session, account_id: int, data: InitialBalanceSet
) -> Account:
    obj = db.query(Account).filter(Account.id == account_id).first()
    if not obj:
        raise ValueError("账户不存在")
    event_count = (
        db.query(FundEvent)
        .filter(FundEvent.account_code == obj.account_code)
        .count()
    )
    if event_count > 0:
        raise ValueError("该账户已有资金流水，无法修改期初余额")
    obj.initial_balance = data.initial_balance
    obj.balance_date = data.balance_date
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


# ──────────────────────────────────────────
# 别名
# ──────────────────────────────────────────

def list_aliases(db: Session, account_id: int) -> List[AccountAlias]:
    return (
        db.query(AccountAlias)
        .filter(AccountAlias.account_id == account_id)
        .order_by(AccountAlias.id)
        .all()
    )


def create_alias(db: Session, account_id: int, data: AliasCreate) -> AccountAlias:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise ValueError("账户不存在")
    obj = AccountAlias(account_id=account_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_alias(db: Session, account_id: int, alias_id: int) -> None:
    obj = (
        db.query(AccountAlias)
        .filter(AccountAlias.id == alias_id, AccountAlias.account_id == account_id)
        .first()
    )
    if not obj:
        raise ValueError("别名不存在")
    db.delete(obj)
    db.commit()


# ──────────────────────────────────────────
# 内部辅助
# ──────────────────────────────────────────

def _entity_to_dict(e: Entity, division_name: str = None) -> Dict[str, Any]:
    return {
        "id": e.id,
        "division_id": e.division_id,
        "division_name": division_name,
        "entity_code": e.entity_code,
        "name": e.name,
        "full_name": e.name,
        "short_name": e.short_name,
        "status": e.status,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }


def _account_to_dict(a: Account) -> Dict[str, Any]:
    div_name = None
    div_code = None
    ent_code = None
    ent_full_name = None
    if a.entity:
        ent_code = a.entity.entity_code
        ent_full_name = a.entity.name
        if a.entity.division:
            div_name = a.entity.division.name
            div_code = a.entity.division.division_code
    return {
        "id": a.id,
        "entity_id": a.entity_id,
        "bank_id": a.bank_id,
        "division_name": div_name,
        "division_code": div_code,
        "entity_code": ent_code,
        "entity_full_name": ent_full_name,
        "entity_name": a.entity.short_name if a.entity else None,
        "account_code": a.account_code,
        "account_alias": a.account_alias,
        "bank_name": a.bank_name,
        "branch_name": a.branch_name,
        "account_number": a.account_number,
        "account_last_four": a.account_last_four,
        "account_type": a.account_type,
        "instrument_type": a.instrument_type,
        "input_method": a.input_method,
        "has_online_banking": a.has_online_banking if a.has_online_banking is not None else False,
        "include_in_daily_report": a.include_in_daily_report if a.include_in_daily_report is not None else True,
        "allow_manual_entry": a.allow_manual_entry if a.allow_manual_entry is not None else True,
        "currency": a.currency,
        "initial_balance": float(a.initial_balance) if a.initial_balance else 0,
        "balance_date": a.balance_date,
        "status": a.status,
        "notes": a.notes,
        "bank_short_name": a.bank.short_name if a.bank else None,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


# ──────────────────────────────────────────
# Re-export from batch module (backward compatibility)
# ──────────────────────────────────────────

from services.master_data_batch import (  # noqa: E402
    batch_action_divisions,
    batch_action_entities,
    batch_action_accounts,
    batch_import_accounts,
    load_column_meta,
    save_column_meta,
    FIELD_ALIASES,
    FIELD_TO_API,
    FIELD_RENDER_TYPES,
)

