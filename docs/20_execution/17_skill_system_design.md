# 17 · Skill 与 Memory 标准

本文件定义 Skill 和 Memory 的当前标准格式。

## Skill 目录结构

```text
skills/{skill_name}/
  SKILL.md              必需，技能说明和触发信息
  scripts/              可选，确定性脚本
  references/           可选，按需读取的参考资料
  assets/               可选，模板或输出资源
  tests/                可选，样本和期望输出
  experience.json       自动生成，执行经验
  .meta.json            自动生成，生命周期和内容哈希
```

## SKILL.md 必填字段

```yaml
---
name: parse-bank-example
description: "说明技能做什么，以及什么时候使用。description 是主要触发依据。"
when_to_use: "用户上传某类流水、模板或要求创建对应规则时使用。"
allowed-tools:
  - file_parse
  - openpyxl_read
inputs:
  file_path:
    description: "用户上传文件路径"
    required: true
outputs:
  artifact:
    description: "Parser 或 Rule 草稿"
---
```

正文必须包含：

- 工作流程。
- 规则和限制。
- 样本校验要求。
- 失败时如何询问用户。
- 何时保存经验到 Memory。

## Skill 类型

| 类型 | 用途 |
| --- | --- |
| 指令型 | 指导 Agent 讨论、分析、创建规则 |
| 代码型 | 封装确定性脚本 |
| 混合型 | 指令负责判断，脚本负责关键计算 |

财务准确性关键任务应优先沉淀为 Parser 或 Rule artifact，而不是依赖长期对话指令。

## experience.json

```json
{
  "stats": {
    "total_runs": 0,
    "successes": 0,
    "last_run_at": null
  },
  "learned_aliases": {},
  "corrections": [],
  "recent_errors": []
}
```

用途：

- 保存字段别名。
- 保存用户纠错。
- 保存成功率和错误摘要。
- 帮助 Agent 后续维护 Skill。

不得保存完整账号、完整流水行、未脱敏金额明细。

## .meta.json

```json
{
  "source": "agent_created",
  "lifecycle": "active",
  "content_hash": "",
  "created_at": "",
  "last_used_at": ""
}
```

用途：

- 标记来源。
- 标记生命周期。
- 保护用户修改过的 Skill 不被自动覆盖。

## Memory 标准

Memory 记录格式：

```json
{
  "category": "preference | business_fact | rule_experience | correction",
  "content": "可复用且已脱敏的事实或经验",
  "source": "user_confirmed | agent_observed | rule_review",
  "importance": 0.0
}
```

保存规则：

- 用户明确确认的信息优先保存。
- Agent 推断的信息必须标记来源，不得当作确定事实。
- 敏感数据必须脱敏。
- 可从规则、批次、审核记录追溯来源。

## 创建规则时的沉淀要求

Agent 创建 Parser 或 Rule 后，至少沉淀：

- 规则名称和适用场景。
- 样本校验结果。
- 用户接受或拒绝意见。
- 新发现字段别名。
- 新发现银行或模板特征。

这些经验用于下一次匹配、解释和维护，不替代确定性执行。
