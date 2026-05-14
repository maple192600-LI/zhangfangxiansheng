"""Workflow executor unit tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from database import Base
from db.tables import WorkflowRun, WorkflowRunStep, WorkflowVersion
from services import workflow_executor


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


def _make_run(db, graph_json, input_json="{}"):
    version = WorkflowVersion(
        workflow_id=1,
        version=1,
        graph_json=graph_json,
        created_by="tester",
    )
    db.add(version)
    db.flush()
    run = WorkflowRun(
        workflow_id=1,
        workflow_version_id=version.id,
        workflow_code="wf_exec",
        workflow_version=1,
        status="pending",
        input_json=input_json,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run, version


# ── simple success chain ──────────────────────


def test_start_noop_end_completes(db):
    graph = '{"nodes":[{"id":"s","type":"control.start","params":{}},{"id":"m","type":"noop","params":{"msg":"hi"}},{"id":"e","type":"control.end","params":{}}],"edges":[{"from":"s","to":"m"},{"from":"m","to":"e"}]}'
    run, version = _make_run(db, graph)
    result = workflow_executor.execute_workflow(db, run, version)
    steps = db.query(WorkflowRunStep).filter(WorkflowRunStep.run_id == run.id).order_by(WorkflowRunStep.id).all()

    assert result.status == "completed"
    assert result.output_json is not None
    assert len(steps) == 3
    assert steps[0].node_id == "s"
    assert steps[0].status == "completed"
    assert steps[1].node_id == "m"
    assert steps[1].status == "completed"
    assert steps[2].node_id == "e"
    assert steps[2].status == "completed"


# ── pause chain ───────────────────────────────


def test_pause_stops_before_later_nodes(db):
    graph = '{"nodes":[{"id":"s","type":"control.start","params":{}},{"id":"p","type":"control.pause","params":{}},{"id":"e","type":"control.end","params":{}}],"edges":[{"from":"s","to":"p"},{"from":"p","to":"e"}]}'
    run, version = _make_run(db, graph)
    result = workflow_executor.execute_workflow(db, run, version)
    steps = db.query(WorkflowRunStep).filter(WorkflowRunStep.run_id == run.id).all()

    assert result.status == "paused"
    assert len(steps) == 2
    assert steps[0].node_id == "s"
    assert steps[0].status == "completed"
    assert steps[1].node_id == "p"
    assert steps[1].status == "paused"
    # end node should NOT have been executed


# ── failed chain — unknown node ───────────────


def test_unknown_node_fails_run(db):
    graph = '{"nodes":[{"id":"bad","type":"nonexistent.node","params":{}}],"edges":[]}'
    run, version = _make_run(db, graph)
    result = workflow_executor.execute_workflow(db, run, version)
    step = db.query(WorkflowRunStep).filter(WorkflowRunStep.run_id == run.id).first()

    assert result.status == "failed"
    assert result.error_message is not None
    assert "未知工作流节点" in result.error_message
    assert step is not None
    assert step.status == "failed"
    assert step.error_message is not None


# ── topological ordering ──────────────────────


def test_unordered_nodes_execute_in_edge_order(db):
    graph = '{"nodes":[{"id":"z","type":"noop","params":{}},{"id":"a","type":"noop","params":{}},{"id":"m","type":"noop","params":{}}],"edges":[{"from":"a","to":"m"},{"from":"m","to":"z"}]}'
    run, version = _make_run(db, graph)
    result = workflow_executor.execute_workflow(db, run, version)
    steps = db.query(WorkflowRunStep).filter(WorkflowRunStep.run_id == run.id).order_by(WorkflowRunStep.id).all()

    assert result.status == "completed"
    assert [s.node_id for s in steps] == ["a", "m", "z"]


# ── cycle detection ───────────────────────────


def test_cycle_in_graph_raises(db):
    graph = '{"nodes":[{"id":"a","type":"noop","params":{}},{"id":"b","type":"noop","params":{}}],"edges":[{"from":"a","to":"b"},{"from":"b","to":"a"}]}'
    run, version = _make_run(db, graph)
    result = workflow_executor.execute_workflow(db, run, version)
    assert result.status == "failed"
    assert "循环" in result.error_message


# ── resume: success chain ──────────────────────


def test_resume_completes_after_pause(db):
    graph = '{"nodes":[{"id":"s","type":"control.start","params":{}},{"id":"p","type":"control.pause","params":{}},{"id":"m","type":"noop","params":{}},{"id":"e","type":"control.end","params":{}}],"edges":[{"from":"s","to":"p"},{"from":"p","to":"m"},{"from":"m","to":"e"}]}'
    run, version = _make_run(db, graph)

    # First execution stops at pause
    result = workflow_executor.execute_workflow(db, run, version)
    assert result.status == "paused"
    steps_before = db.query(WorkflowRunStep).filter(WorkflowRunStep.run_id == run.id).all()
    assert len(steps_before) == 2
    assert steps_before[0].node_id == "s"
    assert steps_before[0].status == "completed"
    assert steps_before[1].node_id == "p"
    assert steps_before[1].status == "paused"

    # Resume
    resumed = workflow_executor.resume_workflow(db, run, version)
    assert resumed.status == "completed"

    all_steps = db.query(WorkflowRunStep).filter(WorkflowRunStep.run_id == run.id).order_by(WorkflowRunStep.id).all()
    assert len(all_steps) == 4
    assert all_steps[2].node_id == "m"
    assert all_steps[2].status == "completed"
    assert all_steps[3].node_id == "e"
    assert all_steps[3].status == "completed"

    output = json.loads(resumed.output_json)
    assert "s" in output
    assert "m" in output
    assert "e" in output


def test_resume_does_not_reexecute_completed_nodes(db):
    graph = '{"nodes":[{"id":"s","type":"control.start","params":{}},{"id":"p","type":"control.pause","params":{}},{"id":"e","type":"control.end","params":{}}],"edges":[{"from":"s","to":"p"},{"from":"p","to":"e"}]}'
    run, version = _make_run(db, graph)

    workflow_executor.execute_workflow(db, run, version)
    steps_before = db.query(WorkflowRunStep).filter(WorkflowRunStep.run_id == run.id).all()
    start_step_count = len(steps_before)

    workflow_executor.resume_workflow(db, run, version)
    all_steps = db.query(WorkflowRunStep).filter(WorkflowRunStep.run_id == run.id).all()
    # Only end node should be added (pause node is skipped, start node is skipped)
    assert len(all_steps) == start_step_count + 1


# ── resume: failure chain ──────────────────────


def test_resume_failure_records_failed_step(db):
    graph = '{"nodes":[{"id":"s","type":"control.start","params":{}},{"id":"p","type":"control.pause","params":{}},{"id":"bad","type":"nonexistent.node","params":{}},{"id":"e","type":"control.end","params":{}}],"edges":[{"from":"s","to":"p"},{"from":"p","to":"bad"},{"from":"bad","to":"e"}]}'
    run, version = _make_run(db, graph)

    workflow_executor.execute_workflow(db, run, version)
    assert run.status == "paused"

    resumed = workflow_executor.resume_workflow(db, run, version)
    assert resumed.status == "failed"
    assert resumed.error_message is not None
    assert "未知工作流节点" in resumed.error_message

    all_steps = db.query(WorkflowRunStep).filter(WorkflowRunStep.run_id == run.id).order_by(WorkflowRunStep.id).all()
    bad_step = [s for s in all_steps if s.node_id == "bad"][0]
    assert bad_step.status == "failed"
    assert bad_step.error_message is not None


# ── resume: non-paused run ─────────────────────


def test_resume_completed_run_still_runs(db):
    """resume_workflow does not guard status — that's the service layer's job."""
    graph = '{"nodes":[{"id":"s","type":"control.start","params":{}},{"id":"e","type":"control.end","params":{}}],"edges":[{"from":"s","to":"e"}]}'
    run, version = _make_run(db, graph)
    workflow_executor.execute_workflow(db, run, version)
    assert run.status == "completed"

    # Executor-level resume does not check status; it just re-runs the loop.
    # Status guard is in the service layer.
    resumed = workflow_executor.resume_workflow(db, run, version)
    assert resumed.status == "completed"
