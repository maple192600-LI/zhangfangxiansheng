"""Workflow API smoke tests — all 11 endpoints."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from database import Base, get_db


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


@pytest.fixture()
def client(db):
    from api.workflow import router

    app = FastAPI()
    app.include_router(router, prefix="/api")

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def _graph():
    return {
        "nodes": [{"id": "n1", "type": "noop", "params": {}}],
        "edges": [],
    }


def _create_workflow(client, code="wf_api"):
    resp = client.post("/api/workflow/workflows", json={
        "workflow_code": code,
        "name": "API Test",
        "graph": _graph(),
    })
    assert resp.json()["code"] == 0
    return resp.json()["data"]


# W1: GET /nodes


def test_w1_list_nodes(client):
    resp = client.get("/api/workflow/nodes")
    body = resp.json()
    assert body["code"] == 0
    items = body["data"]["items"]
    assert len(items) == 13
    assert "control.start" in items
    assert "control.end" in items
    assert "noop" in items
    assert "control.pause" in items
    assert "export.excel" in items


# W2: POST /workflows


def test_w2_create_workflow(client):
    data = _create_workflow(client, code="wf_w2")
    assert data["workflow_code"] == "wf_w2"
    assert data["status"] == "draft"
    assert data["current_version"]["version"] == 1


# W3: GET /workflows


def test_w3_list_workflows(client):
    _create_workflow(client, code="wf_list1")
    _create_workflow(client, code="wf_list2")
    resp = client.get("/api/workflow/workflows")
    body = resp.json()
    assert body["code"] == 0
    assert len(body["data"]) == 2


def test_w3_list_workflows_status_filter(client):
    _create_workflow(client, code="wf_filt_draft")
    resp = client.get("/api/workflow/workflows", params={"status": "draft"})
    assert len(resp.json()["data"]) == 1
    resp2 = client.get("/api/workflow/workflows", params={"status": "active"})
    assert len(resp2.json()["data"]) == 0


# W4: GET /workflows/{id}


def test_w4_get_workflow(client):
    created = _create_workflow(client, code="wf_get")
    resp = client.get(f"/api/workflow/workflows/{created['id']}")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["workflow_code"] == "wf_get"


def test_w4_get_workflow_not_found(client):
    resp = client.get("/api/workflow/workflows/99999")
    assert resp.json()["code"] == 2001


# W5: PUT /workflows/{id}


def test_w5_update_workflow(client):
    created = _create_workflow(client, code="wf_upd")
    resp = client.put(f"/api/workflow/workflows/{created['id']}", json={
        "name": "Updated Name",
        "description": "Updated Desc",
    })
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["name"] == "Updated Name"
    assert body["data"]["description"] == "Updated Desc"


# W6: PATCH /workflows/{id}/graph


def test_w6_patch_replace_graph(client):
    created = _create_workflow(client, code="wf_patch")
    resp = client.patch(f"/api/workflow/workflows/{created['id']}/graph", json={
        "patches": [{"op": "replace_graph", "graph": {
            "nodes": [
                {"id": "a", "type": "noop", "params": {}},
                {"id": "b", "type": "noop", "params": {}},
            ],
            "edges": [{"from": "a", "to": "b"}],
        }}],
        "change_summary": "v2",
    })
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["current_version"]["version"] == 2


def test_w6_patch_unsupported_op(client):
    created = _create_workflow(client, code="wf_badpatch")
    resp = client.patch(f"/api/workflow/workflows/{created['id']}/graph", json={
        "patches": [{"op": "nuke"}],
    })
    assert resp.json()["code"] == 1002


# W7: POST /workflows/{id}/activate


def test_w7_activate_workflow(client):
    created = _create_workflow(client, code="wf_act")
    resp = client.post(f"/api/workflow/workflows/{created['id']}/activate")
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["status"] == "active"


# W8: POST /workflows/{id}/archive


def test_w8_archive_workflow(client):
    created = _create_workflow(client, code="wf_arch")
    resp = client.post(f"/api/workflow/workflows/{created['id']}/archive")
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["status"] == "archived"


# W9: POST /workflows/{id}/runs


def test_w9_start_run(client):
    created = _create_workflow(client, code="wf_run")
    client.post(f"/api/workflow/workflows/{created['id']}/activate")
    resp = client.post(f"/api/workflow/workflows/{created['id']}/runs", json={"input": {"x": 1}})
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "completed"
    assert body["data"]["output"]["n1"]["ok"] is True


def test_w9_start_run_draft_blocked(client):
    created = _create_workflow(client, code="wf_draft")
    resp = client.post(f"/api/workflow/workflows/{created['id']}/runs", json={"input": {}})
    assert resp.json()["code"] == 2001


# W10: GET /runs


def test_w10_list_runs(client):
    created = _create_workflow(client, code="wf_runlist")
    client.post(f"/api/workflow/workflows/{created['id']}/activate")
    client.post(f"/api/workflow/workflows/{created['id']}/runs", json={"input": {}})

    resp = client.get("/api/workflow/runs", params={"workflow_id": created["id"]})
    body = resp.json()
    assert body["code"] == 0
    assert len(body["data"]) == 1
    assert body["data"][0]["status"] == "completed"


# W11: GET /runs/{run_id}


def test_w11_get_run_with_steps(client):
    created = _create_workflow(client, code="wf_runget")
    client.post(f"/api/workflow/workflows/{created['id']}/activate")
    run_resp = client.post(f"/api/workflow/workflows/{created['id']}/runs", json={"input": {}})
    run_id = run_resp.json()["data"]["id"]

    resp = client.get(f"/api/workflow/runs/{run_id}")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] == run_id
    assert "steps" in body["data"]
    assert len(body["data"]["steps"]) == 1
    assert body["data"]["steps"][0]["node_id"] == "n1"
    assert body["data"]["steps"][0]["status"] == "completed"


def test_w11_get_run_not_found(client):
    resp = client.get("/api/workflow/runs/99999")
    assert resp.json()["code"] == 2001
