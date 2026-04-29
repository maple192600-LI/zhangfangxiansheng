# 25 · 基元库白名单（v3 · §C5）

> 本文件定义 Parser / Rule artifact **唯一允许调用**的函数白名单。
> 任何调用白名单外的函数 = `tools/guards/check_primitives_whitelist.py` 拒绝。
> 宪法锚点见 [../00_governance/00_project_constitution.md](../00_governance/00_project_constitution.md) §C5。

---

## §P0 · 总览

基元库位于 `backend/fund/primitives/`，共 **37 个函数** 分布在 **7 个模块**：

| 模块 | 路径 | 函数数 | 职责 |
|---|---|---|---|
| `sheet_ops` | `sheet_ops.py` | 6 | Excel 表格操作 |
| `value_parsers` | `value_parsers.py` | 5 | 单元格取值 / 归一化 |
| `canonical` | `canonical.py` | 4 | 12 列 canonical 行产出 |
| `master_match` | `master_match.py` | 4 | 单位 / 账户匹配 |
| `base_queries` | `base_queries.py` | 6 | 基础数据表查询 |
| `aggregations` | `aggregations.py` | 6 | 聚合运算 |
| `template_fill` | `template_fill.py` | 6 | 报表模板填写 |

---

## §P1 · `fund.primitives.sheet_ops` · 6 个

```python
def read_sheet(wb, index: int = 0, name: str | None = None) -> Sheet
def detect_header_row(sheet: Sheet, max_scan: int = 20) -> int
def extract_headers(sheet: Sheet, header_row: int) -> dict[str, int]
def iter_data_rows(sheet: Sheet, start_row: int) -> Iterator[dict]
def is_empty_row(row: dict) -> bool
def locate_merged_cells(sheet: Sheet) -> list[MergedCell]
```

**语义**：
- `read_sheet`：按索引或名称取工作表，工作簿由 Runtime 预加载（Agent 不得调 `open()`）
- `detect_header_row`：扫描前 N 行，返回字段最多的那一行（就是表头）
- `extract_headers`：把表头行取出，返回 `{中文名: 列索引}` 字典
- `iter_data_rows`：从 start_row 开始迭代数据行，每行 yield 为 dict
- `is_empty_row`：判定全空 / 分隔行
- `locate_merged_cells`：返回合并单元格区域（用于处理"合计行"、"标题行"）

---

## §P2 · `fund.primitives.value_parsers` · 5 个

```python
def parse_date(raw, default_year: int | None = None) -> date | None
def parse_amount(raw, default: Decimal = Decimal("0")) -> Decimal
def parse_text(raw, max_len: int = 500) -> str
def parse_counterparty(raw, max_len: int = 200) -> str
def normalize_whitespace(s: str) -> str
```

**语义**：
- `parse_date`：支持 `2026-04-23 / 2026/4/23 / 20260423 / 4月23日 / 4-23`；无年时用 default_year
- `parse_amount`：支持千分位 / 货币符号 / 括号负号 / 中文大写金额
- `parse_text`：去首尾空白、归一化全半角、截断到 max_len
- `parse_counterparty`：同 `parse_text`，但额外去除账号后缀
- `normalize_whitespace`：压缩连续空白

---

## §P3 · `fund.primitives.canonical` · 4 个

```python
def normalize_row(raw: dict) -> CanonicalRow
def emit_row(**fields) -> CanonicalRow
def mark_row_state(row: CanonicalRow, state: Literal["正常","待确认","异常","已作废"]) -> CanonicalRow
def derive_source(input_method: str) -> Literal["网银导入","手工录入","现金录入","票据录入","财务公司单据"]
```

**语义**：
- `normalize_row`：从字段字典匹配结果 → 填入 12 列 canonical 结构
- `emit_row`：便捷构造器，校验 12 列完整性（少一列就抛）
- `mark_row_state`：设置状态，金额互斥冲突自动标 `异常`
- `derive_source`：根据账户 `input_method` 字段映射到 source 枚举

---

## §P4 · `fund.primitives.master_match` · 4 个

