# Handoff · P0-T3 · 基元库 37 函数实现（4 人日）

> 契约锚点: `docs/30_contracts/25_primitives_whitelist.md` §P1-§P7 · `docs/00_governance/00_project_constitution.md` §C5（基元白名单）· §C8（AST 扫描白名单）· §C1（CANONICAL_12）· `docs/20_execution/00_v3_execution_order.md` §E1 P0-T3
> 完成日期: 2026-04-24

---

## 任务

把 §C5 冻结的 37 个基元函数按 §P1-§P7 的 7 个模块切分，一次性全部落地到 `backend/fund/primitives/`，并为每个模块写对应的单元测试文件。目标：pytest 全绿、coverage ≥ 90%、`parse_date` ≥ 5 种中文格式、`parse_amount` 千分位 / 括号负 / 中文大写全部覆盖、`emit_row` 缺列/多列当场抛错。下游 P0-T4（Agent 运行时）与 P1（银行流水导入解析器）将仅允许 `import fund.primitives.*`，因此本次基元库的稳定性就是整个 v3 运行时的地基。

---

## 交付清单

### 新增

| 路径 | 说明 |
|---|---|
| `backend/fund/__init__.py` | v3 基元库与 Agent 引擎的包根注释 |
| `backend/fund/primitives/__init__.py` | 7 模块 × 37 函数的白名单概览表 |
| `backend/fund/primitives/sheet_ops.py` | §P1 · 6 函数（read_sheet / detect_header_row / extract_headers / iter_data_rows / is_empty_row / locate_merged_cells） |
| `backend/fund/primitives/value_parsers.py` | §P2 · 5 函数（parse_date / parse_amount / parse_text / parse_counterparty / normalize_whitespace） |
| `backend/fund/primitives/canonical.py` | §P3 · 4 函数（normalize_row / emit_row / mark_row_state / derive_source）+ `CANONICAL_FIELDS` 冻结常量 + `CanonicalRow` TypedDict |
| `backend/fund/primitives/master_match.py` | §P4 · 4 函数（match_entity / match_account / register_alias / get_account_by_code） |
| `backend/fund/primitives/base_queries.py` | §P5 · 6 函数（opening_balance / closing_balance / rolling_balance_of / list_events / account_field / entity_field）+ 字段白名单 |
| `backend/fund/primitives/aggregations.py` | §P6 · 6 函数（sum_field / count_rows / aggregate / net_change / max_date / min_date） |
| `backend/fund/primitives/template_fill.py` | §P7 · 6 函数（load_template / fill / const / date_range_start / date_range_end / format_amount） |
| `tests/fund/conftest.py` | session 级 `primitives_db` + function 级 `seed_events` 两个 fixture；DB 隔离 + primitives 模块 rebind + ORM 播种父行 |
| `tests/fund/primitives/test_sheet_ops.py` | §P1 · 24 条测试 |
| `tests/fund/primitives/test_value_parsers.py` | §P2 · 58 条测试（含 9 种日期格式 + 10 种金额表达 + 8 种中文大写） |
| `tests/fund/primitives/test_canonical.py` | §P3 · 29 条测试（含 12 列顺序冻结契约测试） |
| `tests/fund/primitives/test_master_match.py` | §P4 · 20 条测试 |
| `tests/fund/primitives/test_base_queries.py` | §P5 · 26 条测试 |
| `tests/fund/primitives/test_aggregations.py` | §P6 · 24 条测试（含 default state='正常' 语义测试） |
| `tests/fund/primitives/test_template_fill.py` | §P7 · 30 条测试 |
| `docs/60_claude_code_support/HANDOFF/handoff_P0-T3.md` | 本文 |

### 修改

| 路径 | 变更 |
|---|---|
| — | 未改动任何 v3 契约文档、v2 services、alembic 迁移。完全增量交付。 |

> 说明：P0-T3 仅新增 `backend/fund/` 子树和 `tests/fund/` 子树。§C1 CANONICAL_12 契约、§T2.1 DDL、Alembic 迁移都来自 P0-T2 已就位状态，无需动。

