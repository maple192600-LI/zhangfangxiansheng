"""fund.primitives · 37 函数基元库白名单

契约锚点：docs/30_contracts/25_primitives_whitelist.md
保护脚本：tools/guards/check_primitives_whitelist.py

| 模块            | 函数数 | 职责                     |
|-----------------|--------|--------------------------|
| sheet_ops       | 6      | Excel 表格操作           |
| value_parsers   | 5      | 单元格取值 / 归一化      |
| canonical       | 4      | 12 列 canonical 行产出   |
| master_match    | 4      | 单位 / 账户匹配          |
| base_queries    | 6      | 基础数据表查询           |
| aggregations    | 6      | 聚合运算                 |
| template_fill   | 6      | 报表模板填写             |

合计 37。禁止 Agent 在 artifact 代码里"临时实现"缺失基元（违反 §C5）。
"""
