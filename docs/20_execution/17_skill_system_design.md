# 技能系统完整技术设计文档

> 版本: 3.0 · 2026-05-06 · 基于 4 项目源码深度研究 + 本项目实际需求
>
> 研究来源：Hermes Agent（agent/skill_*.py + tools/skill_*.py）、Codex skill-creator、OpenClaw skills 系统、Claude Code superpowers

---

## §0 · 4 项目源码研究提炼

> 本章记录从本地安装的 4 个项目源码中提炼的 skill 系统核心设计。

### §0.1 Hermes Agent（最成熟的 skill 系统）

**源码位置**：`AppData/Local/Temp/zf-agent-connectors-research/hermes-agent/`

| 文件 | 核心职责 | 关键设计 |
|------|---------|---------|
| `agent/skill_utils.py` | frontmatter 解析 + 平台匹配 + 渐进加载 | CSafeLoader 优化、`platforms: [macos]` 声明、EXCLUDED_SKILL_DIRS |
| `agent/skill_commands.py` | slash 命令调用技能 + config 注入 | 从 skill frontmatter 的 `metadata.hermes.config` 读取配置值注入 |
| `agent/skill_preprocessing.py` | 模板变量替换 + 内联 shell 展开 | `${HERMES_SKILL_DIR}` 替换、`!`date +%Y-%m-%d`` 内联执行 |
| `tools/skill_manager_tool.py` | Agent 自主管理技能 CRUD | create/edit/patch/delete/write_file/remove_file 六个操作、安全扫描可选 |
| `tools/skills_tool.py` | 渐进披露加载 + 环境检查 | `SkillReadinessStatus`(available/setup_needed/unsupported)、注入检测 |
| `tools/skills_guard.py` | 安全扫描（正则 + AST） | 信任级别(builtin/trusted/community/agent-created)、威胁模式库(20+模式) |
| `tools/skills_hub.py` | GitHub 注册表 + 分发 | SkillSource ABC、GitHubAuth(PAT/gh/App)、HubLockFile、quarantine |
| `tools/skills_sync.py` | 打包技能同步 + 哈希跟踪 | MD5 检测用户修改、用户定制过的技能永不覆盖 |

**核心设计模式**：
1. **单一真相源**：所有技能统一在 `~/.hermes/skills/`（bundled + hub-installed + agent-created 共存）
2. **信任分级**：builtin（不扫描）→ trusted（openai/skills, anthropics/skills）→ community（任何扫描发现都阻止）
3. **用户定制保护**：skills_sync 用哈希检测用户是否修改过技能，修改过的永不覆盖
4. **Agent 可自创建技能**：skill_manager_tool 允许 Agent 创建/编辑/删除技能
5. **安全扫描可选**：`skills.guard_agent_created` 默认关闭（Agent 已经能通过 terminal 执行同样代码）

### §0.2 Codex / Claude Code（官方 skill-creator）

**源码位置**：`.codex/skills/skill-creator/SKILL.md`

**核心设计理念**：
1. **上下文窗口是公共资源** — 技能必须精简，只包含 Claude 不知道的信息
2. **自由度匹配** — 高自由度（文本指令）/ 中自由度（伪代码+参数）/ 低自由度（固定脚本）
3. **三类捆绑资源**：
   - `scripts/` — 可执行代码，可脱离上下文直接运行
   - `references/` — 参考文档，按需加载（SKILL.md 中引用）
   - `assets/` — 模板/图片等，用于输出而非阅读
4. **description 是主触发机制** — 不是 triggers 字段，而是 description 中的内容
5. **skill-comply** — 自动测量技能合规率，3 级 prompt 严格度测试

**关键引用**：
> "Default assumption: Claude is already very smart. Only add context Claude doesn't already have."
> "Scripts may still need to be read by Claude for patching or environment-specific adjustments."
> "Avoid deeply nested references — Keep references one level deep from SKILL.md."

### §0.3 OpenClaw

**源码位置**：`AppData/Roaming/npm/node_modules/openclaw/`

- 技能存储在 `~/.openclaw/skills/`
- ClawHub：公共技能注册表，CLI 命令 publish/install
- 多 Agent 路由：不同 channel 可以路由到不同 agent
- 渐进披露：与 Hermes 兼容的 SKILL.md 格式

### §0.4 跨项目共识

