# 09 · AI 能力配置（v3 · Fund Agent）

> 本文件定义 V1 阶段 Fund Agent 的完整能力边界。任何增加、删除、修改 skill 的操作都必须走 [00_project_constitution.md](00_project_constitution.md) §ChangeFlow。
> 配合 [08_anti_drift.md](08_anti_drift.md)、[../30_contracts/25_primitives_whitelist.md](../30_contracts/25_primitives_whitelist.md) 使用。

---

## §1 · 用户画像反推（为什么 AI 必须接管）

### §1.1 · 目标用户

- **职业**：中国企业财务人员（出纳、会计、资金主管）
- **工具习惯**：Excel、网银导出、财务软件（用友 / 金蝶 / 浪潮）
- **技术水平**：**不会编程**、**不会写正则**、**不会配 JSON**、**不会写 SQL**
- **年龄分布**：主力在 35–55 岁

### §1.2 · 这个用户画像的后果

| 如果我们让用户做 … | 会发生什么 |
|---|---|
| 写银行流水解析模板 | 立刻放弃 |
| 配占位符到字段的映射 | 立刻放弃 |
| 调正则表达式 | 立刻放弃 |
| 手动对齐列头到字段字典 | 勉强能做，错误率高 |
| 点按钮上传 Excel、下载 Excel | **可以** |

### §1.3 · 结论

**所有涉及"写代码、写规则、写映射"的活，必须由 AI 完成。用户只做点按钮 / 上传 / 下载。**
这是 §C9 用户零编程原则的理论基础，也是 Fund Agent 必须存在、必须在 Phase 0 就建好的原因。

---

## §2 · Fund Agent 架构

### §2.1 · 物理位置

```
backend/agents/fund/
├── AGENT.md          ← Agent 主提示词（职责、边界、工具清单）
├── harness.py        ← harness_strict 模式调度器
├── schemas.py        ← 输入/输出 JSON Schema（Pydantic）
├── memory.py         ← 样本库 / 字段字典 / 别名库的访问层
└── skills/
    ├── parser_bank.py
    ├── parser_manual.py
    ├── rule_template_fill.py
    ├── rule_maintain.py
    └── template_inference.py
```

### §2.2 · 执行模式 · harness_strict

**对比**：

| 模式 | 适合场景 | 本项目是否采用 |
|---|---|---|
| hermes-style 自由 agent | 探索型、多工具自选 | **否**（风险：AI 随便调工具、修契约） |
| harness_strict（2026 OpenAI） | 工具预定义、步骤固定、产物受约束 | **是** |
| ReAct 循环 | 推理 + 行动多轮交替 | 局部用于 `template.inference` 的置信度判断 |

harness_strict 强制：
- **工具白名单**：只能调 `backend/fund/primitives/` 白名单函数（§C5）
- **产物模板**：输出必须符合 Pydantic Schema（`schemas.py`）
- **步骤固定**：每个 skill 的执行步骤在代码中写死，AI 只填参数
- **沙箱执行**：Agent 生成的 Python 代码必须通过 AST 扫描（`tools/guards/check_primitives_whitelist.py`）再入库

---

## §3 · 5 个 Skill 详细规约（§C4）

### §3.1 · `parser.bank` · 生成银行流水解析器

**输入**：
```json
{
  "skill": "parser.bank",
  "account_code": "ZH0001",
  "sample_file": "uploads/batch-20260423/icbc_sample.xlsx",
  "field_dictionary_snapshot": "fixtures/field_dictionary.json",
  "alias_library_snapshot": "fixtures/alias_library.json",
  "privacy_mode": "standard"
}
```

**输出**（Parser artifact 草稿）：
```json
{
  "name": "ICBC_网银_v1",
  "kind": "bank",
  "account_code": "ZH0001",
  "code": "from fund.primitives.sheet_ops import ...\n\ndef parse(wb, ctx):\n    ...",
  "primitives_imports": ["sheet_ops.read_sheet", "value_parsers.parse_date", "canonical.emit_row"],
  "sample_check_log": {
    "sample_rows": 50,
    "parsed_rows": 50,
    "canonical_violations": 0,
    "amount_sum_in": "12345.67",
    "amount_sum_out": "8901.23"
  },
  "confidence": 0.94
}
```

