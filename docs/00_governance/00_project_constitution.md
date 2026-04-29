# 00 · 项目宪法（v3 · FROZEN CONTRACTS）

> 本文件是本项目所有"不可变"约定的**唯一真相源**。任何 AI 或人类开发者在产出代码、SQL、API、UI 交互之前，必须先确认本文件中相关条款的编号，并在 commit 前过一次 `tools/guards/` 校验。
>
> **修改流程**：本文档只有用户本人书面同意才能修改。任何 AI 修改本文件 = 立即回滚 + 作废当次会话产出。修改后必须更新 `contracts.lock`（SHA256）并触发 `tools/guards/` 全量回归。
>
> 相关文档：
> - [01_v1_scope_and_order.md](01_v1_scope_and_order.md) · V1 范围与执行顺序
> - [08_anti_drift.md](08_anti_drift.md) · 防跑偏六层机制
> - [09_ai_capability_v3.md](09_ai_capability_v3.md) · Fund Agent 能力配置
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
- §C8 Runtime 无 AI 原则下，运行时填入 fund_events 的代码必须来自 Parser/Rule artifact，不得有其它路径

---

## §C2 · 现金日记账月账模板 · 18 占位符不可变 `TEMPLATE_18`

现金日记账是 V1 唯一必须交付的报表模板。其 Excel 模板的占位符集合冻结如下：

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

## §C4 · Fund Agent · 5 skill 不可增不可减

V1 阶段 Fund Agent 仅有且必有如下 5 个 skill：

| # | skill | 职责 | 输入 | 输出 |
|---|---|---|---|---|
| 1 | `parser.bank` | 生成银行流水解析器 | 流水样本 + 账户上下文 | Parser artifact（Python 代码） |
| 2 | `parser.manual` | 生成手工流水解析器 | 手工表单字段映射 | Parser artifact |
| 3 | `rule.template_fill` | 生成报表填充规则 | 已标占位符的模板 + 字段字典 | Rule artifact（`PLACEHOLDER_BINDINGS + LOOP`） |
| 4 | `rule.maintain` | 维护/迭代现有规则 | 原 Rule + 修改需求 | 新版 Rule artifact |
| 5 | `template.inference` | 自动识别空白模板的占位符并出规则草稿 | 空白 Excel 模板 | 带占位符的模板 + Rule artifact 草稿 + 置信度 |

> 任何"第 6 个 skill"的新增 = 违反 §C4。如需新增必须走 §ChangeFlow。

详细能力配置见 [09_ai_capability_v3.md](09_ai_capability_v3.md)。

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

违反 = `tools/guards/check_primitives_whitelist.py` 拒绝 commit。

---

## §C6 · 数据库 · v3 活动表集合

```
1. divisions
2. entities
3. banks
4. accounts
5. account_aliases
6. parser_templates                ← 仍在用作"已生效模板列表" UI 渲染（与 parser_artifacts 互补）
7. manual_field_pool
8. manual_template_schemes
9. import_batches
10. fund_events                    ← CANONICAL_12（§C1）
11. daily_report_runs
12. ai_configs
13. ai_call_logs
14. agent_configs
15. operation_logs
16. users
17. report_templates
18. parser_artifacts               ← Fund Agent 长期记忆（§7.2）
19. rule_artifacts                 ← 同上
20. template_inference_job         ← template.inference 三阶段流水线状态表
```

合计 20 表。完整 DDL 见 [`../30_contracts/20_database_schema.md`](../30_contracts/20_database_schema.md) §T1-§T6。

---

## §C7 · API · 42 端点清单上限

API 端点总数上限 **42**（见 [`../30_contracts/23_api_contracts.md`](../30_contracts/23_api_contracts.md)）。任何新增端点必须：
- 属于 42 条清单之一，**或**
- 走 §ChangeFlow 追加并更新 `23_api_contracts.md`

统一响应格式（强制）：

```json
{ "code": 0, "message": "ok", "data": {} }
```

错误码对照见 `23_api_contracts.md` §错误码表。

---

## §C8 · Runtime 无 AI 原则

以下阶段**禁止调用任何 LLM**：
- 流水导入执行（Parser artifact 已就绪 → 纯代码执行）
- 报表生成执行（Rule artifact 已就绪 → 纯代码执行）
- 写库、汇总、导出

LLM 仅在以下阶段可调用：
- Fund Agent 的 5 个 skill 被**显式触发**时
- AI 配置的连接测试

违反 = CRITICAL 级缺陷，直接回滚 PR。

---

## §C9 · 用户零编程原则（新增 v3）

目标用户是中国财务人员（出纳、会计），**不会编程、不会写模板、不会配字段映射**。系统所有页面必须满足：

- 用户只需点击按钮、上传 Excel、下载 Excel
- 不暴露任何 JSON 编辑、正则表达式、字段映射配置界面
- 模板识别 / 字段匹配 / 规则生成**全部由 Fund Agent 完成**
- 所有 AI 产出必须可见可审（前端展示版本号、样本校验结果、可接受 / 拒绝）

违反 = HIGH 级缺陷。

---

## §ChangeFlow · 契约修改流程

1. 用户本人书面同意（不能是"你看着办"或"都可以"）
2. 修改对应章节，更新末尾的 `v` 版本号和日期
3. 运行 `tools/guards/check_contract_hash.py --update` 重算 `contracts.lock`
4. Commit 消息必须以 `chore(constitution):` 开头
5. 触发 `tools/guards/` 全量回归
6. 在 `docs/60_claude_code_support/HANDOFF/` 写一份 `constitution_change_YYYYMMDD.md` 说明 why / what / impact

---

## 锚点速查

```
§C1  · CANONICAL_12 基础数据表
§C2  · 18 占位符模板
§C3  · 20 列账户主数据
§C4  · 5 个 skill
§C5  · 基元库白名单
§C6  · v3 活动表集合
§C7  · 42 API 端点 + 响应格式
§C8  · Runtime 无 AI
§C9  · 用户零编程原则
§ChangeFlow · 修改流程
```

---

**版本**
- v3.0 · 2026-04-23 · 基于 AI-First 反转和现状盘点重写（覆盖 v1 / v2）
- v2 · 原英文版归档见 git 历史
