"""Workflow service unit tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from database import Base
from db.schemas import WorkflowCreate, WorkflowMetadataUpdate, WorkflowPatchRequest, WorkflowRunCreate
from services import workflow_service


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _graph(nodes=None, edges=None):
    return {
        "nodes": nodes or [{"id": "n1", "type": "noop", "params": {}}],
        "edges": edges or [],
    }


def _create(db, code="wf_test", name="Test WF"):
    return workflow_service.create_workflow_definition(
        db,
        WorkflowCreate(workflow_code=code, name=name, graph=_graph()),
    )


# ── get_workflow_definition ───────────────────


def test_get_workflow_definition_returns_created(db):
    created = _create(db, code="wf_get")
    result = workflow_service.get_workflow_definition(db, created["id"])
    assert result is not None
    assert result["id"] == created["id"]
    assert result["workflow_code"] == "wf_get"


def test_get_workflow_definition_returns_none_for_missing(db):
    result = workflow_service.get_workflow_definition(db, 99999)
    assert result is None


# ── update_workflow_definition ─────────────────


def test_update_workflow_name_and_description(db):
    created = _create(db, code="wf_upd")
    updated = workflow_service.update_workflow_definition(
        db,
        created["id"],
        WorkflowMetadataUpdate(name="New Name", description="New Desc"),
    )
    assert updated["name"] == "New Name"
    assert updated["description"] == "New Desc"


def test_update_does_not_change_version(db):
    created = _create(db, code="wf_ver")
    updated = workflow_service.update_workflow_definition(
        db,
        created["id"],
        WorkflowMetadataUpdate(name="Renamed"),
    )
    assert updated["current_version"]["version"] == 1


def test_update_nonexistent_raises(db):
    with pytest.raises(ValueError, match="工作流不存在"):
        workflow_service.update_workflow_definition(
            db, 99999, WorkflowMetadataUpdate(name="X"),
        )


# ── list_workflow_definitions ──────────────────


def test_list_workflows_with_status_filter(db):
    _create(db, code="wf_list_d1")
    created2 = _create(db, code="wf_list_d2")
    workflow_service.activate_workflow_definition(db, created2["id"])
    active = workflow_service.list_workflow_definitions(db, status="active")
    assert len(active) == 1
    assert active[0]["workflow_code"] == "wf_list_d2"


# ── retire_workflow_definition ─────────────────


def test_retire_sets_archived(db):
    created = _create(db, code="wf_retire")
    retired = workflow_service.retire_workflow_definition(db, created["id"])
    assert retired["status"] == "archived"


def test_retire_active_workflow(db):
    created = _create(db, code="wf_retire_active")
    workflow_service.activate_workflow_definition(db, created["id"])
    retired = workflow_service.retire_workflow_definition(db, created["id"])
    assert retired["status"] == "archived"


# ── apply_workflow_patch — set_metadata ────────


def test_patch_set_metadata(db):
    created = _create(db, code="wf_meta")
    patched = workflow_service.apply_workflow_patch(
        db,
        created["id"],
        WorkflowPatchRequest(
            patches=[{"op": "set_metadata", "name": "Meta Name", "description": "Meta Desc"}],
            created_by="tester",
            change_summary="metadata update",
        ),
    )
    assert patched["name"] == "Meta Name"
    assert patched["description"] == "Meta Desc"


def test_patch_unsupported_op_raises(db):
    created = _create(db, code="wf_badop")
    with pytest.raises(ValueError, match="不支持的工作流 patch 操作"):
        workflow_service.apply_workflow_patch(
            db,
            created["id"],
            WorkflowPatchRequest(
                patches=[{"op": "delete_everything"}],
                created_by="tester",
            ),
        )


# ── start_workflow_run — draft blocked ────────


def test_start_run_on_draft_raises(db):
    created = _create(db, code="wf_draft_run")
    with pytest.raises(ValueError, match="只有 active 工作流可以执行"):
        workflow_service.start_workflow_run(db, created["id"], WorkflowRunCreate(input={}))


# ── list / get workflow runs ──────────────────


def test_list_and_get_workflow_runs(db):
    created = _create(db, code="wf_runs")
    workflow_service.activate_workflow_definition(db, created["id"])
    workflow_service.start_workflow_run(db, created["id"], WorkflowRunCreate(input={"x": 1}))
    workflow_service.start_workflow_run(db, created["id"], WorkflowRunCreate(input={"y": 2}))

    runs = workflow_service.list_workflow_runs(db, workflow_id=created["id"])
    assert len(runs) == 2

    detail = workflow_service.get_workflow_run(db, runs[0]["id"])
    assert detail is not None
    assert "steps" in detail
    assert detail["status"] == "completed"


def test_list_runs_with_status_filter(db):
    created = _create(db, code="wf_filter")
    workflow_service.activate_workflow_definition(db, created["id"])
    workflow_service.start_workflow_run(db, created["id"], WorkflowRunCreate(input={}))

    completed = workflow_service.list_workflow_runs(db, status="completed")
    assert len(completed) >= 1

    pending = workflow_service.list_workflow_runs(db, status="pending")
    assert len(pending) == 0


def test_get_run_nonexistent_returns_none(db):
    result = workflow_service.get_workflow_run(db, 99999)
    assert result is None


# ── list_workflow_versions ─────────────────────


def test_list_versions_returns_v1_after_create(db):
    created = _create(db, code="wf_ver_list")
    versions = workflow_service.list_workflow_versions(db, created["id"])
    assert versions is not None
    assert len(versions) == 1
    assert versions[0]["version"] == 1


def test_list_versions_returns_v1_v2_after_patch(db):
    created = _create(db, code="wf_ver_patch")
    workflow_service.apply_workflow_patch(
        db,
        created["id"],
        WorkflowPatchRequest(
            patches=[{"op": "replace_graph", "graph": _graph()}],
            created_by="tester",
            change_summary="v2",
        ),
    )
    versions = workflow_service.list_workflow_versions(db, created["id"])
    assert versions is not None
    assert len(versions) == 2
    assert versions[0]["version"] == 2  # newest first
    assert versions[1]["version"] == 1


def test_list_versions_returns_none_for_missing(db):
    result = workflow_service.list_workflow_versions(db, 99999)
    assert result is None


# ── resume_workflow_run ────────────────────────


def test_resume_paused_run_succeeds(db):
    graph = {
        "nodes": [
            {"id": "s", "type": "control.start", "params": {}},
            {"id": "p", "type": "control.pause", "params": {}},
            {"id": "e", "type": "control.end", "params": {}},
        ],
        "edges": [
            {"from": "s", "to": "p"},
            {"from": "p", "to": "e"},
        ],
    }
    created = workflow_service.create_workflow_definition(
        db, WorkflowCreate(workflow_code="wf_resume", name="Resume Test", graph=graph),
    )
    workflow_service.activate_workflow_definition(db, created["id"])
    run = workflow_service.start_workflow_run(db, created["id"], WorkflowRunCreate(input={}))
    assert run["status"] == "paused"

    resumed = workflow_service.resume_workflow_run(db, run["id"])
    assert resumed["status"] == "completed"
    steps = resumed["steps"]
    assert len(steps) == 3
    assert steps[2]["node_id"] == "e"
    assert steps[2]["status"] == "completed"


def test_resume_completed_run_raises(db):
    created = _create(db, code="wf_res_done")
    workflow_service.activate_workflow_definition(db, created["id"])
    run = workflow_service.start_workflow_run(db, created["id"], WorkflowRunCreate(input={}))
    assert run["status"] == "completed"
    with pytest.raises(ValueError, match="只有暂停的运行可以恢复"):
        workflow_service.resume_workflow_run(db, run["id"])


def test_resume_failed_run_raises(db):
    graph = {
        "nodes": [{"id": "bad", "type": "nonexistent.node", "params": {}}],
        "edges": [],
    }
    created = workflow_service.create_workflow_definition(
        db, WorkflowCreate(workflow_code="wf_res_fail", name="Fail Test", graph=graph),
    )
    workflow_service.activate_workflow_definition(db, created["id"])
    run = workflow_service.start_workflow_run(db, created["id"], WorkflowRunCreate(input={}))
    assert run["status"] == "failed"
    with pytest.raises(ValueError, match="只有暂停的运行可以恢复"):
        workflow_service.resume_workflow_run(db, run["id"])


def test_resume_nonexistent_run_raises(db):
    with pytest.raises(ValueError, match="工作流运行记录不存在"):
        workflow_service.resume_workflow_run(db, 99999)


# ── validate_workflow_graph ────────────────────


def test_validate_valid_graph(db):
    created = _create(db, code="wf_val_ok")
    graph = {
        "nodes": [
            {"id": "s", "type": "control.start", "params": {}},
            {"id": "e", "type": "control.end", "params": {}},
        ],
        "edges": [{"from": "s", "to": "e"}],
    }
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json=graph)
    assert result is not None
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []


def test_validate_invalid_edge(db):
    created = _create(db, code="wf_val_edge")
    graph = {
        "nodes": [{"id": "n1", "type": "noop", "params": {}}],
        "edges": [{"from": "n1", "to": "n99"}],
    }
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json=graph)
    assert result["valid"] is False
    assert any(e["code"] == "INVALID_EDGE_REF" for e in result["errors"])


def test_validate_unknown_node_type(db):
    created = _create(db, code="wf_val_type")
    graph = {
        "nodes": [{"id": "n1", "type": "nonexistent.node", "params": {}}],
        "edges": [],
    }
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json=graph)
    assert result["valid"] is False
    assert any(e["code"] == "UNKNOWN_NODE_TYPE" for e in result["errors"])


def test_validate_cycle(db):
    created = _create(db, code="wf_val_cycle")
    graph = {
        "nodes": [
            {"id": "a", "type": "noop", "params": {}},
            {"id": "b", "type": "noop", "params": {}},
        ],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
    }
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json=graph)
    assert result["valid"] is False
    assert any(e["code"] == "CYCLE_DETECTED" for e in result["errors"])


def test_validate_no_graph_json_uses_current_version(db):
    created = _create(db, code="wf_val_curr")
    result = workflow_service.validate_workflow_graph(db, created["id"])
    assert result is not None
    assert result["valid"] is True


def test_validate_does_not_create_version(db):
    created = _create(db, code="wf_val_nov")
    versions_before = workflow_service.list_workflow_versions(db, created["id"])
    assert len(versions_before) == 1

    workflow_service.validate_workflow_graph(
        db, created["id"],
        graph_json={"nodes": [{"id": "x", "type": "noop", "params": {}}], "edges": []},
    )

    versions_after = workflow_service.list_workflow_versions(db, created["id"])
    assert len(versions_after) == 1
    assert versions_after[0]["version"] == 1


def test_validate_orphan_node_error(db):
    created = _create(db, code="wf_val_orph")
    graph = {
        "nodes": [
            {"id": "n1", "type": "noop", "params": {}},
            {"id": "n2", "type": "noop", "params": {}},
        ],
        "edges": [],
    }
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json=graph)
    assert result["valid"] is False
    assert any(e["code"] == "ORPHAN_NODE" for e in result["errors"])


def test_validate_missing_start_end_warning(db):
    created = _create(db, code="wf_val_se")
    graph = {
        "nodes": [{"id": "n1", "type": "noop", "params": {}}],
        "edges": [],
    }
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json=graph)
    assert result["valid"] is True
    codes = [w["code"] for w in result["warnings"]]
    assert "MISSING_START" in codes
    assert "MISSING_END" in codes


def test_validate_nonexistent_workflow(db):
    result = workflow_service.validate_workflow_graph(db, 99999)
    assert result is None


def test_validate_not_dict_error(db):
    created = _create(db, code="wf_val_nd")
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json="not a dict")
    assert result["valid"] is False
    assert any(e["code"] == "INVALID_STRUCTURE" for e in result["errors"])


def test_validate_empty_nodes_error(db):
    created = _create(db, code="wf_val_en")
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json={"nodes": [], "edges": []})
    assert result["valid"] is False
    assert any(e["code"] == "EMPTY_NODES" for e in result["errors"])


def test_validate_duplicate_node_id(db):
    created = _create(db, code="wf_val_dup")
    graph = {
        "nodes": [
            {"id": "n1", "type": "noop", "params": {}},
            {"id": "n1", "type": "control.start", "params": {}},
        ],
        "edges": [],
    }
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json=graph)
    assert result["valid"] is False
    assert any(e["code"] == "DUPLICATE_NODE_ID" for e in result["errors"])


def test_validate_pause_no_successor_warning(db):
    created = _create(db, code="wf_val_pns")
    graph = {
        "nodes": [{"id": "p", "type": "control.pause", "params": {}}],
        "edges": [],
    }
    result = workflow_service.validate_workflow_graph(db, created["id"], graph_json=graph)
    assert result["valid"] is True
    assert any(w["code"] == "PAUSE_NO_SUCCESSOR" for w in result["warnings"])
