# Agent V2 改造方案

> 基于 pi-mono / Hermes / OpenClaw 架构研究
> 日期：2026-04-30

## 1. 改造目标

解决 Agent 运行中频繁中断、不完成任务的问题，同时引入上下文压缩、多 tool_call、记忆自动注入、并发控制等核心能力。

## 2. 改造范围与优先级

| 优先级 | 改造项 | 解决问题 | 参考来源 |
|--------|--------|---------|---------|
| P0 | 上下文压缩（Context Compaction） | P1：超出模型上下文导致崩溃 | pi-mono compaction/ |
| P0 | 错误恢复与续写增强 | P3/P4：截断/中断无恢复 | pi-mono agent-loop |
| P0 | 多 tool_call 支持 | P2：多个 tool_call 只执行最后一个 | pi-mono agent-loop |
| P1 | 记忆自动注入 | P7：LLM 不知道记忆存在 | Hermes 多源数据 |
| P1 | 并发控制（Session 锁） | P8：同一 session 并发执行 | pi-mono AbortController |
| P2 | needs_confirm 实际实现 | P5/P6：确认机制形同虚设 | pi-mono beforeToolCall |
| P2 | Skill 运行记录 | P14：无审计 | OpenClaw 运行记录 |
| P3 | Skill 安全扫描 | P10：python_exec 不安全 | OpenClaw 安全扫描 |

## 3. 文件变更清单

### 新增文件

```
backend/agents_v2/
├── compaction.py      ← 上下文压缩引擎（~150行）
├── session_lock.py    ← Session 并发锁（~30行）
└── tools/
    └── ... (无新增)
```

### 修改文件

| 文件 | 改动概要 |
|------|---------|
| `runtime.py` | 核心循环重写：多 tool_call + 错误恢复 + compaction 调用 + 记忆注入 |
| `provider.py` | 新增 token 使用量统计回调 |
| `session_store.py` | 新增 token 使用记录 + 会话状态管理 |
| `memory_store.py` | 新增 `get_relevant_memories()` 自动检索接口 |
| `_build_system_prompt` (runtime.py内) | 注入记忆摘要 + 可用技能列表 |
| `permission.py` | needs_confirm 实际拦截逻辑 |
| `tool_registry.py` | execute_tool 支持批量执行 |

### 不修改文件

