"""看板 API — 指标 / 趋势 / 分布"""
import logging
from typing import Optional

from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import dashboard_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics")
def get_metrics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        data = svc.get_metrics(db, start_date, end_date)
        return success(data)
    except Exception as e:
        logger.error("获取看板指标失败: %s", str(e), exc_info=True)
        return error(5000, "获取看板指标失败")


@router.get("/trends")
def get_trends(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    try:
        data = svc.get_trends(db, days)
        return success(data)
    except Exception as e:
        logger.error("获取收支趋势失败: %s", str(e), exc_info=True)
        return error(5000, "获取收支趋势失败")


@router.get("/composition")
def get_composition(db: Session = Depends(get_db)):
    try:
        data = svc.get_composition(db)
        return success(data)
    except Exception as e:
        logger.error("获取账户分布失败: %s", str(e), exc_info=True)
        return error(5000, "获取账户分布失败")
