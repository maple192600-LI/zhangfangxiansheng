"""rule.template_fill — 报表填充规则生成

固定步骤：
1. 验证输入 Schema（template_file, placeholder_list）
2. 为每个占位符匹配字段字典 → 选择基元
3. 生成 placeholder_bindings
4. 生成 loop 配置（行数据区域）
5. 创建 Rule artifact 草稿
6. 校验：18 个占位符必须恰好全部覆盖
"""
