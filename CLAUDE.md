# CLAUDE.md

Claude Code 项目专用规则。每次会话开始时自动加载。

## 文档入口

先读 [`docs/README.md`](docs/README.md)。

## 项目定位

**账房先生 (ZhangFang)** — 面向中国财务人员的本地部署 Agent 驱动财务工作台。Agent 编写脚本/规则，脚本确定性处理数据，用户只需上传和确认。

## 技术栈（来自代码，非文档）

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy / Alembic / SQLite |
| 数据处理 | openpyxl / xlrd / Polars |
| 前端 | Vue 3 / Vite / naive-ui / ECharts / Pinia |
| 表格组件 | Tabulator Tables / naive-ui Data Table |
| 工作流画布 | Vue Flow |
| 本地分析引擎 | DuckDB WASM |

## 项目结构

```
backend/
  main.py / config.py / database.py
  api/         ← 路由层（22 模块）
  services/    ← 业务逻辑（25 模块）
  db/          ← ORM 表定义（28 张表）
  core/        ← 安全、响应格式、运行时守卫
  agents/      ← Agent 引擎（运行时 + 工具 + 记忆）
  data/        ← SQLite 数据 + 上传/导出/备份
frontend/
  src/
    views/     ← 42 个页面组件（含 agent/ 子目录）
    components/ / composables/ / stores/ / router/ / api/ / styles/
agents/        ← Agent 运行时数据（用户创建的实例）
samples/       ← 样本文件
templates/     ← 前端模板、手工模板
references/    ← 截图、样式规范
tools/guards/  ← 契约守卫脚本
tests/         ← pytest 测试
```

## 单通用 Agent 架构原则

- 本项目只有一个通用 Agent（`backend/agents/runtime.py`）。
- 不允许新增独立的领域 Agent 类（如 FundAgent、ReportAgent、ParserAgent、RuleAgent）。
- 不允许新增 `fund_skill_run` 调用。
- 不允许新增 `/api/fund/agent/skills/*/invoke` 路由。
- ParserArtifact / RuleArtifact 由通用 Agent 生成和维护，由 artifact service 管理和审核，由 artifact runtime 确定性执行。
- Artifact 审核必须由用户确认后通过 artifact service 完成。
- 执行阶段不能由 Agent 决策。

## 当前最大阻断

| 阻断点 | 位置 | 状态 |
|--------|------|------|
| `run_parser` | `backend/core/artifact_runtime.py` | 已实现 ParserArtifact deterministic runtime |
| `run_rule` | `backend/core/artifact_runtime.py` | NotImplementedError，Phase H1 待交付 |

`run_parser` 已实现，ParserArtifact 可真实解析 xlsx 并返回 CANONICAL_12 rows。`run_rule` 仍为阻断。

## V1 范围

**包含：** 主数据中心、银行导入、手工流水双轨、日报生成、导出打印、基础看板、备份回滚、日志、Agent 系统

**禁止：** 发票 OCR 正式流程、费用审批、合同管理、多人协作、集中部署

## 关键约束

- 核心逻辑确定性优先，AI 辅助其次。报表生成禁止调 LLM（§C8）。
- 表格是主战场，卡片和图表只做辅助。
- 全中文 UI，错误信息中文可读。
- 用户无需命令行，双击即可启动。
- 路由层不承载业务逻辑，业务逻辑放 `services/`。
- 增强层不阻断核心功能 — 模板/主题缺失时降级到默认行为。

## 完成要求

每步完成后必须：1) 输出文件清单 2) 实际验证通过 3) 检查是否破坏其他功能。未达标不得跳步。
