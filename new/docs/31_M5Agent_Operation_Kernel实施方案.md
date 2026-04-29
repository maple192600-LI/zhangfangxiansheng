# 31_M5Agent_Operation_Kernel实施方案

## READ WHEN

执行 `24_产品代码开发路线图.md` 的 M5 Agent Operation Kernel 时读取。

## GOAL

实现一个可运行的 Agent 工具调用闭环：用户消息进入 AgentLoop，FakeModel 生成工具调用，权限守卫检查，工具真实执行或阻断，前端展示消息、工具事件、workspace 产物、token 和压缩状态。

## MUST READ

```text
AGENTS.md
docs/01_项目文件地图与交付边界.md
docs/02_测试与验收规范.md
docs/03_AI_Coding_开发协作规范.md
docs/15_浏览器验收记录规范.md
docs/18_API与前后端契约规范.md
docs/20_Agent_Runtime与权限边界规范.md
docs/24_产品代码开发路线图.md
docs/25_技术栈与工程架构蓝图.md
docs/30_Agent_Runtime架构与实现蓝图.md
docs/41_pi-mono_Agent与Skill技术研究.md
docs/42_Claw_Code权限工具与MCP技术研究.md
docs/45_Hermes_Agent记忆压缩与自我改进技术研究.md
docs/46_Claude_Code工具契约与兼容边界研究.md
```

## REFERENCE BASIS

| 参考项目 | M5 采用的实现方法 |
|---|---|
| pi-mono | AgentMessage 与 LLM Message 分离、beforeToolCall、afterToolCall、parallel / sequential 工具批次、事件流 |
| Claw Code | ToolSpec、PermissionPolicy、文件大小限制、二进制识别、路径边界、结构化 patch |
| Claude Code | 类型化工具输出、Agent 子任务统计、文件读取按 text / sheet / image / pdf 分流 |
| OpenClaw | Agent workspace、per-agent session、Skill snapshot |
| Hermes Agent | SQLite 会话、FTS 搜索、压缩摘要防注入、失败和重复动作沉淀 |

## ROUTE RULES

```text
rules/02_单一事实源与数据联动.md
rules/03_浏览器验收.md
rules/06_PR与完成定义.md
rules/10_环境隔离与依赖安装.md
rules/12_项目护栏检查.md
rules/15_任务单与PR模板.md
rules/21_API与前后端契约.md
rules/23_Agent_Runtime与权限边界.md
```

## MODIFY FILES

```text
app/backend/db/models/system.py
app/backend/main.py
app/frontend/src/router/index.ts
app/frontend/src/layouts/MainLayout.vue
```

## CREATE FILES

```text
app/backend/db/models/agent.py
app/backend/schemas/agents.py
app/backend/services/agent_service.py
app/backend/services/agent_session_service.py
app/backend/api/agents.py

app/backend/core/agent/loop.py
app/backend/core/agent/models.py
app/backend/core/agent/model_adapters.py
app/backend/core/agent/fake_model.py
app/backend/core/agent/context_builder.py
app/backend/core/agent/permission_guard.py
app/backend/core/agent/events.py
app/backend/core/agent/command_registry.py
app/backend/core/agent/command_router.py
app/backend/core/agent/token_meter.py
app/backend/core/agent/compaction.py
app/backend/core/agent/workspace_store.py

app/backend/core/tools/specs.py
app/backend/core/tools/registry.py
app/backend/core/tools/executor.py
app/backend/core/tools/filesystem.py
app/backend/core/tools/workspace.py
app/backend/core/tools/data_preview.py
app/backend/core/tools/file_guard.py

app/backend/tests/test_agent_workspace.py
app/backend/tests/test_agent_loop_filesystem.py
app/backend/tests/test_agent_permission_guard.py
app/backend/tests/test_agent_tool_events.py
app/backend/tests/test_agent_compaction.py

app/frontend/src/api/agents.ts
app/frontend/src/types/agents.ts
app/frontend/src/stores/agentStore.ts
app/frontend/src/views/AgentsView.vue
app/frontend/src/views/AgentChatView.vue
app/frontend/src/views/AgentWorkspaceView.vue
app/frontend/src/views/AgentPermissionsView.vue
app/frontend/src/components/AgentStatusBar.vue
app/frontend/src/components/AgentToolEventList.vue
app/frontend/src/components/AgentEntryButton.vue
app/frontend/src/components/AgentMessageList.vue
app/frontend/src/components/AgentComposer.vue
```

