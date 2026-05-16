# TABLE-UX-14：ADT 单视图架构收口 + 旧双视图残留审计

> 状态：只读审计完成，待决定是否开修复 PR
> 基线 commit：8d1addd（PR #51 squash merge）
> 日期：2026-05-17

---

## 1. 当前总判断

TABLE-UX-13 的改造目标（ADT 唯一主视图）**已全部完成**：

- PR #47（规划）→ #48（默认 ADT）→ #49（移除双视图分支）→ #50（清理基础设施）→ #51（CashJournal 专项）
- 旧 `useDualView` composable 已被完全移除，代码中无任何引用
- 旧 `viewMode / isBookView / isDataView / setView` 在所有页面中均已清零
- 所有报表页面默认进入 AdvancedDataTable 主视图
- CashJournal 保留了账簿预览功能（previewOpen 模式），不视为双视图残留

**唯一的架构残留：`isInDataView` prop。**

---

## 2. PR #51 后的 TABLE-UX 状态

### 2.1 已完成的改造

| 阶段 | PR | 内容 |
|------|-----|------|
| TABLE-UX-13A | #47 | 架构规划文档 |
| TABLE-UX-13B | #48 | 默认 ADT 主视图 |
| TABLE-UX-13C | #49 | 移除双视图分支 |
| TABLE-UX-13D | #50 | 清理基础设施 |
| TABLE-UX-13E | #51 | CashJournal 专项：ADT + 账簿预览 |

### 2.2 旧双视图概念清除状态

| 旧概念 | 当前状态 |
|--------|---------|
| `useDualView` | 完全清除，0 引用 |
| `viewMode` | 完全清除，0 引用 |
| `isBookView` | 完全清除（CashJournal 保留同名 computed 但语义不同：判断是否有预览可用） |
| `isDataView` | 完全清除，0 引用 |
| `setView()` | 完全清除，0 引用 |
| `template-hint` CSS class | 完全清除 |
| `view-mode-strip` CSS class | 完全清除 |
| `template-view` CSS class | 完全清除（CashJournal 改为 `book-preview`） |
| `data-view` CSS class | 完全清除 |

---

## 3. 页面分级表

### 3.1 A 级：纯 ADT 主视图，无模板渲染（无收口需求）

| 页面文件 | 主视图 | isInDataView | viewMode残留 | templateExcelHtml | templateLayout | useTemplateColumns | ADT | 列设置 | 密度 | 偏好保存 | 打印 | 导出 | 打印误导风险 | 导出走后端 | 滚动风险 | 必须收口 | 建议动作 |
|---------|--------|-------------|-------------|------------------|----------------|-------------------|-----|-------|------|---------|------|------|------------|----------|---------|---------|---------|
| ExceptionCenter.vue | ADT | ❌不传 | ❌无 | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | — | 低 | ❌ | 无需改动 |
| OperationLog.vue | ADT | ❌不传 | ❌无 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — | 低 | ❌ | 无需改动 |

### 3.2 B 级：ADT 主视图 + 模板列配置（无渲染残留，需清理 isInDataView）