**硬边界**：
- 只能调白名单基元库
- 输出的 `code` 必须通过 AST 扫描
- `sample_check_log.canonical_violations` 必须为 0 才能入库
- few-shot 至少 3 条该银行真实样本

### §3.2 · `parser.manual` · 生成手工流水解析器

**场景**：用户按"多主体 Excel"模式上传一份包含多家单位多账户的手工流水表。Agent 根据字段池（`manual_field_pool`）和模板方案（`manual_template_schemes`）生成解析器。

**输入 / 输出** 与 §3.1 结构相同，`kind="manual"`。

**额外约束**：
- 必须支持"一行一条" 和 "一行多科目"两种布局
- 必须识别"单位 / 账户 / 金额 / 摘要 / 对方 / 日期"6 个核心字段
- 对无法匹配的字段，生成 `state="待确认"` 的行，不丢数据

### §3.3 · `rule.template_fill` · 生成报表填充规则

**输入**：
```json
{
  "skill": "rule.template_fill",
  "template_job_id": 42,
  "placeholder_list": ["报表标题", "开始期间", ..., "月末余额"],
  "template_file": "uploads/templates/cash_journal_blank.xlsx"
}
```

**输出**（Rule artifact 草稿）：
```json
{
  "name": "现金日记账_月账_v1",
  "template_id": 42,
  "placeholder_bindings": {
    "报表标题":   { "primitive": "const",            "value": "现金日记账" },
    "开始期间":   { "primitive": "date_range_start", "params": {} },
    ...
  },
  "loop": { ... },
  "primitives_imports": ["template_fill.const", "template_fill.date_range_start", ...],
  "sample_check_log": {
    "placeholder_bound": 18,
    "placeholder_unbound": 0,
    "placeholder_extra": 0,
    "amount_match_rate": 0.998
  }
}
```

**硬边界**：
- 18 个占位符必须**恰好**全部覆盖（§C2）
- `placeholder_bindings` + `loop.columns` 的 key 合集 == 18 个占位符
- 生成的 bindings 只能引用白名单 primitives

### §3.4 · `rule.maintain` · 维护/迭代现有规则

**场景**：已有 `现金日记账_月账_v1`，用户说"合计行要加粗"/"日期格式改成 MM月DD日"。

**输入**：
```json
{
  "skill": "rule.maintain",
  "rule_id": 17,
  "change_request": "日期格式改成 MM月DD日",
  "user_id": "admin"
}
```

**输出**：新版 Rule artifact（v2），旧版保留。不覆盖。

### §3.5 · `template.inference` · 自动识别空白模板

**三阶段流水线**：

```
Stage A · 纯代码结构解析（无 AI）
  └─ 扫描 .xlsx / .xltx，找到 ${xxx} 或 {{xxx}} 或中文占位符
  └─ 识别合并单元格、行数据锚点、表头行
  
Stage B · AI 语义映射
  └─ 把 Stage A 的占位符列表传给 LLM
  └─ LLM 返回每个占位符对应的字段字典 key 和建议 primitive
  └─ 产出 Rule artifact 草稿 + 置信度
  
Stage C · 用户确认
  └─ 前端显示：占位符 → 绑定 → 置信度
  └─ 用户可接受 / 修改 / 拒绝
  └─ 接受 → 入库 rule_artifacts
```

**置信度规则**：
- 全部 ≥ 0.85 → 默认直接可用
- 任一 < 0.70 → 前端红色标注，强制人工确认
- 0.70–0.85 → 黄色提示，鼓励确认

---

## §4 · 字段字典 + 别名库（种子数据）

### §4.1 · 字段字典结构

路径：`seed/field_dictionary.json`

