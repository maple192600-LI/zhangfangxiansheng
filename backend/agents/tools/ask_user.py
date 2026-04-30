"""向用户提问工具"""
from agents.tool_registry import register_tool, ToolContext


@register_tool(read_only=True)
def ask_user(question: str, ctx: ToolContext = None) -> dict:
    """向用户提问，等待用户回复。用于需要用户确认或补充信息的场景。"""
    # 在 SSE 流中，这个工具直接返回问题文本
    # 前端收到 tool_end 后会展示问题，等待用户回复
    return {"ok": True, "question": question, "status": "waiting_for_user"}
