"""向用户提问工具

特殊处理：ask_user 在 runtime 层会暂停执行，等待用户回复。
工具本身只返回问题信息，runtime 负责等待。
"""
from agents.tool_registry import register_tool, ToolContext


@register_tool(read_only=True)
def ask_user(question: str, ctx: ToolContext = None) -> dict:
    """向用户提问，等待用户回复后继续执行。

    使用场景（仅在真正缺少关键信息时使用）：
    - 缺少账户编码，无法确定操作对象
    - 文件格式异常，需要用户确认处理方式
    - 解析结果有多种可能，需要用户选择

    不要用于：
    - "你确定吗？" 类确认（直接做）
    - 可以通过查询数据库获得的信息
    - 用户已经在消息中提供的信息

    参数：
    - question: 必需，向用户提出的问题，简洁明确，一次只问一个问题

    返回：用户的回复内容。agent 收到回复后应立即继续执行任务。
    """
    return {"ok": True, "question": question, "status": "waiting_for_user", "_ask_user": True}
