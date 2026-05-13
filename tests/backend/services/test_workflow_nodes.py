"""Unit tests for workflow node handlers."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.workflow_nodes import (
    WorkflowNodeContext,
    _end_node,
    _export_excel,
    _major_balance,
    _month_check,
    _query_balance,
    _query_base,
    _query_cash_journal,
    _query_daily,
    _query_expense,
    _query_income,
    _start_node,
    node_registry,
)


def _ctx(**overrides):
    defaults = {
        "db": MagicMock(),
        "run_id": 1,
        "workflow_input": {},
        "previous_outputs": {},
    }
    defaults.update(overrides)
    return WorkflowNodeContext(**defaults)


# ── control.start / control.end ──────────────


def test_control_start_returns_input():
    ctx = _ctx(workflow_input={"source": "test"})
    result = _start_node({}, ctx)
    assert result["started"] is True
    assert result["input"]["source"] == "test"


def test_control_end_returns_previous_outputs():
    ctx = _ctx(previous_outputs={"step1": {"ok": True}})
    result = _end_node({}, ctx)
    assert result["finished"] is True
    assert result["outputs"]["step1"]["ok"] is True


# ── data.query_daily ─────────────────────────


@patch("services.report_service.daily_report")
def test_query_daily_maps_params(mock_svc):
    mock_svc.return_value = [{"entity": "A"}]
    ctx = _ctx()
    _query_daily({"start_date": "2025-01-01", "end_date": "2025-01-31"}, ctx)
    mock_svc.assert_called_once_with(
        ctx.db, date(2025, 1, 1), date(2025, 1, 31), None,
    )


@patch("services.report_service.daily_report")
def test_query_daily_uses_workflow_input_fallback(mock_svc):
    mock_svc.return_value = []
    ctx = _ctx(workflow_input={"start_date": "2025-03-01", "end_date": "2025-03-31", "entity_id": 5})
    _query_daily({}, ctx)
    mock_svc.assert_called_once_with(
        ctx.db, date(2025, 3, 1), date(2025, 3, 31), 5,
    )


def test_query_daily_missing_start_date_raises():
    with pytest.raises(ValueError, match="缺少必填参数: start_date"):
        _query_daily({"end_date": "2025-01-31"}, _ctx())


def test_query_daily_missing_end_date_raises():
    with pytest.raises(ValueError, match="缺少必填参数: end_date"):
        _query_daily({"start_date": "2025-01-01"}, _ctx())


# ── data.query_cash_journal ──────────────────


@patch("services.report_service.cash_journal")
def test_query_cash_journal_maps_params(mock_svc):
    mock_svc.return_value = [{"account": "B"}]
    ctx = _ctx()
    result = _query_cash_journal(
        {"start_date": "2025-01-01", "end_date": "2025-01-31", "account_id": 3}, ctx,
    )
    mock_svc.assert_called_once_with(
        ctx.db, date(2025, 1, 1), date(2025, 1, 31), 3,
    )
    assert result["rows"][0]["account"] == "B"


def test_query_cash_journal_missing_dates_raises():
    with pytest.raises(ValueError, match="缺少必填参数"):
        _query_cash_journal({}, _ctx())


# ── data.query_balance ───────────────────────


@patch("services.report_service.account_balance")
def test_query_balance_maps_params(mock_svc):
    mock_svc.return_value = [{"entity": "C"}]
    ctx = _ctx()
    result = _query_balance(
        {"start_date": "2025-01-01", "end_date": "2025-01-31"}, ctx,
    )
    mock_svc.assert_called_once_with(
        ctx.db, date(2025, 1, 1), date(2025, 1, 31), None,
    )
    assert result["rows"][0]["entity"] == "C"


def test_query_balance_missing_dates_raises():
    with pytest.raises(ValueError, match="缺少必填参数"):
        _query_balance({}, _ctx())


# ── data.query_income ────────────────────────


@patch("services.report_service.income_list")
def test_query_income_maps_params(mock_svc):
    mock_svc.return_value = {"rows": [], "total": 0}
    ctx = _ctx()
    result = _query_income(
        {"start_date": "2025-01-01", "end_date": "2025-01-31"}, ctx,
    )
    mock_svc.assert_called_once_with(
        ctx.db, date(2025, 1, 1), date(2025, 1, 31), None, 1, 50,
    )
    assert "rows" in result


def test_query_income_missing_dates_raises():
    with pytest.raises(ValueError, match="缺少必填参数"):
        _query_income({}, _ctx())


# ── data.query_expense ───────────────────────


@patch("services.report_service.expense_list")
def test_query_expense_maps_params(mock_svc):
    mock_svc.return_value = {"rows": [], "total": 0}
    ctx = _ctx()
    result = _query_expense(
        {"start_date": "2025-01-01", "end_date": "2025-01-31"}, ctx,
    )
    mock_svc.assert_called_once_with(
        ctx.db, date(2025, 1, 1), date(2025, 1, 31), None, 1, 50,
    )
    assert "rows" in result


def test_query_expense_missing_dates_raises():
    with pytest.raises(ValueError, match="缺少必填参数"):
        _query_expense({}, _ctx())


# ── data.query_base ──────────────────────────


@patch("services.base_data_service.query_base_data")
def test_query_base_maps_params(mock_svc):
    mock_svc.return_value = {"rows": [], "total": 0}
    ctx = _ctx()
    result = _query_base(
        {"date_from": "2025-01-01", "date_to": "2025-01-31", "keyword": "test"}, ctx,
    )
    mock_svc.assert_called_once_with(
        ctx.db,
        date_from="2025-01-01",
        date_to="2025-01-31",
        entity_id=None,
        account_id=None,
        direction=None,
        keyword="test",
        page=1,
        page_size=50,
    )
    assert "rows" in result


def test_query_base_no_required_params():
    """query_base 所有参数都是可选的，不应抛异常。"""
    ctx = _ctx()
    with patch("services.base_data_service.query_base_data", return_value={"rows": []}):
        result = _query_base({}, ctx)
    assert "rows" in result


# ── report.major_balance ─────────────────────


@patch("services.report_service.major_balance")
def test_major_balance_maps_params(mock_svc):
    mock_svc.return_value = [{"entity": "D"}]
    ctx = _ctx()
    result = _major_balance(
        {"start_date": "2025-01-01", "end_date": "2025-01-31", "entity_id": 2}, ctx,
    )
    mock_svc.assert_called_once_with(
        ctx.db, date(2025, 1, 1), date(2025, 1, 31), 2,
    )
    assert result["rows"][0]["entity"] == "D"


def test_major_balance_missing_dates_raises():
    with pytest.raises(ValueError, match="缺少必填参数"):
        _major_balance({}, _ctx())


# ── report.month_check ───────────────────────


@patch("services.report_service.month_check")
def test_month_check_maps_params(mock_svc):
    mock_svc.return_value = [{"entity": "E"}]
    ctx = _ctx()
    result = _month_check({"year": 2025, "month": 3, "entity_id": 1}, ctx)
    mock_svc.assert_called_once_with(ctx.db, 2025, 3, 1)
    assert result["rows"][0]["entity"] == "E"


def test_month_check_missing_year_raises():
    with pytest.raises(ValueError, match="缺少必填参数: year"):
        _month_check({"month": 3}, _ctx())


def test_month_check_missing_month_raises():
    with pytest.raises(ValueError, match="缺少必填参数: month"):
        _month_check({"year": 2025}, _ctx())


# ── export.excel ─────────────────────────────


@patch("services.export_service.generate_export")
def test_export_excel_maps_params(mock_svc):
    mock_svc.return_value = "/tmp/export.xlsx"
    ctx = _ctx()
    result = _export_excel(
        {"export_type": "daily", "start_date": "2025-01-01", "end_date": "2025-01-31"}, ctx,
    )
    mock_svc.assert_called_once_with(
        ctx.db,
        export_type="daily",
        start_date="2025-01-01",
        end_date="2025-01-31",
        entity_id=None,
        account_id=None,
        year=None,
        month=None,
    )
    assert result == {"file_path": "/tmp/export.xlsx"}


def test_export_excel_missing_type_raises():
    with pytest.raises(ValueError, match="缺少必填参数: export_type"):
        _export_excel({}, _ctx())


# ── 统一缺参参数化测试 ───────────────────────


_VALID_VALUES = {
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "year": 2025,
    "month": 1,
    "export_type": "daily",
}


@pytest.mark.parametrize("node_type,required_keys", [
    ("data.query_daily", ["start_date", "end_date"]),
    ("data.query_cash_journal", ["start_date", "end_date"]),
    ("data.query_balance", ["start_date", "end_date"]),
    ("data.query_income", ["start_date", "end_date"]),
    ("data.query_expense", ["start_date", "end_date"]),
    ("report.major_balance", ["start_date", "end_date"]),
    ("report.month_check", ["year", "month"]),
    ("export.excel", ["export_type"]),
])
def test_missing_required_params_raises(node_type, required_keys):
    handler = node_registry.get(node_type)
    for key in required_keys:
        params = {k: _VALID_VALUES[k] for k in required_keys if k != key}
        with pytest.raises(ValueError, match="缺少必填参数"):
            handler(params, _ctx())
