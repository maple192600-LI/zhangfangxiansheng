# docs/ · 项目文档主入口

> **任何 AI 或人类开发者开工前，必须按本文件指定的顺序阅读。**
> 文档冲突时以 `00_governance/00_project_constitution.md` 为最高优先级。
> 
> 版本：v5.0 · 2026-05-10

---

## 必读顺序

### 第一优先级：当前代码实况

| 序号 | 文件 | 内容 |
|------|------|------|
| 1 | [`00_governance/00_project_constitution.md`](00_governance/00_project_constitution.md) | **核心契约** — 数据库schema冻结、字段枚举、Agent技能体系、不可变规则 |
| 2 | [`00_governance/04_user_constraints.md`](00_governance/04_user_constraints.md) | 用户画像 — 谁用、习惯、技术能力 |
| 3 | [`00_governance/05_tech_constraints.md`](00_governance/05_tech_constraints.md) | 技术栈锁定 — Python/FastAPI/Vue/SQLite |

### 第二步：理解项目（5分钟）

| 序号 | 文件 | 内容 |
|------|------|------|
| 4 | [`00_governance/03_scope_and_order.md`](00_governance/03_scope_and_order.md) | 范围边界 + 验收清单 |
| 5 | [`10_product_design/03_funds_workflow.md`](10_product_design/03_funds_workflow.md) | 资金板块主链路 — 从导入到报表的完整流程 |
| 6 | [`10_product_design/02_frontend_information_architecture.md`](10_product_design/02_frontend_information_architecture.md) | 前端信息架构 — 页面结构、导航、职责划分 |

### 第三步：了解范围（10分钟）

| 序号 | 文件 | 内容 |
|------|------|------|
| 6 | [`00_governance/01_v1_scope_and_order.md`](00_governance/01_v1_scope_and_order.md) | V1范围边界 + 验收清单 |
| 7 | [`10_product_design/03_funds_v1_workflow.md`](10_product_design/03_funds_v1_workflow.md) | 资金板块主链路 — 从导入到报表的完整流程 |
| 8 | [`10_product_design/02_frontend_information_architecture.md`](10_product_design/02_frontend_information_architecture.md) | 前端信息架构 — 页面结构、导航、职责划分 |

### 第四步：查契约（按需查阅）

| 文件 | 内容 |
|------|------|
| [`30_contracts/20_database_schema.md`](30_contracts/20_database_schema.md) | 数据库DDL — 当前需修订，以项目地图 24 张业务 ORM 表为准 |
| [`30_contracts/21_field_dictionary.md`](30_contracts/21_field_dictionary.md) | 字段字典 — 字段编码、中文名、类型、验证规则 |
| [`30_contracts/22_manual_field_pool.md`](30_contracts/22_manual_field_pool.md) | 手工字段池 — 核心字段/可选字段/系统字段 |
| [`30_contracts/23_api_contracts.md`](30_contracts/23_api_contracts.md) | API契约 — 当前需修订，42 上限为历史设计 |
| [`30_contracts/24_page_states_and_exceptions.md`](30_contracts/24_page_states_and_exceptions.md) | 页面状态 + 异常码 |
| [`30_contracts/25_primitives_whitelist.md`](30_contracts/25_primitives_whitelist.md) | 基元库白名单 — Agent产物可调用的函数 |

### 第五步：看规则（开发前必读）

| 文件 | 内容 |
|------|------|
| [`00_governance/06_coding_conventions.md`](00_governance/06_coding_conventions.md) | 编码规范 — 命名、分层、响应格式、错误处理 |
| [`00_governance/07_testing_strategy.md`](00_governance/07_testing_strategy.md) | 测试策略 — 分层、覆盖率、fixture、现有测试清单 |
| [`00_governance/08_anti_drift.md`](00_governance/08_anti_drift.md) | 防跑偏六层机制 — 契约冻结、guards、DoD、Kickoff |
| [`00_governance/09_ai_capability.md`](00_governance/09_ai_capability.md) | Agent能力体系 — 架构、工具、记忆、技能、隐私三档 |

