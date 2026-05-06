"""技能执行器 — 统一 code/instruction/hybrid 三种模式

执行策略：
  - code: 直接 import run.py 执行（确定性）
  - instruction: 注入 SKILL.md body 到 LLM 上下文
  - hybrid: run.py 执行核心逻辑 + SKILL.md 提供上下文指导

指令注入使用 <active-skill> XML 标签 + 步骤编号 + 强制报告机制。
"""
import importlib.util
import json
import logging
import os
import re
import time
from typing import Any, Optional

from agents.skill_registry import SkillMeta
from agents.tool_registry import ToolContext

logger = logging.getLogger(__name__)


def execute_skill_code(
    skill: SkillMeta,
    params: dict,
    ctx: Optional[ToolContext] = None,
) -> dict:
    """code/hybrid 模式执行：直接调用 run.py"""
    run_file = os.path.join(skill.skill_dir, "run.py")
    if not os.path.isfile(run_file):
        return {"ok": False, "error": f"run.py 不存在: {skill.skill_dir}"}

    # 注入 experience 数据
    experience = _load_experience(skill.skill_dir)
    if experience:
        params["_experience"] = experience

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

        # 记录执行经验
        _record_execution(skill.skill_dir, ok=True, duration_ms=duration)

        return {"ok": True, "result": result, "duration_ms": duration}

    except Exception as e:
        duration = int((time.time() - started) * 1000)
        _record_execution(skill.skill_dir, ok=False, duration_ms=duration, error=str(e))
        return {"ok": False, "error": str(e), "duration_ms": duration}


def format_skill_instruction(skill: SkillMeta) -> str:
    """instruction/hybrid 模式：将技能格式化为 LLM 强制执行的指令"""
    body = skill.load_l2()

    # code 模式：生成简短指令引导调用 fund_skill_run 或 skill_run
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

    # 注入 experience 摘要
    experience = _load_experience(skill.skill_dir)
    if experience:
        exp_summary = _format_experience_summary(experience)
        if exp_summary:
            parts.append(f"### 积累经验")
            parts.append(exp_summary)
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

    # 工作流程
    if body:
        enhanced_body = _enhance_steps(body, skill.code)
        max_body = 4000
        if len(enhanced_body) > max_body:
            enhanced_body = enhanced_body[:max_body] + "\n\n[...技能指令已截断，请按已显示的步骤执行]"
        parts.append(enhanced_body)

    parts.append("</active-skill>")

    return "\n".join(parts)


def _format_code_directive(skill: SkillMeta) -> str:
    """code 模式：生成简短指令引导 LLM 调用代码入口"""
    args_example = ""
    if skill.arguments:
        arg_parts = []
        for name, info in skill.arguments.items():
            if isinstance(info, dict):
                arg_parts.append(f'{name}="<{info.get("description", name)}>"')
            else:
                arg_parts.append(f'{name}="<{info}>"')
        args_example = ", ".join(arg_parts)

    # 如果有 code_entry，走 fund_skill_run
    if skill.code_entry:
        tool_name = "fund_skill_run"
        call_args = f'skill_name="{skill.code_entry}", payload={{{args_example}}}'
    else:
        tool_name = "skill_run"
        call_args = f'skill_code="{skill.code}", {args_example}'

    return f"""<active-skill id="{skill.code}" mode="code">
## 技能已激活（代码执行模式）：{skill.name or skill.code}

**目标**: {skill.description}

此技能将通过确定性代码执行，无需手动编排步骤。

### 执行方式

调用 `{tool_name}` 工具：
```
{tool_name}({call_args})
```

根据返回结果向用户汇报。如果失败，分析错误信息并重试。
</active-skill>"""


def _enhance_steps(body: str, skill_code: str) -> str:
    """增强步骤格式：添加编号标记和 step report 指令"""
    step_pattern = re.compile(r'^(##\s*第\s*\w+\s*步|##\s*Step\s*\d+)', re.MULTILINE)
    steps = list(step_pattern.finditer(body))
    total_steps = len(steps)

    if total_steps == 0:
        return body

    enhanced = body
    for i, match in enumerate(reversed(steps), 1):
        step_num = total_steps - i + 1
        original = match.group(0)
        marker = f'{original}  [{step_num}/{total_steps} MANDATORY]'
        enhanced = enhanced.replace(original, marker, 1)

    tracking_directive = (
        f"\n### 步骤跟踪（强制）\n\n"
        f"每完成一个步骤，**必须**调用 `skill_step_report(skill_code=\"{skill_code}\", "
        f"step_number=<步骤编号>, step_name=\"<步骤名称>\", result=\"<完成情况>\")` 汇报进度。\n"
        f"这是验证技能执行完整性的必要步骤，不可跳过。"
    )
    enhanced += tracking_directive

    return enhanced


