# UI 表格系统

## 当前统一表格体系

项目使用两层表格体系：

### 1. Tabulator Tables（主表格引擎）

- 包：`tabulator-tables ^6.4.0`
- 用于需要高级功能的数据表格：排序、筛选、分页、虚拟滚动、行编辑
- 封装在 `AdvancedDataTable.vue` 组件中

### 2. naive-ui 组件（辅助 UI）

- 包：`naive-ui ^2.44.1`
- 用于表单、弹窗、布局、选择器等 UI 组件
- 当前前端代码中未发现直接使用 `n-data-table` 的场景

### 职责边界

| 场景 | 使用 |
|------|------|
| 资金流水、主数据、报表等数据密集型表格 | Tabulator (AdvancedDataTable) |
| 表单输入、选择器、弹窗 | naive-ui |
| 图表 | ECharts |

## AdvancedDataTable 组件

- 路径：`frontend/src/components/workbench/AdvancedDataTable.vue`
- 封装 Tabulator，提供统一的数据表格接口

## 使用 Tabulator 的页面（20 个文件）

| 页面/组件 | 文件 |
|----------|------|
| 账户管理 | `AccountManage.vue` |
| 银行导入 | `BankImport.vue` |
| 手工流水 | `ManualFlow.vue` |
| 手工维护 | `ManualMaintenance.vue` |
| 上传预览 | `UploadPreview.vue` |
| 基础数据 | `BaseDataTable.vue` |
| 日报 | `DailyReport.vue` |
| 现金日记账 | `CashJournal.vue` |
| 账户余额 | `AccountBalance.vue` |
| 收入明细 | `IncomeList.vue` |
| 支出明细 | `ExpenseList.vue` |
| 异常中心 | `ExceptionCenter.vue` |
| 操作日志 | `OperationLog.vue` |
| 报表模板 | `TemplateReport.vue` |
| 工作台实验 | `WorkbenchTableLab.vue` |

### Tabulator 支持文件

| 文件 | 用途 |
|------|------|
| `composables/useTabulatorTable.js` | Tabulator 初始化和配置 hook |
| `composables/useTemplateColumns.js` | 模板列配置 |
| `utils/tabulatorFormatters.js` | 自定义格式化器 |
| `styles/tabulator-theme.css` | 主题样式 |

---
**校准来源：** `frontend/package.json`、`frontend/src/components/workbench/AdvancedDataTable.vue`、`frontend/src/views/`、`frontend/src/composables/useTabulatorTable.js`
**最后校准：** 2026-05-17
