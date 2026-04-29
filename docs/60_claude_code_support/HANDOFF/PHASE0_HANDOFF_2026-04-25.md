# Phase 0 交班单 · 2026-04-25

## P0-1 完成报告

- 文件：`docs/00_governance/00_project_constitution.md`
- 动作：§C1 从旧字段语义冻结复位为 CANONICAL_12 列序冻结。
- 结果：`fund_events` 12 列、CHECK 约束、辅助列白名单、Runtime 无 AI 写入边界已恢复。

## P0-2 完成报告

- 文件：`docs/00_governance/00_project_constitution.md`
- 动作：§C6 恢复为 v3 活动表集合。
- 结果：表序号更新到 20，恢复 `parser_artifacts` / `rule_artifacts` / `template_inference_job`，保留 `parser_templates` 作为已生效模板列表 UI 渲染表。

## P0-3 完成报告

- 文件：`docs/00_governance/01_v1_scope_and_order.md`
- 动作：整文件重写为 v3.1 AI-First 路线。
- 结果：明确 V1 当前结论、包含/禁止边界、P0-P8 开发顺序、§5 Phase 依赖图和 Phase 进入/完成条件。

## P0-4 完成报告

- 文件：`docs/30_contracts/20_database_schema.md`
- 动作：恢复为 v3 真实 Schema 文档契约。
- 结果：§T0 为 20 表清单；§T2.5 为 CANONICAL_12 `fund_events`；§T4 恢复三张 Fund Agent 产物表 DDL；§T6 明确守护脚本时序。

## P0-5 完成报告

- 文件：`docs/00_governance/03_tech_constraints.md`、`docs/00_governance/08_anti_drift.md`、`docs/00_governance/09_ai_capability_v3.md`
- 动作：扫描残留措辞。
- 结果：未发现需清理项；`docs/00_governance` 与 `docs/30_contracts` 中未检出指定残留短语。

## P0-6 完成报告

- 文件：`docs/99_archived/b_plan_repealed/B_PLAN_COMPLETE_2026-04-24.md`
- 动作：移动作废方案文件，并在文件头追加作废标记。
- 结果：原 `docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md` 已不存在；归档文件首行为作废提示。

## P0-7 完成报告

- 文件：`contracts.lock`
- 动作：运行 `python tools/guards/check_contract_hash.py --update`。
- 结果：契约哈希已重算，随后 `python tools/guards/check_contract_hash.py` 退出码 0。

## 守护脚本状态

| 脚本 | Phase 0 状态 | 说明 |
|---|---|---|
| `check_contract_hash.py` | 通过 | Phase 0 唯一硬性要求，退出码 0 |
| `check_canonical_schema.py` | 红色可接受 | 当前扫描 `backend/db/tables.py::FundEvent`，仍是旧 ORM 列集合；由 Phase 1 P1-2 转绿 |
| `check_primitives_whitelist.py` | 跳过 | artifact 表与记录在后续 Phase 建立 |
| `check_placeholder_binding.py` | 跳过 | Rule artifact 在后续 Phase 建立 |
| `check_api_inventory.py` | 跳过 | Phase 6 才作为接口清单守护 |

## Phase 1 接手点

1. P1-1 先备份当前 `backend/data/zhangfang.db`。
2. P1-2 修改 `backend/db/tables.py::FundEvent`，使 `check_canonical_schema.py` 转绿。
3. P1-3 恢复 `ParserArtifact` / `RuleArtifact` / `TemplateInferenceJob` ORM。
4. P1-4 清理旧 ORM 兼容字段。

## 是否达到 Phase 1 进入条件

YES。Phase 0 文档自洽已完成，唯一硬性守护 `check_contract_hash.py` 已通过；代码与数据库未动，留给 Phase 1。