| 设计原则 | Hermes | Codex | OpenClaw | 本项目采纳 |
|----------|--------|-------|----------|-----------|
| SKILL.md 为统一格式 | ✓ | ✓ | ✓ | ✓ |
| 渐进披露（metadata → body → assets） | ✓ | ✓ | ✓ | ✓ |
| description 是主触发机制 | ✓ | ✓（明确说明） | ✓ | ✓ |
| scripts 可脱离上下文执行 | ✓ | ✓ | - | ✓ |
| 安全扫描 | ✓（20+威胁模式） | - | ✓ | ✓（需增强） |
| 信任级别 | ✓（4级） | - | ✓ | ✓ |
| Agent 可自主创建技能 | ✓ | ✓ | - | ✓ |
| 打包分发 | ✓（hub） | ✓（.skill文件） | ✓（ClawHub） | 后续 |
| 用户定制保护 | ✓（MD5哈希） | - | - | ✓ |
| 经验/进化 | ✓（memory集成） | - | - | ✓ |

---

## §1 · 问题诊断

### §1.1 当前系统的 5 个根本缺陷

| # | 缺陷 | 表现 | 根因 |
|---|------|------|------|
| D1 | 两套技能范式断联 | SKILL.md 指令式 vs manifest.yaml+run.py 代码式互不认识 | 没有统一格式 |
| D2 | 技能创建流程缺失 | skill_creator 只能生成骨架 SKILL.md，用户实际靠手动搬代码 | 没有"工作代码→技能"管道 |
| D3 | 技能执行不可靠 | LLM 经常忽略注入的技能指令 | 指令是"建议"不是"命令" |
| D4 | 无自进化能力 | 420 行硬编码的实体名、账户别名从不更新 | 没有经验积累机制 |
| D5 | 无外部导入能力 | 无法从其他 Agent 或外部来源引入技能 | 只有基本安装器 |

### §1.2 与 4 项目的差距分析

| 能力 | Hermes | Codex | 本项目现状 | 差距 |
|------|--------|-------|-----------|------|
| 技能目录布局 | SKILL.md + scripts/ + references/ + assets/ | 同左 | SKILL.md + run.py | **缺少 scripts/references/assets** |
| 渐进披露 | L1 metadata → L2 body → L3 resources | 同左 | L1/L2 已有 | **L3 资源按需加载缺失** |
| 安全扫描 | 20+ 威胁模式 + 信任分级 | - | 基础 AST 扫描 | **差距大** |
| Agent 自创建 | skill_manager_tool（6个操作） | skill-creator | skill_save（基本版） | **需要增强** |
| 用户定制保护 | MD5 哈希检测 | - | 无 | **需要实现** |
| 合规测量 | - | skill-comply | 无 | **后续** |

---

## §2 · 统一技能格式规范（v3，对标 Hermes/Codex）

### §2.1 技能目录结构

```
skills/{skill_name}/
├── SKILL.md              ← [必需] 元数据 + 工作流描述
├── run.py                ← [可选] 确定性执行代码（code/hybrid 模式）
├── scripts/              ← [可选] 可执行脚本（脱离上下文运行）
│   └── rotate_pdf.py
├── references/           ← [可选] 参考文档（按需加载进上下文）
│   └── bank_formats.md
├── assets/               ← [可选] 输出资源（模板/图片，不加载进上下文）
│   └── report_template.xlsx
├── tests/
│   ├── sample.xlsx       ← [可选] 测试样本
│   └── expected.json     ← [可选] 期望输出
├── experience.json       ← [自动生成] 积累的经验数据
└── .meta.json            ← [自动生成] 生命周期 + 统计 + 内容哈希
```

**三类捆绑资源的区分（来自 Codex skill-creator 研究成果）：**

| 类型 | 加载方式 | 用途 | 示例 |
|------|---------|------|------|
| `scripts/` | 可直接执行，不需要读入上下文 | 确定性计算、重复代码 | `scripts/calculate_tax.py` |
| `references/` | 按需读入上下文 | 参考文档、API 文档、字段字典 | `references/bank_columns.md` |
| `assets/` | 用于输出，不读入上下文 | 模板、图片、字体 | `assets/report_template.xlsx` |

### §2.2 SKILL.md Frontmatter 规范

