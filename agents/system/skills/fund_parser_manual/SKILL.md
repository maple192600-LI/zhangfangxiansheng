---
name: fund_parser_manual
description: "解析手工流水记录，生成手工流水解析器"
when_to_use: "当用户需要录入手工流水、解析手工流水、或处理非银行流水的财务记录时"
allowed-tools:
  - file_parse
  - db_query_business
  - db_insert_fund_event
  - memory_save
triggers:
  - "解析手工流水"
  - "手工流水解析"
  - "录入手工流水"
  - "手工账"
arguments:
  account_code:
    description: "账户编码"
    required: true
  sample_file:
    description: "样本文件路径"
    required: false
---

# 手工流水解析器

## 工作流程

1. 如果有文件，先用 file_parse 解析
2. 如果是用户直接描述的流水，按描述创建记录
3. 识别关键字段：日期、摘要、收入/支出、金额
4. 生成解析规则并入库
5. 使用 memory_save 记录账户和规则对应关系

## 规则

- 手工流水必须有日期和金额
- 缺少摘要时使用默认摘要"手工录入"
- 金额为负数表示支出
