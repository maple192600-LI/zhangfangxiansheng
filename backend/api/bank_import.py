"""银行流水导入 API 路由

POST /api/bank-import/upload   — 上传文件
POST /api/bank-import/preview  — 预览解析结果
POST /api/bank-import/commit   — 确认提交
"""
from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from core.response import error, success, ErrorCode
from database import get_db
from services import bank_import_service as svc

router = APIRouter()


# ── 请求体 ──

class PreviewBody(BaseModel):
    batch_code: str
    template_id: Optional[int] = None
    header_row: Optional[int] = None
    mapping: Optional[Dict[str, str]] = None


class CommitBody(BaseModel):
    batch_code: str
    parsed_rows: List[Dict[str, Any]]


# ── 上传 ──

@router.post("/bank-import/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        return error(ErrorCode.PARAM_MISSING, "缺少文件名")
    data = await file.read()
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
            template_id=body.template_id,
            header_row=body.header_row,
            mapping=body.mapping,
        )
    except ValueError as e:
        return error(ErrorCode.NOT_FOUND, str(e))
    return success(result)


# ── 确认提交 ──

@router.post("/bank-import/commit")
def commit(body: CommitBody, db: Session = Depends(get_db)):
    try:
        result = svc.commit(db, body.batch_code, body.parsed_rows)
    except ValueError as e:
        return error(ErrorCode.NOT_FOUND, str(e))
    return success(result)