```yaml
---
name: parse_boc                              # 必需，kebab-case，≤64字符
description: "中国银行流水智能解析，支持 xls/xlsx，自动识别列映射、生成会计摘要。当用户上传中行流水、中行对账单、BOC 流水时触发。"  # 必需，≤1024字符，这是主触发机制
version: "2.0.0"                             # 可选
execution_mode: code                         # instruction | code | hybrid
code_entry: ""                               # 旧体系字段，映射到 fund_skill_run。fund_skill_run 是旧桥接工具，待删除。新技能应通过通用 Agent 工具与 artifact service / artifact runtime 契约完成
allowed-tools:                               # 此技能可用的工具白名单
  - file_parse
  - db_query_business
  - skill_step_report
arguments:                                   # 技能参数定义
  file_path:
    description: "文件路径"
    required: true
triggers:                                    # 显式触发关键词（补充 description）
  - "中行流水"
  - "中国银行"
dependencies:                                # 依赖声明
  pip:
    - "xlrd==1.2.0"
---
```

**触发机制（对标 Codex）**：
- `description` 是**主触发机制**（Codex 明确说明"Include all when-to-use information here"）
- `triggers` 是**补充触发**，用于精确子串匹配
- `when_to_use` 降级为内部文档字段，不参与匹配

### §2.3 三种执行模式

| 模式 | 工作方式 | 自由度 | 文件要求 |
|------|---------|--------|---------|
| `instruction` | SKILL.md body 注入 LLM，LLM 按步骤调用工具 | **高自由度** — LLM 自主判断细节 | 仅 SKILL.md |
| `code` | 直接 import run.py 执行 run(params) | **低自由度** — 确定性执行 | SKILL.md + run.py |
| `hybrid` | run.py 执行核心 + SKILL.md 提供上下文 | **中自由度** — 脚本+指导 | SKILL.md + run.py |

**自由度原则（来自 Codex skill-creator）**：
> "窄桥旁边有悬崖需要具体护栏（低自由度），开阔的田野可以走多条路（高自由度）"

- 银行解析 = 低自由度（准确性关键，用 code 模式）
- 报表填充 = 中自由度（有规则但需灵活，用 hybrid）
- 创建技能 = 高自由度（多种方式都有效，用 instruction）

### §2.4 experience.json 格式

```json
{
  "stats": {
    "total_runs": 12,
    "successes": 11,
    "total_ms": 34200,
    "last_run_at": "2026-05-06T14:30:00"
  },
  "learned_aliases": {
    "交易日期": "business_date",
    "贷方发生额": "income_amount"
  },
  "corrections": [
    {"field": "summary", "from": "银行手续费", "to": "转账手续费", "at": "..."}
  ],
  "recent_errors": [
    {"error": "...", "at": "..."}
  ]
}
```

### §2.5 .meta.json 格式

```json
{
  "source": "agent_created",
  "lifecycle": "active",
  "pinned": false,
  "content_hash": "md5:abc123...",
  "created_at": "2026-05-01T10:00:00",
  "last_used_at": "2026-05-06T14:30:00",
  "version_history": ["1.0.0", "1.0.1", "2.0.0"]
}
```

**content_hash（来自 Hermes skills_sync）**：
- 技能首次安装/创建时记录内容哈希
- 同步时对比：如果用户修改过（哈希不同），永不覆盖
- 如果用户未修改（哈希相同），可以安全更新

---

## §3 · 技能创建流程

### §3.1 创建管道总览

```
用户意图 → 意图分析 → 模式选择 → 内容生成 → 安全扫描 → 验证 → 注册
```

### §3.2 四种创建场景

**场景 A：从工作代码保存（最常见）**
```
1. Agent 在对话中开发了可用的 Python 代码（如 boc_parser_v2.py）
2. 用户说"保存为技能"或 Agent 主动建议
3. 调用 skill_save(skill_code="parse_boc", run_py=<代码>, execution_mode="code")
4. 系统自动生成 SKILL.md + experience.json + .meta.json
5. 记录 content_hash
6. 注册到 SkillRegistry
```

**场景 B：从意图创建 instruction 技能**
```
1. 用户描述需求："创建一个解析招行流水的技能"
2. skill-creator 技能触发
3. 如果有样本文件 → file_parse 分析结构
4. Agent 设计分步工作流
5. 调用 skill_save(skill_code="parse_cmb", workflow_md=<工作流>, execution_mode="instruction")
6. 注册
```

**场景 C：从意图创建 code 技能**
```
1. 用户描述需求 + 提供样本文件
2. skill-creator 触发 → 选择 code 模式（低自由度，准确性关键）
3. Agent 分析样本 → 编写 run.py 代码
4. 调用 skill_save(skill_code="parse_cmb", run_py=<代码>, execution_mode="code")
5. 可选：自动用样本文件测试
6. 注册
```

