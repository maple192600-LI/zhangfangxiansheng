"""手工流水 API — 快速录入 + Excel上传/预览/提交 + 方案管理"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from io import BytesIO

from database import get_db
from core.response import success, error
from db.schemas import (
    ManualSchemeCreate,
    ManualSchemeUpdate,
    QuickEntrySave,
    ManualPreviewBody,
    ManualCommitBody,
    ManualExportTemplateBody,
)
from services import manual_scheme_service as scheme_svc
from services import manual_flow_service as flow_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manual-flow", tags=["manual-flow"])


# ── 字段池 ──

@router.get("/field-pool")
def get_field_pool(db: Session = Depends(get_db)):
    return success(scheme_svc.list_field_pool(db))


# ── 方案 CRUD ──

@router.get("/schemes")
def list_schemes(db: Session = Depends(get_db)):
    return success(scheme_svc.list_schemes(db))


@router.post("/schemes")
def create_scheme(body: ManualSchemeCreate, db: Session = Depends(get_db)):
    try:
        result = scheme_svc.create_scheme(db, body)
        return success(result)
    except ValueError as e:
        return error(1003, str(e))


@router.put("/schemes/{scheme_id}")
def update_scheme(scheme_id: int, body: ManualSchemeUpdate, db: Session = Depends(get_db)):
    try:
        result = scheme_svc.update_scheme(db, scheme_id, body)
        if not result:
            return error(2001, "方案不存在")
        return success(result)
    except ValueError as e:
        return error(1003, str(e))


# ── Track A: 快速录入 ──

@router.post("/quick-entry/save")
def quick_entry_save(body: QuickEntrySave, db: Session = Depends(get_db)):
    try:
        rows = [r.model_dump() for r in body.rows]
        result = flow_svc.quick_entry_save(db, rows, body.scheme_code)
        return success(result)
    except Exception as e:
        logger.error("快速录入保存失败: %s", str(e), exc_info=True)
        return error(5000, "快速录入保存失败，请查看操作日志")

@router.post("/upload")
async def upload_workbook(
    file: UploadFile = File(...),
    scheme_code: str = Form("manual_multi_subject_basic"),
    db: Session = Depends(get_db),
):
    try:
        data = await file.read()
        result = flow_svc.upload_workbook(db, data, file.filename or "upload.xlsx", scheme_code)
        return success(result)
    except Exception as e:
        logger.error("Excel上传失败: %s", str(e), exc_info=True)
        return error(5000, "Excel上传失败，请查看操作日志")

@router.post("/preview")
def preview(body: ManualPreviewBody, db: Session = Depends(get_db)):
    try:
        result = flow_svc.preview_manual(db, body.batch_code, body.scheme_code)
        return success(result)
    except Exception as e:
        logger.error("手工流水预览失败: %s", str(e), exc_info=True)
        return error(5000, "手工流水预览失败，请查看操作日志")

@router.post("/commit")
def commit(body: ManualCommitBody, db: Session = Depends(get_db)):
    try:
        result = flow_svc.commit_manual(
            db,
            body.batch_code,
            body.confirm_rows,
            body.fixes,
            body.parser_artifact_id,
        )
        return success(result)
    except Exception as e:
        logger.error("手工流水提交失败: %s", str(e), exc_info=True)
        return error(5000, "手工流水提交失败，请查看操作日志")

@router.post("/export-template")
def export_template(body: ManualExportTemplateBody, db: Session = Depends(get_db)):
    try:
        xlsx_bytes = flow_svc.export_template(db, body.scheme_code, body.include_example_rows)
        buf = BytesIO(xlsx_bytes)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=manual_template.xlsx"},
        )
    except Exception as e:
        logger.error("导出模板失败: %s", str(e), exc_info=True)
        return error(5000, "导出模板失败，请查看操作日志")


# ── AI 智能解析（手工流水） ──

class ManualAIParseBody(BaseModel):
    headers: List[str]
    sample_rows: Optional[List[List[str]]] = None
    agent_id: Optional[int] = None
    scheme_code: Optional[str] = None


@router.post("/ai-parse")
def ai_parse_manual(body: ManualAIParseBody, db: Session = Depends(get_db)):
    try:
        result = flow_svc.ai_parse_headers(
            db, body.headers, body.sample_rows,
            agent_id=body.agent_id, scheme_code=body.scheme_code,
        )
        return success(result)
    except Exception as e:
        logger.error("手工流水AI解析失败: %s", str(e), exc_info=True)
        return error(5000, "AI解析失败，请查看操作日志")
