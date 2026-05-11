# 项目地图

> **当前实现地图** — 只描述 main 分支真实状态。
> 本文件不是目标产品蓝图（目标见 [03_target_product_map.md](03_target_product_map.md)）。
> 本文件不是永久不变契约（路线图见 [04_roadmap_and_change_log.md](04_roadmap_and_change_log.md)）。
> 本文件中的"可用、半成品、断链、占位"状态必须随相关 PR 更新。
> 凡是涉及页面、API、Service、数据库表、Artifact、Agent、报表链路的 PR，都必须检查是否需要更新本文件。

## 0. Phase 0 冻结标记（当前仓库状态说明）

> 本节标记旧 FundAgent 体系的当前状态，不改变任何运行时行为。
> 完整审计基线见 [`00_single_agent_cleanup_audit.md`](00_single_agent_cleanup_audit.md)。

- `backend/agents/fund/` 是旧 FundAgent 中间态，待迁移后删除。不得新增对此目录的依赖。
- `backend/api/fund_agent.py` 定义的 `/api/fund/*` 路由未注册到 `main.py`，生产环境不可用（全部 404）。
- 前端中任何 `/api/fund/*` 调用都是死链路，不得作为目标实现依据。
- `backend/fund/`（含 `primitives/` 和 `artifacts/parsers/`）是产物确定性执行基础设施，必须保留，不等于 `backend/agents/fund/`。
- 本文件中旧 FundAgent 相关内容（§7 三层架构、§9 半成品链路等）仅表示当前仓库状态，不代表目标架构。目标架构见 [`03_target_product_map.md`](03_target_product_map.md) 和审计基线。

## 1. 项目总览

**账房先生 (ZhangFang)** — Agent 驱动的本地财务工作台。

**目标愿景**：文件上传 → Agent 解析 → FundEvent → 报表查询/导出

**当前实际可用主线**：手工快速录入 → FundEvent → 报表查询/导出

**关键阻塞**：银行导入和手工 Excel 文件导入都依赖 `artifact_runtime.run_parser`，该函数当前直接抛异常（`core/artifact_runtime.py:31`），导致两条文件导入链路不可完整使用。

## 2. 前端页面地图

### 已实现页面

