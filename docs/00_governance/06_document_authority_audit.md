# 06 · 文档权威审计

本文档用于说明项目 Markdown 的权威边界。它不是新的产品设想，而是当前项目“谁说了算”的索引。

## 1. 当前权威链

AI coding 工具只应从以下文件开始理解项目：

1. `AGENTS.md`
2. `CLAUDE.md`
3. `README.md`
4. `docs/README.md`
5. `docs/00_governance/01_scope_and_order.md`
6. `docs/00_governance/02_user_constraints.md`
7. `docs/00_governance/03_tech_constraints.md`
8. `docs/00_governance/04_coding_conventions.md`
9. `docs/00_governance/05_testing_strategy.md`
10. `docs/00_governance/08_anti_drift.md`
11. `docs/00_governance/09_agent_capability.md`
12. `docs/20_execution/12_bank_import_execution.md`
13. `docs/20_execution/13_manual_flow_execution.md`
14. `docs/20_execution/14_base_data_and_report_execution.md`
15. `docs/20_execution/16_agent_system_execution.md`
16. `docs/20_execution/17_skill_system_design.md`
17. `docs/30_contracts/`

## 2. 已归档旧文档

以下旧项目文档已经从项目文档目录移走，统一放入 `new/project_doc_archive/2026-05-07/`：

- 旧产品设计文档。
- 旧首页、主数据、导出、部署、前端规范执行文档。
- 旧手工模板说明。
- 前端脚手架默认 README。

这些文件只保留历史追溯价值，不再参与项目权威排序，不得作为开发输入。

## 3. `new/` 边界

`new/` 不是账房先生开发权威目录。

允许存放：

- 第三方源码。
- 研究资料。
- 已归档旧项目文档。

禁止作为：

- AI coding 必读入口。
- 当前产品需求。
- 当前 API、数据库或页面契约。
- 规避现有缺陷的平行实现目录。

## 4. 当前产品结论

当前主链路固定为：

```text
上传流水或模板
  -> 匹配 Parser 或 Rule
  -> 无规则时由 Agent 创建
  -> 用户审核
  -> 规则中心保存
  -> 确定性执行
  -> 预览
  -> 用户确认
  -> fund_events
  -> 报表
```

Agent 负责学习、讨论、创建和维护规则。日常导入、入库、报表生成必须由已审核规则确定性执行。

## 5. 仍需治理的契约冲突

以下内容仍是代码迁移对象，不允许继续扩大：

- 数据库中残留的旧命名表。
- API 中残留的旧命名路径。
- 银行导入中残留的旧映射提交路径。
- Artifact runtime 中尚未真正执行 Parser/Rule 的路径。
- API 契约数量与真实代码数量不一致。

这些冲突后续必须通过迁移清单逐项处理，而不是新增一套平行实现。
