"""Agent tool: write candidate parser code into a training job."""
from agents.tool_registry import register_tool, ToolContext


@register_tool(toolset="database")
def parser_training_update_candidate(
    job_code: str,
    code: str,
    notes: str = None,
    ctx: ToolContext = None,
) -> dict:
    """Write candidate parser code into a parser training job.

    Args:
        job_code: The training job code (e.g. pt_xxxxxxxx)
        code: Python parser code defining parse(wb, ctx) function
        notes: Optional notes about this candidate
    """
    if ctx is None or ctx.db is None:
        return {"ok": False, "error": "无数据库连接"}

    from services.parser_training_service import update_candidate_code
    return update_candidate_code(ctx.db, job_code, code, notes)