| 路径 | 页面文件 | 前端 API 模块 | 后端路由前缀 | 状态 |
|------|---------|-------------|------------|------|
| `/` | `HomeDashboard.vue` | `home` + `dashboard` | `/api/home` + `/api/dashboard` | 可用 — 展示概览、指标、趋势 |
| `/home/tasks` | `HomeTasks.vue` | `home` | `/api/home/todos` | 可用 — 展示待办 |
| `/home/quick` | `HomeQuick.vue` | `home` | `/api/home/quick-links` | 可用 — 快捷入口 |
| `/home/system` | `HomeSystem.vue` | `home` | `/api/home/system-status` | 可用 — 系统状态 |
| `/bank-import` | `BankImport.vue` | `bank` | `/api/bank-import` | **断链** — upload 可上传文件，preview/commit 依赖 `artifact_runtime.run_parser` 抛异常 |
| `/manual-flow` | `ManualFlow.vue` | `manual` + `fund` + `master` | `/api/manual-flow` + `/api/fund` | **部分可用** — 快速录入可用；Excel 上传可上传文件，但预览/提交依赖 ParserArtifact runtime，闭环不完整 |
| `/manual-maintenance` | `ManualMaintenance.vue` | `manual` + `master` | `/api/manual-flow` + `/api/master` | 可用 — 方案管理 + 字段池 |
| `/upload-preview` | `UploadPreview.vue` | `manual` | `/api/manual-flow` | **断链** — 调用 `manual-flow/preview`，对 `manual_excel` 类型不完整 |
| `/daily-report` | `DailyReport.vue` | `report` + `master` + `export` | `/api/reports` | 可用 — 日报展示 + 模板列 + 导出 |
| `/base-data` | `BaseDataTable.vue` | `report` + `master` + `export` | `/api/reports` | 可用 — 基础数据表 |
| `/cash-journal` | `CashJournal.vue` | `report` + `master` + `export` | `/api/reports` | 可用 — 现金日记账 |
| `/account-balance` | `AccountBalance.vue` | `report` + `master` + `export` | `/api/reports` | 可用 — 账户余额日报 |
| `/income-list` | `IncomeList.vue` | `report` + `master` + `export` | `/api/reports` | 可用 — 收入明细 |
| `/expense-list` | `ExpenseList.vue` | `report` + `master` + `export` | `/api/reports` | 可用 — 支出明细 |
| `/major-balance` | `MajorBalance.vue` | `TemplateReport.vue` composable | `/api/reports/major-balance` | 可用 — 主要账户余额表 |
| `/month-check` | `MonthCheck.vue` | `TemplateReport.vue` composable | `/api/reports/month-check` | 可用 |
| `/week-report` | `WeekReport.vue` | `TemplateReport.vue` composable | `/api/reports/week-report` | 可用 |
| `/month-report` | `MonthReport.vue` | `TemplateReport.vue` composable | `/api/reports/month-report` | 可用 |
| `/year-report` | `YearReport.vue` | `TemplateReport.vue` composable | `/api/reports/year-report` | 可用 |
| `/rule/bank` | `BankRule.vue` | 无 | 无后端 | **占位** — 纯提示页，提示"规则中心将在后续阶段重建" |
| `/agent/review/:type/:id` | `AgentReview.vue` | `fund` + `bank` + `manual` | `/api/fund` | **半成品** — 可审批 Parser/Rule artifact，但审批后 artifact_runtime 仍无法执行 |
| `/agents/:id` | `AgentDetail.vue` | `stores/agents` → `/api/agent` | `/api/agent` | 可用 — 完整 Agent 聊天/文件/记忆/技能面板 |
| `/data/report-tpl` | `ReportTemplate.vue` | `reportTemplate` + `fund` | `/api/report-templates` + `/api/fund` | 可用 — 模板 CRUD + Excel 上传识别 |
| `/account-manage` | `AccountManage.vue` | `master` | `/api/master` | 可用 — 完整主数据管理（板块/法人/银行/账户/别名） |
| `/ai-config` | `AIConfig.vue` | `ai` | `/api/ai-configs` | 可用 — AI 配置管理 |
| `/exception/receipt` | `ExceptionCenter.vue` | `events` | `/api/events` | 可用 — 异常事件处理 |
| `/system-maintenance` | `SystemMaintenance.vue` | `backup` | `/api/backups` + `/api/reset` | 可用 — 备份/恢复/清理合并为 tab |
| `/backup-restore` | 同 `SystemMaintenance.vue` | 同上 | 同上 | 别名路由，指向同一组件 |
| `/data-cleanup` | 同 `SystemMaintenance.vue` | 同上 | 同上 | 别名路由，指向同一组件 |
| `/operation-log` | `OperationLog.vue` | `log` | `/api/logs` | 可用 |
| `/login` | `Login.vue` | `auth` | `/api/auth` | 可用 |

### 占位路由（共 26 个，全部使用 `Placeholder.vue`）

票据中心（4）：
- `/ocr/upload`, `/ocr/settings`, `/invoice-ledger`, `/contract-ledger`

贷款管理（4）：
- `/loan-ledger`, `/loan-interest`, `/loan-other-ledger`, `/loan-other`

预算管理（1）：
- `/budget-plan`

AI 智能体预留（7）：
- `/agent/social`, `/agent/daily`, `/agent/cost`, `/agent/income`, `/agent/material`, `/agent/tax`, `/agent/custom`

系统设置预留（1）：
- `/data/department`

规则中心预留（4）：
- `/rule/io`, `/rule/origin`, `/rule/voucher`, `/rule/other`

权限管理预留（5）：
- `/perm/admin`, `/perm/cashier`, `/perm/manager`, `/perm/boss`, `/perm/accountant`

## 3. 前端 API 地图

