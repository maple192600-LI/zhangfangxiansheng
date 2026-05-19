# 后端地图

## API 模块 → Service → 表/能力映射

| API 模块 | Service | 核心表/能力 |
|----------|---------|------------|
| `health.py` | — | 健康检查 |
| `auth.py` | `auth_service` | User |
| `home.py` | `home_service` | 概览/待办/快捷方式/系统状态 |
| `master_data.py` | `master_data_service`, `master_data_batch` | Division, Entity, Account, AccountAlias |
| `bank_master.py` | `bank_service` | Bank |
| `bank_import.py` | `bank_import_service` | FundEvent, ImportBatch, ParserArtifact, SourceFile（不再公开 commit） |
| `manual_flow.py` | `manual_flow_service`, `manual_scheme_service` | FundEvent, ManualFieldPool, ManualTemplateScheme（不再公开 commit） |
| `base_data.py` | `base_data_service` | FundEvent（聚合查询） |
| `import_preview.py` | `import_preview_service` | ImportBatch, FundEvent, SourceFile, AccountResolutionAttempt, AccountResolutionEvidence（唯一正式提交入口：get/update/validate/commit） |
| `reports.py` | `report_service` | FundEvent, DailyReportRun, ReportTemplate |
| `report_template.py` | `report_template_service` | ReportTemplate |
| `dashboard.py` | `dashboard_service` | FundEvent（趋势/构成） |
| `export.py` | `export_service` | FundEvent（Excel 导出） |
| `backup.py` | `backup_service` | 数据库备份/恢复/清理 |
| `batch.py` | `bank_import_service` | ImportBatch（回滚） |
| `logs.py` | `log_service` | OperationLog |
| `ai_config.py` | `ai_config_service` | AIConfig |
| `agent_config.py` | `agent_init` | Agent workspace 初始化 |
| `agent.py` | — | Agent, AgentSession, AgentMessage, AgentRun, Skill, AgentMemory |
| `artifacts.py` | `artifact_service`, `template_analysis` | ParserArtifact, RuleArtifact, TemplateInferenceJob |
| `reset.py` | `reset_service` | 数据库重置 |
| `workflow.py` | `workflow_service`, `workflow_executor` | Workflow, WorkflowVersion, WorkflowRun, WorkflowRunStep |
| `parser_training.py` | `parser_training_service`, `parser_context_service` | ParserTrainingJob（训练任务、候选试运行、保存规则、Agent 会话、主数据上下文） |

## 关键数字

| 维度 | 数量 |
|------|------|
| API 模块（`.py`，含 `__init__.py`） | 24 |
| 业务 API 模块（扣除 `__init__.py`） | 23 |
| Service 模块（`.py`，含 `__init__.py`） | 28 |
| 业务 Service 模块 | 27 |
| ORM 表 | 32 |
| API inventory（effective path） | 173 endpoints, 0 duplicate |

## ORM 表清单（32 张）

Division, Entity, Bank, Account, AccountAlias, ManualFieldPool, ManualTemplateScheme, ImportBatch, FundEvent, SourceFile, AccountResolutionAttempt, AccountResolutionEvidence, ParserArtifact, RuleArtifact, TemplateInferenceJob, DailyReportRun, AIConfig, AICallLog, OperationLog, User, ReportTemplate, Agent, Skill, AgentSession, AgentMessage, AgentRun, AgentMemory, Workflow, WorkflowVersion, WorkflowRun, WorkflowRunStep, ParserTrainingJob

## FundEvent 状态边界

`FundEvent` 既保存上传结果预览阶段的未完成行，也保存 `state == "正常"` 的正式基础数据行。

- `待确认` / `异常`：预览阶段，可允许 `business_date`、`entity_code`、`account_code` 暂缺，由 `import_preview_service` 在上传结果预览页校验和修正。
- `正常`：正式基础数据，必须具备业务日期、单位编码、账户编码；`base_data_service`、报表、导出只读取该状态。
- 不新增 `import_batch_rows` 暂存表，行级隔离由 `ImportBatch` + `FundEvent.state` 完成。

## API Inventory Guard

当前行为（Step 2 修正后）：
- 扫描 `backend/api/**/*.py` 提取 FastAPI 路由装饰器
- 解析 effective path = include_prefix + router_prefix + decorator_path
- 检测重复 effective path（同一 method + effective path 出现多次）→ exit 1
- 不使用端点数量上限作为 guard 机制

---
**校准来源：** `backend/main.py`、`backend/api/`、`backend/services/`、`backend/db/tables.py`、`tools/guards/check_api_inventory.py --list`
**最后校准：** 2026-05-19（12B 返工：job_code 驱动 + ParserTrainingJob 表）
