"""银行流水导入 API 路由

POST /api/bank-import/upload   — 上传文件
POST /api/bank-import/preview  — 预览解析结果
POST /api/bank-import/commit   — 确认提交
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from core.response import error, success, ErrorCode
from database import get_db
from services import bank_import_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


# ── 请求体 ──

class PreviewBody(BaseModel):
    batch_code: str
    template_id: Optional[int] = None
    header_row: Optional[int] = None
    mapping: Optional[Dict[str, Any]] = None


class CommitBody(BaseModel):
    batch_code: str
    parser_artifact_id: int


class AIParseBody(BaseModel):
    headers: List[str]
    sample_rows: Optional[List[List[str]]] = None
    agent_id: Optional[int] = None


class CommitByMappingBody(BaseModel):
    batch_code: str
    account_code: str
    mapping: Optional[Dict[str, Any]] = None
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    sample_headers: Optional[List[str]] = None


class SaveTemplateBody(BaseModel):
    template_name: str
    file_format: str = "xlsx"
    header_row: int = 0
    skip_rows: int = 0
    sample_headers: List[str] = []
    mapping_json: Dict[str, Any]


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
        result = svc.commit(db, body.batch_code, body.parser_artifact_id)
    except ValueError as e:
        return error(ErrorCode.NOT_FOUND, str(e))
    return success(result)


# ── 基于映射直接提交 ──

@router.post("/bank-import/commit-by-mapping")
def commit_by_mapping(body: CommitByMappingBody, db: Session = Depends(get_db)):
    try:
        result = svc.commit_by_mapping(
            db,
            batch_code=body.batch_code,
            account_code=body.account_code,
            mapping=body.mapping,
            template_id=body.template_id,
            template_name=body.template_name,
            sample_headers=body.sample_headers,
        )
    except ValueError as e:
        return error(ErrorCode.NOT_FOUND, str(e))
    return success(result)


# ── AI 智能解析表头 ──

@router.post("/bank-import/ai-parse")
def ai_parse(body: AIParseBody, db: Session = Depends(get_db)):
    try:
        result = svc.ai_parse_headers(db, body.headers, body.sample_rows, agent_id=body.agent_id)
        return success(result)
    except Exception as e:
        logger.error("AI解析表头失败: %s", str(e), exc_info=True)
        return error(5000, "AI解析表头失败，请查看操作日志")


# ── 保存为规则模板 ──

@router.post("/bank-import/save-template")
def save_template(body: SaveTemplateBody, db: Session = Depends(get_db)):
    try:
        result = svc.create_template(db, {
            "template_name": body.template_name,
            "template_type": "bank",
            "file_format": body.file_format,
            "header_row": body.header_row,
            "skip_rows": body.skip_rows,
            "sample_headers": body.sample_headers,
            "mapping_json": body.mapping_json,
            "created_by": "ai_assist",
        })
        return success(result)
    except Exception as e:
        logger.error("保存规则模板失败: %s", str(e), exc_info=True)
        return error(5000, "保存规则模板失败，请查看操作日志")
