# 16 · Agent 系统开发文档

> 本文档是 Agent 系统的开发参考。描述代码结构、模块职责、关键流程、扩展方式。
> 配合 [19_ai_capability.md](../00_governance/19_ai_capability.md)（设计文档）和 [00_project_constitution.md](../00_governance/00_project_constitution.md) §C4 §C8 使用。

---

## §1 · 系统架构总览

Agent 系统采用 **单 Agent 实例 + 工具注册 + 技能匹配 + 记忆注入** 的架构模式。参考 Hermes Agent 的成熟设计，适配本项目的财务场景。

```
用户消息
  │
  ▼
┌─────────────────────────────────────────────────┐
│ PromptBuilder                                    │
│   ├─ Agent 身份（名称、角色、职责）                │
│   ├─ 记忆上下文（MemoryManager.build_system_prompt）│
│   ├─ 技能提示（SkillRegistry 匹配结果）            │
│   └─ 工具清单（ToolRegistry 注册的工具 schema）    │
│                                                   │
│ → 组装为 system prompt + messages                 │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ Provider（AI 适配层）                             │
│   ├─ stream_chat() → 流式 SSE 输出               │
│   ├─ 支持 OpenAI / DeepSeek / 其他兼容 Provider   │
│   └─ 处理 tool_calls / reasoning_content          │
└────────────────────┬────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
    文本响应              工具调用（tool_calls）
    → 直接输出            → ToolRegistry 分发
                              → 权限检查
                              → 执行工具
                              → 结果返回 LLM
                              → 继续循环
```

### 核心循环（runtime.py）

```python
# 伪代码
async def run_turn(agent, session_id, user_text, db):
    # 1. 保存用户消息
    save_message(db, session_id, "user", content=user_text)

    # 2. Curator 技能生命周期检查
    Curator(agent_code).maybe_run()

    # 3. 加载历史消息
    history = load_recent_messages(db, session_id)

    # 4. 记忆预加载
    memory_mgr = MemoryManager(DBMemoryProvider(agent, db))
    memory_mgr.prefetch(session_id, user_text)
    memory_block = memory_mgr.build_system_prompt()

    # 5. 技能匹配
    matched_skills = skill_registry.trigger(user_text)

    # 6. 构建系统提示词
    system_prompt = prompt_builder.build(agent, memory_block, skill_hints)

    # 7. 获取工具列表（受权限控制）
    tools = get_tools_for_llm(get_permission(agent.permission_json))

    # 8. 上下文压缩检查
    if context_engine.needs_compaction(messages):
        memory_mgr.on_pre_compress(messages)
        messages = context_engine.compact(session_id, messages)

    # 9. 流式 LLM 调用循环（最多 MAX_TURNS=40 轮）
    while turn < MAX_TURNS:
        async for chunk in stream_chat(...):
            if chunk.type == "text":
                yield sse_text(chunk.text)
            elif chunk.type == "tool_call":
                execute_and_continue()
            elif chunk.type == "done":
                break

    # 10. 记忆同步
    memory_mgr.sync_all(session_id, messages)
```

---

## §2 · 模块清单与职责

### §2.1 · 核心模块（backend/agents/）

| 模块 | 文件 | 职责 | 对标 Hermes |
|------|------|------|-------------|
| 运行时 | `runtime.py` | 核心对话循环、工具执行、错误恢复 | `run_agent.py` |
| 工作区 | `workspace.py` | Agent 文件系统隔离 | `file_safety.py` |
| 上下文引擎 | `context.py` | 三段压缩保护 | `context_engine.py` + `context_compressor.py` |
| 提示词构建 | `prompt_builder.py` | 系统提示词组装 | `prompt_builder.py` |
| 权限控制 | `permission.py` | 工具白名单控制 | `tools/registry.py` (toolset) |
| 工具注册 | `tool_registry.py` | 注册 + 分发工具调用 | `tools/registry.py` |
| 技能注册 | `skill_registry.py` | 技能发现 + 热加载 + 匹配 | `agent/skill_utils.py` |
| 技能创建 | `skill_creator.py` | LLM 驱动的技能生成 | `tools/skill_manager_tool.py` |
| 技能执行 | `skill_executor.py` | 技能指令格式化 + 注入 | `agent/skill_commands.py` |
| 会话存储 | `session_store.py` | 消息历史 CRUD | 内置 |
| 会话锁 | `session_lock.py` | 防止并发写入 | 内置 |
| 记忆存储 | `memory_store.py` | 记忆的数据库 CRUD | `tools/memory_tool.py` |
| 记忆提供者 | `memory_provider.py` / `db_memory_provider.py` | 记忆加载 + 注入 | `agent/memory_provider.py` |
| 记忆管理 | `memory_manager.py` | 记忆编排 + 同步 + 清洗 | `agent/memory_manager.py` |
| 上下文整理 | `curator.py` | 技能生命周期检查 | `agent/curator.py` |
| AI 适配 | `provider.py` | 多 Provider 流式调用 | `agent/transports/*` |
| SSE 输出 | `sse_helper.py` | 流式事件格式化 | `agent/display.py` |
| 提示词构建 | `prompt_builder.py` | 组装系统提示词 | `agent/prompt_builder.py` |

