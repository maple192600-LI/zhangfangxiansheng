"""技能执行器

支持两种执行模式：
1. inline: 在当前进程中执行 run.py（兼容旧格式）
2. skill_md: 执行 SKILL.md 定义的技能（指令由 LLM 解读执行）

SKILL.md 技能不直接执行代码，而是将 SKILL.md body 注入到 LLM 上下文中，
由 LLM 根据工作流程描述和 allowed-tools 自主完成。

注入策略：L2 摘要模式 — 只注入 frontmatter + body 前 500 字，减少 token 消耗。
"""
import importlib.util
import json
import os
import time
from typing import Any, Optional

from agents.skill_registry import SkillMeta, load_skill_l2
from agents.tool_registry import ToolContext


def execute_skill_inline(
    skill: SkillMeta,
    params: dict,
    ctx: ToolContext,
) -> dict:
    """inline 模式执行：直接调用 skill 目录下的 run.py

    兼容旧 manifest.yaml + run.py 格式。
    """
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
    """将 SKILL.md 技能格式化为 LLM 可执行的指令（L2 摘要模式）

    只注入 frontmatter 元数据 + body 前 500 字摘要。
    完整 body 通过 skill_run 工具按需加载。
    """
    body_summary = skill.load_l2_summary(max_chars=500)

    parts = [
        f"# 技能：{skill.name}",
        f"\n{skill.description}",
    ]

    if skill.arguments:
        parts.append("\n## 参数")
        for arg_name, arg_info in skill.arguments.items():
            if isinstance(arg_info, dict):
                req = "（必需）" if arg_info.get("required") else "（可选）"
                parts.append(f"- {arg_name}: {arg_info.get('description', '')} {req}")
            else:
                parts.append(f"- {arg_name}: {arg_info}")

    if skill.allowed_tools:
        parts.append(f"\n## 可用工具\n{', '.join(skill.allowed_tools)}")

    if body_summary:
        parts.append(f"\n{body_summary}")

    return "\n".join(parts)


def get_skill_run_path(skill_dir: str) -> Optional[str]:
    """检查 skill 目录是否有 run.py（旧格式兼容）"""
    run_file = os.path.join(skill_dir, "run.py")
    return run_file if os.path.isfile(run_file) else None
