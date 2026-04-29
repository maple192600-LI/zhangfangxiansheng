# 30_Agent_Runtime架构与实现蓝图

## READ WHEN

设计或实现 Agent Runtime、工具调用、权限拦截、上下文压缩、Skill 调用、Agent workspace、模型适配器、自我改进流程时读取。

## REFERENCE BASIS

| 参考项目 | 借鉴点 | 本产品实现方式 |
|---|---|---|
| pi-mono | 小核心 runtime、工具注册、扩展事件、权限钩子、路径保护、上下文压缩、Skill 渐进加载 | AgentLoop、ToolRegistry、PermissionGuard、EventStream、CompactionEngine、SkillLoader |
| OpenClaw | Agent 工作区、Skill 发现与加载、安全扫描、运行记录 | workspace 目录、全局 Skill、工作区 Skill、Skill 测试与启用记录 |
| Hermes Agent | 记忆、技能、自我改进循环 | 运行复盘、候选改进、样本评估、用户确认后沉淀 |
| Claude Code | 工具调用、文件操作、命令执行、权限确认、MCP 扩展 | 受控本地工具、文件夹授权、高风险确认、连接器边界 |
| Claw Code | 工具注册、权限模式、文件边界、MCP 生命周期、Skill 命令分发 | ToolSpec、PermissionGuard、FileGuard、McpConnector、CommandRouter |
| n8n | Agent 状态机、暂停恢复、工作流节点图、确定性校验 | run state、pending tool call、workflow validator、node event |

详细研究依据：

```text
docs/41_pi-mono_Agent与Skill技术研究.md
docs/42_Claw_Code权限工具与MCP技术研究.md
docs/43_n8n工作流与Agent_Runtime技术研究.md
docs/44_OpenClaw_Gateway与多Agent技术研究.md
docs/45_Hermes_Agent记忆压缩与自我改进技术研究.md
docs/46_Claude_Code工具契约与兼容边界研究.md
```

## CORE RULE

Agent Runtime 不是聊天框。

Agent Runtime 必须实现：

```text
用户消息
-> 上下文组装
-> 模型适配器
-> 工具调用计划
-> 权限检查
-> 工具执行
-> 工具事件记录
-> Agent 结果摘要
-> 前端可见过程
```

没有真实工具调用闭环的 Agent 功能不得声明完成。

## ARCHITECTURE

```text
AgentLoop
  ModelAdapter
  ContextBuilder
  ToolRegistry
  PermissionGuard
  ToolExecutor
  EventStream
  CommandRegistry
  CommandRouter
  WorkspaceStore
  MemoryStore
  CompactionEngine
  SkillLoader
  ImprovementEngine
```

职责：

| 组件 | 职责 |
|---|---|
| AgentLoop | 单轮对话编排，串起上下文、模型、工具、权限、事件和回复 |
| ModelAdapter | 屏蔽不同模型供应商；返回文本和 tool_calls |
| ContextBuilder | 组装页面上下文、会话摘要、记忆摘要、Skill 摘要和权限摘要 |
| ToolRegistry | 注册工具 schema、权限级别、输入输出约束和 handler |
| PermissionGuard | 检查工具、路径、业务对象、数据写入和高风险动作 |
| ToolExecutor | 执行通过权限检查的工具，并捕获结果或错误 |
| EventStream | 保存并推送工具计划、运行、成功、失败、阻断和确认事件 |
| CommandRegistry | 保存中文命令、别名、参数 schema、权限和底层 command_id |
| CommandRouter | 把中文命令或页面动作路由到稳定 service / tool handler |
| WorkspaceStore | 管理 Agent 工作区目录、草稿、产物和临时输出 |
| MemoryStore | 管理公共记忆、Agent 记忆和会话记忆 |
| CompactionEngine | 生成压缩摘要，减少上下文占用 |
| SkillLoader | 扫描 Skill 摘要，按需加载完整 Skill |
| ImprovementEngine | 从失败、重复动作和用户修正中生成候选改进 |

