# 00 · 项目宪法（v4 · FROZEN CONTRACTS）

> 本文件是本项目所有"不可变"约定的**唯一真相源**。任何 AI 或人类开发者在产出代码、SQL、API、UI 交互之前，必须先确认本文件中相关条款的编号，并在 commit 前过一次 `tools/guards/` 校验。
>
> **修改流程**：本文档只有用户本人书面同意才能修改。任何 AI 修改本文件 = 立即回滚 + 作废当次会话产出。修改后必须更新 `contracts.lock`（SHA256）并触发 `tools/guards/` 全量回归。
>
> 相关文档：
> - [10_scope_and_order.md](10_scope_and_order.md) · 范围与执行顺序
> - [18_anti_drift.md](18_anti_drift.md) · 防跑偏六层机制
> - [19_ai_capability.md](19_ai_capability.md) · Agent 能力体系
> - [30_contracts/](../30_contracts/) · 数据库 / 字段 / API 契约

---

## §C1 · 基础数据表 · CANONICAL_12 列序冻结

`fund_events` 是本系统的事实表。其 12 列 canonical schema 列序、列名、枚举值冻结：

| # | 列名 | 类型 | NULL | 语义 |
|---|---|---|---|---|
| 1 | business_date | DATE | NO | 业务日期 |
| 2 | entity_code | VARCHAR(50) | NO | 法人/单位编码 |
| 3 | entity_name | VARCHAR(200) | NO | 法人/单位名称 |
| 4 | account_code | VARCHAR(50) | NO | 账户编码 |
| 5 | account_name | VARCHAR(100) | NO | 账户名称 |
| 6 | summary | VARCHAR(500) | YES | 摘要 |
| 7 | counterparty | VARCHAR(200) | YES | 对方 |
| 8 | amount_in | NUMERIC(18,2) | NO | 收入（DEFAULT 0） |
| 9 | amount_out | NUMERIC(18,2) | NO | 支出（DEFAULT 0） |
| 10 | rolling_balance | NUMERIC(18,2) | YES | 滚动余额 |
| 11 | state | VARCHAR(20) | NO | 状态枚举（默认"正常"） |
| 12 | source | VARCHAR(20) | NO | 来源枚举 |

CHECK 约束：
- NOT (amount_in > 0 AND amount_out > 0) -- 互斥
- amount_in >= 0 AND amount_out >= 0 -- 非负
- state IN ('正常','待确认','异常','已作废')
- source IN ('网银导入','手工录入','现金录入','票据录入','财务公司单据')

不变量：
- 12 列列序 / 列名 / 枚举值冻结，新增字段一律走辅助列（batch_id / parser_artifact_id / created_at / updated_at）
- §C8 脚本编排模式下，运行时填入 fund_events 的代码必须来自 Parser/Rule artifact，不得有其它路径。执行由 artifact runtime 确定性完成，不由 Agent 运行期决策

---

## §C2 · 现金日记账月账模板 · 18 占位符不可变 `TEMPLATE_18`

现金日记账是唯一必须交付的报表模板。其 Excel 模板的占位符集合冻结如下：

```
报表标题, 开始期间, 结束期间, 板块, 核算方式,
开户行, 账户信息, 银行编号,
月, 日,
月初余额, 摘要, 收入, 支出, 余额,
本月收入小计, 本月支出小计, 月末余额
```

**18 个，一个不多一个不少。** 每个占位符必须在 Rule artifact 的 `PLACEHOLDER_BINDINGS` 中有且仅有一条绑定。违反 = `tools/guards/check_placeholder_binding.py` 拒绝 commit。

未来新增报表（农民工工资表、集团资金日报等）走 `template.inference` skill，自动识别占位符并登记到**动态占位符字典**；不影响 §C2 本身。

---

## §C3 · 账户数据中心 · 20 列不可变 `MASTER_20`

```
1.  核算组织 (org_segment)        13. 币种 (currency)
2.  单位名称 (entity_name)         14. 期初余额 (initial_balance)
3.  单位简称 (entity_short_name)   15. 余额日期 (balance_date)
4.  单位编码 (entity_code)         16. 是否纳入日报 (include_in_daily_report)
5.  开户银行 (bank_name)           17. 是否允许手工录入 (allow_manual_entry)
6.  银行账号 (account_number)      18. 状态 (status)
7.  账户名称 (account_name)        19. 备注 (notes)
8.  账户编号 (account_code)        20. (预留)
9.  账户后四位 (account_last_four)
10. 账户类型 (account_type)        ← 枚举见 §C3.1
11. 资金类型 (instrument_type)     ← 枚举见 §C3.2
12. 是否网银 (has_online_banking)
    录入方式 (input_method)        ← 枚举见 §C3.3
```

