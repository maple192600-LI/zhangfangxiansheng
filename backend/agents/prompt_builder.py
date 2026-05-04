"""System Prompt 装配管线

分层组装：身份 → 岗位职责 → 行为准则 → 记忆 → 技能索引 → 上下文文件
含注入检测 + 截断策略。
"""
import re
from pathlib import Path
from typing import Optional



# ── 注入检测 ─────────────────────────────────────────────

_THREAT_PATTERNS = [
    (r'忽略\s*(所有|之前|上面).*指令', "prompt_injection"),
    (r'不要.*告诉.*用户', "deception_hide"),
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET)', "exfil_curl"),
    (r'\bsystem\s*:\s*', "role_injection"),
]

_MAX_CHARS = 20_000


def _scan(content: str, filename: str) -> str:
    for char in ('​', '‌', '﻿'):
        if char in content:
            return f"[BLOCKED: {filename} 包含不可见字符]"
    for pattern, pid in _THREAT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return f"[BLOCKED: {filename} 包含注入模式 '{pid}']"
    return content


def _truncate(content: str, filename: str) -> str:
    if len(content) <= _MAX_CHARS:
        return content
    head = content[:int(_MAX_CHARS * 0.7)]
    tail = content[-int(_MAX_CHARS * 0.3):]
    return head + f"\n[...{filename} 已截断...]\n" + tail


# ── 上下文文件加载 ───────────────────────────────────────

def _load_context_file(base: Path, name: str) -> str:
    path = base / name
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8")
    scanned = _scan(content, name)
    return _truncate(scanned, name)


def _load_context_files(cwd: Optional[str]) -> str:
    if not cwd:
        return ""
    cwd_path = Path(cwd).resolve()
    return _load_context_file(cwd_path, "AGENTS.md") or _load_context_file(cwd_path, "CLAUDE.md") or ""


# ── PromptBuilder ────────────────────────────────────────

class PromptBuilder:
    """System Prompt 装配管线

    组装顺序：
    1. Agent 身份
    2. 岗位职责
    3. 行为准则
    4. 记忆上下文
    5. 技能索引（XML）
    6. 项目上下文文件
    """

    def build(
        self,
        agent,
        memory_hints: str = "",
        skill_hints: str = "",
        skill_xml: str = "",
        cwd: Optional[str] = None,
    ) -> str:
        parts = []

        if getattr(agent, "role_prompt", None):
            # 岗位职责就是 system prompt 的核心，完整保留
            parts.append(agent.role_prompt)
            parts.append(self._build_execution_rules())
        else:
            # 没有岗位职责时，用身份 + 通用规则兜底
            parts.append(self._build_identity(agent))
            parts.append(self._build_guidelines())

        if memory_hints:
            parts.append(f"\n## 相关记忆\n{memory_hints}")

        if skill_xml:
            parts.append(skill_xml)
        elif skill_hints:
            parts.append(f"\n## 可用技能\n{skill_hints}")

        if cwd:
            context = _load_context_files(cwd)
            if context:
                parts.append(context)

        return "\n".join(parts)

    def _build_identity(self, agent) -> str:
        name = getattr(agent, "display_name", "") or getattr(agent, "name", "AI 助手")
        return f"你是「{name}」，一个 AI 智能体。"

    def _build_guidelines(self) -> str:
        """完整行为准则（用于没有 role_prompt 的 agent）"""
        return """## 核心执行原则（最高优先级）

### 1. 任务必须完成，不允许半途而废
- 用户交给你的任务，你必须**一步步执行到底**，直到最终交付结果。
- 每一步都要调用合适的工具，**不能只说不做**。如果你的回复中没有调用任何工具，那说明你可能偷懒了。
- 遇到错误时，分析原因并重试，或换一种方式解决。绝不能简单报告错误就停止。
- 如果一个工具调用失败，尝试其他方式完成任务。

### 2. 工具驱动的执行循环
- 你的每次回复都应该包含工具调用，除非：
  - 任务已完全完成，你正在向用户交付最终结果
  - 你需要向用户 ask_user 获取关键信息才能继续
- 收到文件后，立即用 file_parse 解析，然后根据内容采取行动
- 收到图片后，分析图片内容，提取关键信息，然后继续执行任务
- 不要只是"查看"或"读取"后就停下来——读取是为了行动

### 3. 文件和图片处理
- 用户上传文件/图片时，先用 file_parse 解析，理解内容
- 图片可能包含：表格截图、操作指引、数据样本、配置参考等
- 解析完文件后，根据用户意图**立即执行下一步操作**，不要等用户催促
- 如果文件内容需要调整解析器/模板/规则，直接动手修改

### 4. 代码和数据处理
- 需要修改文件时，用 fs_edit 精准替换，或用 fs_write 写入新文件
- 需要查询数据库时，用 db_query_business 获取数据
- 需要创建/修改模板时，用 db_save_parser_template 保存
- 每次修改后验证结果是否正确

### 5. 与用户交互
- 用中文回答
- 只在真正需要用户输入关键信息时才使用 ask_user
- 不要用 ask_user 来问"你确定吗？"这类问题——直接做
- 回答简洁专业，先做再说

## 记忆管理
- 你可以使用 memory_search 工具搜索历史记忆
- 当用户告诉你重要的业务规则、偏好、账户信息、常联系对象等时，主动使用 memory_save 工具保存
- 需要保存的记忆类型：用户偏好、业务规则、账户对应关系、常用操作流程、错误教训
- 不要保存临时对话内容或已存在于系统中的常识"""

    def _build_execution_rules(self) -> str:
        """精简执行规则（附加在 role_prompt 之后，不重复 role_prompt 已有的内容）"""
        return """

## 执行规则
- 任务必须一步步执行到底，不允许半途而废。遇到错误时重试或换方式解决。
- 除非任务已完成或需要用户输入关键信息，否则每一步都要调用工具——不能只说不做。
- 收到文件/图片后，立即解析并根据内容采取行动，不要停下来等用户催促。
- 用中文回答，简洁专业。"""


def build_skill_xml(matched_skills: list) -> str:
    """构建 <available_skills> XML 块"""
    if not matched_skills:
        return ""
    parts = ["<available_skills>"]
    for skill in matched_skills:
        name = getattr(skill, "name", "") or getattr(skill, "code", "")
        desc = getattr(skill, "description", "")
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts.append(f'  <skill name="{name}">')
        parts.append(f"    <description>{desc}</description>")
        parts.append(f"  </skill>")
    parts.append("</available_skills>")
    return "\n".join(parts)


prompt_builder = PromptBuilder()