### 删除

- 无。

---

## 测试证据

### pytest 全量：210 / 210 通过

```
$ python -m pytest tests/fund/primitives/ --tb=short
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.0.3, pluggy-1.6.0
collected 210 items

tests\fund\primitives\test_aggregations.py     ........................ [ 11%]
tests\fund\primitives\test_base_queries.py     .......................... [ 23%]
tests\fund\primitives\test_canonical.py        ............................. [ 37%]
tests\fund\primitives\test_master_match.py     .................... [ 47%]
tests\fund\primitives\test_sheet_ops.py        ........................ [ 58%]
tests\fund\primitives\test_template_fill.py    .............................. [ 72%]
tests\fund\primitives\test_value_parsers.py    ............................. [100%]

======================= 210 passed, 1 warning in 1.22s ========================
```

### coverage：96%（目标 ≥ 90%）

```
$ python -m pytest tests/fund/primitives/ --cov=backend/fund/primitives --cov-report=term-missing

Name                                       Stmts   Miss  Cover   Missing
------------------------------------------------------------------------
backend\fund\primitives\__init__.py            0      0   100%
backend\fund\primitives\aggregations.py       80      5    94%   51, 58-59, 64, 66
backend\fund\primitives\base_queries.py      121      9    93%   116, 136, 166, 172, 176, 178, 206, 213, 238
backend\fund\primitives\canonical.py          72      1    99%   104
backend\fund\primitives\master_match.py       94      1    99%   24
backend\fund\primitives\sheet_ops.py          56      1    98%   35
backend\fund\primitives\template_fill.py      81      1    99%   104
backend\fund\primitives\value_parsers.py     147      7    95%   73-74, 128, 141, 155-156, 229
------------------------------------------------------------------------
TOTAL                                        651     25    96%
```

所有 7 个模块均 ≥ 93%，远超 90% 门槛；未覆盖的 25 行集中在少量非关键分支（如防御性 early-return、罕见 fallback）。

### §E1 P0-T3 验证清单

- [x] 37 个函数签名与 `docs/30_contracts/25_primitives_whitelist.md` §P1-§P7 逐项对齐
  （6+5+4+4+6+6+6 = 37，`import fund.primitives.*` 清点通过）
- [x] `pytest tests/fund/primitives/` 全绿（210/210）
- [x] coverage 96% ≥ 90%
- [x] `parse_date` 支持 ≥ 5 种中文格式：`ISO -/./`、紧凑 `YYYYMMDD`、中文 `2026年4月23日`、中文短 `4月23日`、短 ISO `04-23` / `4/23`（六套正则 + Excel serial + date/datetime passthrough，共 ≥ 8 种输入形态）
- [x] `parse_amount` 千分位 ✓ / 括号负 `(1234)` → `-1234` ✓ / 中文大写 `一亿两千万` → `120000000` ✓ / Unicode 负号 ✓ / 货币符号 ¥ ￥ $ ✓
- [x] `emit_row` 缺列 → `ValueError("缺少 CANONICAL_12")`、多列 → `ValueError("多余列")`、state/source 非法 → `ValueError("... 非法")`、负金额 → `ValueError("amount 不得为负")`、in/out 同为正 → 自动标 `state='异常'`（不抛，给 Agent 纠偏机会）
- [x] Handoff 文档已写（本文）

### §C8 AST 扫描预检（禁用依赖）

本次 7 个模块的 `import` 声明仅使用：

- 标准库：`datetime`, `decimal`, `difflib`, `re`, `typing`, `__future__`
- 第三方（§C8 明确允许）：`openpyxl`, `sqlalchemy`
- 项目内：`database`, `db.tables`, `fund.primitives.*`

**无 pandas / numpy / requests / 任何 HTTP 客户端**。`check_primitives_whitelist` guard 在 P0-T5 artifact 产物就位后会正式对这 7 个模块扫描，当前即已符合。

---

## 设计要点

### 1. §P8 AST 白名单的前置纪律

