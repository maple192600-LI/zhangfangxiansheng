# 01 · V1 范围与执行顺序（v3.1 · AI-First）

> 本文档定义账房先生 V1 的当前执行边界与开发顺序。V1 走 v3 AI-First Schema：CANONICAL_12 `fund_events` + `parser_artifacts` + `rule_artifacts` + `template_inference_job` + 5 个 skill 实体化的 Fund Agent。
> 配合 [00_project_constitution.md](00_project_constitution.md)、[03_tech_constraints.md](03_tech_constraints.md)、[08_anti_drift.md](08_anti_drift.md)、[09_ai_capability_v3.md](09_ai_capability_v3.md) 与 [../30_contracts/20_database_schema.md](../30_contracts/20_database_schema.md) 使用。

---

## §0 · 当前结论

### §0.1 · V1 主线

- 基础事实表使用 §C1 冻结的 CANONICAL_12 `fund_events`。
- Fund Agent 是 V1 核心能力，不是预留骨架；5 个 skill 名单以 §C4 为准，不增不减。
- `parser_artifacts`、`rule_artifacts`、`template_inference_job` 是 V1 活动 schema，用于承载 Agent 产物、报表规则与模板推断状态。
- Runtime 阶段执行已审核的 artifact，不调用 LLM，不让 AI 自由决定账户归属、金额汇总或报表结果。
- 用户界面遵守 §C9 零编程原则：上传样本、审核草稿、接受产物，不要求用户写正则、改 JSON、维护映射代码。

### §0.2 · 最小可用闭环

| 模块 | V1 策略 |
|---|---|
| 主数据 | 板块、法人、银行、账户、账户别名、期初余额由确定性 CRUD 维护 |
| 银行导入 | 上传样本 → Fund Agent 生成 Parser artifact → 用户审核 → Runtime 执行入库 |
| 手工流水 | 快速录入直接写结构化数据；多主体 Excel 上传走 `parser.manual` skill |
| 报表 | Fund Agent 生成/维护 Rule artifact；Runtime 纯代码生成日报、日记账、余额表 |
| 模板推断 | `template.inference` 三阶段：结构解析、语义草稿、人工审核 |
| AI 配置 | 本地 Provider、Agent 绑定、调用审计与隐私档位可配置 |
| 审计 | artifact 版本、样本校验、用户接受记录、操作日志可追溯 |

---

## §1 · V1 范围边界

### §1.1 · 包含

- 主数据中心：板块、法人、银行、账户、账户别名、期初余额。
- 基础数据表：按 CANONICAL_12 查询资金流水，支持日期、主体、账户、摘要、对方、状态、来源等筛选。
- Fund Agent 5 个 skill 完整实现（§C4）。
- 字段字典 + 别名库 + 隐私三档。
- artifact 沙箱执行（AST 扫描 + 超时 + 内存限制）。
- 用户零编程交互：上传 → Agent 处理 → 审核 → 接受 → 入库。
- 银行流水导入：样本识别、Parser artifact 草稿、审核、确认入库。
- 手工流水双轨：快速录入 + 多主体 Excel 上传。
- 报表：资金日报、现金日记账、账户余额表、收支明细、主要账户余额、周/月/年报。
- 首页与看板：待办、进度、关键账户、收支趋势。
- 导出、打印预留、备份、恢复、操作日志。
- AI 配置、Agent 配置、AI 调用审计。
- 本地单用户认证与默认用户初始化。

### §1.2 · 禁止

- 发票 OCR 正式流程。
- 费用审批、合同审批。
- 多人协作、集中部署。
- Electron / Tauri / Rust 重写。
- 收费表格组件。
- 让用户在 UI 中直接编辑字段映射 / 正则 / JSON / 占位符绑定。
- Runtime 阶段调用 LLM（§C8）。
- Agent 产物代码绕过 AST 扫描入库。
- 新增第 6 个 skill（§C4）。

---

## §2 · 开发顺序

必须按以下顺序推进，不能跳步：

