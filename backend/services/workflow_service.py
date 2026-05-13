"""Workflow definition, version, patch, and run service."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from db.tables import Workflow, WorkflowRun, WorkflowRunStep, WorkflowVersion
from services import workflow_executor


def list_workflow_definitions(
    db: Session,
    *,
    status: Optional[str] = None,
) -> list[dict[str, Any]]:
    query = db.query(Workflow)
    if status:
        query = query.filter(Workflow.status == status)
    rows = query.order_by(Workflow.id.desc()).all()
    return [workflow_to_dict(row) for row in rows]


def get_workflow_definition(db: Session, workflow_id: int) -> Optional[dict[str, Any]]:
    row = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if row is None:
        return None
    return workflow_to_dict(row)


def create_workflow_definition(db: Session, data: Any) -> dict[str, Any]:
    _validate_graph(data.graph)
    row = Workflow(
        workflow_code=data.workflow_code,
        name=data.name,
        description=data.description,
        status="draft",
        current_version=1,
        created_by=data.created_by,
    )
    db.add(row)
    db.flush()

    version = WorkflowVersion(
        workflow_id=row.id,
        version=1,
        graph_json=_dump_json(data.graph),
        change_summary="initial version",
        created_by=data.created_by,
    )
    db.add(version)
    db.commit()
    db.refresh(row)
    return workflow_to_dict(row)


def update_workflow_definition(db: Session, workflow_id: int, data: Any) -> dict[str, Any]:
    row = _get_workflow_or_raise(db, workflow_id)
    if data.name is not None:
        row.name = data.name
    if data.description is not None:
        row.description = data.description
    if data.status is not None:
        row.status = data.status.value if hasattr(data.status, "value") else data.status
    row.updated_at = datetime.now()
    db.commit()
    db.refresh(row)
    return workflow_to_dict(row)


def apply_workflow_patch(db: Session, workflow_id: int, data: Any) -> dict[str, Any]:
    row = _get_workflow_or_raise(db, workflow_id)
    current = _get_current_version_or_raise(db, row)
    graph = _load_json(current.graph_json)

    for patch in data.patches:
        op = patch.get("op")
        if op == "replace_graph":
            graph = patch.get("graph")
            _validate_graph(graph)
        elif op == "set_metadata":
            if "name" in patch:
                row.name = patch["name"]
            if "description" in patch:
                row.description = patch["description"]
        else:
            raise ValueError(f"不支持的工作流 patch 操作: {op}")

    next_version = row.current_version + 1
    version = WorkflowVersion(
        workflow_id=row.id,
        version=next_version,
        graph_json=_dump_json(graph),
        change_summary=data.change_summary,
        created_by=data.created_by,
    )
    row.current_version = next_version
    row.updated_at = datetime.now()
    db.add(version)
    db.commit()
    db.refresh(row)
    return workflow_to_dict(row)


def activate_workflow_definition(db: Session, workflow_id: int) -> dict[str, Any]:
    row = _get_workflow_or_raise(db, workflow_id)
    _get_current_version_or_raise(db, row)
    row.status = "active"
    row.updated_at = datetime.now()
    db.commit()
    db.refresh(row)
    return workflow_to_dict(row)


def retire_workflow_definition(db: Session, workflow_id: int) -> dict[str, Any]:
    row = _get_workflow_or_raise(db, workflow_id)
    row.status = "archived"
    row.updated_at = datetime.now()
    db.commit()
    db.refresh(row)
    return workflow_to_dict(row)


def start_workflow_run(db: Session, workflow_id: int, data: Any) -> dict[str, Any]:
    workflow = _get_workflow_or_raise(db, workflow_id)
    if workflow.status != "active":
        raise ValueError("只有 active 工作流可以执行")
    version = _get_current_version_or_raise(db, workflow)

    run = WorkflowRun(
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        workflow_code=workflow.workflow_code,
        workflow_version=version.version,
        status="pending",
        input_json=_dump_json(data.input or {}),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    executed = workflow_executor.execute_workflow(db, run, version)
    return workflow_run_to_dict(executed, include_steps=True)


def list_workflow_runs(
    db: Session,
    *,
    workflow_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[dict[str, Any]]:
    query = db.query(WorkflowRun)
    if workflow_id is not None:
        query = query.filter(WorkflowRun.workflow_id == workflow_id)
    if status:
        query = query.filter(WorkflowRun.status == status)
    rows = query.order_by(WorkflowRun.id.desc()).all()
    return [workflow_run_to_dict(row, include_steps=False) for row in rows]


def get_workflow_run(db: Session, run_id: int) -> Optional[dict[str, Any]]:
    row = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if row is None:
        return None
    return workflow_run_to_dict(row, include_steps=True)


def workflow_to_dict(row: Workflow) -> dict[str, Any]:
    current = _get_current_version(row)
    return {
        "id": row.id,
        "workflow_code": row.workflow_code,
        "name": row.name,
        "description": row.description,
        "status": row.status,
        "current_version": workflow_version_to_dict(current) if current else None,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def workflow_version_to_dict(row: WorkflowVersion) -> dict[str, Any]:
    return {
        "id": row.id,
        "workflow_id": row.workflow_id,
        "version": row.version,
        "graph": _load_json(row.graph_json),
        "change_summary": row.change_summary,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def workflow_run_to_dict(row: WorkflowRun, *, include_steps: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": row.id,
        "workflow_id": row.workflow_id,
        "workflow_version_id": row.workflow_version_id,
        "workflow_code": row.workflow_code,
        "workflow_version": row.workflow_version,
        "status": row.status,
        "input": _load_json(row.input_json),
        "output": _load_json(row.output_json) if row.output_json else None,
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }
    if include_steps:
        data["steps"] = [workflow_run_step_to_dict(step) for step in row.steps]
    return data


def workflow_run_step_to_dict(row: WorkflowRunStep) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "node_id": row.node_id,
        "node_type": row.node_type,
        "status": row.status,
        "input": _load_json(row.input_json),
        "output": _load_json(row.output_json) if row.output_json else None,
        "error_message": row.error_message,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }


def _get_workflow_or_raise(db: Session, workflow_id: int) -> Workflow:
    row = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if row is None:
        raise ValueError("工作流不存在")
    return row


def _get_current_version_or_raise(db: Session, workflow: Workflow) -> WorkflowVersion:
    row = (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_id == workflow.id,
            WorkflowVersion.version == workflow.current_version,
        )
        .first()
    )
    if row is None:
        raise ValueError("工作流当前版本不存在")
    return row


def _get_current_version(workflow: Workflow) -> Optional[WorkflowVersion]:
    for version in workflow.versions:
        if version.version == workflow.current_version:
            return version
    return None


def _validate_graph(graph: Any) -> None:
    if not isinstance(graph, dict):
        raise ValueError("工作流图必须是对象")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("工作流图必须包含 nodes")

    seen: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("工作流节点必须是对象")
        node_id = node.get("id")
        node_type = node.get("type")
        if not node_id or not node_type:
            raise ValueError("工作流节点必须包含 id 和 type")
        if node_id in seen:
            raise ValueError(f"工作流节点重复: {node_id}")
        seen.add(node_id)

    edges = graph.get("edges") or []
    if not isinstance(edges, list):
        raise ValueError("工作流 edges 必须是数组")
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("工作流 edge 必须是对象")
        source = edge.get("from")
        target = edge.get("to")
        if source not in seen or target not in seen:
            raise ValueError("工作流 edge 引用了不存在的节点")


def _dump_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_json(value: Optional[str]) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(value)
