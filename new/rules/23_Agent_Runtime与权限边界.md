# 23_Agent_Runtime与权限边界

## READ WHEN

设计或实现 Agent 对话、页面召唤 Agent、Agent 配置、会话树、上下文压缩、记忆、工具调用、权限拦截、Agent workspace、Skill 调用时读取。

## READ ALSO

`../docs/20_Agent_Runtime与权限边界规范.md`
`../docs/30_Agent_Runtime架构与实现蓝图.md`

## MUST

- Agent 只负责理解、规划、生成草稿、解释和编排。
- 解析、计算、写库、导出、校验由确定性工具执行。
- 每个 Agent 有独立 workspace。
- 记忆分公共记忆、Agent 私有记忆、会话记忆、压缩摘要。
- 工具调用经过权限守卫。
- 高权限动作必须用户确认。
- Agent 输出必须标记类型，草稿不得伪装正式结果。
- Agent 功能必须实现 AgentLoop，不得只做聊天页面。
- 开发验收必须先用 FakeModelAdapter 跑通工具调用链。
- 文件夹操作必须通过 allowed_folders 和 PermissionGuard。

## METHOD

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

## NEVER

- 不要让 Agent 直接写正式数据库。
- 不要让 Agent 直接启用规则、Skill 或工作流。
- 不要把记忆当成正式数据来源。
- 不要把全部文件无差别塞进上下文。
- 不要让工具绕过权限。
- 不要把 workspace 当正式业务数据区。

## DONE

```text
Agent 配置：
workspace：
记忆：
会话树：
AgentLoop：
FakeModelAdapter：
真实工具调用：
上下文压缩：
工具权限：
浏览器验收：
```

