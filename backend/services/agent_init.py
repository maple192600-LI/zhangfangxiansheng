"""Agent 工作空间初始化

首次启动时创建 shared/master/parser-assistant/custom 目录 + 17 个 MD 骨架文件。
"""
import os
from config import BASE_DIR

AGENTS_DIR = os.path.join(BASE_DIR, "agents")

# ── 骨架内容 ──

SHARED_FILES = {
    "COMPANY.md": "# 公司信息\n\n此文件由系统自动生成，包含当前板块、法人、账户的概要信息。\n",
    "KNOWLEDGE.md": "# 公共知识库\n\n所有 Agent 共享的知识区域。可在此补充业务常识、行业术语等。\n",
    "DATA_SCHEMA.md": "# 数据模型\n\n此文件由系统自动生成，描述当前数据库表结构概要。\n",
}

AGENT_FILES = {
    "SOUL.md": "# 性格与表达风格\n\n定义此 Agent 的语气、表达习惯和身份基调。\n",
    "AGENT.md": "# 角色定义\n\n描述此 Agent 的职责范围和核心任务。\n",
    "USER.md": "# 用户偏好\n\n记录用户对本 Agent 的特殊要求和偏好。\n",
    "MEMORY.md": "# 记忆区\n\nAgent 的长期记忆存储区域。\n",
    "TOOLS.md": "# 工具权限\n\n定义此 Agent 可使用的工具和数据访问边界。\n",
    "RULES.md": "# 业务规则\n\n此 Agent 必须遵守的业务规则和约束。\n",
    "WORKFLOW.md": "# 标准工作流\n\n此 Agent 的标准工作流程和操作步骤。\n",
}

AGENT_SPECIFIC = {
    "master": {
        "AGENT.md": "# 总管 Agent\n\n负责统筹协调其他 Agent，处理用户直接指令。\n",
        "TOOLS.md": "# 工具权限 — 总管\n\n拥有全局数据读取权限，可调用所有子 Agent。\n",
    },
    "parser-assistant": {
        "AGENT.md": "# 解析助手 Agent\n\n负责银行流水模板识别、字段映射和新模板保存。\n",
        "TOOLS.md": "# 工具权限 — 解析助手\n\n可读取 parser_templates 表、fund_events 表，可写入 parser_templates。\n",
    },
}


def init_agent_workspaces():
    """首次启动时调用，创建目录和骨架文件"""
    dirs = ["shared", "master", "parser-assistant", "custom"]
    for d in dirs:
        dir_path = os.path.join(AGENTS_DIR, d)
        os.makedirs(dir_path, exist_ok=True)

    # shared/ 的 3 个文件
    for fname, content in SHARED_FILES.items():
        _write_if_missing(os.path.join(AGENTS_DIR, "shared", fname), content)

    # master/ 和 parser-assistant/ 的 7 个文件
    for agent_name in ["master", "parser-assistant"]:
        for fname, default_content in AGENT_FILES.items():
            # 如果有 agent 专属内容则用专属的
            content = AGENT_SPECIFIC.get(agent_name, {}).get(fname, default_content)
            _write_if_missing(os.path.join(AGENTS_DIR, agent_name, fname), content)

    return True


def _write_if_missing(filepath: str, content: str):
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
