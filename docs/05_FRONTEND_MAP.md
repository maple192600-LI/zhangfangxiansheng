# 前端地图

## 路由统计

| 指标 | 数量 |
|------|------|
| Placeholder route entries | 26 |
| Implemented route import entries | 36 |
| `.vue` 文件 | 42 |

## 已实现页面（36 个 route import entries）

| 分组 | 路由名 | 组件 |
|------|--------|------|
| 登录 | `login` | Login.vue |
| 首页 | `home` | HomeDashboard.vue |
| | `home-tasks` | HomeTasks.vue |
| | `home-quick` | HomeQuick.vue |
| | `home-system` | HomeSystem.vue |
| 工作台 | `bank-import` | BankImport.vue |
| | `manual-flow` | ManualFlow.vue |
| | `manual-maintenance` | ManualMaintenance.vue |
| | `upload-preview` | UploadPreview.vue |
| 工作流 | `workflow-list` | WorkflowList.vue |
| | `workflow-editor` | WorkflowEditor.vue |
| 日报/报表 | `daily-report` | DailyReport.vue |
| | `base-data` | BaseDataTable.vue |
| | `cash-journal` | CashJournal.vue |
| | `account-balance` | AccountBalance.vue |
| | `income-list` | IncomeList.vue |
| | `expense-list` | ExpenseList.vue |
| | `major-balance` | MajorBalance.vue |
| | `month-check` | MonthCheck.vue |
| | `week-report` | WeekReport.vue |
| | `month-report` | MonthReport.vue |
| | `year-report` | YearReport.vue |
| Agent | `agent-review` | AgentReview.vue |
| | `agent-detail` | AgentDetail.vue |
| 工作台实验 | `workbench-table-lab` | WorkbenchTableLab.vue |
| 数据中心 | `account-manage` | AccountManage.vue |
| | `data-report-tpl` | ReportTemplate.vue |
| 规则中心 | `rule-bank` | BankRule.vue |
| 异常中心 | `exception-receipt` | ExceptionCenter.vue |
| | `exception-other` | ExceptionCenter.vue |
| 系统设置 | `ai-config` | AIConfig.vue |
| | `system-maintenance` | SystemMaintenance.vue |
| | `backup-restore` | SystemMaintenance.vue |
| | `data-cleanup` | SystemMaintenance.vue |
| | `operation-log` | OperationLog.vue |

## Placeholder 路由（26 个）

### V1 禁止（应清理）

| 路由名 | 路径 | 禁止原因 |
|--------|------|----------|
| `ocr-upload` | `/ocr/upload` | OCR 属于 V1 禁止 |
| `ocr-settings` | `/ocr/settings` | 同上 |
| `invoice-ledger` | `/invoice-ledger` | 发票属 V1 禁止 |
| `contract-ledger` | `/contract-ledger` | 合同属 V1 禁止 |
| `loan-ledger` | `/loan-ledger` | 贷款属 V1 禁止 |
| `loan-interest` | `/loan-interest` | 同上 |
| `loan-other-ledger` | `/loan-other-ledger` | 同上 |
| `loan-other` | `/loan-other` | 同上 |
| `budget-plan` | `/budget-plan` | 预算属 V1 禁止 |

### 待产品决策

| 路由名 | 路径 | 说明 |
|--------|------|------|
| `agent-social` | `/agent/social` | Agent 细分 |
| `agent-daily` | `/agent/daily` | Agent 细分 |
| `agent-cost` | `/agent/cost` | Agent 细分 |
| `agent-income` | `/agent/income` | Agent 细分 |
| `agent-material` | `/agent/material` | Agent 细分 |
| `agent-tax` | `/agent/tax` | Agent 细分 |
| `agent-custom` | `/agent/custom` | Agent 细分 |
| `data-department` | `/data/department` | 部门管理 |
| `rule-io` | `/rule/io` | 收支规则 |
| `rule-origin` | `/rule/origin` | 来源规则 |
| `rule-voucher` | `/rule/voucher` | 凭证规则 |
| `rule-other` | `/rule/other` | 其他规则 |
| `perm-admin` | `/perm/admin` | 管理员权限 |
| `perm-cashier` | `/perm/cashier` | 出纳权限 |
| `perm-manager` | `/perm/manager` | 经理权限 |
| `perm-boss` | `/perm/boss` | 老板权限 |
| `perm-accountant` | `/perm/accountant` | 会计权限 |

## 共享组件

| 组件 | 用途 |
|------|------|
| `MasterAccountSelect.vue` | 账户选择器 |
| `MasterEntitySelect.vue` | 法人选择器 |
| `AdvancedDataTable.vue` | 高级表格组件 |
| `WorkflowNode.vue` | 工作流节点组件 |
| `AgentCreateModal.vue` | Agent 创建弹窗 |

## Agent 页面子组件（AgentDetail 内部）

| 组件 | 用途 |
|------|------|
| `ChatPanel.vue` | 聊天面板 |
| `FilePanel.vue` | 文件面板 |
| `MemoryPanel.vue` | 记忆面板 |
| `SessionsPanel.vue` | 会话列表 |
| `SettingsPanel.vue` | 设置面板 |
| `SkillsPanel.vue` | 技能面板 |

---
**校准来源：** `frontend/src/router/index.js`、`frontend/src/views/`、`frontend/src/components/`
**最后校准：** 2026-05-17
