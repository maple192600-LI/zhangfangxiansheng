---
name: fund_parser_bank
description: "解析银行流水文件，生成银行流水解析器"
when_to_use: "当用户需要解析银行流水、创建银行流水解析规则、或上传了银行流水文件时"
version: "2.0.0"
execution_mode: instruction
code_entry: "parser.bank"
allowed-tools:
  - file_parse
  - db_query_business
  - db_insert_fund_event
  - db_save_parser_template
  - memory_save
  - memory_search
  - skill_step_report
triggers:
  - "解析银行流水"
  - "银行流水解析"
  - "银行流水解析器"
  - "解析银行对账单"
  - "导入银行流水"
arguments:
  account_code:
    description: "银行账户编码"
    required: true
  sample_file:
    description: "样本文件路径"
    required: true
dependencies:
  pip:
    - "pdfplumber>=0.10"
    - "xlrd==1.2.0"
    - "openpyxl>=3.0"
---

# 银行流水解析器

## 第一步：获取文件内容

调用 `file_parse(path="<用户提供的文件路径>")` 解析文件。
检查返回的 `format` 字段判断文件类型。

如果 `ok=False`，报告具体错误并停止。

## 第二步：分析文件结构

根据 file_parse 返回的表格内容，识别：
1. 表头行位置（第几行是列名）
2. 数据开始行（跳过表头和非数据行）
3. 关键列：交易日期列、收入金额列、支出金额列、余额列、摘要列、对方户名列
4. 日期格式（如 YYYY-MM-DD、YYYY/MM/DD、MM-DD-YYYY 等）
5. 金额格式（是否有千分位逗号、是否分列表示收入/支出）

## 第三步：查询账户信息

调用 `db_query_business(table_name="accounts", filters={"account_code": "<account_code>"})` 获取账户详情。
确认账户存在且 account_type 为银行账户。如果不存在，告知用户并停止。

## 第四步：查询现有解析规则

调用 `db_query_business(table_name="parser_templates", filters={"template_type": "bank", "account_code": "<account_code>"})`。
如果已有规则，向用户确认是否复用现有规则或创建新规则。

## 第五步：生成列映射

根据第二步的分析结果，构建 mapping_json。标准字段包括：
- `business_date`: 交易日期
- `income_amount`: 收入金额（如果银行不分收支列，用正数表示）
- `expense_amount`: 支出金额（如果银行不分收支列，用负数表示）
- `balance`: 余额
- `counterparty_name`: 对方户名
- `summary_text`: 摘要
- `counterpart_account`: 对方账号
- `counterpart_bank`: 对方开户行

示例映射：
```json
{
  "交易日期": "business_date",
  "贷方发生额": "income_amount",
  "借方发生额": "expense_amount",
  "余额": "balance",
  "对方户名": "counterparty_name",
  "摘要": "summary_text"
}
```

## 第六步：保存解析规则

调用 `db_save_parser_template(
  template_name="<银行名称>流水规则",
  account_code="<account_code>",
  file_format="<xlsx/xls/csv>",
  header_row=<表头行号>,
  skip_rows=<数据前跳过行数>,
  sample_headers=<JSON数组：银行原始列名>,
  mapping_json=<JSON对象：列映射>
)`。

## 第七步：解析数据并写入流水表

对文件中的每一行数据：
1. 按列映射提取字段值
2. 转换日期格式为 YYYY-MM-DD
3. 清洗金额（去除逗号、空格、货币符号）
4. 去重检查：调用 `db_query_business(table_name="fund_events", filters={"business_date": "<日期>", "account_code": "<account_code>"})` 查看是否已存在相同记录
5. 调用 `db_insert_fund_event(business_date=..., entity_code=..., entity_name=..., account_code=..., account_name=..., amount_in=..., amount_out=..., summary=..., counterparty=...)` 写入

## 第八步：记录经验

调用 `memory_save(key="<银行名称>解析规则", content="<银行名称>流水的特征：列位置、日期格式、金额格式、跳过行数等>")`。

## 关键规则

- 金额列必须区分收入/支出方向，不能搞反
- 日期格式统一转换为 YYYY-MM-DD
- 余额列做校验：当前余额 ≈ 上一条余额 + 收入 - 支出（允许0.01误差）
- 去重：相同日期+金额+摘要的记录不重复导入
- 每条记录的 entity_code 和 entity_name 从账户信息中获取，不是从流水文件中读取
