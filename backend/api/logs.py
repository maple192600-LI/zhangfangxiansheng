"""操作日志 API"""
from typing import Optional

from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import log_service as svc

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
def query_logs(
    module: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        data = svc.query_logs(db, module, action, start_date, end_date, page, page_size)
        return success(data)
    except Exception:
        return error(5000, "查询操作日志失败")
