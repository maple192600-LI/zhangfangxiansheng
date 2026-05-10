# 09 · AI 能力配置（v4 · Agent 能力体系）

> 本文件定义账房先生的完整 Agent 能力体系。包含通用 Agent 架构、Fund Agent 专用约束、执行模式、记忆系统、技能生命周期。
>
> 配合 [00_project_constitution.md](00_project_constitution.md)、[08_anti_drift.md](08_anti_drift.md)、[../30_contracts/25_primitives_whitelist.md](../30_contracts/25_primitives_whitelist.md) 使用。

---

## §1 · 为什么 Agent 必须存在

### §1.1 · 用户画像

| 维度 | 描述 |
|------|------|
| 职业 | 出纳、会计、资金主管、代账会计 |
| 技术水平 | 不编程、不写正则、不配 JSON、不会 SQL |
| 工作习惯 | Excel 为主、网银导出、逐行核对 |
| 期望 | 拿来就用，上传就出表，偶尔配置但不写代码 |

### §1.2 · Agent 的定位

Agent 是整个产品的**核心驱动力**，不是辅助工具：

- **技术活全包**：所有"写代码、写规则、写映射"的活由 Agent 完成，用户只上传和确认
- **越用越懂**：通过记忆积累，逐步了解用户的业务模式、账户习惯、报表偏好
- **能力成长**：从初始的 5 个基础 skill，逐步学会处理更多银行格式、更多报表模板
- **未来扩展**：多 Agent 协作（凭证 Agent、审计 Agent、合同审核 Agent）

### §1.3 · 两种执行模式

用户可以根据偏好选择 Agent 的工作方式：

| 模式 | 适用场景 | 工作方式 | 用户确认 |
|------|----------|----------|----------|
| **脚本编排** | 准确性关键任务（导入、汇总、报表） | Agent 生成脚本 → 脚本确定性执行 | 审核脚本 + 确认结果 |
| **直接 AI** | 非关键任务（文档、查询、建议） | Agent 直接处理并返回结果 | 直接查看结果 |

脚本编排模式的核心链路：
```
用户上传 → Agent 分析 → 生成脚本(Parser/Rule artifact)
→ 用户审核 → 确定性执行 → 用户确认结果
```

---

## §2 · Agent 通用架构

### §2.1 · 运行时核心

```
用户消息 → PromptBuilder（组装系统提示词）
         → MemoryManager（注入记忆上下文）
         → SkillRegistry（匹配激活技能）
         → ToolRegistry（注册可用工具）
         → 流式 LLM 调用
         → 工具执行循环（最多 40 轮）
         → 上下文压缩检查
         → 记忆同步
         → SSE 流式返回
```

### §2.2 · 模块组成

| 模块 | 文件 | 职责 |
|------|------|------|
| 运行时 | `runtime.py` | 核心对话循环、工具执行、错误恢复 |
| 工作区 | `workspace.py` | Agent 文件系统隔离 |
| 上下文 | `context.py` | 三段压缩保护（防止上下文溢出） |
| 提示词 | `prompt_builder.py` | 系统提示词组装（身份+记忆+技能+工具） |
| 权限 | `permission.py` | 工具白名单控制 |
| 工具注册 | `tool_registry.py` | 注册 + 调度 Agent 可用工具 |
| 技能注册 | `skill_registry.py` | 技能发现 + 热加载 + 匹配触发 |
| 技能创建 | `skill_creator.py` | LLM 驱动的技能生成器 |
| 技能执行 | `skill_executor.py` | 技能指令格式化 + 注入 |
| 会话存储 | `session_store.py` | 消息历史加载 + 保存 |
| 会话锁 | `session_lock.py` | 防止并发写入同一会话 |
| 记忆存储 | `memory_store.py` | 记忆的 CRUD |
| 记忆提供者 | `memory_provider.py` / `db_memory_provider.py` | 记忆的加载 + 注入 |
| 记忆管理 | `memory_manager.py` | 记忆同步 + 预加载 + 清洗 |
| 上下文整理 | `curator.py` | 技能生命周期检查 |
| AI 适配 | `provider.py` | 多 Provider 流式调用 |
| SSE | `sse_helper.py` | 流式事件格式化 |

### §2.3 · 工具系统

Agent 可调用的工具通过 `tool_registry.py` 注册，用户可在 Agent 设置中控制权限：

