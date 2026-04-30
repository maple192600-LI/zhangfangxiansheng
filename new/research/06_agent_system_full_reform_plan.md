# 账房先生 — 智能体系统全局重构方案

> 基于 5 份架构研究：pi-mono / Hermes / OpenClaw / Claude Code skill-creator / 当前项目分析
> 日期：2026-04-30

## 1. 重构目标

不是修补现有 Agent，而是**重建整个智能体系统**：

1. **配置即 Agent**（OpenClaw 模式）— Agent 通过 JSON 配置定义，不需要写代码
2. **SKILL.md 为核心的技能系统**（Claude Code 规范）— 兼容 Claude Code 生态，可安装第三方 skill
3. **渐进式 Skill 加载**（OpenClaw 三级加载）— L1 元数据始终加载，L2/L3 按需加载
4. **上下文压缩引擎**（pi-mono 模式）— 解决 Agent 超上下文崩溃的根本问题
5. **混合记忆系统**（OpenClaw 模式）— 自动注入 + Flush + 关键词检索
6. **自进化能力**（Hermes 模式）— 从执行轨迹中提取改进建议

## 2. 新目录结构

```
backend/
├── agents_v2/                        # Agent 运行时（重构）
│   ├── __init__.py
│   ├── runtime.py                    # 核心循环（重写：多 tool_call + 错误恢复）
│   ├── provider.py                   # LLM 调用层（增强：token 统计）
│   ├── context_engine.py             # NEW: 可插拔上下文引擎
│   ├── compaction.py                 # NEW: 上下文压缩
│   ├── session_lock.py               # NEW: 并发控制
│   ├── tool_registry.py              # 工具注册（改造：支持批量执行）
│   ├── permission.py                 # 权限（改造：needs_confirm 实际生效）
│   ├── memory_store.py               # 记忆（重写：自动检索 + Flush）
│   ├── session_store.py              # 会话（增强：token 审计）
│   ├── workspace.py                  # 工作区（不变）
│   ├── sse_helper.py                 # SSE 事件（不变）
│   ├── skill_loader.py               # 重写：SKILL.md 规范 + 三级加载
│   ├── skill_registry.py             # NEW: 技能注册表 + 发现 + 安全扫描
│   ├── skill_executor.py             # NEW: 技能执行器（inline + fork 模式）
│   ├── skill_creator.py              # NEW: skill-creator 核心（预制技能）
│   └── tools/                        # 工具实现
│       ├── __init__.py
│       ├── ask_user.py
│       ├── db_ops.py
│       ├── fs.py
│       ├── memory.py
│       ├── openpyxl_ops.py
│       ├── shell_ops.py
│       └── skill_ops.py              # 改造：对接新 skill 系统
│
├── data/agents/                      # Agent 运行时数据
│   ├── system/
│   │   └── skills/                   # 全局技能（SKILL.md 规范）
│   │       ├── parse_bank_flow/
│   │       │   └── SKILL.md          # 从 manifest.yaml 迁移
│   │       ├── gen_report/
│   │       │   └── SKILL.md
│   │       └── skill-creator/        # NEW: 预装的 skill-creator
│   │           └── SKILL.md
│   └── ag_xxxxx/                     # 各 Agent 实例
│       ├── config.json               # Agent 配置（新增）
│       ├── memory/                   # Agent 记忆目录（新增）
│       │   └── MEMORY.md
│       ├── skills/                   # Agent 专属技能
│       │   └── parse_bank_boc/
│       │       └── SKILL.md          # 从 manifest.yaml 迁移
│       ├── workspace/
│       └── sessions/                 # 会话 JSONL（新增）
```

## 3. 核心模块设计

### 3.1 Skill 系统（完全重建）

#### 3.1.1 SKILL.md 规范（兼容 Claude Code）

```yaml
---
name: parse-bank-flow                 # kebab-case
description: "解析银行流水 Excel，自动识别列映射并提取标准字段。支持多银行格式。"
when_to_use: "当需要解析银行流水文件、匹配解析规则、或创建新的银行流水解析技能时使用"
allowed-tools:
  - openpyxl_read
  - openpyxl_write
  - fs_read
  - fs_write
  - db_query_business
  - db_save_parser_template
arguments:
  file_path:
    description: "银行流水文件路径"
    required: true
  bank_name:
    description: "银行名称（可选，自动检测）"
    required: false
---

# 银行流水解析技能

## 工作流程
1. 读取文件，检测格式（xls/xlsx/csv）
2. 自动检测表头行位置
3. 匹配已有解析规则
4. 如无匹配规则，使用 AI 智能识别列映射
5. 提取标准字段并返回结构化数据

## 规则
- 金额字段必须处理千分位和负数格式
- 日期字段统一转为 YYYY-MM-DD 格式
- 收入/支出必须分开，不能只存交易金额
```

