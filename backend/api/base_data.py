"""基础数据 API — 查询 + 滚动余额重建"""
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
from core.response import success, error
from services import base_data_service as svc

router = APIRouter(prefix="/base-data", tags=["base-data"])


@router.get("")
def get_base_data(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    account_id: Optional[int] = Query(None),
    direction: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        result = svc.query_base_data(
            db, date_from, date_to, entity_id, account_id,
            direction, keyword, page, page_size,
        )
        return success(result)
    except ValueError as e:
        return error(4001, str(e))
    except Exception:
        return error(5000, "查询基础数据失败，请检查参数后重试")


@router.post("/rebuild")
def rebuild_balance(db: Session = Depends(get_db)):
    try:
        result = svc.rebuild_rolling_balance(db)
        return success(result)
    except Exception:
        return error(5000, "余额重建失败，请稍后重试")
