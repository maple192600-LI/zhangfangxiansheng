"""文件系统工具"""
from agents.tool_registry import register_tool, ToolContext
from agents import workspace


@register_tool(read_only=True)
def fs_list(path: str = "workspace", ctx: ToolContext = None) -> dict:
    """列出工作区目录下的文件和子目录。path 为相对路径，如 'workspace/inbox'。"""
    files = workspace.list_files(ctx.agent_code, path)
    return {"files": files, "count": len(files)}


@register_tool(read_only=True)
def fs_read(path: str, ctx: ToolContext = None) -> dict:
    """读取工作区内的文件内容。path 为相对路径。"""
    content = workspace.read_file(ctx.agent_code, path)
    if content is None:
        return {"ok": False, "error": f"文件不存在或路径越界: {path}"}
    # 截断预览
    preview = content[:2000]
    return {"ok": True, "content": preview, "total_chars": len(content)}


@register_tool(read_only=False)
def fs_write(path: str, content: str, ctx: ToolContext = None) -> dict:
    """写入文件到工作区。path 为相对路径，content 为文件内容。"""
    result = workspace.write_file(ctx.agent_code, path, content)
    if result is None:
        return {"ok": False, "error": "路径越界，无法写入"}
    return {"ok": True, "path": path}


@register_tool(read_only=False)
def fs_edit(path: str, old_text: str, new_text: str, ctx: ToolContext = None) -> dict:
    """编辑工作区内文件：将 old_text 替换为 new_text。"""
    content = workspace.read_file(ctx.agent_code, path)
    if content is None:
        return {"ok": False, "error": f"文件不存在: {path}"}
    if old_text not in content:
        return {"ok": False, "error": "未找到要替换的文本"}
    new_content = content.replace(old_text, new_text, 1)
    workspace.write_file(ctx.agent_code, path, new_content)
    return {"ok": True, "path": path}
