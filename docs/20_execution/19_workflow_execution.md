# 19 · 工作流编排模块 — 执行文档

> 本文档定义工作流编排模块的执行规范：执行引擎、节点协议、版本管理、错误处理。
> 产品设计见 [10_product_design/07_workflow_module.md](../10_product_design/07_workflow_module.md)。
> 数据库契约见 [30_contracts/20_database_schema.md](../30_contracts/20_database_schema.md) §T8。
> API 契约见 [30_contracts/23_api_contracts.md](../30_contracts/23_api_contracts.md) W1-W11。

---

## 1. 执行引擎架构

> **已实现事实**

```
start_workflow_run()
    │
    ├─ 校验 workflow.status == "active"
    ├─ 获取当前版本 graph_json
    ├─ 创建 WorkflowRun (status=pending)
    │
    └─ execute_workflow(db, run, version)
         │
         ├─ run.status = "running", 记录 started_at
         ├─ 解析 graph_json
         ├─ _ordered_nodes(graph) → 拓扑排序
         │
         └─ 逐节点执行:
              ├─ 创建 WorkflowRunStep (status=running)
              ├─ 特殊: control.pause → run.paused, return
              ├─ node_registry.get(type) → handler
              ├─ 构建 WorkflowNodeContext
              ├─ handler(params, ctx) → output
              ├─ 成功: step.completed, outputs[id] = output
              └─ 失败: step.failed, run.failed, return
```

**关键特性**：
- **同步执行**：整个工作流在一次函数调用中完成，阻塞当前 HTTP 请求
- **拓扑排序**：Kahn 算法（入度归零法），检测循环依赖
- **步骤审计**：每个节点创建 WorkflowRunStep 记录 input/output/error/耗时
- **即时失败**：任何节点失败立即终止，不继续执行后续节点

---

## 2. 执行流程详述

> **已实现事实**：基于 `workflow_executor.py` 代码。

### 2.1 创建运行

1. `workflow_service.start_workflow_run()` 校验 workflow 状态为 active
2. 获取当前版本（`workflow.current_version` 对应的 `WorkflowVersion`）
3. 创建 `WorkflowRun`，记录 workflow_id / version_id / workflow_code / version / input_json
4. 调用 `workflow_executor.execute_workflow()`

### 2.2 执行

1. 设置 `run.status = "running"`，`run.started_at = now()`
2. 从 `version.graph_json` 解析 graph
3. `_ordered_nodes(graph)` 拓扑排序
4. 遍历排序后的节点列表：
   - 创建 `WorkflowRunStep(status="running")`，记录 node_id / node_type / input_json
   - 检查 `node.type == "control.pause"` → 暂停退出
   - 从 `node_registry` 获取 handler
   - 构建 `WorkflowNodeContext(db, run_id, workflow_input, previous_outputs)`
   - 调用 `handler(node.params, ctx)` → node_output
   - 成功：`step.status = "completed"`，`outputs[node_id] = node_output`
   - 失败：`step.status = "failed"`，`run.status = "failed"`，记录 error_message，return

### 2.3 完成

- 全部节点成功：`run.status = "completed"`，`run.output_json = all outputs`
- 节点失败：`run.status = "failed"`，`run.error_message = exception message`
- 暂停：`run.status = "paused"`
- 无论如何都记录 `run.finished_at = now()`

---

## 3. 节点执行协议

> **已实现事实**：基于 `workflow_nodes.py` 代码。

### 3.1 NodeHandler 签名

```python
NodeHandler = Callable[[dict[str, Any], WorkflowNodeContext], dict[str, Any]]
```

- 第一个参数：`params` — 来自 graph 中节点的 `params` 字段
- 第二个参数：`WorkflowNodeContext` — 运行时上下文
- 返回：`dict[str, Any]` — 节点输出，会被存入 `step.output_json`

### 3.2 WorkflowNodeContext 结构

```python
@dataclass(frozen=True)
class WorkflowNodeContext:
    db: Session                    # 数据库会话
    run_id: int                    # 运行 ID
    workflow_input: dict[str, Any] # 运行级别的输入参数
    previous_outputs: dict[str, Any]  # 已执行节点的输出 {node_id: output}
```

### 3.3 已注册节点

| node_type | handler | 输出 |
|-----------|---------|------|
| `noop` | `_noop_node` | `{"ok": true, "params": params, "input": workflow_input}` |
| `control.pause` | `_pause_node` | `{"paused": true, "params": params, "run_id": run_id}` |

### 3.4 节点注册方式

```python
from services.workflow_nodes import node_registry

def my_handler(params: dict, ctx: WorkflowNodeContext) -> dict:
    # 业务逻辑
    return {"result": "..."}

node_registry.register("my.node_type", my_handler)
```

### 3.5 节点命名规范

> **目标设计** — 当前仅有 noop 和 control.pause。

