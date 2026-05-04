"""parser.manual — 手工流水解析器生成

固定步骤：
1. 验证输入 Schema
2. 读取 Excel 样本
3. 加载手工字段池（manual_field_pool）
4. 识别布局（一行一条 / 一行多科目）
5. 生成解析代码
6. 创建 Parser artifact 草稿
"""