**场景 D：从外部导入**
```
1. 用户提供 zip/目录/SKILL.md
2. 调用 skill_install
3. 格式检测 + 转换（见 §8.1）
4. 安全扫描（见 §8.2）
5. 记录 content_hash
6. 注册
```

### §3.3 工具 API 设计

```
skill_save(skill_code, display_name, description, run_py, workflow_md, execution_mode, triggers, **kwargs)
  → 创建新技能或覆盖已有技能（旧版本备份到 .archive/）
  → 自动生成 experience.json, .meta.json（含 content_hash）
  → 自动注册到 SkillRegistry + DB

skill_learn(skill_code, correction_type, wrong_value, correct_value)
  → 记录用户修正到 experience.json
  → correction_type: alias | summary | direction | mapping

skill_upgrade(skill_code, run_py, workflow_md, new_triggers)
  → 升级技能，自动备份旧版本
  → 版本号自动递增

skill_install(source_path, agent_code, auto_install_deps)
  → 从目录/zip 安装外部技能
  → 自动格式检测 + 转换 + 安全扫描

skill_test(skill_code, **kwargs)
  → 运行技能 + 比对 expected.json

skill_step_report(skill_code, step_number, step_name, result)
  → 步骤跟踪（instruction 模式）
```

---

## §4 · 技能执行流程

### §4.1 渐进披露（对标 Hermes skills_tool）

```
Level 1: name + description（始终在上下文中，~100 tokens）
  → 技能列表展示、触发匹配依据

Level 2: SKILL.md body（触发时加载，≤3000 字）
  → instruction 模式的完整步骤
  → code 模式的简短调用指令
  → 经验摘要（从 experience.json 生成）

Level 3: 捆绑资源（按需加载，不限大小）
  → references/*.md（参考文档）
  → scripts/*.py（可执行脚本）
  → assets/*（输出资源，不加载进上下文）
```

### §4.2 instruction 模式执行流

```
用户消息 "解析银行流水"
  ↓
skill_registry.trigger() → 匹配 fund_parser_bank
  ↓
format_skill_instruction(skill)
  → 生成 <active-skill> XML 标签包裹的指令
  → 步骤标记 [1/8 MANDATORY] [2/8 MANDATORY] ...
  → 注入经验摘要（从 experience.json）
  → 添加步骤跟踪指令
  → 列出可按需加载的 references（如果有）
  ↓
注入到 system prompt 的 <skill-context> 中
  ↓
LLM 按步骤执行，每步调用 skill_step_report 汇报
  ↓
完成，记录执行结果到 experience.json
```

### §4.3 code 模式执行流

```
用户消息 "解析中行流水"
  ↓
skill_registry.trigger() → 匹配 parse_boc
  ↓
format_skill_instruction(skill)
  → 生成简短 code 指令：调用 skill_run(skill_code="parse_boc", ...)
  → 注意：fund_skill_run 是旧桥接工具，待删除，不得作为新技能的执行路径
  ↓
LLM 调用 skill_run 工具
  ↓
execute_skill_code() → import run.py → run(params)
  → params 中注入 _experience 数据（learned_aliases, corrections）
  → 记录执行结果到 experience.json
  → 更新 .meta.json last_used_at
  ↓
返回结果
```

### §4.4 hybrid 模式执行流

```
同 code 模式执行 run.py
+ SKILL.md body 作为额外上下文注入（用于 LLM 解释结果或处理异常）
+ LLM 可以读取 references/ 中的补充信息
```

---

## §5 · 技能自进化机制

### §5.1 进化层次

| 层次 | 机制 | 触发条件 | 存储 |
|------|------|---------|------|
| L1 被动记录 | 记录执行成功/失败统计 | 每次执行 | experience.json → stats |
| L2 修正学习 | 记录用户修正 | 用户说"这个不对" | experience.json → corrections |
| L3 别名学习 | 记录新的字段别名映射 | 用户或 Agent 发现新映射 | experience.json → learned_aliases |
| L4 规则优化 | 自动更新 run.py 中的规则 | 积累足够修正后（≥3次同类） | run.py |
| L5 知识提炼 | 从多次执行中提炼通用模式 | N 次成功执行后 | memory 系统 |

### §5.2 进化实现

**L1-L3（已实现）：**
- `execute_skill_code()` 每次执行后调用 `_record_execution()` 更新 stats
- `skill_learn()` 工具记录修正和别名
- instruction 模式通过 `_format_experience_summary()` 注入经验摘要
- code 模式通过 `params["_experience"]` 注入经验数据

