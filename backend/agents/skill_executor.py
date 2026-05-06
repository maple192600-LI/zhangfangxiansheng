"""技能执行器

支持两种执行模式：
1. instruction: SKILL.md body 注入 LLM 上下文，由 LLM 按步骤执行
2. code: 调用 fund_skill_run 等确定性代码执行，LLM 仅负责调参
3. hybrid: code 执行 + instruction 补充指导

指令注入策略：使用 <active-skill> XML 标签 + 步骤编号 + 强制报告机制
"""
import importlib.util
import logging
import os
import re
import time
from typing import Any, Optional

from agents.skill_registry import SkillMeta
from agents.tool_registry import ToolContext

logger = logging.getLogger(__name__)


def execute_skill_inline(
    skill: SkillMeta,
    params: dict,
    ctx: ToolContext,
) -> dict:
    """inline 模式执行：直接调用 skill 目录下的 run.py"""
    run_file = os.path.join(skill.skill_dir, "run.py")
    if not os.path.isfile(run_file):
        return {"ok": False, "error": f"run.py 不存在: {skill.skill_dir}"}

    started = time.time()
    try:
        spec = importlib.util.spec_from_file_location("skill_run", run_file)
        mod = importlib.util.module_from_spec(spec)
        mod.SKILL_PARAMS = params
        mod.SKILL_DIR = skill.skill_dir
        spec.loader.exec_module(mod)

        if not hasattr(mod, "run"):
            return {"ok": False, "error": "run.py 缺少 run(params) 函数"}

        result = mod.run(params)
        duration = int((time.time() - started) * 1000)
        return {"ok": True, "result": result, "duration_ms": duration}

    except Exception as e:
        duration = int((time.time() - started) * 1000)
        return {"ok": False, "error": str(e), "duration_ms": duration}


def format_skill_instruction(skill: SkillMeta) -> str:
    """将技能格式化为 LLM 强制执行的指令

    使用 <active-skill> XML 标签包裹，步骤编号标注 [MANDATORY]，
    要求 LLM 在每个步骤完成后调用 skill_step_report。
    """
    body = skill.load_l2()

    # code 模式：生成简短指令，要求调用 code entry 工具
    if skill.execution_mode == "code" and skill.code_entry:
        return _format_code_directive(skill)

    # instruction / hybrid 模式：注入完整指令
    parts = [
        f'<active-skill id="{skill.code}" mode="{skill.execution_mode}">',
        f"## 技能已激活：{skill.name or skill.code}",
        "",
    ]

    if skill.description:
        parts.append(f"**目标**: {skill.description}")
        parts.append("")

    # 参数
    if skill.arguments:
        parts.append("### 输入参数")
        for arg_name, arg_info in skill.arguments.items():
            if isinstance(arg_info, dict):
                req = "（必需）" if arg_info.get("required") else "（可选）"
                parts.append(f"- `{arg_name}`: {arg_info.get('description', '')} {req}")
            else:
                parts.append(f"- `{arg_name}`: {arg_info}")
        parts.append("")

    # 工具白名单
    if skill.allowed_tools:
        parts.append(f"### 可用工具: {', '.join(f'`{t}`' for t in skill.allowed_tools)}")
        parts.append("")

    # 工作流程 — 增强步骤编号和强制标记
    if body:
        enhanced_body = _enhance_steps(body, skill.code)
        max_body = 4000
        if len(enhanced_body) > max_body:
            enhanced_body = enhanced_body[:max_body] + "\n\n[...技能指令已截断，请按已显示的步骤执行]"
        parts.append(enhanced_body)

    parts.append(f"</active-skill>")

    return "\n".join(parts)


def _format_code_directive(skill: SkillMeta) -> str:
    """code 模式：生成简短指令，引导 LLM 调用代码入口"""
    args_example = ""
    if skill.arguments:
        arg_parts = []
        for name, info in skill.arguments.items():
            if isinstance(info, dict):
                arg_parts.append(f'{name}="<{info.get("description", name)}>"')
            else:
                arg_parts.append(f'{name}="<{info}>"')
        args_example = ", ".join(arg_parts)

    return f"""<active-skill id="{skill.code}" mode="code">
## 技能已激活（代码执行模式）：{skill.name or skill.code}

**目标**: {skill.description}

此技能将通过确定性代码执行，无需手动编排步骤。

### 执行方式

调用 `fund_skill_run` 工具：
```
fund_skill_run(skill_name="{skill.code_entry}", payload={{{args_example}}})
```

根据返回结果向用户汇报。如果失败，分析错误信息并重试。
</active-skill>"""


def _enhance_steps(body: str, skill_code: str) -> str:
    """增强步骤格式：添加编号标记和 step report 指令"""
    # 匹配 "## 第X步" 或 "## Step X" 模式，添加编号标记
    step_pattern = re.compile(r'^(##\s*第\s*\w+\s*步|##\s*Step\s*\d+)', re.MULTILINE)

    steps = list(step_pattern.finditer(body))
    total_steps = len(steps)

    if total_steps == 0:
        return body

    # 在每步前面添加强制标记
    enhanced = body
    for i, match in enumerate(reversed(steps), 1):
        step_num = total_steps - i + 1
        original = match.group(0)
        marker = f'{original}  [{step_num}/{total_steps} MANDATORY]'
        enhanced = enhanced.replace(original, marker, 1)

    # 在末尾追加步骤跟踪指令
    tracking_directive = (
        f"\n### 步骤跟踪（强制）\n\n"
        f"每完成一个步骤，**必须**调用 `skill_step_report(skill_code=\"{skill_code}\", "
        f"step_number=<步骤编号>, step_name=\"<步骤名称>\", result=\"<完成情况>\")` 汇报进度。\n"
        f"这是验证技能执行完整性的必要步骤，不可跳过。"
    )
    enhanced += tracking_directive

    return enhanced


def get_skill_run_path(skill_dir: str) -> Optional[str]:
    """检查 skill 目录是否有 run.py"""
    run_file = os.path.join(skill_dir, "run.py")
    return run_file if os.path.isfile(run_file) else None