| 页面文件 | 主视图 | isInDataView | viewMode残留 | templateExcelHtml | templateLayout | useTemplateColumns | ADT | 列设置 | 密度 | 偏好保存 | 打印 | 导出 | 打印误导风险 | 导出走后端 | 滚动风险 | 必须收口 | 建议动作 |
|---------|--------|-------------|-------------|------------------|----------------|-------------------|-----|-------|------|---------|------|------|------------|----------|---------|---------|---------|
| IncomeList.vue | ADT | ✅传true | ❌无 | ❌不渲染 | ❌ | ✅(loadExcelHtml:false) | ✅ | ✅ | ✅ | ✅ | ✅页面打印 | ✅ | ❌ | ✅ | 低 | ✅ | 移除isInDataView |
| ExpenseList.vue | ADT | ✅传true | ❌无 | ❌不渲染 | ❌ | ✅(loadExcelHtml:false) | ✅ | ✅ | ✅ | ✅ | ✅页面打印 | ✅ | ❌ | ✅ | 低 | ✅ | 移除isInDataView |
| AccountBalance.vue | ADT | ✅传true | ❌无 | ❌不渲染 | ❌ | ✅(loadExcelHtml:false) | ✅ | ✅ | ✅ | ✅ | ✅页面打印 | ✅ | ❌ | ✅ | 低 | ✅ | 移除isInDataView |
| BaseDataTable.vue | ADT | ✅传true | ❌无 | ❌不渲染 | ❌ | ✅(loadExcelHtml:false) | ✅ | ✅ | ✅ | ✅ | ✅页面打印 | ✅ | ❌ | ✅ | 低 | ✅ | 移除isInDataView |
| DailyReport.vue | ADT | ✅传true | ❌无 | ❌不渲染 | ❌ | ✅(loadExcelHtml:true但不渲染) | ✅ | ✅ | ✅ | ✅ | ✅页面打印 | ✅ | ❌ | ✅ | 低 | ✅ | 移除isInDataView |

### 3.3 C 级：ADT 主视图 + 模板列配置 + 账簿预览（CashJournal 模式）

| 页面文件 | 主视图 | isInDataView | viewMode残留 | templateExcelHtml | templateLayout | useTemplateColumns | ADT | 列设置 | 密度 | 偏好保存 | 打印 | 导出 | 打印误导风险 | 导出走后端 | 滚动风险 | 必须收口 | 建议动作 |
|---------|--------|-------------|-------------|------------------|----------------|-------------------|-----|-------|------|---------|------|------|------------|----------|---------|---------|---------|
| CashJournal.vue | ADT+账簿预览 | ❌不传 | ❌无 | ✅渲染 | ✅渲染 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅(页面打印/打印账簿) | ✅ | ❌文案明确 | ✅ | 低 | ❌ | 已完成，无需改动 |

### 3.4 D 级：TemplateReport 通用壳（覆盖 5 个复合报表页）

| 页面文件 | 主视图 | isInDataView | viewMode残留 | templateExcelHtml | templateLayout | useTemplateColumns | ADT | 列设置 | 密度 | 偏好保存 | 打印 | 导出 | 打印误导风险 | 导出走后端 | 滚动风险 | 必须收口 | 建议动作 |
|---------|--------|-------------|-------------|------------------|----------------|-------------------|-----|-------|------|---------|------|------|------------|----------|---------|---------|---------|
| TemplateReport.vue | ADT | ✅传true | ❌无 | ❌不渲染 | ❌ | ✅(loadExcelHtml:false) | ✅ | ✅ | ✅ | ✅ | ✅页面打印 | ✅ | ❌ | ✅ | 低 | ✅ | 移除isInDataView |

被 TemplateReport 覆盖的页面：MajorBalance、WeekReport、MonthReport、YearReport、MonthCheck

---

## 4. 旧双视图残留清单

### 4.1 已完全清除（0 残留）

- `useDualView` composable（已删除）
- `viewMode` ref（所有页面已清除）
- `isDataView` computed（所有页面已清除）
- `setView()` 方法（所有页面已清除）
- `template-hint` / `view-mode-strip` DOM 和样式（已清除）
- CashJournal 的 `isBookView` computed 语义已变（现在是"是否有预览可用"，不是"当前是否在账簿视图"）

### 4.2 仅存残留：isInDataView prop

**位置：**
- `AdvancedDataTable.vue` prop 定义（L68）
- `AdvancedDataTable.vue` 模板 3 处条件（L13, L14, L21）
- `AdvancedDataTable.vue` watcher 1 处（L248）
- 6 个页面/组件传 `:is-in-data-view="true"`：
  - IncomeList.vue:32
  - ExpenseList.vue:32
  - AccountBalance.vue:32
  - BaseDataTable.vue:44
  - DailyReport.vue:36
  - TemplateReport.vue:46（影响 MajorBalance、WeekReport、MonthReport、YearReport、MonthCheck）

