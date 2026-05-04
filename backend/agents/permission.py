"""权限网关

控制 agent 可以调用哪些工具，哪些需要用户确认
支持 toolset 分组粒度过滤
"""
import json


DEFAULT_PERMISSION = {
    "allowed_tools": [
        "fs_list", "fs_read",
        "file_parse",
        "memory_save", "memory_search",
        "skill_list", "skill_run",
        "ask_user",
        "openpyxl_read",
        "db_query_business",
    ],
    "needs_user_confirm": [
        "fs_write", "fs_edit",
        "python_exec",
        "skill_create", "skill_test",
        "db_insert_fund_event",
        "db_save_parser_template",
    ],
    "disabled_toolsets": [],
    "allowed_paths": [
        "workspace",
        "skills",
    ],
    "allowed_shell": [],
}

_CONFIRM_MESSAGES = {
    "fs_write": "确认允许写入文件？",
    "fs_edit": "确认允许编辑文件？",
    "python_exec": "确认允许执行 Python 代码？",
    "skill_create": "确认允许创建新技能？",
    "skill_test": "确认允许测试技能？",
    "db_insert_fund_event": "确认允许插入资金流水记录？",
    "db_save_parser_template": "确认允许保存解析模板？",
}


def get_permission(permission_json_str: str) -> dict:
    """解析 agent 的权限配置"""
    if not permission_json_str or permission_json_str == "{}":
        return DEFAULT_PERMISSION.copy()
    try:
        user_perm = json.loads(permission_json_str)
        merged = DEFAULT_PERMISSION.copy()
        merged.update(user_perm)
        return merged
    except (json.JSONDecodeError, TypeError):
        return DEFAULT_PERMISSION.copy()


def is_tool_allowed(permission: dict, tool_name: str) -> bool:
    """检查工具是否在允许列表中"""
    allowed = set(permission.get("allowed_tools", []))
    needs_confirm = set(permission.get("needs_user_confirm", []))
    return tool_name in (allowed | needs_confirm)


def needs_confirm(permission: dict, tool_name: str) -> bool:
    """检查工具是否需要用户确认"""
    return tool_name in permission.get("needs_user_confirm", [])


def get_confirm_message(tool_name: str, args: dict | None = None) -> str:
    """生成人类可读的确认提示"""
    msg = _CONFIRM_MESSAGES.get(tool_name, f"确认允许执行工具 '{tool_name}'？")
    if args:
        if tool_name in ("fs_write", "fs_edit") and args.get("path"):
            msg = f"确认允许{'写入' if tool_name == 'fs_write' else '编辑'}文件 `{args['path']}`？"
        elif tool_name == "python_exec" and args.get("code"):
            code_preview = args["code"][:100]
            msg = f"确认允许执行以下代码？\n```\n{code_preview}\n```"
    return msg


def is_toolset_enabled(permission: dict, toolset_name: str) -> bool:
    """检查工具组是否启用"""
    disabled = set(permission.get("disabled_toolsets", []))
    return toolset_name not in disabled
