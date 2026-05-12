# FundEvent

## 基本信息

| 字段 | 内容 |
|------|------|
| 术语 | FundEvent |
| 所属模块 | 核心概念 |
| 业务解释 | 一笔标准资金流水记录。所有来源的流水最终都统一成这个格式，所有报表都从这里取数。 |

## 易混淆

| 字段 | 内容 |
|------|------|
| 容易混淆什么 | FundEvent ≠ FundAgent。FundAgent 是已删除的旧领域 Agent 系统，FundEvent 是当前的流水事实表。两者没有关系。 |

## 给 Agent 的提示

- 数据库表名：`fund_events`
- 标准 12 字段格式（CANONICAL_12）：business_date, entity_code, entity_name, account_code, account_name, summary, counterparty, amount_in, amount_out, rolling_balance, state, source
- 状态只有四种：正常、待确认、异常、已作废
- 报表只统计 state="正常"的记录
- `backend/fund/` 是确定性执行基础设施，不等于旧 FundAgent
