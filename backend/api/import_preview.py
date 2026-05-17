"""统一导入预览 API — 网银/手工快速录入/手工Excel 共用"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.response import error, success
from database import get_db
from services import import_preview_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import-preview", tags=["import-preview"])


class UpdateRowBody(BaseModel):
    updates: Dict[str, Any]


@router.get("/{batch_code}")
def get_preview(batch_code: str, db: Session = Depends(get_db)):
    try:
        result = svc.get_preview(db, batch_code)
        return success(result)
    except ValueError as e:
        return error(2001, str(e))
    except Exception as e:
        logger.error("获取预览失败: %s", e, exc_info=True)
        return error(5000, "获取预览失败")


@router.put("/{batch_code}/rows/{row_no}")
def update_row(batch_code: str, row_no: int, body: UpdateRowBody, db: Session = Depends(get_db)):
    try:
        result = svc.update_row(db, batch_code, row_no, body.updates)
        return success(result)
    except ValueError as e:
        return error(2001, str(e))
    except Exception as e:
        logger.error("更新行失败: %s", e, exc_info=True)
        return error(5000, "更新行失败")


@router.post("/{batch_code}/validate")
def validate_all(batch_code: str, db: Session = Depends(get_db)):
    try:
        result = svc.validate_all(db, batch_code)
        return success(result)
    except ValueError as e:
        return error(2001, str(e))
    except Exception as e:
        logger.error("校验失败: %s", e, exc_info=True)
        return error(5000, "校验失败")


@router.post("/{batch_code}/commit")
def commit(batch_code: str, db: Session = Depends(get_db)):
    try:
        result = svc.commit(db, batch_code)
        return success(result)
    except ValueError as e:
        return error(2003, str(e))
    except Exception as e:
        logger.error("提交失败: %s", e, exc_info=True)
        return error(5000, "提交失败")
