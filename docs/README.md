# docs/ · 项目文档主入口

> **任何 AI 或人类开发者开工前，先读本文件。**

## 文档体系状态

文档体系已完成重建和清理。15 个 active docs 从当前代码事实校准，是唯一的权威入口。旧文档污染源已清理，当前入口为 active docs + 必要契约文件。

## 治理须知

- 新增永久文档不要直接创建，先读 [`13_DOCUMENT_GOVERNANCE.md`](13_DOCUMENT_GOVERNANCE.md) 了解规则
- 写任务计划先读 [`11_AI_CODING_WORKFLOW.md`](11_AI_CODING_WORKFLOW.md) 了解计划模板和放置位置
- `ai_coordination/` 是协作工作区，不是正式项目文档入口

## 按任务类型查阅

### 项目状态

| 文件 | 内容 |
|------|------|
| [`00_PROJECT_STATE.md`](00_PROJECT_STATE.md) | 项目当前状态总览：可用能力、阻断能力、关键数字 |
| [`12_ROADMAP.md`](12_ROADMAP.md) | 路线图与优先级 |

### 产品与范围

| 文件 | 内容 |
|------|------|
| [`01_PRODUCT_SCOPE.md`](01_PRODUCT_SCOPE.md) | 目标用户、当前必须完成/禁止进入主流程、最小闭环边界 |

### 技术栈

真相源始终是代码文件，不是文档：`frontend/package.json`、`backend/requirements.txt`

| 文件 | 内容 |
|------|------|
| [`02_TECH_STACK.md`](02_TECH_STACK.md) | 完整技术栈（从代码校准） |

### 架构

| 文件 | 内容 |
|------|------|
| [`03_ARCHITECTURE.md`](03_ARCHITECTURE.md) | 系统架构、请求流、当前边界 |
| [`04_DATA_LIFECYCLE.md`](04_DATA_LIFECYCLE.md) | 数据生命周期：FundEvent、导入路径、报表路径 |

### 前端页面

| 文件 | 内容 |
|------|------|
| [`05_FRONTEND_MAP.md`](05_FRONTEND_MAP.md) | 前端路由地图、已实现/placeholder 页面、组件清单 |

### 后端 API / Service / DB

| 文件 | 内容 |
|------|------|
| [`06_BACKEND_MAP.md`](06_BACKEND_MAP.md) | 后端模块映射、API inventory、ORM 表清单 |

### Agent / Artifact / Workflow

| 文件 | 内容 |
|------|------|
| [`07_AGENT_SYSTEM.md`](07_AGENT_SYSTEM.md) | 单通用 Agent 架构、工具、技能、权限 |
| [`08_ARTIFACT_AND_WORKFLOW.md`](08_ARTIFACT_AND_WORKFLOW.md) | Artifact 系统、Workflow 执行器、当前阻断 |

### UI 表格系统

| 文件 | 内容 |
|------|------|
| [`09_UI_TABLE_SYSTEM.md`](09_UI_TABLE_SYSTEM.md) | Tabulator + naive-ui 职责边界、使用页面清单 |

### 测试与验收

| 文件 | 内容 |
|------|------|
| [`10_TESTING_AND_ACCEPTANCE.md`](10_TESTING_AND_ACCEPTANCE.md) | 测试分层、guard 清单、验收标准 |

### 银行导入通用化

| 文件 | 内容 |
|------|------|
| [`14_BANK_IMPORT_GENERALIZATION.md`](14_BANK_IMPORT_GENERALIZATION.md) | 银行导入通用识别与主数据归属匹配：术语、业务链路、四类文件场景、后续阶段 |
| [`15_AGENT_IMPORT_DEVELOPMENT_PLAN.md`](15_AGENT_IMPORT_DEVELOPMENT_PLAN.md) | Agent 定位、解析器/规则分工、银行导入闭环后续开发计划 |

### AI Coding 协作

| 文件 | 内容 |
|------|------|
| [`11_AI_CODING_WORKFLOW.md`](11_AI_CODING_WORKFLOW.md) | 任务包格式、文件传递流程 |
| [`13_DOCUMENT_GOVERNANCE.md`](13_DOCUMENT_GOVERNANCE.md) | 文档治理规则 |

## 当前阻断

| 阻断点 | 位置 | 影响 |
|--------|------|------|
| `run_parser` | `backend/core/artifact_runtime.py` | ParserArtifact 已实现 deterministic runtime |
| `run_rule` | `backend/core/artifact_runtime.py` | RuleArtifact 驱动的规则执行路径阻断 |

手工流水快速录入有独立路径可直接写入 FundEvent，不受上述阻断影响。

## 契约文件

以下文件作为受保护的契约参考。**它们不是完整事实源，修改或引用前必须与代码核对。**

- `docs/00_governance/00_project_constitution.md` — 项目宪法（被 `contracts.lock` SHA256 锁定，修改需走 §ChangeFlow）
- `docs/30_contracts/20_database_schema.md` — 数据库 DDL
- `docs/30_contracts/23_api_contracts.md` — API 契约
- `docs/30_contracts/25_primitives_whitelist.md` — 基元库白名单
