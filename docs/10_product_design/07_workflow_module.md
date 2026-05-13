# 07 · 工作流编排模块 — 产品设计

> 本文档定义工作流编排模块的产品目标、用户场景、核心概念和设计边界。
> 当前实现状态见 [20_execution/19_workflow_execution.md](../20_execution/19_workflow_execution.md)。
> 数据库契约见 [30_contracts/20_database_schema.md](../30_contracts/20_database_schema.md) §T8。
> API 契约见 [30_contracts/23_api_contracts.md](../30_contracts/23_api_contracts.md) W1-W11。

---

## 1. 模块定位

工作流编排模块让财务人员通过可视化画布组合系统内已有的数据处理能力（银行导入、手工录入、报表生成、数据导出等），形成可重复执行的自动化流程。Agent 负责创建和调试工作流，用户负责确认和触发执行。

**核心原则**：
- 执行层确定性优先，不依赖 LLM 运行时决策（遵守宪法 §C8）
- 用户只需"确认 + 触发"，无需编写脚本
- Agent 只在创建/调试阶段介入，执行阶段完全确定性

---

## 2. 产品目标

| # | 目标 | 衡量标准 |
|---|------|---------|
| G1 | 减少重复操作 | 用户可将日常操作序列保存为工作流，一键执行 |
| G2 | 降低出错率 | 每个节点的输入/输出有明确 schema，执行过程全审计 |
| G3 | 可追溯 | 每次运行记录完整的步骤级输入/输出/耗时/错误 |
| G4 | 可回滚 | 版本化管理，任何修改不覆盖旧版本 |

---

## 3. 用户场景

### 场景 A：日常资金日报生成

> **角色**：代账会计小李
> **当前痛点**：每天早上要手动导入 5 家银行流水 → 确认 → 切到日报页面 → 选日期 → 导出 Excel，操作重复耗时
> **工作流化后**：小李打开"资金日报工作流" → 点"运行" → 系统自动依次执行 5 个银行导入节点 + 日报生成节点 + 导出节点 → 完成后通知

### 场景 B：月度多账户资金盘点

> **角色**：财务主管王姐
> **当前痛点**：月底要导出所有账户的余额日报 + 收支明细 + 月报，来回切换页面
> **工作流化后**：创建"月度盘点"工作流，包含数据查询节点 + 报表生成节点 + 导出节点，每月一键执行

### 场景 C：Agent 辅助创建工作流

> **角色**：新用户小张
> **场景**：小张在 Agent 聊天中说"帮我创建一个每天自动生成资金日报的流程"，Agent 创建工作流草稿 → 用户在画布上确认节点和顺序 → 激活

### 场景 D：工作流调试与迭代

> **角色**：小李
> **场景**：运行失败后，查看步骤级错误信息 → 修改节点参数 → 自动生成新版本 → 重新运行

---

## 4. 核心概念

### 4.1 工作流（Workflow）

工作流是一个有向无环图（DAG），由节点和边组成。

- 每个工作流有唯一 `workflow_code`、名称、描述
- 拥有版本化历史（每次修改生成新版本）
- 三种状态：`draft`（草稿）→ `active`（启用）→ `archived`（归档）

### 4.2 节点（Node）

节点是最小执行单元。每个节点有：
- `id`：节点唯一标识（工作流内唯一）
- `type`：节点类型（对应节点注册表中的 handler）
- `params`：节点参数（传递给 handler）

### 4.3 边（Edge）

边定义节点之间的执行顺序和依赖关系。
- `from`：源节点 id
- `to`：目标节点 id
- 执行引擎通过拓扑排序确定执行顺序

### 4.4 版本（Version）

每次修改工作流图都生成新的不可变版本：
- `graph_json`：完整的图快照（nodes + edges）
- `version`：递增版本号
- 旧版本永远不会被覆盖或修改

### 4.5 运行（Run）

运行是工作流的一次执行实例：
- 绑定到特定工作流和版本
- 记录输入/输出/错误/耗时
- 包含每个节点的步骤级执行记录

---

## 5. graph_json 结构

> **已实现事实**：以下结构基于 `workflow_service.py:_validate_graph()` 和 `workflow_executor.py:_ordered_nodes()` 的实际验证逻辑。

```json
{
  "nodes": [
    {
      "id": "node_1",
      "type": "control.start",
      "params": {}
    },
    {
      "id": "node_2",
      "type": "bank.import",
      "params": { "bank_account": "6225xxx", "date_range": "last_week" }
    }
  ],
  "edges": [
    { "from": "node_1", "to": "node_2" }
  ]
}
```

