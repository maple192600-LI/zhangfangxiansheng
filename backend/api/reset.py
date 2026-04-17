"""恢复出厂 API"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import reset_service
from services import backup_service
from services import log_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reset", tags=["reset"])


@router.post("/factory")
def factory_reset(db: Session = Depends(get_db)):
    # 1. 先自动创建备份
    try:
        backup_data = backup_service.create_backup(db)
    except Exception as e:
        logger.error("出厂重置前自动备份失败: %s", str(e), exc_info=True)
        backup_data = {"filename": "备份失败"}

    # 2. 执行重置
    data = reset_service.factory_reset(db)

    # 3. 记录日志
    log_service.write_log(db, action="factory_reset", module="system", detail={
        "auto_backup": backup_data.get("filename"),
    })

    return success(data)
