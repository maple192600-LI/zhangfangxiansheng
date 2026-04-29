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


def delete_division(db: Session, division_id: int, force: bool = False, cascade: bool = False) -> None:
    """删除核算组织。cascade=True 时同时删除下属单位及其账户；force=True 仅解除关联。"""
    obj = db.query(Division).filter(Division.id == division_id).first()
    if not obj:
        raise ValueError("板块不存在")
    linked_entities = db.query(Entity).filter(Entity.division_id == division_id).all()
    if linked_entities and not force and not cascade:
        raise ValueError(f"该核算组织下存在 {len(linked_entities)} 个单位，请先确认后再删除")
    if cascade:
        # 级联删除：先删下属单位的账户，再删单位（用 SQL 避免触发 FundEvent relationship）
        ent_ids = [ent.id for ent in linked_entities]
        if ent_ids:
            db.execute(Account.__table__.delete().where(Account.entity_id.in_(ent_ids)))
            db.execute(Entity.__table__.delete().where(Entity.id.in_(ent_ids)))
    else:
        # force 模式：仅解除关联
        db.query(Entity).filter(Entity.division_id == division_id).update({"division_id": None})
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


def delete_entity(db: Session, entity_id: int, cascade: bool = False) -> None:
    """删除单位。cascade=True 时同时删除关联账户。"""
    obj = db.query(Entity).filter(Entity.id == entity_id).first()
    if not obj:
        raise ValueError("单位不存在")
    linked_accounts = db.query(Account).filter(Account.entity_id == entity_id).all()
    if linked_accounts and not cascade:
        codes = ", ".join(a.account_code for a in linked_accounts[:5])
        raise ValueError(f"该单位下存在 {len(linked_accounts)} 个账户（{codes}），请先删除账户或使用级联删除")
    # 级联：先删除关联账户（用 SQL 避免触发 FundEvent relationship）
    for acc in linked_accounts:
        db.execute(Account.__table__.delete().where(Account.id == acc.id))
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
# 批量操作
# ──────────────────────────────────────────

def batch_action_divisions(db: Session, ids: List[int], action: str, cascade: bool = False) -> Dict[str, Any]:
    success, failed = 0, []
    for did in ids:
        try:
            if action == "delete":
                delete_division(db, did, cascade=cascade)
            elif action in ("enable", "disable"):
                toggle_division_status(db, did, "enabled" if action == "enable" else "disabled")
            else:
                raise ValueError(f"不支持的操作: {action}")
            success += 1
        except ValueError as e:
            failed.append({"id": did, "message": str(e)})
        except Exception as e:
            db.rollback()
            failed.append({"id": did, "message": str(e)})
    return {"success": success, "failed": failed}


def batch_action_entities(db: Session, ids: List[int], action: str, cascade: bool = False) -> Dict[str, Any]:
    success, failed = 0, []
    for eid in ids:
        try:
            if action == "delete":
                delete_entity(db, eid, cascade=cascade)
            elif action in ("enable", "disable"):
                toggle_entity_status(db, eid, "enabled" if action == "enable" else "disabled")
            else:
                raise ValueError(f"不支持的操作: {action}")
            success += 1
        except ValueError as e:
            failed.append({"id": eid, "message": str(e)})
        except Exception as e:
            db.rollback()
            failed.append({"id": eid, "message": str(e)})
    return {"success": success, "failed": failed}