| 前端 API 文件 | 路由前缀 | 后端路由文件 | 对应 Service | 主要数据库表 |
|-------------|---------|------------|------------|-----------|
| `api/auth.js` | `/api/auth` | `api/auth.py` | `auth_service` | `users` |
| `api/master.js` | `/api/divisions` `/api/entities` `/api/banks` `/api/accounts` | `api/master_data.py` + `api/bank_master.py` | `master_data_service` + `bank_service` | `divisions`, `entities`, `banks`, `accounts`, `account_aliases` |
| `api/bank.js` | `/api/bank-import` | `api/bank_import.py` | `bank_import_service` | `import_batches`, `fund_events`, `parser_artifacts` |
| `api/manual.js` | `/api/manual-flow` | `api/manual_flow.py` | `manual_flow_service` + `manual_scheme_service` | `import_batches`, `fund_events`, `manual_field_pool`, `manual_template_schemes` |
| `api/report.js` | `/api/base-data` `/api/reports` | `api/base_data.py` + `api/reports.py` | `base_data_service` + `report_service` | `fund_events` |
| `api/reportTemplate.js` | `/api/report-templates` | `api/report_template.py` | `report_template_service` | `report_templates` |
| `api/fund.js` | `/api/fund` | `api/fund_agent.py` | `agents.fund.harness` + `agents.fund.memory` | `parser_artifacts`, `rule_artifacts`, `template_inference_job` |
| `api/agent.js` | `/api/agent` | `api/agent.py` | `agent_init` + `agents.runtime` | `agents_v2`, `skills_v2`, `agent_sessions`, `agent_messages`, `agent_memories`, `agent_runs` |
| `api/ai.js` | `/api/ai-configs` | `api/ai_config.py` + `api/agent_config.py` | `ai_config_service` | `ai_configs` |
| `api/home.js` | `/api/home` | `api/home.py` | `home_service` | `fund_events`, `accounts` |
| `api/dashboard.js` | `/api/dashboard` | `api/dashboard.py` | `dashboard_service` | `fund_events` |
| `api/events.js` | `/api/events` | `api/events.py` | `exception_center_service` | `fund_events` |
| `api/export.js` | `/api/export` | `api/export.py` | `export_service` + `report_template_service` | `fund_events`, `report_templates` |
| `api/backup.js` | `/api/backups` `/api/reset` | `api/backup.py` + `api/reset.py` | `backup_service` + `reset_service` | 全库 |
| `api/batch.js` | `/api/batches` | `api/batch.py` | (内联) | `import_batches`, `fund_events` |
| `api/log.js` | `/api/logs` | `api/logs.py` | `log_service` | `operation_logs` |

## 4. 后端 API 地图

| API 文件 | 路由前缀 | 路由数 | 前端入口 | 状态 |
|---------|---------|-------|---------|------|
| `api/health.py` | `/api/health` | 1 | 无（健康检查） | 可用 |
| `api/auth.py` | `/api/auth` | 3 | `auth.js` | 可用 |
| `api/master_data.py` | `/api/divisions` `/api/entities` `/api/accounts` | 20 | `master.js` | 可用 |
| `api/bank_master.py` | `/api/banks` | 7 | `master.js` | 可用 |
| `api/bank_import.py` | `/api/bank-import` | 3 | `bank.js` | **断链** — upload 可上传文件，preview/commit 依赖 `artifact_runtime.run_parser` 抛异常 |
| `api/manual_flow.py` | `/api/manual-flow` | 9 | `manual.js` | **部分可用** — quick-entry/save 和 upload 可用；preview/commit 对 manual_excel 类型依赖 `artifact_runtime.run_parser` |
| `api/base_data.py` | `/api/base-data` | 3 | `report.js` | 可用 |
| `api/reports.py` | `/api/reports` | 12 | `report.js` | 10 条查询可用；`/generate` 后端存在但前端无入口且依赖 `artifact_runtime.run_rule` 抛异常；`/download` 无前端入口 |
| `api/report_template.py` | `/api/report-templates` | 10 | `reportTemplate.js` | 可用 |
| `api/home.py` | `/api/home` | 4 | `home.js` | 可用 |
| `api/dashboard.py` | `/api/dashboard` | 3 | `dashboard.js` | 可用 |
| `api/export.py` | `/api/export` | 1 | `export.js` | 可用 |
| `api/events.py` | `/api/events` | 3 | `events.js` | 可用 |
| `api/backup.py` | `/api/backups` | 3 | `backup.js` | 可用 |
| `api/reset.py` | `/api/reset` | 1 | `backup.js` | 可用 |
| `api/batch.py` | `/api/batches` | 2 | `batch.js` | 可用 |
| `api/logs.py` | `/api/logs` | 1 | `log.js` | 可用 |
| `api/ai_config.py` | `/api/ai-configs` | 9 | `ai.js` | 可用 |
| `api/agent_config.py` | `/api/agent-workspaces` | 1 | `ai.js` | 可用 |
| `api/agent.py` | `/api/agent` | 30 | `agent.js` + `stores/agents.js` | 可用 — 完整 Agent 管理和聊天 |
| `api/fund_agent.py` | `/api/fund` | 9 | `fund.js` | **半成品** — skill invoke 创建占位 artifact（confidence=0），无法实际执行解析 |