## MODULE PATHS

```text
app/backend/core/agent/
  loop.py
  models.py
  model_adapters.py
  fake_model.py
  context_builder.py
  permission_guard.py
  events.py
  command_registry.py
  command_router.py
  token_meter.py
  compaction.py
  memory.py
  workspace_store.py

app/backend/core/tools/
  registry.py
  executor.py
  specs.py
  filesystem.py
  workspace.py
  data_preview.py

app/backend/core/commands/
  registry.py
  parser.py
  router.py

app/backend/core/skills/
  loader.py
  scanner.py
  lifecycle.py

app/backend/core/improvement/
  reviewer.py
  candidates.py
  evaluator.py
```

## CORE INTERFACES

### ModelAdapter

```python
from typing import Protocol

class ModelAdapter(Protocol):
    def generate(self, request: "ModelRequest") -> "ModelResult":
        ...
```

```python
class ModelRequest(BaseModel):
    messages: list["AgentMessageInput"]
    tools: list["ToolSpec"]
    context_state: dict
```

```python
class ModelResult(BaseModel):
    content: str
    tool_calls: list["ToolCall"] = []
    stop_reason: str = "end_turn"
    token_usage: dict = {}
```

### ToolRegistry

```python
class ToolRegistry:
    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        ...

    def list_specs(self, agent_id: str) -> list[ToolSpec]:
        ...

    def get_handler(self, tool_name: str) -> ToolHandler:
        ...
```

### PermissionGuard

```python
class PermissionGuard:
    def check(self, agent: AgentConfig, tool_call: ToolCall) -> PermissionResult:
        ...
```

```python
class PermissionResult(BaseModel):
    allowed: bool
    reason: str
    requires_user_confirm: bool = False
```

### CommandRegistry

```python
class CommandSpec(BaseModel):
    command_id: str
    label_zh: str
    aliases_zh: list[str] = []
    scope: list[str] = []
    input_schema: dict
    required_permission: str
    handler: str
```

```python
class CommandRouter:
    def resolve(self, text: str, page_context: dict | None = None) -> "ResolvedCommand":
        ...

    def execute(self, command: "ResolvedCommand") -> "CommandResult":
        ...
```

中文命令示例：

```text
/压缩上下文 -> agent.compact
/查看状态 -> agent.status
/查看工具 -> agent.tools.list
/运行工作流 -> workflow.run
/生成报表 -> report.generate
```

### AgentLoop

```python
class AgentLoop:
    def run_turn(
        self,
        session_id: str,
        user_message: str,
        page_context: dict | None = None
    ) -> AgentTurnResult:
        ...
```

## AGENT LOOP FLOW

```text
1. 读取 session 和 agent 配置
2. 保存 user message
3. ContextBuilder 生成 context_snapshot
4. 如果用户输入是中文命令，CommandRouter 解析为 command_id
5. ToolRegistry 返回当前 Agent 可见工具 schema
6. ModelAdapter.generate 返回 content 和 tool_calls
7. 对每个 tool_call 执行参数校验
8. before_tool_call 执行权限、路径、业务对象、确认状态检查
9. blocked：写 agent_tool_events，返回阻断说明
10. requires_user_confirm：写 waiting_confirm 事件，不执行
11. allowed：ToolExecutor 执行工具
12. after_tool_call 裁剪输出、写审计、生成中文摘要
13. 工具输出写 agent_tool_events 和 workspace/tool_outputs
14. AgentLoop 生成 assistant summary
15. 保存 assistant message
16. token_meter 更新估算或真实用量
17. compaction_policy 判断是否需要压缩
18. 返回 messages、tool_events、context_state
```

## FIRST TOOLS

M5 必须先实现最小工具集：

