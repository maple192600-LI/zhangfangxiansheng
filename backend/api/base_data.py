"""基础数据 API — 查询 + 滚动余额重建 + 批量删除"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
from core.response import success, error
from services import base_data_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/base-data", tags=["base-data"])


class BatchDeleteRequest(BaseModel):
    ids: List[int]


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
    except Exception as e:
        logger.error("查询基础数据失败: %s", str(e), exc_info=True)
        return error(5000, "查询基础数据失败，请检查参数后重试")


@router.post("/rebuild")
def rebuild_balance(db: Session = Depends(get_db)):
    try:
        result = svc.rebuild_rolling_balance(db)
        return success(result)
    except Exception as e:
        logger.error("余额重建失败: %s", str(e), exc_info=True)
        return error(5000, "余额重建失败，请稍后重试")


@router.post("/batch-delete")
def batch_delete(body: BatchDeleteRequest, db: Session = Depends(get_db)):
    from db.tables import FundEvent
    deleted = 0
    for fid in body.ids:
        row = db.query(FundEvent).filter(FundEvent.id == fid).first()
        if row:
            db.delete(row)
            deleted += 1
    db.commit()
    return success({"deleted": deleted, "total_requested": len(body.ids)})