| 工具 | 模块 | 能力 |
|------|------|------|
| `db_query` | `tools/db_ops.py` | 数据库查询（只读或受控写入） |
| `db_execute` | `tools/db_ops.py` | 数据库写入（受权限控制） |
| `file_list` | `tools/fs.py` | 列出文件 |
| `file_read` | `tools/fs.py` | 读取文件内容 |
| `file_write` | `tools/fs.py` | 写入文件 |
| `file_parse` | `tools/file_parse.py` | 解析 PDF/DOCX/Excel/CSV |
| `openpyxl_read` | `tools/openpyxl_ops.py` | Excel 读取 |
| `openpyxl_write` | `tools/openpyxl_ops.py` | Excel 写入 |
| `shell_exec` | `tools/shell_ops.py` | 受限 Shell 命令 |
| `memory_save` | `tools/memory.py` | 保存记忆 |
| `memory_search` | `tools/memory.py` | 搜索记忆 |
| `skill_create` | `tools/skill_ops.py` | 创建新技能 |
| `skill_list` | `tools/skill_ops.py` | 列出技能 |
| `ask_user` | `tools/ask_user.py` | 询问用户确认 |

### §2.4 · Agent 实例数据

每个 Agent 实例在 `agents/` 目录下有独立的工作区：

```
agents/{agent_code}/
├── workspace/          ← 工作文件
│   ├── inbox/          ← 输入文件
│   ├── outputs/        ← 输出文件
│   └── tmp/            ← 临时文件
├── sessions/           ← 会话数据
├── memory/             ← 记忆存储
└── skills/             ← 该 Agent 创建的技能
    └── {skill_name}/
        └── SKILL.md    ← 技能定义（frontmatter + body）
```

---

## §3 · 记忆系统

### §3.1 · 记忆层级

| 层级 | 存储 | 生命周期 | 内容 |
|------|------|----------|------|
| 工作记忆 | 会话消息 | 单次会话 | 当前对话上下文 |
| 短期记忆 | `agent_memories` 表 | 跨会话 | 近期交互摘要、待办事项 |
| 长期记忆 | `agent_memories` 表 | 永久 | 用户偏好、业务知识、技能经验 |

### §3.2 · 记忆注入机制

每轮对话开始时：
1. `MemoryManager.prefetch_with_query()` 根据用户消息预加载相关记忆
2. `MemoryManager.build_system_prompt()` 构建记忆提示块
3. 记忆块注入到系统提示词中
4. Agent 响应时通过 `memory_save` 工具主动保存重要信息
5. 对话结束时 `sync_all()` 同步本轮关键信息

### §3.3 · 记忆清洗

- `Scrubber` 清洗 LLM 输出中的 `<memory-context>` 标签，防止记忆泄露到用户界面
- 记忆内容自动压缩，避免上下文膨胀
- 隐私模式下，敏感数据（金额、账号）脱敏后存储

---

## §4 · 技能生命周期

### §4.1 · 技能发现与加载

```
启动时扫描（startup_scan）
  → 扫描 agents/{agent_code}/skills/ 目录
  → 扫描 agents/system/skills/ 目录（全局技能）
  → 读取每个技能的 SKILL.md frontmatter
  → 注册到 SkillRegistry

运行时热加载（hot_reload）
  → 检查技能目录是否有变更
  → 自动重新加载已变更的技能
```

### §4.2 · 技能匹配与触发

```
用户消息 → SkillRegistry.trigger(message)
  → L1 扫描：关键词匹配（when_to_use 字段）
  → 匹配成功 → 注入技能指令到提示词
  → 匹配失败 → 注入 L1 技能摘要（供 Agent 自主决定）
```

### §4.3 · 技能创建

用户可以要求 Agent 创建新技能，流程如下：

```
1. 用户描述需求（"帮我创建一个分析招行流水的技能"）
2. skill_creator.py 捕获意图
3. 分析样本文件，理解数据结构
4. 生成标准 SKILL.md（frontmatter + workflow + rules）
5. LLM 验证技能可用性
6. 保存到 agents/{agent_code}/skills/{skill_name}/
7. 自动注册到 SkillRegistry
```

技能定义格式（SKILL.md）：
```yaml
---
name: skill_name
description: "技能描述"
when_to_use: "触发条件"
allowed-tools:
  - tool_name
arguments:
  param_name:
    description: "参数说明"
    required: true/false
---

# 技能名称

## 工作流程
（技能执行的步骤描述）

## 规则
（技能执行的约束和注意事项）
```

---

## §5 · Fund Agent 专用约束

Fund Agent 是核心财务 Agent，处理所有财务相关任务。它在通用 Agent 架构基础上增加了严格的约束。

### §5.1 · 5 个基础 Skill（§C4 冻结）

| # | Skill | 职责 | 输入 | 输出 |
|---|-------|------|------|------|
| 1 | `parser.bank` | 生成银行流水解析器 | 流水样本 + 账户上下文 | Parser artifact |
| 2 | `parser.manual` | 生成手工流水解析器 | 手工表单字段映射 | Parser artifact |
| 3 | `rule.template_fill` | 生成报表填充规则 | 模板 + 字段字典 | Rule artifact |
| 4 | `rule.maintain` | 维护/迭代现有规则 | 原 Rule + 修改需求 | 新版 Rule artifact |
| 5 | `template.inference` | 自动识别模板占位符 | 空白 Excel 模板 | 占位符绑定 + 置信度 |

