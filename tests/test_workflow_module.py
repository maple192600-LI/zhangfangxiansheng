"""Workflow module contract tests."""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import Base, get_db
from db.schemas import WorkflowCreate, WorkflowPatchRequest, WorkflowRunCreate
from db.tables import Workflow, WorkflowRun, WorkflowRunStep, WorkflowVersion
from services import workflow_service
from services.workflow_nodes import node_registry


@pytest.fixture()
def db_session():
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


def _single_noop_graph():
    return {
        "nodes": [
            {"id": "prepare", "type": "noop", "params": {"message": "ready"}},
        ],
        "edges": [],
    }


@pytest.fixture()
def workflow_api_client(db_session):
    from api.workflow import router

    app = FastAPI()
    app.include_router(router, prefix="/api")

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_workflow_router_has_expected_prefix():
    from api.workflow import router

    assert router.prefix == "/workflow"


def test_workflow_api_exposes_node_registry(workflow_api_client):
    response = workflow_api_client.get("/api/workflow/nodes")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert "noop" in body["data"]["items"]


def test_workflow_api_creates_definition(workflow_api_client):
    response = workflow_api_client.post(
        "/api/workflow/workflows",
        json={
            "workflow_code": "wf_api_noop",
            "name": "API Noop",
            "graph": _single_noop_graph(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["workflow_code"] == "wf_api_noop"
    assert body["data"]["status"] == "draft"
    assert body["data"]["current_version"]["version"] == 1


def test_workflow_module_does_not_import_legacy_fund_agent():
    import api.workflow
    import services.workflow_executor
    import services.workflow_service

    module_names = set(sys.modules.keys())
    assert "agents.fund" not in module_names

    for module in (api.workflow, services.workflow_executor, services.workflow_service):
        src = Path(module.__file__).read_text(encoding="utf-8")
        assert "agents.fund" not in src
        assert "fund_skill_run" not in src
        assert "FundAgent" not in src


def test_node_registry_exposes_noop_and_rejects_unknown_node():
    assert node_registry.has("noop") is True
    assert node_registry.has("control.pause") is True

    with pytest.raises(ValueError, match="未知工作流节点"):
        node_registry.get("missing.node")


def test_create_activate_and_list_workflow_definition(db_session):
    created = workflow_service.create_workflow_definition(
        db_session,
        WorkflowCreate(
            workflow_code="wf_daily_import",
            name="Daily Import",
            description="Test workflow",
            graph=_single_noop_graph(),
            created_by="tester",
        ),
    )
    activated = workflow_service.activate_workflow_definition(db_session, created["id"])
    listed = workflow_service.list_workflow_definitions(db_session, status="active")
    version_row = db_session.query(WorkflowVersion).filter(
        WorkflowVersion.workflow_id == created["id"]
    ).first()

    assert created["status"] == "draft"
    assert created["current_version"]["version"] == 1
    assert activated["status"] == "active"
    assert listed[0]["workflow_code"] == "wf_daily_import"
    assert version_row.graph_json.startswith("{")


def test_apply_patch_creates_new_version_without_overwriting_old_graph(db_session):
    created = workflow_service.create_workflow_definition(
        db_session,
        WorkflowCreate(
            workflow_code="wf_patch",
            name="Patch Workflow",
            graph=_single_noop_graph(),
        ),
    )

    patched = workflow_service.apply_workflow_patch(
        db_session,
        created["id"],
        WorkflowPatchRequest(
            patches=[
                {
                    "op": "replace_graph",
                    "graph": {
                        "nodes": [
                            {"id": "prepare", "type": "noop", "params": {}},
                            {"id": "finish", "type": "noop", "params": {"done": True}},
                        ],
                        "edges": [{"from": "prepare", "to": "finish"}],
                    },
                }
            ],
            created_by="tester",
            change_summary="add finish node",
        ),
    )
    versions = db_session.query(WorkflowVersion).filter(
        WorkflowVersion.workflow_id == created["id"]
    ).order_by(WorkflowVersion.version.asc()).all()

    assert patched["current_version"]["version"] == 2
    assert len(versions) == 2
    assert '"finish"' not in versions[0].graph_json
    assert '"finish"' in versions[1].graph_json


def test_start_workflow_run_executes_nodes_and_records_steps(db_session):
    definition = workflow_service.create_workflow_definition(
        db_session,
        WorkflowCreate(
            workflow_code="wf_noop",
            name="Noop Workflow",
            graph=_single_noop_graph(),
        ),
    )
    workflow_service.activate_workflow_definition(db_session, definition["id"])

    run = workflow_service.start_workflow_run(
        db_session,
        definition["id"],
        WorkflowRunCreate(input={"source": "test"}),
    )
    step_rows = db_session.query(WorkflowRunStep).filter(
        WorkflowRunStep.run_id == run["id"]
    ).all()

    assert run["status"] == "completed"
    assert run["output"]["prepare"]["ok"] is True
    assert len(step_rows) == 1
    assert step_rows[0].node_id == "prepare"
    assert step_rows[0].status == "completed"


def test_unknown_node_fails_run_and_records_error_step(db_session):
    definition = workflow_service.create_workflow_definition(
        db_session,
        WorkflowCreate(
            workflow_code="wf_bad",
            name="Bad Workflow",
            graph={
                "nodes": [{"id": "bad", "type": "missing.node", "params": {}}],
                "edges": [],
            },
        ),
    )
    workflow_service.activate_workflow_definition(db_session, definition["id"])

    run = workflow_service.start_workflow_run(
        db_session,
        definition["id"],
        WorkflowRunCreate(input={}),
    )
    stored_run = db_session.query(WorkflowRun).filter(WorkflowRun.id == run["id"]).first()
    error_step = db_session.query(WorkflowRunStep).filter(
        WorkflowRunStep.run_id == run["id"]
    ).first()

    assert run["status"] == "failed"
    assert "未知工作流节点" in run["error_message"]
    assert stored_run.status == "failed"
    assert error_step.status == "failed"
    assert error_step.error_message


def test_edge_order_controls_execution_order(db_session):
    definition = workflow_service.create_workflow_definition(
        db_session,
        WorkflowCreate(
            workflow_code="wf_edges",
            name="Edge Workflow",
            graph={
                "nodes": [
                    {"id": "finish", "type": "noop", "params": {}},
                    {"id": "prepare", "type": "noop", "params": {}},
                ],
                "edges": [{"from": "prepare", "to": "finish"}],
            },
        ),
    )
    workflow_service.activate_workflow_definition(db_session, definition["id"])

    run = workflow_service.start_workflow_run(
        db_session,
        definition["id"],
        WorkflowRunCreate(input={}),
    )
    step_rows = db_session.query(WorkflowRunStep).filter(
        WorkflowRunStep.run_id == run["id"]
    ).order_by(WorkflowRunStep.id.asc()).all()

    assert [step.node_id for step in step_rows] == ["prepare", "finish"]


def test_control_pause_marks_run_paused(db_session):
    definition = workflow_service.create_workflow_definition(
        db_session,
        WorkflowCreate(
            workflow_code="wf_pause",
            name="Pause Workflow",
            graph={
                "nodes": [
                    {"id": "review", "type": "control.pause", "params": {"reason": "need approval"}},
                    {"id": "finish", "type": "noop", "params": {}},
                ],
                "edges": [{"from": "review", "to": "finish"}],
            },
        ),
    )
    workflow_service.activate_workflow_definition(db_session, definition["id"])

    run = workflow_service.start_workflow_run(
        db_session,
        definition["id"],
        WorkflowRunCreate(input={}),
    )
    step_rows = db_session.query(WorkflowRunStep).filter(
        WorkflowRunStep.run_id == run["id"]
    ).all()

    assert run["status"] == "paused"
    assert len(step_rows) == 1
    assert step_rows[0].node_id == "review"
    assert step_rows[0].status == "paused"


def test_workflow_tables_are_registered_with_metadata():
    assert Workflow.__tablename__ == "workflows"
    assert WorkflowVersion.__tablename__ == "workflow_versions"
    assert WorkflowRun.__tablename__ == "workflow_runs"
    assert WorkflowRunStep.__tablename__ == "workflow_run_steps"


def test_node_registry_has_all_executable_nodes():
    expected = [
        "noop", "control.pause", "control.start", "control.end",
        "data.query_daily", "data.query_cash_journal", "data.query_balance",
        "data.query_income", "data.query_expense", "data.query_base",
        "report.major_balance", "report.month_check", "export.excel",
    ]
    for t in expected:
        assert node_registry.has(t), f"{t} 未注册"


def test_node_registry_excludes_deferred_nodes():
    deferred = [
        "data.bank_import", "data.manual_excel",
        "report.generate", "agent.invoke",
    ]
    for t in deferred:
        assert not node_registry.has(t), f"{t} 不应注册"