### 第六步：查执行细节（开发时按需）

| 文件 | 内容 |
|------|------|
| [`20_execution/10_master_data_execution.md`](20_execution/10_master_data_execution.md) | 主数据中心执行 |
| [`20_execution/11_home_dashboard_execution.md`](20_execution/11_home_dashboard_execution.md) | 首页总控台执行 |
| [`20_execution/12_bank_import_execution.md`](20_execution/12_bank_import_execution.md) | 银行流水导入执行 |
| [`20_execution/13_manual_flow_execution.md`](20_execution/13_manual_flow_execution.md) | 手工流水执行 |
| [`20_execution/14_base_data_and_report_execution.md`](20_execution/14_base_data_and_report_execution.md) | 基础数据与报表执行 |
| [`20_execution/15_export_dashboard_backup_execution.md`](20_execution/15_export_dashboard_backup_execution.md) | 导出/看板/备份执行 |
| [`20_execution/16_agent_system_execution.md`](20_execution/16_agent_system_execution.md) | Agent 系统开发参考 — 架构、模块、工具、技能、记忆、扩展方式 |
| [`20_execution/17_frontend_conventions.md`](20_execution/17_frontend_conventions.md) | 前端开发规范 — 组件约定、API调用、状态管理、视觉风格 |
| [`20_execution/18_deployment_guide.md`](20_execution/18_deployment_guide.md) | 部署与打包 — 开发环境、生产部署、环境变量、问题排查 |

### 手工流水专项（按需）

| 文件 | 内容 |
|------|------|
| [`10_product_design/04_manual_flow_multi_subject.md`](10_product_design/04_manual_flow_multi_subject.md) | 多主体总表机制设计 |
| [`10_product_design/05_manual_field_pool_and_template_scheme.md`](10_product_design/05_manual_field_pool_and_template_scheme.md) | 字段池与模板方案 |
| [`10_product_design/06_manual_template_spec.md`](10_product_design/06_manual_template_spec.md) | 手工模板规范 |

---

## 文件优先级（冲突时）

```
00_project_constitution.md（宪法）
       > 30_contracts/*（契约实现）
       > 20_execution/*（执行文档）
       > 10_product_design/*（产品设计）
```

高者优先。若宪法与其他文档冲突 → 改其他文档，**不改宪法**（除非走 §ChangeFlow）。

若仍无法判定 → **停下报告**，不擅自选择。

---

## 本地开发启动

```bash
# 安装后端依赖
pip install -r backend/requirements.txt

# 安装前端依赖
cd frontend && npm install

# 启动后端（默认端口8000）
python backend/main.py

# 启动前端开发服务器
cd frontend && npm run dev

# 构建前端（后端自动挂载 dist/）
cd frontend && npm run build
```

---

## 项目根目录说明

| 目录/文件 | 用途 |
|-----------|------|
| `backend/` | FastAPI后端（API/Services/DB/Agents） |
| `frontend/` | Vue 3前端 |
| `docs/` | **本目录 — 所有开发文档** |
| `agents/` | Agent运行时数据（用户创建的实例） |
| `samples/` | 银行流水/手工流水样本文件 |
| `templates/` | 前端模板、手工模板 |
| `references/` | 原始输入、截图、样式规范 |
| `tools/guards/` | 契约守卫脚本 |
| `tests/` | pytest测试 |
| `alembic/` | 数据库迁移 |
| `CLAUDE.md` | Claude Code项目指令（自动加载） |

---

## 核心规则速查

```
§C1  · CANONICAL_12 基础数据表（12列冻结）
§C2  · TEMPLATE_18 模板占位符（18个冻结）
§C3  · MASTER_20 账户主数据（20列冻结）
§C4  · Agent 技能体系（预置5个 + 动态创建）
§C5  · 基元库白名单（37函数）
§C6  · 数据库（当前真实业务 ORM 表为 24 张，sqlite_sequence 不计入业务表）
§C7  · API（端点数量以 23_api_contracts.md 为准，旧 42 上限已失效）
§C8  · 脚本编排确定性原则
§C9  · 用户零编程原则
```
