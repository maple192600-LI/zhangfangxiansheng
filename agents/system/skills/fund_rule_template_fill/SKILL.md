---
name: fund_rule_template_fill
description: "根据模板生成报表填充规则，将数据映射到报表模板的占位符"
when_to_use: "当用户需要生成报表、填充报表模板、或创建报表生成规则时"
version: "3.0.0"
execution_mode: instruction
code_entry: "rule.template_fill"
allowed-tools:
  - file_parse
  - db_query_business
  - openpyxl_read
  - openpyxl_write
  - memory_save
  - memory_search
  - skill_step_report
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
    required: false
---

# 报表填充规则生成

## 第一步：读取模板文件

调用 `file_parse(path="<模板文件路径>")` 或 `openpyxl_read(path="<模板文件路径>")`。
读取模板的全部 sheet 和单元格内容。

## 第二步：提取占位符

扫描模板内容，识别所有占位符：
- `${xxx}` 格式
- `{{xxx}}` 格式
- `【xxx】` 格式
- 其他明显的标记（如 `__XXX__`）

将找到的占位符整理为列表。

## 第三步：查询可用数据源

调用 `db_query_business(table_name="fund_events")` 获取最近资金流水数据。
根据占位符名称推断需要的数据：
- 含"收入"、"收款"、"贷方" → 汇总 amount_in
- 含"支出"、"付款"、"借方" → 汇总 amount_out
- 含"余额" → 取最新 rolling_balance
- 含"日期"、"期间" → 使用当前会计期间
- 含"法人"、"公司" → 从 entities 表获取

## 第四步：为每个占位符创建映射规则

对每个占位符生成映射：
```json
{
  "占位符名称": {
    "source": "fund_events|entities|accounts|fixed",
    "field": "amount_in|amount_out|rolling_balance|...",
    "filter": {"business_date": "2025-01", ...},
    "aggregate": "sum|latest|count",
    "format": "number:2|date|text"
  }
}
```

无法自动匹配的占位符标记为 `"source": "manual", "reason": "需要用户指定数据源"`。

## 第五步：产出 RuleArtifact

将占位符映射整理为 RuleArtifact 的 placeholder_bindings 和 loop_config。
RuleArtifact 通过 Fund Agent 技能 `rule.template_fill` 产出，状态为 draft，需要用户审批后变为 active。

## 第六步：向用户报告结果

列出：
- 已自动映射的占位符（N个）
- 需要用户确认的占位符（N个）
- 完全无法推断的占位符（N个）

调用 `memory_save(key="报表规则_<报表名称>", content="<报表名称>的填充规则，包含<N>个自动映射和<M>个待确认占位符")`。

## 关键规则

- 占位符名称中包含"日期"时默认使用当前会计期间，必须向用户确认
- 金额类占位符必须指定数字格式（保留几位小数）
- 无法匹配数据源的占位符不得猜测，必须标记为"需手动填充"
- 所有自动推断结果必须向用户展示并确认后才能使用