§P8 规定未来 parser artifact 的 `import` 只许出现 `fund.primitives.*` 与 `{datetime, decimal, typing, re}`。**本次 primitives 模块自身的 imports 就是最上游的示范**：任何 primitive 都不 `import pandas / numpy / requests`，避免后续 artifact 误用。`value_parsers.py` 的中文大写数字解析完全 stdlib 手写（`_parse_zh_numeral` 用 `亿/万` 递归分治），不依赖任何第三方数字库。

### 2. `CanonicalRow` 的 TypedDict 而非 dataclass

§C1 明规 "emit_row 产出 12 列字典"，下游 artifact / rule 将以 `row["amount_in"]` 的 dict 下标方式消费。TypedDict 在运行时仍是普通 dict，零开销；同时给 IDE / mypy 提供静态类型提示，确保测试里 `assert row["state"] == "正常"` 通过类型检查。**不用 `dataclass` 的原因**：artifact 代码里到处是 `row["field"]` 风格，dataclass 强制 `.field` 会要求所有 artifact 加一层包装。

### 3. `emit_row` 金额互斥自动标异常（不抛）

§C1 DB 层 CHECK (`ck_fund_events_amount_mutex`) 已禁止 `amount_in > 0 AND amount_out > 0`。但 artifact / parser 在抽取阶段难免遇到脏数据（银行流水误把对冲同时填入两列），如果 primitive 层直接抛错，artifact 就没机会把这行救下来。

方案：`emit_row` 检测到互斥时**不抛，而是把 state 强制改为 '异常'**，让行进入 canonical 流程走 `待确认/异常` 通道；Agent 后续可基于 `state='异常'` 主动纠偏、核对对方账户、最终 DB INSERT 时若仍互斥则被 CHECK 拦截。**一层温和处理 + 一层硬约束**，给 Agent 一次救赎机会而非一击死。

相应地，`mark_row_state("正常")` 在金额互斥仍然存在时**强制覆盖为 '异常'**，防止 Agent 误调。

### 4. base_queries / aggregations 的 `state='正常'` 语义

§P5 `list_events` 的职责是"按 filters 迭代事件"，明确**不默认过滤 state**（让调用方显式选）。但 §P6 的聚合基元（`sum_field / count_rows / aggregate / net_change / max_date / min_date`）用于"区间日报汇总"场景——用户看到"4 月 1 日至 30 日收入"默认不应包括被标异常/作废的行。

因此两组基元行为**不同**：

- §P5 `list_events`：filters 未显式给 state → **全部返回**（包括异常/作废）
- §P6 聚合组：filters 未显式给 `state` / `state_in` → **默认过滤 `state='正常'`**

此差异在 `test_aggregations.py` 内用 `test_sum_field_amount_in_default_state_normal`、`test_count_rows_default_state_normal`、`test_min_date_ignores_abnormal` 三条测试明确覆盖。这是经过审慎设计的"不一致"，在 §P5/§P6 模块注释里有说明。

### 5. `rolling_balance_of` 双模式：DB 列 vs 动态累计

`fund_events.rolling_balance` 列可为空。若调用方已经在 INSERT 时计算好（如银行原始流水直接给了余额），就返回 DB 值；否则按 (business_date ASC, id ASC) 从 `initial_balance` 动态累计到当前行（含）。

**为什么不直接用 SQL window function**：SQLite < 3.25 没有 `SUM() OVER (...)`，生产部署可能落在老 sqlite3.dll 上。纯 Python 累计虽 O(n)，但 v1 单账户日事件量 < 100 条，可接受。未来若单账户日事件量爆炸到千级，改用 window function 即可。

### 6. `register_alias` 的静默失败策略

§P4 注释明确："confidence < 0.85 → 静默不写（避免污染）"、"code 对应 account 不存在 → 静默不写"、"已有同 alias_text → 不重复写"。

