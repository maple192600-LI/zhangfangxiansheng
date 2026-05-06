---
name: parse_bank_flow
description: "通用银行流水智能解析——自动识别不同银行流水格式，联查数据中心实体判断内部交易，按出纳习惯生成摘要，输出结构化预览数据。"
when_to_use: "当用户上传银行流水文件但不确定是哪家银行时"
version: "3.0"
execution_mode: code
allowed-tools:
  - file_parse
  - db_query_business
  - memory_search
  - skill_step_report
arguments:
  file_path:
    description: "银行流水文件路径"
    required: true
dependencies:
  pip:
    - "xlrd==1.2.0"
    - "openpyxl>=3.0"
triggers:
  - "银行流水"
  - "解析流水"
  - "流水解析"
---