**验证规则**（基于代码 `_validate_graph`）：
- `graph` 必须是 dict
- `nodes` 必须是非空数组
- 每个 node 必须是 dict，必须包含 `id`（字符串）和 `type`（字符串）
- `id` 在 nodes 内必须唯一
- `edges` 必须是数组（可以为空）
- 每个 edge 必须是 dict，必须包含 `from` 和 `to`
- `from` 和 `to` 必须引用 nodes 中存在的 id

**执行规则**（基于代码 `_ordered_nodes`）：
- 通过 Kahn 算法拓扑排序确定执行顺序
- 存在循环时抛出异常，拒绝执行
- 节点按排序顺序依次执行
- `previous_outputs` 传递已执行节点的输出

---

## 6. 状态流转

### 6.1 工作流状态

> **已实现事实**：基于 `workflows` 表 CHECK 约束和 `workflow_service.py` 代码。

```
draft ──activate──→ active ──archive──→ archived
  ↑                                      │
  └──── (新建)                           └── (不可逆转)
```

| 状态 | 含义 | 允许操作 |
|------|------|---------|
| `draft` | 草稿，可编辑 | 创建、更新元数据、patch graph、activate |
| `active` | 启用，可执行 | start_run、archive |
| `archived` | 已归档，只读 | 无操作（查看） |

### 6.2 运行状态

> **已实现事实**：基于 `workflow_runs` 表 CHECK 约束和 `workflow_executor.py` 代码。

```
pending ──→ running ──→ completed
                │
                ├──→ failed
                ├──→ paused
                └──→ cancelled
```

| 状态 | 含义 |
|------|------|
| `pending` | 已创建，等待执行 |
| `running` | 正在执行 |
| `completed` | 所有节点执行成功 |
| `failed` | 某个节点执行失败 |
| `paused` | 遇到 control.pause 节点，暂停等待 |
| `cancelled` | 已取消（**目标设计**，当前代码未实现取消端点） |

### 6.3 步骤状态

> **已实现事实**：基于 `workflow_run_steps` 表 CHECK 约束。

| 状态 | 含义 |
|------|------|
| `pending` | 等待执行 |
| `running` | 正在执行 |
| `completed` | 执行成功 |
| `failed` | 执行失败 |
| `skipped` | 已跳过（**目标设计**，当前代码未实现跳过逻辑） |
| `paused` | 已暂停 |

---

## 7. 节点类型体系

### 7.1 已实现节点

> **已实现事实**：基于 `workflow_nodes.py` 代码。

| type | 功能 | input | output |
|------|------|-------|--------|
| `noop` | 空操作（测试用） | params + workflow_input | `{"ok": true, "params": ..., "input": ...}` |
| `control.pause` | 暂停执行 | params + run_id | `{"paused": true, "params": ..., "run_id": ...}` |

### 7.2 V1 候选节点设计

> **目标设计** — Phase 1 需基于真实 handler 再确认。以下为候选分类和节点定义，schema 仅为草案。

#### 控制节点

| type | 功能 | params（草案） | output（草案） |
|------|------|---------------|---------------|
| `control.start` | 流程起点 | 无 | `{"started": true}` |
| `control.end` | 流程终点 | 无 | `{"finished": true}` |
| `control.pause` | 暂停等待人工确认 | `{"message": "请确认数据"}` | `{"paused": true, "message": ...}` |
| `control.branch` | 条件分支 | `{"condition": "field > 0", "true_target": "...", "false_target": "..."}` | `{"branch": "true/false"}` |

#### 数据导入节点

| type | 功能 | params（草案） | output（草案） |
|------|------|---------------|---------------|
| `data.bank_import` | 银行流水导入 | `{"account_code": "...", "file_key": "..."}` | `{"rows_imported": N, "batch_id": "..."}` |
| `data.manual_entry` | 手工流水录入 | `{"entries": [...]}` | `{"rows_created": N}` |
| `data.base_query` | 基础数据查询 | `{"query_type": "daily_report", "filters": {...}}` | `{"rows": [...], "total": N}` |

#### 报表节点

| type | 功能 | params（草案） | output（草案） |
|------|------|---------------|---------------|
| `report.daily_fund` | 资金日报生成 | `{"date": "2026-05-13", "account_codes": [...]}` | `{"report_id": "...", "rows": N}` |
| `report.cash_journal` | 现金日记账 | `{"date_range": ["2026-05-01", "2026-05-31"]}` | `{"report_id": "...", "rows": N}` |

#### 导出节点

| type | 功能 | params（草案） | output（草案） |
|------|------|---------------|---------------|
| `export.excel` | 导出 Excel | `{"data_source": "previous_output_key", "template_id": "..."}` | `{"file_path": "..."}` |

#### Agent 节点

| type | 功能 | params（草案） | output（草案） |
|------|------|---------------|---------------|
| `agent.invoke` | 调用 Agent 执行任务 | `{"agent_id": N, "prompt": "...", "tools": [...]}` | `{"agent_response": "..."}` |