**L4 规则优化（待实现）：**
```
当 experience.json 中同一类型修正 ≥3 次时：
  → Curator 建议升级技能
  → skill_upgrade() 自动更新 run.py 中的规则
  → 例如：3次修正 "银行手续费→转账手续费" → 自动更新 FEE_PATTERNS
```

**L5 知识提炼（待实现）：**
```
当 parse_boc 成功执行 ≥10 次：
  → 提炼：该银行的列位置、日期格式、金额格式的稳定模式
  → 保存到 memory 系统
  → 创建新的 bank-specific 技能时可以参考
```

---

## §6 · 触发匹配策略

### §6.1 description 为主触发机制（对标 Codex）

Codex skill-creator 明确指出：
> "description is the primary triggering mechanism for your skill"

因此触发策略调整为：

```
Level 0: description 全文匹配（权重最高）
  → description 中的关键词出现在用户输入中
  → 这是 Codex 推荐的方式

Level 1: 精确子串匹配 triggers 字段
  → "解析银行流水" in "帮我解析银行流水文件" → 命中

Level 2: 名称精确匹配
  → skill.name 完整出现在用户输入中（≥3字符）

Level 3: 关键词 bigram 匹配（从 description + when_to_use 提取 2-4 字片段）
  → 至少命中 2 个不同关键词
```

### §6.2 匹配结果处理

```
有匹配 → 注入匹配技能的完整指令（instruction）或 code 指令
无匹配 → 注入 L1 摘要（所有技能的 name+description，供 LLM 自主判断）
```

---

## §7 · 技能生命周期管理

### §7.1 状态流转

```
draft → active → stale → archived
  ↑       │                  │
  └───────┘                  │
  (skill_upgrade)           (手动恢复)
```

| 状态 | 含义 | 触发条件 |
|------|------|---------|
| draft | 刚创建，未验证 | skill_save 创建 |
| active | 正常可用 | 首次成功执行 |
| stale | 30天未使用 | Curator 检查 |
| archived | 90天未使用 | Curator 归档 |
| pinned | 永不过期 | 用户手动标记 |

### §7.2 Curator 增强（对标 Hermes）

```
每次审查：
  1. 检查 experience.json stats
  2. 如果 success_rate < 50% → 标记为需要修复
  3. 如果有 ≥3 条同类修正 → 建议升级
  4. 如果 total_runs > 10 且 success_rate > 90% → 建议标记为 verified
  5. 更新 .meta.json lifecycle 状态
  6. 对比 content_hash：如果技能被外部修改，重新记录哈希
```

---

## §8 · 外部技能转换

### §8.1 格式检测与转换矩阵

| 来源格式 | 检测条件 | 转换动作 | 目标模式 |
|----------|---------|---------|---------|
| SKILL.md only | 有 SKILL.md，无 run.py | 直接使用 | instruction |
| run.py only | 有 run.py，无 SKILL.md | 生成 wrapper SKILL.md | code |
| SKILL.md + run.py | 两者都有 | 直接使用 | hybrid |
| manifest.yaml + run.py | 有 manifest.yaml | 读取 manifest 生成 SKILL.md | code |
| Claude Code SKILL.md | 只有 name+description+body | 添加 execution_mode 等字段 | instruction |
| zip 包 | 解压后检测 | 按上述规则处理 | 自动 |
| 裸 Python 文件 | 单个 .py 文件 | 包装为 run.py + 生成 SKILL.md | code |

### §8.2 安全扫描（对标 Hermes skills_guard）

**信任级别（来自 Hermes）**：

| 级别 | 含义 | 安装策略 |
|------|------|---------|
| builtin | 随产品发布 | 不扫描，始终信任 |
| trusted | 已知可靠来源 | 扫描但仅阻止危险级别 |
| community | 未知来源 | 扫描发现任何问题都阻止 |
| agent-created | Agent 自己创建 | 可选扫描（默认关闭） |

**威胁模式库（来自 Hermes skills_guard，20+ 模式）**：

| 类别 | 示例模式 | 严重级别 |
|------|---------|---------|
| 数据泄露 | `curl ... $API_KEY` | critical |
| 注入攻击 | `ignore previous instructions` | high |
| 破坏性操作 | `rm -rf /` | critical |
| 持久化 | `crontab -r` | high |
| 网络通信 | `requests.post(secret_url)` | medium |
| 混淆 | `exec(decode(...))` | high |

