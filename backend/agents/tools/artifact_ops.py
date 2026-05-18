"""Agent tool: create parser artifact draft for bank rule center."""
from agents.tool_registry import register_tool, ToolContext


@register_tool(toolset="database")
def artifact_create_parser_draft(
    name: str,
    code: str,
    bank_id: int = None,
    format_key: str = None,
    match_rules: str = "{}",
    ctx: ToolContext = None,
) -> dict:
    """Create a bank parser artifact draft. Only kind=bank is allowed.

    Args:
        name: Parser name (e.g. "工商银行标准对账单_v1")
        code: Python parser code defining parse(wb, ctx) function
        bank_id: Optional bank ID from master data
        format_key: Optional format fingerprint
        match_rules: JSON string of match rules
    """
    import json
    from core.artifact_ast_guard import validate_artifact_code

    _BLOCKED_PATTERNS = [
        "DEFAULT_ACCOUNT_CODE",
        "DEFAULT_ENTITY_CODE",
        "default_account",
        "default_entity",
    ]

    code_upper = code.upper()
    for pat in _BLOCKED_PATTERNS:
        if pat.upper() in code_upper:
            idx = code_upper.index(pat.upper())
            context_snippet = code[max(0, idx - 20):idx + len(pat) + 20]
            return {
                "ok": False,
                "error": f"parser 代码中不允许硬编码默认账户/单位: 发现 '{pat}'",
                "hint": "Parser 只负责读取文件结构，不负责账户归属。移除固定的 account_code / entity_code。",
            }

    try:
        validate_artifact_code(code, artifact_id=0)
    except Exception as e:
        return {"ok": False, "error": f"AST 安全检查失败: {e}"}

    try:
        rules = json.loads(match_rules) if isinstance(match_rules, str) else match_rules
    except json.JSONDecodeError:
        return {"ok": False, "error": "match_rules 不是有效的 JSON"}

    primitives_imports = []
    for line in code.split("\n"):
        stripped = line.strip()
        if stripped.startswith("from fund.primitives") or stripped.startswith("import fund.primitives"):
            primitives_imports.append(stripped)

    return {
        "ok": True,
        "result": {
            "name": name,
            "kind": "bank",
            "bank_id": bank_id,
            "format_key": format_key,
            "match_rules": rules,
            "primitives_imports": primitives_imports,
            "message": "候选规则已通过安全检查。请在规则中心点击「试运行」验证解析结果，确认后保存。",
        },
    }
