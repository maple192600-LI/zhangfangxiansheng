# 当前项目 Agent V2 架构分析

> 研究日期：2026-04-30
> 分支：feat/round11-agent-selector-and-ai-parse

## 1. 目录结构

```
backend/agents_v2/                       # Agent 运行时核心代码
├── __init__.py          (5行)
├── runtime.py           (294行)         # Agent 主循环
├── provider.py          (406行)         # LLM 调用抽象层
├── tool_registry.py     (144行)         # 工具注册表
├── skill_loader.py      (94行)          # Skill 加载/执行/测试
├── memory_store.py      (83行)          # 记忆持久化
├── session_store.py     (135行)         # 会话/消息历史管理
├── workspace.py         (81行)          # 工作区文件系统隔离
├── permission.py        (56行)          # 权限网关
├── sse_helper.py        (34行)          # SSE 事件序列化
└── tools/                               # 工具实现
    ├── __init__.py      (3行)
    ├── ask_user.py      (10行)
    ├── db_ops.py        (156行)
    ├── fs.py            (43行)
    ├── memory.py        (19行)
    ├── openpyxl_ops.py  (101行)
    ├── shell_ops.py     (75行)
    └── skill_ops.py     (131行)

backend/data/agents/                     # Agent 运行时数据
├── system/skills/
│   ├── parse_bank_flow/  (manifest.yaml + run.py 296行)
│   └── gen_report/       (manifest.yaml + run.py 207行)
├── ag_grlslj/            # Agent 实例
│   └── workspace/inbox/
└── ag_kbdpch/            # Agent 实例
    ├── skills/parse_bank_boc/  (manifest.yaml + run.py 529行)
    └── workspace/inbox/
```

**核心代码量**：agents_v2/ 共 1332 行（不含 tools），tools 共 538 行，总计 **1870 行**。

## 2. Agent 运行流程

```
用户消息 → POST /api/agent_v2/sessions/{id}/messages
  → run_turn()
    → save_message(user)
    → load_recent_messages(50)
    → _build_system_prompt()
    → get_tools_for_llm(perm)
    → while turn < 40:
        → stream_chat()
          → provider.py 路由（ollama/anthropic/openai-compatible）
          → 流式 SSE 返回
        → if stop_reason == "length": 截断续写 → continue
        → if text and no tool_call: save → done → return
        → if tool_call:
            → is_tool_allowed?
            → execute_tool(name, args, ctx)
            → save assistant + tool result
            → continue
```

## 3. 已注册工具（14 个）

| 工具名 | 类型 | 权限 |
|--------|------|------|
| fs_list / fs_read | 只读 | allowed |
| fs_write / fs_edit | 写入 | needs_confirm |
| memory_save / memory_search | 只读 | allowed |
| ask_user | 只读 | allowed |
| skill_list / skill_run | 只读 | allowed |
| skill_test / skill_create | 写入 | needs_confirm |
| openpyxl_read | 只读 | allowed |
| openpyxl_write | 写入 | **未加入默认权限** |
| db_query_business | 只读 | allowed |
| db_insert_fund_event / db_save_parser_template | 写入 | needs_confirm |
| python_exec | 写入 | needs_confirm |

## 4. 已知架构问题（16 项）

### 致命问题（直接导致 Agent 中断）

**P1: 历史消息无 token 管理**
- `load_recent_messages` 固定加载最近 50 条
- 长对话或大 tool_result 会超出模型上下文限制
- **根因：没有 context compaction 机制**

**P2: 单 tool_call 限制**
- `last_tool_call` 只保存最后一个 tool call
- LLM 返回多个 tool_calls 时，前面的会丢失

**P3: llm_max_tokens 默认值不一致**
- 数据库默认 16384，runtime 默认 4096
- 导致 Agent 可能只生成很少内容就触发 length 截断

**P4: 错误处理粗糙**
- error 事件直接 return，不保存错误信息到会话历史
- 用户看到中断但无法追溯原因

### 高优先级问题

**P5: needs_confirm 机制未实际实现**
- 定义了但从未调用，需要确认的工具直接执行

**P6: ask_user 是非阻塞的**
- 立即返回 waiting_for_user，不会暂停 Agent 循环

**P7: 记忆不自动注入上下文**
- 完全依赖 LLM 主动调用 memory_search
- system prompt 中未提及记忆存在

**P8: 无并发控制**
- 同一 session 多个请求可能并发执行 run_turn

**P9: 无 token 使用审计**
- 有 ai_call_logs 表但从未写入

### 中优先级问题

**P10: python_exec 沙箱不安全** — exec 在主线程运行，无超时
**P11: openpyxl_write 未加入默认权限** — 永远不会被使用
**P12: agent_init.py 名不副实** — 只创建空目录
**P13: 数据库 Session 生命周期问题** — Skill 可能泄漏连接
**P14: Skill 运行记录缺失** — agent_runs 表从未写入
**P15: 无上下文压缩** — 只有 MAX_TURNS=40 和 limit=50 粗略控制
**P16: parse_bank_boc/run.py 过大（529行）** — 多职责混合

## 5. 与参考项目对比

| 能力 | pi-mono | Hermes | OpenClaw | 当前项目 |
|------|---------|--------|----------|---------|
| 核心循环 | 双层 while + steering/followUp 队列 | — | — | 单层 while，无队列 |
| 工具注册 | 动态 registerTool + beforeToolCall 钩子 | — | Skill Registry | 装饰器静态注册 |
| 上下文压缩 | token 预算 + LLM 摘要 + 增量更新 | — | — | 无（仅限50条历史） |
| Skill 加载 | Markdown 发现 + 按需读取 | DSPy 模块化 + GEPA 进化 | 按需加载 + 安全扫描 | importlib 动态加载 |
| 记忆 | — | 评估数据集 + 多源挖掘 | — | 简单 ORM 存储 |
| 错误恢复 | AbortSignal 贯穿 + 续写 | — | — | 粗糙 return |
| 权限 | beforeToolCall 钩子 | — | 安全扫描 | 白名单（未完整实现） |
| 会话持久化 | JSONL 追加写入 | — | — | SQLAlchemy ORM |
| 并发控制 | — | — | — | 无 |

## 6. 改造优先级建议

1. **上下文压缩** — 解决 P1（Agent 中断的主因）
2. **错误恢复与续写** — 解决 P3/P4（截断与中断无恢复）
3. **多 tool_call 支持** — 解决 P2
4. **记忆自动注入** — 解决 P7
5. **并发控制** — 解决 P8
6. **needs_confirm 实际实现** — 解决 P5/P6
