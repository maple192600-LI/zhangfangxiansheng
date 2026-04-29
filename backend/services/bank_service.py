"""银行信息 CRUD 服务层"""
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from db.tables import Account, Bank
from db.schemas import BankCreate, BankUpdate, PaginatedData
from services.master_data_service import _next_code, CODE_CONFIG


def get_bank_usage(db: Session, bank_id: int) -> Dict[str, Any]:
    """查询银行关联的账户列表"""
    obj = db.query(Bank).filter(Bank.id == bank_id).first()
    if not obj:
        raise ValueError("银行不存在")
    accounts = db.query(Account).filter(Account.bank_id == bank_id).all()
    return {
        "account_count": len(accounts),
        "accounts": [
            {
                "id": a.id,
                "account_code": a.account_code,
                "account_alias": a.account_alias,
                "entity_name": a.entity.short_name if a.entity else None,
            }
            for a in accounts
        ],
    }


def batch_action_banks(db: Session, ids: List[int], action: str) -> Dict[str, Any]:
    success, failed = 0, []
    for bid in ids:
        try:
            if action == "delete":
                delete_bank(db, bid)
            elif action in ("enable", "disable"):
                toggle_bank_status(db, bid, "enabled" if action == "enable" else "disabled")
            else:
                raise ValueError(f"不支持的操作: {action}")
            success += 1
        except ValueError as e:
            failed.append({"id": bid, "message": str(e)})
    return {"success": success, "failed": failed}


def list_banks(
    db: Session,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedData:
    q = db.query(Bank)
    if status:
        q = q.filter(Bank.status == status)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(or_(
            Bank.bank_name.like(kw),
            Bank.bank_code.like(kw),
            Bank.short_name.like(kw),
        ))
    total = q.count()
    total_pages = math.ceil(total / page_size) if page_size else 1
    items = (
        q.order_by(Bank.sort_order, Bank.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedData(
        items=[_bank_to_dict(b) for b in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_bank(db: Session, bank_id: int) -> Optional[Bank]:
    return db.query(Bank).filter(Bank.id == bank_id).first()


def create_bank(db: Session, data: BankCreate) -> Bank:
    cfg = CODE_CONFIG["bank"]
    code = data.bank_code or _next_code(db, Bank, cfg["field"], cfg["prefix"], cfg["digits"])
    existing = db.query(Bank).filter(Bank.bank_code == code).first()
    if existing:
        raise ValueError(f"银行编码已存在: {code}")
    existing_name = db.query(Bank).filter(Bank.bank_name == data.bank_name).first()
    if existing_name:
        raise ValueError(f"银行名称已存在: {data.bank_name}")
    dump = data.model_dump()
    dump["bank_code"] = code
    obj = Bank(**dump)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_bank(db: Session, bank_id: int, data: BankUpdate) -> Bank:
    obj = db.query(Bank).filter(Bank.id == bank_id).first()
    if not obj:
        raise ValueError("银行不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def toggle_bank_status(db: Session, bank_id: int, status: str) -> Bank:
    obj = db.query(Bank).filter(Bank.id == bank_id).first()
    if not obj:
        raise ValueError("银行不存在")
    obj.status = status
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def delete_bank(db: Session, bank_id: int) -> None:
    obj = db.query(Bank).filter(Bank.id == bank_id).first()
    if not obj:
        raise ValueError("银行不存在")
    ref_count = db.query(Account).filter(Account.bank_id == bank_id).count()
    if ref_count > 0:
        raise ValueError(f"该银行下存在 {ref_count} 个关联账户，无法删除")
    db.delete(obj)
    db.commit()


def _bank_to_dict(b: Bank) -> Dict[str, Any]:
    return {
        "id": b.id,
        "bank_code": b.bank_code,
        "bank_name": b.bank_name,
        "short_name": b.short_name,
        "cnaps_code": b.cnaps_code,
        "contact_phone": b.contact_phone,
        "website": b.website,
        "notes": b.notes,
        "status": b.status,
        "sort_order": b.sort_order,
        "created_at": b.created_at,
        "updated_at": b.updated_at,
    }