def _format_experience_summary(experience: dict) -> str:
    """格式化经验摘要用于注入"""
    parts = []
    if experience.get("learned_aliases"):
        aliases = experience["learned_aliases"]
        if aliases:
            items = [f"{k}→{v}" for k, v in list(aliases.items())[:10]]
            parts.append(f"已学别名: {', '.join(items)}")
    if experience.get("corrections"):
        corrections = experience["corrections"]
        if corrections:
            parts.append(f"历史修正({len(corrections)}条):")
            for c in corrections[-3:]:
                parts.append(f"  - {c.get('from', '')} → {c.get('to', '')}")
    stats = experience.get("stats", {})
    if stats.get("total_runs", 0) > 0:
        success_rate = stats.get("successes", 0) / stats["total_runs"] * 100
        parts.append(f"历史执行: {stats['total_runs']}次, 成功率 {success_rate:.0f}%")
    return "\n".join(parts)


# ── Experience 管理 ──────────────────────────────────────

def _load_experience(skill_dir: str) -> dict:
    """加载技能的经验数据"""
    exp_file = os.path.join(skill_dir, "experience.json")
    if not os.path.isfile(exp_file):
        return {}
    try:
        with open(exp_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_experience(skill_dir: str, data: dict) -> None:
    """保存技能经验数据"""
    exp_file = os.path.join(skill_dir, "experience.json")
    try:
        with open(exp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存经验失败: {e}")


def _record_execution(skill_dir: str, ok: bool, duration_ms: int, error: str = "") -> None:
    """记录一次执行结果到 experience"""
    exp = _load_experience(skill_dir)
    if not exp:
        exp = {"stats": {"total_runs": 0, "successes": 0, "total_ms": 0}, "learned_aliases": {}, "corrections": []}

    stats = exp["stats"]
    stats["total_runs"] = stats.get("total_runs", 0) + 1
    if ok:
        stats["successes"] = stats.get("successes", 0) + 1
    stats["total_ms"] = stats.get("total_ms", 0) + duration_ms
    stats["last_run_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    if error:
        errors = exp.setdefault("recent_errors", [])
        errors.append({"error": error[:200], "at": stats["last_run_at"]})
        exp["recent_errors"] = errors[-10:]  # 只保留最近 10 条

    _save_experience(skill_dir, exp)


def record_correction(skill_dir: str, field: str, wrong: str, correct: str) -> None:
    """记录用户修正到 experience"""
    exp = _load_experience(skill_dir)
    if not exp:
        exp = {"stats": {"total_runs": 0, "successes": 0, "total_ms": 0}, "learned_aliases": {}, "corrections": []}

    corrections = exp.setdefault("corrections", [])
    corrections.append({
        "field": field,
        "from": wrong,
        "to": correct,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    exp["corrections"] = corrections[-50:]  # 最多保留 50 条

    _save_experience(skill_dir, exp)


def record_alias(skill_dir: str, original: str, canonical: str) -> None:
    """记录学习到的别名映射"""
    exp = _load_experience(skill_dir)
    if not exp:
        exp = {"stats": {"total_runs": 0, "successes": 0, "total_ms": 0}, "learned_aliases": {}, "corrections": []}

    aliases = exp.setdefault("learned_aliases", {})
    aliases[original] = canonical

    _save_experience(skill_dir, exp)


# ── 旧版兼容 ──────────────────────────────────────────────

def execute_skill_inline(skill: SkillMeta, params: dict, ctx: ToolContext) -> dict:
    """兼容旧版 inline 执行"""
    return execute_skill_code(skill, params, ctx)


def get_skill_run_path(skill_dir: str) -> Optional[str]:
    """检查 skill 目录是否有 run.py"""
    run_file = os.path.join(skill_dir, "run.py")
    return run_file if os.path.isfile(run_file) else None