### §2.2 · 工具模块（backend/agents/tools/）

| 工具 | 文件 | 注册名 | 能力 |
|------|------|--------|------|
| 数据库查询 | `db_ops.py` | `db_query` | 数据库只读查询 |
| 数据库写入 | `db_ops.py` | `db_execute` | 数据库写入（受权限控制） |
| 文件列表 | `fs.py` | `file_list` | 列出工作区文件 |
| 文件读取 | `fs.py` | `file_read` | 读取文件内容 |
| 文件写入 | `fs.py` | `file_write` | 写入文件到工作区 |
| 文件解析 | `file_parse.py` | `file_parse` | 自动解析 PDF/DOCX/Excel/CSV |
| Excel 读取 | `openpyxl_ops.py` | `openpyxl_read` | 读取 Excel 结构 |
| Excel 写入 | `openpyxl_ops.py` | `openpyxl_write` | 生成 Excel 文件 |
| Shell 命令 | `shell_ops.py` | `shell_exec` | 受限 Shell 命令 |
| 记忆保存 | `memory.py` | `memory_save` | 保存长期记忆 |
| 记忆搜索 | `memory.py` | `memory_search` | 搜索相关记忆 |
| 技能创建 | `skill_ops.py` | `skill_create` | 创建新技能 |
| 技能列表 | `skill_ops.py` | `skill_list` | 列出可用技能 |
| 询问用户 | `ask_user.py` | `ask_user` | 请求用户确认 |

### ~~§2.3 · 旧 FundAgent 模块（已删除）~~

> `backend/agents/fund/` 已在 Phase 5（2026-05-11）全部删除。可复用逻辑已迁移到 `backend/services/`。`backend/fund/` 是产物确定性执行基础设施，保留。

| 模块 | 状态 |
|------|------|
| `harness.py` | ~~Phase 5 已删除~~ |
| `schemas.py` | ~~Phase 3 迁移 → Phase 5 已删除~~ |
| `memory.py` | ~~Phase 3 迁移 → Phase 5 已删除~~ |
| `skills/*.py` | ~~Phase 5 已删除~~ |

---

## §3 · 关键流程详解

### §3.1 · 工具注册与调用

**注册**（模块加载时自动注册）：

```python
# tools/db_ops.py
import agents.tools  # 触发 __init__.py 中的批量注册

def register():
    tool_registry.register("db_query", schema={...}, handler=db_query)
    tool_registry.register("db_execute", schema={...}, handler=db_execute)
```

**调用**（runtime.py 中的循环）：

```python
for tc in tool_calls:
    tool_name = tc["name"]
    tool_args = tc["arguments"]

    # 权限检查
    if not is_tool_allowed(permission, tool_name):
        result = {"ok": False, "error": f"工具 '{tool_name}' 未被允许"}
    else:
        # 构建上下文
        ctx = ToolContext(agent_id, agent_code, session_id, db)
        result = await execute_tool(tool_name, tool_args, ctx)

    # 结果返回 LLM 继续循环
    messages.append({"role": "tool", "content": json.dumps(result)})
```

### §3.2 · 技能生命周期

```
创建 → 发现 → 匹配 → 注入 → 执行 → 维护
  │       │       │       │       │       │
  │       │       │       │       │       └─ Curator 定期检查技能质量
  │       │       │       │       └─ Agent 按技能指令工作
  │       │       │       └─ 匹配到的技能指令注入 system prompt
  │       │       └─ 用户消息触发 skill_registry.trigger()
  │       └─ SkillRegistry 扫描 skills/ 目录读取 SKILL.md
  └─ skill_creator.py 生成标准 SKILL.md
```

**技能文件格式**：

