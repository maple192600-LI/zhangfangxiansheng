---
name: fund_parser_bank
description: "解析银行流水文件，生成银行流水解析器"
when_to_use: "当用户需要解析银行流水、创建银行流水解析规则、或上传了银行流水文件时"
allowed-tools:
  - file_parse
  - db_query_business
  - db_insert_fund_event
  - memory_save
triggers:
  - "解析银行流水"
  - "银行流水解析"
  - "银行流水解析器"
  - "解析银行对账单"
arguments:
  account_code:
    description: "银行账户编码"
    required: true
  sample_file:
    description: "样本文件路径"
    required: true
---

# 银行流水解析器

## 工作流程

1. 使用 file_parse 解析用户上传的银行流水文件
2. 分析文件结构（列名、数据格式、日期/金额列位置）
3. 识别银行类型（根据文件格式和列名特征）
4. 生成解析规则：列映射 + 数据清洗 + 日期格式转换 + 金额规范化
5. 使用 db_insert_fund_event 将解析结果写入资金流水表
6. 使用 memory_save 记录该银行的特征和解析规则

## 规则

- 金额列必须识别收入/支出方向
- 日期格式统一转换为 YYYY-MM-DD
- 余额列做校验：当前余额 = 上一条余额 + 本次变动
- 去重：相同日期+金额+摘要的记录不重复导入