**性质：** 这是 TABLE-UX-13 之前的历史遗留。当时 ADT 既用于模板视图旁边的数据视图，也用于纯数据页面。`isInDataView` 的作用是在"模板视图"下隐藏列设置/重置按钮。

现在所有页面都是 ADT 唯一主视图，**没有任何页面会传 `false`**，这个 prop 永远为 `true`。

---

## 5. isInDataView prop 去留判断

### 5.1 当前控制什么

`isInDataView` 在 AdvancedDataTable 中控制 3 个 UI 元素的显示：

1. **"☰ 列"按钮**（L13）：`v-if="showColumnSettings && isInDataView"`
2. **"↺ 重置"按钮**（L14）：`v-if="showResetPreferences && isInDataView"`
3. **列设置面板**（L21）：`v-if="columnPanelOpen && showColumnSettings && isInDataView"`

加上 1 个 watcher（L248）：当 `isInDataView` 变为 false 时关闭列设置面板。

### 5.2 是否还有真正的双视图场景

**没有。** 所有使用 ADT 的页面（共 12 个 + WorkbenchTableLab）现在都只有一个 ADT 视图。没有任何页面会在同一时间既渲染模板视图又渲染 ADT。

### 5.3 传 `:is-in-data-view="true"` 是否只是历史残留

**是。** 6 个页面显式传 `true`，其余页面不传（default 就是 `true`）。无论传不传，结果完全一样。这是纯粹的死代码。

### 5.4 能否简化为只依赖 showColumnSettings / showResetPreferences

**可以。** 简化后：

```
原来：v-if="showColumnSettings && isInDataView"
简化：v-if="showColumnSettings"

原来：v-if="showResetPreferences && isInDataView"
简化：v-if="showResetPreferences"
```

因为 `showColumnSettings` 默认 `false`，页面需要显式传 `show-column-settings` 才会显示列设置。已经足够控制显示/隐藏。

### 5.5 移除 isInDataView 影响哪些页面

**影响列表（全部无害）：**

| 页面 | 改动 |
|------|------|
| IncomeList.vue | 删除 `:is-in-data-view="true"` |
| ExpenseList.vue | 删除 `:is-in-data-view="true"` |
| AccountBalance.vue | 删除 `:is-in-data-view="true"` |
| BaseDataTable.vue | 删除 `:is-in-data-view="true"` |
| DailyReport.vue | 删除 `:is-in-data-view="true"` |
| TemplateReport.vue | 删除 `:is-in-data-view="true"`（影响 5 个子页面） |
| AdvancedDataTable.vue | 删除 prop 定义、3 处条件中的 `&& isInDataView`、1 处 watcher |
| CashJournal.vue | 无需改动（已经不传） |
| ExceptionCenter.vue | 无需改动（已经不传） |
| OperationLog.vue | 无需改动（已经不传） |

### 5.6 最小安全改法

```
PR 范围（TABLE-UX-14A）：
1. AdvancedDataTable.vue：
   - 删除 isInDataView prop 定义
   - 模板中 3 处 `&& isInDataView` → 直接用 showColumnSettings / showResetPreferences
   - 删除 watcher（L248-250）
2. 6 个页面/组件：
   - 删除 `:is-in-data-view="true"` 属性
3. 不改任何其他逻辑
```

### 5.7 结论

**建议移除。** 无任何功能影响，纯清理，改动量极小（约 12 行删除，0 行新增）。

---

## 6. CashJournal 模式是否可复用的判断

### 6.1 各页面是否需要"账簿预览"按钮

| 页面 | 是否需要 | 理由 |
|------|---------|------|
| IncomeList | **否** | 收入明细是流水列表，不是正式账簿，无合并单元格/分块/小计需求 |
| ExpenseList | **否** | 同 IncomeList |
| AccountBalance | **否** | 汇总表，数据行少，ADT 已足够展示，无版式需求 |
| BaseDataTable | **否** | 原始数据底表，不是报表，用户不需要账簿版式 |
| ExceptionCenter | **否** | 运维页面，处理异常流水，不是报表概念 |
| DailyReport | **否** | 日报是汇总表，行数少，ADT 已够。如果未来需要正式打印版式，可另加预览，但当前无需求 |
| MajorBalance | **否** | 同 AccountBalance |
| WeekReport / MonthReport / YearReport / MonthCheck | **否** | 周期报表，汇总数据，ADT 已足够 |

