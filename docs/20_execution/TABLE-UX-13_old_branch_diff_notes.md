# TABLE-UX-13 旧分支对比记录

> 分支：fix/table-ux-13-view-mode-copy（commit 8bb377c）
> 基于：main（旧版本，非当前 main）
> 对比基准：当前 main (e068d5e)
> 日期：2026-05-16

## 变更范围

8 个文件，35 行增 / 70 行删：

| 文件 | 变更内容 |
|------|---------|
| TemplateReport.vue | 文案修改 |
| AccountBalance.vue | 文案修改 |
| BaseDataTable.vue | 文案修改 |
| CashJournal.vue | 文案修改 + DatePicker 简化 |
| DailyReport.vue | 文案修改 |
| ExceptionCenter.vue | DatePicker 简化 |
| ExpenseList.vue | 文案修改 |
| IncomeList.vue | 文案修改 |

## 具体变更

### 文案修改（未合入）

所有使用 useDualView 的页面，视图切换提示文案从：

```
模板视图 · 当前使用 Excel 模板渲染，保留原始报表版式；高级表格交互未启用。
切换到数据视图
```

改为：

```
模板视图：保留 Excel 模板版式，适合正式打印和导出。
切换到高级表格
```

数据视图侧从：

```
数据视图 · 当前启用高级表格，可调整列宽、排序和切换密度。
切换到模板视图
```

改为：

```
高级表格视图：可调整列宽、排序、列显示和密度；正式打印导出仍以模板视图为准。
返回模板视图
```

### DatePicker 简化（已由 PR #46 在 main 完成）

- CashJournal：删除 `dateStringToTs`/`tsToDateString`/`startDateTs`/`endDateTs` computed 包装，改为 `NDatePicker v-model:value="startDate" value-format="yyyy-MM-dd"`
- ExceptionCenter：删除 `dateStringToTs`/`tsToDateString`/`businessDateTs`，改为 `NDatePicker v-model:value="form.business_date" value-format="yyyy-MM-dd"`

## 结论

旧分支的实质改动只有文案重命名和 DatePicker 修复。DatePicker 修复已在 PR #46 合入。文案修改方向与 TABLE-UX-13 新方向冲突（新方向是移除双视图，而非重命名按钮文案）。**不采用旧分支。**