#### 3.1.2 三级渐进式加载

```python
class SkillRegistry:
    """技能注册表"""
    
    def startup_scan(self):
        """启动时只读 frontmatter 构建 L1 索引"""
        # 每个 skill 仅 ~100 tokens 的 name + description
    
    def trigger(self, user_input: str) -> Optional[Skill]:
        """根据用户输入匹配并加载 L2"""
        # 关键词匹配 + description 语义匹配
    
    def load_resource(self, skill: Skill, path: str):
        """按需加载 L3 资源（scripts/references）"""
```

#### 3.1.3 skill-creator 预装

将 Claude Code 的 skill-creator 流程预制为系统级技能，用户创建新技能时：

```
用户请求 "帮我创建一个解析XX银行流水的技能"
  → Agent 识别到需要创建技能
  → 加载 skill-creator SKILL.md
  → 按 skill-creator 的工作流执行：
     1. 捕获意图
     2. 读取样本文件分析结构
     3. 生成 SKILL.md
     4. 编写测试用例（evals.json）
     5. 运行测试验证
     6. 优化直到通过
```

#### 3.1.4 兼容 Claude Code 第三方 Skill

用户可以将 Claude Code 生态的 skill 直接安装到 `data/agents/system/skills/`，系统自动识别 SKILL.md 并加载。

### 3.2 上下文压缩引擎（context_engine.py）

```python
class ContextEngine:
    """可插拔上下文引擎（借鉴 pi-mono + OpenClaw）"""
    
    def ingest(self, session_id: int, message: dict):
        """接收消息"""
    
    def assemble(self, session_id: int, messages: list, token_budget: int) -> list:
        """组装上下文：压缩 + 记忆注入 + Skill 指令"""
    
    def compact(self, session_id: int, token_budget: int) -> CompactResult:
        """压缩：保留最近消息 + LLM 生成摘要 + 增量更新"""
    
    def after_turn(self, session_id: int, messages: list):
        """回合后维护：记忆 Flush + token 审计"""
```

压缩策略（来自 pi-mono）：
1. 检测 token 是否接近上限
2. 保留 system prompt + 最近 20 条消息
3. 较早消息用 LLM 生成摘要（增量更新）
4. **压缩前先 Flush 记忆**（来自 OpenClaw）— 防止丢失重要信息

### 3.3 记忆系统（memory_store.py 重写）

```python
class MemoryStore:
    """混合记忆系统（借鉴 OpenClaw）"""
    
    # 存储方式保持 SQLAlchemy ORM
    # 新增自动检索接口
    
    def get_relevant(self, agent_id: int, query: str, limit: int = 5) -> list[Memory]:
        """根据 query 检索相关记忆（关键词匹配）"""
    
    def flush_from_context(self, agent_id: int, messages: list):
        """从上下文中提取重要信息保存为记忆（压缩前调用）"""
    
    def auto_search_and_format(self, agent_id: int, user_text: str) -> str:
        """自动检索 + 格式化为可注入 system prompt 的文本"""
```

三层自动注入（来自 OpenClaw）：
1. System Prompt 注入记忆搜索指导
2. 启动时注入最近记忆
3. 每轮对话自动检索相关记忆

### 3.4 runtime.py 核心循环重写

```
run_turn()
  → get_session_lock(session_id)                  # 并发控制
  → save_message(user)
  → load_recent_messages(50)
  → memory_store.auto_search(agent_id, user_text) # 记忆注入
  → skill_registry.trigger(user_text)              # Skill 匹配
  → _build_system_prompt(agent, memories, skills)  # 增强 prompt
  → context_engine.assemble(messages, budget)      # 上下文组装
  → context_engine.compact()                       # 压缩（如需要）
  
  → while turn < MAX_TURNS:
      → stream_chat(...)
      → 收集所有 tool_calls (list)                  # 多 tool_call
      → error: 保存到历史 + yield error + break      # 错误恢复
      → length: 截断续写
      → end_turn: save + return
      → tool_calls: 批量执行
          → for tc in tool_calls:
              → permission check (含 needs_confirm) # 权限实际生效
              → execute_tool(tc)
              → save assistant + tool result
      → context_engine.after_turn()                 # 回合后维护
```

