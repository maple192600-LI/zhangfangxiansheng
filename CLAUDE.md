# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**账房先生 (ZhangFang)** — 面向中国财务人员的本地部署财务工作台。当前阶段 V1，仅交付"出纳资金日报最小可用闭环"。

本仓库当前是**纯文档总包**，包含完整的产品设计、技术约束、执行文档、数据库契约、API 契约、测试规范和样本骨架。代码将在后续开发中创建。

## Tech Stack (Fixed)

| Layer | Tech |
|-------|------|
| Backend | Python 3.11+ / FastAPI / SQLAlchemy |
| Database | SQLite (V1) |
| Data Processing | Polars / openpyxl |
| Frontend | Vue 3 / Vite / Ant Design Vue / ECharts |
| OCR | PaddleOCR (backend integration) |
| Packaging | 前端静态编译 + 后端挂载 + PyInstaller |

**未经批准不得更换上述主技术栈。**

## Document Architecture (Must Read In Order)

```
docs/
├── 00_governance/     ← 上位约束层（最高优先级）
│   ├── 00_project_constitution.md   ← 项目宪法
│   ├── 01_v1_scope_and_order.md     ← V1 范围与开发顺序
│   ├── 02_user_constraints.md       ← 用户边界
│   ├── 03_tech_constraints.md       ← 技术约束
│   └── 04_CLAUDE.md                 ← 项目级 Claude 指令
├── 10_product_design/ ← 产品与设计层
├── 20_execution/      ← 模块执行文档（Claude Code 直接开工输入）
├── 30_contracts/      ← 契约层（数据库、字段、API、页面状态）
├── 40_expected_outputs/ ← 期望输出定义
├── 50_tests/          ← 测试与验收
└── 60_claude_code_support/ ← 开工手册、目录规范、交付定义、协作协议
```

**冲突处理：** 文档冲突时以 governance → contracts → execution 优先级解决，先报告冲突再等待修订。

## Target Code Structure (After Development Begins)

```
backend/
  main.py / config.py / database.py
  api/         ← 路由层，只做请求收发
  services/    ← 业务逻辑
  db/          ← 数据模型定义
  core/        ← 通用引擎（导出、解析、Agent、日志、备份）
  parsers/     ← 银行流水解析器与模板匹配
  agents/      ← Agent 骨架（shared/ + master/ + parser-assistant/）
  data/        ← 种子数据
frontend/
  src/
    views/     ← 页面按模块拆分
    components/
    api/       ← 接口请求统一收敛
    stores/ / router/ / styles/ / utils/
tests/
  backend/ / frontend/ / e2e/ / fixtures/
```

## Development Order (Strict Sequence, No Skipping)

1. 项目骨架与可运行环境
2. 数据库与基础表
3. 主数据中心（CRUD + 账户初始化 + 期初余额）
4. AI 配置与 Agent 骨架
5. 银行流水导入与模板识别骨架
6. 手工流水双轨（快速录入 + 多主体 Excel 上传）
7. 基础数据表与区间日报生成
8. 首页总控台、导出、打印、看板、备份、回滚
9. 集成测试与真实样本回归

## Key Constraints

- **核心逻辑确定性优先**，AI 辅助其次；运行时 AI 不得自由决定账户归属、汇总正确性
- **表格是主战场**，卡片和图表只做辅助
- **全中文 UI**，错误信息中文可读
- **用户无需命令行**，双击即可启动
- 路由层不承载业务逻辑，业务逻辑放 `services/`
- API 统一响应格式：`{ "code": 0, "message": "ok", "data": {} }`

## V1 Scope Boundaries

**包含：** 主数据中心、银行导入、手工流水双轨、日报生成、导出打印、基础看板、备份回滚、日志、AI 配置与 Agent 骨架

**禁止：** 发票 OCR 正式流程、费用审批、合同管理、多人协作、集中部署、Electron/Tauri/Rust 重写、收费表格组件

## Visual Style

稳重复克制的暖色系：柔和浅暖中性背景 + 低饱和稳重绿色主强调色 + 砂金/暖棕辅助色。大圆角、轻阴影、温度感微文案。详细规范见 `references/style_and_interaction/style_theme_spec.md`。

## Per-Step Completion Requirements

每步完成后必须输出：新增/修改文件清单、完成功能、已知风险、为何达到进入下一步条件。未达标不得跳步。

## Collaboration Protocol

详见 `docs/60_claude_code_support/12_claude_code_collaboration_protocol.md`。核心原则：严格执行文档，不是自由发挥型写手。遇到文档冲突或关键歧义必须停下报告。