建议采用 `category.name` 格式：
- `control.*` — 控制节点（start, end, pause, branch）
- `data.*` — 数据操作节点（bank_import, manual_entry, query）
- `report.*` — 报表节点（daily_fund, cash_journal）
- `export.*` — 导出节点（excel）
- `agent.*` — Agent 调用节点（invoke）

---

## 4. 版本管理协议

> **已实现事实**：基于 `workflow_service.py` 代码。

### 4.1 创建版本

- 创建工作流时自动生成 v1，graph_json 存储完整图快照
- `workflow.current_version = 1`

### 4.2 Patch 操作

通过 `PATCH /workflows/{id}/graph` 修改，支持两种操作：

**replace_graph**：替换整个图
```json
{
  "patches": [
    {"op": "replace_graph", "graph": {"nodes": [...], "edges": [...]}}
  ],
  "change_summary": "更新节点配置"
}
```

**set_metadata**：修改元数据（不影响版本号，但仍会生成新版本）
```json
{
  "patches": [
    {"op": "set_metadata", "name": "新名称", "description": "新描述"}
  ]
}
```

### 4.3 版本不可变原则

- 任何 patch 都会创建新的 `WorkflowVersion` 记录
- `current_version` 自增
- 旧版本的 `graph_json` 永远不会被修改或删除
- 运行记录绑定特定版本，确保可追溯

### 4.4 版本号校验

- `workflow_versions` 表有唯一索引 `(workflow_id, version)`
- 同一工作流内版本号不会重复

---

## 5. 暂停/恢复机制

### 5.1 暂停（已实现）

> **已实现事实**：基于 `workflow_executor.py` 代码。

- 当执行到 `control.pause` 类型节点时：
  1. 当前 step 标记为 `paused`
  2. run 标记为 `paused`
  3. 记录 `run.finished_at`
  4. 立即返回，后续节点不执行

### 5.2 恢复（目标设计）

> **目标设计** — 当前代码未实现恢复功能。

恢复需要：
1. 新增 API 端点：`POST /workflow/runs/{id}/resume`
2. 从 paused run 中识别已完成的步骤和未执行的节点
3. 从暂停点继续拓扑排序执行
4. 已完成节点的输出需要从 step 记录中恢复

**待确认假设**：恢复时是否允许用户修改 input 参数？还是严格使用原始 input？

---

## 6. 错误处理策略

> **已实现事实**

| 错误类型 | 处理方式 | 记录位置 |
|----------|---------|---------|
| 节点 handler 抛异常 | run.failed, step.failed, 记录 error_message | `workflow_runs.error_message` + `workflow_run_steps.error_message` |
| 节点类型未注册 | 同上（`node_registry.get` 抛 ValueError） | 同上 |
| 图结构无效 | 创建时 `_validate_graph` 拒绝 | API 返回 error 1002 |
| 循环依赖 | `_ordered_nodes` 检测并抛异常 | API 返回 error 1002 |
| 数据库操作失败 | 外层 try-except 捕获，run.failed | `workflow_runs.error_message` |

**当前限制**：
- 无重试机制 — 节点失败后不会自动重试
- 无超时控制 — handler 执行无时间限制
- 无回滚 — 失败后不撤销已执行节点的副作用（如已写入数据库的记录）

---

## 7. 拓扑排序算法

> **已实现事实**：基于 `workflow_executor.py:_ordered_nodes` 代码。

算法：Kahn 算法（入度归零法）

1. 从 graph.nodes 构建节点索引 `{node_id: node}`
2. 从 graph.edges 构建邻接表（incoming / outgoing）
3. 初始化 ready 队列：入度为 0 的节点
4. 循环：从 ready 取出节点，加入有序列表，将其后继节点入度减 1，入度归零的后继加入 ready
5. 如果排序结果数量 < 总节点数 → 存在循环 → 抛异常
6. 后继节点按 node_id 排序（确保确定性）

**确定性保证**：相同 graph 总是产生相同的执行顺序。

---

## 8. API 端点实现状态

> **已实现事实**：基于 `api/workflow.py` 代码。

| 端点 | 方法 | 路径 | 状态 | 备注 |
|------|------|------|------|------|
| W1 | GET | `/api/workflow/workflows` | ✅ 已实现 | 支持 status 筛选 |
| W2 | POST | `/api/workflow/workflows` | ✅ 已实现 | 创建 + v1 版本 |
| W3 | GET | `/api/workflow/nodes` | ✅ 已实现 | 返回已注册节点类型列表 |
| W4 | GET | `/api/workflow/runs` | ✅ 已实现 | 支持 workflow_id/status 筛选 |
| W5 | GET | `/api/workflow/runs/{id}` | ✅ 已实现 | 含步骤详情 |
| W6 | GET | `/api/workflow/workflows/{id}` | ✅ 已实现 | 含当前版本 |
| W7 | PUT | `/api/workflow/workflows/{id}` | ✅ 已实现 | 更新元数据/状态 |
| W8 | PATCH | `/api/workflow/workflows/{id}/graph` | ✅ 已实现 | replace_graph + set_metadata |
| W9 | POST | `/api/workflow/workflows/{id}/activate` | ✅ 已实现 | draft → active |
| W10 | POST | `/api/workflow/workflows/{id}/archive` | ✅ 已实现 | active → archived |
| W11 | POST | `/api/workflow/workflows/{id}/runs` | ✅ 已实现 | 同步执行 |

