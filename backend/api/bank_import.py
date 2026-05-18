"""银行流水导入 API 路由

POST /api/bank-import/upload   — 上传文件
POST /api/bank-import/preview  — 预览解析结果

最终提交通过 POST /api/import-preview/{batch_code}/commit 完成。
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from core.response import error, success, ErrorCode
from database import get_db
from services import bank_import_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


# ── 请求体 ──

class PreviewBody(BaseModel):
    batch_code: str
    parser_artifact_id: Optional[int] = None


# ── 上传 ──

@router.post("/bank-import/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        return error(ErrorCode.PARAM_MISSING, "缺少文件名")
    MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB
    data = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(data) > MAX_UPLOAD_SIZE:
        return error(ErrorCode.PARAM_FORMAT, "文件大小超过 20MB 限制")
    if not data:
        return error(ErrorCode.PARAM_MISSING, "文件为空")
    try:
        result = svc.upload_file(db, data, file.filename)
    except ValueError as e:
        return error(ErrorCode.FILE_READ_FAIL, str(e))
    return success(result)


# ── 预览 ──

@router.post("/bank-import/preview")
def preview(body: PreviewBody, db: Session = Depends(get_db)):
    try:
        result = svc.preview(
            db,
            batch_code=body.batch_code,
            parser_artifact_id=body.parser_artifact_id,
        )
    except ValueError as e:
        return error(ErrorCode.NOT_FOUND, str(e))
    return success(result)
