"""记忆工具"""
from agents.tool_registry import register_tool, ToolContext
from agents import memory_store


@register_tool(read_only=True)
def memory_save(key: str, content: str, ctx: ToolContext = None) -> dict:
    """保存一条记忆，供后续对话检索使用。

    使用场景：
    - 用户告知了重要的业务规则（如"我们公司用自然月作为会计期间"）
    - 识别出了银行流水的格式特征（如"中国银行流水的表头在第3行"）
    - 记录账户和解析规则的对应关系（如"ZH0008 使用中国银行流水规则"）
    - 记录用户的偏好或常用操作流程

    参数说明：
    - key: 必需，记忆标题，简洁标识这条记忆的内容。格式建议："类别_具体项"，如"银行流水_中国银行"、"规则_报表A"、"偏好_日期格式"
    - content: 必需，记忆内容，详细描述要记住的信息

    注意：不要保存临时性对话内容或系统已有的常识。只保存真正需要跨会话记住的业务信息。
    """
    result = memory_store.save_memory(
        ctx.db, ctx.agent_id, key, content, source="agent"
    )
    return {"ok": True, "key": key}


@register_tool(read_only=True)
def memory_search(query: str, ctx: ToolContext = None) -> dict:
    """搜索历史记忆，查找与关键词相关的已保存信息。

    使用场景：
    - 用户提到某个银行/账户，搜索是否有已保存的解析规则
    - 需要确认用户的某个偏好设置
    - 查找之前处理过类似文件的经验

    参数说明：
    - query: 必需，搜索关键词，建议使用具体的业务术语而非模糊描述。
      好的示例："中国银行流水规则"、"ZH0008"、"日期格式偏好"
      差的示例："那个东西"、"之前说的"

    返回格式：{"results": [{"key": "...", "content": "...", ...}], "count": N}
    """
    results = memory_store.search_memory(ctx.db, ctx.agent_id, query)
    return {"results": results, "count": len(results)}