```yaml
---
name: parse_bank_boc
description: "中国银行流水专用解析"
when_to_use: "当用户上传中国银行流水时"
allowed-tools:
  - openpyxl_read
  - file_list
  - file_read
arguments:
  file_path:
    description: "中行流水文件路径"
    required: true
---

# 中国银行流水解析

## 工作流程
1. 接收 file_path 参数，判断文件格式
2. 读取 Excel 或 CSV，提取全部非空行
3. 返回结构化结果

## 规则
- 仅处理中国银行流水格式
- 空行跳过
- 编码统一 utf-8-sig
```

### §3.3 · 记忆系统流程

```
┌───────────────────────────────────────────────────┐
│ MemoryManager                                      │
│                                                    │
│  初始化时：                                          │
│    provider = DBMemoryProvider()                   │
│    provider.initialize(agent_code, agent_id, db)   │
│                                                    │
│  每轮对话前：                                        │
│    prefetch_with_query(session_id, user_message)   │
│    → 根据用户消息预加载相关记忆                        │
│    build_system_prompt()                           │
│    → 构建记忆提示块，注入 system prompt               │
│                                                    │
│  每轮对话后：                                        │
│    sync_all(session_id, messages)                  │
│    → 将本轮关键信息同步到记忆存储                       │
│                                                    │
│  上下文压缩前：                                      │
│    on_pre_compress(messages)                       │
│    → 从即将丢弃的消息中提取重要信息                     │
└───────────────────────────────────────────────────┘
```

**记忆清洗**（StreamingContextScrubber）：

Agent 响应中可能包含 `<memory-context>` 标签（记忆上下文），需要清洗掉后再返回给用户。`memory_manager.py` 中的 Scrubber 实现了流式清洗，防止记忆泄露到前端。

### §3.4 · 上下文压缩

```python
# context.py — 三段保护
def needs_compaction(messages):
    """检查是否需要压缩"""
    # 计算 token 数，超过阈值则压缩

def compact(session_id, messages):
    """执行压缩"""
    # 保留前 N 条（系统提示 + 身份）
    # 保留后 N 条（最近对话）
    # 中间部分摘要压缩
    return CompactResult(messages=new_messages, removed_count=N)
```

---

## §4 · 数据库表结构

### §4.1 · Agent 实例表（agents_v2）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| agent_code | VARCHAR(50) UNIQUE | Agent 唯一编码（如 ag_fe4xf2） |
| name | VARCHAR(100) | 显示名称 |
| description | TEXT | Agent 职责描述 |
| personality | TEXT | 人格设定（系统提示词的一部分） |
| ai_config_id | INTEGER FK | 关联的 AI 配置 |
| permission_json | TEXT | 工具权限 JSON |
| llm_timeout | INTEGER | LLM 调用超时（秒） |
| llm_max_tokens | INTEGER | 最大输出 token 数 |
| created_at / updated_at | DATETIME | 时间戳 |

### §4.2 · 会话表（agent_sessions）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| agent_id | INTEGER FK | 关联 Agent |
| title | VARCHAR(200) | 会话标题 |
| created_at | DATETIME | 创建时间 |

### §4.3 · 消息表（agent_messages）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| session_id | INTEGER FK | 关联会话 |
| role | VARCHAR(20) | user / assistant / tool |
| content | TEXT | 消息内容 |
| tool_call_json | TEXT | 工具调用 JSON（assistant 消息） |
| tool_result_json | TEXT | 工具返回 JSON（tool 消息） |
| reasoning_content | TEXT | 推理内容（思维链） |
| duration_ms | INTEGER | 响应耗时 |

### §4.4 · 记忆表（agent_memories）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| agent_id | INTEGER FK | 关联 Agent |
| session_id | INTEGER FK | 关联会话 |
| content | TEXT | 记忆内容 |
| category | VARCHAR(50) | 分类（preference / fact / skill / correction） |
| importance | REAL | 重要度（0-1） |
| created_at | DATETIME | 创建时间 |

### §4.5 · 技能表（skills_v2）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| skill_code | VARCHAR(100) UNIQUE | 技能编码 |
| display_name | VARCHAR(200) | 显示名称 |
| description | TEXT | 技能描述 |
| owner_agent_id | INTEGER FK | 所属 Agent（NULL=全局） |
| manifest_json | TEXT | 完整 manifest JSON |
| source_path | VARCHAR(500) | SKILL.md 文件路径 |
| status | VARCHAR(20) | verified / draft / archived |
| created_at / updated_at | DATETIME | 时间戳 |

---

## §5 · 扩展方式

### §5.1 · 添加新工具

