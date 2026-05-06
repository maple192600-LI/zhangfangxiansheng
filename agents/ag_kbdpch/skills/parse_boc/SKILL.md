---
name: parse_boc
description: "中国银行流水智能解析——自动识别 .xls 和 .xlsx 格式，提取日期、方向、对方、收入、支出、余额，生成可读摘要，输出结构化预览数据。"
when_to_use: "当用户上传中国银行流水、中行对账单时"
version: "2.0"
execution_mode: code
allowed-tools:
  - file_parse
  - db_query_business
  - memory_search
  - skill_step_report
arguments:
  file_path:
    description: "中行流水文件路径"
    required: true
dependencies:
  pip:
    - "xlrd==1.2.0"
    - "openpyxl>=3.0"
triggers:
  - "中行流水"
  - "中国银行流水"
  - "中行对账单"
  - "BOC流水"
---
