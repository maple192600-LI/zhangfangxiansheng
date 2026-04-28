"""权限网关

控制 agent 可以调用哪些工具，哪些需要用户确认
"""
import json
from typing import Optional


# 默认权限模板
DEFAULT_PERMISSION = {
    "allowed_tools": [
        "fs_list", "fs_read",
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
    ],
    "allowed_paths": [
        "workspace",
        "skills",
    ],
    "allowed_shell": [],
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
