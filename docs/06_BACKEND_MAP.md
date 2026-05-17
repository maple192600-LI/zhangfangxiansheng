# 后端地图

## API 模块 → Service → 表/能力映射

| API 模块 | Service | 核心表/能力 |
|----------|---------|------------|
| `health.py` | — | 健康检查 |
| `auth.py` | `auth_service` | User |
| `home.py` | `home_service` | 概览/待办/快捷方式/系统状态 |
| `master_data.py` | `master_data_service`, `master_data_batch` | Division, Entity, Account, AccountAlias |
| `bank_master.py` | `bank_service` | Bank |
| `bank_import.py` | `bank_import_service` | FundEvent, ImportBatch, ParserArtifact |
| `manual_flow.py` | `manual_flow_service`, `manual_scheme_service` | FundEvent, ManualFieldPool, ManualTemplateScheme |
| `base_data.py` | `base_data_service` | FundEvent（聚合查询） |
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
| `events.py` | `exception_center_service` | FundEvent（异常处理） |
| `reset.py` | `reset_service` | 数据库重置 |
| `workflow.py` | `workflow_service`, `workflow_executor` | Workflow, WorkflowVersion, WorkflowRun, WorkflowRunStep |

## 关键数字

| 维度 | 数量 |
|------|------|
| API 模块（`.py`，含 `__init__.py`） | 23 |
| 业务 API 模块（扣除 `__init__.py`） | 22 |
| Service 模块（`.py`，含 `__init__.py`） | 26 |
| 业务 Service 模块 | 25 |
| ORM 表 | 28 |
| API inventory（effective path） | 166 endpoints, 0 duplicate |

## ORM 表清单（28 张）

Division, Entity, Bank, Account, AccountAlias, ManualFieldPool, ManualTemplateScheme, ImportBatch, FundEvent, ParserArtifact, RuleArtifact, TemplateInferenceJob, DailyReportRun, AIConfig, AICallLog, OperationLog, User, ReportTemplate, Agent, Skill, AgentSession, AgentMessage, AgentRun, AgentMemory, Workflow, WorkflowVersion, WorkflowRun, WorkflowRunStep

## API Inventory Guard

当前行为（Step 2 修正后）：
- 扫描 `backend/api/**/*.py` 提取 FastAPI 路由装饰器
- 解析 effective path = include_prefix + router_prefix + decorator_path
- 检测重复 effective path（同一 method + effective path 出现多次）→ exit 1
- 不使用端点数量上限作为 guard 机制

---
**校准来源：** `backend/main.py`、`backend/api/`、`backend/services/`、`backend/db/tables.py`、`tools/guards/check_api_inventory.py --list`
**最后校准：** 2026-05-17
