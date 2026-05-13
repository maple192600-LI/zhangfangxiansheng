"""Deterministic workflow node registry."""
from __future__ import annotations

from datetime import date
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class WorkflowNodeContext:
    db: Session
    run_id: int
    workflow_input: dict[str, Any]
    previous_outputs: dict[str, Any]


NodeHandler = Callable[[dict[str, Any], WorkflowNodeContext], dict[str, Any]]


class WorkflowNodeRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, NodeHandler] = {}

    def register(self, node_type: str, handler: NodeHandler) -> None:
        if not node_type:
            raise ValueError("工作流节点类型不能为空")
        self._handlers[node_type] = handler

    def has(self, node_type: str) -> bool:
        return node_type in self._handlers

    def get(self, node_type: str) -> NodeHandler:
        try:
            return self._handlers[node_type]
        except KeyError as exc:
            raise ValueError(f"未知工作流节点: {node_type}") from exc

    def list_types(self) -> list[str]:
        return sorted(self._handlers)


# ── 参数辅助 ──────────────────────────────────


def _get_param(params: dict, ctx: WorkflowNodeContext, key: str, default: Any = None) -> Any:
    """params 优先，缺省从 workflow_input 取，最后用 default。"""
    if key in params and params[key] is not None:
        return params[key]
    if key in ctx.workflow_input and ctx.workflow_input[key] is not None:
        return ctx.workflow_input[key]
    return default


def _require_param(params: dict, ctx: WorkflowNodeContext, key: str) -> Any:
    val = _get_param(params, ctx, key)
    if val is None:
        raise ValueError(f"缺少必填参数: {key}")
    return val


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"无效的日期格式: {value!r}")


def _require_date(params: dict, ctx: WorkflowNodeContext, key: str) -> date:
    return _parse_date(_require_param(params, ctx, key))


# ── 纯控制节点 ────────────────────────────────


def _noop_node(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    return {
        "ok": True,
        "params": params,
        "input": ctx.workflow_input,
    }


def _pause_node(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    return {
        "paused": True,
        "params": params,
        "run_id": ctx.run_id,
    }


def _start_node(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    return {
        "started": True,
        "input": ctx.workflow_input,
    }


def _end_node(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    return {
        "finished": True,
        "outputs": ctx.previous_outputs,
    }


# ── 数据查询节点 ──────────────────────────────


def _query_daily(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    from services.report_service import daily_report

    start_date = _require_date(params, ctx, "start_date")
    end_date = _require_date(params, ctx, "end_date")
    entity_id = _get_param(params, ctx, "entity_id")

    rows = daily_report(ctx.db, start_date, end_date, entity_id)
    return {"rows": rows}


def _query_cash_journal(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    from services.report_service import cash_journal

    start_date = _require_date(params, ctx, "start_date")
    end_date = _require_date(params, ctx, "end_date")
    account_id = _get_param(params, ctx, "account_id")

    rows = cash_journal(ctx.db, start_date, end_date, account_id)
    return {"rows": rows}


def _query_balance(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    from services.report_service import account_balance

    start_date = _require_date(params, ctx, "start_date")
    end_date = _require_date(params, ctx, "end_date")
    entity_id = _get_param(params, ctx, "entity_id")

    rows = account_balance(ctx.db, start_date, end_date, entity_id)
    return {"rows": rows}


def _query_income(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    from services.report_service import income_list

    start_date = _require_date(params, ctx, "start_date")
    end_date = _require_date(params, ctx, "end_date")
    entity_id = _get_param(params, ctx, "entity_id")
    page = _get_param(params, ctx, "page", 1)
    page_size = _get_param(params, ctx, "page_size", 50)

    result = income_list(ctx.db, start_date, end_date, entity_id, page, page_size)
    return result if isinstance(result, dict) else {"rows": result}


def _query_expense(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    from services.report_service import expense_list

    start_date = _require_date(params, ctx, "start_date")
    end_date = _require_date(params, ctx, "end_date")
    entity_id = _get_param(params, ctx, "entity_id")
    page = _get_param(params, ctx, "page", 1)
    page_size = _get_param(params, ctx, "page_size", 50)

    result = expense_list(ctx.db, start_date, end_date, entity_id, page, page_size)
    return result if isinstance(result, dict) else {"rows": result}


def _query_base(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    from services.base_data_service import query_base_data

    result = query_base_data(
        ctx.db,
        date_from=_get_param(params, ctx, "date_from"),
        date_to=_get_param(params, ctx, "date_to"),
        entity_id=_get_param(params, ctx, "entity_id"),
        account_id=_get_param(params, ctx, "account_id"),
        direction=_get_param(params, ctx, "direction"),
        keyword=_get_param(params, ctx, "keyword"),
        page=_get_param(params, ctx, "page", 1),
        page_size=_get_param(params, ctx, "page_size", 50),
    )
    return result if isinstance(result, dict) else {"rows": result}


# ── 报表节点 ──────────────────────────────────


def _major_balance(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    from services.report_service import major_balance

    start_date = _require_date(params, ctx, "start_date")
    end_date = _require_date(params, ctx, "end_date")
    entity_id = _get_param(params, ctx, "entity_id")

    rows = major_balance(ctx.db, start_date, end_date, entity_id)
    return {"rows": rows}


def _month_check(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    from services.report_service import month_check

    year = _require_param(params, ctx, "year")
    month = _require_param(params, ctx, "month")
    entity_id = _get_param(params, ctx, "entity_id")

    rows = month_check(ctx.db, int(year), int(month), entity_id)
    return {"rows": rows}


# ── 导出节点 ──────────────────────────────────


def _export_excel(params: dict[str, Any], ctx: WorkflowNodeContext) -> dict[str, Any]:
    from services.export_service import generate_export

    export_type = _require_param(params, ctx, "export_type")
    start_date = _get_param(params, ctx, "start_date")
    end_date = _get_param(params, ctx, "end_date")
    entity_id = _get_param(params, ctx, "entity_id")
    account_id = _get_param(params, ctx, "account_id")
    year = _get_param(params, ctx, "year")
    month = _get_param(params, ctx, "month")

    file_path = generate_export(
        ctx.db,
        export_type=export_type,
        start_date=start_date,
        end_date=end_date,
        entity_id=entity_id,
        account_id=account_id,
        year=int(year) if year is not None else None,
        month=int(month) if month is not None else None,
    )
    return {"file_path": file_path}


# ── 注册表 ────────────────────────────────────

node_registry = WorkflowNodeRegistry()

# 可执行节点
node_registry.register("noop", _noop_node)
node_registry.register("control.pause", _pause_node)
node_registry.register("control.start", _start_node)
node_registry.register("control.end", _end_node)
node_registry.register("data.query_daily", _query_daily)
node_registry.register("data.query_cash_journal", _query_cash_journal)
node_registry.register("data.query_balance", _query_balance)
node_registry.register("data.query_income", _query_income)
node_registry.register("data.query_expense", _query_expense)
node_registry.register("data.query_base", _query_base)
node_registry.register("report.major_balance", _major_balance)
node_registry.register("report.month_check", _month_check)
node_registry.register("export.excel", _export_excel)

# ── DEFERRED NODES（不注册到可执行 registry）──
# data.bank_import   → 依赖 artifact_runtime + 文件上传
# data.manual_excel  → 依赖 artifact_runtime + 文件上传
# report.generate    → 依赖 artifact_runtime.run_rule
# agent.invoke       → V1 禁止
