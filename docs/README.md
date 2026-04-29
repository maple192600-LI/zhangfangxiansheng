# docs/ · 开发文档主入口（v3）

> 这是本项目**所有开发相关文档的唯一聚合位置**。项目根目录之前散落的 `development_errors.md`、`user_requirements.md` 已并入本目录。
> 任何 AI 或人类开发者开工前，请严格按本 README 指定的顺序阅读。

---

## 必读顺序（新人 / 新 AI / 新会话）

### 1. 先读"契约"（Layer 1）

1. [`00_governance/00_project_constitution.md`](00_governance/00_project_constitution.md) — **§C1–C9 + §ChangeFlow** · 项目宪法，FROZEN 契约
2. [`00_governance/01_v1_scope_and_order.md`](00_governance/01_v1_scope_and_order.md) — 三阶段（Phase 0 / 1 / 2）总视图
3. [`00_governance/08_anti_drift.md`](00_governance/08_anti_drift.md) — **防跑偏六层机制**（必读）
4. [`00_governance/09_ai_capability_v3.md`](00_governance/09_ai_capability_v3.md) — Fund Agent 与 5 skill 设计

### 2. 再读"契约细节"

5. [`30_contracts/20_database_schema.md`](30_contracts/20_database_schema.md) — 14 张表完整 DDL
6. [`30_contracts/23_api_contracts.md`](30_contracts/23_api_contracts.md) — 42 端点 + 错误码表
7. [`30_contracts/25_primitives_whitelist.md`](30_contracts/25_primitives_whitelist.md) — 37 个基元库函数

### 3. 最后读"执行清单"

8. [`20_execution/00_v3_execution_order.md`](20_execution/00_v3_execution_order.md) — **任务卡 · 从 P0-T1 开始做**

### 4. 开工前的 Kickoff 五条（强制）

见 [`00_governance/08_anti_drift.md`](00_governance/08_anti_drift.md) §7 —— 每次会话开始必须先回答的 5 个问题。

---

## 文档目录结构

```
docs/
├── README.md                          ← 本文件
├── 00_governance/                     ← 契约层（最高优先级）
│   ├── 00_project_constitution.md     ← ★ §C1–C9 FROZEN（v3）
│   ├── 01_v1_scope_and_order.md       ← ★ Phase 0/1/2（v3）
│   ├── 02_user_constraints.md         ← 用户边界
│   ├── 03_tech_constraints.md         ← 技术约束
│   ├── 04_CLAUDE.md                   ← 项目级 Claude 指令
│   ├── 05_目标用户与使用习惯约束_原版.md   ← v2 归档
│   ├── 06_技术选型约束_原版.md           ← v2 归档
│   ├── 07_V1开发任务总控文档_原版.md     ← v2 归档
│   ├── 08_anti_drift.md               ← ★ 防跑偏六层（v3 新增）
│   └── 09_ai_capability_v3.md         ← ★ Fund Agent（v3 新增）
├── 10_product_design/                 ← 产品设计层
│   ├── 00_user_requirements.md        ← 用户需求（从根目录迁入）
│   ├── 00_project_settled_index.md
│   ├── 01_product_master_outline.md
│   ├── 02_frontend_information_architecture.md
│   ├── 03_funds_v1_workflow.md
│   ├── 04_manual_flow_multi_subject.md
│   ├── 05_manual_field_pool_and_template_scheme.md
│   ├── 06_manual_template_v2_spec.md
│   └── 07_zhangfang_v2_design_outline.md
├── 20_execution/                      ← 模块执行文档
│   ├── 00_v3_execution_order.md       ← ★ 任务卡（v3 新增，从 P0-T1 开始）
│   ├── 10_master_data_execution.md
│   ├── 11_home_dashboard_execution.md
│   ├── 12_bank_import_execution.md    ← v2 版，v3 走 00_v3_execution_order
│   ├── 13_manual_flow_execution.md
│   ├── 14_base_data_and_report_execution.md
│   ├── 15_export_dashboard_backup_execution.md
│   └── 16..20_V1执行文档_*_原版.md     ← v2 归档
├── 30_contracts/                      ← 契约实现层
│   ├── 20_database_schema.md          ← ★ 14 表（v3 重写）
│   ├── 21_field_dictionary.md
│   ├── 22_manual_field_pool.md
│   ├── 23_api_contracts.md            ← ★ 42 端点（v3 重写）
│   ├── 24_page_states_and_exceptions.md
│   └── 25_primitives_whitelist.md     ← ★ 37 基元（v3 新增）
├── 40_expected_outputs/               ← 期望输出
├── 50_tests/                          ← 测试与验收
└── 60_claude_code_support/            ← 开工手册 + Handoff
    ├── 07_claude_code_startup_runbook.md
    ├── 08_repo_bootstrap_and_structure.md
    ├── 09_seed_sample_and_fixture_plan.md
    ├── 10_visual_reference_and_page_mapping.md
    ├── 11_done_definition_and_handoff.md
    ├── 12_claude_code_collaboration_protocol.md
    ├── development_errors.md          ← 从根目录迁入
    └── HANDOFF/                       ← ★ 每阶段交付报告（Phase 0 起逐个产生）
```

带 **★** 的文件是 v3 的核心必读文档。

---

## v2 → v3 的变化（简版）

| 项 | v2 | v3 |
|---|---|---|
| 核心解析 | 传统表头相似度匹配 | **Fund Agent 生成 Parser artifact** |
| 报表生成 | 硬编码 Python 聚合 | **Rule artifact 纯代码执行** |
| AI 定位 | 连接测试 + chat 封装 | **生成解析器与规则**（Phase 0 就全面接入） |
| 数据库 | 12 表 | **14 表**（新增 `fund_events / parser_artifacts / rule_artifacts / template_inference_job`） |
| API 上限 | 未限 | **42 条上限**（§C7） |
| Runtime | 允许 AI | **禁用 AI**（§C8） |
| 防跑偏 | 无 | **六层防御 + 5 guards + contracts.lock** |

详见 [`00_governance/01_v1_scope_and_order.md`](00_governance/01_v1_scope_and_order.md) §0。

---

## 文件优先级冲突解决

若发现文档之间内容冲突：

```
00_project_constitution.md（宪法）
       > 30_contracts/*（契约实现）
       > 20_execution/*（执行文档）
       > 10_product_design/*（产品设计）
```

以上顺序高者为准。若宪法与其他文档冲突 → 改其他文档，**不改宪法**（除非走 §ChangeFlow）。

若仍无法判定 → **停下报告**，不擅自选择。

---

## Kickoff 必答清单（每次会话开始）

```
1. 我要做的任务属于哪个 Phase / Task ID？
   答：________________

2. 该任务的 DoD 清单是什么？（§08_anti_drift §5 四项交付物）
   答：文件清单 / 测试证据 / Guards 绿 / Handoff 文档

3. 本任务会触发哪些 guard？
   答：________________

4. 本任务是否涉及修改宪法（§C1–C9）？
   答：不涉及 → 继续；涉及 → 先停下走 §ChangeFlow。

5. 如果中途发现"基元不够 / 占位符不够 / 端点不够"，怎么办？
   答：停下，写 ChangeFlow 申请；绝不悄悄加。
```

缺任一条 = 不开工。

---

**版本**
- v3.0 · 2026-04-23 · 首版发布
- 维护者：项目所有者（书面同意才可修改 00 宪法）
