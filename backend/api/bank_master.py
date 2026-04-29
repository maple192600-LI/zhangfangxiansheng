"""银行信息 API 路由"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.response import error, success
from database import get_db
from db.schemas import BankCreate, BankUpdate, StatusToggle
from services import bank_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


class BatchAction(BaseModel):
    ids: List[int]
    action: str  # "enable" | "disable" | "delete"


@router.get("/banks")
def get_banks(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    result = svc.list_banks(db, status=status, keyword=keyword, page=page, page_size=page_size)
    return success(result.model_dump())


@router.get("/banks/{bank_id}")
def get_bank(bank_id: int, db: Session = Depends(get_db)):
    obj = svc.get_bank(db, bank_id)
    if not obj:
        return error(2001, "银行不存在")
    return success(svc._bank_to_dict(obj))


@router.post("/banks")
def create_bank(body: BankCreate, db: Session = Depends(get_db)):
    try:
        obj = svc.create_bank(db, body)
    except ValueError as e:
        return error(2001, str(e))
    return success(svc._bank_to_dict(obj))


@router.put("/banks/{bank_id}")
def update_bank(
    bank_id: int, body: BankUpdate, db: Session = Depends(get_db),
):
    try:
        obj = svc.update_bank(db, bank_id, body)
    except ValueError as e:
        return error(2001, str(e))
    return success(svc._bank_to_dict(obj))


@router.put("/banks/{bank_id}/status")
def toggle_bank_status(
    bank_id: int, body: StatusToggle, db: Session = Depends(get_db),
):
    try:
        obj = svc.toggle_bank_status(db, bank_id, body.status)
    except ValueError as e:
        return error(2001, str(e))
    return success({"id": obj.id, "status": obj.status})


@router.delete("/banks/{bank_id}")
def delete_bank(bank_id: int, db: Session = Depends(get_db)):
    try:
        svc.delete_bank(db, bank_id)
    except ValueError as e:
        return error(2001, str(e))
    return success(None, message="银行已删除")


@router.get("/banks/{bank_id}/usage")
def get_bank_usage(bank_id: int, db: Session = Depends(get_db)):
    try:
        return success(svc.get_bank_usage(db, bank_id))
    except ValueError as e:
        return error(2001, str(e))


@router.post("/banks/batch")
def batch_banks(body: BatchAction, db: Session = Depends(get_db)):
    return success(svc.batch_action_banks(db, body.ids, body.action))
