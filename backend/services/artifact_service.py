"""Artifact Service — CRUD and lifecycle management for Parser/Rule artifacts.

Independent of legacy agent system. Operates on existing ORM models:
  ParserArtifact, RuleArtifact, TemplateInferenceJob.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from db.tables import ParserArtifact, RuleArtifact, TemplateInferenceJob


# ── ParserArtifact ──

def list_parser_artifacts(
    db: Session,
    *,
    status: Optional[str] = None,
    kind: Optional[str] = None,
    account_code: Optional[str] = None,
) -> list[dict[str, Any]]:
    q = db.query(ParserArtifact)
    if status:
        q = q.filter(ParserArtifact.status == status)
    if kind:
        q = q.filter(ParserArtifact.kind == kind)
    if account_code:
        q = q.filter(ParserArtifact.account_code == account_code)
    return [parser_to_dict(r, include_code=False) for r in q.order_by(ParserArtifact.id.desc()).all()]


def get_parser_artifact(db: Session, artifact_id: int) -> Optional[dict[str, Any]]:
    row = db.query(ParserArtifact).filter(ParserArtifact.id == artifact_id).first()
    if row is None:
        return None
    return parser_to_dict(row, include_code=True)


def create_parser_draft(db: Session, data: Any) -> dict[str, Any]:
    version = _next_parser_version(db, data.name)
    row = ParserArtifact(
        name=data.name,
        kind=data.kind.value if hasattr(data.kind, "value") else data.kind,
        account_code=data.account_code,
        version=version,
        status="draft",
        code=data.code,
        primitives_imports=data.primitives_imports,
        sample_check_log=data.sample_check_log or {},
        confidence=data.confidence,
        created_by=data.created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return parser_to_dict(row, include_code=True)


def approve_parser_artifact(db: Session, artifact_id: int, approver: str) -> dict[str, Any]:
    row = db.query(ParserArtifact).filter(ParserArtifact.id == artifact_id).first()
    if row is None:
        raise ValueError(f"Parser artifact {artifact_id} 不存在")
    if row.status != "draft":
        raise ValueError(f"Parser artifact {artifact_id} 状态为 {row.status}，只有 draft 可审批")
    # retire current active of same account+kind
    db.query(ParserArtifact).filter(
        ParserArtifact.account_code == row.account_code,
        ParserArtifact.kind == row.kind,
        ParserArtifact.status == "active",
    ).update({"status": "retired"})
    row.status = "active"
    row.approved_by = approver
    row.approved_at = datetime.now()
    db.commit()
    db.refresh(row)
    return parser_to_dict(row, include_code=True)


def reject_parser_artifact(db: Session, artifact_id: int, reason: str, rejected_by: str) -> dict[str, Any]:
    row = db.query(ParserArtifact).filter(ParserArtifact.id == artifact_id).first()
    if row is None:
        raise ValueError(f"Parser artifact {artifact_id} 不存在")
    if row.status not in ("draft", "pending_review"):
        raise ValueError(f"Parser artifact {artifact_id} 状态为 {row.status}，只有 draft 可拒绝")
    row.status = "retired"
    meta = dict(row.sample_check_log or {})
    meta["__rejection"] = {
        "reason": reason,
        "rejected_by": rejected_by,
        "rejected_at": datetime.now().isoformat(),
    }
    row.sample_check_log = meta
    db.commit()
    db.refresh(row)
    return parser_to_dict(row, include_code=True)


# ── RuleArtifact ──

def list_rule_artifacts(
    db: Session,
    *,
    status: Optional[str] = None,
    template_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    q = db.query(RuleArtifact)
    if status:
        q = q.filter(RuleArtifact.status == status)
    if template_id is not None:
        q = q.filter(RuleArtifact.template_id == template_id)
    return [rule_to_dict(r, include_bindings=False) for r in q.order_by(RuleArtifact.id.desc()).all()]


def get_rule_artifact(db: Session, artifact_id: int) -> Optional[dict[str, Any]]:
    row = db.query(RuleArtifact).filter(RuleArtifact.id == artifact_id).first()
    if row is None:
        return None
    return rule_to_dict(row, include_bindings=True)


def create_rule_draft(db: Session, data: Any) -> dict[str, Any]:
    version = _next_rule_version(db, data.name)
    row = RuleArtifact(
        name=data.name,
        template_id=data.template_id,
        version=version,
        status="draft",
        placeholder_bindings=data.placeholder_bindings,
        loop_config=data.loop_config,
        primitives_imports=data.primitives_imports,
        sample_check_log=data.sample_check_log or {},
        confidence=data.confidence,
        created_by=data.created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return rule_to_dict(row, include_bindings=True)


def approve_rule_artifact(db: Session, artifact_id: int, approver: str) -> dict[str, Any]:
    row = db.query(RuleArtifact).filter(RuleArtifact.id == artifact_id).first()
    if row is None:
        raise ValueError(f"Rule artifact {artifact_id} 不存在")
    if row.status != "draft":
        raise ValueError(f"Rule artifact {artifact_id} 状态为 {row.status}，只有 draft 可审批")
    row.status = "active"
    row.approved_by = approver
    row.approved_at = datetime.now()
    db.commit()
    db.refresh(row)
    return rule_to_dict(row, include_bindings=True)


def reject_rule_artifact(db: Session, artifact_id: int, reason: str, rejected_by: str) -> dict[str, Any]:
    row = db.query(RuleArtifact).filter(RuleArtifact.id == artifact_id).first()
    if row is None:
        raise ValueError(f"Rule artifact {artifact_id} 不存在")
    if row.status not in ("draft", "pending_review"):
        raise ValueError(f"Rule artifact {artifact_id} 状态为 {row.status}，只有 draft 可拒绝")
    row.status = "retired"
    meta = dict(row.sample_check_log or {})
    meta["__rejection"] = {
        "reason": reason,
        "rejected_by": rejected_by,
        "rejected_at": datetime.now().isoformat(),
    }
    row.sample_check_log = meta
    db.commit()
    db.refresh(row)
    return rule_to_dict(row, include_bindings=True)


# ── TemplateInferenceJob ──

def list_template_inference_jobs(
    db: Session,
    *,
    status: Optional[str] = None,
) -> list[dict[str, Any]]:
    q = db.query(TemplateInferenceJob)
    if status:
        q = q.filter(TemplateInferenceJob.status == status)
    return [job_to_dict(j) for j in q.order_by(TemplateInferenceJob.id.desc()).all()]


def get_template_inference_job(db: Session, job_id: int) -> Optional[dict[str, Any]]:
    job = db.query(TemplateInferenceJob).filter(TemplateInferenceJob.id == job_id).first()
    if job is None:
        return None
    return job_to_dict(job)


# ── Serialization helpers ──

def parser_to_dict(row: ParserArtifact, *, include_code: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": row.id,
        "name": row.name,
        "kind": row.kind,
        "account_code": row.account_code,
        "version": row.version,
        "status": row.status,
        "primitives_imports": row.primitives_imports,
        "sample_check_log": row.sample_check_log,
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "created_by": row.created_by,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }
    if include_code:
        data["code"] = row.code
    return data


def rule_to_dict(row: RuleArtifact, *, include_bindings: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": row.id,
        "name": row.name,
        "template_id": row.template_id,
        "version": row.version,
        "status": row.status,
        "primitives_imports": row.primitives_imports,
        "sample_check_log": row.sample_check_log,
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "created_by": row.created_by,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }
    if include_bindings:
        data["placeholder_bindings"] = row.placeholder_bindings
        data["loop_config"] = row.loop_config or row.loop_spec or {}
    return data


def job_to_dict(job: TemplateInferenceJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "template_file": job.template_file,
        "original_filename": job.original_filename,
        "stage": job.stage,
        "status": job.status,
        "stage_a_output": job.stage_a_output,
        "stage_b_output": job.stage_b_output,
        "stage_c_decision": job.stage_c_decision,
        "rule_artifact_id": job.rule_artifact_id,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


# ── Private helpers ──

def _next_parser_version(db: Session, name: str) -> int:
    latest = (
        db.query(ParserArtifact)
        .filter(ParserArtifact.name == name)
        .order_by(ParserArtifact.version.desc())
        .first()
    )
    return (latest.version + 1) if latest else 1


def _next_rule_version(db: Session, name: str) -> int:
    latest = (
        db.query(RuleArtifact)
        .filter(RuleArtifact.name == name)
        .order_by(RuleArtifact.version.desc())
        .first()
    )
    return (latest.version + 1) if latest else 1