## 5. Service 地图

| Service 文件 | 核心函数 | 主要操作表 | 依赖 | 状态 |
|------------|---------|----------|------|------|
| `bank_import_service.py` | `upload_file`, `preview`, `commit` | `import_batches`, `fund_events` | **`artifact_runtime.run_parser`** ← 卡点 | upload 可用，preview/commit 不可用 |
| `manual_flow_service.py` | 见下方逐函数拆解 | `import_batches`, `fund_events`, `manual_field_pool`, `manual_template_schemes` | 逐函数不同 | 部分可用 |
| `manual_scheme_service.py` | (方案管理) | `manual_template_schemes`, `manual_field_pool` | 自包含 | 可用 |
| `report_service.py` | `daily_report`, `cash_journal`, `account_balance`, `income_list`, `expense_list`, `major_balance`, `month_check`, `week_report`, `month_report`, `year_report`, `generate_report` | `fund_events` | `generate_report` 依赖 **`artifact_runtime.run_rule`** ← 卡点 | 10 条查询可用，generate_report 不可用 |
| `report_template_service.py` | `list_templates`, `get_template`, `create_template`, `update_template`, `delete_template`, `set_default`, `parse_excel_headers`, `parse_excel_layout`, `excel_to_html` | `report_templates` | 自包含 | 可用 |
| `base_data_service.py` | `query_base_data`, `rebuild_rolling_balance` | `fund_events`, `accounts`, `entities` | 自包含 | 可用 |
| `home_service.py` | `get_overview`, `get_todos`, `get_quick_links`, `get_system_status` | `fund_events`, `accounts`, `import_batches` | 自包含 | 可用 |
| `dashboard_service.py` | `get_metrics`, `get_trends`, `get_composition` | `fund_events` | 自包含 | 可用 |
| `export_service.py` | `generate_export` | `fund_events`, `report_templates` | 依赖 `report_template_service` | 可用 |
| `exception_center_service.py` | `query_pending_events`, `resolve_event`, `void_event` | `fund_events` | 自包含 | 可用 |
| `master_data_service.py` | (板块/法人管理) | `divisions`, `entities` | 自包含 | 可用 |
| `bank_service.py` | (银行管理) | `banks` | 自包含 | 可用 |
| `log_service.py` | `write_log`, `query_logs` | `operation_logs` | 自包含 | 可用 |
| `backup_service.py` | (备份/恢复/清理) | 全库 | 自包含 | 可用 |
| `reset_service.py` | (工厂重置) | 全库 | 自包含 | 可用 |
| `ai_config_service.py` | (AI 配置管理) | `ai_configs` | 自包含 | 可用 |
| `agent_init.py` | (Agent 初始化) | `agents_v2` | 自包含 | 可用 |

### `manual_flow_service.py` 逐函数拆解

