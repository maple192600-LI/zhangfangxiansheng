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
