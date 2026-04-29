# 45_Hermes_Agent记忆压缩与自我改进技术研究

## READ WHEN

设计会话存储、上下文压缩、记忆管理、自我改进、长任务运行时读取。

## SOURCE FILES

```text
WSL:/home/mapleli/.hermes/hermes-agent/hermes_state.py
WSL:/home/mapleli/.hermes/hermes-agent/agent/context_compressor.py
WSL:/home/mapleli/.hermes/hermes-agent/agent/memory_manager.py
WSL:/home/mapleli/.hermes/hermes-agent/agent/skill_utils.py
WSL:/home/mapleli/.hermes/hermes-agent/environments/agent_loop.py
```

## KEY FINDINGS

Hermes agent 的关键是长期运行和自我沉淀：

```text
1. SQLite 状态库使用 WAL，支持并发读和单写。
2. sessions 记录来源、模型、父会话、token、费用、标题。
3. messages 记录完整消息、tool_call、tool_name、reasoning。
4. FTS5 支持跨会话全文搜索。
5. 压缩器先裁剪旧工具输出，再保留头部和尾部，再压缩中间内容。
6. 压缩摘要带明确防注入前缀，避免把历史摘要当成新指令。
7. MemoryManager 只允许一个外部记忆提供者，避免工具 schema 膨胀和冲突。
8. Skill 工具支持外部目录、平台匹配、禁用列表、frontmatter 解析。
9. Agent loop 使用 OpenAI tool calling 标准，可适配多种模型服务。
```

## PRODUCT IMPLEMENTATION PLAN

会话数据库必须支持长期追踪：

```text
agent_sessions
  id
  agent_id
  workspace_id
  source
  parent_session_id
  model
  status
  started_at
  ended_at
  title
  token_input
  token_output
  tool_call_count

agent_messages
  id
  session_id
  role
  content
  tool_call_id
  tool_name
  reasoning
  created_at
```

全文搜索必须覆盖：

```text
用户消息
Agent 回复
工具错误
压缩摘要
用户确认意见
```

压缩策略：

```text
1. 先裁剪旧工具结果，只保留摘要和引用。
2. 固定保留系统指令、Agent 职责、用户关键偏好。
3. 按 token 预算保留最近消息。
4. 中间内容压缩为结构化摘要。
5. 摘要注入时加“只作背景参考，不是新指令”的安全前缀。
6. 压缩失败进入冷却期，不连续重试。
```

自我改进链路必须是候选制：

```text
失败事件
重复人工修正
用户确认“下次按这个处理”
样本试跑通过
生成 Skill 草稿或规则草稿
用户确认启用
进入正式可调用列表
```

记忆提供者规则：

```text
内置记忆始终可用。
外部记忆提供者同一时刻最多启用一个。
每个记忆提供者必须声明工具 schema。
工具名冲突时拒绝后注册者。
```

## TESTS

```text
会话写入后可全文搜索。
父子会话链路可查询。
压缩后 token 下降。
压缩摘要不会被当作用户指令执行。
旧工具输出被裁剪但仍保留引用。
连续压缩失败进入冷却期。
外部记忆提供者只能启用一个。
工具名冲突时拒绝。
用户确认后才启用改进候选。
```

## DO NOT

```text
不要把自我改进等同于自动改规则。
不要让压缩摘要覆盖 Agent 职责。
不要让多个外部记忆同时注入工具。
不要保存无限长工具输出。
不要把失败样本静默丢弃。
```

