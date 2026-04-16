"""统一响应包装器"""
from typing import Any, Optional


def success(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


def error(code: int = 9001, message: str = "系统内部错误", data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data}


# 错误码常量
class ErrorCode:
    SUCCESS = 0
    PARAM_MISSING = 1001
    PARAM_FORMAT = 1002
    UNIQUE_CONFLICT = 1003
    NOT_FOUND = 2001
    STATE_INVALID = 2002
    FILE_READ_FAIL = 3001
    TEMPLATE_MATCH_FAIL = 3002
    ACCOUNT_MATCH_FAIL = 4001
    BALANCE_MISMATCH = 4002
    DUPLICATE_INTERCEPT = 4003
    AI_CONNECT_FAIL = 5001
    AI_TIMEOUT = 5002
    INTERNAL = 9001
