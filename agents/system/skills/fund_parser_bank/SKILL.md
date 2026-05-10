---
name: fund_parser_bank
description: "解析银行流水文件，生成银行流水解析器"
when_to_use: "当用户需要解析银行流水、创建银行流水解析规则、或上传了银行流水文件时"
version: "3.0.0"
execution_mode: instruction
code_entry: "parser.bank"
allowed-tools:
  - file_parse
  - db_query_business
  - db_insert_fund_event
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

## 第四步：查询现有解析器

调用 `db_query_business(table_name="parser_artifacts", filters={"kind": "bank", "account_code": "<account_code>", "status": "active"})`。
如果已有解析器，向用户确认是否复用现有解析器或创建新版本。

## 第五步：生成解析器代码

根据第二步的分析结果，编写 ParserArtifact Python 代码。代码必须：
- 使用 `fund.primitives` 白名单内的函数
- 产出 CANONICAL_12 标准行（entity_code, entity_name, account_code, account_name, summary, counterparty, amount_in, amount_out, rolling_balance, state, source）
- 不调用任何 LLM（§C8 确定性原则）

## 第六步：保存解析器

产出 ParserArtifact（kind="bank", status="draft"）。用户审批后变为 active。

## 第七步：记录经验

调用 `memory_save(key="<银行名称>解析规则", content="<银行名称>流水的特征：列位置、日期格式、金额格式、跳过行数等>")`。

## 关键规则

- 金额列必须区分收入/支出方向，不能搞反
- 日期格式统一转换为 YYYY-MM-DD
- 余额列做校验：当前余额 ≈ 上一条余额 + 收入 - 支出（允许0.01误差）
- 去重：相同日期+金额+摘要的记录不重复导入
- 每条记录的 entity_code 和 entity_name 从账户信息中获取，不是从流水文件中读取
- 解析器只产出 ParserArtifact，不得写入 ParserTemplate
