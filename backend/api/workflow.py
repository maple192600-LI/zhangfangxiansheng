"""Workflow definition and run API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.response import error, success
from database import get_db
from db.schemas import (
    WorkflowCreate,
    WorkflowMetadataUpdate,
    WorkflowPatchRequest,
    WorkflowRunCreate,
    WorkflowValidateRequest,
)
from services import workflow_service
from services.workflow_nodes import node_registry

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.get("/workflows")
def list_workflows(status: Optional[str] = None, db: Session = Depends(get_db)):
    return success(workflow_service.list_workflow_definitions(db, status=status))


@router.post("/workflows")
def create_workflow(body: WorkflowCreate, db: Session = Depends(get_db)):
    try:
        return success(workflow_service.create_workflow_definition(db, body))
    except ValueError as exc:
        return error(1002, str(exc))


@router.get("/nodes")
def list_workflow_nodes():
    return success({"items": node_registry.list_types()})


@router.get("/runs")
def list_workflow_runs(
    workflow_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return success(
        workflow_service.list_workflow_runs(
            db,
            workflow_id=workflow_id,
            status=status,
        )
    )


@router.get("/runs/{run_id}")
def get_workflow_run(run_id: int, db: Session = Depends(get_db)):
    result = workflow_service.get_workflow_run(db, run_id)
    if result is None:
        return error(2001, "工作流运行记录不存在")
    return success(result)


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    result = workflow_service.get_workflow_definition(db, workflow_id)
    if result is None:
        return error(2001, "工作流不存在")
    return success(result)


@router.put("/workflows/{workflow_id}")
def update_workflow(
    workflow_id: int,
    body: WorkflowMetadataUpdate,
    db: Session = Depends(get_db),
):
    try:
        return success(workflow_service.update_workflow_definition(db, workflow_id, body))
    except ValueError as exc:
        return error(1002, str(exc))


@router.patch("/workflows/{workflow_id}/graph")
def patch_workflow_graph(
    workflow_id: int,
    body: WorkflowPatchRequest,
    db: Session = Depends(get_db),
):
    try:
        return success(workflow_service.apply_workflow_patch(db, workflow_id, body))
    except ValueError as exc:
        return error(1002, str(exc))


@router.post("/workflows/{workflow_id}/validate")
def validate_workflow(
    workflow_id: int,
    body: Optional[WorkflowValidateRequest] = None,
    db: Session = Depends(get_db),
):
    graph_json = body.graph_json if body else None
    result = workflow_service.validate_workflow_graph(db, workflow_id, graph_json)
    if result is None:
        return error(2001, "工作流不存在")
    return success(result)


@router.post("/workflows/{workflow_id}/activate")
def activate_workflow(workflow_id: int, db: Session = Depends(get_db)):
    try:
        return success(workflow_service.activate_workflow_definition(db, workflow_id))
    except ValueError as exc:
        return error(2001, str(exc))


@router.post("/workflows/{workflow_id}/archive")
def retire_workflow(workflow_id: int, db: Session = Depends(get_db)):
    try:
        return success(workflow_service.retire_workflow_definition(db, workflow_id))
    except ValueError as exc:
        return error(2001, str(exc))


@router.post("/workflows/{workflow_id}/runs")
def start_workflow_run(
    workflow_id: int,
    body: WorkflowRunCreate,
    db: Session = Depends(get_db),
):
    try:
        return success(workflow_service.start_workflow_run(db, workflow_id, body))
    except ValueError as exc:
        return error(2001, str(exc))


@router.get("/workflows/{workflow_id}/versions")
def list_workflow_versions(workflow_id: int, db: Session = Depends(get_db)):
    result = workflow_service.list_workflow_versions(db, workflow_id)
    if result is None:
        return error(2001, "工作流不存在")
    return success(result)


@router.post("/runs/{run_id}/resume")
def resume_workflow_run(run_id: int, db: Session = Depends(get_db)):
    try:
        return success(workflow_service.resume_workflow_run(db, run_id))
    except ValueError as exc:
        return error(2001, str(exc))