### §8.3 用户定制保护（来自 Hermes skills_sync）

```
首次安装 → 记录 SKILL.md 的 MD5 哈希到 .meta.json.content_hash
后续同步 → 对比当前哈希 vs 记录哈希
  → 哈希相同（用户未修改）→ 可以安全更新
  → 哈希不同（用户修改过）→ 跳过更新，保护用户定制
```

---

## §9 · 实现计划

### Phase 1: 基础架构（已完成 ✓）
- [x] 统一 SKILL.md 格式（含 execution_mode）
- [x] 迁移 manifest.yaml 技能
- [x] skill_save / skill_learn / skill_upgrade 工具
- [x] experience.json 机制
- [x] 触发匹配三级策略
- [x] instruction 模式强制指令格式

### Phase 2: 执行管道（已完成 ✓）
- [x] code 模式执行：runtime 检测到 code 技能时，直接调 run.py 而非仅注入指令
- [x] skill_run 工具增强：区分 code/instruction 执行路径，instruction 模式拒绝调用
- [x] 经验注入：code 模式执行时将 experience 数据注入 params._experience
- [x] 执行结果记录：每次执行后更新 experience.json + .meta.json last_used_at
- [x] L3 资源按需加载：references/ 目录扫描 + 安全校验 + load_skill_reference()
- [x] fund_skill_run 经验记录：执行后记录到对应系统技能的 experience.json（注：fund_skill_run 是旧桥接工具，待删除）
- [x] Curator 经验分析：成功率 <50% 标记需修复，≥3 次同类修正建议升级，>10 次且 >90% 建议标记 verified

### Phase 3: 创建管道（已完成 ✓）
- [x] skill-creator SKILL.md 更新：引导 LLM 正确使用 skill_save + 自由度概念（v3.0）
- [x] 从工作代码创建技能的完整流程（skill_save 工具）
- [x] 自动测试增强：skill_test 支持 test_params.json + 新执行路径
- [x] content_hash 记录：首次创建时记录 MD5 哈希到 .meta.json

### Phase 4: 自进化增强（已完成 ✓）
- [x] Curator 增强：基于 experience stats 做智能决策（成功率/修正/verified）
- [x] 修正累积规则：≥3 次同类修正 → 建议升级
- [x] 经验数据注入到 instruction 模式的 prompt 中（_format_experience_summary）

### Phase 5: 安全与导入（已完成 ✓）
- [x] 安全扫描增强：20+ 威胁模式（正则 + AST）+ 信任级别门控
- [x] 信任级别：builtin/trusted/community/agent_created，不同级别不同扫描策略
- [x] 格式自动检测 + 转换：manifest.yaml→SKILL.md、裸 run.py→SKILL.md
- [x] 用户定制保护：content_hash 对比，用户修改过的技能永不覆盖
- [x] 裸 Python 文件包装：自动生成 SKILL.md + 从 docstring 提取描述

---

## §10 · 文件清单与职责

| 文件 | 职责 | 改动状态 |
|------|------|---------|
| `backend/agents/skill_registry.py` | 技能发现 + 加载 + 触发匹配 | ✓ 已改 |
| `backend/agents/skill_executor.py` | 统一执行器 + experience 管理 | ✓ 已改 |
| `backend/agents/skill_creator.py` | SKILL.md 模板 + 创建器 | ✓ 已改 |
| `backend/agents/skill_installer.py` | 安装/卸载/格式转换/定制保护 | ✓ Phase 5 |
| `backend/agents/skill_deps.py` | 依赖管理 | ✓ 已有 |
| `backend/agents/skill_scanner.py` | 安全扫描（20+ 威胁模式 + 信任级别 + AST） | ✓ Phase 5 |
| `backend/agents/curator.py` | 生命周期 + 经验分析 | ✓ Phase 4 |
| `backend/agents/tools/skill_ops.py` | 技能工具定义 | ✓ 已改 |
| `backend/agents/runtime.py` | 核心循环 + 技能集成 + code 自动执行 | ✓ Phase 2 |
| `backend/agents/prompt_builder.py` | system prompt 组装 | ✓ 已改 |
| `backend/agents/permission.py` | 工具权限配置 | ✓ 已改 |
| `agents/system/skills/*/SKILL.md` | 5 个系统技能 | ✓ 已改 |
| `agents/ag_*/skills/*/SKILL.md` | 用户技能迁移 | ✓ 已改 |