## DEPENDENCIES

M5 不新增外部模型 SDK。

M5 使用 `FakeModelAdapter` 完成确定性开发和验收。

真实模型接入放在后续任务，不得阻塞 M5。

## ARCHITECTURE

M5 只实现可运行的 Agent 操作内核：

```text
AgentChatView
-> api/agents.ts
-> api/agents.py
-> agent_session_service.py
-> AgentLoop
-> CommandRouter
-> ContextBuilder
-> FakeModelAdapter
-> ToolRegistry
-> PermissionGuard
-> ToolExecutor
-> agent_tool_events
```

前端必须展示工具事件，后端必须保存工具事件。不能只返回一段 assistant 文本。

## CORE INTERFACES

M5 的核心接口以 `docs/30_Agent_Runtime架构与实现蓝图.md` 为准，必须至少落地：

```text
ModelAdapter
ToolRegistry
PermissionGuard
AgentLoop
WorkspaceStore
ToolExecutor
EventStream
CommandRegistry
CommandRouter
```

## CHINESE COMMANDS

M5 必须先实现 Agent 对话页的中文命令解析，不要求用户记英文命令。

命令注册：

```text
/查看状态 -> agent.status
/查看工具 -> agent.tools.list
/压缩上下文 -> agent.compact
/继续 -> agent.continue
/停止 -> agent.cancel
```

中文命令可以有别名，例如：

```text
/状态、/现在状态、/上下文状态 -> agent.status
/压缩、/整理上下文 -> agent.compact
```

执行规则：

```text
中文命令只解析为 command_id
command_id 再进入权限检查和 service handler
不得在业务代码中用中文字符串判断具体动作
命令结果、错误、确认提示必须中文显示
```

## NEW TABLES

### agents

| 字段 | 类型 | 约束 |
|---|---|---|
| id | string | 主键，`agent_<uuid>` |
| name | string | 必填 |
| role | string | 必填 |
| responsibilities_json | text | JSON 数组 |
| allowed_objects_json | text | JSON 数组 |
| allowed_tools_json | text | JSON 数组 |
| allowed_skills_json | text | JSON 数组 |
| allowed_folders_json | text | JSON 数组 |
| memory_scope | string | public_and_private / private_only / disabled |
| workspace_id | string | 必填 |
| context_policy_json | text | JSON 对象 |
| compaction_policy_json | text | JSON 对象 |
| approval_policy_json | text | JSON 对象 |
| status | string | active / disabled |
| created_at | datetime | 必填 |
| updated_at | datetime | 必填 |

### agent_workspaces

| 字段 | 类型 | 约束 |
|---|---|---|
| id | string | 主键，`workspace_<uuid>` |
| display_name | string | 必填 |
| workspace_path | string | 指向 `workspaces/<workspace_id>/` |
| policy_json | text | JSON 对象 |
| status | string | active / archived |
| created_at | datetime | 必填 |
| updated_at | datetime | 必填 |

### agent_sessions

| 字段 | 类型 | 约束 |
|---|---|---|
| id | string | 主键，`session_<uuid>` |
| agent_id | string | 指向 agents.id |
| parent_session_id | string | 可空 |
| branch_id | string | 必填 |
| title | string | 可空 |
| status | string | active / archived |
| created_at | datetime | 必填 |
| updated_at | datetime | 必填 |

### agent_messages

