# 命名词典

> 本文档基于 main 分支 `3a7dd83`（PR #2 合并后）的实际代码审计生成。
> 本文档不修改代码，只记录当前事实、风险边界和后续建议。

## 术语表

### A. 核心业务术语

| 术语 | 准确定义 | 代码位置 | 数据库表 | 允许使用的中文名 | 状态 |
|------|---------|---------|---------|--------------|------|
| **FundEvent** | 资金流水事实表，CANONICAL_12 标准行，整个系统的数据核心 | `db/tables.py:190` | `fund_events` | 资金流水、流水事实 | 合理，不建议改名 |
| **ImportBatch** | 导入批次，追踪每次文件上传的状态 | `db/tables.py:169` | `import_batches` | 导入批次 | 合理 |
| **ReportTemplate** | 报表模板定义，包含列配置、Excel 布局、数据源文件路径。是**报表**的模板，定义报表长什么样 | `db/tables.py:413` | `report_templates` | 报表模板 | 合理 |
| **BankRule** | 前端路由名，当前无实体。原指银行解析规则管理页面，待重建 | 路由 `rule/bank`，页面 `BankRule.vue` | 无 | 银行规则 | 当前无对应后端，名称留用 |

### B. Agent 系统术语

| 术语 | 准确定义 | 代码位置 | 数据库表 | 允许使用的中文名 | 状态 |
|------|---------|---------|---------|--------------|------|
| **Agent** | 通用 AI 智能体，由 LLM 驱动，可执行工具调用、对话、技能 | `backend/agents/runtime.py`，ORM `db/tables.py:439` | `agents_v2` | 智能体 | 概念合理；表名带 `_v2` 后缀需后续清理 |
| **AgentV2** | `Agent` 的历史兼容别名，`AgentV2 = Agent`（`tables.py:464`） | `db/tables.py:464` | 同 `agents_v2` | — | 历史兼容别名，应冻结，Phase 7 删除 |
| **Skill** | 技能定义，包含 SKILL.md 指令集和执行代码 | `backend/agents/skill_registry.py`，ORM `db/tables.py:470` | `skills_v2` | 技能 | 概念合理；表名带 `_v2` 后缀需后续清理 |
| **SkillV2** | `Skill` 的历史兼容别名，`SkillV2 = Skill`（`tables.py:491`） | `db/tables.py:491` | 同 `skills_v2` | — | 历史兼容别名，应冻结，Phase 7 删除 |
| **FundAgent** | 旧中间态：独立的 Python 类（`backend/agents/fund/harness.py:35`）。不继承 Agent，不调用 LLM，不做对话。只做 5 个固定 skill 的确定性执行。**待迁移后删除，不是目标实体**。ParserArtifact / RuleArtifact 的生成和维护应由通用 Agent 完成 | `backend/agents/fund/harness.py:35` | 无专属表 | 财务调度器 | 旧中间态，待迁移后删除 |

### C. Artifact 术语

| 术语 | 准确定义 | 代码位置 | 数据库表 | 允许使用的中文名 | 状态 |
|------|---------|---------|---------|--------------|------|
| **ParserArtifact** | 解析器产物，包含 Python 代码。用于将银行/手工流水文件转为 CANONICAL_12 行。当前运行时（`artifact_runtime.run_parser`）**未实现**，是抛异常的占位函数 | `db/tables.py:232`，`agents/fund/memory.py:13`，`core/artifact_runtime.py:29` | `parser_artifacts` | 解析器产物、解析器 | 术语合理；运行时未实现 |
| **RuleArtifact** | 报表填充规则产物，定义模板占位符到数据的映射。当前运行时（`artifact_runtime.run_rule`）**未实现** | `db/tables.py:264`，`agents/fund/memory.py:63`，`core/artifact_runtime.py:35` | `rule_artifacts` | 填充规则、规则产物 | 术语合理；运行时未实现 |
| **TemplateInferenceJob** | 模板推断任务，三阶段流水线（结构解析→语义映射→用户确认）。Stage A 可用，Stage B 为简单匹配 | `db/tables.py:295`，`agents/fund/memory.py:107` | `template_inference_job` | 模板推断任务 | 合理但略长 |
| **artifact_runtime** | `core/artifact_runtime.py` 中的模块。**文件名高度误导** — 叫 "runtime" 但实际是两个抛 `ValueError` 的占位函数，从未实现 | `core/artifact_runtime.py` | — | — | 高风险命名误导 — 见下方详解 |

### D. Skill 名称映射

| Skill 名称 | SKILL.md 所在目录 | harness 方法 | 实际功能 | 状态 |
|-----------|------------------|-------------|---------|------|
| `parser.bank` | `fund_parser_bank/` | `_parser_bank` | 银行流水解析器创建 | 占位 — 只创建 draft，code 为注释 |
| `parser.manual` | `fund_parser_manual/` | `_parser_manual` | 手工流水解析器创建 | 占位 — 同上 |
| `rule.template_fill` | `fund_rule_template_fill/` | `_rule_template_fill` | 报表填充规则创建 | 占位 — 只创建空 binding |
| `rule.maintain` | `fund_rule_maintain/` | `_rule_maintain` | 规则迭代维护 | 占位 — 只复制旧版配置 |
| `template.inference` | `fund_template_inference/` | `_template_inference` | 模板自动推断 | 部分可用 — Stage A 工作，Stage B 简单匹配 |