> **注意**：`agent.invoke` 是唯一的 LLM 调用入口。受宪法 §C8 约束，Agent 节点只能用于创建/调试阶段，报表生成节点禁止调用 LLM。

### 7.3 节点注册协议

> **已实现事实**：基于 `workflow_nodes.py` 代码。

- 节点通过 `node_registry.register(node_type, handler)` 注册
- handler 签名：`(params: dict, ctx: WorkflowNodeContext) -> dict`
- `WorkflowNodeContext` 包含 `db`、`run_id`、`workflow_input`、`previous_outputs`
- 执行时遇到未注册的节点类型，run 标记为 failed

---

## 8. 版本管理机制

> **已实现事实**：基于 `workflow_service.py` 代码。

### 8.1 创建

- 创建工作流时自动生成 v1 版本
- `graph_json` 存储完整的图快照

### 8.2 修改（Patch）

- 通过 `PATCH /workflows/{id}/graph` 修改
- 支持两种 patch 操作：
  - `replace_graph`：替换整个图
  - `set_metadata`：修改名称/描述
- 每次 patch 自动递增版本号，生成新版本
- **旧版本不可变**：patch 不会覆盖任何已存在的版本

### 8.3 激活

- 只有 `draft` 状态的工作流可以激活
- 激活后状态变为 `active`，可执行

---

## 9. 前端页面范围

> **目标设计** — 当前无任何前端页面实现。

| 页面 | 路由（候选） | 功能 |
|------|-------------|------|
| 工作流列表 | `/workflows` | 展示所有工作流，筛选状态，快速运行/编辑/归档 |
| 工作流编辑器 | `/workflows/:id/edit` | Vue Flow 可视化画布，拖拽节点、连线、配置参数 |
| 运行详情 | `/workflows/runs/:id` | 运行记录查看，步骤级状态、输入/输出、错误信息 |

### 编辑器技术选型（目标设计）

- **@vue-flow/core**：Vue 3 流程图组件库
- 节点拖拽面板：从节点类型列表拖入画布
- 属性面板：选中节点后右侧展示参数配置
- 自动保存：修改后自动 patch 生成新版本

---

## 10. Agent 工具范围

> **目标设计** — 当前无 Agent 工具实现。

| 工具名 | 功能 | 对应 API |
|--------|------|---------|
| `workflow_list` | 列出工作流 | GET /workflow/workflows |
| `workflow_create` | 创建工作流 | POST /workflow/workflows |
| `workflow_update_graph` | 修改工作流图 | PATCH /workflow/workflows/{id}/graph |
| `workflow_activate` | 激活工作流 | POST /workflow/workflows/{id}/activate |
| `workflow_run` | 启动运行 | POST /workflow/workflows/{id}/runs |

---

## 11. V1 边界

### 包含

- 工作流 CRUD + 版本管理
- 画布式可视化编辑器
- 同步确定性执行引擎
- 节点级执行审计
- Agent 创建/调试工作流的工具
- 暂停节点（人工确认场景）

### 不包含

- 异步/定时执行（定时任务、后台队列）
- 条件分支节点（V2 考虑）
- 并行节点执行（当前为顺序拓扑排序）
- 工作流间调用（子工作流嵌套）
- 多用户协作编辑
- 工作流模板市场
- 节点执行的超时控制（当前无超时机制）
- 运行取消端点（当前代码未实现）

---

## 12. 当前代码与目标设计的差距

| 维度 | 已实现 | 目标 | 差距 |
|------|--------|------|------|
| 数据模型 | 4 表 + ORM + Pydantic + 迁移 | 同左 | ✅ 数据模型已到位 |
| API 端点 | 11 个端点（CRUD + patch + activate/archive + runs） | 11 个端点 | ✅ API 层基本到位 |
| 执行引擎 | 同步拓扑排序 + 步骤记录 + 暂停 | 同左 | ✅ 核心引擎已到位 |
| 节点注册表 | 2 个节点（noop, control.pause） | 10+ 个业务节点 | ❌ **仅骨架** |
| Agent 工具 | 无 | 5 个工具 | ❌ 未实现 |
| 前端页面 | 无 | 3 个页面 | ❌ 未实现 |
| Vue Flow 集成 | 无 | 画布编辑器 | ❌ 未安装依赖 |
| 运行取消 | 无 | 端点 + 逻辑 | ❌ 未实现 |
| 恢复机制 | 暂停可检测 | 恢复端点 + 续执行 | ❌ 未实现 |
| 条件分支 | 无 | branch 节点 | ❌ V2 考虑 |
| 定时执行 | 无 | 定时调度 | ❌ V2 考虑 |
