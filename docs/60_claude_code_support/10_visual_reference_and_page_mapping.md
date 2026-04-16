# 视觉参考与页面映射文档

## 一、作用

这份文档用于把截图、HTML 原型、最终页面名和开发页面文件一一对应。

否则 Claude Code 很容易看过截图，实际却不知道该把它落成哪个 Vue 页面。

## 二、页面映射表

> 以下映射与 `templates/frontend/preview_v4_confirmed.html` 导航结构完全对齐。

### 首页（一级导航）

| 页面中文名 | Tab 名 | 前端文件建议 | 当前来源 | HTML type |
|---|---|---|---|---|
| 首页 / 工作总览 | 工作总览 | `frontend/src/views/HomeDashboard.vue` | 已确认 HTML | home_dashboard |
| 首页 / 待办追踪 | 待办追踪 | `frontend/src/views/HomeTasks.vue` | 已确认 HTML | home_tasks |
| 首页 / 快捷入口 | 快捷入口 | `frontend/src/views/HomeQuick.vue` | 已确认 HTML | home_quick |
| 首页 / 系统提醒 | 系统提醒 | `frontend/src/views/HomeSystem.vue` | 已确认 HTML | home_system |

### 资金板块 — 工作台

| 页面中文名 | Tab 名 | 前端文件建议 | 当前来源 | HTML type |
|---|---|---|---|---|
| 资金板块 / 工作台 / 网银导入 | 网银导入 | `frontend/src/views/BankImport.vue` | 已确认 HTML | bank_import |
| 资金板块 / 工作台 / 手工流水 | 手工流水 | `frontend/src/views/ManualFlow.vue` | 已确认 HTML | manual_flow |
| 资金板块 / 工作台 / 手动维护 | 手动维护 | `frontend/src/views/ManualMaintenance.vue` | 已确认 HTML | manual_fix |
| 资金板块 / 工作台 / 上传结果预览 | 上传结果预览 | `frontend/src/views/UploadPreview.vue` | 已确认 HTML | upload_preview |

### 资金板块 — 资金日报表

| 页面中文名 | Tab 名 | 前端文件建议 | 当前来源 | HTML type |
|---|---|---|---|---|
| 资金板块 / 资金日报表 / 基础数据表 | 基础数据表 | `frontend/src/views/BaseDataTable.vue` | 已确认 HTML | base_data |
| 资金板块 / 资金日报表 / 现金日记账 | 现金日记账 | `frontend/src/views/CashJournal.vue` | 已确认导航 | cash_journal |
| 资金板块 / 资金日报表 / 账户余额表 | 账户余额表 | `frontend/src/views/AccountBalance.vue` | 已确认导航 | account_balance |
| 资金板块 / 资金日报表 / 收入明细表 | 收入明细表 | `frontend/src/views/IncomeList.vue` | 已确认导航 | income_list |
| 资金板块 / 资金日报表 / 支出明细表 | 支出明细表 | `frontend/src/views/ExpenseList.vue` | 已确认导航 | expense_list |

### 资金板块 — 资金综合报表（V1 简化，后续扩展）

| 页面中文名 | Tab 名 | 前端文件建议 | 当前来源 |
|---|---|---|---|
| 资金板块 / 资金综合报表 / 主要账户余额表 | 主要账户余额表 | `frontend/src/views/MajorBalance.vue` | 导航占位 |
| 资金板块 / 资金综合报表 / 月末盘点表 | 月末盘点表 | `frontend/src/views/MonthCheck.vue` | 导航占位 |
| 资金板块 / 资金综合报表 / 资金周报 | 资金周报 | `frontend/src/views/WeekReport.vue` | 导航占位 |
| 资金板块 / 资金综合报表 / 资金月报 | 资金月报 | `frontend/src/views/MonthReport.vue` | 导航占位 |
| 资金板块 / 资金综合报表 / 资金年报 | 资金年报 | `frontend/src/views/YearReport.vue` | 导航占位 |

### 系统设置（V1 必做）

| 页面中文名 | Tab 名 | 前端文件建议 | 当前来源 |
|---|---|---|---|
| 系统设置 / 数据中心 / 账户数据管理 | 账户数据管理 | `frontend/src/views/AccountManage.vue` | 需求已确认 |
| 系统设置 / AI配置 / API KEY配置 | API KEY 配置 | `frontend/src/views/AIConfig.vue` | 执行文档已确认 |
| 系统设置 / AI配置 / Agent配置 | Agent 配置 | `frontend/src/views/AgentConfig.vue` | 执行文档已确认 |
| 系统设置 / 备份恢复 | 备份恢复 | `frontend/src/views/BackupRestore.vue` | 执行文档已确认 |
| 系统设置 / 操作日志 | 操作日志 | `frontend/src/views/OperationLog.vue` | 执行文档已确认 |

### 系统设置（V2+ 占位，V1 仅建路由骨架）

| 页面中文名 | 前端文件建议 | 备注 |
|---|---|---|
| 系统设置 / 数据中心 / 报表模板管理 | `frontend/src/views/ReportTemplate.vue` | V2+ |
| 系统设置 / 数据中心 / 部门信息管理 | `frontend/src/views/Department.vue` | V2+ |
| 系统设置 / 规则中心/* | `frontend/src/views/rules/` | V2+ |
| 系统设置 / 异常中心/* | `frontend/src/views/exceptions/` | V2+ |
| 系统设置 / 用户和权限/* | `frontend/src/views/permissions/` | V2+ |

### OCR、贷款、预算（V2+ 占位）

| 一级导航 | 前端路由 | 备注 |
|---|---|---|
| OCR识别 | `/ocr` | V2+ 建路由占位 |
| 贷款管理 | `/loan` | V2+ 建路由占位 |
| 预算管理 | `/budget` | V2+ 建路由占位 |
| AI智能体 | `/ai-agent` | V1 仅展示 Agent 列表和状态 |

## 三、页面来源优先级

1. 已确认 HTML 原型
2. 页面执行文档
3. 视觉风格规范
4. 临时草图

若不同来源冲突，以页面执行文档和已确认 HTML 原型为准。

## 四、页面状态要求

每个页面至少要落以下状态：
- 空状态
- 正常状态
- 处理中状态
- 异常状态
- 无权限状态（预留）

## 五、开发要求

Claude Code 新建任何页面前，必须先在本文件补充对应映射，再开始写页面文件。
