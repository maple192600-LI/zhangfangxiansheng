# UI-4A: 筛选栏布局标准化修复

> 分支: `audit/frontend-ui-4a-filter-bar-layout-fix`
> 日期: 2026-05-12
> 前置: UI-3 Naive UI 迁移完成后，遗留的内联样式导致筛选栏控件宽度不一致

## 问题

Naive UI 迁移后，9 个页面的筛选栏存在以下遗留问题：

1. **控件宽度不一致** — NDatePicker 有 `width:150px`、`width:160px`；NSelect 有 `min-width:130px`、`min-width:140px`、`min-width:160px`、`min-width:180px`、`max-width:140px`、`max-width:150px`
2. **spacer 不统一** — 使用 `style="flex:1"` 的 inline div 而非 CSS 类
3. **flex-wrap 设置不当** — 部分页面 `flex-wrap: wrap` 导致控件换行

## 修改内容

### common.css — 统一筛选栏 CSS 规则

| 类名 | 用途 | NDatePicker | NSelect |
|------|------|-------------|---------|
| `.filters-bar` | 默认单行筛选栏 | 150px | 180px |
| `.filters-bar-dense` | 高密度（控件多的页面） | 140px | 150px |
| `.filters-bar-multi` | 允许多行（备选） | 150px | 180px |

新增 `.filter-spacer` 类替代 `style="flex:1"` 的 inline spacer。

默认改为 `flex-wrap: nowrap`（单行不换行）。

### 页面级修改

| 页面 | 变更 |
|------|------|
| AccountBalance | 去 NDatePicker/NSelect inline width，加 filter-spacer |
| DailyReport | 同上 |
| ExpenseList | 同上 |
| IncomeList | 同上 |
| CashJournal | 同上 |
| OperationLog | 去 NSelect max-width、NDatePicker max-width |
| BaseDataTable | 加 `filters-bar-dense`，去 inline width，加 filter-spacer |
| AccountManage tab1 (accounts) | 加 `filters-bar-dense`，去 NSelect min-width，加 filter-spacer |
| AccountManage tab2 (divisions) | 加 filter-spacer |
| AccountManage tab3 (entities) | 去 NSelect min-width，加 filter-spacer |
| AccountManage tab4 (banks) | 加 filter-spacer |

## 验证结果

### Build

`npm run build` 通过，无错误。

### Grep 检查

| 检查项 | 结果 |
|--------|------|
| `style="flex:1"` 在 9 个文件中 | 无匹配（已清理） |
| `min-width:160px/180px`、`max-width:140px/150px`、`width:160px` 在 9 个文件中 | 无匹配（已清理） |
| 其他文件中的 `style="flex:1"` | 7 个文件（不在本轮范围，未修改） |

### CDP 验证（8 个页面）

通过 Chrome DevTools Protocol 在浏览器中实际检查：

| 页面 | flexWrap | NDatePicker | NSelect | filter-spacer | 结果 |
|------|----------|-------------|---------|---------------|------|
| AccountBalance | nowrap | 150px | 180px | 1162px flex | OK |
| DailyReport | nowrap | 150px | 180px | 1162px flex | OK |
| ExpenseList | nowrap | 150px | 180px | 1162px flex | OK |
| IncomeList | nowrap | 150px | 180px | 1162px flex | OK |
| CashJournal | nowrap | 150px | 180px | 1166px flex | OK |
| OperationLog | nowrap | 150px | 180px | 无（不需要） | OK |
| AccountManage (accounts) | nowrap | — | 150px dense | 885px flex | OK |
| BaseDataTable | nowrap | 140px dense | 150px dense | 808px flex | OK |

### AccountManage 4 个 tab 检查

| Tab | 筛选栏 | 问题 | 处理 |
|-----|--------|------|------|
| accounts | filters-bar-dense | 无 | 已修复（spacer + 去 inline width） |
| divisions | filters-bar | 无 | 已修复（spacer） |
| entities | filters-bar | 无 | 已修复（spacer + 去 inline width） |
| banks | filters-bar | 无 | 已修复（spacer） |

## 不在范围的遗留

以下 7 个文件仍有 `style="flex:1"` spacer，属于后续 UI 标准化工作：
- BankManage.vue
- ExceptionCenter.vue
- ManualFlow.vue
- ManualMaintenance.vue
- UploadPreview.vue
- composables/TemplateReport.vue
- agent/SettingsPanel.vue

## 修改文件清单

1. `frontend/src/views/common.css` — 新增筛选栏 CSS 规则
2. `frontend/src/views/AccountBalance.vue`
3. `frontend/src/views/DailyReport.vue`
4. `frontend/src/views/ExpenseList.vue`
5. `frontend/src/views/IncomeList.vue`
6. `frontend/src/views/CashJournal.vue`
7. `frontend/src/views/OperationLog.vue`
8. `frontend/src/views/BaseDataTable.vue`
9. `frontend/src/views/AccountManage.vue`（4 个 tab）
10. `docs/20_execution/UI-4A_filter_bar_layout_fix.md` — 本文档
