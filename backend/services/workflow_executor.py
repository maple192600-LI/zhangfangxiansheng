"""Synchronous deterministic workflow executor."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from db.tables import WorkflowRun, WorkflowRunStep, WorkflowVersion
from services.workflow_nodes import WorkflowNodeContext, node_registry


def execute_workflow(
    db: Session,
    run: WorkflowRun,
    version: WorkflowVersion,
) -> WorkflowRun:
    """Execute a workflow version and persist run/step state."""
    run.status = "running"
    run.started_at = datetime.now()
    db.commit()
    db.refresh(run)

    graph = _load_json(version.graph_json)
    outputs: dict[str, Any] = {}
    workflow_input = _load_json(run.input_json)
    try:
        for node in _ordered_nodes(graph):
            step = _create_running_step(db, run.id, node, workflow_input, outputs)
            try:
                if node["type"] == "control.pause":
                    step.status = "paused"
                    step.output_json = _dump_json({"paused": True})
                    step.finished_at = datetime.now()
                    run.status = "paused"
                    run.output_json = _dump_json(outputs)
                    run.finished_at = datetime.now()
                    db.commit()
                    db.refresh(run)
                    return run

                handler = node_registry.get(node["type"])
                ctx = WorkflowNodeContext(
                    db=db,
                    run_id=run.id,
                    workflow_input=workflow_input,
                    previous_outputs=dict(outputs),
                )
                node_output = handler(node.get("params") or {}, ctx)
                outputs[node["id"]] = node_output
                step.status = "completed"
                step.output_json = _dump_json(node_output)
            except Exception as exc:
                step.status = "failed"
                step.error_message = str(exc)
                step.finished_at = datetime.now()
                run.status = "failed"
                run.error_message = str(exc)
                run.output_json = _dump_json(outputs)
                run.finished_at = datetime.now()
                db.commit()
                db.refresh(run)
                return run

            step.finished_at = datetime.now()
            db.commit()

        run.status = "completed"
        run.output_json = _dump_json(outputs)
        run.finished_at = datetime.now()
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.output_json = _dump_json(outputs)
        run.finished_at = datetime.now()
        db.commit()
        db.refresh(run)
        return run


def _ordered_nodes(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("工作流图必须包含 nodes")

    node_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("工作流节点必须是对象")
        node_id = node.get("id")
        node_type = node.get("type")
        if not node_id or not node_type:
            raise ValueError("工作流节点必须包含 id 和 type")
        if node_id in node_by_id:
            raise ValueError(f"工作流节点重复: {node_id}")
        node_by_id[node_id] = node

    edges = graph.get("edges") or []
    incoming: dict[str, set[str]] = {node_id: set() for node_id in node_by_id}
    outgoing: dict[str, set[str]] = {node_id: set() for node_id in node_by_id}
    for edge in edges:
        source = edge.get("from")
        target = edge.get("to")
        if source not in node_by_id or target not in node_by_id:
            raise ValueError("工作流 edge 引用了不存在的节点")
        outgoing[source].add(target)
        incoming[target].add(source)

    ready = [node_id for node_id in node_by_id if not incoming[node_id]]
    ordered: list[dict[str, Any]] = []
    while ready:
        node_id = ready.pop(0)
        ordered.append(node_by_id[node_id])
        for target in sorted(outgoing[node_id]):
            incoming[target].discard(node_id)
            if not incoming[target] and target not in [n["id"] for n in ordered] and target not in ready:
                ready.append(target)

    if len(ordered) != len(node_by_id):
        raise ValueError("工作流图不能包含循环")
    return ordered


def _create_running_step(
    db: Session,
    run_id: int,
    node: dict[str, Any],
    workflow_input: dict[str, Any],
    outputs: dict[str, Any],
) -> WorkflowRunStep:
    step = WorkflowRunStep(
        run_id=run_id,
        node_id=node["id"],
        node_type=node["type"],
        status="running",
        input_json=_dump_json(
            {
                "params": node.get("params") or {},
                "workflow_input": workflow_input,
                "previous_outputs": outputs,
            }
        ),
        started_at=datetime.now(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def _dump_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(value)
