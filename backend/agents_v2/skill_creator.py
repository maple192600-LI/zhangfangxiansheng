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

from config import DATA_DIR


SKILL_CREATOR_TEMPLATE = '''---
name: {name}
description: "{description}"
when_to_use: "{when_to_use}"
allowed-tools:
{allowed_tools}
arguments:
{arguments}
---

# {display_name}

## 工作流程
{workflow}

## 规则
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
) -> str:
    """生成标准 SKILL.md 内容"""
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

    return SKILL_CREATOR_TEMPLATE.format(
        name=name,
        display_name=display_name,
        description=description,
        when_to_use=when_to_use,
        allowed_tools=tools_yaml,
        arguments=args_yaml,
        workflow=workflow,
        rules=rules,
    )


def get_skill_creator_dir() -> str:
    """获取 skill-creator 系统技能目录"""
    return os.path.join(DATA_DIR, "agents", "system", "skills", "skill-creator")


def get_target_skill_dir(agent_code: str, skill_code: str) -> str:
    """获取新技能的目标目录"""
    return os.path.join(DATA_DIR, "agents", agent_code, "skills", skill_code)


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
        allowed_tools=[
            "fs_read", "fs_write", "fs_list",
            "openpyxl_read", "openpyxl_write",
            "ask_user", "skill_run", "skill_test",
        ],
        arguments={
            "intent": {"description": "用户想创建的技能意图描述", "required": True},
            "sample_files": {"description": "样本文件路径列表", "required": False},
        },
        workflow=(
            "1. 捕获意图：理解用户要创建什么技能\n"
            "2. 分析样本：读取用户提供的样本文件，理解数据结构\n"
            "3. 生成 SKILL.md：按标准格式生成技能定义\n"
            "4. 验证：使用 skill_test 测试新技能\n"
            "5. 优化：根据测试结果迭代改进"
        ),
        rules=(
            "- 技能名称使用 kebab-case 格式\n"
            "- description 必须简洁准确\n"
            "- 工作流程必须可由 LLM 自主执行\n"
            "- 规则要包含边界条件和错误处理"
        ),
    )

    with open(os.path.join(creator_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_content)

    return True
