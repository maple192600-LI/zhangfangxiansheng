"""解析模板 API 路由

GET  /api/parser-templates          — 列表
POST /api/parser-templates          — 创建
PUT  /api/parser-templates/{id}     — 更新
DELETE /api/parser-templates/{id}   — 删除
POST /api/parser-templates/batch-delete — 批量删除
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from core.response import error, success, ErrorCode
from database import get_db
from db.tables import ParserTemplate
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
    status: Optional[str] = None


class BatchDeleteBody(BaseModel):
    ids: List[int]


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


# ── 更新 ──

@router.put("/parser-templates/{template_id}")
def update_template(template_id: int, body: TemplateUpdateBody, db: Session = Depends(get_db)):
    tpl = db.query(ParserTemplate).filter(ParserTemplate.id == template_id).first()
    if not tpl:
        return error(ErrorCode.NOT_FOUND, "模板不存在")
    data = body.model_dump(exclude_none=True)
    for key, val in data.items():
        if key == "mapping_json" and isinstance(val, dict):
            import json
            val = json.dumps(val, ensure_ascii=False)
        if key == "sample_headers" and isinstance(val, list):
            import json
            val = json.dumps(val, ensure_ascii=False)
        setattr(tpl, key, val)
    db.commit()
    db.refresh(tpl)
    return success(svc._tpl_out(tpl))


# ── 单个删除 ──

@router.delete("/parser-templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tpl = db.query(ParserTemplate).filter(ParserTemplate.id == template_id).first()
    if not tpl:
        return error(ErrorCode.NOT_FOUND, "模板不存在")
    db.delete(tpl)
    db.commit()
    return success(None, "已删除")


# ── 批量删除 ──

@router.post("/parser-templates/batch-delete")
def batch_delete_templates(body: BatchDeleteBody, db: Session = Depends(get_db)):
    if not body.ids:
        return error(ErrorCode.PARAM_MISSING, "请选择要删除的模板")
    count = db.query(ParserTemplate).filter(ParserTemplate.id.in_(body.ids)).delete(synchronize_session=False)
    db.commit()
    return success({"deleted": count})
