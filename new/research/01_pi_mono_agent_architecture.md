# pi-mono Agent 架构研究

> 来源：[badlogic/pi-mono](https://github.com/badlogic/pi-mono)
> 研究日期：2026-04-30

## 1. 仓库目录结构

```
pi-mono/
├── packages/
│   ├── agent/          ← @mariozechner/pi-agent-core：纯 Agent Runtime 核心
│   │   └── src/
│   │       ├── agent.ts        ← Agent 类（有状态包装器）
│   │       ├── agent-loop.ts   ← 核心循环（纯函数）
│   │       ├── types.ts        ← 所有类型定义
│   │       ├── proxy.ts        ← 代理流（服务端转发 LLM 请求）
│   │       └── index.ts        ← 统一导出
│   │
│   ├── ai/             ← @mariozechner/pi-ai：LLM Provider 抽象层
│   │   └── src/
│   │       ├── stream.ts       ← streamSimple / completeSimple
│   │       ├── api-registry.ts ← Provider 注册表
│   │       ├── providers/      ← 各 LLM Provider 实现
│   │       ├── types.ts        ← Message, Model, Tool, Context 等核心类型
│   │       └── utils/          ← OAuth, JSON 解析, 校验等工具
│   │
│   ├── coding-agent/   ← @mariozechner/pi-coding-agent：完整编码 Agent
│   │   └── src/
│   │       ├── core/
│   │       │   ├── agent-session.ts          ← 会话生命周期
│   │       │   ├── agent-session-runtime.ts  ← 会话管理（new/switch/fork/import）
│   │       │   ├── session-manager.ts        ← JSONL 持久化 + 会话树
│   │       │   ├── skills.ts                 ← Skill 发现与加载
│   │       │   ├── compaction/               ← 上下文压缩
│   │       │   ├── extensions/               ← 插件系统
│   │       │   ├── tools/                    ← 内置工具
│   │       │   ├── system-prompt.ts          ← 系统提示构建
│   │       │   └── model-registry.ts         ← 模型注册表
│   │       └── modes/
│   │           ├── interactive/              ← TUI 交互模式
│   │           └── rpc/                      ← JSONL-RPC 模式
│   │
│   ├── tui/            ← 终端 UI 组件库
│   ├── web-ui/         ← Web UI（React）
│   └── pods/           ← 沙箱执行环境
```

## 2. Agent Runtime — 三层分离架构

### 第一层：agent-loop.ts（纯函数）

- `runAgentLoop()` — 从新 prompt 启动
- `runAgentLoopContinue()` — 从当前上下文续写
- 核心循环 `runLoop()` — 内外双层 while 循环

### 第二层：agent.ts（Agent 类）

- 拥有 `state`（消息、工具、模型、流式状态）
- 管理 `steeringQueue` 和 `followUpQueue`
- 处理 `AbortController` 生命周期
- 通过 `subscribe()` 通知监听器

### 第三层：AgentSession（coding-agent 层）

- 连接 Agent + SessionManager + ExtensionRunner
- 处理工具的动态启禁、系统提示构建、会话持久化

## 3. 核心循环伪代码

```python
def runLoop(context, config, signal, emit, streamFn):
    pending_messages = config.getSteeringMessages()
    
    while True:  # 外层循环：followUp 消息驱动
        has_more_tool_calls = True
        
        while has_more_tool_calls or pending_messages:  # 内层循环
            # 1. 注入 steering 消息
            for msg in pending_messages:
                context.messages.append(msg)
            pending_messages = []
            
            # 2. 调用 LLM（流式）
            assistant_msg = streamAssistantResponse(context, config, signal)
            #    a. config.transformContext(messages)  ← 上下文压缩
            #    b. config.convertToLlm(messages)      ← 转为 LLM 格式
            #    c. streamFn(model, llmContext, options) ← 实际 API 调用
            
            # 3. 错误/中止检查
            if assistant_msg.stopReason in ("error", "aborted"):
                return  # 直接终止，不重试
            
            # 4. 执行工具调用
            tool_calls = [c for c in assistant_msg.content if c.type == "toolCall"]
            if tool_calls:
                tool_results = executeToolCalls(tool_calls, ...)
                context.messages.extend(tool_results)
        
        # 5. 检查 followUp 消息
        follow_up = config.getFollowUpMessages()
        if follow_up:
            pending_messages = follow_up
            continue
        break
```

## 4. Tool Registry

工具注册分两个层级：

- **Agent Core 层**：静态工具列表 `AgentContext.tools`
- **Extension 层**：动态注册 `api.registerTool({...})`

工具执行流程：
```
prepareToolCall → validateArguments → beforeToolCall hook → execute → afterToolCall hook → emitToolResult
```

关键：`beforeToolCall` 钩子可以阻止工具执行（`{ block: true }`）。

## 5. Skill Loader

Skill 是纯 Markdown 文件：

**搜索路径（按优先级）：**
1. `~/.pi/agent/skills/` — 用户全局
2. `cwd/.pi/skills/` — 项目本地
3. `settings.jsonl` 中配置的显式路径

**发现规则：**
1. 目录中有 `SKILL.md` → 视为技能根，不递归
2. 否则扫描直接 `.md` 子文件
3. 递归子目录查找 `SKILL.md`

## 6. Context Compaction — 上下文压缩

触发条件：`contextTokens > contextWindow - reserveTokens`（默认预留 16384 tokens）

压缩算法：
1. 找到上次压缩边界
2. 估算当前 token 数（chars/4）
3. 找切割点（保留最近 20000 tokens）
4. 只在 user/assistant 消息处切割（绝不在 toolResult 处）
5. 用 LLM 生成历史摘要
6. 增量更新：如果有上次摘要，使用 UPDATE prompt 合并

## 7. 错误恢复策略

| 场景 | 处理方式 |
|------|---------|
| LLM 调用错误 | 返回 stopReason="error"，直接终止 |
| 工具执行错误 | 错误作为 toolResult 返回给 LLM，由 LLM 决定下一步 |
| 用户中止 | AbortSignal 贯穿全流程，产生 stopReason="aborted" |
| 会话恢复 | JSONL 追加写入，每条独立，崩溃后可恢复 |
| 续写 | `agentLoopContinue` 从断点恢复 |

## 8. 可借鉴的设计模式

| 问题 | pi-mono 方案 |
|------|-------------|
| Agent 循环卡死 | 外层 while + hasMoreToolCalls 条件，不依赖递归 |
| LLM 调用超时 | AbortSignal 传递到 fetch 层 |
| 工具执行阻塞 | 并行执行 + 顺序 preflight |
| 上下文溢出 | 自动压缩：token 预算制 + LLM 摘要 + 增量更新 |
| 会话丢失 | JSONL 追加写入，每条独立 |
| 中断后续写 | agentLoopContinue + 会话持久化 |
| 用户中途插话 | Steering queue + FollowUp queue |
| 插件热更新 | Extension stale 检测 + invalidate 机制 |