| 字段 | 类型 | 约束 |
|---|---|---|
| id | string | 主键，`msg_<uuid>` |
| session_id | string | 指向 agent_sessions.id |
| agent_id | string | 指向 agents.id |
| role | string | user / assistant / system / tool |
| output_type | string | explanation / question / tool_plan / tool_result_summary / user_action_required |
| content | text | 必填 |
| context_snapshot_json | text | JSON 对象 |
| token_estimate | integer | 默认 0 |
| created_at | datetime | 必填 |

### agent_tool_events

| 字段 | 类型 | 约束 |
|---|---|---|
| id | string | 主键，`tool_event_<uuid>` |
| agent_id | string | 指向 agents.id |
| session_id | string | 指向 agent_sessions.id |
| tool_call_id | string | 必填 |
| tool_name | string | 必填 |
| input_summary | text | 必填 |
| output_summary | text | 可空 |
| status | string | planned / running / succeeded / failed / blocked / waiting_confirm |
| permission | string | 必填 |
| user_confirmed | boolean | 默认 false |
| error | text | 可空 |
| started_at | datetime | 必填 |
| finished_at | datetime | 可空 |

### agent_compaction_summaries

| 字段 | 类型 | 约束 |
|---|---|---|
| id | string | 主键，`compact_<uuid>` |
| agent_id | string | 指向 agents.id |
| session_id | string | 指向 agent_sessions.id |
| summary_json | text | JSON 对象 |
| source_message_count | integer | 必填 |
| token_before | integer | 必填 |
| token_after | integer | 必填 |
| created_at | datetime | 必填 |

## IMPLEMENTATION STEPS

### Step 1: 数据模型和迁移

实现 agents、agent_workspaces、agent_sessions、agent_messages、agent_tool_events、agent_compaction_summaries。

完成后必须能初始化数据库并插入一个 Agent。

### Step 2: WorkspaceStore

创建 Agent 时自动创建：

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

`workspace_path` 必须保存到 agent_workspaces。

### Step 3: ToolSpec 和 ToolRegistry

定义：

```python
class ToolSpec(BaseModel):
    name: str
    label_zh: str
    description: str
    permission: str
    input_schema: dict
    output_schema: dict | None = None
    execution_mode: str = "parallel"
```

注册以下工具：

```text
filesystem.list
filesystem.read_preview
workspace.write_artifact
data.query_preview
```

### Step 4: 文件系统工具

文件系统工具必须先经过 `file_guard.py`：

```text
resolve 绝对路径
检查授权根目录
检查符号链接真实路径
检查文件大小
检查二进制文件
读取 offset / limit
输出中文摘要
```

`filesystem.list`：

```json
{
  "path": "F:/finance_samples",
  "pattern": "*.xlsx"
}
```

输出：

```json
{
  "files": [
    {
      "name": "sample.xlsx",
      "path": "F:/finance_samples/sample.xlsx",
      "size_bytes": 1234
    }
  ]
}
```

`filesystem.read_preview`：

```json
{
  "path": "F:/finance_samples/sample.xlsx",
  "max_rows": 20
}
```

输出只返回预览摘要，不返回整份文件。

### Step 5: PermissionGuard

检查顺序：

```text
tool_name 是否在 allowed_tools
permission 是否匹配工具权限
target path 是否位于 allowed_folders
写入是否只发生在 workspace 或显式授权写入目录
高风险动作是否需要 user_confirmed
```

路径检查必须使用绝对路径和规范化路径。

未授权时写入 blocked 工具事件。

权限模式：

```text
read_only
workspace_write
external_write
confirm
```

`before_tool_call` 必须调用 PermissionGuard。`after_tool_call` 必须写审计、裁剪输出、生成中文工具摘要。

### Step 6: FakeModelAdapter

规则：

```text
消息包含“列出授权目录” -> filesystem.list
消息包含“读取授权文件” -> filesystem.read_preview
消息包含“写入工作区产物” -> workspace.write_artifact
消息包含“查询数据预览” -> data.query_preview
消息包含“读取未授权目录” -> filesystem.read_preview，目标为未授权路径
```

FakeModelAdapter 只用于开发、测试和 M5 验收。

### Step 7: AgentLoop

`run_turn` 必须执行：

