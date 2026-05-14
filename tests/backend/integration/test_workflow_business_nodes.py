"""Workflow business node integration tests.

Tests go through the full chain:
  workflow_service.create → activate → start_workflow_run → executor → step records → node handlers.

Business nodes call real report_service / base_data_service against a seeded test database.
Only export.excel mocks the file write to avoid real Excel I/O.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from database import Base
from db.schemas import WorkflowCreate, WorkflowRunCreate
from db.tables import Account, Bank, Division, Entity, FundEvent, ImportBatch, WorkflowRunStep
from services import workflow_service


# ── Fixtures ──────────────────────────────────


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
def seeded(db):
    now = datetime.now()
    division = Division(
        division_code="D01", name="联调板块", status="enabled",
        created_at=now, updated_at=now,
    )
    db.add(division)
    db.flush()

    entity = Entity(
        division_id=division.id, entity_code="E01", name="联调实体有限公司",
        short_name="联调实体", status="enabled",
        created_at=now, updated_at=now,
    )
    db.add(entity)
    db.flush()

    bank = Bank(
        bank_code="B01", bank_name="联调银行", status="enabled",
        created_at=now, updated_at=now,
    )
    db.add(bank)
    db.flush()

    account = Account(
        entity_id=entity.id, bank_id=bank.id,
        account_code="A01", account_alias="联调主账户",
        account_type="basic", instrument_type="银行存款",
        input_method="online", currency="CNY",
        initial_balance=10000, balance_date=date(2026, 1, 1),
        status="enabled", include_in_daily_report=True,
        created_at=now, updated_at=now,
    )
    db.add(account)
    db.flush()

    batch = ImportBatch(
        batch_code="BATCH_INT", source_type="test", source_name="int_test",
        status="uploaded", created_at=now, updated_at=now,
    )
    db.add(batch)
    db.flush()

    fund_event = FundEvent(
        batch_id=batch.id,
        business_date=date(2026, 3, 15),
        entity_code=entity.entity_code, entity_name=entity.short_name,
        account_code=account.account_code, account_name=account.account_alias,
        summary="测试收入", counterparty="供应商A",
        amount_in=5000, amount_out=0,
        rolling_balance=15000, state="正常", source="网银导入",
    )
    db.add(fund_event)
    db.commit()

    return {
        "division": division,
        "entity": entity,
        "bank": bank,
        "account": account,
        "batch": batch,
        "fund_event": fund_event,
    }


def _create_and_activate(db, code, nodes, edges):
    graph = {"nodes": nodes, "edges": edges}
    wf = workflow_service.create_workflow_definition(
        db, WorkflowCreate(workflow_code=code, name=code, graph=graph),
    )
    workflow_service.activate_workflow_definition(db, wf["id"])
    return wf


def _run(db, wf, input_data=None):
    return workflow_service.start_workflow_run(
        db, wf["id"], WorkflowRunCreate(input=input_data or {}),
    )


# ── A. Query nodes via full workflow chain ────


def test_data_query_daily_via_executor(db, seeded):
    wf = _create_and_activate(db, "int_daily", [
        {"id": "start", "type": "control.start", "params": {}},
        {"id": "q", "type": "data.query_daily", "params": {
            "start_date": "2026-03-01", "end_date": "2026-03-31",
        }},
        {"id": "end", "type": "control.end", "params": {}},
    ], [
        {"from": "start", "to": "q"},
        {"from": "q", "to": "end"},
    ])
    run = _run(db, wf)

    assert run["status"] == "completed"
    output = run["output"]
    assert "q" in output
    assert isinstance(output["q"]["rows"], list)
    assert len(output["q"]["rows"]) == 1
    assert output["q"]["rows"][0]["entity_name"] == "联调实体"
    assert output["q"]["rows"][0]["ending_balance"] == 15000.0

    steps = db.query(WorkflowRunStep).filter(
        WorkflowRunStep.run_id == run["id"],
    ).order_by(WorkflowRunStep.id).all()
    assert len(steps) == 3
    assert all(s.status == "completed" for s in steps)


def test_data_query_cash_journal_via_executor(db, seeded):
    wf = _create_and_activate(db, "int_cash", [
        {"id": "q", "type": "data.query_cash_journal", "params": {
            "start_date": "2026-03-01", "end_date": "2026-03-31",
        }},
    ], [])
    run = _run(db, wf)

    assert run["status"] == "completed"
    rows = run["output"]["q"]["rows"]
    assert len(rows) == 1
    assert rows[0]["account_code"] == "A01"
    assert rows[0]["total_income"] == 5000.0


def test_data_query_balance_via_executor(db, seeded):
    wf = _create_and_activate(db, "int_balance", [
        {"id": "q", "type": "data.query_balance", "params": {
            "start_date": "2026-03-01", "end_date": "2026-03-31",
        }},
    ], [])
    run = _run(db, wf)

    assert run["status"] == "completed"
    rows = run["output"]["q"]["rows"]
    assert len(rows) >= 1
    non_sub = [r for r in rows if not r["is_subtotal"]]
    assert len(non_sub) == 1
    assert non_sub[0]["ending_balance"] == 15000.0


def test_data_query_base_via_executor(db, seeded):
    wf = _create_and_activate(db, "int_base", [
        {"id": "q", "type": "data.query_base", "params": {
            "date_from": "2026-03-01", "date_to": "2026-03-31",
        }},
    ], [])
    run = _run(db, wf)

    assert run["status"] == "completed"
    result = run["output"]["q"]
    assert "items" in result
    assert result["total"] == 1
    assert result["items"][0]["summary_text"] == "测试收入"


def test_report_month_check_via_executor(db, seeded):
    wf = _create_and_activate(db, "int_month", [
        {"id": "q", "type": "report.month_check", "params": {
            "year": 2026, "month": 3,
        }},
    ], [])
    run = _run(db, wf)

    assert run["status"] == "completed"
    rows = run["output"]["q"]["rows"]
    non_sub = [r for r in rows if not r["is_subtotal"]]
    assert len(non_sub) == 1
    assert non_sub[0]["ending_balance"] == 15000.0

    steps = db.query(WorkflowRunStep).filter(
        WorkflowRunStep.run_id == run["id"],
    ).all()
    assert len(steps) == 1
    assert steps[0].node_type == "report.month_check"
    assert steps[0].status == "completed"


# ── B. Export node via executor ───────────────


def test_export_excel_via_executor(db, seeded):
    wf = _create_and_activate(db, "int_export", [
        {"id": "ex", "type": "export.excel", "params": {
            "export_type": "daily_report",
            "start_date": "2026-03-01", "end_date": "2026-03-31",
        }},
    ], [])

    with patch("services.export_service.generate_export", return_value="/tmp/test_export.xlsx"):
        run = _run(db, wf)

    assert run["status"] == "completed"
    assert run["output"]["ex"]["file_path"] == "/tmp/test_export.xlsx"

    step = db.query(WorkflowRunStep).filter(
        WorkflowRunStep.run_id == run["id"],
    ).first()
    assert step is not None
    assert step.status == "completed"
    assert step.node_type == "export.excel"


# ── C. Multi-node business chain ──────────────


def test_start_query_export_end_chain(db, seeded):
    wf = _create_and_activate(db, "int_chain", [
        {"id": "s", "type": "control.start", "params": {}},
        {"id": "q", "type": "data.query_daily", "params": {
            "start_date": "2026-03-01", "end_date": "2026-03-31",
        }},
        {"id": "ex", "type": "export.excel", "params": {
            "export_type": "daily_report",
            "start_date": "2026-03-01", "end_date": "2026-03-31",
        }},
        {"id": "e", "type": "control.end", "params": {}},
    ], [
        {"from": "s", "to": "q"},
        {"from": "q", "to": "ex"},
        {"from": "ex", "to": "e"},
    ])

    with patch("services.export_service.generate_export", return_value="/tmp/chain_export.xlsx"):
        run = _run(db, wf)

    assert run["status"] == "completed"
    output = run["output"]

    assert output["s"]["started"] is True
    assert len(output["q"]["rows"]) == 1
    assert output["ex"]["file_path"] == "/tmp/chain_export.xlsx"
    assert output["e"]["finished"] is True
    assert "s" in output["e"]["outputs"]
    assert "q" in output["e"]["outputs"]
    assert "ex" in output["e"]["outputs"]
    assert "e" not in output["e"]["outputs"]  # snapshot, no circular ref

    steps = db.query(WorkflowRunStep).filter(
        WorkflowRunStep.run_id == run["id"],
    ).order_by(WorkflowRunStep.id).all()
    assert len(steps) == 4
    assert all(s.status == "completed" for s in steps)

    step_output = json.loads(steps[3].output_json)
    assert step_output["finished"] is True
    assert "s" in step_output["outputs"]


# ── D. Parameter missing → fail ───────────────


def test_missing_required_params_fails_run(db, seeded):
    wf = _create_and_activate(db, "int_noparam", [
        {"id": "s", "type": "control.start", "params": {}},
        {"id": "q", "type": "data.query_daily", "params": {}},
    ], [
        {"from": "s", "to": "q"},
    ])
    run = _run(db, wf)

    assert run["status"] == "failed"
    assert "缺少必填参数" in run["error_message"]

    steps = db.query(WorkflowRunStep).filter(
        WorkflowRunStep.run_id == run["id"],
    ).order_by(WorkflowRunStep.id).all()
    assert len(steps) == 2
    assert steps[0].status == "completed"  # control.start succeeded
    assert steps[1].status == "failed"
    assert steps[1].node_type == "data.query_daily"
    assert "缺少必填参数" in steps[1].error_message
