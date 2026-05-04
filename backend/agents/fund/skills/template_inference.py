"""template.inference — 模板自动识别

三阶段流水线：
Stage A: 纯代码结构解析（无 AI）
  - 扫描 .xlsx/.xltx
  - 找到 ${xxx}/{{xxx}}/【xxx】占位符
  - 识别合并单元格、行数据锚点

Stage B: AI 语义映射
  - 占位符 → 字段字典 key
  - 选择建议 primitive
  - 产出 Rule artifact 草稿 + 置信度

Stage C: 用户确认
  - 前端显示：占位符 → 绑定 → 置信度
  - 用户接受/修改/拒绝
"""
