"""主数据 CRUD 服务层

板块 / 法人 / 账户 / 别名 的全部业务逻辑。
"""
import math
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
    obj = Division(**data.model_dump())
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
    return PaginatedData(
        items=[_entity_to_dict(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def create_entity(db: Session, data: EntityCreate) -> Entity:
    existing = db.query(Entity).filter(Entity.entity_code == data.entity_code).first()
    if existing:
        raise ValueError(f"法人编码已存在: {data.entity_code}")
    obj = Entity(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_entity(db: Session, entity_id: int, data: EntityUpdate) -> Entity:
    obj = db.query(Entity).filter(Entity.id == entity_id).first()
    if not obj:
        raise ValueError("法人不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


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
    existing = db.query(Account).filter(Account.account_code == data.account_code).first()
    if existing:
        raise ValueError(f"账户编码已存在: {data.account_code}")
    obj = Account(**data.model_dump())
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
        .filter(FundEvent.account_id == account_id)
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

def _entity_to_dict(e: Entity) -> Dict[str, Any]:
    return {
        "id": e.id,
        "division_id": e.division_id,
        "entity_code": e.entity_code,
        "name": e.name,
        "short_name": e.short_name,
        "status": e.status,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }


def _account_to_dict(a: Account) -> Dict[str, Any]:
    return {
        "id": a.id,
        "entity_id": a.entity_id,
        "account_code": a.account_code,
        "account_alias": a.account_alias,
        "bank_name": a.bank_name,
        "branch_name": a.branch_name,
        "account_number": a.account_number,
        "account_type": a.account_type,
        "instrument_type": a.instrument_type,
        "input_method": a.input_method,
        "currency": a.currency,
        "initial_balance": float(a.initial_balance) if a.initial_balance else 0,
        "balance_date": a.balance_date,
        "status": a.status,
        "notes": a.notes,
        "entity_name": a.entity.short_name if a.entity else None,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }
