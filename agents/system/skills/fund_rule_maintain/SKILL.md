---
name: fund_rule_maintain
description: "维护和迭代现有的报表填充规则"
when_to_use: "当用户需要修改报表规则、调整填充逻辑、或更新已有规则时"
allowed-tools:
  - db_query_business
  - db_save_parser_template
  - openpyxl_read
  - memory_save
triggers:
  - "修改规则"
  - "更新规则"
  - "调整报表规则"
  - "规则维护"
arguments:
  rule_id:
    description: "要修改的规则 ID"
    required: true
  change_request:
    description: "修改请求描述"
    required: true
---

# 规则维护

## 工作流程

1. 加载现有规则（db_query_business 查询）
2. 解析用户的修改请求
3. 创建新版本规则（旧版保留，版本号+1）
4. 使用 db_save_parser_template 保存新版本
5. 使用 memory_save 记录修改原因

## 规则

- 旧版本不删除，只标记为"已过期"
- 新版本继承旧版本的未修改配置
- 修改记录包含：修改时间、修改人、修改原因
