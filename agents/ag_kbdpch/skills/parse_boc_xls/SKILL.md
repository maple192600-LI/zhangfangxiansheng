---
name: parse_boc_xls
description: "解析中行银行流水XLS文件（旧格式专用）"
when_to_use: "当用户上传中国银行 .xls 格式流水时"
version: "1.0"
execution_mode: code
allowed-tools:
  - file_parse
arguments:
  file_path:
    description: "中行 XLS 流水文件路径"
    required: true
dependencies:
  pip:
    - "xlrd==1.2.0"
---