> 基础 5 skill 冻结于 §C4。新增 skill 走 §ChangeFlow。
> 用户通过 `skill_creator` 创建的技能不受 §C4 限制。

### §5.2 · 执行模式 · harness_strict

Fund Agent 对准确性关键任务采用 harness_strict 模式：

| 约束 | 说明 |
|------|------|
| 工具白名单 | 只能调 `backend/fund/primitives/` 白名单函数（§C5） |
| 产物模板 | 输出必须符合 Pydantic Schema |
| 步骤固定 | 每个 skill 的执行步骤在代码中写死，AI 只填参数 |
| 沙箱执行 | 生成的 Python 代码必须通过 AST 扫描再入库 |

### §5.3 · Fund Agent 物理位置

```
backend/agents/fund/
├── harness.py        ← harness_strict 调度器
├── schemas.py        ← 输入/输出 Pydantic Schema
├── memory.py         ← 样本库/字段字典/别名库访问层
└── skills/
    ├── parser_bank.py
    ├── parser_manual.py
    ├── rule_template_fill.py
    ├── rule_maintain.py
    └── template_inference.py
```

---

## §6 · 字段字典 + 别名库

### §6.1 · 字段字典

路径：`seed/field_dictionary.json`

```json
{
  "business_date": {
    "cn_name": "日期",
    "type": "DATE",
    "aliases": ["日期", "交易日期", "记账日期", "业务日期", "入账日期", "发生日期"]
  }
}
```

字段字典是 Agent 识别银行流水列头的核心参考。Agent 每次解析后可发现新别名并写回 `account_aliases` 表。

### §6.2 · 别名库

路径：`seed/alias_library.json`（运行时动态增长）

Agent 每次成功识别后，把新发现的别名写回 `account_aliases` 表，由 `master_match.register_alias` 基元完成。这构成了 Agent 的**学习积累**——处理过越多银行，识别能力越强。

---

## §7 · 隐私三档

| 档位 | Agent 可见 | Agent 不可见 |
|------|-----------|-------------|
| `standard`（默认） | 列头 + 样本 5-10 行（金额脱敏到千位） | 完整明细、对方明细、账号全位 |
| `strict` | 仅列头 + 占位符名称 | 任何数据行 |
| `offline` | 不允许调 AI，只匹配已有 artifact | 全封闭 |

配置路径：`ai_configs.privacy_mode`，UI 切换后立即生效。

---

## §8 · 用户可定制能力

### §8.1 · Agent 人格设定

用户可以在 Agent 设置中自定义：
- **名称和角色**：如"小账"、"财务助手"
- **职责描述**：定义 Agent 负责什么、不负责什么
- **工作风格**：简洁/详细、主动确认/直接执行

### §8.2 · 工具权限

用户可以控制 Agent 可使用的工具集合：
- 财务 Agent：开放 db_ops + openpyxl + file_parse
- 通用助手：开放 shell + fs + memory + skill_ops
- 受限模式：仅开放 db_query + file_read

### §8.3 · 技能管理

- 用户可以要求 Agent 创建新技能（自然语言描述）
- 用户可以查看、编辑、删除已有技能
- 系统级技能不可删除（如 parse_bank_boc）

---

## §9 · 硬边界（10 条）

Agent 在任何情况下**禁止**：

1. 写非白名单代码（pandas / numpy / requests / os / pathlib / open）
2. 发送用户原始 Excel 到 LLM（只能发脱敏后的样本）
3. 修改基础数据表列数 / 列名 / 枚举
4. 修改 API 路由
5. 访问数据库以外的外部网络（除 AI Provider 域名）
6. 执行未授权的 shell 命令
7. 绕过 AST 扫描入库 artifact
8. 跨用户共享实际数据行
9. 把用户数据写入 LLM provider 训练集
10. 在 Runtime 执行阶段调用 LLM（§C8）

---

## §10 · 未来演进方向

以下能力当前不交付，但架构设计必须预留扩展空间：

| 方向 | 说明 |
|------|------|
| 多 Agent 协作 | 凭证 Agent、审计 Agent、合同审核 Agent 各自独立运行 |
| Agent 间通信 | Agent 产出可作为另一个 Agent 的输入 |
| 技能市场 | 用户可导出/导入技能，跨 Agent 共享 |
| 角色模板 | 预置多种 Agent 角色（出纳助手、会计助手、审计助手） |
| 知识沉淀 | Agent 从每次交互中提炼业务知识，形成可复用的知识库 |

---

**版本**
- v4.0 · 2026-05-02 · 全面重写：从"5 固定 skill 的 Fund Agent"扩展为完整 Agent 能力体系
- v3.0 · 2026-04-23 · AI-First artifact 方案
