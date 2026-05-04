"""rule.maintain — 规则维护/迭代

固定步骤：
1. 加载现有 Rule artifact
2. 解析用户修改请求
3. 应用修改到 bindings / loop_config
4. 创建新版本 Rule artifact（旧版保留）
5. 返回新旧版本对比
"""