### §C3.1 · `account_type` 枚举

```
{ 基本户, 一般户, 临时户, 现金账户, 农民工工资专用账户 }
```

### §C3.2 · `instrument_type` 枚举

```
{ 银行存款, 现金, 票据, 信用证, 保证金 }
```

### §C3.3 · `input_method` 枚举

```
{ 网银, 手工, 现金, 票据, 财务公司 }
```

---

## §C4 · Agent 技能体系

### §C4.1 · 单通用 Agent 原则

本项目只有一个通用 Agent（`backend/agents/runtime.py`），不存在独立的 FundAgent、ReportAgent、ParserAgent、RuleAgent 等领域 Agent 类。

- 不允许新增领域 Agent 类
- 不允许新增领域专用调度器（如 harness_strict）
- 不允许新增对 `backend/agents/fund/` 的依赖
- 不允许新增 `fund_skill_run` 调用
- 不允许新增 `/api/fund/agent/skills/*/invoke` 路由或调用

### §C4.2 · 通用 Agent 初始技能与动态技能体系

通用 Agent 初始具备以下财务相关技能，可通过 `skill_creator` 动态创建新技能：

| # | 能力方向 | 职责 | 输入 | 输出 |
|---|---|---|---|---|
| 1 | 银行流水解析器生成 | 生成银行流水解析器 | 流水样本 + 账户上下文 | ParserArtifact（Python 代码） |
| 2 | 手工流水解析器生成 | 生成手工流水解析器 | 手工表单字段映射 | ParserArtifact |
| 3 | 报表填充规则生成 | 生成报表填充规则 | 已标占位符的模板 + 字段字典 | RuleArtifact |
| 4 | 规则维护迭代 | 维护/迭代现有规则 | 原 Rule + 修改需求 | 新版 RuleArtifact |
| 5 | 模板占位符识别 | 识别模板占位符并出规则草稿 | 空白 Excel 模板 | 占位符列表 + RuleArtifact 草稿 + 置信度 |

> **注意**：上述能力方向不代表固定的 5 个 skill 绑定。技能由通用 Agent 统一调度，不得绑定到领域专用调度器。`backend/agents/fund/` 是旧 FundAgent 中间态，待迁移后删除。

### §C4.3 · 技能创建机制

- Agent 可通过 `skill_creator` 动态创建新技能（如处理新银行格式、新报表类型）
- 用户可要求 Agent 创建技能，也可在 Agent 设置中管理已有技能
- 新技能遵循标准 SKILL.md 格式（frontmatter + body）
- 技能存放在 `agents/{agent_code}/skills/` 或 `agents/system/skills/` 目录
- 技能通过 `SkillRegistry` 自动发现、热加载、匹配触发

详细能力配置见 [19_ai_capability.md](19_ai_capability.md)。

清理审计基线见 [00_single_agent_cleanup_audit.md](00_single_agent_cleanup_audit.md)。

---

## §C5 · 基元库白名单

基元库是 Parser 和 Rule artifact **唯一允许调用的函数集合**。白名单清单见 [`../30_contracts/25_primitives_whitelist.md`](../30_contracts/25_primitives_whitelist.md)，当前冻结为 **37 个函数** 分布在 **7 个子模块**：

```
fund.primitives.sheet_ops       · 6 个
fund.primitives.value_parsers   · 5 个
fund.primitives.canonical       · 4 个
fund.primitives.master_match    · 4 个
fund.primitives.base_queries    · 6 个
fund.primitives.aggregations    · 6 个
fund.primitives.template_fill   · 6 个
```

Parser/Rule artifact 的 AST 扫描必须满足：
- 所有顶层 `import` 和 `from ... import` 的目标模块路径必须以 `fund.primitives.` 开头，或属于 Python 标准库的 **白名单子集**（`datetime / decimal / typing / re`）
- 禁止 `pandas / numpy / requests / os / sys / subprocess / pathlib / open()` 等

此限制仅适用于 Parser/Rule artifact（脚本编排产物）。Agent 通用工具（db_ops / fs / openpyxl_ops 等）不受此限。

违反 = `tools/guards/check_primitives_whitelist.py` 拒绝 commit。

---

## §C6 · 数据库 · 当前活动表集合

以下为当前 `backend/db/tables.py` 中 `__tablename__` 定义的全部 24 张业务 ORM 表。`sqlite_sequence` 为 SQLite 系统表，不计入业务表。