### 3.5 Skill 安全扫描

```python
class SkillScanner:
    """Skill 安装前的安全扫描（借鉴 OpenClaw）"""
    
    RULES = [
        {"id": "dangerous-exec", "severity": "critical", "pattern": r"exec\(|spawn|subprocess"},
        {"id": "dynamic-code", "severity": "critical", "pattern": r"eval\(|__import__"},
        {"id": "env-harvest", "severity": "critical", "pattern": r"os\.environ.*requests|fetch"},
        {"id": "crypto-mine", "severity": "critical", "pattern": r"stratum|xmrig|coinhive"},
    ]
    
    def scan(self, skill_dir: Path) -> ScanReport:
        """递归扫描 skill 目录，返回安全报告"""
```

## 4. 迁移计划

### Phase 1：基础设施（不破坏现有功能）

| 步骤 | 内容 | 文件 |
|------|------|------|
| 1.1 | 新建 context_engine.py | agents_v2/context_engine.py |
| 1.2 | 新建 compaction.py | agents_v2/compaction.py |
| 1.3 | 新建 session_lock.py | agents_v2/session_lock.py |
| 1.4 | 新建 skill_registry.py | agents_v2/skill_registry.py |
| 1.5 | 新建 skill_executor.py | agents_v2/skill_executor.py |
| 1.6 | 新建 skill_creator.py | agents_v2/skill_creator.py |
| 1.7 | 新建 skill 扫描器 | agents_v2/skill_scanner.py |

### Phase 2：核心改造

| 步骤 | 内容 | 文件 |
|------|------|------|
| 2.1 | 重写 runtime.py 核心循环 | agents_v2/runtime.py |
| 2.2 | 重写 skill_loader.py | agents_v2/skill_loader.py |
| 2.3 | 重写 memory_store.py | agents_v2/memory_store.py |
| 2.4 | 改造 tool_registry.py | agents_v2/tool_registry.py |
| 2.5 | 改造 permission.py | agents_v2/permission.py |
| 2.6 | 增强 session_store.py | agents_v2/session_store.py |
| 2.7 | 增强 provider.py | agents_v2/provider.py |

### Phase 3：迁移现有数据

| 步骤 | 内容 |
|------|------|
| 3.1 | 将 manifest.yaml 技能迁移为 SKILL.md 格式 |
| 3.2 | 创建 skill-creator 系统技能 |
| 3.3 | 创建 MEMORY.md 模板 |
| 3.4 | 更新 main.py 中的技能注册逻辑 |

### Phase 4：测试验证

| 步骤 | 内容 |
|------|------|
| 4.1 | 验证现有 Agent 功能不受影响 |
| 4.2 | 验证上下文压缩正常工作 |
| 4.3 | 验证 Skill 创建/安装/执行流程 |
| 4.4 | 验证记忆自动注入 |
| 4.5 | 验证错误恢复 |

## 5. 新增文件预估行数

| 文件 | 行数 | 说明 |
|------|------|------|
| context_engine.py | ~200 | 上下文引擎 |
| compaction.py | ~150 | 压缩引擎 |
| session_lock.py | ~30 | 并发锁 |
| skill_registry.py | ~200 | 技能注册表 + 发现 |
| skill_executor.py | ~120 | 技能执行器 |
| skill_creator.py | ~100 | skill-creator 核心 |
| skill_scanner.py | ~80 | 安全扫描 |
| **新增合计** | **~880** | |

| 文件 | 原行数 | 新行数 | 变化 |
|------|--------|--------|------|
| runtime.py | 294 | ~420 | +126 |
| skill_loader.py | 94 | ~150 | +56 |
| memory_store.py | 83 | ~140 | +57 |
| tool_registry.py | 144 | ~180 | +36 |
| permission.py | 56 | ~80 | +24 |
| session_store.py | 135 | ~160 | +25 |
| provider.py | 406 | ~430 | +24 |
| **改造合计** | 1212 | ~1560 | +348 |

**项目总计：约 +1230 行新代码**
