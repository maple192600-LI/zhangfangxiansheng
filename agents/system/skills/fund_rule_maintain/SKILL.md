---
name: fund_rule_maintain
description: "维护和迭代现有的报表填充 RuleArtifact 草稿"
when_to_use: "当用户需要修改报表规则、调整填充逻辑、或更新已有规则时"
version: "4.0.0"
execution_mode: instruction
allowed-tools:
  - db_query_business
  - memory_save
  - memory_search
  - skill_step_report
triggers:
  - "修改规则"
  - "更新规则"
  - "调整报表规则"
  - "规则维护"
  - "编辑规则"
arguments:
  rule_id:
    description: "要修改的规则 ID（RuleArtifact ID）"
    required: true
  change_request:
    description: "修改请求描述"
    required: true
---

# 规则维护

## 第一步：加载现有规则

调用 `db_query_business(table_name="rule_artifacts", filters={"id": <rule_id>})`。
如果规则不存在，告知用户并列出所有可用规则。

## 第二步：展示当前规则

将当前规则的内容展示给用户：
- 规则名称
- placeholder_bindings（占位符绑定）
- loop_config（循环配置）
- 关联模板
- 创建时间

## 第三步：解析修改请求

根据用户的 change_request 理解需要修改什么：
- 修改占位符绑定
- 修改循环配置
- 修改数据查询逻辑
- 增加新的绑定
- 删除某个绑定

## 第四步：应用修改

在当前规则基础上修改（保留未修改的部分），生成新的规则配置。

## 第五步：保存新版本草稿

通过 `artifact_service.create_rule_draft` 保存新版本 RuleArtifact 草稿。
旧版本保留供回溯（不删除）。
新版本继承旧版本的未修改配置。
新版本作为 draft 状态，需要用户审批后才能变为 active。

## 第六步：记录修改历史

调用 `memory_save(key="规则修改_<rule_id>", content="修改了规则<rule_id>：<修改原因>。新版本ID=<新ID>")`。

## 关键规则

- 旧版本不删除，只保留供回溯
- 新版本继承旧版本的未修改配置
- 修改记录必须包含：修改了什么、为什么修改
- 如果修改涉及数据表字段映射的变化，必须先验证新映射能正确获取数据
