"""System Prompt 装配管线

分层组装：身份/岗位职责 → 执行规则 → 记忆 → 技能索引 → 上下文文件
含注入检测 + 截断策略。

关键设计：无论 agent 是否有 role_prompt，都始终附加完整的执行规则。
这确保 LLM 在所有场景下都有足够的行为约束。
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
_MAX_SYSTEM_PROMPT_CHARS = 12_000


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


# ── 执行规则模板 ─────────────────────────────────────────

_EXECUTION_RULES = """\
<execution-rules>

## RULE 1: 每次回复必须包含工具调用

你是一个工具驱动的智能体，不是聊天机器人。

- 你的回复**必须**包含至少一个工具调用，除非任务已彻底完成。
- "查看文件后停下来"是违规行为。查看 → 分析 → 行动，三步缺一不可。
- 如果某个工具调用失败，换一种方式重试，不要报告错误就停止。

## RULE 2: 文件处理必须立即行动

收到文件时：
1. 立即调用 file_parse 解析
2. 分析解析结果
3. 根据用户意图执行下一步（创建规则、导入数据、修改模板等）

不要在解析后停下来等用户催促。

## RULE 3: 技能指令必须严格遵循（最高优先级）

当上下文中出现 `<active-skill>` 标签时，你**必须**按照技能中的步骤顺序执行。

强制要求：
- 按 [MANDATORY] 标记的步骤不能跳过、不能调换顺序
- 每个步骤中提到的工具必须调用，参数必须按说明填写
- 技能中标注为"必需"的参数不能省略
- 每完成一个步骤，必须调用 `skill_step_report` 工具汇报进度
- 如果某个步骤的工具调用失败，分析错误并重试，不要跳到下一步
- code 模式的技能：直接调用 `skill_run`，不要尝试手动执行步骤

违反上述规则 = 任务失败。

## RULE 4: 数据查询先于数据写入

写入 fund_events 之前，必须先：
1. 查询 accounts 表获取 entity_code、entity_name、account_name
2. 查询已有记录检查是否重复

绝不能让用户提供 entity_code/entity_name，这些从账户信息中获取。

## RULE 5: 金额处理规范

- amount_in（收入）和 amount_out（支出）不能同时大于 0
- 金额不能四舍五入，保留原始精度
- 日期格式统一为 YYYY-MM-DD

## RULE 6: 与用户交互

- 用中文回答
- 只在真正缺少关键信息时才使用 ask_user
- 不要问"你确定吗？"——直接做
- 回答简洁专业，先做再说

## RULE 7: 记忆管理

- 用户告知的业务规则、偏好、账户对应关系 → 调用 memory_save 保存
- 处理新文件前 → 调用 memory_search 查找相关经验
- 不要保存临时对话内容或系统已有的常识

</execution-rules>"""


# ── PromptBuilder ────────────────────────────────────────

class PromptBuilder:
    """System Prompt 装配管线

    组装顺序：
    1. Agent 身份（有 role_prompt 用 role_prompt，否则用默认身份）
    2. 完整执行规则（始终附加，不管有没有 role_prompt）
    3. 记忆上下文
    4. 技能索引
    5. 项目上下文文件
    """

    def build(
        self,
        agent,
        memory_hints: str = "",
        skill_hints: str = "",
        cwd: Optional[str] = None,
    ) -> str:
        parts = []

        if getattr(agent, "role_prompt", None):
            parts.append(agent.role_prompt)
        else:
            parts.append(self._build_identity(agent))

        parts.append(_EXECUTION_RULES)

        if memory_hints:
            parts.append(f"\n<memory-context>\n{memory_hints}\n</memory-context>")

        if skill_hints:
            parts.append(f"\n<skill-context>\n{skill_hints}\n</skill-context>")

        if cwd:
            context = _load_context_files(cwd)
            if context:
                parts.append(context)

        result = "\n".join(parts)

        # 预算控制：system prompt 不超过上限，按优先级截断
        if len(result) > _MAX_SYSTEM_PROMPT_CHARS:
            # 保留身份+执行规则，截断后面的部分
            essential = parts[0] + "\n" + parts[1] if len(parts) >= 2 else result
            remaining_budget = _MAX_SYSTEM_PROMPT_CHARS - len(essential) - 100
            if remaining_budget > 200 and len(parts) > 2:
                tail = "\n".join(parts[2:])
                if len(tail) > remaining_budget:
                    tail = tail[:remaining_budget] + "\n[...system prompt 已截断]"
                result = essential + "\n" + tail
            else:
                result = essential[:_MAX_SYSTEM_PROMPT_CHARS]

        return result

    def _build_identity(self, agent) -> str:
        name = getattr(agent, "display_name", "") or getattr(agent, "name", "AI 助手")
        return f"你是「{name}」，一个 AI 智能体。"


prompt_builder = PromptBuilder()