```json
{
  "business_date": {
    "cn_name": "日期",
    "type": "DATE",
    "aliases": ["日期", "交易日期", "记账日期", "业务日期", "入账日期", "发生日期"]
  },
  "entity_code": { "cn_name": "单位编码", "type": "VARCHAR", "aliases": ["单位编码","主体编码","组织编码"] },
  "entity_name": { "cn_name": "单位名称", "type": "VARCHAR", "aliases": ["单位","单位名称","主体","公司"] },
  "account_code": { "cn_name": "账户编码", "type": "VARCHAR", "aliases": ["账户编码","账号","ZH 编码"] },
  "account_name": { "cn_name": "账户名称", "type": "VARCHAR", "aliases": ["账户","账户名称","账户名"] },
  "summary":     { "cn_name": "摘要",     "type": "TEXT",    "aliases": ["摘要","用途","备注","说明","事项"] },
  "counterparty":{ "cn_name": "对方",     "type": "TEXT",    "aliases": ["对方","对方户名","往来单位","客户","付款方","收款方"] },
  "amount_in":   { "cn_name": "收入",     "type": "NUMERIC", "aliases": ["收入","贷方","进账","贷记","入账金额","收款","到账"] },
  "amount_out":  { "cn_name": "支出",     "type": "NUMERIC", "aliases": ["支出","借方","出账","借记","付款","付出"] },
  "rolling_balance": { "cn_name": "余额", "type": "NUMERIC", "aliases": ["余额","账户余额","滚动余额"] }
}
```

### §4.2 · 别名库

路径：`seed/alias_library.json`（运行时动态增长）

```json
{
  "ICBC": ["工商银行", "ICBC", "中国工商银行"],
  "DW0001": ["集团本部", "总部", "股份公司本部"]
}
```

Agent 每次成功识别后，把新发现的别名写回 `account_aliases` 表（§T1.1），由 `master_match.register_alias` 基元完成。

---

## §5 · 隐私三档

| 档位 | Agent 可见内容 | Agent 不可见 |
|---|---|---|
| `standard`（默认） | 列头 + 样本 5–10 行（金额脱敏到千位、单位脱敏为首字母） | 完整明细、对方明细、账号全位 |
| `strict` | 仅列头 + 占位符名称 | 任何数据行 |
| `offline` | 不允许调 AI，只允许匹配已有 artifact | 全封闭 |

配置路径：`ai_configs.privacy_mode`，UI 切换后**立即生效**，不回填历史 artifact。

---

## §6 · 硬边界（8 条）

Fund Agent 在任何情况下**禁止**：

1. 写非白名单代码（pandas / numpy / requests / os / pathlib / open）
2. 发送用户原始 Excel 到 LLM（只能发脱敏后的样本）
3. 新增第 6 个 skill
4. 修改基础数据表列数 / 列名 / 枚举
5. 修改 API 路由（AI 不得接触路由注册代码）
6. 访问数据库以外的外部网络（除了配置的 AI Provider 域名）
7. 执行任何 shell 命令 / subprocess
8. 输出没有 `sample_check_log` 的 artifact

---

## §7 · Agent Memory（记忆机制）

### §7.1 · 短期记忆（单次 skill 调用内）

- 当前 skill 的输入 Schema
- 当前样本（脱敏后）
- 字段字典 snapshot
- 上一轮基元调用的返回值

### §7.2 · 长期记忆（跨 skill 跨会话）

- `parser_artifacts` 表 —— 所有历史 Parser 代码
- `rule_artifacts` 表 —— 所有历史 Rule 代码
- `account_aliases` 表 —— 所有历史别名
- `seed/field_dictionary.json` —— 字段字典（只读，修改需 ChangeFlow）

### §7.3 · 禁止的"记忆"

- 跨用户共享任何实际数据行
- 把用户数据写入 LLM provider 的训练集（privacy_mode 控制）
- 把 artifact 代码泄露给前端以外的调用者

---

## §8 · v2 → v3 差异表

| 项 | v2 | v3 |
|---|---|---|
| Agent 数量 | master + parser-assistant（2 个空壳） | Fund Agent 1 个（实体） |
| skill 数量 | 0（只有空 AGENT.md） | 5（§C4 冻结） |
| AI 介入阶段 | 仅连接测试 | 从 Phase 0 就生成 Parser/Rule |
| 用户配模板 | 要 | 不要（AI 全包） |
| 产物形态 | 无 | Parser/Rule artifact（代码 + 版本 + 校验日志） |
| 沙箱 | 无 | AST 扫描 + 超时 + 内存限制 |
| 隐私 | 无 | 3 档 |
| Runtime AI | 允许 | 禁止（§C8） |

---

**版本**
- v3.0 · 2026-04-23 · 首次发布
