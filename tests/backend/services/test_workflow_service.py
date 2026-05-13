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
