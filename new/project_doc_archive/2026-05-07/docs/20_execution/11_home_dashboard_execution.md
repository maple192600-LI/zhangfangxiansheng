# 11 Home Dashboard Execution

> 状态：reference。本文为首页工作台参考，不能覆盖当前主链路和文档审计结论。

## 1. Module goal

Build the V1 home page as a work control board.

It is not a boss BI page.
It is the first screen a cashier opens every day.

## 2. Confirmed information architecture

Top-level left navigation:

- 首页
- 资金板块
- OCR识别
- 贷款管理
- 预算管理
- AI智能体
- 系统设置

V1 coding only needs to fully implement:

- 首页
- 资金板块
- 系统设置中的必要项

Other top-level items can stay as placeholders.

## 3. Page and tabs

### page
`frontend/src/views/HomeDashboard.vue`

### tabs to implement
- 工作总览
- 待办追踪
- 快捷入口
- 系统提醒

## 4. Data sources

The page must read from:

- pending bank import batches
- pending manual batches
- pending abnormal rows
- latest report generation status
- latest backup status
- latest operation logs
- highlighted account summary

## 5. Required cards and widgets

### 工作总览
must show:

- 待处理任务数
- 异常提醒数
- 今日生成状态
- 重点账户变化

### 待办追踪
must show:

- 待导入
- 待确认
- 待生成

### 快捷入口
must include at least:

- 进入工作台
- 查看基础数据表
- 异常中心
- 操作日志

### 系统提醒
must include at least:

- 最近一次日报生成时间
- 最近一次备份
- OCR 状态占位
- 最近动作摘要

## 6. APIs

- `GET /api/home/overview`
- `GET /api/home/todos`
- `GET /api/home/quick-links`
- `GET /api/home/system-status`

## 7. Done standard

This module is complete only if:

- home page is independent and top-level
- all texts are Chinese
- data is from real tables, not hard-coded mock only
- the page works even when there is no data
