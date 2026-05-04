"""parser.bank — 银行流水解析器生成

固定步骤：
1. 验证输入 Schema（account_code, sample_file）
2. 读取样本文件 → 脱敏处理
3. 加载字段字典 + 别名库
4. 生成解析代码（只能调白名单基元）
5. 创建 Parser artifact 草稿
6. 返回校验日志 + 置信度
"""
