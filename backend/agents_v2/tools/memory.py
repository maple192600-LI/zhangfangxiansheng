"""记忆工具"""
from agents_v2.tool_registry import register_tool, ToolContext
from agents_v2 import memory_store


@register_tool(read_only=True)
def memory_save(key: str, content: str, ctx: ToolContext = None) -> dict:
    """保存一条记忆。key 为记忆标题，content 为记忆内容。"""
    result = memory_store.save_memory(
        ctx.db, ctx.agent_id, key, content, source="agent"
    )
    return {"ok": True, "key": key}


@register_tool(read_only=True)
def memory_search(query: str, ctx: ToolContext = None) -> dict:
    """搜索记忆。query 为搜索关键词。"""
    results = memory_store.search_memory(ctx.db, ctx.agent_id, query)
    return {"results": results, "count": len(results)}