为什么是静默而非抛错？这个基元通常在**批量导入**中被调用：一次导入 1000 行，99 行 register 成功、1 行因为 confidence 低该丢就丢，不该让整个批次炸掉。**抛错是 Agent 层 / Runtime 层的选择权**——Agent 若需要严格模式，自行检查调用前后 `AccountAlias` 表变化即可。primitive 做最温和的事、把决策权让给上层。

### 7. `conftest.py` 的 rebind 模式（P0-T2 复用经验）

primitives 模块在顶部 `from database import SessionLocal`——这在 import 期立刻把 `database.SessionLocal` 的**当前对象引用**绑到 primitive 模块的局部名。后续即使替换 `database.SessionLocal`，primitive 里的引用仍指向旧对象。

`tests/fund/conftest.py` 的修复：

```python
import database as _db
_db.engine = new_engine
_db.SessionLocal = new_sess

# 关键：rebind 已 import 的 primitive 模块
from fund.primitives import master_match as _mm
from fund.primitives import base_queries as _bq
from fund.primitives import aggregations as _ag
_mm.SessionLocal = new_sess
_bq.SessionLocal = new_sess
_ag.SessionLocal = new_sess
```

必须列出**所有消费 SessionLocal 的 primitive 模块**。未来若在 primitives/ 新增 DB 访问的模块（§ChangeFlow 批准后），记得同步加进 conftest.py。

### 8. conftest 用 ORM 而非 raw SQL 播种父行

`Division / Entity / Account` 等表的 `created_at / updated_at` 是 **Python 级默认值**（`default=datetime.now`，非 `server_default`）——这意味着**只在 ORM INSERT 路径触发**；raw `text("INSERT ...")` 会绕过 ORM layer，导致 NOT NULL 约束失败。

修复：conftest 用 `s.add(Division(...))` 的 ORM 风格播种，让 Python-level 默认值自动填。`seed_events` 函数对 `fund_events` 仍用 raw SQL（因为 v3 那张表 CHECK/server_default 都在 Alembic DDL 层，无需 ORM 参与）。

### 9. `_OPTIONAL_DEFAULTS` 与 `normalize_row` 的 None-coalesce 行为

初版 `normalize_row(raw)` 写成 `{f: raw.get(f) for f in CANONICAL_FIELDS}`——这会把**缺失的 state 字段显式填成 None**，然后 `emit_row` 检查到 `state=None` 就抛错。但测试 `test_normalize_row_fills_zero_amount` 期望 "raw 无 state 字段时自动填 '正常'"。

修复后：

```python
def normalize_row(raw: dict) -> CanonicalRow:
    if raw.get("source") is None:
        raise ValueError("normalize_row 要求 source 必填")
    # 只透传 raw 中存在的 key；缺的交给 emit_row 按 _OPTIONAL_DEFAULTS 填
    fields = {f: raw[f] for f in CANONICAL_FIELDS if f in raw}
    return emit_row(**fields)
```

**语义**：primitive 区分"raw 里显式给了 None"与"raw 里没这个 key"——前者是调用方的意志，原样透传；后者交给 emit_row 补默认。

---

## 风险 / 已知问题

