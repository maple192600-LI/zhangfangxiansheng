"""Workflow definition, version, patch, and run service."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from db.tables import Workflow, WorkflowRun, WorkflowRunStep, WorkflowVersion
from services import workflow_executor
from services.workflow_nodes import node_registry


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


def list_workflow_versions(db: Session, workflow_id: int) -> Optional[list[dict[str, Any]]]:
    row = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if row is None:
        return None
    versions = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version.desc())
        .all()
    )
    return [workflow_version_to_dict(v) for v in versions]


def resume_workflow_run(db: Session, run_id: int) -> dict[str, Any]:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise ValueError("工作流运行记录不存在")
    if run.status != "paused":
        raise ValueError("只有暂停的运行可以恢复")
    version = db.query(WorkflowVersion).filter(WorkflowVersion.id == run.workflow_version_id).first()
    if version is None:
        raise ValueError("工作流版本不存在")
    executed = workflow_executor.resume_workflow(db, run, version)
    return workflow_run_to_dict(executed, include_steps=True)


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


def validate_workflow_graph(
    db: Session,
    workflow_id: int,
    graph_json: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Validate a workflow graph without saving or creating any records."""
    row = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if row is None:
        return None

    graph = graph_json
    if graph is None:
        version = _get_current_version(row)
        if version is None:
            return None
        graph = _load_json(version.graph_json)

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    _run_graph_validation(graph, errors, warnings)
    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _run_graph_validation(
    graph: Any,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    if not isinstance(graph, dict):
        errors.append({"code": "INVALID_STRUCTURE", "message": "工作流图必须是对象"})
        return

    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append({"code": "EMPTY_NODES", "message": "工作流图必须包含 nodes"})
        return

    seen_ids: set[str] = set()
    valid_nodes: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            errors.append({"code": "INVALID_NODE", "message": "工作流节点必须是对象"})
            continue
        nid, ntype = node.get("id"), node.get("type")
        if not nid or not ntype:
            errors.append({"code": "MISSING_NODE_FIELD", "message": "工作流节点必须包含 id 和 type"})
            continue
        if nid in seen_ids:
            errors.append({"code": "DUPLICATE_NODE_ID", "message": f"工作流节点重复: {nid}", "node_ids": [nid]})
        else:
            seen_ids.add(nid)
            valid_nodes.append(node)

    if not seen_ids:
        return

    raw_edges = graph.get("edges")
    if raw_edges is not None and not isinstance(raw_edges, list):
        errors.append({"code": "INVALID_EDGES", "message": "工作流 edges 必须是数组"})
        return

    edges = raw_edges or []
    for edge in edges:
        if not isinstance(edge, dict):
            errors.append({"code": "INVALID_EDGE", "message": "工作流 edge 必须是对象"})
            continue
        src, tgt = edge.get("from"), edge.get("to")
        if src not in seen_ids or tgt not in seen_ids:
            errors.append({"code": "INVALID_EDGE_REF", "message": "工作流 edge 引用了不存在的节点"})

    for node in valid_nodes:
        if not node_registry.has(node["type"]):
            errors.append({
                "code": "UNKNOWN_NODE_TYPE",
                "message": f"未知工作流节点类型: {node['type']}",
                "node_ids": [node["id"]],
            })

    if not any(e["code"] == "INVALID_EDGE_REF" for e in errors):
        _check_cycle(seen_ids, edges, errors)

    _check_orphan_nodes(valid_nodes, edges, errors)

    _check_warnings(valid_nodes, edges, warnings)


def _check_orphan_nodes(
    valid_nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> None:
    if len(valid_nodes) <= 1:
        return
    connected: set[str] = set()
    for edge in edges:
        if isinstance(edge, dict):
            connected.add(edge.get("from", ""))
            connected.add(edge.get("to", ""))
    for node in valid_nodes:
        if node["id"] not in connected:
            errors.append({
                "code": "ORPHAN_NODE",
                "message": f"节点 {node['id']} 未被任何边连接",
                "node_ids": [node["id"]],
            })


def _check_cycle(
    node_ids: set[str],
    edges: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> None:
    incoming: dict[str, set[str]] = {nid: set() for nid in node_ids}
    outgoing: dict[str, set[str]] = {nid: set() for nid in node_ids}
    for edge in edges:
        if isinstance(edge, dict):
            src, tgt = edge.get("from"), edge.get("to")
            if src in node_ids and tgt in node_ids:
                outgoing[src].add(tgt)
                incoming[tgt].add(src)

    ready = [nid for nid in node_ids if not incoming[nid]]
    ordered: list[str] = []
    while ready:
        nid = ready.pop(0)
        ordered.append(nid)
        for tgt in sorted(outgoing[nid]):
            incoming[tgt].discard(nid)
            if not incoming[tgt] and tgt not in ordered and tgt not in ready:
                ready.append(tgt)

    if len(ordered) != len(node_ids):
        cycle_nodes = sorted(nid for nid in node_ids if nid not in set(ordered))
        errors.append({
            "code": "CYCLE_DETECTED",
            "message": "工作流图不能包含循环",
            "node_ids": cycle_nodes,
        })


def _check_warnings(
    valid_nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    node_types = {n["type"] for n in valid_nodes}

    if "control.start" not in node_types:
        warnings.append({"code": "MISSING_START", "message": "工作流缺少 control.start 节点"})
    if "control.end" not in node_types:
        warnings.append({"code": "MISSING_END", "message": "工作流缺少 control.end 节点"})

    out_map: dict[str, list[str]] = {n["id"]: [] for n in valid_nodes}
    for edge in edges:
        if isinstance(edge, dict):
            src = edge.get("from")
            if src in out_map:
                out_map[src].append(edge.get("to"))
    for node in valid_nodes:
        if node["type"] == "control.pause" and not out_map.get(node["id"]):
            warnings.append({
                "code": "PAUSE_NO_SUCCESSOR",
                "message": f"暂停节点 {node['id']} 后无后续节点",
                "node_ids": [node["id"]],
            })


def _dump_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_json(value: Optional[str]) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(value)