| 文件 | 原因 |
|------|------|
| `workspace.py` | 当前功能满足需求 |
| `sse_helper.py` | 事件格式不变 |
| `skill_loader.py` | Skill 加载逻辑不变 |
| 所有 tools/*.py | 工具实现不变 |

## 4. 核心改造设计

### 4.1 上下文压缩（compaction.py）

借鉴 pi-mono 的增量摘要模式：

```python
class CompactionEngine:
    def __init__(self, model_config, max_context_tokens=128000, reserve_tokens=8192):
        self.max_context = max_context_tokens
        self.reserve = reserve_tokens
    
    def estimate_tokens(self, messages: list[dict]) -> int:
        """粗估 token 数：chars / 4"""
        total = sum(len(str(m)) for m in messages)
        return total // 4
    
    def should_compact(self, messages: list[dict]) -> bool:
        return self.estimate_tokens(messages) > self.max_context - self.reserve
    
    async def compact(self, messages: list[dict], existing_summary: str = "") -> tuple[list[dict], str]:
        """
        压缩策略：
        1. 保留 system prompt + 最近 20 条消息
        2. 较早消息用 LLM 生成摘要
        3. 如果有 existing_summary，增量合并
        4. 返回 [system, summary_msg, ...recent] + 新摘要文本
        """
```

在 runtime.py 的 while 循环**每次 LLM 调用前**检查是否需要压缩。

### 4.2 多 tool_call 支持

当前问题（runtime.py:92-93）：
```python
elif chunk["type"] == "tool_call":
    last_tool_call = chunk.get("tool_call")  # 只保存最后一个
```

改造为：
```python
tool_calls: list[dict] = []

# 在 LLM 流式返回中收集所有 tool_call
elif chunk["type"] == "tool_call":
    tool_calls.append(chunk.get("tool_call"))

# 循环结束后批量执行所有 tool_call
for tc in tool_calls:
    result = await execute_tool(tc["name"], tc["arguments"], ctx)
    # ... 保存到 messages
```

### 4.3 错误恢复增强

当前问题（runtime.py:100-103）：
```python
elif chunk["type"] == "error":
    yield sse.sse_error(...)
    return  # 直接终止，不保存
```

改造为：
```python
elif chunk["type"] == "error":
    error_msg = chunk.get("error", "AI 调用失败")
    # 保存错误到会话历史（标记为 error 类型）
    save_message(db, session_id, "assistant", content=f"[错误] {error_msg}", is_error=True)
    yield sse.sse_error(error_msg)
    # 不 return，而是设置 error 标记让外层处理
    has_error = True
    break
```

### 4.4 记忆自动注入

在 `_build_system_prompt` 中注入相关记忆：

```python
def _build_system_prompt(agent, memories=None, skills=None):
    parts = [...]
    
    # 注入记忆
    if memories:
        parts.append("\n## 相关记忆")
        for mem in memories[:5]:
            parts.append(f"- [{mem.key}]: {mem.content[:100]}")
    
    # 注入可用技能列表
    if skills:
        parts.append("\n## 可用技能")
        for skill in skills:
            parts.append(f"- {skill.display_name}: {skill.description}")
    
    parts.append("\n你可以使用 memory_search 工具搜索更多记忆。")
    return "\n".join(parts)
```

### 4.5 Session 并发锁

```python
# session_lock.py
import asyncio

_locks: dict[int, asyncio.Lock] = {}

def get_session_lock(session_id: int) -> asyncio.Lock:
    if session_id not in _locks:
        _locks[session_id] = asyncio.Lock()
    return _locks[session_id]

# runtime.py 中使用
lock = get_session_lock(session_id)
if lock.locked():
    yield sse.sse_error("该会话正在处理中，请等待完成后再发送消息")
    return
async with lock:
    # ... 正常执行 run_turn
```

### 4.6 llm_max_tokens 默认值统一

在 runtime.py 中统一使用数据库默认值 16384：

```python
max_tokens=getattr(agent, "llm_max_tokens", 16384),  # 统一默认值
```

## 5. runtime.py 核心循环新流程

```
run_turn()
  → save_message(user)
  → load_recent_messages(50)
  → get_relevant_memories(agent_id, user_text)   # 新增
  → _build_system_prompt(agent, memories, skills) # 增强
  → get_session_lock(session_id)                  # 新增
  → _format_messages(system_prompt, history)
  → compaction.check_and_compact(messages)         # 新增
  
  → while turn < MAX_TURNS:
      → stream_chat(...)
      → 收集所有 tool_calls (list)                 # 改造
      → 错误：保存到历史 + yield error + break      # 改造
      → length 截断：续写逻辑不变
      → end_turn：保存 + return
      → tool_calls 批量执行：                       # 改造
          for tc in tool_calls:
            → is_tool_allowed?
            → execute_tool(tc)
            → save assistant + tool result
```

## 6. 不做的事（V2 后续）

- DSPy + GEPA 技能进化（Hermes Phase 1 级别）— 需要 DSPy 依赖，过于复杂
- Extension 插件系统（pi-mono 级别）— 当前规模不需要
- 会话分支/切换 — 后续版本
- python_exec 沙箱加固 — 需要独立的沙箱进程，当前用白名单够用

## 7. 预期改动量

| 文件 | 改动类型 | 预估行数变化 |
|------|---------|-------------|
| runtime.py | 重写 | 294 → ~400行 |
| compaction.py | 新增 | ~150行 |
| session_lock.py | 新增 | ~30行 |
| session_store.py | 修改 | +20行 |
| memory_store.py | 修改 | +25行 |
| provider.py | 修改 | +15行 |
| permission.py | 修改 | +15行 |
| **总计** | | ~+360行 |