```text
保存用户消息
生成 context_snapshot
读取工具 schema
调用 FakeModelAdapter
写 planned 工具事件
执行权限检查
blocked / waiting_confirm / running / succeeded / failed 状态流转
保存工具输出摘要
保存 assistant message
返回统一响应
```

### Step 8: 前端页面

`/agents`：

```text
Agent 列表
新建 Agent
授权文件夹配置
进入对话
```

`/agents/:agent_id/chat`：

```text
消息列表
输入框
工具事件列表
状态栏
手动压缩按钮
workspace 摘要
```

`/agents/:agent_id/permissions`：

```text
allowed_tools
allowed_folders
allowed_objects
allowed_skills
```

### Step 9: AgentEntryButton

首页和数据页面必须显示 `AgentEntryButton`。

点击后进入 Agent 对话页，并带入：

```json
{
  "source_page": "home",
  "selected_object_ids": [],
  "selected_file_ids": []
}
```

## API

```text
GET    /api/agents
POST   /api/agents
GET    /api/agents/{agent_id}
PATCH  /api/agents/{agent_id}
POST   /api/agents/{agent_id}/sessions
GET    /api/agents/{agent_id}/sessions
POST   /api/agent-sessions/{session_id}/messages
GET    /api/agent-sessions/{session_id}/messages
POST   /api/agent-sessions/{session_id}/compact
GET    /api/agents/{agent_id}/tool-events
GET    /api/agents/{agent_id}/workspace
```

## TESTS

后端测试必须覆盖：

```text
创建 Agent 自动创建 workspace 目录
Agent 可配置 allowed_folders
filesystem.list 只能读取授权目录
filesystem.read_preview 只能读取授权文件
读取未授权目录时生成 blocked 事件
workspace.write_artifact 写入当前 Agent workspace
AgentLoop 能从用户消息触发 FakeModel tool_call
中文命令能解析为 command_id
中文命令不会绕过 PermissionGuard
工具事件状态从 planned 到 succeeded
工具失败时写 failed 和中文错误
发送消息后前端可查询消息和工具事件
手动压缩生成 compaction summary
```

## BROWSER ACCEPTANCE

验收记录：

```text
dev/reports/browser_acceptance/YYYYMMDD_HHMM_m5_agent_operation_kernel.md
```

必须使用：

```text
Claude Code: web-access skill
Codex: browser-use
```

必须准备：

```text
dev/fixtures/agent_allowed/sample.xlsx
dev/fixtures/agent_forbidden/secret.xlsx
```

必须验证：

```text
打开 /agents
创建 Agent
给 Agent 授权 dev/fixtures/agent_allowed
进入 Agent 对话页
输入：列出授权目录
页面显示 sample.xlsx
工具事件显示 filesystem.list succeeded
输入：读取未授权目录
页面显示 blocked
工具事件显示未授权中文原因
输入：写入工作区产物
workspace 页面出现 artifact
输入：/压缩上下文
页面显示压缩摘要
点击手动压缩
页面出现压缩摘要
刷新页面后消息、工具事件、workspace 产物仍存在
从首页点击 AgentEntryButton 能进入对话页并带入页面上下文
```

## EXIT CONDITION

```text
AgentLoop 可运行：
FakeModelAdapter 可触发工具：
ToolRegistry 可列出工具：
PermissionGuard 可阻断越权：
filesystem.list 真实执行：
filesystem.read_preview 真实执行：
workspace.write_artifact 真实执行：
工具事件可查：
前端可见工具过程：
上下文状态可见：
压缩摘要可生成：
后端测试通过：
前端构建通过：
浏览器验收记录已落文件：
项目护栏检查通过：
PR 模板填写完整：
```

## DO NOT

```text
不要只做 Agent 页面
不要只保存聊天消息
不要只写提示词
不要用假文件名冒充真实工具结果
不要跳过 FakeModelAdapter
不要跳过 PermissionGuard
不要让模型直接访问文件系统
不要读取未授权目录
不要把工具输出整份塞进上下文
不要把 Agent 写成固定出纳场景
```
