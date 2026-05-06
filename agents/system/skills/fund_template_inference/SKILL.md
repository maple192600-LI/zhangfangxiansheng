---
name: fund_template_inference
description: "自动识别空白模板中的占位符并推断数据映射"
when_to_use: "当用户上传空白报表模板、需要自动识别模板结构、或创建新报表模板时"
version: "2.0.0"
execution_mode: instruction
code_entry: "template.inference"
allowed-tools:
  - file_parse
  - openpyxl_read
  - db_query_business
  - db_save_parser_template
  - memory_save
  - memory_search
  - skill_step_report
triggers:
  - "识别模板"
  - "模板推断"
  - "空白模板"
  - "模板占位符"
  - "新建模板"
arguments:
  template_file:
    description: "模板文件路径"
    required: true
---

# 模板自动推断

## 第一步：读取模板原始结构

调用 `openpyxl_read(path="<template_file>")` 读取模板。
获取所有 sheet 名称、每个 sheet 的行列数据。

## 第二步：扫描占位符

逐单元格扫描，识别占位符模式：
- `${xxx}` 格式
- `{{xxx}}` 格式
- `【xxx】` 格式
- 单元格值为空但周围有标签的（隐式占位符）

记录每个占位符的：
- 所在 sheet 和单元格位置（如 Sheet1!B3）
- 占位符文本
- 周围的标签文本（上下左右相邻单元格的值）

## 第三步：识别合并单元格

检查合并单元格区域：
- 跨多列的合并 → 通常是表头标题
- 跨多行的合并 → 通常是分组标签
- 记录合并区域的范围和用途

## 第四步：推断数据映射

对每个占位符，根据名称和上下文推断数据源：

调用 `db_query_business(table_name="fund_events", limit=5)` 查看可用字段。

推断规则：
- 占位符含"收入"/"贷方"/"收款" → `fund_events.amount_in` 的汇总
- 占位符含"支出"/"借方"/"付款" → `fund_events.amount_out` 的汇总
- 占位符含"余额" → 最新 `fund_events.balance`
- 占位符含"日期" → 当前会计期间
- 占位符含"法人"/"公司" → `entities` 表的名称字段
- 占位符含"银行" → `accounts` 表的相关字段
- 占位符含"合计"/"小计"/"汇总" → 金额汇总
- 占位符含"期初"/"年初" → 期初余额查询
- 占位符含"期末"/"年末" → 期末余额查询

为每个推断给出置信度（high/medium/low）。

## 第五步：生成映射规则

将推断结果整理为结构化 JSON：
```json
{
  "Sheet1!B3": {
    "placeholder": "${本月收入合计}",
    "source": "fund_events",
    "field": "amount_in",
    "aggregate": "sum",
    "filter": {"business_date": "当月"},
    "confidence": "high"
  }
}
```

## 第六步：向用户确认

展示推断结果，分三类：
1. 高置信度映射（绿色）— 建议直接使用
2. 中置信度映射（黄色）— 需要用户确认
3. 低置信度映射（红色）— 需要用户指定

用户确认后，调用 `db_save_parser_template(
  template_name="<用户指定的模板名称>",
  account_code="",
  file_format="xlsx",
  sample_headers="<占位符列表>",
  mapping_json="<确认后的映射规则>"
)`。

## 第七步：记录经验

调用 `memory_save(key="模板推断_<模板名称>", content="<模板名称>包含<N>个占位符，<M>个自动推断成功，<K>个需手动指定")`。

## 关键规则

- 无法自动推断的占位符必须标记为"待人工确认"，绝不能猜测
- 置信度评估要保守，宁多问不少问
- 合并单元格区域必须保持原有格式，不在合并区域内拆分填充
- 推断结果必须全部展示给用户确认后才能保存
