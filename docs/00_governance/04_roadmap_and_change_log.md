# 路线图与变更记录

> 本文件记录开发阶段划分、每个阶段改变哪些地图状态、完成后必须更新哪些文档。
> 当前实现状态见 [01_project_map.md](01_project_map.md)，目标能力见 [03_target_product_map.md](03_target_product_map.md)。

---

## 阶段总览

| 阶段 | 目标 | 状态 |
|------|------|------|
| Phase A | 旧路线清理 | ✅ 已完成 |
| Phase B | 项目地图与命名词典 | ✅ 已完成 |
| Phase C | 文档口径修复 | 待合并 |
| Phase 2 | 通用 Artifact API + Service | ✅ 已完成（PR #11） |
| Phase 3 | 复用逻辑迁移 | ✅ 已完成（PR #12） |
| Phase 4 | 前端迁移到 /api/artifacts | ✅ 已完成（PR #13） |
| Phase 5 | 删除旧 FundAgent 体系残留 | ✅ 已完成 |
| Phase D | ParserArtifact runtime 契约 | 待做 |
| Phase 6 / Runtime R0 | Artifact Runtime 守护与测试骨架 | ✅ 已完成 |
| Phase E1 | 最小 run_parser | 待做 |
| Phase F | account_resolver | 待做 |
| Phase G | BankRule 规则中心重建 | 待做 |
| Phase H1 | RuleArtifact runtime | 待做 |
| Phase I | 企业初始化向导 | 待做 |
| Phase WF0 | 工作流模块文档对齐 | ✅ 已完成 |
| Phase WF1 | 工作流业务节点 + Agent 工具 | 待做 |
| Phase WF2 | 工作流前端页面（Vue Flow 画布） | 待做 |

---

## Phase A：旧路线清理

**状态**：✅ 已完成（PR #2, #5）

**目标**：删除 `parser_templates` 旧路线，迁移到 ParserArtifact / RuleArtifact 体系。

**改变的地图状态**：
- `parser_templates` 表已删除，禁止恢复
- `01_project_map.md` 中 `parser_templates` 标记为"已移除"
- `02_naming_glossary.md` 中明确 `ReportTemplate ≠ ParserTemplate`

**必须更新的文档**：
- [x] `01_project_map.md` — 已更新
- [x] `02_naming_glossary.md` — 已更新
- [x] `00_project_constitution.md` §C6 — 已更新

---

## Phase B：项目地图与命名词典

**状态**：✅ 已完成（PR #4）

**目标**：审计 main 分支代码实况，产出当前状态地图和术语边界。

**改变的地图状态**：
- 新增 `01_project_map.md`（24 张表、150 个 API、31 个页面的完整地图）
- 新增 `02_naming_glossary.md`（术语定义、命名问题、禁止混用）

**必须更新的文档**：
- [x] `01_project_map.md` — 本阶段产物
- [x] `02_naming_glossary.md` — 本阶段产物

---

## Phase 5：删除旧 FundAgent 体系残留

**状态**：✅ 已完成

**目标**：删除旧 FundAgent 体系的所有残留文件和引用，完成单通用 Agent 架构清理。

**删除的文件/目录**：
- `backend/agents/fund/` — 旧 FundAgent 调度器、harness、schemas、skills
- `backend/api/fund_agent.py` — 旧 `/api/fund/*` 路由
- `frontend/src/api/fund.js` — 旧前端 API（无消费方）
- `agents/system/skills/fund_parser_manual/` — 绕过 ParserArtifact 的旧技能
- `tests/fund/test_phase6_api.py`、`test_artifact_runtime.py`、`test_sandbox.py`、`test_phase7_privacy.py` — 旧测试
- `tests/e2e/test_security_regression.py` — 依赖已删除的 sandbox

**清理的引用**：
- `fund_skill_run` 从 skill_ops.py、tool_registry.py、permission.py、prompt_builder.py、runtime.py、skill_executor.py 中清除
- `agents.fund.skills` 导入从 tests/fund/conftest.py 和 tests/e2e/conftest.py 中清除
- `fund_agent` router 从 tests/e2e/conftest.py 中清除

**保留的新体系**：
- `backend/fund/`（primitives + artifacts）— 确定性执行基础设施
- `backend/core/artifact_runtime.py` — 新 Artifact Runtime 契约
- `backend/api/artifacts.py` — 通用 Artifact API
- `backend/services/artifact_service.py`、`template_analysis.py`、`field_dictionary_service.py`

**必须更新的文档**：
- [x] `01_project_map.md` — 旧体系标记已删除
- [x] `04_roadmap_and_change_log.md` — Phase 5 标记完成
- [x] `23_api_contracts.md` — 旧端点标记已删除
- [x] `00_single_agent_cleanup_audit.md` — Phase 5 删除项更新

