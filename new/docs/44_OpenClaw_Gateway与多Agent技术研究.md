# 44_OpenClaw_Gateway与多Agent技术研究

## READ WHEN

设计多 Agent、工作区、会话路由、远程入口、沙箱、Skill 快照时读取。

## SOURCE FILES

```text
C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/README.md
C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/dist/agent-command-*.js
C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/dist/agent-scope-*.js
C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/dist/acp-spawn-*.js
C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/dist/audit-*.js
C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/skills/skill-creator/SKILL.md
```

## KEY FINDINGS

OpenClaw 的核心不是“更多入口”，而是一个 Gateway 控制面：

```text
1. Gateway 统一管理 sessions、channels、tools、events。
2. inbound channel 可路由到隔离 Agent。
3. 每个 Agent 有 workspace 和 per-agent session。
4. sessions_spawn 有深度限制、子会话数量限制、agent allowlist、沙箱限制。
5. Skill snapshot 会按 workspace 和 agent skill filter 缓存。
6. 安全审计会检查沙箱、公开入口、Skill 自动授权、符号链接逃逸。
7. bundled skills 放在产品包内，workspace skills 放在工作区内。
```

## PRODUCT IMPLEMENTATION PLAN

本产品需要一个本地控制面，不要让页面直接驱动各个模块：

```text
LocalControlPlane
  sessions
  agents
  skills
  workflows
  connectors
  events
  audits
```

Agent 配置最少包含：

```json
{
  "agent_id": "cashier",
  "display_name": "出纳",
  "workspace_id": "finance",
  "allowed_tools": [],
  "allowed_connectors": [],
  "skill_filter": {
    "include": [],
    "exclude": []
  },
  "limits": {
    "max_child_sessions": 3,
    "max_spawn_depth": 1
  }
}
```

子 Agent 或子会话必须受控：

```text
检查调用方 Agent
检查深度
检查同时运行数量
检查目标 Agent 是否允许
检查沙箱与权限
创建 session
事件写入 agent_session_events
```

Skill 快照必须按 Agent 保存：

```text
agent_skill_snapshots
  agent_id
  workspace_id
  skill_filter_hash
  snapshot_version
  skill_ids
  created_at
```

安全审计必须作为产品功能：

```text
Agent 是否有过高权限
外部连接器是否可写
Skill 是否带脚本
脚本是否访问未授权目录
工作区 Skill 是否符号链接逃逸
工作流是否含明文密钥
```

## TESTS

```text
不同 Agent 的 workspace 隔离。
Agent 只能看到自己允许的 Skill。
Skill 更新后 snapshot 版本变化。
子会话超过深度限制失败。
子会话超过数量限制失败。
未允许目标 Agent 时 spawn 失败。
安全审计能发现高风险配置。
浏览器页面能查看 session、Agent、Skill snapshot、审计结果。
```

## DO NOT

```text
不要让所有 Agent 共用一个隐式工作区。
不要让子 Agent 无限创建。
不要让远程入口默认拥有本机高权限。
不要把 Skill snapshot 只存在内存。
不要跳过安全审计。
```