### 6.2 为什么不能机械复制

CashJournal 是**正式账簿**类页面，具有：
- 合并单元格标题行
- 按账户分块的数据行
- 小计行
- 完整的 Excel 版式渲染

其他页面都是**流水明细或汇总表**，数据结构简单（行列表），没有账簿版式需求。给这些页面加"账簿预览"是过度设计。

### 6.3 结论

CashJournal 模式不应复制到其他页面。当前各页面只需做 `isInDataView` 清理即可。

---

## 7. 各页面下一步动作建议

| 页面 | 动作 | 优先级 |
|------|------|--------|
| CashJournal.vue | 已完成，无需改动 | — |
| IncomeList.vue | 移除 `:is-in-data-view="true"` | P1 |
| ExpenseList.vue | 移除 `:is-in-data-view="true"` | P1 |
| AccountBalance.vue | 移除 `:is-in-data-view="true"` | P1 |
| BaseDataTable.vue | 移除 `:is-in-data-view="true"` | P1 |
| DailyReport.vue | 移除 `:is-in-data-view="true"` | P1 |
| TemplateReport.vue | 移除 `:is-in-data-view="true"`（覆盖 5 个子页面） | P1 |
| AdvancedDataTable.vue | 移除 isInDataView prop + 条件 + watcher | P1 |
| ExceptionCenter.vue | 无需改动 | — |
| OperationLog.vue | 无需改动 | — |

---

## 8. 风险点

### 8.1 低风险（isInDataView 清理）

移除 `isInDataView` 对所有页面功能无影响。因为：
- 所有页面要么传 `true`（6 个），要么不传（default `true`）
- 删除后行为完全一致：列设置/重置按钮的显示继续由 `showColumnSettings` / `showResetPreferences` 控制

### 8.2 无滚动风险

所有 ADT 页面使用 `.table-workspace-page` + `.table-workspace-main` 的 flex 布局：
- `common.css:520-544`：flex column + `overflow: hidden` + `min-height: 0`
- ADT `fill-parent` 模式：`height: 100%` + `flex: 1`
- Tabulator 自带虚拟滚动

无双滚动条风险、无 body 级滚动风险。

### 8.3 打印风险（信息级，不需要本轮修复）

所有 ADT 页面的打印走 `window.print()`，打印的是当前可见 DOM（高级表格），不是正式账簿版式。对大多数页面这是可接受的（明细表/汇总表没有版式要求）。

CashJournal 已通过"页面打印/打印账簿"双文案明确区分。

### 8.4 导出风险（无）

所有页面导出走后端 `exportReport` API，与前端渲染完全解耦。

### 8.5 DailyReport 的 templateExcelHtml（信息级）

DailyReport 调用 `useTemplateColumns('daily_report')` 时 `loadExcelHtml` 为默认 `true`，但实际上不渲染 HTML（因为模板视图片段已移除）。这个 `templateExcelHtml` ref 被加载了但从未使用。不造成功能问题，但浪费了一次 HTTP 请求。可考虑后续改为 `{ loadExcelHtml: false }`。

---

## 9. 建议拆分的后续 PR

### TABLE-UX-14A：移除 isInDataView prop（建议执行）

**范围：**
1. `AdvancedDataTable.vue`：删除 prop、条件、watcher
2. `IncomeList.vue`：删除 `:is-in-data-view="true"`
3. `ExpenseList.vue`：删除 `:is-in-data-view="true"`
4. `AccountBalance.vue`：删除 `:is-in-data-view="true"`
5. `BaseDataTable.vue`：删除 `:is-in-data-view="true"`
6. `DailyReport.vue`：删除 `:is-in-data-view="true"`
7. `TemplateReport.vue`：删除 `:is-in-data-view="true"`

