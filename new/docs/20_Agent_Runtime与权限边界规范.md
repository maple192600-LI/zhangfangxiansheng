# 20_Agent_Runtime与权限边界规范

## READ WHEN

设计或实现 Agent 对话、页面召唤 Agent、Agent 配置、会话树、上下文压缩、记忆、工具调用、权限拦截、Agent workspace、Skill 调用时必须读取。

## CORE RULE

Agent 负责理解、规划、生成草稿、解释和编排。

确定性工具负责解析、计算、写库、导出和校验。

Agent 不得绕过工具权限直接修改正式数据、正式规则、正式工作流或正式 Skill。

## REFERENCE BASIS

| 参考项目 | 借鉴点 | 本产品实现方式 |
|---|---|---|
| pi-mono | Agent runtime、工具注册、事件流、权限钩子、压缩 | AgentLoop、ToolRegistry、EventStream、PermissionGuard、CompactionEngine |
| Claude Code | 文件操作、命令执行、权限确认、MCP 扩展 | 文件夹授权、工具权限、高风险确认、连接器边界 |
| Claw Code | 本地任务循环和工具执行可见 | FakeModelAdapter、可测试工具闭环 |
| OpenClaw | Agent workspace、Skill 加载、运行记录 | workspace、Skill 摘要加载、工具监控 |
| Hermes Agent | 执行轨迹到候选改进 | ImprovementEngine、候选 Skill / 规则 / 工作流 |

不采用：

```text
不把 Agent 做成固定提示词网页
不让模型直接操作文件或数据库
不让自我改进自动生效
```

## IMPLEMENTATION METHOD

必须按 `docs/30_Agent_Runtime架构与实现蓝图.md` 的 AgentLoop 实现。

最小运行链路：

```text
用户消息
-> ContextBuilder
-> ModelAdapter
-> ToolRegistry
-> PermissionGuard
-> ToolExecutor
-> EventStream
-> assistant summary
```

开发阶段必须先用 FakeModelAdapter 证明链路可运行，再接真实模型。

## data COMPONENTS

Agent Runtime 至少包含：

```text
session_manager
message_store
context_builder
compaction_engine
memory_store
workspace_store
tool_registry
permission_guard
skill_loader
artifact_store
event_stream
audit_logger
```

组件必须对应真实模块或 service，不得只存在于页面字段或提示词中。

## AGENT CONFIG

每个 Agent 至少配置：

```yaml
agent_id:
name:
role:
responsibilities:
allowed_objects:
allowed_tools:
allowed_skills:
memory_scope:
workspace_id:
context_policy:
compaction_policy:
approval_policy:
status:
created_at:
updated_at:
```

## WORKSPACE

`workspace` 只表示 Agent 工作区，不用于普通业务页面路由。

普通业务页面不得使用 `/workspace` 作为路由。日常工作台使用业务路由，例如：

```text
/daily-workbench
```

Agent 相关页面使用：

```text
/agents
/agents/:agent_id
/agents/:agent_id/chat
/agents/:agent_id/sessions
/agents/:agent_id/workspace
/agents/:agent_id/skills
/agents/:agent_id/permissions
```

每个 Agent 默认分配独立 workspace：

```text
workspace_id
agent_id
workspace_path
status
created_at
updated_at
```

物理目录：

```text
workspaces/<workspace_id>/
  files/
  rules/
  workflows/
  reports/
  skills/
  drafts/
  artifacts/
  notes/
  tool_outputs/
  scratch/
```

workspace 用于草稿、分析过程、临时产物和 Agent 自己的工作记录。

workspace 不等于正式数据区。

workspace 内容进入正式规则、Skill、工作流或业务数据前，必须经过用户确认和工具层校验。

## WORKSPACE ASSIGNMENT

Agent 工作区分配在 Agent 配置中完成。

默认规则：

```text
创建 Agent 时自动创建 workspace
workspace_id 默认由系统生成
workspace_path 指向 workspaces/<workspace_id>/
Agent 配置保存 workspace_id
```

允许用户在 Agent 配置中：

```text
查看当前 workspace
重命名 workspace 展示名
更换 workspace
新建 workspace
将当前 Agent 绑定到已有 workspace
设置 workspace 可访问的业务对象范围
设置 workspace 可用 Skill 范围
```

共享规则：