1. 治理文档回滚（Phase 0）。
2. v3 Schema 落地（Phase 1）。
3. Fund Agent 骨架（Phase 2）。
4. 5 个 skill 实现（Phase 3）。
5. 沙箱与守护（Phase 4）。
6. Runtime 执行器（Phase 5）。
7. API + 前端（Phase 6）。
8. 字段字典 / 别名库 / 隐私三档（Phase 7）。
9. 集成测试 + 真实样本回归（Phase 8）。

---

## §3 · 验收清单

用户应能在不写代码、不改 JSON、不配置正则的前提下完成：

1. 双击启动系统。
2. 维护法人、银行、账户和期初余额。
3. 上传一份银行流水，等待 Agent 给出解析草稿并审核接受。
4. 手工录入或上传一份多主体流水，处理异常行。
5. 查看基础数据表，生成资金日报和账户余额表。
6. 上传一个报表模板，由 `template.inference` 生成占位符绑定草稿并审核接受。
7. 导出 Excel，金额与基础数据表、日报、余额表一致。
8. 创建备份，并能看到操作日志与 artifact 审计记录。

---

## §4 · 目录结构

```text
backend/
  api/         路由层，只做请求收发
  services/    业务逻辑
  db/          ORM 与 Pydantic schema
  core/        Runtime、沙箱、脱敏、安全、导出等
  agents/      Fund Agent 实体目录与 5 skill
  data/        SQLite、上传、导出、备份数据
frontend/
  src/
    views/     页面
    api/       接口封装
tests/
  backend/     后端服务与核心测试
  fund/        Fund Agent、artifact、基元库测试
  e2e/         业务闭环测试
  fixtures/    脱敏样本
docs/
  00_governance/
  30_contracts/
  60_claude_code_support/
  99_archived/
```

---

## §5 · Phase 依赖图

```text
P0 → P1 → P2 ─┐
              ├─ P3 ─┐
            P7 ──────┤
                     ├─ P4 ─┬─ P6 ─ P8
                     ├─ P5 ─┘
```

| Phase | 进入条件 | 完成条件 |
|---|---|---|
| P0 | 用户书面授权治理回滚 | 文档自洽，`check_contract_hash.py` 绿 |
| P1 | P0 完成 | ORM、Alembic、SQLite 对齐 CANONICAL_12 + 三表 |
| P2 | P1 完成 | Fund Agent 实体目录、harness、schema、memory 骨架可 import |
| P3 | P2 完成，P7 可并行准备 | 5 个 skill 产出 artifact 草稿并可校验 |
| P4 | P3 有 artifact 样本 | AST 扫描、超时、内存限制与白名单守护可用 |
| P5 | P3 有稳定 artifact | Runtime 执行器可纯代码运行 Parser/Rule artifact |
| P6 | P4/P5 完成 | API 与前端完成上传、审核、接受、入库闭环 |
| P7 | P1 完成后可并行 | 字段字典、别名库、隐私三档可供 Agent 使用 |
| P8 | P6 完成 | 集成测试与真实样本回归通过 |

---

## §6 · 风险与后续

| 风险 | 处理 |
|---|---|
| 真实银行流水格式差异大 | 使用脱敏样本回归，沉淀 Parser artifact 与别名库 |
| 用户误以为要配置规则 | 前端只暴露审核/接受/拒绝，不暴露正则、JSON、代码编辑 |
| artifact 生成质量不稳定 | 所有产物必须过样本校验、AST 扫描与用户接受 |
| Runtime 与 Agent 边界混淆 | §C8 固定：Runtime 只执行已审核 artifact，不调用 LLM |
| ORM 当前仍未回滚 | Phase 1 P1-2 将 `backend/db/tables.py::FundEvent` 转绿 |

---

**版本**
- v3.1 · 2026-04-25 · V1 AI-First 路线复位，明确 P0-P8 执行顺序与 Phase 0 守护口径。
- v3.0 · 2026-04-23 · AI-First artifact 方案。
