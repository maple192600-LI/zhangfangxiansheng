"""解析模板 API 路由

GET  /api/parser-templates          — 列表
POST /api/parser-templates          — 创建
PUT  /api/parser-templates/{id}     — 更新
DELETE /api/parser-templates/{id}   — 删除（停用）
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from core.response import error, success, ErrorCode
from database import get_db
from services import bank_import_service as svc

router = APIRouter()


class TemplateCreateBody(BaseModel):
    template_name: str = Field(..., max_length=100)
    template_type: str = Field("bank", max_length=50)
    file_format: str = Field("xlsx", max_length=20)
    header_row: int = 0
    skip_rows: int = 0
    sample_headers: List[str] = []
    mapping_json: Dict[str, str]


class TemplateUpdateBody(BaseModel):
    template_name: Optional[str] = None
    template_type: Optional[str] = None
    file_format: Optional[str] = None
    header_row: Optional[int] = None
    skip_rows: Optional[int] = None
    sample_headers: Optional[List[str]] = None
    mapping_json: Optional[Dict[str, str]] = None


# ── 列表 ──

@router.get("/parser-templates")
def list_templates(
    template_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    result = svc.list_templates(db, template_type)
    return success(result)


# ── 创建 ──

@router.post("/parser-templates")
def create_template(body: TemplateCreateBody, db: Session = Depends(get_db)):
    try:
        result = svc.create_template(db, body.model_dump())
    except ValueError as e:
        return error(ErrorCode.PARAM_FORMAT, str(e))
    return success(result)