```text
默认不共享 workspace
多个 Agent 共享 workspace 必须由用户显式确认
共享 workspace 时必须显示影响范围
共享 workspace 不等于共享全部权限
```

权限由以下三层共同决定：

```text
Agent.allowed_objects
Agent.allowed_tools
workspace policy
```

Agent 即使绑定某个 workspace，也只能访问权限允许的文件、业务对象、Skill 和工具。

## MEMORY

记忆分层：

```text
公共记忆：组织级通用口径、常用规则、术语
Agent 私有记忆：该 Agent 的职责、偏好、常用流程
会话记忆：当前任务上下文
压缩摘要：长会话压缩后的关键事实
```

记忆必须可查看、可编辑、可禁用。

记忆不得作为正式数据来源。正式数据必须来自数据库、文件仓库、规则版本或工作流配方。

## SESSION TREE

会话必须支持：

```text
session_id
parent_session_id
branch_id
messages
tool_events
artifacts
compaction_summaries
created_at
updated_at
```

从某条消息继续时，必须生成会话分支，不得覆盖原会话记录。

## CONTEXT BUILDING

上下文组装必须可解释：

```text
用户消息
页面上下文
已上传文件摘要
业务对象摘要
字段字典摘要
相关记忆
相关 Skill 摘要
工具结果摘要
压缩摘要
权限说明
```

上下文不得无上限塞入全部文件、全部表格、全部日志。

上下文组装方法：

```text
1. 收集当前页面上下文摘要
2. 收集最近消息窗口
3. 收集压缩摘要
4. 收集相关业务对象和字段字典摘要
5. 收集可用 Skill 摘要
6. 收集权限摘要
7. 生成 context_snapshot_json
8. 保存引用 id，不保存整份文件
```

## COMPACTION

必须支持自动压缩和手动压缩。

压缩摘要必须保留：

```text
用户目标
关键决策
已确认规则
未解决问题
引用文件
引用业务对象
工具执行结果摘要
下一步建议
```

压缩不得删除原会话记录；原会话记录可归档。

## TOOL PERMISSION

工具调用必须经过权限守卫。

权限级别：

```text
read_context
read_file
preview_file
query_data
draft_rule
draft_workflow
draft_skill
run_sample
write_staged_data
commit_confirmed_data
export_file
call_connector
run_sandbox_script
```

需要用户确认的动作：

```text
commit_confirmed_data
启用规则
启用 Skill
启用工作流
撤销导入
作废数据
彻底删除
连接外部系统
运行高权限脚本
```

权限检查方法：

```text
1. 检查 Agent.allowed_tools
2. 检查 tool permission
3. 检查业务对象授权
4. 检查文件夹授权
5. 检查 workspace policy
6. 检查是否需要用户确认
7. 写入 tool_event
```

## TOOL EVENT

每次工具调用必须记录：

```yaml
tool_event_id:
agent_id:
session_id:
tool_name:
input_summary:
output_summary:
status:
permission:
user_confirmed:
started_at:
finished_at:
error:
```

前端必须能展示工具执行过程。

## AGENT OUTPUT TYPES

Agent 输出必须标记类型：

```text
explanation
question
draft_rule
draft_workflow
draft_skill
draft_mapping
tool_plan
tool_result_summary
user_action_required
```

草稿不得伪装成正式结果。

## NEVER

- 不要让 Agent 直接写正式数据库。
- 不要让 Agent 直接启用规则、Skill 或工作流。
- 不要让 Agent 把记忆当成正式数据来源。
- 不要把所有文件内容无差别塞进上下文。
- 不要让工具调用绕过权限守卫。
- 不要让压缩覆盖或删除原会话记录。
- 不要把 workspace 当成正式业务数据区。

## BROWSER CHECK

Agent 功能必须验证：

- 独立 Agent 对话页可用。
- 业务页面可召唤 Agent。
- Agent 状态栏显示模型、token、context、session、压缩状态。
- 工具调用过程可见。
- 高权限动作需要确认。
- Agent 生成的是草稿，不直接生效。
- 会话可恢复。
- 会话分支可查看。
- 压缩摘要可查看。

## DONE

```text
Agent 配置：
workspace：
记忆分层：
会话树：
上下文组装：
压缩策略：
工具权限：
工具事件：
浏览器验收：
```

