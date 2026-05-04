---
name: fund_rule_template_fill
description: "根据模板生成报表填充规则，将数据映射到报表模板的占位符"
when_to_use: "当用户需要生成报表、填充报表模板、或创建报表生成规则时"
allowed-tools:
  - file_parse
  - db_query_business
  - db_save_parser_template
  - openpyxl_read
  - openpyxl_write
  - memory_save
triggers:
  - "生成报表"
  - "填充报表"
  - "报表模板"
  - "报表规则"
arguments:
  template_job_id:
    description: "模板任务 ID"
    required: true
  placeholder_list:
    description: "需要填充的占位符列表"
    required: true
---

# 报表填充规则生成

## 工作流程

1. 读取报表模板文件（openpyxl_read 或 file_parse）
2. 解析模板中的占位符（${xxx}, {{xxx}}, 【xxx】）
3. 为每个占位符匹配数据源（数据库查询或固定值）
4. 创建填充规则：占位符 → 数据查询 + 格式化
5. 使用 db_save_parser_template 保存规则

## 规则

- 占位符名称中包含"日期"时使用当前会计期间
- 金额类占位符必须指定数字格式
- 无法匹配数据源的占位符标记为"需手动填充"
