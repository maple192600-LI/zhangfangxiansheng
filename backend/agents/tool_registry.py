"""工具注册系统

ToolDef dataclass + register_tool 装饰器
schema 从 Python 函数签名 + docstring 自动推断
TOOLSETS 分组支持 + disabled_toolsets 过滤
"""
import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints


@dataclass
class ToolDef:
    """工具定义"""
    name: str
    description: str
    input_schema: dict
    func: Callable
    read_only: bool = False
    concurrent_safe: bool = False
    toolset: str = ""


# 全局工具注册表
_TOOLS: dict[str, ToolDef] = {}

# 工具分组
TOOLSETS: dict[str, list[str]] = {
    "file": ["fs_list", "fs_read", "fs_write", "fs_edit"],
    "parse": ["file_parse"],
    "shell": ["python_exec"],
    "database": ["db_query_business", "db_insert_fund_event", "db_save_parser_template", "fund_skill_run"],
    "excel": ["openpyxl_read", "openpyxl_write"],
    "skill": ["skill_list", "skill_run", "skill_test", "skill_create"],
    "memory": ["memory_save", "memory_search"],
    "agent": ["ask_user"],
}


def register_tool(read_only: bool = False, concurrent_safe: bool = False, toolset: str = ""):
    """工具注册装饰器"""
    def deco(func: Callable) -> Callable:
        schema = _infer_schema(func)
        _TOOLS[func.__name__] = ToolDef(
            name=func.__name__,
            description=(func.__doc__ or "").strip(),
            input_schema=schema,
            func=func,
            read_only=read_only,
            concurrent_safe=concurrent_safe,
            toolset=toolset,
        )
        return func
    return deco


def get_tool(name: str) -> ToolDef | None:
    return _TOOLS.get(name)


def list_tools() -> list[dict]:
    result = []
    for td in _TOOLS.values():
        result.append({
            "name": td.name,
            "description": td.description,
            "input_schema": td.input_schema,
            "toolset": td.toolset,
        })
    return result


def list_toolsets() -> dict[str, list[str]]:
    return TOOLSETS.copy()


def get_tools_for_llm(agent_permission: dict) -> list[dict]:
    """根据 agent 权限返回可用的工具列表（用于 LLM function calling）

    支持 disabled_toolsets 批量禁用整个工具组。
    """
    allowed = set(agent_permission.get("allowed_tools", []))
    needs_confirm = set(agent_permission.get("needs_user_confirm", []))
    disabled_toolsets = set(agent_permission.get("disabled_toolsets", []))

    # 展开 disabled_toolsets 为具体工具名
    disabled = set()
    for ts in disabled_toolsets:
        disabled.update(TOOLSETS.get(ts, []))

    usable = (allowed | needs_confirm) - disabled
    result = []
    for name in usable:
        td = _TOOLS.get(name)
        if td:
            result.append({
                "type": "function",
                "function": {
                    "name": td.name,
                    "description": td.description,
                    "parameters": td.input_schema,
                },
            })
    return result


async def execute_tool(name: str, args: dict, ctx: "ToolContext") -> dict:
    """执行指定工具"""
    td = _TOOLS.get(name)
    if not td:
        return {"ok": False, "error": f"未知工具: {name}"}
    try:
        result = td.func(ctx=ctx, **args)
        if inspect.isawaitable(result):
            result = await result
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _infer_schema(func: Callable) -> dict:
    """从函数签名推断 JSON Schema"""
    sig = inspect.signature(func)
    hints = {}
    try:
        hints = get_type_hints(func)
    except Exception:
        pass

    properties = {}
    required = []

    for pname, param in sig.parameters.items():
        if pname == "ctx":
            continue
        prop: dict = {}
        hint = hints.get(pname, str)

        if hint == int:
            prop["type"] = "integer"
        elif hint == float:
            prop["type"] = "number"
        elif hint == bool:
            prop["type"] = "boolean"
        elif hint == list:
            prop["type"] = "array"
        elif hint == dict:
            prop["type"] = "object"
        else:
            prop["type"] = "string"

        properties[pname] = prop

        if param.default is inspect.Parameter.empty:
            required.append(pname)

    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


@dataclass
class ToolContext:
    """工具执行上下文"""
    agent_id: int
    agent_code: str
    session_id: int
    db: Any
    user_message_fn: Any = None
