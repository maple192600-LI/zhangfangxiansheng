"""首页 API — 总览 / 待办 / 快捷入口 / 系统状态"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import home_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    try:
        data = svc.get_overview(db)
        return success(data)
    except Exception as e:
        logger.error("获取首页总览失败: %s", str(e), exc_info=True)
        return error(5000, "获取首页总览失败")


@router.get("/todos")
def get_todos(db: Session = Depends(get_db)):
    try:
        data = svc.get_todos(db)
        return success(data)
    except Exception as e:
        logger.error("获取待办数据失败: %s", str(e), exc_info=True)
        return error(5000, "获取待办数据失败")


@router.get("/quick-links")
def get_quick_links(db: Session = Depends(get_db)):
    try:
        data = svc.get_quick_links(db)
        return success(data)
    except Exception as e:
        logger.error("获取快捷入口失败: %s", str(e), exc_info=True)
        return error(5000, "获取快捷入口失败")


@router.get("/system-status")
def get_system_status(db: Session = Depends(get_db)):
    try:
        data = svc.get_system_status(db)
        return success(data)
    except Exception as e:
        logger.error("获取系统状态失败: %s", str(e), exc_info=True)
        return error(5000, "获取系统状态失败")