## 当前命名问题

| # | 问题 | 严重度 | 位置 | 说明 |
|---|------|--------|------|------|
| N1 | **`artifact_runtime.py` 命名误导** | 高 | `core/artifact_runtime.py` | 文件名叫 "runtime"，但 `run_parser` 和 `run_rule` 都是直接 `raise ValueError` 的占位函数。不是 deprecated（不曾有过实现），是**从未实现**的占位入口。开发者看到文件名会误以为解析器运行时已经存在 |
| N2 | **`agents_v2` / `skills_v2` 表名** | 中 | `db/tables.py:440,471` + 全部 FK 引用 | 从未存在 v1 表，`_v2` 是历史预命名。6 张表的 FK 引用 `agents_v2.id`/`skills_v2.id`，`backup.py` 中有大量原生 SQL 引用。改名需 Alembic 迁移 |
| N3 | **`AgentV2 = Agent` / `SkillV2 = Skill` 兼容别名** | 低 | `db/tables.py:464,491` | 代码中未使用这些别名，纯兼容声明。可在 Phase 7 清理 |
| N4 | **`FundAgent` 命名过于宽泛** | 中 | `backend/agents/fund/harness.py:35` | 叫 "Fund Agent" 但实际是**确定性 Artifact 工厂**，不调用 LLM，不是 Agent 子类。与通用 Agent 系统（`backend/agents/runtime.py`）共用 `agents/` 目录，`api/fund_agent.py` 路由前缀 `/fund`，容易误解为"一种特殊的 Agent" |
| N5 | **Skill 目录名与 code_entry 不一致** | 低 | `agents/system/skills/fund_parser_bank/` vs `parser.bank` | 目录用 `fund_` 前缀+下划线，harness 用点分命名。两套命名体系共存，但修改成本高于收益 |
| N6 | **`BankRule` 无实体支撑** | 低 | `BankRule.vue` | 页面名暗示有"规则"实体，实际只显示提示。待 Phase 4 重建 |
| N7 | **`/reports/generate` 前端无入口** | 中 | `api/reports.py:236` | 后端路由存在但无前端调用。依赖 Phase 5 实现 `run_rule` 后再暴露 |

## 禁止混用

| 绝对不能混用 | 原因 |
|-------------|------|
| `ReportTemplate` ≠ `ParserTemplate` | ParserTemplate 已删除（`005_drop_parser_templates`），禁止恢复。ReportTemplate 是报表模板（定义报表列和布局），不是解析模板的替代品，不是 ParserTemplate 的继任者 |
| `ReportTemplate` ≠ `ParserArtifact` | 完全不同的概念：ReportTemplate 定义报表长什么样，ParserArtifact 定义怎么解析文件 |
| `ParserArtifact` ≠ `RuleArtifact` | 完全不同的用途：ParserArtifact 解析文件→FundEvent，RuleArtifact 填充模板→报表 |
| `FundAgent` ≠ 通用 Agent | FundAgent 是旧中间态（待迁移后删除），通用 Agent 是唯一的 Agent 实体。`backend/agents/fund/` ≠ `backend/fund/`，前者是旧调度器待删除，后者是产物执行基础设施必须保留 |
| `template.inference` ≠ `rule.template_fill` | inference 识别模板结构，template_fill 生成填充规则 |
| `artifact_runtime` ≠ 已实现的运行时 | 当前是未实现的占位，不是 deprecated（不曾有过实现） |

## 后续重命名建议

| 优先级 | 建议 | 原因 | 风险 | 建议时机 |
|--------|------|------|------|---------|
| P1 | 在 `artifact_runtime.py` 中添加明确的模块文档，标明"未实现占位，非 deprecated" | 消除 N1 命名误导 | 无风险 — 只改注释 | 立即可做 |
| P2 | 旧 `FundAgent` 类删除，可复用逻辑迁移到 `backend/services/` | 旧 FundAgent 体系待迁移后删除 | 低 — 迁移后删除旧类 | 清理审计 Phase 3 之后 |
| P3 | `agents_v2` → `agents`，`skills_v2` → `skills` | 消除不必要的版本后缀 | 中 — 需 Alembic 迁移，6 张表 FK 需更新，`backup.py` 中有原生 SQL | Phase 7（功能稳定后） |
| P4 | 删除 `AgentV2 = Agent` / `SkillV2 = Skill` 别名 | 代码中未使用 | 低 | Phase 7 |
| P5 | 统一 Skill 目录名与 code_entry 命名 | 一致性 | 低 — 修改成本高于收益 | 按需 |
