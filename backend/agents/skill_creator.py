"""skill-creator — 预制技能创建器

基于 Claude Code skill-creator 工作流：
1. 捕获意图 — 用户想创建什么技能
2. 分析样本 — 读取样本文件，理解数据结构
3. 生成 SKILL.md — 标准格式，含 frontmatter + body
4. 验证 — 通过 LLM 执行测试
5. 优化 — 根据结果迭代改进

预制为系统级技能，用户创建新技能时自动触发。
"""
import os
import re
from typing import Optional

from config import AGENTS_ROOT


SKILL_CREATOR_TEMPLATE = '''---
name: {name}
description: "{description}"
when_to_use: "{when_to_use}"
version: "{version}"
execution_mode: {execution_mode}
allowed-tools:
{allowed_tools}
arguments:
{arguments}
dependencies:
{dependencies}
triggers:
{triggers}
---

# {display_name}

{workflow}

## 关键规则
{rules}
'''


def generate_skill_md(
    name: str,
    display_name: str,
    description: str,
    when_to_use: str,
    allowed_tools: list[str],
    arguments: dict,
    workflow: str,
    rules: str,
    version: str = "1.0.0",
    execution_mode: str = "instruction",
    dependencies: dict = None,
    triggers: list[str] = None,
) -> str:
    """生成标准 SKILL.md 内容（V2 指令式格式）"""
    tools_yaml = "\n".join(f"  - {t}" for t in allowed_tools)

    args_yaml = ""
    for arg_name, arg_info in arguments.items():
        if isinstance(arg_info, dict):
            req = "true" if arg_info.get("required") else "false"
            args_yaml += f"  {arg_name}:\n"
            args_yaml += f'    description: "{arg_info.get("description", "")}"\n'
            args_yaml += f"    required: {req}\n"
        else:
            args_yaml += f"  {arg_name}: {arg_info}\n"

    if not args_yaml:
        args_yaml = "  {}"

    deps = dependencies or {}
    deps_yaml = ""
    if deps.get("pip"):
        deps_yaml += "  pip:\n"
        for pkg in deps["pip"]:
            deps_yaml += f'    - "{pkg}"\n'
    if deps.get("skills"):
        deps_yaml += "  skills:\n"
        for sk in deps["skills"]:
            deps_yaml += f'    - "{sk}"\n'
    if not deps_yaml:
        deps_yaml = "  {}"

    triggers_yaml = ""
    if triggers:
        for t in triggers:
            triggers_yaml += f'  - "{t}"\n'
    if not triggers_yaml:
        triggers_yaml = "  []"

    return SKILL_CREATOR_TEMPLATE.format(
        name=name,
        display_name=display_name,
        description=description,
        when_to_use=when_to_use,
        version=version,
        execution_mode=execution_mode,
        allowed_tools=tools_yaml,
        arguments=args_yaml,
        dependencies=deps_yaml,
        triggers=triggers_yaml,
        workflow=workflow,
        rules=rules,
    )


def get_skill_creator_dir() -> str:
    """获取 skill-creator 系统技能目录"""
    return os.path.join(AGENTS_ROOT, "system", "skills", "skill-creator")


def get_target_skill_dir(agent_code: str, skill_code: str) -> str:
    """获取新技能的目标目录"""
    return os.path.join(AGENTS_ROOT, agent_code, "skills", skill_code)


def save_skill(agent_code: str, skill_code: str, skill_md_content: str) -> str:
    """保存新创建的技能到 Agent 目录"""
    skill_dir = get_target_skill_dir(agent_code, skill_code)
    os.makedirs(skill_dir, exist_ok=True)

    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    with open(skill_md_path, "w", encoding="utf-8") as f:
        f.write(skill_md_content)

    return skill_dir


def ensure_skill_creator_installed() -> bool:
    """确保 skill-creator 系统技能已安装"""
    creator_dir = get_skill_creator_dir()
    if os.path.isfile(os.path.join(creator_dir, "SKILL.md")):
        return True

    os.makedirs(creator_dir, exist_ok=True)

    skill_content = generate_skill_md(
        name="skill-creator",
        display_name="技能创建器",
        description="帮助用户创建新的技能。分析样本文件，生成标准 SKILL.md 格式的技能定义。",
        when_to_use="当用户要求创建新技能、学习新能力、或需要自动化某个重复性任务时",
        version="2.0.0",
        execution_mode="instruction",
        allowed_tools=[
            "fs_read", "fs_write", "fs_list",
            "openpyxl_read", "openpyxl_write",
            "ask_user", "skill_run", "skill_test",
            "skill_step_report",
        ],
        arguments={
            "intent": {"description": "用户想创建的技能意图描述", "required": True},
            "sample_files": {"description": "样本文件路径列表", "required": False},
        },
        triggers=["创建技能", "新建技能", "学习新能力", "自动化"],
        workflow=(
            "## 第一步：理解意图\n\n"
            "与用户确认要创建什么技能，明确：\n"
            "- 技能的目标（解决什么问题）\n"
            "- 触发条件（什么情况下使用）\n"
            "- 需要哪些工具\n"
            "- 输入参数是什么\n\n"
            "如果用户提供的信息不足，使用 ask_user 提问。\n\n"
            "## 第二步：分析样本\n\n"
            "如果用户提供了样本文件，调用 `file_parse(path='<文件路径>')` 或 "
            "`openpyxl_read(path='<文件路径>')` 分析数据结构。\n\n"
            "## 第三步：设计工作流程\n\n"
            "按以下格式设计分步指令：\n"
            "- 每一步必须明确调用哪个工具、参数怎么填\n"
            "- 包含错误处理（工具调用失败时怎么办）\n"
            "- 包含数据校验步骤\n\n"
            "## 第四步：生成 SKILL.md\n\n"
            "使用 `fs_write(path='skills/<skill-name>/SKILL.md', content='<SKILL.md内容>')` 写入文件。\n\n"
            "## 第五步：验证\n\n"
            "调用 `skill_test(skill_code='<skill-name>')` 测试新技能。如果测试失败，分析错误并修复 SKILL.md。"
        ),
        rules=(
            "- 技能名称使用 kebab-case 格式（如 fund_parser_bank）\n"
            "- description 必须简洁准确（一句话说清楚技能做什么）\n"
            "- 工作流程必须使用分步指令格式（## 第一步、## 第二步...）\n"
            "- 每个步骤必须明确指定调用的工具和参数\n"
            "- 包含关键规则（边界条件、错误处理、数据校验）"
        ),
    )

    with open(os.path.join(creator_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_content)

    return True
