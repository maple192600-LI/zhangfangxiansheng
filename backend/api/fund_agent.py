"""Fund Agent API: skill invocation and artifact review."""
from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from agents.fund import memory
from agents.fund.harness import ALLOWED_SKILLS, FundAgent
from config import DATA_DIR
from core.response import error, success
from database import get_db
from db.tables import ImportBatch, ParserArtifact, RuleArtifact, TemplateInferenceJob

router = APIRouter(prefix="/fund", tags=["fund-agent"])


@router.post("/agent/skills/{skill_name}/invoke")
async def invoke_skill(skill_name: str, request: Request, db: Session = Depends(get_db)):
    if skill_name not in ALLOWED_SKILLS:
        return error(3001, f"未知 Fund Agent skill: {skill_name}")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    try:
        payload = _resolve_skill_payload(skill_name, payload, db)
        draft = FundAgent(db).run_skill(skill_name, payload)
        return success(_skill_response(draft.payload))
    except ValueError as exc:
        return error(3001, str(exc))
    except Exception as exc:
        return error(3001, f"Fund Agent 执行失败: {exc}")


@router.get("/parsers")
def list_parsers(
    status: Optional[str] = None,
    kind: Optional[str] = None,
    account_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ParserArtifact)
    if status:
        q = q.filter(ParserArtifact.status == status)
    if kind:
        q = q.filter(ParserArtifact.kind == kind)
    if account_code:
        q = q.filter(ParserArtifact.account_code == account_code)
    rows = q.order_by(ParserArtifact.id.desc()).all()
    return success([_parser_to_dict(row, include_code=False) for row in rows])


@router.get("/parsers/{artifact_id}")
def get_parser(artifact_id: int, db: Session = Depends(get_db)):
    artifact = db.query(ParserArtifact).filter(ParserArtifact.id == artifact_id).first()
    if artifact is None:
        return error(2001, "Parser artifact 不存在")
    return success(_parser_to_dict(artifact, include_code=True))


@router.post("/parsers/{artifact_id}/approve")
def approve_parser(artifact_id: int, db: Session = Depends(get_db)):
    try:
        artifact = memory.approve_parser(db, artifact_id, "admin")
        return success(_parser_to_dict(artifact, include_code=True))
    except ValueError as exc:
        return error(2001, str(exc))