| 函数 | 功能 | 依赖 | 状态 |
|------|------|------|------|
| `quick_entry_save` | 快速录入，直接构建 FundEvent 写入 | 自包含 | 可用 |
| `upload_workbook` | 上传 Excel 文件，创建 `source_type="manual_excel"` 的 ImportBatch | 自包含 | 可用（仅上传） |
| `preview_manual` | 预览：对 `manual_quick`/`manual_file` 走已有路径；对 `manual_excel` 不完整 | `artifact_runtime`（间接） | 不完整 — `manual_excel` 路径处理不完整 |
| `commit_manual` | 提交：需要 `parser_artifact_id`，调用 `artifact_runtime.run_parser` | **`artifact_runtime.run_parser`** ← 卡点 | 不可用 |
| `ai_parse_headers` | AI 辅助表头识别 | 依赖有效 Agent 和 AI 配置 | 有实现，但非离线确定性可用能力 — 需要 active agent + 有效 AI config，否则返回错误 |
| `export_template` | 导出手工录入模板 | 自包含 | 可用 |

## 6. 数据库表地图

共 **24 张表**（按 `backend/db/tables.py` 中 `__tablename__` 统计）。`parser_templates` 已在 Alembic 迁移 `005_drop_parser_templates` 中移除，不在当前数据库中。

### 主数据模块（6 张）

| 表名 | ORM 类 | 说明 |
|------|--------|------|
| `divisions` | `Division` | 板块 |
| `entities` | `Entity` | 法人实体 |
| `banks` | `Bank` | 银行 |
| `accounts` | `Account` | 账户 |
| `account_aliases` | `AccountAlias` | 账户别名 |
| `users` | `User` | 用户（单用户认证） |

### 手工流水配置（2 张）

| 表名 | ORM 类 | 说明 |
|------|--------|------|
| `manual_field_pool` | `ManualFieldPool` | 手工字段池 |
| `manual_template_schemes` | `ManualTemplateScheme` | 手工模板方案 |

### 流水事实（2 张）

| 表名 | ORM 类 | 说明 |
|------|--------|------|
| `import_batches` | `ImportBatch` | 导入批次 |
| `fund_events` | `FundEvent` | **核心事实表**，CANONICAL_12 标准行 |

### Agent 产物（3 张）

| 表名 | ORM 类 | 说明 |
|------|--------|------|
| `parser_artifacts` | `ParserArtifact` | 解析器产物（bank/manual），含 Python 代码 |
| `rule_artifacts` | `RuleArtifact` | 报表填充规则产物，含占位符绑定 |
| `template_inference_job` | `TemplateInferenceJob` | 模板推断任务 |

### 报表（2 张）

| 表名 | ORM 类 | 说明 |
|------|--------|------|
| `report_templates` | `ReportTemplate` | 报表模板，含 columns_json / layout_json / source_file_path |
| `daily_report_runs` | `DailyReportRun` | 日报生成记录 |

### AI / 日志（3 张）

| 表名 | ORM 类 | 说明 |
|------|--------|------|
| `ai_configs` | `AIConfig` | AI 模型配置 |
| `ai_call_logs` | `AICallLog` | AI 调用审计日志 |
| `operation_logs` | `OperationLog` | 操作日志 |

### Agent 系统（6 张）

| 表名 | ORM 类 | 说明 |
|------|--------|------|
| `agents_v2` | `Agent` | 智能体定义 |
| `skills_v2` | `Skill` | 技能定义 |
| `agent_sessions` | `AgentSession` | 会话 |
| `agent_messages` | `AgentMessage` | 消息 |
| `agent_runs` | `AgentRun` | 技能运行记录 |
| `agent_memories` | `AgentMemory` | 记忆 |

### 已移除

- `parser_templates` — Alembic `005_drop_parser_templates` 中移除，禁止恢复

## 7. Agent / Skill / Artifact 地图

### 三层架构

```
通用 Agent 系统（backend/agents/）
├── runtime.py          — Agent 运行时（LLM 调度、工具注册）
├── skill_executor.py   — 通用技能执行器
├── skill_loader.py     — 技能加载
├── skill_registry.py   — 技能注册
├── skill_creator.py    — 技能创建管道
├── skill_scanner.py    — 技能扫描器
├── curator.py          — 经验分析 + 自进化
├── memory_store.py     — 记忆存储
├── tool_registry.py    — 工具注册
├── tools/              — 工具集（file_parse, db_ops, shell_ops, skill_ops 等）
└── fund/               — 旧 FundAgent 中间态（待迁移后删除）
    ├── harness.py      — FundAgent 调度器（旧体系，待迁移后删除）
    ├── schemas.py      — Pydantic 输入/输出 Schema（待迁移）
    ├── memory.py       — Artifact CRUD + 别名库（待迁移）
    └── skills/         — 5 个空壳 skill 文件（待删除）
```