```python
def match_entity(hint: str, alias_library: dict) -> Entity | None
def match_account(hint: str, alias_library: dict, threshold: float = 0.85) -> Account | None
def register_alias(code: str, alias: str, confidence: float, alias_type: str = "自动") -> None
def get_account_by_code(code: str) -> Account
```

**语义**：
- `match_entity / match_account`：模糊匹配（后四位 / 名称相似度），阈值可调
- `register_alias`：把成功匹配的新别名写入 `account_aliases`
- `get_account_by_code`：精确查询

---

## §P5 · `fund.primitives.base_queries` · 6 个

```python
def opening_balance(account_code: str, as_of: date) -> Decimal
def closing_balance(account_code: str, as_of: date) -> Decimal
def rolling_balance_of(event_id: int) -> Decimal
def list_events(filters: dict) -> Iterator[CanonicalRow]
def account_field(account_code: str, field: str) -> Any
def entity_field(entity_code: str, field: str) -> Any
```

**语义**：
- `opening_balance`：`accounts.initial_balance + sum(fund_events WHERE business_date < as_of)`
- `closing_balance`：opening + 当期合计
- `rolling_balance_of`：某一行的滚动余额（必要时按日期排序动态算）
- `list_events`：按账户 / 日期范围 / 状态筛选基础数据表
- `account_field / entity_field`：取主数据字段（bank_name / account_last_four 等）

---

## §P6 · `fund.primitives.aggregations` · 6 个

```python
def sum_field(field: Literal["amount_in","amount_out"], filters: dict) -> Decimal
def count_rows(filters: dict) -> int
def aggregate(field: str, op: Literal["sum","max","min","avg"], filters: dict) -> Decimal
def net_change(account_code: str, start: date, end: date) -> Decimal
def max_date(filters: dict) -> date | None
def min_date(filters: dict) -> date | None
```

**语义**：
- `sum_field`：分列累加（只用于 amount_in / amount_out）
- `count_rows`：符合条件的行数
- `aggregate`：通用聚合，但函数受限在 4 个
- `net_change`：期末 - 期初
- `max_date / min_date`：期内极值日期

---

## §P7 · `fund.primitives.template_fill` · 6 个

```python
def load_template(path: str) -> Workbook
def fill(wb, placeholder: str, value: Any, format: str | None = None) -> None
def const(value: Any) -> Any
def date_range_start(ctx: dict) -> date
def date_range_end(ctx: dict) -> date
def format_amount(value: Decimal, digits: int = 2) -> str
```

**语义**：
- `load_template`：加载空白 Excel 模板（只读）
- `fill`：把 value 填到 placeholder 位置（单元格 / 合并区）
- `const`：常量占位
- `date_range_start / date_range_end`：从 ctx 读期间起止
- `format_amount`：格式化金额

---

## §P8 · 引入规则

### §P8.1 · 合法 import

```python
# ✅ 允许
from fund.primitives.sheet_ops    import read_sheet, detect_header_row
from fund.primitives.value_parsers import parse_date, parse_amount
from fund.primitives.canonical    import emit_row
from datetime import date, datetime, timedelta
from decimal  import Decimal
from typing   import Iterator, Optional, Literal
import re
```

### §P8.2 · 禁止 import

```python
# ❌ 拒绝（AST 扫描拦截）
import pandas as pd             # 禁止
import numpy as np              # 禁止
import requests                 # 禁止
import os                       # 禁止
import sys                      # 禁止
import subprocess               # 禁止
from pathlib import Path        # 禁止
import json                     # 禁止（Agent 产物不应自己做 JSON I/O）
open("x.xlsx")                  # 禁止
eval("...")                     # 禁止
exec("...")                     # 禁止
__import__(...)                 # 禁止
```

### §P8.3 · AST 扫描规则

`tools/guards/check_primitives_whitelist.py` 对所有 artifact code 做：

```
对每个 AST：
  Import / ImportFrom:
    module 以 fund.primitives. 开头 → ✓
    module ∈ {datetime, decimal, typing, re} → ✓
    其他 → ✗（拒绝）
  Call:
    函数名 ∈ {open, exec, eval, compile, __import__} → ✗
  Attribute:
    访问 __class__ / __subclasses__ / __globals__ → ✗
```

---

## §P9 · Parser Artifact 示例骨架

