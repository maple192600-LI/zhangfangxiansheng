# OpenClaw Agent 架构深度研究

> 来源：[openclaw/openclaw](https://github.com/openclaw/openclaw)
> 研究日期：2026-04-30

## 1. 整体架构概览

OpenClaw 是基于 TypeScript/Node.js 的多通道 AI Agent 平台，核心设计理念：
- **插件优先（Plugin-First）**：Agent、Memory、ContextEngine 都是可插拔的
- **通道无关（Channel-Agnostic）**：Agent 逻辑与通信通道解耦
- **配置驱动（Config-Driven）**：通过 `openclaw.json` 配置一切

```
核心分层:
  Channel Layer    → src/channels/  (Discord/Slack/Telegram...)
  Gateway Layer    → src/gateway/   (协议、路由、会话)
  Agent Layer      → src/config/types.agents.ts (配置型Agent)
  Plugin Layer     → src/plugins/   (插件注册、发现、加载)
  Context Engine   → src/context-engine/ (可插拔上下文管理)
  Memory Layer     → src/memory-host-sdk/ (向量+全文记忆)
  Skill Layer      → skills/        (SKILL.md驱动的技能包)
```

## 2. Agent 设计方法 — 配置即 Agent

Agent 不是代码类，而是纯配置对象：

```python
class AgentConfig:
    id: str                              # Agent 唯一标识
    name: str | None                     # 显示名
    workspace: str | None                # 工作目录
    model: str | {"primary": str, "fallbacks": list}  # 模型配置
    thinking_default: str                # off/low/medium/high/max/adaptive
    system_prompt_override: str | None   # 完整替换系统提示词
    skills: list[str] | None             # skill 白名单
    memory_search: MemorySearchConfig    # 记忆配置
    subagents: {
        allow_agents: list[str],         # "*" = 允许所有
        max_concurrent: int,             # 默认1
        max_spawn_depth: int,            # 默认1
    }
    runtime: "embedded" | {"type": "acp"}
    sandbox: AgentSandboxConfig
    tools: AgentToolsConfig
```

### 多 Agent 协作

- 通过 `sessions_spawn` 工具创建子 Agent
- 子 Agent 有独立的 session（独立 JSONL 文件）
- 支持 Agent-to-Agent 消息
- 可视性控制：`self` / `tree` / `agent` / `all`

## 3. 记忆模式

### 架构

```
MemoryPlugin (插件接口)
  ├── MemorySearchManager
  │   ├── search(query) → MemorySearchResult[]
  │   ├── readFile(relPath) → MemoryReadResult
  │   └── sync() → void
  ├── Backend: "builtin" (SQLite + sqlite-vec)
  │   ├── FTS5 全文搜索
  │   ├── 向量搜索 (sqlite-vec)
  │   └── Hybrid: BM25 + Vector 加权融合
  └── Backend: "qmd" (外部进程)
```

### 存储方式

```
<workspace>/
├── MEMORY.md              ← 主记忆文件
├── memory/                ← 记忆目录（可含子目录）
├── DREAMS.md              ← Agent 自主生成的思考
└── (extraPaths)
```

### 三层自动注入

1. **System Prompt 注入**：`buildMemoryPromptSection()` 注入记忆搜索指导
2. **Startup Context 注入**：加载最近 N 天记忆（默认 2 天）
3. **Context Engine 注入**：每轮对话中组装上下文

### 混合检索策略

```python
hybrid = {
    "vector_weight": 0.7,     # 向量权重
    "text_weight": 0.3,       # 文本权重
    "mmr": {"lambda": 0.7},   # MMR 去重
    "temporal_decay": {"half_life_days": 30},  # 时间衰减
}
```

### 记忆 Flush（压缩前自动保存）

上下文压缩前，先把重要内容保存到记忆文件中，防止丢失。

## 4. Skill 系统

### Skill 规范

```
skill-name/
├── SKILL.md                 ← 必需（YAML frontmatter + Markdown 指令）
├── scripts/                 ← 可选，可执行脚本
├── references/              ← 可选，按需加载的参考文档
└── assets/                  ← 可选，输出资源
```

### 三级渐进式加载

| 级别 | 内容 | Token 开销 | 时机 |
|------|------|-----------|------|
| L1 | name + description（~100 tokens） | 极低 | **始终在上下文中** |
| L2 | SKILL.md body（<5000 词） | 中等 | **触发时加载** |
| L3 | scripts / references | 不限 | **按需执行** |

### Skill 发现来源（按优先级）

1. Bundled skills（随产品发布）
2. Workspace skills（Agent 工作区下）
3. Extra dirs（配置的额外目录）

### Skill 安全扫描

静态分析扫描规则：
- `dangerous-exec`：检测 child_process.exec/spawn
- `dynamic-code-execution`：检测 eval/new Function
- `crypto-mining`：检测挖矿关键词
- `suspicious-network`：检测可疑 WebSocket
- `potential-exfiltration`：检测文件读取 + 网络发送组合
- `env-harvesting`：检测 process.env + 网络发送

## 5. Context Engine（可插拔上下文引擎）

```python
class ContextEngine:
    info: {id, name, version}
    
    bootstrap(session_id) -> BootstrapResult          # 初始化
    ingest(session_id, message) -> IngestResult       # 接收消息
    assemble(session_id, messages, token_budget)      # 组装上下文
    compact(session_id, token_budget) -> CompactResult # 压缩上下文
    after_turn(session_id, messages) -> None           # 回合后维护
    prepare_subagent_spawn(parent, child) -> Prep      # 子Agent准备
```

关键设计：
- **Registry 模式**：全局单例注册表，支持多 owner
- **优雅降级**：非默认引擎失败时自动回退
- **Contract 校验**：解析后验证必需方法存在

## 6. 可借鉴的设计模式

| 模式 | 描述 | 适用性 |
|------|------|--------|
| 配置即 Agent | Agent 纯配置，无代码类 | ✅ 直接可用 |
| 插件插槽 | 排他插槽 + 自动禁用 + 回退 | ✅ 解耦核心与实现 |
| 渐进式 Skill 披露 | 三级加载节省 token | ✅ 直接可用 |
| 混合记忆检索 | BM25 + Vector + MMR + 时间衰减 | ⚠️ V2 再实现向量搜索 |
| Context Engine 接口 | ingest → assemble → compact 生命周期 | ✅ 直接可用 |
| Skill 安全扫描 | 静态分析 + 缓存 | ✅ 直接可用 |
| 记忆 Flush | 压缩前自动保存 | ✅ 直接可用 |
