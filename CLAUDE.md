# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 强制：文档入口

**每次会话开始，必须先读 [`docs/README.md`](docs/README.md)。** 该文件是所有开发文档的唯一入口，包含必读顺序和文件优先级。

## Skill Policy

Skills auto-load via forced-eval hook. When the hook triggers a YES for a skill, read its SKILL.md before proceeding.

| Task Type | Skill |
|-----------|-------|
| Python backend | `python-patterns` |
| API/architecture | `backend-patterns`, `api-design` |
| Frontend | `frontend-patterns` |
| Testing | `python-testing`, `tdd-workflow` |
| Verification | `verification-loop` |
| Browser testing | `web-access` |
| Debugging | `systematic-debugging` |
| Code review | `requesting-code-review` |
| Security | `security-review` |
| Coding standards | `coding-standards` |
| Complex planning | `blueprint` |
| Codebase analysis | `codebase-onboarding` |
| Architecture decisions | `architecture-decision-records` |
| Research before coding | `search-first` |
| Library docs lookup | `documentation-lookup` |
| Product → engineering | `product-capability` |
| Context management | `strategic-compact` |

## Project Overview

**账房先生 (ZhangFang)** — 面向中国财务人员的本地部署财务工作台。Agent驱动的产品：Agent编写脚本/规则，脚本确定性处理数据，用户只需上传和确认。

## Tech Stack (Fixed)

| Layer | Tech |
|-------|------|
| Backend | Python 3.11+ / FastAPI / SQLAlchemy |
| Database | SQLite |
| Data Processing | Polars / openpyxl |
| Frontend | Vue 3 / Vite / Ant Design Vue / ECharts |
| OCR | PaddleOCR (后续) |
| Packaging | 前端静态编译 + 后端挂载 + PyInstaller |

**未经批准不得更换上述主技术栈。**

## Document Architecture

所有文档在 `docs/` 目录下，入口为 [`docs/README.md`](docs/README.md)。

```
docs/
├── README.md                        ← 文档主入口（必读）
├── 00_governance/                   ← 核心契约层（最高优先级）
│   ├── 00_project_constitution.md   ← 项目宪法（冻结）
│   ├── 01_project_map.md            ← 当前实现地图
│   ├── 02_naming_glossary.md        ← 命名词典
│   ├── 03_target_product_map.md     ← 目标产品蓝图
│   ├── 04_roadmap_and_change_log.md ← 阶段路线图
│   ├── 10_scope_and_order.md        ← 范围与顺序
│   ├── 11_user_constraints.md       ← 用户约束
│   ├── 12_tech_constraints.md       ← 技术约束
│   ├── 18_anti_drift.md             ← 防跑偏机制
│   └── 19_ai_capability.md          ← Agent能力配置
├── 10_product_design/               ← 产品设计
├── 20_execution/                    ← 模块执行文档
└── 30_contracts/                    ← 数据库/API/字段契约
```

**冲突处理：** constitution > contracts > execution > product_design。先报告冲突，不擅自决定。

## Business Context

业务上下文包在 `project_context/business/`。遇到业务相关任务时：

1. 先读 `project_context/business/INDEX.md`
2. 根据 INDEX.md 按需读取 1-3 个相关文件
3. **不要**一次性读取全部 project_context

## Current Code Structure

```
backend/
  main.py / config.py / database.py
  api/         ← 路由层（23个路由文件）
  services/    ← 业务逻辑（18个服务文件）
  db/          ← ORM表定义（25个表）
  core/        ← 安全、响应格式、运行时守卫
  agents/      ← Agent引擎（运行时+工具+记忆）
  data/        ← SQLite数据库 + 上传/导出/备份
frontend/
  src/
    views/     ← 31个页面（含agent/子目录）
    components/ / composables/ / stores/ / router/ / api/ / styles/
agents/        ← Agent运行时数据（用户创建的实例）
samples/       ← 样本文件
templates/     ← 前端/手工模板
references/    ← 截图、样式规范
tools/guards/  ← 契约守卫脚本
tests/         ← pytest测试
```

## Key Constraints

- **核心逻辑确定性优先**，AI辅助其次；报表生成禁止调LLM（§C8）
- **表格是主战场**，卡片和图表只做辅助
- **全中文 UI**，错误信息中文可读
- **用户无需命令行**，双击即可启动
- 路由层不承载业务逻辑，业务逻辑放 `services/`
- API 统一响应格式：`{ "code": 0, "message": "ok", "data": {} }`
- **增强层不阻断核心功能** — 模板/主题缺失时降级到默认行为

## 单通用 Agent 架构原则

- 本项目只有一个通用 Agent（`backend/agents/runtime.py`），不存在独立的 FundAgent、ReportAgent、ParserAgent、RuleAgent 等领域 Agent 类
- 不允许新增对 `backend/agents/fund/` 的依赖
- 不允许新增 `fund_skill_run` 调用
- 不允许新增 `/api/fund/agent/skills/*/invoke` 路由或调用
- ParserArtifact / RuleArtifact 由通用 Agent 生成和维护，由 artifact service 管理和审核，由 artifact runtime 确定性执行
- Artifact 审核必须由用户确认后通过 artifact service 完成
- 执行阶段不能由 Agent 决策
- 完整审计基线见 [`docs/00_governance/00_single_agent_cleanup_audit.md`](docs/00_governance/00_single_agent_cleanup_audit.md)

## V1 Scope

**包含：** 主数据中心、银行导入、手工流水双轨、日报生成、导出打印、基础看板、备份回滚、日志、Agent系统

**禁止：** 发票OCR正式流程、费用审批、合同管理、多人协作、集中部署

## Visual Style

稳重复克制的暖色系：柔和浅暖中性背景 + 低饱和稳重绿色主强调色 + 砂金/暖棕辅助色。详细规范见 `references/style_and_interaction/style_theme_spec.md`。

## Completion Requirements

每步完成后必须：1) 输出文件清单 2) 实际验证通过 3) 检查是否破坏其他功能。未达标不得跳步。


# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