@router.get("/rules")
def list_rules(status: Optional[str] = None, template_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(RuleArtifact)
    if status:
        q = q.filter(RuleArtifact.status == status)
    if template_id is not None:
        q = q.filter(RuleArtifact.template_id == template_id)
    rows = q.order_by(RuleArtifact.id.desc()).all()
    return success([_rule_to_dict(row, include_bindings=False) for row in rows])


@router.get("/rules/{artifact_id}")
def get_rule(artifact_id: int, db: Session = Depends(get_db)):
    artifact = db.query(RuleArtifact).filter(RuleArtifact.id == artifact_id).first()
    if artifact is None:
        return error(2001, "Rule artifact 不存在")
    return success(_rule_to_dict(artifact, include_bindings=True))


@router.post("/rules/{artifact_id}/approve")
def approve_rule(artifact_id: int, db: Session = Depends(get_db)):
    try:
        artifact = memory.approve_rule(db, artifact_id, "admin")
        job = (
            db.query(TemplateInferenceJob)
            .filter(TemplateInferenceJob.rule_artifact_id == artifact.id)
            .order_by(TemplateInferenceJob.id.desc())
            .first()
        )
        if job is not None:
            job.status = "approved"
            job.stage_c_decision = "approved"
            job.updated_at = datetime.now()
            db.commit()
        return success(_rule_to_dict(artifact, include_bindings=True))
    except ValueError as exc:
        return error(2001, str(exc))


@router.post("/templates/upload")
async def upload_template(
    file: UploadFile = File(...),
    kind: str = Form("cash_journal"),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        return error(4001, "仅支持 Excel 模板文件")
    upload_dir = os.path.join(DATA_DIR, "template_uploads")
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    file_path = os.path.join(upload_dir, f"tpl_{uuid.uuid4().hex[:8]}_{safe_name}")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        draft = FundAgent(db).run_skill(
            "template.inference",
            {"template_file": file_path, "privacy_mode": "standard", "user_id": "admin"},
        )
        payload = draft.payload
        rule_draft = payload.get("rule_draft") or {}
        return success({
            "job_id": payload.get("job_id"),
            "detected_placeholders": payload.get("detected_placeholders") or [],
            "confidence": payload.get("confidence"),
            "rule_draft_id": rule_draft.get("artifact_id"),
            "status": "pending",
            "kind": kind,
        })
    except Exception as exc:
        return error(3001, f"模板识别失败: {exc}")


@router.get("/templates/jobs/{job_id}")
def get_template_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(TemplateInferenceJob).filter(TemplateInferenceJob.id == job_id).first()
    if job is None:
        return error(2001, "模板识别任务不存在")
    return success(_job_to_dict(job))


@router.post("/templates/jobs/{job_id}/confirm")
def confirm_template_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(TemplateInferenceJob).filter(TemplateInferenceJob.id == job_id).first()
    if job is None:
        return error(2001, "模板识别任务不存在")
    if not job.rule_artifact_id:
        return error(2004, "模板识别任务尚未生成 Rule artifact")
    approved = memory.approve_rule(db, job.rule_artifact_id, "admin")
    job.status = "approved"
    job.stage_c_decision = "approved"
    job.updated_at = datetime.now()
    db.commit()
    return success({"job": _job_to_dict(job), "rule": _rule_to_dict(approved, include_bindings=True)})


def _resolve_skill_payload(skill_name: str, payload: dict[str, Any], db: Session) -> dict[str, Any]:
    out = dict(payload or {})
    if skill_name in {"parser.bank", "parser.manual"} and not out.get("sample_file"):
        out["sample_file"] = _resolve_uploaded_file(out, db)
    if skill_name == "parser.bank" and not out.get("account_code"):
        raise ValueError("parser.bank 需要 account_code")
    if skill_name == "template.inference" and not out.get("template_file"):
        out["template_file"] = _resolve_template_file(out)
    return out


def _resolve_uploaded_file(payload: dict[str, Any], db: Session) -> str:
    candidate = payload.get("sample_file_id") or payload.get("batch_code") or payload.get("sample_file")
    if not candidate:
        raise ValueError("缺少 sample_file / sample_file_id / batch_code")
    if os.path.isfile(str(candidate)):
        return str(candidate)

    upload_dir = os.path.join(DATA_DIR, "uploads")
    if os.path.isdir(upload_dir):
        for filename in os.listdir(upload_dir):
            if str(candidate) in filename:
                path = os.path.join(upload_dir, filename)
                if os.path.isfile(path):
                    return path
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == str(candidate)).first()
    if batch and batch.source_name and os.path.isdir(upload_dir):
        for filename in os.listdir(upload_dir):
            if filename.endswith(batch.source_name):
                path = os.path.join(upload_dir, filename)
                if os.path.isfile(path):
                    return path
    raise ValueError(f"上传样本文件不存在: {candidate}")


def _resolve_template_file(payload: dict[str, Any]) -> str:
    candidate = payload.get("template_file") or payload.get("template_file_id") or payload.get("job_id")
    if not candidate:
        raise ValueError("缺少 template_file / template_file_id")
    if os.path.isfile(str(candidate)):
        return str(candidate)
    upload_dir = os.path.join(DATA_DIR, "template_uploads")
    if os.path.isdir(upload_dir):
        for filename in os.listdir(upload_dir):
            if str(candidate) in filename:
                path = os.path.join(upload_dir, filename)
                if os.path.isfile(path):
                    return path
    raise ValueError(f"模板文件不存在: {candidate}")


def _skill_response(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    if "sample_check_log" in out and hasattr(out["sample_check_log"], "model_dump"):
        out["sample_check_log"] = out["sample_check_log"].model_dump()
    if "rule_draft" in out and hasattr(out["rule_draft"], "model_dump"):
        out["rule_draft"] = out["rule_draft"].model_dump()
    if "artifact_id" in out:
        out.setdefault("status", "draft")
    return out


def _parser_to_dict(row: ParserArtifact, *, include_code: bool) -> dict[str, Any]:
    data = {
        "id": row.id,
        "artifact_id": row.id,
        "name": row.name,
        "kind": row.kind,
        "account_code": row.account_code,
        "version": row.version,
        "status": row.status,
        "primitives_imports": row.primitives_imports,
        "sample_check_log": row.sample_check_log,
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }
    if include_code:
        data["code"] = row.code
    return data


def _rule_to_dict(row: RuleArtifact, *, include_bindings: bool) -> dict[str, Any]:
    data = {
        "id": row.id,
        "artifact_id": row.id,
        "name": row.name,
        "template_id": row.template_id,
        "version": row.version,
        "status": row.status,
        "primitives_imports": row.primitives_imports,
        "sample_check_log": row.sample_check_log,
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }
    if include_bindings:
        data["placeholder_bindings"] = row.placeholder_bindings
        data["loop_config"] = row.loop_config or row.loop_spec or {}
    return data


def _job_to_dict(job: TemplateInferenceJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "job_id": job.id,
        "template_file": job.template_file,
        "original_filename": job.original_filename,
        "stage": job.stage,
        "status": job.status,
        "stage_a_output": job.stage_a_output,
        "stage_b_output": job.stage_b_output,
        "stage_c_decision": job.stage_c_decision,
        "rule_artifact_id": job.rule_artifact_id,
        "error_message": job.error_message,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