1. 在 `backend/agents/tools/` 下创建新文件（如 `pdf_ops.py`）
2. 实现 `register()` 函数，调用 `tool_registry.register()`
3. 在 `backend/agents/tools/__init__.py` 中 import 新模块触发注册
4. 在 `backend/agents/permission.py` 中添加默认权限配置

```python
# tools/pdf_ops.py
from agents.tool_registry import tool_registry

def pdf_extract_text(args, ctx):
    """提取 PDF 文本"""
    file_path = args.get("file_path")
    # ... 实现
    return {"ok": True, "text": extracted_text}

def register():
    tool_registry.register(
        "pdf_extract",
        schema={
            "name": "pdf_extract",
            "description": "提取 PDF 文件文本内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "PDF 文件路径"}
                },
                "required": ["file_path"]
            }
        },
        handler=pdf_extract_text
    )

register()
```

### §5.2 · 添加新技能

**方式一**：用户在对话中要求 Agent 创建（推荐）

```
用户：帮我创建一个解析招商银行流水的技能
Agent → 调用 skill_creator → 生成 SKILL.md → 保存到 agents/{code}/skills/
```

**方式二**：手动创建

1. 在 `agents/system/skills/` 或 `agents/{agent_code}/skills/` 下创建目录
2. 编写 `SKILL.md`（frontmatter + body）
3. 启动时 `SkillRegistry.startup_scan()` 自动发现并注册

### §5.3 · 添加新 AI Provider

1. 在 `backend/core/ai_provider.py` 中添加 Provider 配置
2. 在 `backend/agents/provider.py` 的 `stream_chat()` 中添加适配逻辑
3. 前端 AI 配置页面会自动支持新 Provider

### §5.4 · 添加新 Agent 实例

通过 API `POST /api/agent_v2/agents` 创建，参数：

```json
{
  "name": "凭证助手",
  "description": "处理会计凭证相关任务",
  "personality": "你是一个专业的会计凭证助手...",
  "ai_config_id": 1,
  "permission_json": {"allowed_tools": ["db_query", "file_read", "file_parse"]}
}
```

系统自动创建：
- `agents/{agent_code}/` 目录
- `workspace/` 子目录
- `sessions/` 子目录
- `memory/` 子目录
- `skills/` 子目录

---

## §6 · 与 Hermes 的关键差异

| 维度 | Hermes | 账房先生 |
|------|--------|----------|
| 运行平台 | CLI + 多平台（Telegram/Discord/Web） | Web SPA（浏览器） |
| 用户 | 开发者/技术用户 | 财务人员（零编程） |
| 工具数量 | 60+（终端/浏览器/MCP/语音） | 14（数据库/文件/Excel/Shell/记忆/技能） |
| 技能管理 | skill_manage 工具 + Curator 自动维护 | skill_creator + SkillRegistry |
| 记忆 | MemoryProvider（可插拔，支持 Honcho/Mem0） | DBMemoryProvider（SQLite 内置） |
| 上下文 | ContextEngine（可插拔，支持 LCM） | ContextEngine（内置压缩） |
| 脚本编排 | 无 | 通用 Agent + artifact runtime 确定性执行 |
| 安全 | AST 扫描 + skills_guard + file_safety | AST 扫描（Parser/Rule） + permission.py |
| 对话输出 | 终端渲染 / Markdown / 平台适配 | SSE 流式 → 前端渲染 |

---

## §7 · 开发注意事项

### §7.1 · 不要做的事

- 不要在 `api/` 层写 Agent 逻辑——全部走 `agents/` 模块
- 不要让工具直接操作 `agents/` 以外的文件系统（走 workspace 隔离）
- 不要修改 `runtime.py` 的核心循环（最多调参数）
- 不要绕过 `permission.py` 的工具权限检查
- 不要在 Parser/Rule artifact 中引入白名单外的 import

### §7.2 · 调试技巧

- 查看某个 Agent 的对话：`SELECT * FROM agent_messages WHERE session_id = ? ORDER BY id`
- 查看技能匹配：`skill_registry.trigger(message_text)` 返回匹配列表
- 查看工具权限：`agent.permission_json` 中 `allowed_tools` 列表
- 查看记忆：`SELECT * FROM agent_memories WHERE agent_id = ?`
- SSE 流式调试：浏览器 F12 → Network → EventStream

---

**版本**
- v1.0 · 2026-05-02 · 首次发布，基于 Hermes/pi-mono/openclaw 架构分析 + 当前项目代码