def batch_action_accounts(db: Session, ids: List[int], action: str) -> Dict[str, Any]:
    success, failed = 0, []
    for aid in ids:
        try:
            acc = db.query(Account).filter(Account.id == aid).first()
            if not acc:
                raise ValueError("账户不存在")
            if action in ("enable", "disable"):
                acc.status = "enabled" if action == "enable" else "disabled"
                acc.updated_at = datetime.now()
                db.commit()
                success += 1
            elif action == "delete":
                # 用原始 SQL 检查是否有关联的资金流水（避免 ORM 模型列名不匹配问题）
                try:
                    from sqlalchemy import text as _sql_text
                    result = db.execute(
                        _sql_text("SELECT COUNT(*) FROM fund_events WHERE account_id = :aid OR account_code = :acode"),
                        {"aid": acc.id, "acode": acc.account_code}
                    )
                    ref = result.scalar()
                    if ref and ref > 0:
                        raise ValueError(f"账户 {acc.account_code} 有 {ref} 条关联资金流水，无法删除")
                except ValueError:
                    raise
                except Exception:
                    pass  # 表可能不存在或无此列，跳过检查
                # 用原始 SQL 删除，避免 ORM 的 fund_events relationship 触发加载不匹配的列
                db.execute(Account.__table__.delete().where(Account.id == acc.id))
                db.commit()
                success += 1
            else:
                raise ValueError(f"不支持的操作: {action}")
        except ValueError as e:
            failed.append({"id": aid, "message": str(e)})
        except Exception as e:
            db.rollback()
            failed.append({"id": aid, "message": str(e)})

    # 删除操作后自动清理孤立数据（无账户的空单位、无单位的空核算组织）
    if action == "delete" and success > 0:
        _cleanup_orphans(db)

    return {"success": success, "failed": failed}


def _cleanup_orphans(db: Session) -> None:
    """清理孤立数据：删除没有关联账户的空单位，以及没有关联单位的空核算组织。"""
    # 1. 找出有账户的单位 ID
    entity_ids_with_accounts = set(
        eid for (eid,) in
        db.query(Account.entity_id).filter(Account.entity_id.isnot(None)).distinct().all()
    )

    # 2. 找出没有账户的单位并删除
    if entity_ids_with_accounts:
        orphan_entities = db.query(Entity).filter(~Entity.id.in_(entity_ids_with_accounts)).all()
    else:
        orphan_entities = db.query(Entity).all()

    if orphan_entities:
        ent_ids = [e.id for e in orphan_entities]
        db.execute(Entity.__table__.delete().where(Entity.id.in_(ent_ids)))

    # 3. 找出有单位的核算组织 ID
    division_ids_with_entities = set(
        did for (did,) in
        db.query(Entity.division_id).filter(Entity.division_id.isnot(None)).distinct().all()
    )

    # 4. 找出没有单位的核算组织并删除
    if division_ids_with_entities:
        orphan_divisions = db.query(Division).filter(~Division.id.in_(division_ids_with_entities)).all()
    else:
        orphan_divisions = db.query(Division).all()

    if orphan_divisions:
        div_ids = [d.id for d in orphan_divisions]
        db.execute(Division.__table__.delete().where(Division.id.in_(div_ids)))

    # 5. 如果所有账户都被删除了，清除 column_meta.json 缓存
    remaining = db.query(Account).count()
    if remaining == 0:
        _clear_column_meta()

    db.commit()


# ──────────────────────────────────────────
# 批量导入
# ──────────────────────────────────────────

# 字段别名映射：一个逻辑字段可以对应多个 Excel 列名
# key = 内部逻辑字段名, value = 可能出现在 Excel 表头的列名列表
FIELD_ALIASES = {
    "division_name":   ["核算组织", "板块名称", "板块", "核算组织名称"],
    "entity_name":     ["单位名称", "法人全称", "法人名称", "单位全称"],
    "entity_short":    ["单位简称", "法人简称", "简称"],
    "entity_code":     ["单位编码", "法人编码", "单位编号"],
    "bank_name":       ["开户银行", "银行", "银行名称"],
    "account_number":  ["银行账号", "账号", "银行账号/卡号"],
    "branch_name":     ["银行账户", "开户行名称", "开户网点", "账户名称", "开户行", "网点名称", "开户行网点"],
    "account_code":    ["账户编号", "账户编码", "账户代码"],
    "last_four":       ["账户后四位", "后四位"],
    "account_type":    ["账户类型"],
    "instrument_type": ["资金类型", "工具类型", "资金性质"],
    "has_online":      ["是否网银", "网银"],
    "input_method":    ["录入方式"],
    "currency":        ["币种"],
    "initial_balance": ["期初余额", "余额"],
    "balance_date":    ["余额日期", "日期"],
    "in_report":       ["是否纳入日报", "纳入日报"],
    "allow_manual":    ["是否允许手工录入", "允许手工录入", "是否允许手工"],
    "status":          ["状态"],
    "notes":           ["备注", "说明"],
}

