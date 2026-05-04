---
name: fund_template_inference
description: "自动识别空白模板中的占位符并推断数据映射"
when_to_use: "当用户上传空白报表模板、需要自动识别模板结构、或创建新报表模板时"
allowed-tools:
  - file_parse
  - openpyxl_read
  - db_query_business
  - db_save_parser_template
  - memory_save
triggers:
  - "识别模板"
  - "模板推断"
  - "空白模板"
  - "模板占位符"
arguments:
  template_file:
    description: "模板文件路径"
    required: true
---

# 模板自动推断

## 工作流程

1. 使用 openpyxl_read 读取模板结构
2. 提取所有占位符（${xxx}, {{xxx}}, 【xxx】）
3. 识别合并单元格区域（表头、标题等）
4. 为每个占位符推断数据源（基于字段字典和别名库）
5. 生成映射规则草稿供用户确认

## 规则

- 无法自动推断的占位符标记为"待人工确认"
- 推断置信度低于 0.5 时必须提示用户确认
- 合并单元格区域保持原有格式
