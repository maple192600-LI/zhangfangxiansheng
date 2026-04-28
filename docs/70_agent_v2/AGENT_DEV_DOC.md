# 账房先生 Agent 系统开发文档 v2.0

> 编制日期：2026-04-27
> 范围：账房先生 V1 真正"AI 智能体"开发——用户可自建多个、自由命名、有聊天 UI、Skill 系统、工作区、记忆、运行历史、权限控制
> 目标读者：开发执行者（人或 AI Coding 工具）+ 业务负责人验收

---

## 0. 立项依据与设计参考

### 0.1 业务现状的痛点

当前所谓"AI Agent"只是 `provider + apikey + system_prompt + user_prompt` 的 LLM 调用链——这是 2024 年的玩具，不是 agent。用户的真实诉求（2026 年范式）：

- **Agent 是岗位主体**（理解+编排）：理解业务意图、生成规则、写 SQL/脚本草案、调用工具试运行、解释差异、维护 skill。
- **Skill 是手艺**（确定性执行）：解析银行流水、读写 Excel、跑 DuckDB SQL、生成报表、导出文件。
- **Agent 负责"编排和理解"，工具/Skill 负责"确定性执行"。**

### 0.2 参考项目（已调研）

| 项目 | 作者 / Stars | 价值 |
|---|---|---|
| **CheetahClaws (nano-claude-code)** | SafeRL-Lab / ~40K 行 Python | **首选参考**——多模型支持（Ollama/Claude/GPT/Qwen/智谱），完整 Agent/Tool/Skill/Plugin/MCP 体系，源码可读 |
| claude-code-python-rewrite | TeeWhyKay / 50K stars 2 小时 | Clean-room Python 重写，src/ 目录组织清晰 |
| claw-code | instructkr / 100K stars | 韩国作者首发，事件起点，现转 Rust |

**采纳**：以 CheetahClaws 为蓝本，按账房先生场景做减法和定制化。

### 0.3 关键设计决策（直接照搬经验证的范式）