# 导入字段名 → API 返回字段名 的映射
FIELD_TO_API = {
    "division_name": "division_name",
    "entity_name": "entity_full_name",
    "entity_short": "entity_name",
    "entity_code": "entity_code",
    "bank_name": "bank_name",
    "account_number": "account_number",
    "branch_name": "branch_name",
    "account_code": "account_code",
    "last_four": "account_last_four",
    "account_type": "account_type",
    "instrument_type": "instrument_type",
    "has_online": "has_online_banking",
    "input_method": "input_method",
    "currency": "currency",
    "initial_balance": "initial_balance",
    "balance_date": "balance_date",
    "in_report": "include_in_daily_report",
    "allow_manual": "allow_manual_entry",
    "status": "status",
    "notes": "notes",
}

# 渲染类型（前端根据 type 决定如何渲染单元格）
FIELD_RENDER_TYPES = {
    "division_name": "text",
    "entity_name": "text",
    "entity_short": "text",
    "entity_code": "text",
    "bank_name": "text",
    "account_number": "text",
    "branch_name": "text",
    "account_code": "code",
    "last_four": "text",
    "account_type": "tag",
    "instrument_type": "tag",
    "has_online": "bool",
    "input_method": "input_method",
    "currency": "text",
    "initial_balance": "money",
    "balance_date": "text",
    "in_report": "bool",
    "allow_manual": "bool",
    "status": "status",
    "notes": "text",
}


