---
name: skill-creator
description: "帮助用户创建新的技能。分析样本文件，生成标准 SKILL.md 格式的技能定义。"
when_to_use: "当用户要求创建新技能、学习新能力、或需要自动化某个重复性任务时"
allowed-tools:
  - fs_read
  - fs_write
  - fs_list
  - openpyxl_read
  - openpyxl_write
  - ask_user
  - skill_run
  - skill_test
arguments:
  intent:
    description: "用户想创建的技能意图描述"
    required: true
  sample_files:
    description: "样本文件路径列表"
    required: false

---

# 技能创建器

## 工作流程
1. 捕获意图：理解用户要创建什么技能
2. 分析样本：读取用户提供的样本文件，理解数据结构
3. 生成 SKILL.md：按标准格式生成技能定义
4. 验证：使用 skill_test 测试新技能
5. 优化：根据测试结果迭代改进

## 规则
- 技能名称使用 kebab-case 格式
- description 必须简洁准确
- 工作流程必须可由 LLM 自主执行
- 规则要包含边界条件和错误处理
