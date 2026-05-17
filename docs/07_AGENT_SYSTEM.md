# Agent 系统

## 架构：单通用 Agent

本项目只有一个通用 Agent（`backend/agents/runtime.py`）。不存在独立的 FundAgent、ReportAgent、ParserAgent、RuleAgent 等领域 Agent 类。

### 禁止事项

- 不允许新增领域专用 Agent 类来绕过通用 Agent 架构
- 不允许调用旧 `fund_skill_run`
- 不允许新增 `/api/fund/agent/skills/*/invoke` 路由

## 核心模块

| 模块 | 职责 |
|------|------|
| `runtime.py` | Agent 运行时：接收消息、调用 LLM、处理工具调用、流式输出 |
| `provider.py` | LLM Provider 适配（OpenAI 兼容协议） |
| `prompt_builder.py` | 系统 prompt 构建 |
| `context.py` | 上下文管理 |
| `tool_registry.py` | 工具注册 |
| `skill_registry.py` | 技能注册与发现 |
| `skill_loader.py` | 技能 manifest 加载 |
| `skill_executor.py` | 技能执行 |
| `memory_manager.py` | 记忆管理 |
| `memory_store.py` | 记忆存储接口 |
| `db_memory_provider.py` | 基于数据库的记忆提供者 |
| `permission.py` | Agent 权限管理 |
| `session_store.py` | 会话存储 |
| `session_lock.py` | 会话锁（防止并发冲突） |
| `curator.py` | 记忆整理 |
| `workspace.py` | 工作空间管理 |
| `sse_helper.py` | SSE 流式输出辅助 |

## 内置工具

| 工具 | 职责 |
|------|------|
| `ask_user.py` | 向用户提问 |
| `db_ops.py` | 数据库操作 |
| `file_parse.py` | 文件解析（PDF/DOCX/Excel/CSV） |
| `fs.py` | 文件系统操作 |
| `memory.py` | 记忆读写 |
| `openpyxl_ops.py` | Excel 操作 |
| `shell_ops.py` | Shell 命令执行 |
| `skill_ops.py` | 技能操作 |

## 数据模型

| 表 | 用途 |
|----|------|
| `agents_v2` | Agent 实例配置 |
| `agent_sessions` | 会话 |
| `agent_messages` | 消息（含 tool_call、tool_result、reasoning） |
| `agent_runs` | 技能运行记录 |
| `agent_memories` | 记忆 |
| `skills_v2` | 技能定义 |

## 工具确认与用户审核

- Agent 调用工具前可通过 `ask_user` 请求用户确认
- ParserArtifact / RuleArtifact 的审核必须由用户确认后通过 artifact service 完成
- 执行阶段不能由 Agent 决策

---
**校准来源：** `backend/agents/runtime.py`、`backend/agents/`、`backend/api/agent.py`、`backend/db/tables.py`
**最后校准：** 2026-05-17