1. **Agent loop = Python generator 流式事件**——`yield TextChunk / ToolStart / ToolEnd / TurnDone`，前端 SSE 实时渲染
2. **Tool 注册 = `ToolDef` dataclass + 装饰器**——schema 从 Python 函数签名 + docstring 自动推断
3. **Skill 用 manifest.yaml + run.py + tests/**（不是写死 Python 代码）——用户/AI 都可创建
4. **Subagent 用工作区目录隔离**
5. **Memory 双 scope**（agent + project）+ recency-weighted search
6. **Session 持久化** 用 daily/YYYY-MM-DD/ + history.json + latest.json
7. **Permission gating** 在 tool 执行前——白名单 + 危险操作弹窗
8. **Provider abstraction**——本地 Ollama 优先，云端可选

---

## 1. 用户视角的产品形态（方案 B）

### 1.1 左侧导航变化

**改造前**（当前现状）：

```
🤖 AI智能体 ▾
   规则agent           ← 占位符，无功能
   日报agent           ← 占位符
   费用agent           ← 占位符
   收入agent           ← 占位符
   材料agent           ← 占位符
   工资、税费agent      ← 占位符
   自定义agent         ← 占位符
```

**改造后**（方案 B：完全动态）：

```
🤖 AI智能体 ▾
   财务总监            ← 用户建的，点击进聊天
   出纳助手            ← 用户建的
   报表分析师          ← 用户建的
   ...                ← 任意多个
   ＋ 新建 agent       ← 固定在末尾，弹窗创建
```

**取消所有 7 个预设占位符**。导航里展示的就是用户当前已建的所有 active agent，按 `created_at` 倒序或用户拖拽排序。

### 1.2 用户能做的事

| 操作 | 入口 | 结果 |
|---|---|---|
| 新建 agent | 左导航 "+ 新建 agent" 或 `/agents` 列表页"新建"按钮 | 弹窗填名字/岗位职责/选模型 → 保存 → 立即出现在左导航 |
| 进入 agent | 左导航点该 agent 名 | 进入聊天界面，恢复最近一次会话或开新会话 |
| 改 agent 设置 | agent 详情页"设置"标签 | 改名字/岗位职责/模型/权限 |
| 看 agent 已学技能 | agent 详情页"技能"标签 | skill 列表，每个可手动跑测试或运行 |
| 看 agent 工作区 | agent 详情页"文件"标签 | 工作区目录树，可上传/下载/删除文件 |
| 看 agent 记忆 | agent 详情页"记忆"标签 | 长期记忆 .md 文件列表，可手编 |
| 看历史会话 | agent 详情页"会话"标签 | 会话列表 + 可恢复任一历史会话继续聊 |
| 删除 agent | 左导航右键 / 列表页"删除" | 二次确认 → 标记 status=deleted → 左导航消失 |

---

## 2. 总体架构

```
┌────────────────────────────────────────────────────────────────────────┐
│  前端：Vue 3 SPA                                                       │
│  ├─ MainLayout.vue 导航：「AI智能体」改为动态从 /api/agent_v2/agents 拉  │
│  ├─ /agents              我的 agent 列表 + 新建/编辑/删除               │
│  ├─ /agents/:id          agent 详情，标签：聊天/设置/技能/文件/记忆/会话 │
│  ├─ /agents/:id/chat/:sid  聊天界面（默认 sid=latest）                  │
│  └─ SSE 流式接收 TextChunk/ToolStart/ToolEnd/TurnDone                  │
└────────────────────────┬───────────────────────────────────────────────┘
                         │ HTTP + SSE
┌────────────────────────▼───────────────────────────────────────────────┐
│  后端：FastAPI                                                         │
│  ├─ api/agent_v2.py     ★ 新路由（CRUD agent / 聊天 SSE / skill / 文件）│
│  ├─ agents_v2/          ★ 新模块                                       │
│  │   ├─ runtime.py       Agent loop（generator 流式）                  │
│  │   ├─ provider.py      Provider 抽象（复用现有 core/ai_call.py）     │
│  │   ├─ tool_registry.py ToolDef + register_tool 装饰器               │
│  │   ├─ tools/                                                         │
│  │   │   ├─ fs.py          read/write/list/edit                        │
│  │   │   ├─ shell.py       bash（白名单 + 沙箱）                      │
│  │   │   ├─ python_run.py  python.exec（沙箱）                         │
│  │   │   ├─ duckdb_q.py    duckdb 查询                                 │
│  │   │   ├─ openpyxl_io.py 读写 Excel                                  │
│  │   │   ├─ db_read.py     业务 DB 只读查询                            │
│  │   │   ├─ memory.py      记忆 save/recall/search                     │
│  │   │   ├─ skill_ops.py   skill create/update/test/list/run           │
│  │   │   ├─ task.py        task 管理                                   │
│  │   │   └─ ask_user.py    向用户提问                                  │
│  │   ├─ skill_loader.py   skill 加载 + 执行                            │
│  │   ├─ memory_store.py   记忆持久化                                   │
│  │   ├─ session_store.py  会话历史                                     │
│  │   ├─ permission.py     权限网关                                     │
│  │   └─ workspace.py      工作区文件系统隔离                           │
│  └─ db/tables.py 新增：Agent/Skill/AgentSession/AgentMessage/...       │
└────────────────────────┬───────────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────────────┐
│  存储                                                                   │
│  ├─ SQLite：agents_v2/skills_v2/sessions/messages/runs/memories       │
│  └─ data/agents/{agent_code}/                                          │
│      ├─ workspace/      用户工作区（读写）                              │
│      ├─ skills/         此 agent 的 skill                               │
│      ├─ memory/         长期记忆 .md                                    │
│      └─ sessions/       会话日志（按日期）                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 数据模型

### 3.1 SQLite 新增 6 张表

```sql
CREATE TABLE agents_v2 (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_code      VARCHAR(50)  NOT NULL UNIQUE,    -- 系统生成（ag_a3f2b9）
  display_name    VARCHAR(100) NOT NULL,           -- ★ 用户中文名（"财务总监"）
  role_prompt     TEXT         NOT NULL,           -- 岗位职责（system prompt）
  ai_config_id    INTEGER      REFERENCES ai_configs(id),
  workspace_path  VARCHAR(500) NOT NULL,
  permission_json TEXT         NOT NULL,           -- 工具白名单 + 路径白名单
  status          VARCHAR(20)  NOT NULL DEFAULT 'active',  -- active / deleted
  sort_order      INTEGER      NOT NULL DEFAULT 0,         -- 用户拖拽排序
  created_by      VARCHAR(50),
  created_at      DATETIME     NOT NULL DEFAULT (datetime('now')),
  updated_at      DATETIME     NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE skills_v2 (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_code      VARCHAR(80)  NOT NULL UNIQUE,
  display_name    VARCHAR(150) NOT NULL,
  description     TEXT,
  owner_agent_id  INTEGER      REFERENCES agents_v2(id),  -- NULL = 全局
  manifest_json   TEXT         NOT NULL,
  source_path     VARCHAR(500) NOT NULL,
  status          VARCHAR(20)  NOT NULL DEFAULT 'draft',  -- draft / verified / disabled
  verified_at     DATETIME,
  test_pass_count INTEGER      NOT NULL DEFAULT 0,
  test_fail_count INTEGER      NOT NULL DEFAULT 0,
  created_at      DATETIME     NOT NULL DEFAULT (datetime('now')),
  updated_at      DATETIME     NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE agent_sessions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id        INTEGER      NOT NULL REFERENCES agents_v2(id),
  title           VARCHAR(200),
  context_summary TEXT,
  status          VARCHAR(20)  NOT NULL DEFAULT 'active',
  created_at      DATETIME     NOT NULL DEFAULT (datetime('now')),
  last_active_at  DATETIME     NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE agent_messages (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id       INTEGER     NOT NULL REFERENCES agent_sessions(id),
  role             VARCHAR(20) NOT NULL,           -- user / assistant / tool / system
  content          TEXT,
  tool_call_json   TEXT,
  tool_result_json TEXT,
  duration_ms      INTEGER,
  created_at       DATETIME    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE agent_runs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_id     INTEGER REFERENCES skills_v2(id),
  agent_id     INTEGER REFERENCES agents_v2(id),
  session_id   INTEGER REFERENCES agent_sessions(id),
  inputs_json  TEXT,
  outputs_json TEXT,
  logs         TEXT,
  status       VARCHAR(20) NOT NULL,
  duration_ms  INTEGER,
  created_at   DATETIME    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE agent_memories (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id     INTEGER     NOT NULL REFERENCES agents_v2(id),
  key          VARCHAR(200) NOT NULL,
  content      TEXT         NOT NULL,
  scope        VARCHAR(30)  NOT NULL DEFAULT 'agent',  -- agent / project
  confidence   REAL         NOT NULL DEFAULT 1.0,
  source       VARCHAR(50),
  created_at   DATETIME     NOT NULL DEFAULT (datetime('now')),
  last_used_at DATETIME     NOT NULL DEFAULT (datetime('now'))
);
```

### 3.2 工作区目录

```
data/agents/{agent_code}/
├── workspace/
│   ├── inbox/                 用户上传文件
│   ├── outputs/               agent 生成文件
│   └── tmp/
├── skills/
│   └── {skill_code}/
│       ├── manifest.yaml
│       ├── run.py
│       └── tests/
├── memory/
│   ├── domain.md
│   └── patterns.md
└── sessions/
    ├── 2026-04-27/ses_xxx.jsonl
    └── latest.json
```

---

## 4. 核心组件

### 4.1 Agent Loop（runtime.py）

```python
async def run_turn(agent, session, user_text):
    """单轮对话→多次 tool 循环→返回最终回复。

    yield 事件：
      TextChunk(text)         流式文本
      ToolStart(name, args)   开始执行工具
      ToolEnd(name, result)   工具完成
      TurnDone(stop_reason)   本轮结束
    """
    messages = load_recent_messages(session)
    messages.append({"role": "user", "content": user_text})
    turn = 0
    MAX_TURNS = 20

    while turn < MAX_TURNS:
        turn += 1
        async for chunk in provider.stream_chat(
            system=build_system_prompt(agent),
            messages=messages,
            tools=registered_tools(agent),
        ):
            if chunk.type == "text":
                yield TextChunk(chunk.text)
            elif chunk.type == "tool_call":
                tool_call = chunk.tool_call
                break

        if not tool_call:
            yield TurnDone("end_turn")
            return

        if not permission.check(agent, tool_call):
            result = {"ok": False, "error": "权限拒绝"}
        else:
            yield ToolStart(tool_call.name, tool_call.args)
            result = await execute_tool(tool_call, ToolCtx(agent, session))
            yield ToolEnd(tool_call.name, result)

        messages.append({"role": "assistant", "tool_call": tool_call})
        messages.append({"role": "tool", "result": result})

    yield TurnDone("max_turns_reached")
```

### 4.2 Tool 注册（tool_registry.py）

```python
@dataclass
class ToolDef:
    name: str
    description: str
    input_schema: dict
    func: Callable
    read_only: bool
    concurrent_safe: bool

_TOOLS: dict[str, ToolDef] = {}

def register_tool(read_only=False, concurrent_safe=False):
    def deco(func):
        _TOOLS[func.__name__] = ToolDef(
            name=func.__name__,
            description=(func.__doc__ or "").strip(),
            input_schema=infer_schema_from_signature(func),
            func=func,
            read_only=read_only,
            concurrent_safe=concurrent_safe,
        )
        return func
    return deco

@register_tool(read_only=True)
def fs_read(path: str) -> str:
    """读取工作区文件内容（仅当前 agent 工作区内）。"""
    ...
```

### 4.3 Skill 形态

`data/agents/{agent_code}/skills/{skill_code}/manifest.yaml`

```yaml
name: parse_zhaoshang_bank_flow
display_name: 招商银行流水解析
description: |
  解析招商银行导出的 xls/xlsx 流水，识别 12 个标准列，
  规范化日期/金额，输出 fund_event 标准行列表。
inputs:
  - name: file_path
    type: str
  - name: account_id
    type: int
outputs:
  - name: rows
    type: list
  - name: skipped_rows
    type: list
dependencies: [openpyxl, polars]
verified_with: [tests/sample_zhaoshang.xlsx]
runtime:
  timeout_ms: 30000
  memory_mb: 256
created_by: agent      # agent 或 user
```

### 4.4 Permission（permission.py）

默认 `permission_json`：

```json
{
  "allowed_tools": [
    "fs_read", "fs_list", "duckdb_query", "openpyxl_read",
    "db_query_business", "memory_save", "memory_search",
    "skill_list", "skill_run", "task_create", "task_update",
    "task_list", "ask_user"
  ],
  "allowed_paths": [
    "data/agents/{this_agent}/workspace",
    "data/agents/{this_agent}/skills"
  ],
  "allowed_shell": [],
  "needs_user_confirm": [
    "fs_write", "fs_edit", "python_exec", "skill_create"
  ]
}
```

### 4.5 内置工具清单（Phase 1-2 上 13 个）

| 工具 | 类别 | 默认权限 |
|---|---|---|
| fs_read / fs_list | 文件 | read_only |
| fs_write / fs_edit | 文件 | 需用户确认 |
| openpyxl_read | Excel | read_only |
| openpyxl_write | Excel | 需用户确认 |
| duckdb_query | SQL | read_only |
| db_query_business | DB | read_only（fund_events / accounts / report_templates 等只读） |
| memory_save / memory_search | 记忆 | read_only |
| skill_list / skill_run | skill | read_only |
| skill_create / skill_test | skill | 需用户确认 |
| task_create / task_update / task_list | 计划 | read_only |
| ask_user | 交互 | 特殊（弹窗） |
| python_exec | 代码 | 需用户确认 |
| bash_run | shell | 需用户确认（白名单 ls/cat/wc） |

---

## 5. 前端集成方案

### 5.1 改造 MainLayout 左侧导航

**文件**：`frontend/src/layouts/MainLayout.vue`

把 `'AI智能体'` 这个分组的 `.tabs[]` 数组**改为响应式**——从 `pinia store` 拉取，store 在 mount 时调 `GET /api/agent_v2/agents` 拉列表。

```js
// stores/agents.js
import { defineStore } from 'pinia'
import http from '@/api'

export const useAgentsStore = defineStore('agents', {
  state: () => ({ list: [] }),
  actions: {
    async fetchAll() {
      this.list = await http.get('/agent_v2/agents') || []
    }
  }
})
```

`MainLayout.vue` 渲染时：

```js
const agentsStore = useAgentsStore()
onMounted(() => agentsStore.fetchAll())

// computed: AI智能体 group 的 tabs
const aiAgentTabs = computed(() => {
  const items = agentsStore.list.map(a => ({
    name: a.display_name,
    explain: a.role_prompt?.slice(0, 30) || '',
    route: { name: 'agent-chat', params: { id: a.id } },
  }))
  items.push({
    name: '＋ 新建 agent',
    explain: '创建一个新的 AI 智能体',
    route: 'agent-new',
    isAction: true,
  })
  return items
})
```

### 5.2 路由

```
/agents                  我的 agent 列表 + 新建按钮
/agents/new              触发新建弹窗（不真正跳页，弹窗形式）
/agents/:id              agent 详情，默认聊天 tab
/agents/:id/settings     设置 tab
/agents/:id/skills       技能 tab
/agents/:id/skills/:scode 技能详情
/agents/:id/files        工作区文件 tab
/agents/:id/memory       记忆 tab
/agents/:id/sessions     会话历史 tab
/agents/:id/chat/:sid    指定会话恢复
```

### 5.3 聊天界面布局

```
┌──────────────────────────────────────────────────────────────────┐
│ [财务总监]   ▼会话切换   [+ 新会话]   设置 | 技能 | 文件 | 记忆     │
├────────────────────────────────────┬─────────────────────────────┤
│ 消息流                              │ 工作区文件树                 │
│ 👤 用户：把今年 3 月招行流水解析了   │ 📁 inbox/                   │
│                                    │   📄 招行2603.xls           │
│ 🤖 收到，先看下文件...             │ 📁 outputs/                 │
│ 🔧 fs_read(招行2603.xls)          │                             │
│    ↳ 读取 16 行                   │ [📤 上传文件]                │
│ 🔧 skill_run(parse_zhaoshang)    │                             │
│    ↳ 解析出 12 行 fund_event     │                             │
│ 🤖 已写入业务库...                │                             │
├────────────────────────────────────┴─────────────────────────────┤
│ [输入框]                                  [📎 引用文件] [🚀 发送]  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.4 SSE 流式渲染

后端 `POST /api/agent_v2/sessions/:sid/messages` 返回 `text/event-stream`：

```
event: text
data: {"text": "正在读取文件"}

event: tool_start
data: {"name": "fs_read", "args": {"path": "招行2603.xls"}}

event: tool_end
data: {"name": "fs_read", "result": {"ok": true, "preview": "..."}}

event: text
data: {"text": "解析完成，共 16 行..."}

event: done
data: {"stop_reason": "end_turn"}
```

前端用原生 `EventSource` 接收 → 按事件类型分别渲染。

---

## 6. 分阶段开发计划与验收

### Phase 1 — agent 列表 + 新建/删除 + 简单对话（5 天）

#### 任务

后端：
- DB 新增 6 张表 + alembic 迁移
- `agents_v2/runtime.py` agent loop 雏形
- `agents_v2/provider.py` 适配 ollama（复用 core/ai_call.py 流式接口）
- `agents_v2/tool_registry.py` 注册装饰器
- 4 个最小工具：`fs_list / memory_save / memory_search / ask_user`
- `agents_v2/permission.py` 权限网关
- `api/agent_v2.py` 路由：CRUD agent + 创建 session + 发消息（SSE）
- 创建 agent 时自动建 `data/agents/{code}/workspace|skills|memory|sessions/`

前端：
- 取消 MainLayout 中"AI智能体"下 7 个占位符
- 改为从 `useAgentsStore.list` 动态渲染 + 末尾固定一个"+ 新建 agent"
- 新建弹窗组件（中文名 / 岗位职责 / 选 AI 配置）
- `/agents/:id` 页面（标签页结构，但只先做"聊天"和"设置"两个 tab）
- 聊天组件：消息流 + SSE 渲染 + 输入框
- 设置 tab：改名字 / 改 role_prompt / 改 model / 删除按钮

#### 验收（用户视角）

1. 用户登录后点左侧"AI智能体"展开 → 看到的不再是 7 个占位符，而是空的 + 一个"+ 新建 agent"
2. 点"+ 新建 agent" → 弹窗：填名字"财务总监" + 岗位职责自由文字 + 下拉选 ollama qwen3:8b → 保存
3. 左导航**立即出现**"财务总监"（无需刷新）
4. 点"财务总监" → 进入聊天界面，标题显示 "财务总监"
5. 输入框打字"你好,你是谁" → 回车发送
6. 看到流式回复（基于岗位职责的 AI 回答）
7. 点页面右上角"设置"tab → 看到当前名字/岗位职责/模型，可改可保存
8. 点"删除"按钮 → 二次确认弹窗 → 确认 → 左导航"财务总监"消失

**技术验收**：
- 所有 6 条用户操作在 Chrome 中点出来不报错
- 后端 6 张表全部建好，agent_messages 表有该会话的消息记录
- `data/agents/{ag_xxx}/` 目录自动创建
- 单元测试：runtime / tool_registry / permission 三个模块覆盖率 ≥ 80%

---

### Phase 2 — 工作区文件 + 第一个真实技能（4 天）

#### 任务

后端：
- 工具补全：`fs_read / fs_write / fs_edit / openpyxl_read / openpyxl_write / db_query_business / duckdb_query / python_exec / bash_run`
- `agents_v2/skill_loader.py` 从 manifest.yaml + run.py 加载执行
- 4 个 skill 工具：`skill_list / skill_run / skill_test / skill_create`
- 内置 skill：`parse_bank_zhaoshang/`（移植 worktree 的 bank_parser.py）
- 文件上传 API：`POST /api/agent_v2/agents/:id/files` → 写入 `workspace/inbox/`

前端：
- agent 详情页加 3 个 tab："技能" / "文件" / "会话"
- 聊天页右侧加文件树组件 + 上传按钮
- 工具调用块组件：默认折叠，点开看完整 JSON；error 红色、ok 绿色
- 技能 tab：list 表格（display_name / status / 验证次数 / 上次跑耗时）+ 每行"运行"和"测试"按钮

#### 验收（用户视角）

1. 进入"财务总监"聊天 → 右侧文件区点上传 → 选 `招行.xlsx` → 上传完文件树立即显示
2. 在聊天里说"用招行解析技能把刚上传的文件解析了"
3. 看到 AI 流式回复 → 工具调用块"skill_run(parse_bank_zhaoshang)" 折叠状态显示"运行中..."
4. 几秒后块变绿 → 点开看到 "解析了 16 行 fund_event"
5. AI 接着说"是否写入业务库?"→ 用户回复"写入" → 工具调用 db_query_business 写入 fund_events
6. 切到"基础数据表"业务页面 → 看到刚才写入的 16 行流水数据

7. 进入 agent 详情"技能"tab → 看到列表里有 `招商银行流水解析`，状态 verified
8. 点该 skill 的"测试"按钮 → 跑 tests/ 下样本 → 显示通过

**技术验收**：
- 前端工具调用块 UI 流畅折叠/展开，不阻塞输入
- 端到端延迟（本地 ollama qwen3:8b，1 次 tool call）< 10 秒
- 上传 100KB Excel 文件 < 1 秒

---

### Phase 3 — AI 自创建技能（5 天）

#### 任务

后端：
- `skill_create` 工具：agent 调用时传 name + description + run.py 字符串 + tests，自动落盘 + 入库 status=draft
- `skill_test` 工具：跑 tests/ 下所有样本 → 比对 expected.json → 返回 pass/fail + diff
- AI 编写 skill 的标准 prompt 模板（写在 system prompt 里）

前端：
- agent 详情"技能"tab 加"教 agent 学新手艺"按钮 → 弹窗引导：上传 1-2 个样本 + 简短描述目标
- skill 详情页：源码查看（只读 + 高亮）/ 测试结果表 / 手动跑一次按钮

#### 验收（用户视角）

完整对话流：
1. 进"财务总监"聊天，点"教 agent 学新手艺"
2. 弹窗：上传 `中行银行流水.xls` 样本 + 描述"识别中行的字段，输出标准 fund_event 行"
3. agent 在聊天里：
   - 用 fs_read + openpyxl_read 看样本结构
   - 识别表头与字段映射
   - 起草 run.py 草案 + 一份 expected.json
   - 调 skill_test 验证 → 失败则迭代修改
   - 通过后调 skill_create 落盘
4. agent 在聊天里说"已学完，技能名: 中行流水解析，已通过测试"
5. 切到"技能"tab → 看到列表多了"中行流水解析"，状态 verified
6. 上传一个**不同月份**的中行流水 → 在聊天里说"用中行解析技能跑一下" → 一次成功不再走 LLM 起草

#### 验收

- 一次完整对话流能成功学出 1 个技能
- 学完后第二次调用纯粹是 skill_run，不再调 LLM 起草代码
- skill_test 的 diff 输出友好（不是裸 JSON）

---

### Phase 4 — 业务场景闭环（4 天）

#### 任务

- 给新建 agent 时提供"快速模板"下拉：
  - 出纳助手（预填 role_prompt + 自带 3 个 skill：解析模板/解析报表模板/生成报表）
  - 报表分析师
  - 自定义（空白）
- `gen_report` skill：从 fund_events 取数 → 按 layout 写入 → 导出 .xlsx（不走 LLM）
- 业务页面"生成报表"按钮调对应 agent 的 gen_report skill

#### 验收

完整业务闭环：
1. 用快速模板"出纳助手"建一个 agent
2. 上传招行/中行流水 → agent 自动解析进 fund_events
3. 切到"现金日记账"业务页面 → 点"生成报表" → 调 agent skill_run → 下载到的 .xlsx 与原模板格式一致
4. 性能：1000 行 fund_events + 现金日记账模板 → 报表生成 < 3 秒
5. 幂等：同输入跑 5 次输出 100% 一致

---

## 7. 技术栈与依赖

| 层 | 选择 | 理由 |
|---|---|---|
| 后端框架 | FastAPI（已有）| 同栈 |
| ORM | SQLAlchemy（已有）| 同栈 |
| LLM client | 复用 `core/ai_call.py` + 加流式 | 已支持 8 provider |
| 流式协议 | SSE | 单向、轻、原生 EventSource 即可消费 |
| Excel | openpyxl + xlrd | xls 兼容已实现 |
| SQL on data | DuckDB | 嵌入式、零依赖 |
| DataFrame | Polars | 已在 requirements |
| Sandbox | subprocess + resource limits + 临时 cwd | 不引 Docker |
| YAML | PyYAML | 新增（skill manifest）|
| 前端 | Vue 3 + Vite + Pinia | 已有 |
| SSE 前端 | EventSource 原生 | 不引第三方 |

---

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| LLM 在 tool 循环中失控（无限调用）| MAX_TURNS=20 硬上限；tool_call 超时 60s |
| 用户/AI 写的 skill 含恶意代码 | python_exec 默认 read_only fs + cpu/memory 限制；高危默认禁用 |
| 长会话上下文爆炸 | 50 条 message 触发 summarize；context_summary 替换早期消息 |
| Ollama JSON 不稳定 | LLMStep 已有 max_retries + JSON repair；可用 `<tool>...</tool>` 兜底 |
| Windows 中文路径 | 复用 excel_compat 经验；新工具一律 `Path(...).resolve()` |
| 删除 agent 后导航不刷新 | pinia store + 删除后调 `agentsStore.fetchAll()` |
| skill 改动后业务页面不感知 | 已有 onActivated + axios cache-buster 经验，复用 |

---

## 9. 不在本阶段做（明确划界）

- **不做**：MCP 服务器对接（Phase 5+）
- **不做**：多 agent orchestration / Task subagent（Phase 6+）
- **不做**：语音 / 图片输入
- **不做**：Docker 沙箱（subprocess + resource limits 够）
- **不做**：大规模并行任务/Job 队列

---

## 10. 验收里程碑表

| Phase | 时长 | 用户能看到的最小可见效果 |
|---|---|---|
| 1 | 5d | 在浏览器里建第一个 "财务总监" agent，能聊天 |
| 2 | 4d | 上传招行流水，agent 调技能解析进业务库 |
| 3 | 5d | 教 agent 学中行流水，自动学成可复用技能 |
| 4 | 4d | 完整业务闭环：上传流水 → 解析 → 生成报表 |
| **合计** | **18d** | |

---

## 11. 参考源码定位（开发时按需直接读）

- **CheetahClaws** [`agent.py`](https://github.com/SafeRL-Lab/nano-claude-code/blob/main/agent.py)（174 行，agent loop 范本）
- **CheetahClaws** providers.py（多 provider 抽象）
- **CheetahClaws** tool_registry.py（工具注册）
- **CheetahClaws** skill/（skill 系统）
- **TeeWhyKay/claude-code-python-rewrite** src/（清晰目录组织参考）

---

## 12. 智能体外部调用（Round 11 补充）

### 12.1 调用场景

Agent V2 智能体不仅限于聊天界面交互，还可在以下业务场景中被直接调用：

| 场景 | 入口 | 说明 |
|---|---|---|
| **银行流水 AI 解析** | `POST /api/bank-import/ai-parse` | 用户选择智能体 → 上传流水 → AI 分析列映射 |
| **手工流水 AI 解析** | `POST /api/manual-flow/ai-parse` | 用户选择智能体 → 上传 Excel → AI 分析列映射 |
| **规则模板自动保存** | `commit_by_mapping` 自动触发 | 提交后自动保存确认的映射为规则模板 |

### 12.2 调用机制

外部调用不走 Agent Loop（不需要 SSE/多轮对话），而是直接使用智能体的 `ai_config` 和 `role_prompt` 进行一次性 LLM 调用：

```python
# bank_import_service.py / manual_flow_service.py
agent = db.query(AgentV2).filter(AgentV2.id == agent_id, AgentV2.status == "active").first()
result = chat(
    provider=agent.ai_config.provider,
    api_key=decrypt_key(agent.ai_config.api_key_local),
    messages=[
        {"role": "system", "content": agent.role_prompt + "【任务模式】"},
        {"role": "user", "content": "请分析以下表头列名..."},
    ],
)
```

### 12.3 前端智能体选择器

在需要调用智能体的页面，提供统一的下拉选择器：

- **BankImport.vue** — 「调用智能体」下拉框（toolbar-row 区域）
- **ManualFlow.vue** — 「调用智能体」下拉框（filters-bar 区域）

选择器数据来源：`GET /api/agent_v2/agents`（返回所有 active 智能体列表）。

### 12.4 DeepSeek 推理模型兼容

DeepSeek V4 Flash 等思考模型在多轮对话中会返回 `reasoning_content` 字段，后续请求必须将其传回，否则返回 HTTP 400。

兼容方案：
1. `provider.py` 在流式 delta 中捕获 `reasoning_content`
2. `runtime.py` 在消息中保存和传递 `reasoning_content`
3. `session_store.py` 将 `reasoning_content` 持久化到 `agent_messages` 表
4. `_format_messages()` 在构建 LLM 上下文时包含 `reasoning_content`
