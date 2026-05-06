"""文件系统工具"""
from agents.tool_registry import register_tool, ToolContext
from agents import workspace


@register_tool(read_only=True)
def fs_list(path: str = "workspace", ctx: ToolContext = None) -> dict:
    """列出工作区目录下的文件和子目录。

    使用场景：
    - 查看用户上传了哪些文件（inbox 目录）
    - 检查输出文件是否已生成（output 目录）
    - 浏览技能目录结构

    参数：path 可选，相对路径，默认 "workspace"。如 "workspace/inbox" 查看收件箱。
    返回：{"files": [{"name": "文件名", "size": 大小, "type": "file|dir"}], "count": N}
    """
    files = workspace.list_files(ctx.agent_code, path)
    return {"files": files, "count": len(files)}


@register_tool(read_only=True)
def fs_read(path: str, max_chars: int = 10000, ctx: ToolContext = None) -> dict:
    """读取工作区内的文件内容。

    使用场景：
    - 读取配置文件、规则文件
    - 查看 SKILL.md 内容
    - 读取 CSV/TXT 等文本文件（结构化文件建议用 file_parse）

    参数：
    - path: 必需，相对路径，如 "workspace/inbox/流水.xlsx"
    - max_chars: 可选，最大读取字符数，默认 10000

    返回：{"ok": true, "content": "文件内容", "total_chars": 总字符数}
    """
    content = workspace.read_file(ctx.agent_code, path)
    if content is None:
        return {"ok": False, "error": f"文件不存在或路径越界: {path}"}
    if len(content) > max_chars:
        truncated = content[:max_chars] + f"\n[...已截断，原始内容共 {len(content)} 字符，仅展示前 {max_chars} 字符]"
        return {"ok": True, "content": truncated, "total_chars": len(content), "truncated": True}
    return {"ok": True, "content": content, "total_chars": len(content)}


@register_tool(read_only=False)
def fs_write(path: str, content: str, ctx: ToolContext = None) -> dict:
    """写入文件到工作区。path 为相对路径，content 为文件内容。自动创建目录。"""
    result = workspace.write_file(ctx.agent_code, path, content)
    if result is None:
        return {"ok": False, "error": "路径越界，无法写入"}
    return {"ok": True, "path": path}


@register_tool(read_only=False)
def fs_edit(path: str, old_text: str, new_text: str, ctx: ToolContext = None) -> dict:
    """编辑工作区内文件：将 old_text 替换为 new_text。只替换第一次出现的位置。

    使用场景：修改配置文件、更新 SKILL.md、调整规则参数。
    """
    content = workspace.read_file(ctx.agent_code, path)
    if content is None:
        return {"ok": False, "error": f"文件不存在: {path}"}
    if old_text not in content:
        return {"ok": False, "error": "未找到要替换的文本"}
    new_content = content.replace(old_text, new_text, 1)
    workspace.write_file(ctx.agent_code, path, new_content)
    return {"ok": True, "path": path}
