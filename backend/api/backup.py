"""备份恢复 API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import backup_service as svc
from services import log_service

router = APIRouter(prefix="/backups", tags=["backup"])


@router.get("")
def list_backups():
    try:
        data = svc.list_backups()
        return success(data)
    except Exception:
        return error(5000, "获取备份列表失败")


@router.post("/create")
def create_backup(db: Session = Depends(get_db)):
    try:
        data = svc.create_backup(db)
        log_service.write_log(db, action="backup_create", module="backup", detail={
            "filename": data.get("filename"),
            "size_mb": data.get("size_mb"),
        })
        return success(data)
    except Exception as e:
        return error(5000, f"创建备份失败: {str(e)}")


class RestoreRequest(BaseModel):
    filename: str


@router.post("/restore")
def restore_backup(req: RestoreRequest, db: Session = Depends(get_db)):
    try:
        data = svc.restore_backup(req.filename)
        log_service.write_log(db, action="backup_restore", module="backup", detail={
            "restored_from": req.filename,
        })
        return success(data)
    except ValueError as e:
        return error(2001, str(e))
    except Exception as e:
        return error(5000, f"恢复备份失败: {str(e)}")
