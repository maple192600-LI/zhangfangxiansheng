---
name: fund_parser_manual
description: "解析手工流水记录，生成手工流水解析器"
when_to_use: "当用户需要录入手工流水、解析手工流水、或处理非银行流水的财务记录时"
version: "2.0.0"
execution_mode: instruction
code_entry: "parser.manual"
allowed-tools:
  - file_parse
  - db_query_business
  - db_insert_fund_event
  - memory_save
  - memory_search
  - skill_step_report
triggers:
  - "解析手工流水"
  - "手工流水解析"
  - "录入手工流水"
  - "手工账"
  - "手工录入"
arguments:
  account_code:
    description: "账户编码"
    required: true
  sample_file:
    description: "样本文件路径"
    required: false
---

# 手工流水解析器

## 场景 A：用户上传了文件

### 第一步：解析文件

调用 `file_parse(path="<用户提供的文件路径>")` 解析文件。
检查返回的 `ok` 字段。如果失败，报告错误并停止。

### 第二步：提取流水数据

从解析结果中识别：
1. 日期列或日期字段
2. 摘要/说明列
3. 金额列（区分正负或分收入/支出）
4. 对方信息（如有）

### 第三步：查询账户信息

调用 `db_query_business(table_name="accounts", filters={"account_code": "<account_code>"})`。
确认账户存在。从结果中获取 entity_code、entity_name、account_name。

### 第四步：逐条写入

对文件中每一行有效数据，调用：
```
db_insert_fund_event(
  business_date="<YYYY-MM-DD>",
  entity_code="<从账户信息获取>",
  entity_name="<从账户信息获取>",
  account_code="<account_code>",
  account_name="<从账户信息获取>",
  amount_in=<收入金额，无则为0>,
  amount_out=<支出金额，无则为0>,
  summary="<摘要>",
  counterparty="<对方户名>"
)
```

注意：amount_in 和 amount_out 不能同时大于 0。

## 场景 B：用户口述流水

### 第一步：确认账户

调用 `db_query_business(table_name="accounts", filters={"account_code": "<account_code>"})`。
获取 entity_code、entity_name、account_name。

### 第二步：直接写入

根据用户的描述，提取日期、金额、摘要等信息，调用 `db_insert_fund_event` 写入。
缺少摘要时使用默认值 "手工录入"。

## 收尾步骤

无论哪种场景，完成后都调用：
```
memory_save(key="手工流水_<account_code>", content="账户<account_code>的手工流水录入记录，最近一次录入：<日期>，共<N>条")
```

## 关键规则

- 手工流水必须有日期和金额，缺一不可
- 金额为正数表示收入，负数表示支出（或用户明确指定方向）
- 去重：写入前查询同日期+同金额+同摘要是否已存在
- entity_code/entity_name 从账户信息获取，不要求用户提供