---

## Phase 6 / Runtime R0：Artifact Runtime 守护与测试骨架

**状态**：✅ 已完成

**目标**：为 ParserArtifact / RuleArtifact runtime 实现建立守护基础设施——Schema、AST 白名单、沙箱配置、测试骨架。

**新增文件：**
- `backend/core/artifact_ast_guard.py` — AST 白名单验证，禁止 os/subprocess/eval/exec 等
- `backend/core/artifact_sandbox.py` — 沙箱配置（超时、白名单、最大行数）
- `tests/test_artifact_ast_guard.py` — 29 个 AST 守护测试
- `tests/test_artifact_runtime_guard.py` — 13 个 runtime 守护测试

**修改文件：**
- `backend/core/artifact_runtime.py` — 加固 docstring，明确 Phase E1/H1 计划
- `backend/db/schemas.py` — 新增 ParserRuntimeRow/Input/Result、RuleRuntimeInput/Result

**未做：**
- 未实现 run_parser / run_rule（仍抛 NotImplementedError）
- 未执行 artifact.code
- 未写 fund_events
- 未修改前端

**必须更新的文档：**
- [x] `01_project_map.md` — 断链状态更新
- [x] `04_roadmap_and_change_log.md` — Phase 6 标记完成

---

## Phase C：文档口径修复

**状态**：待合并（PR #6, #7）

**目标**：修正文档中会误导 Claude Code 的冲突口径。

**具体修复**：
- §C6 表数：27/28 → 24 张业务 ORM 表
- §C7 端点：42 上限 → 标记为历史设计
- 防跑偏 guard：14 张表 → 24 张表
- 数据库 schema 标题：v3 → 当前 Schema
- 文件编号：消除 01/02 重复
- 去除 V1/V2/V3 版本标记

**必须更新的文档**：
- [ ] `00_project_constitution.md` — PR #6
- [ ] `18_anti_drift.md` — PR #6
- [ ] `20_database_schema.md` — PR #6
- [ ] `23_api_contracts.md` — PR #6
- [ ] `docs/README.md` — PR #6
- [ ] `01_project_map.md` 开头定位 — 本 PR

---

## Phase D：ParserArtifact runtime 契约

**状态**：待做

**目标**：定义 `artifact_runtime.run_parser` 的输入/输出格式、执行沙箱约定、错误处理约定。

**将改变的地图状态**：
- `01_project_map.md` 中 `artifact_runtime.run_parser` 从"断链"改为"已有契约"
- `12_bank_import_execution.md` 中 done standard 从"不可达成"变为"有契约可依"

**完成后必须更新的文档**：
- [ ] `01_project_map.md` — 更新 `core/artifact_runtime.py` 的状态描述
- [ ] `12_bank_import_execution.md` — 更新 done standard 可达成条件
- [ ] `13_manual_flow_execution.md` — 同上
- [ ] 新增 runtime 契约文档

**依赖**：无前置依赖

---

## Phase E：最小 run_parser

**状态**：待做

**目标**：实现 `artifact_runtime.run_parser`，能执行一个硬编码或简单的解析器，产出 CANONICAL_12 行。

**将改变的地图状态**：
- `bank_import_service.preview/commit`：从"断链"→"可用"
- `manual_flow_service.commit_manual`：从"不可用"→"可用"
- 银行导入链路：从"断链"→"可用（需有 active ParserArtifact）"
- 手工 Excel 链路：从"不完整"→"可用（需有 active ParserArtifact）"

**完成后必须更新的文档**：
- [ ] `01_project_map.md` — 多处状态变更
- [ ] `02_naming_glossary.md` — `artifact_runtime` 状态更新
- [ ] `12_bank_import_execution.md` — done standard 达成
- [ ] `13_manual_flow_execution.md` — Track B 状态更新

**依赖**：Phase D

---

## Phase F：account_resolver

**状态**：待做

**目标**：让通用 Agent 通过工具和技能生成包含可执行代码的 ParserArtifact 草稿，并由 artifact service 管理审核，由 artifact runtime 确定性执行。替代旧 FundAgent harness 只创建占位 draft 的行为。

**将改变的地图状态**：
- 通用 Agent 初始财务技能：从"占位"→"可用"
- `parser_artifacts` 表：从"0 条"→"有真实产物"
- AgentReview 页面：从"半成品"→"可用"

**完成后必须更新的文档**：
- [ ] `01_project_map.md` — Agent/Skill/Artifact 地图状态更新
- [ ] `02_naming_glossary.md` — Skill 状态更新

**依赖**：Phase E

---

## Phase G：BankRule 规则中心重建

**状态**：待做

**目标**：重建 `/rule/bank` 页面，展示 ParserArtifact 列表，支持编辑和激活。