**改动量：** ~12 行删除，0 行新增

**风险：** 无（功能完全不变）

**验收：** `npm run build` 通过 + 所有 7 个页面浏览器确认列设置/重置按钮仍正常显示

### 可选：DailyReport loadExcelHtml 优化（低优先级）

DailyReport 的 `useTemplateColumns('daily_report')` 可改为 `{ loadExcelHtml: false }`，节省一次无用 HTTP 请求。可与 14A 合并。

---

## 10. 验收标准

### TABLE-UX-14A 合并前必须满足：

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | `npm run build` 通过 | 命令行 |
| 2 | AdvancedDataTable 中 `isInDataView` 完全消失 | grep 确认 |
| 3 | 所有页面中 `is-in-data-view` 完全消失 | grep 确认 |
| 4 | IncomeList/ExpenseList/AccountBalance/BaseDataTable/DailyReport 列设置按钮正常 | 浏览器逐一验证 |
| 5 | TemplateReport（5 个子页面）列设置按钮正常 | 浏览器验证 MajorBalance、WeekReport |
| 6 | 控制台 0 error / 0 warning | 浏览器 DevTools |
| 7 | CashJournal 不受影响 | 浏览器确认账簿预览仍正常 |

### 全量回归验收（14A 合并后）：

| # | 页面 | 确认项 |
|---|------|--------|
| 1 | CashJournal | ADT 主视图 + 账簿预览 + 打印切换 + 导出 |
| 2 | IncomeList | ADT + 列设置 + 导出 |
| 3 | ExpenseList | ADT + 列设置 + 导出 |
| 4 | AccountBalance | ADT + 列设置 + 合计行 + 导出 |
| 5 | BaseDataTable | ADT + 列设置 + 分页 + 批量选择 + 导出 |
| 6 | DailyReport | ADT + 列设置 + 合计行 + 导出 |
| 7 | MajorBalance | ADT + 列设置 + 导出 |
| 8 | WeekReport | ADT + 列设置 + 导出 |
| 9 | MonthReport | ADT + 列设置 + 导出 |
| 10 | YearReport | ADT + 列设置 + 导出 |
| 11 | MonthCheck | ADT + 列设置 + 导出 |
| 12 | ExceptionCenter | ADT + 行内操作 + 分页 |
| 13 | OperationLog | ADT + 分页 |

---

## 审计覆盖文件清单

### 核心组件（6 个）
- `frontend/src/components/workbench/AdvancedDataTable.vue`
- `frontend/src/composables/useTabulatorTable.js`
- `frontend/src/composables/useColumnAdapter.js`
- `frontend/src/composables/useAdvancedTablePreferences.js`
- `frontend/src/composables/useTemplateColumns.js`
- `frontend/src/views/common.css`

### 已完成/核心页面（7 个）
- `frontend/src/views/CashJournal.vue`
- `frontend/src/views/IncomeList.vue`
- `frontend/src/views/ExpenseList.vue`
- `frontend/src/views/AccountBalance.vue`
- `frontend/src/views/BaseDataTable.vue`
- `frontend/src/views/DailyReport.vue`
- `frontend/src/views/ExceptionCenter.vue`

### 复合报表页面（6 个）
- `frontend/src/views/MajorBalance.vue`
- `frontend/src/views/WeekReport.vue`
- `frontend/src/views/MonthReport.vue`
- `frontend/src/views/YearReport.vue`
- `frontend/src/views/MonthCheck.vue`
- `frontend/src/composables/TemplateReport.vue`

### 辅助页面（1 个）
- `frontend/src/views/OperationLog.vue`

### 参考文档（3 个）
- `docs/20_execution/TABLE-UX-13_single_advanced_table_architecture.md`
- `docs/20_execution/TABLE-UX-10_cash_journal_special_audit.md`
- `docs/20_execution/TABLE-UX-8_composite_reports_migration_audit.md`

**总计：23 个文件**
