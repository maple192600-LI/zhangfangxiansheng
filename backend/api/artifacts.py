"""Generic Artifact management API.

Routes under /api/artifacts for ParserArtifact, RuleArtifact,
and TemplateInferenceJob CRUD, review, and lifecycle operations.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.response import error, success
from database import get_db
from db.schemas import (
    ArtifactReviewRequest,
    ParserArtifactDraftCreate,
    RuleArtifactDraftCreate,
)
from services import artifact_service

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


# ── ParserArtifact ──


@router.get("/parsers")
def list_parsers(
    status: Optional[str] = None,
    kind: Optional[str] = None,
    account_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    data = artifact_service.list_parser_artifacts(
        db, status=status, kind=kind, account_code=account_code
    )
    return success(data)


@router.get("/parsers/{artifact_id}")
def get_parser(artifact_id: int, db: Session = Depends(get_db)):
    result = artifact_service.get_parser_artifact(db, artifact_id)
    if result is None:
        return error(2001, "Parser artifact 不存在")
    return success(result)


@router.post("/parsers/drafts")
def create_parser_draft(body: ParserArtifactDraftCreate, db: Session = Depends(get_db)):
    result = artifact_service.create_parser_draft(db, body)
    return success(result)


@router.post("/parsers/{artifact_id}/approve")
def approve_parser(artifact_id: int, body: ArtifactReviewRequest, db: Session = Depends(get_db)):
    try:
        result = artifact_service.approve_parser_artifact(db, artifact_id, body.reviewer)
        return success(result)
    except ValueError as exc:
        return error(2001, str(exc))


@router.post("/parsers/{artifact_id}/reject")
def reject_parser(artifact_id: int, body: ArtifactReviewRequest, db: Session = Depends(get_db)):
    try:
        result = artifact_service.reject_parser_artifact(
            db, artifact_id, body.reason or "", body.reviewer
        )
        return success(result)
    except ValueError as exc:
        return error(2001, str(exc))


# ── RuleArtifact ──


@router.get("/rules")
def list_rules(
    status: Optional[str] = None,
    template_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    data = artifact_service.list_rule_artifacts(db, status=status, template_id=template_id)
    return success(data)


@router.get("/rules/{artifact_id}")
def get_rule(artifact_id: int, db: Session = Depends(get_db)):
    result = artifact_service.get_rule_artifact(db, artifact_id)
    if result is None:
        return error(2001, "Rule artifact 不存在")
    return success(result)


@router.post("/rules/drafts")
def create_rule_draft(body: RuleArtifactDraftCreate, db: Session = Depends(get_db)):
    result = artifact_service.create_rule_draft(db, body)
    return success(result)


@router.post("/rules/{artifact_id}/approve")
def approve_rule(artifact_id: int, body: ArtifactReviewRequest, db: Session = Depends(get_db)):
    try:
        result = artifact_service.approve_rule_artifact(db, artifact_id, body.reviewer)
        return success(result)
    except ValueError as exc:
        return error(2001, str(exc))


@router.post("/rules/{artifact_id}/reject")
def reject_rule(artifact_id: int, body: ArtifactReviewRequest, db: Session = Depends(get_db)):
    try:
        result = artifact_service.reject_rule_artifact(
            db, artifact_id, body.reason or "", body.reviewer
        )
        return success(result)
    except ValueError as exc:
        return error(2001, str(exc))


# ── TemplateInferenceJob ──


@router.get("/template-inference-jobs")
def list_inference_jobs(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    data = artifact_service.list_template_inference_jobs(db, status=status)
    return success(data)


@router.get("/template-inference-jobs/{job_id}")
def get_inference_job(job_id: int, db: Session = Depends(get_db)):
    result = artifact_service.get_template_inference_job(db, job_id)
    if result is None:
        return error(2001, "模板推断任务不存在")
    return success(result)
