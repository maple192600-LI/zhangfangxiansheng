"""SSE 事件序列化工具"""
import json
from typing import Any


def sse_event(event: str, data: Any) -> str:
    """格式化单个 SSE 事件"""
    payload = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    return f"event: {event}\ndata: {payload}\n\n"


def sse_text(text: str) -> str:
    """流式文本事件"""
    return sse_event("text", {"text": text})


def sse_tool_start(name: str, args: dict) -> str:
    """工具开始执行事件"""
    return sse_event("tool_start", {"name": name, "args": args})


def sse_tool_end(name: str, result: Any) -> str:
    """工具执行完成事件"""
    return sse_event("tool_end", {"name": name, "result": result})


def sse_done(stop_reason: str = "end_turn") -> str:
    """本轮对话结束事件"""
    return sse_event("done", {"stop_reason": stop_reason})


def sse_error(message: str) -> str:
    """错误事件"""
    return sse_event("error", {"message": message})


def sse_confirm_request(name: str, args: dict, message: str, tool_call_id: str = "") -> str:
    """工具确认请求事件 — 等待用户确认后继续执行"""
    payload = {
        "name": name,
        "args": args,
        "message": message,
    }
    if tool_call_id:
        payload["tool_call_id"] = tool_call_id
    return sse_event("confirm_request", payload)


def sse_ask_user(question: str, tool_call_id: str = "") -> str:
    """Agent 向用户提问事件 — 暂停执行等待用户回复"""
    payload = {"question": question}
    if tool_call_id:
        payload["tool_call_id"] = tool_call_id
    return sse_event("ask_user", payload)