> **注意**：`backend/fund/`（含 `primitives/` 和 `artifacts/parsers/`）是产物确定性执行基础设施，必须保留，不等于 `backend/agents/fund/`。

```

### Skills（agents/system/skills/）

| Skill 目录 | SKILL.md 描述 | code_entry | 经验文件 | 状态 |
|-----------|-------------|-----------|---------|------|
| `fund_parser_bank` | 银行流水解析器 | `parser.bank` | 有（0 成功 / 4 次运行） | 占位 — harness 只创建 draft artifact，code 为占位注释 |
| `fund_parser_manual` | 手工流水解析器 | `parser.manual` | 有（0 成功 / 3 次运行） | 占位 — 同上 |
| `fund_rule_template_fill` | 报表填充规则生成 | `rule.template_fill` | 无 | 占位 — harness 创建空 binding |
| `fund_rule_maintain` | 规则维护/迭代 | `rule.maintain` | 无 | 占位 — harness 复制旧版配置 |
| `fund_template_inference` | 模板自动推断 | `template.inference` | 无 | 部分可用 — Stage A（结构解析）实际工作，Stage B（映射）为简单字符串匹配 |

### Skill 目录名 vs code_entry 对照

| 目录名 | SKILL.md name | harness key | 一致性 |
|--------|-------------|-------------|-------|
| `fund_parser_bank` | `fund_parser_bank` | `parser.bank` | 不一致 — 目录用下划线，内部用点分 |
| `fund_parser_manual` | `fund_parser_manual` | `parser.manual` | 同上 |
| `fund_rule_template_fill` | `fund_rule_template_fill` | `rule.template_fill` | 同上 |
| `fund_rule_maintain` | `fund_rule_maintain` | `rule.maintain` | 同上 |
| `fund_template_inference` | `fund_template_inference` | `template.inference` | 同上 |

## 8. 当前可用链路

| 链路 | 入口 → 终点 |
|------|-----------|
| 手工快速录入 | `ManualFlow.vue` → `manual-flow/quick-entry/save` → `fund_events` |
| 手工方案管理 | `ManualMaintenance.vue` → `manual-flow/schemes` |
| 日报/基础数据表/日记账/余额/收支 | 各报表页 → `reports/*` → `report_service` → `fund_events` |
| 综合报表（周/月/年/主要余额/盘点） | 各报表页 → `TemplateReport.vue` → `reports/*` |
| 报表模板 CRUD | `ReportTemplate.vue` → `report-templates/*` |
| 报表导出 | 各报表页 → `export/report` → `export_service` |
| 主数据管理 | `AccountManage.vue` → `master_data/*` |
| AI 配置 | `AIConfig.vue` → `ai-configs/*` |
| Agent 聊天 | `AgentDetail.vue` → SSE `/agent/sessions/*/messages` → `agents.runtime` |
| Agent 技能安装/测试 | `AgentDetail.vue` → `/agent/agents/*/skill-run` |
| 异常中心 | `ExceptionCenter.vue` → `events/*` |
| 备份/恢复/清理 | `SystemMaintenance.vue` → `backups/*` + `reset/*` |
| 操作日志 | `OperationLog.vue` → `logs` |
| 手工 Excel 导出模板 | `manual-flow/export-template` |

## 9. 当前半成品链路

| 链路 | 入口 | 卡点 | 缺失能力 |
|------|------|------|---------|
| **银行导入 preview/commit** | `BankImport.vue` → `bank-import/preview` | `artifact_runtime.run_parser` 直接抛异常 (`core/artifact_runtime.py:31`) | 需要实际的 ParserArtifact 执行器：读取 Excel → 用 artifact.code 解析 → 输出 CANONICAL_12 行 |
| **手工 Excel preview/commit** | `ManualFlow.vue` → `manual-flow/preview` → `commit` | `commit_manual` 需要 `parser_artifact_id`，调用 `artifact_runtime.run_parser` 抛异常 | 同上 |
| **ParserArtifact 创建** | Agent 聊天 + `fund/agent/skills/*/invoke` | `harness._parser_bank` 只创建占位 draft（code 为注释，confidence=0） | 需要让 Agent 生成可执行的解析代码 |
| **RuleArtifact 创建** | Agent 聊天 + `fund/agent/skills/*/invoke` | `harness._rule_template_fill` 只创建空 binding | 需要真实的 AI 映射能力 |
| **模板推断 Stage B** | `ReportTemplate.vue` → `fund/templates/upload` | Stage A 可用，Stage B 为简单字符串匹配 | 完整的 Stage B 需要 AI 语义映射 |
| **BankRule 规则中心** | `/rule/bank` 路由存在 | `BankRule.vue` 纯提示页，无后端 API | 需要 ParserArtifact 列表+编辑 UI + 后端 CRUD |
| **AgentReview 审批后执行** | `/agent/review/:type/:id` | 可审批 Parser/Rule artifact，但审批后 artifact_runtime 仍无法执行 | 与银行导入同一卡点 |
| **报表 generate** | 后端 `/reports/generate` 存在，前端无入口 | `artifact_runtime.run_rule` 直接抛异常 (`core/artifact_runtime.py:38`) | 需要实际的 RuleArtifact 执行器 |

## 10. 当前断链

| 断链 | 位置 | 调用方 |
|------|------|--------|
| `artifact_runtime.run_parser` | `core/artifact_runtime.py:29-32` | `bank_import_service.preview` (L130), `bank_import_service.commit` (L157), `manual_flow_service.commit_manual` |
| `artifact_runtime.run_rule` | `core/artifact_runtime.py:35-39` | `report_service.generate_report` (L511) |
| BankRule 无后端 | `BankRule.vue` → 无 API | 前端页面 |
| `/reports/generate` 前端无入口 | `api/reports.py:236` | 无前端调用 |

## 11. 已废弃链路

| 链路 | 清理状态 |
|------|---------|
| `ParserTemplate` / `parser_templates` 表 | 已完全清理 — PR #2 删除，代码零残留，文档标注为 `[已移除]`，禁止恢复 |
| 旧 `agents` 表 | 从未存在，从一开始就是 `agents_v2` |
| 旧 `skills` 表 | 从未存在，从一开始就是 `skills_v2` |

## 12. 关键命名误导

| 文件 | 问题 | 风险 |
|------|------|------|
| `core/artifact_runtime.py` | 文件名叫 "runtime"，但 `run_parser` 和 `run_rule` 都是直接 `raise ValueError` 的占位函数。不是 deprecated（不曾有过实现），是**从未实现**的占位入口 | 高 — 开发者看到文件名会误以为有运行时实现，实际是两个抛异常的空壳 |

## 13. 后续阶段建议顺序

| 阶段 | 目标 | 交付物 | 依赖 |
|------|------|--------|------|
| Phase 1 | 定义 ParserArtifact runtime 契约 | 契约文档：run_parser 的输入/输出格式、CANONICAL_12 行规范、artifact.code 的执行沙箱约定、错误处理约定 | 无 |
| Phase 2 | 实现最小 `run_parser` | `artifact_runtime.run_parser` 可执行一个硬编码或简单的解析器，产出 CANONICAL_12 行；解锁银行导入 preview/commit 和手工 Excel commit | Phase 1 契约 |
| Phase 3 | 让 Agent 生成可执行 ParserArtifact | 替换 harness 中占位 draft 为真正包含解析代码的 artifact | Phase 2 |
| Phase 4 | 重建 BankRule 规则中心 | ParserArtifact 列表/编辑 UI + 后端 CRUD | Phase 3 |
| Phase 5 | 实现 `run_rule` — RuleArtifact runtime | `artifact_runtime.run_rule` 可执行规则填充模板；解锁报表 generate | Phase 1 契约（复用） |
| Phase 6 | 完善模板推断 Stage B | AI 语义映射替代简单字符串匹配 | Phase 5 |
| Phase 7 | 清理 V2 表名 | `agents_v2` → `agents`，`skills_v2` → `skills`，Alembic 迁移 | 所有功能稳定后 |
