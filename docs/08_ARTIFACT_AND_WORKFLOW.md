# Artifact 与 Workflow

## Artifact 系统

### ParserArtifact

- **用途：** 银行流水 / 手工 Excel 的解析规则
- **表：** `parser_artifacts`
- **状态流转：** `draft` → `active` → `retired`
- **当前能力：** 创建、编辑、审核（approve/reject）、激活 — **全部可用**
- **已实现：** `backend/core/artifact_runtime.py::run_parser` 已实现 ParserArtifact deterministic runtime（底层执行器）
- **未实现：** 银行格式识别、账户归属匹配 — 当前 parser 样本含 `DEFAULT_ACCOUNT_CODE` 硬编码，银行通用识别是独立能力，尚未交付

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

AST guard 允许的模块前缀：`fund.primitives.`、`fund.artifacts.`、`datetime`、`decimal`、`typing`、`re`、`collections` 等。

沙箱配置已定义。`run_parser` 已实现执行器；`run_rule` 执行器尚未实现（Phase H1 待交付）。

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
**最后校准：** 2026-05-17
