"""手工流水 API — 快速录入 + Excel上传/预览/提交 + 方案管理"""
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
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
        return error(5000, str(e))


# ── Track B: Excel 上传 ──

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
        return error(5000, str(e))


# ── 预览 ──

@router.post("/preview")
def preview(body: ManualPreviewBody, db: Session = Depends(get_db)):
    try:
        result = flow_svc.preview_manual(db, body.batch_code, body.scheme_code)
        return success(result)
    except Exception as e:
        return error(5000, str(e))


# ── 提交 ──

@router.post("/commit")
def commit(body: ManualCommitBody, db: Session = Depends(get_db)):
    try:
        result = flow_svc.commit_manual(db, body.batch_code, body.confirm_rows, body.fixes)
        return success(result)
    except Exception as e:
        return error(5000, str(e))


# ── 导出模板 ──

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
        return error(5000, str(e))