**将改变的地图状态**：
- `/rule/bank` 路由：从"占位"→"可用"
- `BankRule.vue`：从"纯提示页"→"功能页面"

**完成后必须更新的文档**：
- [ ] `01_project_map.md` — 前端页面地图更新

**依赖**：Phase F

---

## Phase H：RuleArtifact runtime

**状态**：待做

**目标**：实现 `artifact_runtime.run_rule`，能执行 RuleArtifact 填充报表模板。

**将改变的地图状态**：
- `report_service.generate_report`：从"不可用"→"可用"
- `/reports/generate` API：从"断链"→"可用"
- `rule_artifacts` 表：从"0 条"→"有真实产物"

**完成后必须更新的文档**：
- [ ] `01_project_map.md` — 报表生成链路状态更新
- [ ] `14_base_data_and_report_execution.md` — done standard 达成

**依赖**：Phase D（复用契约），可与 Phase E-F 并行

---

## Phase I：企业初始化向导

**状态**：待做

**目标**：为新用户提供首次使用引导流程，帮助完成主数据配置、AI Provider 设置、第一条流水导入。

**将改变的地图状态**：
- 新增引导页面和路由
- 首页总控台数据从 mock → 真实数据

**完成后必须更新的文档**：
- [ ] `01_project_map.md` — 新增页面
- [ ] `11_home_dashboard_execution.md` — 首页数据源更新

**依赖**：Phase E

---

## Phase WF0：工作流模块文档对齐

**状态**：✅ 已完成

**目标**：基于 `codex/workflow-module-phase1` 分支已有代码，补齐产品设计文档和执行文档，对齐治理文档。

**新增文件**：
- `docs/10_product_design/07_workflow_module.md` — 产品设计文档
- `docs/20_execution/19_workflow_execution.md` — 执行文档

**更新文件**：
- `docs/00_governance/01_project_map.md` — 表数 24→28，增加 workflow API/Service 条目
- `docs/00_governance/03_target_product_map.md` — 增加工作流编排能力
- `docs/00_governance/04_roadmap_and_change_log.md` — 增加 WF 阶段

**未修改的代码文件**：
- 所有后端代码、前端代码、测试代码、迁移代码均未修改

**必须更新的文档**：
- [x] `07_workflow_module.md` — 本阶段产物
- [x] `19_workflow_execution.md` — 本阶段产物
- [x] `01_project_map.md` — 表数和条目更新
- [x] `03_target_product_map.md` — 能力清单更新
- [x] `04_roadmap_and_change_log.md` — 阶段定义更新

---

## Phase WF1：工作流业务节点 + Agent 工具

**状态**：待做

**目标**：实现真实的业务节点 handler，让工作流能执行实际的数据处理操作。

**将改变的地图状态**：
- `workflow_nodes.py`：从 2 个骨架节点 → 10+ 个业务节点
- `backend/agents/tools/workflow_ops.py`：从无 → 5 个 Agent 工具
- `workflow_executor.py`：增加超时控制
- `api/workflow.py`：增加运行恢复/取消端点

**依赖**：无前置依赖（可与 Phase D-I 并行）

---

## Phase WF2：工作流前端页面

**状态**：待做

**目标**：实现 Vue Flow 画布编辑器、工作流列表页、运行详情页。

**将改变的地图状态**：
- `frontend/src/api/workflow.js`：从无 → 11 个 API 函数
- `frontend/src/views/WorkflowList.vue`：新增页面
- `frontend/src/views/WorkflowEditor.vue`：新增页面（Vue Flow 画布）
- `frontend/src/views/WorkflowRunDetail.vue`：新增页面
- `router/index.js`：新增 3 个路由
- `layouts/MainLayout.vue`：新增导航入口

**依赖**：Phase WF1

| 日期 | 变更 | 涉及文档 |
|------|------|---------|
| 2026-05-13 | Phase WF0 完成：工作流模块文档对齐（产品设计 + 执行文档 + 治理文档更新） | `07_workflow_module.md`, `19_workflow_execution.md`, `01_project_map.md`, `03_target_product_map.md`, `04_roadmap_and_change_log.md` |
| 2026-05-11 | Phase 6 / Runtime R0 完成：AST guard + Schema + 测试骨架 | `01_project_map.md`, `04_roadmap_and_change_log.md` |
| 2026-05-11 | Phase 5 完成：删除旧 FundAgent 体系残留 | `01_project_map.md`, `04_roadmap_and_change_log.md`, `23_api_contracts.md`, `00_single_agent_cleanup_audit.md` |
| 2026-05-10 | 新增路线图与变更记录文档 | `04_roadmap_and_change_log.md` |
| 2026-05-10 | 新增目标产品地图 | `03_target_product_map.md` |
| 2026-05-10 | 项目地图增加定位说明 | `01_project_map.md` |