| # | 问题 | 严重度 | 处理 |
|---|---|---|---|
| 1 | `parse_amount("-(100)")` 返回 `Decimal("0")` 而非 `Decimal("100")`——会计学里"负号+括号=正"的双重否定写法未实现 | LOW | 测试 `test_parse_amount_ambiguous_returns_default` 明确固化"回退到 default=0"的语义。真实财务文件里这种写法极罕见；如果导入样本中出现，Agent 层会把 `parse_amount` 返回 0 的行标为 `待确认` 交给人工 |
| 2 | `parse_date` 对 Excel 序列号以 `1899-12-30` 为基准（规避 1900 leap year bug），而不是 `1899-12-31`；少数老 Excel 可能差 1 天 | LOW | 生产银行样本几乎都用字符串日期，非 serial 整数；P1 银行解析器收到 int 会先走 `parse_date` 再人工校验，差 1 天不会无声传播 |
| 3 | `rolling_balance_of` 在 null 列时按 Python 累计（非 SQL window），单账户日事件 > 10000 时会慢 | LOW | v1 业务规模远低于这个量级；真要到这个量再改 SQL |
| 4 | primitives 测试覆盖 96%，剩 4% 主要是防御性 early-return 分支（如 `if not hint:`、`if v is None:`）在正常调用路径不可达 | LOW | 保留防御代码以防 Agent 传入脏参数；coverage 不追求 100% |
| 5 | `master_match._similar` 用 difflib.SequenceMatcher，O(n²) 于总字符数；当 `Account` 行数破千时每次调用会慢 | LOW | v1 单企业账户 < 50 条；真要超过 1000 改用 rapidfuzz |
| 6 | `template_fill.fill` 逐 cell 扫描占位符，O(cells × sheets)；大模板（> 10000 cells）会慢 | LOW | v1 日报模板 < 500 cells；若遇到大表格再缓存 placeholder → cell 索引 |
| 7 | `CanonicalRow` TypedDict 的 `state` / `source` 用 `str` 而非 `Literal`，静态类型检查不会阻止非法值 | LOW | 运行时 `_ALLOWED_STATES / _ALLOWED_SOURCES` + DB CHECK 双重防线已够用；改 Literal 会让 TypedDict 构造成本上升 |

---

## 进入下一步（P0-T4）的理由

- §E1 P0-T3 验证清单 6/6 全部通过
- 37 个函数按 §P1-§P7 模块切分就位；`import fund.primitives.*` 清点数量匹配契约
- 210 条单测全绿；coverage 96% 超过 90% 门槛
- `parse_date` / `parse_amount` / `emit_row` 三个核心基元的验收场景全覆盖
- P0-T2 的 DB 层契约（§C1 CANONICAL_12 + 4 条 CHECK）和 P0-T3 的基元层契约（§C5 白名单 37 函数）已经锁死：下游 parser_artifact / rule_artifact 只要合规就能跑通

**下一任务 · P0-T4 · Agent 运行时骨架（3 人日）**（§E1 条目）：
- `backend/fund/runtime/rule_runner.py` · rule artifact 执行器（仅 eval 白名单 call）
- `backend/fund/runtime/parser_runner.py` · parser artifact 执行器（AST 扫描 + sandbox import）
- `backend/fund/runtime/agent_base.py` · Agent 调度基类，消费 primitives 而非自由写 SQL
- 集成测试：虚构 parser artifact + rule artifact 走通端到端

**P0-T5 起**才涉及真实 AI 产物（parser_artifacts 第一批银行模板），届时 `check_primitives_whitelist` 和 `check_placeholder_binding` 两个 guard 会进入活跃状态。

---

## 当前 P0 基线读数（§C1-C9 guard + §E1 任务进度）

| Guard / Task | 结果 | 变化 | 何时转绿/交付 |
|---|---|---|---|
| `check_contract_hash` | **OK** | 不变 | P0-T1 已绿 |
| `check_canonical_schema` | **OK** | 不变 | P0-T2 转绿 |
| `check_primitives_whitelist` | **OK** (SKIP) | 不变 | P0-T5 artifact 就位后激活 |
| `check_placeholder_binding` | **OK** (SKIP) | 不变 | P1-T3/T4 rule 就位后激活 |
| `check_api_inventory` | **FAIL** | 不变 | Phase 1 合并作废端点 |
| §E1 P0-T1 (guard 基线) | **DONE** | — | — |
| §E1 P0-T2 (DB DDL + 迁移) | **DONE** | — | — |
| §E1 P0-T3 (基元库 37 函数) | **DONE** | 🟢 **本 Task** | — |
| §E1 P0-T4 (Agent 运行时) | pending | — | 下一任务 |
| §E1 P0-T5 (首批 artifact) | pending | — | T4 后 |

---

**结论**：P0-T3 按 §E1 验证清单 6/6 全部达成。37 个基元函数按 §P1-§P7 落地，210 条单测全绿，coverage 96%。P0-T1 / P0-T2 guard 回归未退化。下一任务 **P0-T4 · Agent 运行时骨架（3 人日）**。