| 工具 | 权限 | 能力 | 用途 |
|---|---|---|---|
| filesystem.list | read_file | 列出授权目录中文件 | 证明 Agent 能真实操作电脑文件夹 |
| filesystem.read_preview | preview_file | 读取授权文件的前 N 行或文本摘要 | 证明路径授权和文件读取生效 |
| workspace.write_artifact | write_workspace | 写入 Agent workspace 产物 | 证明 Agent 能生成可追踪产物 |
| data.query_preview | query_data | 只读查询业务对象预览 | 证明 Agent 通过工具访问数据，不直接写库 |

工具执行模式：

```text
parallel   默认模式，先逐个完成参数和权限预检，再并发执行允许并发的工具
sequential 涉及写入、外部系统、工作流节点状态变更时必须顺序执行
```

工具钩子：

```text
before_tool_call  参数校验后、工具执行前；可阻断、要求确认或改写安全参数
after_tool_call   工具完成后、事件结束前；可裁剪输出、标记错误、写审计、生成中文摘要
```

## FOLDER PERMISSION

Agent 配置必须支持：

```json
{
  "allowed_folders": [
    {
      "path": "F:/finance_samples",
      "mode": "read"
    }
  ]
}
```

路径规则：

```text
必须 resolve 成绝对路径
必须阻断 .. 越界
必须阻断符号链接逃逸
必须阻断未授权根目录
写入只能写 workspace 或用户显式授权写入目录
```

文件工具还必须检查：

```text
文件大小上限
二进制文件识别
符号链接真实路径
读取 offset / limit
写入结构化 patch
```

## RUN STATE

Agent 运行状态必须显式保存：

```text
idle
running
waiting_confirm
suspended
success
failed
cancelled
```

长任务或需要用户确认的工具调用必须保存 pending tool call，允许用户稍后继续。

## FAKE MODEL

开发和测试必须提供 `FakeModelAdapter`。

FakeModelAdapter 根据用户消息返回稳定 tool_call：

| 用户消息包含 | 返回 tool_call |
|---|---|
| 列出授权目录 | filesystem.list |
| 读取授权文件 | filesystem.read_preview |
| 写入工作区产物 | workspace.write_artifact |
| 查询数据预览 | data.query_preview |
| 读取未授权目录 | filesystem.read_preview，目标为未授权路径 |

FakeModelAdapter 用于证明 AgentLoop、工具注册、权限、事件和前端展示真实可运行。

不得用 FakeModelAdapter 冒充真实模型能力。

## SKILL LOADING METHOD

Skill 加载采用渐进式上下文：

```text
启动时扫描 SKILL.md frontmatter
只加载 name、description、路径、启用状态和权限摘要
任务命中后再加载完整 SKILL.md
需要脚本时由工具层执行 scripts/
需要资料时按引用加载 references/
```

不得把全部 Skill 内容一次性塞入上下文。

## IMPROVEMENT METHOD

自我改进不是自动改系统。

ImprovementEngine 只能生成候选草稿：

```text
候选 Skill
候选规则
候选工作流
候选字段映射
候选提示模板
候选工具建议
```

来源：

```text
失败的工具事件
重复出现的用户修正
多次相同文件适配
同一工作流反复手工调整
用户显式要求沉淀能力
```

候选草稿必须经过：

```text
样本试跑
差异展示
用户确认
版本保存
启用记录
```

## FRONTEND VISIBILITY

前端必须展示：

```text
模型请求状态
工具计划
权限检查结果
工具执行状态
工具输出摘要
阻断原因
等待确认动作
workspace 产物
压缩状态
候选改进草稿
```

用户不能只看到一段 Agent 最终回复。

## DO NOT

```text
不要把 Agent 做成固定提示词网页
不要只保存聊天消息
不要跳过工具调用链
不要让模型直接读写本机文件
不要让 Agent 直接写正式数据库
不要把所有 Skill 全量塞进上下文
不要让自我改进自动启用
不要用假数据证明工具可用
不要用只打开页面证明 Agent 可用
```
