# docs · 项目文档主入口

本目录是账房先生项目的权威文档入口。任何 AI 或人类开发者开工前，必须先读根目录 `AGENTS.md`，再读本文件。

`new/` 保存参考源码、研究资料和已归档旧项目文档，不参与项目权威排序。

## 必读顺序

| 顺序 | 文件 | 用途 |
| --- | --- | --- |
| 1 | `../AGENTS.md` | 项目级硬规则、目录边界、工作流边界 |
| 2 | `00_governance/06_document_authority_audit.md` | 旧 Markdown 权威审计与状态分级 |
| 3 | `00_governance/01_scope_and_order.md` | 当前范围、缺口、执行顺序 |
| 4 | `00_governance/02_user_constraints.md` | 用户画像与零技术配置原则 |
| 5 | `00_governance/03_tech_constraints.md` | 技术栈、分层、数据流约束 |
| 6 | `00_governance/04_coding_conventions.md` | 编码、命名、响应格式 |
| 7 | `00_governance/05_testing_strategy.md` | 测试与验收策略 |
| 8 | `00_governance/08_anti_drift.md` | 防跑偏与守卫机制 |
| 9 | `00_governance/09_agent_capability.md` | Agent、Skill、Memory、Parser、Rule 能力契约 |
| 10 | `20_execution/12_bank_import_execution.md` | 银行流水导入执行规范 |
| 11 | `20_execution/13_manual_flow_execution.md` | 手工流水执行规范 |
| 12 | `20_execution/14_base_data_and_report_execution.md` | 基础数据表和报表执行规范 |
| 13 | `20_execution/16_agent_system_execution.md` | Agent、Skill、Memory、Parser、Rule 工作流 |
| 14 | `20_execution/17_skill_system_design.md` | Skill 和 Memory 标准格式 |
| 15 | `20_execution/18_code_migration_inventory.md` | 代码旧入口迁移清单 |

## 冻结契约

`00_governance/00_project_constitution.md` 是冻结契约文件。它仍然是 schema、字段、Parser/Rule 约束的最终来源，但不得由 AI 在普通开发任务中直接修改。

如果冻结契约与当前产品整理目标冲突，先报告冲突，再由用户决定是否启动契约变更流程。

## 文档分级

| 层级 | 位置 | 说明 |
| --- | --- | --- |
| 项目指令 | `AGENTS.md`、`CLAUDE.md` | AI 工具入口与硬规则 |
| 治理规范 | `docs/00_governance/` | 编码、测试、守卫、契约 |
| 执行文档 | `docs/20_execution/` | 当前仍有效的模块实现和开发协作 |
| 数据/API 契约 | `docs/30_contracts/` | 数据表、字段、API、白名单 |

## 当前主链路

```text
上传流水或模板
  -> 匹配已有 Parser/Rule
  -> 无规则时由 Agent 创建并校验
  -> 用户审核接受
  -> 规则中心保存
  -> 确定性执行
  -> fund_events 基础数据表
  -> 报表生成
```

## GitHub 开发流程

项目采用 GitHub Flow：

```text
main
  -> feature/fix/docs/chore branch
  -> commits
  -> pull request
  -> tests + guards + browser validation
  -> review
  -> merge
```

`main` 必须保持可运行。所有实质性修改都走短分支和 PR，不直接提交到 `main`。开源仓库创建后，PR 是代码、文档、测试和迁移工作的唯一合并入口。

## 旧文档处理规则

旧 Markdown 文件只允许两种处理结果：

- `active`：仍是当前权威，内容必须与本入口一致。
- `archived`：已移动到 `new/project_doc_archive/`，不得被 AI 当作当前需求。

不得用旧文件绕过当前入口，不得把参考项目的 `AGENTS.md` 当作账房先生项目指令。