```python
from fund.primitives.sheet_ops    import read_sheet, detect_header_row, extract_headers, iter_data_rows
from fund.primitives.value_parsers import parse_date, parse_amount, parse_text
from fund.primitives.canonical    import emit_row, mark_row_state
from fund.primitives.master_match import match_account

def parse(wb, ctx):
    """
    wb:  openpyxl Workbook（Runtime 预加载）
    ctx: dict，包含 account_code、field_dictionary、alias_library
    yield: CanonicalRow（12 列 dict）
    """
    sheet = read_sheet(wb, index=0)
    header_row = detect_header_row(sheet)
    headers = extract_headers(sheet, header_row)

    account = match_account(ctx["account_hint"], ctx["alias_library"])

    for raw in iter_data_rows(sheet, header_row + 1):
        date_v   = parse_date(raw.get(headers.get("日期")))
        amt_in   = parse_amount(raw.get(headers.get("收入")))
        amt_out  = parse_amount(raw.get(headers.get("支出")))
        row = emit_row(
            business_date=date_v,
            entity_code=account.entity_code,
            entity_name=account.entity_name,
            account_code=account.account_code,
            account_name=account.account_name,
            summary=parse_text(raw.get(headers.get("摘要"))),
            counterparty=parse_text(raw.get(headers.get("对方"))),
            amount_in=amt_in,
            amount_out=amt_out,
            source="网银导入",
        )
        yield row
```

---

## §P10 · Rule Artifact 示例骨架

Rule artifact 不是自由代码，而是**声明式 JSON + 受限 primitive 引用**：

```json
{
  "name": "现金日记账_月账_v1",
  "template_file": "templates/cash_journal_blank.xlsx",
  "placeholder_bindings": {
    "报表标题":     { "primitive": "const",            "value": "现金日记账" },
    "开始期间":     { "primitive": "date_range_start", "params": {} },
    "结束期间":     { "primitive": "date_range_end",   "params": {} },
    "板块":         { "primitive": "entity_field",     "params": { "field": "division_name" } },
    "核算方式":     { "primitive": "const",            "value": "收付实现制" },
    "开户行":       { "primitive": "account_field",    "params": { "field": "bank_name" } },
    "账户信息":     { "primitive": "account_field",    "params": { "field": "account_name" } },
    "银行编号":     { "primitive": "account_field",    "params": { "field": "account_last_four" } },
    "月初余额":     { "primitive": "opening_balance",  "params": {} },
    "本月收入小计": { "primitive": "sum_field",        "params": { "field": "amount_in" } },
    "本月支出小计": { "primitive": "sum_field",        "params": { "field": "amount_out" } },
    "月末余额":     { "primitive": "closing_balance",  "params": {} }
  },
  "loop": {
    "anchor":  "摘要_data_start",
    "source":  "list_events",
    "filters": { "account_code": "${ctx.account_code}", "state_in": ["正常"] },
    "columns": {
      "月":   { "primitive": "format_amount", "params": { "from": "business_date", "format": "MM" } },
      "日":   { "primitive": "format_amount", "params": { "from": "business_date", "format": "DD" } },
      "摘要": { "primitive": "const",         "value": "${row.summary}" },
      "收入": { "primitive": "const",         "value": "${row.amount_in}" },
      "支出": { "primitive": "const",         "value": "${row.amount_out}" },
      "余额": { "primitive": "rolling_balance_of", "params": {} }
    }
  }
}
```

**18 个占位符必须全部出现在 `placeholder_bindings` 或 `loop.columns` 中，一个不多一个不少**（§C2）。

---

## §P11 · 扩展流程

**当 Agent 发现"基元不够用"时**：

1. Agent 调用 `parser.bank` 返回错误：`{"code":"primitive_gap","missing":"parse_hkd_amount"}`
2. 用户看到前端错误，走 §ChangeFlow 申请
3. 用户批准 → 开发者实现新基元 → 补单元测试 → 更新本文件 → 重算 contracts.lock
4. 新基元生效后，用户重新触发 `parser.bank`

**Agent 绝不可在 artifact 代码里"临时实现"缺失的基元**（= 违反 §C5）。

---

**版本**
- v3.0 · 2026-04-23 · 首次发布（37 函数冻结）
