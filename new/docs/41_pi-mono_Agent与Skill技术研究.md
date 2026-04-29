# 41_pi-mono_Agent与Skill技术研究

## READ WHEN

设计 Agent 循环、工具调用、上下文压缩、Skill 渐进加载、事件流时读取。

## SOURCE FILES

```text
pi-mono/packages/agent/src/agent-loop.ts
pi-mono/packages/agent/src/types.ts
pi-mono/packages/agent/README.md
pi-mono/packages/coding-agent/docs/skills.md
pi-mono/packages/coding-agent/docs/compaction.md
```

## KEY FINDINGS

pi-mono 的 Agent 不是一个提示词执行器，而是一个可插拔的循环：

```text
AgentMessage[]
-> transformContext()
-> convertToLlm()
-> LLM stream
-> tool_calls
-> prepareToolCall
-> beforeToolCall
-> Tool.execute
-> afterToolCall
-> toolResult message
-> 下一轮 LLM
```

关键实现点：

```text
1. AgentMessage 与 LLM Message 分离：UI 消息、系统事件、业务状态可以存在于 AgentMessage，但进入模型前必须过滤或转换。
2. transformContext 是上下文压缩和外部上下文注入入口。
3. beforeToolCall 在参数校验后执行，可阻断工具。
4. afterToolCall 在工具完成后执行，可修正结果、标记错误、要求终止工具批次。
5. toolExecution 支持 parallel / sequential；工具本身可强制 sequential。
6. EventStream 覆盖 agent_start、turn_start、message_update、tool_execution_start、tool_execution_end。
7. Skill 采用渐进加载：启动时只放名称和描述，命中后再读取完整 SKILL.md。
8. 上下文压缩保留最近内容，把较早内容压缩成结构化摘要，并记录读写文件。
```

## PRODUCT IMPLEMENTATION PLAN

Agent Operation Kernel 必须实现同等结构，但用财务工作台的领域对象承载：

```text
AgentMessage
  role
  content
  message_type
  source_page
  related_object_ids
  created_at

ModelMessage
  role
  content
  tool_calls
```

必须实现：

```text
ContextTransformer
  输入 AgentMessage 列表
  输出可进入模型的消息列表
  负责上下文压缩、页面上下文注入、Skill 摘要注入、记忆摘要注入

ToolPreflightHook
  在工具执行前统一检查参数、权限、路径、业务对象、确认状态

ToolPostHook
  在工具执行后统一写事件、裁剪输出、生成页面可展示摘要

AgentEventStream
  给前端实时展示模型回复、工具计划、工具执行、阻断原因、等待确认、完成结果
```

Skill 实现必须采用渐进加载：

```text
启动或刷新：
  扫描 skills/<skill>/SKILL.md
  扫描 workspaces/<workspace_id>/skills/<skill>/SKILL.md
  只读取 frontmatter 和 description

命中或显式调用：
  读取完整 SKILL.md
  按 Skill 目录解析 scripts、references、assets
  生成可执行工具或工作流节点候选
```

上下文压缩必须实现两个入口：

```text
阈值压缩：上下文接近上限后自动压缩。
手动压缩：用户或 Agent 请求压缩。
```

压缩摘要格式必须包含：

```text
目标
约束
已完成
待处理
关键决策
已读取文件
已生成或修改产物
```

## TESTS

```text
FakeModel 返回单个 tool_call，AgentLoop 能执行并返回 toolResult。
FakeModel 返回多个 tool_call，parallel 模式结果按原始顺序写入消息。
工具声明 sequential 时，整个批次按顺序执行。
beforeToolCall 阻断写操作，工具不得执行。
afterToolCall 修改工具结果，前端事件与最终消息一致。
transformContext 裁剪旧消息后，LLM 输入不包含 UI-only 消息。
Skill 列表只加载摘要，打开详情才读取完整 SKILL.md。
上下文压缩后，页面显示 token 下降和压缩摘要。
```

## DO NOT

```text
不要把页面状态直接塞进 LLM 消息。
不要让工具绕过 beforeToolCall。
不要在启动时加载所有 Skill 全文。
不要把压缩摘要当成用户最新指令。
不要只实现聊天输出而没有工具事件。
```

