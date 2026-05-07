# 20 · 数据库契约

本文档定义当前数据库契约和迁移边界。详细物理字段以 `backend/db/tables.py` 和 Alembic 迁移为准；本文只保留项目开发必须遵守的稳定约束。

## 1. 核心事实表

`fund_events` 是所有报表唯一流水事实源。

基础 12 列由 `docs/00_governance/00_project_constitution.md` §C1 冻结：

1. `business_date`
2. `entity_code`
3. `entity_name`
4. `account_code`
5. `account_name`
6. `summary`
7. `counterparty`
8. `amount_in`
9. `amount_out`
10. `rolling_balance`
11. `state`
12. `source`

允许存在元数据列，如 `id`、`batch_id`、`parser_artifact_id`、`created_at`、`updated_at`。元数据列不得改变基础 12 列语义。

## 2. 主数据表

主数据至少覆盖：

- 板块。
- 法人或单位。
- 银行。
- 账户。
- 账户别名。
- 期初余额和余额日期。

Parser 和 Rule 执行时只能通过主数据和 `fund_events` 完成账户、主体、余额和报表取数。

## 3. 规则资产表

规则资产分为：

- Parser artifact：银行流水和手工流水解析规则。
- Rule artifact：报表生成和模板填充规则。
- 模板识别任务：首次上传报表模板时生成 Rule 草稿。
- 规则审核记录：记录用户接受、拒绝、修正和样本校验结果。

旧模板表只能作为迁移兼容来源，不得作为新的规则中心资产模型。

## 4. Agent 数据表

Agent 相关数据至少覆盖：

- Agent 实例。
- 会话。
- 消息。
- 运行记录。
- Memory。
- Skill 注册。

当前代码中仍存在旧物理命名，迁移前不得删除用户数据。命名迁移必须提供：

- Alembic 迁移。
- 数据备份。
- 回滚方案。
- 调用方迁移清单。
- guard 和测试结果。

## 5. 导入和报表记录

导入和报表必须保留可追溯信息：

- 来源文件。
- 批次。
- Parser 或 Rule。
- 用户确认记录。
- 原始行快照或模板来源。
- 解析状态和异常原因。

## 6. 数据库变更规则

- Schema 变更必须走迁移脚本。
- 不得用 `_patch_schema()` 长期替代正式迁移。
- 删除表或列必须先确认没有前端、后端、测试、导出、备份调用方。
- 运行数据不得提交到仓库。
- 用户数据迁移必须先备份。

## 7. 验收

- `tools/guards/check_canonical_schema.py` 通过。
- 银行导入、手工流水、报表生成都以 `fund_events` 为事实源。
- 规则资产可追溯到样本、审核记录和执行结果。
- 命名迁移完成前，旧物理名只作为兼容事实存在，不作为新设计名称继续扩散。