def _column_meta_path() -> str:
    """列元数据文件路径"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "column_meta.json")


def _clear_column_meta() -> None:
    """删除列元数据缓存文件"""
    path = _column_meta_path()
    if os.path.isfile(path):
        os.remove(path)


def save_column_meta(matched_columns: Dict[str, str]) -> None:
    """导入后保存列元数据：{api_field_key: {label, type}}"""
    columns = []
    for field_key, user_label in matched_columns.items():
        api_key = FIELD_TO_API.get(field_key)
        if not api_key:
            continue
        render_type = FIELD_RENDER_TYPES.get(field_key, "text")
        columns.append({"key": api_key, "label": user_label, "type": render_type})
    path = _column_meta_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"columns": columns}, f, ensure_ascii=False, indent=2)


def load_column_meta() -> List[Dict[str, str]]:
    """读取已保存的列元数据，返回 [{key, label, type}, ...]"""
    path = _column_meta_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("columns", [])
    except Exception:
        return []


def _build_column_map(header_row) -> Dict[str, int]:
    """根据表头行动态构建 字段名→列索引 的映射。

    遍历表头每个单元格，尝试匹配 FIELD_ALIASES 中的列名。
    返回 {内部字段名: 列索引(0-based)} 字典。
    """
    col_map: Dict[str, int] = {}
    for col_idx, cell in enumerate(header_row):
        if not cell:
            continue
        header = str(cell).strip()
        if not header:
            continue
        for field_name, aliases in FIELD_ALIASES.items():
            if field_name in col_map:
                continue  # 已匹配，不覆盖
            if header in aliases:
                col_map[field_name] = col_idx
                break
    return col_map


def _parse_bool(val) -> bool:
    """解析布尔值：是/否/true/false/1/0"""
    if not val:
        return False
    s = str(val).strip().lower()
    return s in ("是", "true", "1", "yes")


def _parse_input_method(val) -> str:
    """解析录入方式：网银导入→bank_import, 手工填写→manual, 原值保留"""
    if not val:
        return "manual"
    s = str(val).strip()
    if s in ("网银导入", "bank_import"):
        return "bank_import"
    if s in ("手工填写", "手工录入", "manual"):
        return "manual"
    return s


def _parse_status(val) -> str:
    """解析状态：启用→enabled, 停用/已注销→disabled"""
    if not val:
        return "enabled"
    s = str(val).strip()
    if s in ("启用", "enabled"):
        return "enabled"
    if s in ("停用", "已注销", "disabled"):
        return "disabled"
    return s


def batch_import_accounts(db: Session, file_data: bytes, filename: str) -> Dict[str, Any]:
    fmt = detect_format(filename)
    if fmt == "unknown":
        raise ValueError("不支持的文件格式，仅支持 xls/xlsx")

    rows = read_file_from_bytes(file_data, filename, fmt)
    if len(rows) < 2:
        raise ValueError("文件内容为空")

    # ── 动态表头映射：根据第一行表头自动识别列位置 ──
    header_row = rows[0]
    col_map = _build_column_map(header_row)

    # 检查是否识别到足够的列
    if not col_map:
        raise ValueError("无法识别表头，请确保第一行包含列名（如：核算组织、单位名称、银行账号 等）")

    # 辅助函数：安全取值
    def _get(row_vals, field_name: str, default: str = "") -> str:
        idx = col_map.get(field_name)
        if idx is None or idx >= len(row_vals):
            return default
        v = row_vals[idx]
        if v is None:
            return default
        return str(v).strip()

    # 跳过表头行
    data_rows = rows[1:]
    # 跳过提示行（如果第2行包含"必填"/"怎么理解"等说明文字）
    if data_rows and data_rows[0]:
        first_cell = str(data_rows[0][0] or "").strip()
        if first_cell and ("必填" in first_cell or "怎么理解" in first_cell or "字段名" in first_cell):
            data_rows = data_rows[1:]

    created_divisions = 0
    created_entities = 0
    created_accounts = 0
    errors = []

    division_cache: Dict[str, int] = {}  # name -> id
    entity_cache: Dict[str, int] = {}  # code -> id
    account_cache: Dict[str, int] = {}  # code -> id

    # 预加载已有数据
    for d in db.query(Division).all():
        division_cache[d.name] = d.id
    for e in db.query(Entity).all():
        entity_cache[e.entity_code] = e.id
    for a in db.query(Account).all():
        account_cache[a.account_code] = a.id

    for ri, row in enumerate(data_rows):
        row_no = ri + 2
        vals = [str(c).strip() if c and str(c).strip() else "" for c in row]

        # 通过动态映射取值
        div_name    = _get(vals, "division_name")
        ent_name    = _get(vals, "entity_name")
        ent_short   = _get(vals, "entity_short")
        ent_code    = _get(vals, "entity_code")
        bank_name   = _get(vals, "bank_name")
        acc_number  = _get(vals, "account_number")
        branch_name = _get(vals, "branch_name")
        acc_code    = _get(vals, "account_code")
        last_four   = _get(vals, "last_four")
        acc_type    = _get(vals, "account_type")
        inst_type   = _get(vals, "instrument_type")
        has_online  = _get(vals, "has_online")
        input_meth  = _get(vals, "input_method")
        currency    = _get(vals, "currency")
        balance_str = _get(vals, "initial_balance")
        date_str    = _get(vals, "balance_date")
        in_report   = _get(vals, "in_report")
        allow_man   = _get(vals, "allow_manual")
        status_str  = _get(vals, "status")
        notes       = _get(vals, "notes")

        # 跳过空行
        if not acc_code and not ent_code and not div_name and not acc_number and not ent_name:
            continue

        # 自动生成账户编号（ZH0001）如果没填
        if not acc_code:
            acc_cfg = CODE_CONFIG["account"]
            acc_code = _next_code(db, Account, acc_cfg["field"], acc_cfg["prefix"], acc_cfg["digits"])

        # 单位编码也支持自动生成
        if not ent_code and ent_name:
            ent_cfg = CODE_CONFIG["entity"]
            ent_code = _next_code(db, Entity, ent_cfg["field"], ent_cfg["prefix"], ent_cfg["digits"])

        if not ent_code:
            errors.append(f"第{row_no}行: 缺少单位编码且无法自动生成")
            continue

        # 自动创建核算组织（板块）
        if div_name and div_name not in division_cache:
            div_cfg = CODE_CONFIG["division"]
            div_code = _next_code(db, Division, div_cfg["field"], div_cfg["prefix"], div_cfg["digits"])
            div = Division(division_code=div_code, name=div_name, sort_order=len(division_cache), status="enabled")
            db.add(div)
            db.flush()
            division_cache[div_name] = div.id
            created_divisions += 1

        # 自动创建单位（法人）
        if ent_code not in entity_cache:
            if not ent_name:
                errors.append(f"第{row_no}行: 新单位缺少名称")
                continue
            # 自动生成简称：取名称前2-4个字
            if not ent_short:
                ent_short = ent_name[:4] if len(ent_name) > 4 else ent_name
            div_id = division_cache.get(div_name) if div_name else None
            ent = Entity(
                division_id=div_id,
                entity_code=ent_code,
                name=ent_name,
                short_name=ent_short,
                status="enabled",
            )
            db.add(ent)
            db.flush()
            entity_cache[ent_code] = ent.id
            created_entities += 1

        # 账户去重
        if acc_code in account_cache:
            errors.append(f"第{row_no}行: 账户编号 {acc_code} 已存在，跳过")
            continue

        # 解析余额
        init_balance = 0.0
        if balance_str:
            try:
                init_balance = float(balance_str.replace(",", "").replace("，", ""))
            except ValueError:
                init_balance = 0.0

        # 解析日期（balance_date 是 NOT NULL，没填则默认今天）
        balance_date = date.today()
        if date_str:
            from core.parser_engine import normalize_date
            ds = normalize_date(date_str)
            if ds:
                balance_date = date.fromisoformat(ds)

        # 解析后四位（从银行账号自动提取如果没填）
        parsed_last_four = last_four.strip()
        if not parsed_last_four and acc_number and len(acc_number) >= 4:
            parsed_last_four = acc_number[-4:]

        acc = Account(
            entity_id=entity_cache[ent_code],
            account_code=acc_code,
            account_alias=branch_name or acc_type or acc_code,
            bank_name=bank_name or None,
            branch_name=branch_name or None,
            account_number=acc_number or None,
            account_last_four=parsed_last_four or None,
            account_type=acc_type or "其他账户",
            instrument_type=inst_type or "银行存款",
            input_method=_parse_input_method(input_meth),
            has_online_banking=_parse_bool(has_online),
            include_in_daily_report=_parse_bool(in_report) if in_report else True,
            allow_manual_entry=_parse_bool(allow_man) if allow_man else True,
            currency=currency or "CNY",
            initial_balance=init_balance,
            balance_date=balance_date,
            status=_parse_status(status_str) if status_str else "enabled",
            notes=notes or None,
        )
        db.add(acc)
        db.flush()
        account_cache[acc_code] = acc.id
        created_accounts += 1

    db.commit()

    # 将列映射信息附加到返回结果，便于调试
    matched_headers = {k: header_row[v] if v < len(header_row) else "?" for k, v in col_map.items()}

    # 保存列元数据（用户模板的列名 → 前端显示用）
    save_column_meta(matched_headers)

    return {
        "total_rows": len(data_rows),
        "created_divisions": created_divisions,
        "created_entities": created_entities,
        "created_accounts": created_accounts,
        "errors": errors[:20],
        "error_count": len(errors),
        "matched_columns": matched_headers,
    }