```
── 主数据模块（6 张）──
1.  divisions
2.  entities
3.  banks
4.  accounts
5.  account_aliases
6.  users

── 手工流水配置（2 张）──
7.  manual_field_pool
8.  manual_template_schemes

── 流水事实（2 张）──
9.  import_batches
10. fund_events                    ← CANONICAL_12（§C1）

── Agent 产物（3 张）──
11. parser_artifacts               ← ParserArtifact 银行/手工解析器
12. rule_artifacts                 ← RuleArtifact 报表填充规则
13. template_inference_job

── 报表（2 张）──
14. report_templates
15. daily_report_runs

── AI / 日志（3 张）──
16. ai_configs
17. ai_call_logs
18. operation_logs

── Agent 系统（6 张）──
19. agents_v2                      ← Agent 实例
20. skills_v2                      ← 技能注册表
21. agent_sessions                 ← Agent 会话
22. agent_messages                 ← Agent 消息（含工具调用和推理内容）
23. agent_runs                     ← Agent 运行记录
24. agent_memories                 ← Agent 记忆存储
```

已移除：`parser_templates` — Alembic `005_drop_parser_templates` 中移除，禁止恢复。
已移除：`agent_configs` — 无对应 ORM 类，功能合并入 `agents_v2`。

合计 24 张业务 ORM 表。完整 DDL 见 [`../30_contracts/20_database_schema.md`](../30_contracts/20_database_schema.md) §T1-§T7。

---

## §C7 · API 端点

API 端点清单见 [`../30_contracts/23_api_contracts.md`](../30_contracts/23_api_contracts.md)。

原始设计 42 端点上限，因 Agent 系统扩展已追加至 59 个端点。后续新增端点需更新 `23_api_contracts.md`。

统一响应格式（强制）：

```json
{ "code": 0, "message": "ok", "data": {} }
```

错误码对照见 `23_api_contracts.md` §错误码表。

---

## §C8 · 脚本编排确定性原则

对于准确性关键任务（流水导入、报表生成、数据汇总），Agent 生成脚本（Parser/Rule artifact），脚本确定性执行。执行阶段**禁止调用任何 LLM**：

- 流水导入执行（Parser artifact 已就绪 → 纯代码执行）
- 报表生成执行（Rule artifact 已就绪 → 纯代码执行）
- 写库、汇总、导出

Agent 处理非脚本任务（回答问题、生成文档、分析建议、技能创建）时正常使用 AI 能力，不受此限制。

违反（脚本编排产物执行阶段调用 LLM） = CRITICAL 级缺陷，直接回滚 PR。

---

## §C9 · 用户零编程原则

目标用户是中国财务人员（出纳、会计），**不会编程、不会写模板、不会配字段映射**。系统所有页面必须满足：

- 用户只需点击按钮、上传 Excel、下载 Excel
- 不暴露任何 JSON 编辑、正则表达式、字段映射配置界面
- 模板识别 / 字段匹配 / 规则生成**全部由 Agent 完成**
- 所有 AI 产出必须可见可审（前端展示版本号、样本校验结果、可接受 / 拒绝）

违反 = HIGH 级缺陷。

---

## §ChangeFlow · 契约修改流程

1. 用户本人书面同意（不能是"你看着办"或"都可以"）
2. 修改对应章节，更新末尾的 `v` 版本号和日期
3. 运行 `tools/guards/check_contract_hash.py --update` 重算 `contracts.lock`
4. Commit 消息必须以 `chore(constitution):` 开头
5. 触发 `tools/guards/` 全量回归
6. 在 commit message 中说明 why / what / impact

---

## 锚点速查

```
§C1  · CANONICAL_12 基础数据表
§C2  · 18 占位符模板
§C3  · 20 列账户主数据
§C4  · Agent 技能体系（单通用 Agent + 初始技能 + 动态创建）
§C5  · 基元库白名单
§C6  · 当前活动表集合（24 张业务 ORM 表）
§C7  · API 端点清单
§C8  · 脚本编排确定性原则
§C9  · 用户零编程原则
§ChangeFlow · 修改流程
```

---

**版本**
- v4.3 · 2026-05-10 · §C4 重写为单通用 Agent 技能体系；§C6 "Fund Agent 产物"改为"Agent 产物"；§C8 补充 artifact runtime 确定性执行说明；新增 §C4.1 单通用 Agent 原则
- v4.2 · 2026-05-10 · 修正 §C6 表清单为当前 24 张业务 ORM 表（sqlite_sequence 不计入业务表，agent_configs 无 ORM 不计入，parser_templates 已移除）
- v4.1 · 2026-05-10 · §C6 移除 parser_templates，27 表；ParserArtifact / RuleArtifact 替代旧模板体系
- v4.0 · 2026-05-02 · §C4 改为动态技能体系、§C6 更新 28 表、§C7 更新端点数、§C8 改为脚本编排确定性、§ChangeFlow 删除已归档目录引用
- v3.0 · 2026-04-23 · AI-First artifact 方案
- v2 · 原英文版归档见 git 历史
