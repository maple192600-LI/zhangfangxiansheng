# Artifact 与 Workflow

## Artifact 系统

### ParserArtifact

- **用途：** 银行流水 / 手工 Excel 的解析规则
- **表：** `parser_artifacts`
- **状态流转：** `draft` → `active` → `retired`
- **当前能力：** 创建、编辑、审核（approve/reject）、激活 — **全部可用**
- **已实现：** `backend/core/artifact_runtime.py::run_parser` 已实现 ParserArtifact deterministic runtime（底层执行器）
- **已实现：** `run_parser_trial()` 候选代码安全试运行（不需要 active artifact，共享 AST guard + sandbox + subprocess 基础设施）
- **未实现：** 银行格式识别（Bank Format Identification）、身份线索提取（Identity Hints Extraction）、主数据匹配（Master Data Matching）、账户归属（Account Attribution）— 这些是独立于 Parser Runtime 的能力，详见 [`14_BANK_IMPORT_GENERALIZATION.md`](14_BANK_IMPORT_GENERALIZATION.md)

### RuleArtifact

- **用途：** 报表模板填充规则
- **表：** `rule_artifacts`
- **状态流转：** `draft` → `active` → `retired`
- **当前能力：** 创建、编辑、审核 — **全部可用**
- **阻断：** `backend/core/artifact_runtime.py::run_rule` 是 `NotImplementedError`，无法执行

### 模板推断

- **表：** `template_inference_job`
- **流程：** 上传 Excel 模板 → 推断占位符 → 生成 RuleArtifact 草稿
- **当前状态：** 可以创建 job 并完成推断，但生成的 RuleArtifact 无法执行

### 安全机制

| 机制 | 文件 | 状态 |
|------|------|------|
| AST 白名单 | `backend/core/artifact_ast_guard.py` | 已实现 |
| 沙箱配置 | `backend/core/artifact_sandbox.py` | 已定义（超时 60s，权限策略） |
| 运行时守卫 | `backend/core/runtime_guard.py` | 已实现（`no_ai_runtime()`） |
| Parser 硬编码 guard | `tools/guards/check_parser_hardcoding.py` | 已实现（拦截 DEFAULT_ACCOUNT_CODE / DEFAULT_ENTITY_CODE / 固定账户编码） |

AST guard 允许的模块前缀：`fund.primitives.`、`fund.artifacts.`、`datetime`、`decimal`、`typing`、`re`、`collections` 等。

沙箱配置已定义。`run_parser` 已实现执行器；`run_rule` 执行器尚未实现（Phase H1 待交付）。

### Parser 规则中心

- **用途：** 用户上传银行样本 → Agent 生成候选解析规则 → 试运行展示结果 → 用户确认保存
- **API：** `backend/api/parser_training.py`（6 个端点）
- **Service：** `backend/services/parser_training_service.py`（训练任务、候选试运行、保存并启用 ParserArtifact）
- **上下文：** `backend/services/parser_context_service.py`（银行/法人/账户主数据摘要供规则生成参考）
- **Agent 工具：** `artifact_create_parser_draft`（创建 parser draft，拒绝硬编码账户/单位）
- **设计要点：**
  - Agent 只参与规则中心的前置配置和规则生成，不参与日常导入
  - 用户审核的是解析结果表格，不是代码
  - 保存时自动退役同 bank + format 的旧 active parser
  - ParserArtifact 只负责读取文件结构，不负责账户归属

## Workflow 系统

### 数据模型

| 表 | 用途 |
|----|------|
| `workflows` | 工作流定义（`draft` / `active` / `archived`） |
| `workflow_versions` | 工作流版本（graph_json） |
| `workflow_runs` | 运行实例 |
| `workflow_run_steps` | 运行步骤 |

### 执行器

- **`workflow_executor.py`** — 同步确定性执行器，按节点拓扑顺序执行
- **`workflow_nodes.py`** — 节点注册表，定义 `NodeHandler` 接口和 `WorkflowNodeContext`
- **`workflow_service.py`** — CRUD + 执行触发

### 前端画布

- Vue Flow 图形编辑器（`WorkflowEditor.vue`）
- 支持节点拖放、连接、属性编辑

### 当前状态

- 代码存在，执行器和节点注册机制可用
- **不等于 production-ready 全闭环**
- 前端画布可编辑和保存图形，运行依赖后端节点注册

---
**校准来源：** `backend/core/artifact_runtime.py`、`backend/core/artifact_ast_guard.py`、`backend/core/artifact_sandbox.py`、`backend/services/artifact_service.py`、`backend/services/workflow_executor.py`、`backend/services/workflow_nodes.py`、`backend/services/workflow_service.py`
**最后校准：** 2026-05-19（新增 run_parser_trial + 规则中心 + 硬编码 guard）
