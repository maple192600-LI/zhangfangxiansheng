# 43_n8n工作流与Agent_Runtime技术研究

## READ WHEN

设计可视化工作流、节点图校验、Agent 运行状态、暂停恢复、记忆存储时读取。

## SOURCE FILES

```text
n8n/packages/@n8n/agents/docs/agent-runtime-architecture.md
n8n/packages/@n8n/agents/src/runtime/agent-runtime.ts
n8n/packages/@n8n/agents/src/storage/sqlite-memory.ts
n8n/packages/@n8n/ai-workflow-builder.ee/evaluations/README.md
n8n/packages/@n8n/workflow-sdk/src/codegen/semantic-graph.ts
```

## KEY FINDINGS

n8n 对本产品最有价值的不是节点外观，而是“节点图必须可验证、可执行、可恢复”：

```text
1. AgentRuntime 有明确状态：idle、running、success、failed、suspended、cancelled。
2. 工具调用可暂停并恢复，适合用户确认、人机协作、外部系统等待。
3. 每次运行有 runId，pendingToolCalls 可恢复。
4. 记忆存储使用 threads、messages、working_memory，消息有 seq 顺序。
5. 工作流生成后有程序化校验，不只靠肉眼看流程图。
6. Semantic Graph 把连接关系变成有意义的节点、输入、输出、root、不可达节点。
7. 评估体系把 LLM 判断和确定性检查分开。
```

## PRODUCT IMPLEMENTATION PLAN

工作流配方必须不是前端画布 JSON，而是可执行 recipe：

```yaml
id: string
name: string
trigger:
  type: manual | file_uploaded | schedule | connector_event
nodes:
  - id: string
    type: string
    input: object
    output_ref: string
edges:
  - from: node_id
    to: node_id
    mapping: object
```

运行状态必须独立保存：

```text
workflow_runs
  run_id
  recipe_id
  status
  trigger_payload
  started_at
  ended_at
  error_message

workflow_node_runs
  run_id
  node_id
  status
  input_json
  output_json
  error_message
  started_at
  ended_at
```

必须实现确定性校验：

```text
has_nodes
has_trigger
all_nodes_connected
no_unreachable_nodes
valid_required_parameters
valid_options_values
expressions_reference_existing_nodes
tools_have_parameters
no_hardcoded_credentials
no_unnecessary_code_nodes
```

Agent 生成工作流时必须走草稿链路：

```text
用户描述目标
-> Agent 生成 recipe_draft
-> 系统运行确定性校验
-> 失败则要求 Agent 修正
-> 样本试跑
-> 用户确认启用
-> recipe_version 生效
```

可视化画布只编辑 recipe，不单独保存另一套逻辑。

## TESTS

```text
空工作流校验失败。
没有触发器校验失败。
断开的节点校验失败。
引用不存在节点输出校验失败。
缺少必填参数校验失败。
样本试跑失败时不得启用。
暂停节点进入 suspended 状态。
用户恢复后从 pending node 继续执行。
画布拖拽连线后 recipe edges 同步变化。
```

## DO NOT

```text
不要只保存画布坐标。
不要让 Agent 生成后直接启用工作流。
不要把校验交给模型判断。
不要把节点运行结果只放在前端内存。
不要让临时工作流污染已启用版本。
```

