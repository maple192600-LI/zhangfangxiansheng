"""Runtime execution for approved Fund Agent artifacts."""
from __future__ import annotations

from typing import Any, Iterator, Optional

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
from sqlalchemy.orm import Session

from agents.fund import sandbox
from db.tables import ParserArtifact, RuleArtifact


def run_parser(
    db: Session,
    artifact_id: int,
    file_path: str,
    ctx: Optional[dict[str, Any]] = None,
) -> Iterator[dict[str, Any]]:
    """Execute an approved ParserArtifact without LLM/network access."""
    artifact = db.query(ParserArtifact).filter(ParserArtifact.id == artifact_id).first()
    if artifact is None:
        raise ValueError(f"Parser artifact {artifact_id} 不存在")
    if artifact.status != "active":
        raise ValueError("Parser artifact 尚未审批通过")

    runtime_ctx = dict(ctx or {})
    if artifact.account_code and not runtime_ctx.get("account_code"):
        runtime_ctx["account_code"] = artifact.account_code

    wb = load_workbook(file_path, read_only=True, data_only=True)
    try:
        yield from sandbox.execute(artifact.code, wb, runtime_ctx)
    finally:
        wb.close()


def run_rule(db: Session, artifact_id: int, ctx: dict[str, Any]) -> Workbook:
    """Execute an approved declarative RuleArtifact."""
    artifact = db.query(RuleArtifact).filter(RuleArtifact.id == artifact_id).first()
    if artifact is None:
        raise ValueError(f"Rule artifact {artifact_id} 不存在")
    if artifact.status != "active":
        raise ValueError("Rule artifact 尚未审批通过")
    template_file = ctx.get("template_file")
    if not template_file:
        raise ValueError("缺少 template_file")

    from fund.primitives import aggregations, base_queries, template_fill

    wb = template_fill.load_template(template_file)
    filters = _filters_from_ctx(ctx)
    for placeholder, binding in (artifact.placeholder_bindings or {}).items():
        value = _eval_binding(binding, ctx, filters, base_queries, aggregations, template_fill)
        template_fill.fill(wb, placeholder, value, binding.get("format") if isinstance(binding, dict) else None)
    return wb


def _filters_from_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    for key in ("account_code", "entity_code", "start_date", "end_date"):
        if ctx.get(key) is not None:
            filters[key] = ctx[key]
    return filters


def _eval_binding(binding, ctx, filters, base_queries, aggregations, template_fill):
    if not isinstance(binding, dict):
        return binding
    primitive = binding.get("primitive")
    params = binding.get("params") or {}
    account_code = ctx.get("account_code")
    entity_code = ctx.get("entity_code")
    if not entity_code and account_code:
        entity_code = base_queries.account_field(account_code, "entity_code")

    if primitive == "const":
        return template_fill.const(binding.get("value"))
    if primitive == "date_range_start":
        return template_fill.date_range_start(ctx)
    if primitive == "date_range_end":
        return template_fill.date_range_end(ctx)
    if primitive == "account_field":
        return base_queries.account_field(account_code, params.get("field"))
    if primitive == "entity_field":
        return base_queries.entity_field(entity_code, params.get("field"))
    if primitive == "opening_balance":
        return base_queries.opening_balance(account_code, ctx.get("start_date") or ctx.get("period_start"))
    if primitive == "closing_balance":
        return base_queries.closing_balance(account_code, ctx.get("end_date") or ctx.get("period_end"))
    if primitive == "sum_field":
        return aggregations.sum_field(params.get("field"), filters)
    if primitive == "format_amount":
        return template_fill.format_amount(binding.get("value"), params.get("digits", 2))
    raise ValueError(f"未知 Rule primitive: {primitive}")
