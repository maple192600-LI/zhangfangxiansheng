# UI-4E: 单位选择器 + 主数据字段契约 + 报表打印统一治理

> 阶段：UI-4E | 分支：`audit/frontend-ui-4d-print-masterdata-linkage-fix` | 日期：2026-05-12

## 系统性问题

| # | 问题 | 根因 |
|---|------|------|
| 1 | 综合报表单位下拉显示为一长条 | TemplateReport 用 `style="min-width:140px"` 无上限，全称撑满 |
| 2 | 全称/简称字段语义混乱 | 后端只返回 `entity_name`，前端各页面猜测含义 |
| 3 | 打印预览包含左侧主目录 | `@media print` 在 `<style scoped>` 内，无法匹配 MainLayout 的 `.sidebar` |
| 4 | 同类逻辑逐页重复 | 每页独立写 entityOptions、handlePrint |

## 解决方案

### 1. 后端字段契约

`get_accounts_tree` 现在返回 4 个字段：

```json
{
  "entity_id": 258,
  "entity_name": "养护",           // 向后兼容（= short_name）
  "entity_full_name": "山西喜跃发道路建设养护集团有限公司",
  "entity_short_name": "养护",
  "entity_display_name": "养护",   // UI 展示优先字段
  "accounts": [...]
}
```

### 2. MasterEntitySelect 统一组件

`frontend/src/components/MasterEntitySelect.vue`

- 固定宽度 180px（不因长名称撑满）
- 下拉菜单最小 240px，双行显示（简称 + 全称）
- 统一 clearable、placeholder="全部单位"

### 3. useReportPrint 统一 composable

`frontend/src/composables/useReportPrint.js`

- 所有报表页通过 `const { handlePrint } = useReportPrint()` 获取
- 不再各页面独立定义 `function handlePrint() { window.print() }`

### 4. 全局打印 CSS

从 `common.css`（scoped import）移至 `theme.css`（全局）：

```css
@media print {
  .sidebar, .right-tabs, .filters-bar, .btn-row,
  .bottom-bar, .section-title, ... { display: none !important; }
  .n-layout-sider { display: none !important; }
  .n-layout { display: block !important; }
  ...
}
```

关键新增：`.n-layout-sider { display: none !important; }` 确保 Naive UI 的侧边栏也被隐藏。

### 5. 页面替换清单

| 页面 | 类型 | 变更 |
|------|------|------|
| DailyReport | 日报表 | NSelect→MasterEntitySelect, handlePrint→useReportPrint |
| AccountBalance | 日报表 | 同上 |
| IncomeList | 日报表 | 同上 |
| ExpenseList | 日报表 | 同上 |
| BaseDataTable | 日报表 | 同上 |
| CashJournal | 日报表 | useReportPrint, entity_name→entity_display_name |
| TemplateReport | 综合报表(5页面) | NSelect→MasterEntitySelect, handlePrint→useReportPrint |
| MajorBalance | via TemplateReport | 自动继承 |
| MonthCheck | via TemplateReport | 自动继承 |
| WeekReport | via TemplateReport | 自动继承 |
| MonthReport | via TemplateReport | 自动继承 |
| YearReport | via TemplateReport | 自动继承 |

## 验证结果

| 验证项 | 方法 | 结果 |
|--------|------|------|
| 后端字段扩展 | curl API | 4 个字段全部返回 |
| DailyReport 选择器 | CDP | MasterEntitySelect 宽度 180px |
| MajorBalance 选择器 | CDP | MasterEntitySelect 宽度 180px（一致） |
| handlePrint 去重 | 全仓搜索 | 仅 useReportPrint.js 定义 |
| entityOptions 去重 | 全仓搜索 | 无遗留 entityOptions = computed |
| entityFilterOptions 去重 | 全仓搜索 | 无遗留 |
| 打印 CSS 全局生效 | CDP 检查 CSSMediaRule | hasPrintMedia=true, hasSidebarHide=true, hasNLayoutSiderHide=true |
| 前端构建 | npx vite build | 通过 |

## 文件清单

### 新增
- `frontend/src/components/MasterEntitySelect.vue`
- `frontend/src/composables/useReportPrint.js`

### 修改
- `backend/db/schemas.py` — EntityTreeGroup 新增 3 个字段
- `backend/services/master_data_service.py` — 填充新字段
- `frontend/src/styles/theme.css` — 全局 @media print
- `frontend/src/views/common.css` — 移除 scoped @media print
- `frontend/src/views/DailyReport.vue` — 使用统一组件
- `frontend/src/views/AccountBalance.vue` — 使用统一组件
- `frontend/src/views/IncomeList.vue` — 使用统一组件
- `frontend/src/views/ExpenseList.vue` — 使用统一组件
- `frontend/src/views/BaseDataTable.vue` — 使用统一组件
- `frontend/src/views/CashJournal.vue` — useReportPrint + entity_display_name
- `frontend/src/composables/TemplateReport.vue` — 使用统一组件

### 未修改（向后兼容）
- `ManualFlow.vue` — 继续使用 entity_name，后端保持兼容
- `ManualMaintenance.vue` — 同上
- `AccountManage.vue` — 不涉及单位下拉