---

## 9. Service 函数实现状态

> **已实现事实**：基于 `workflow_service.py` 代码。

| 函数 | 状态 | 说明 |
|------|------|------|
| `list_workflow_definitions` | ✅ 已实现 | 按 status 筛选，按 id 降序 |
| `get_workflow_definition` | ✅ 已实现 | 含当前版本 |
| `create_workflow_definition` | ✅ 已实现 | 校验 graph，创建 Workflow + Version v1 |
| `update_workflow_definition` | ✅ 已实现 | 更新 name/description/status |
| `apply_workflow_patch` | ✅ 已实现 | replace_graph / set_metadata，自增版本 |
| `activate_workflow_definition` | ✅ 已实现 | status → active |
| `retire_workflow_definition` | ✅ 已实现 | status → archived |
| `start_workflow_run` | ✅ 已实现 | 校验 active，创建 Run，调用 executor |
| `list_workflow_runs` | ✅ 已实现 | 按 workflow_id/status 筛选 |
| `get_workflow_run` | ✅ 已实现 | 含 steps |

---

## 10. 已有代码文件清单

> **已实现事实**

| 文件 | 行数 | 职责 |
|------|------|------|
| `backend/db/tables.py:575-669` | ~95 行 | 4 个 ORM 类（Workflow, WorkflowVersion, WorkflowRun, WorkflowRunStep） |
| `backend/db/schemas.py:733-821` | ~90 行 | 2 枚举 + 4 请求模型 + 4 响应模型 |
| `backend/api/workflow.py` | 121 行 | 11 个 API 端点 |
| `backend/services/workflow_service.py` | 298 行 | 10 个业务函数 + 6 个序列化/辅助函数 |
| `backend/services/workflow_executor.py` | 163 行 | execute_workflow + _ordered_nodes（拓扑排序） |
| `backend/services/workflow_nodes.py` | 61 行 | WorkflowNodeRegistry + 2 个内置节点 |
| `backend/main.py:46,253` | 2 行 | import + 路由注册 |
| `alembic/versions/006_add_workflow_tables.py` | 迁移 | 创建 4 张表 + 索引 + CHECK 约束 |
| `tests/test_workflow_module.py` | 11 个测试 | CRUD、版本、执行、拓扑、暂停、架构守卫 |

---

## 11. 待实现清单

> **目标设计** — 按优先级排列。

| 优先级 | 任务 | 依赖 | 说明 |
|--------|------|------|------|
| P0 | 实现业务节点 handler | 无 | 当前只有 noop/pause，无法执行真实业务 |
| P0 | 运行恢复端点 | 暂停机制 | POST /runs/{id}/resume |
| P1 | 运行取消端点 | 无 | POST /runs/{id}/cancel |
| P1 | Agent 工具（workflow_ops.py） | API 层 | 5 个工具函数 |
| P1 | 前端 API 文件（workflow.js） | API 层 | 对接 11 个端点 |
| P2 | Vue Flow 画布编辑器 | 前端 API | WorkflowEditor.vue |
| P2 | 工作流列表页 | 前端 API | WorkflowList.vue |
| P2 | 运行详情页 | 前端 API | RunDetail.vue |
| P3 | 节点超时控制 | 执行引擎 | handler 执行限时 |
| P3 | 节点重试机制 | 执行引擎 | 可配置重试次数 |
| V2 | 条件分支节点 | 拓扑排序改造 | 需要支持条件路由 |
| V2 | 并行执行 | 执行引擎改造 | 多节点同时执行 |
| V2 | 定时调度 | 外部调度器 | cron 触发工作流 |

---

## 12. 已实现 vs 待实现差距汇总

| 文件 | 已实现 | 待实现 |
|------|--------|--------|
| `workflow_nodes.py` | Registry 类 + noop + pause | 10+ 个业务节点 handler |
| `workflow_executor.py` | 同步拓扑排序执行 + 暂停 + 失败记录 | 恢复执行、超时控制、重试 |
| `workflow_service.py` | 完整 CRUD + patch + activate/retire + start_run | 运行取消、运行恢复 |
| `api/workflow.py` | 11 个端点 | 运行恢复端点、运行取消端点 |
| `backend/agents/tools/` | 无 | workflow_ops.py（5 个 Agent 工具） |
| `frontend/src/api/` | 无 | workflow.js（前端 API 文件） |
| `frontend/src/views/` | 无 | 3 个页面组件 |
| `frontend/src/components/` | 无 | workflow/ 画布组件 |
| `package.json` | 无 @vue-flow | 安装 @vue-flow/core |
| `router/index.js` | 无 workflow 路由 | 3 个新路由 |
| `layouts/MainLayout.vue` | 无 workflow 导航 | 导航入口 |
