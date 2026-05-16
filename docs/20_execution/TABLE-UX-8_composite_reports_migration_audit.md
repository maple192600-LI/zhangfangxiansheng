# TABLE-UX-8 综合报表批量迁移前审计

> 审计日期：2026-05-16
> 审计分支：main（commit 4be21c3）
> 审计人：Agent（只读审计，未修改任何业务代码）

---

## 1. 审计结论

### 核心发现

**5个目标页面全部是 `TemplateReport.vue` 的薄包装**，各页面代码量仅 10-15 行。真正的审计对象不是 5 个独立页面，而是 `frontend/src/composables/TemplateReport.vue` 这一个组件。

### 结论

| 项目 | 结论 |
|------|------|
| 是否建议批量迁移 | **是** — 因为实际只迁移一个组件（TemplateReport.vue），5个页面自然一起迁移 |
| 是否建议先抽公共组件 | **不需要单独抽** — 已有 AccountBalance/DailyReport 等已迁移页面作为模式参考，直接将 TemplateReport.vue 改造为高级表格体系即可 |
| 哪些页面可以同批迁移 | **全部5个** — 改造 TemplateReport.vue 后，5个薄包装页自动完成 |
| 是否存在阻塞问题 | **是，有一个** — `defaultHeaders`/`defaultKeys` 属性在 TemplateReport.vue 中声明但从未使用，导致无模板时显示"未配置报表模板"而不是 fallback 到默认列。违反 CLAUDE.md"增强层不阻断核心功能"原则。迁移时必须修复 |

### 迁移实质

不是"5个页面逐一迁移"，而是"改造1个通用组件 + 验证5种配置"。工作量远小于预期。

---

## 2. 当前高级表格底座状态

从代码确认的能力清单：

| 能力 | 文件 | 状态 |
|------|------|------|
| AdvancedDataTable | `components/workbench/AdvancedDataTable.vue` | 已就绪。支持 fill-parent、density、toolbar、column-settings、row-class、pagination |
| useTabulatorTable | `composables/useTabulatorTable.js` | 已就绪。Tabulator 封装，支持 replaceData、setColumns、事件回调 |
| useDualView | `composables/useDualView.js` | 已就绪。自动检测 templateExcelHtml，有模板时默认 template 视图 |
| useColumnAdapter | `composables/useColumnAdapter.js` | 已就绪。field_key/header_name → field/title 转换，支持 moneyFields/directionField |
| useAdvancedTablePreferences | `composables/useAdvancedTablePreferences.js` | 已就绪。localStorage 持久化 width/visibility/order/density |
| useTemplateColumns | `composables/useTemplateColumns.js` | 已就绪。加载 templateExcelHtml + templateColumns，支持 onMounted/onActivated |
| tabulatorFormatters | `utils/tabulatorFormatters.js` | 已就绪。emptyDash、money、direction、abnormalCode、exceptionState 等 |
| table-workspace-page 布局 | `views/common.css` | 已就绪。flex 布局 + overflow:hidden，保证表格高度正确 |
| template-view / data-view | `views/common.css` | 已就绪。模板视图和数据视图的布局约束 |
| 打印排除 | common.css + tabulator-theme.css | 已就绪。`.adt-no-print` 类排除工具条打印 |

### 已迁移页面的模式总结

DailyReport、AccountBalance、IncomeList、ExpenseList 已迁移，共享以下模式：

1. **根容器**：`<div class="section report-print-root table-workspace-page">`
2. **双视图**：`useDualView(templateExcelHtml)` 自动切换模板/数据视图
3. **列定义**：`DEFAULT_COLUMNS` 作为 fallback + `adaptTemplateColumns()` 合并模板列
4. **偏好系统**：`preferencesVersion` + `appliedColumns` + hiddenFields 完整集成
5. **数据加载**：各页面独立 API 调用，结果直接给 AdvancedDataTable
6. **rowClassFn**：通过 `is_total` / `is_subtotal` 标记特殊行样式

---

## 3. 五个页面逐页审计表

### 3.1 关键前提

5个页面文件内容极少，均为 `TemplateReport` 组件的 props 传参。以下审计主要针对 `TemplateReport.vue` 的实际行为。

### 3.2 TemplateReport.vue 当前状态

| # | 审计项 | 结果 |
|---|--------|------|
| 1 | 页面名 | TemplateReport（通用报表组件） |
| 2 | 文件路径 | `frontend/src/composables/TemplateReport.vue` |
| 3 | 当前根容器结构 | `div.report-print-root-wrapper > div.section.report-print-root` |
| 4 | 是否使用 report-print-root | **是** — `class="section report-print-root"` |
| 5 | 是否使用 table-workspace-page | **否** — 缺失，会导致高度溢出 |
| 6 | 是否使用 useTemplateColumns | **是** — 但只用了 `templateColumns`，没有用 `templateExcelHtml` |
| 7 | reportType / export_type | 由各页面 props 传入，5个分别为：`major_balance`、`month_check`、`week_report`、`month_report`、`year_report` |
| 8 | 当前是否 templateExcelHtml 优先 | **否** — 虽然调用了 `useTemplateColumns`，返回值包含 `templateExcelHtml`，但组件内未使用该变量 |
| 9 | 当前是否还有原生 table | **是** — 使用原生 `<table>` + `v-for` 渲染 |
| 10 | 当前是否已使用 AdvancedDataTable | **否** |
| 11 | DEFAULT_COLUMNS 或列定义来源 | `templateColumns`（从后端 `/report-templates/default/{type}` 获取）。有 `defaultHeaders`/`defaultKeys` props 但 **从未在渲染中使用** |
| 12 | 字段结构 | `field_key` / `header_name`（模板列格式） |
| 13 | 是否有合计行、小计行、分组行 | **有小计行** — 通过 `r.is_subtotal` 标记，MajorBalance 和 MonthCheck 后端返回此字段 |
| 14 | 是否有复杂多级表头或合并单元格 | **否** — 简单单行表头 |
| 15 | 是否有后端分页 | **否** — 数据量小（按单位/账户聚合） |
| 16 | 是否有前端分页 | **否** |
| 17 | 是否有生成报表按钮 | **是** |
| 18 | 是否有导出 | **是** — 调用 `exportReport()` |
| 19 | 是否有打印 | **是** — 调用 `useReportPrint()`（即 `window.print()`） |
| 20 | 筛选条件 | 三种日期模式（range/month/year）+ 单位筛选（MasterEntitySelect） |
| 21 | API 调用函数 | `reportApi.getReport(reportType, params)` — 统一入口，内部分发到不同后端路由 |
| 22 | 返回数据结构 | 见下方详细分析 |
| 23 | 是否适合复用 DailyReport 模式 | **是** — 结构高度相似 |
| 24 | 是否适合抽公共 shell | **已经是一个公共组件**，改造它即可 |
| 25 | 迁移难度 | **中** — 单个组件改造，但有 fallback 逻辑需补全 |
| 26 | 迁移风险点 | (1) defaultHeaders/defaultKeys 未使用导致无模板时空白 (2) 缺少 table-workspace-page (3) subtotal 行需 rowClass 支持 |
| 27 | 建议迁移顺序 | 改造 TemplateReport.vue 一次，5个页面同时完成 |
| 28 | 不应该迁移或延后的原因 | 无，全部适合本轮迁移 |

### 3.3 各页面配置差异

| 页面 | reportType | exportType | dateMode | defaultHeaders | defaultKeys | 后端函数 | 返回字段 |
|------|-----------|-----------|----------|---------------|-------------|---------|---------|
| MajorBalance | `major_balance` | `major_balance` | `range` | 单位简称/账户名称/期初余额/本期收入/本期支出/期末余额 | entity_name/account_name/opening_balance/period_income/period_expense/ending_balance | `major_balance()` | entity_name, account_name, opening_balance, period_income, period_expense, ending_balance, **is_subtotal** |
| MonthCheck | `month_check` | `month_check` | `month` | 同 MajorBalance | 同 MajorBalance | `account_balance()`（间接） | 同 MajorBalance + **is_subtotal** |
| WeekReport | `week_report` | `week_report` | `range` | 未传 | 未传 | `daily_report()`（间接） | entity_name, opening_balance, total_income, total_expense, net_change, ending_balance |
| MonthReport | `month_report` | `month_report` | `month` | 未传 | 未传 | `daily_report()`（间接） | 同 WeekReport |
| YearReport | `year_report` | `year_report` | `year` | 未传 | 未传 | `daily_report()`（间接） | 同 WeekReport |

### 3.4 两组数据结构

**A 组（MajorBalance、MonthCheck）— 账户级别明细 + 小计行**

```json
{
  "entity_id": 1,
  "entity_name": "XX公司",
  "account_id": 5,
  "account_name": "6228... 工行",
  "opening_balance": 100000.00,
  "period_income": 50000.00,
  "period_expense": 30000.00,
  "ending_balance": 120000.00,
  "is_subtotal": false
}
// 每个实体最后一行:
{
  "entity_name": "XX公司 小计",
  "opening_balance": ...,
  "is_subtotal": true
}
```

**B 组（WeekReport、MonthReport、YearReport）— 实体级别汇总，无小计行**

```json
{
  "entity_id": 1,
  "entity_name": "XX公司",
  "opening_balance": 100000.00,
  "total_income": 50000.00,
  "total_expense": 30000.00,
  "net_change": 20000.00,
  "ending_balance": 120000.00
}
```

---

## 4. 页面相似性分析

### 4.1 高度相似

5个页面 **100% 结构一致**，因为它们用的是同一个 `TemplateReport.vue` 组件，只通过 props 区分。

### 4.2 共享项

| 维度 | 是否共享 | 说明 |
|------|---------|------|
| 筛选结构 | **是** | 三种日期模式（range/month/year）+ 实体选择器 |
| 模板加载结构 | **是** | 统一 `useTemplateColumns(reportType)` |
| 导出打印结构 | **是** | 统一 `exportReport()` + `window.print()` |
| 数据结构 | **两组** | A组有 account_name + is_subtotal；B组有 total_income/total_expense/net_change |
| 布局问题 | **是，全部相同** | 缺少 `table-workspace-page`，缺少 fallback 默认列 |

### 4.3 差异项

| 差异 | 影响范围 | 迁移处理 |
|------|---------|---------|
| dateMode 不同 | 筛选栏渲染 | props 已区分，无需额外处理 |
| A组有 is_subtotal 行 | 数据渲染 | 需 rowClassFn 支持 `subtotal-row` 样式 |
| A组有 account_name 列 | 列定义 | DEFAULT_COLUMNS 不同，通过 props/defaultColumns 配置 |
| B组有 net_change 列 | 列定义 | 同上 |
| WeekReport 无 defaultHeaders | fallback 列缺失 | 需要在组件内部提供默认 DEFAULT_COLUMNS |

---

## 5. 抽象设计建议

### 5.1 结论：不需要额外抽象

已有 `TemplateReport.vue` 作为统一容器。改造这个组件即可，无需新建 TemplateReportShell / useTemplateReportViewMode / useTemplateReportTable。

原因：
1. 5个页面已经是同一个组件，不需要再抽一层
2. 已有 `useDualView`、`useColumnAdapter`、`useAdvancedTablePreferences` 满足需求
3. 再加抽象层反而增加理解成本

### 5.2 TemplateReport.vue 改造方案

改造目标：将 `TemplateReport.vue` 从"原生 table 渲染"升级为"高级表格双视图体系"。

#### 改造点清单

**1. 根容器修复**

```html
<!-- 现在 -->
<div class="report-print-root-wrapper">
  <div class="section report-print-root">

<!-- 改为 -->
<div class="section report-print-root table-workspace-page">
```

去掉多余的 wrapper，加上 `table-workspace-page` 保证 flex 布局高度正确。

**2. 新增双视图支持**

```html
<!-- 模板视图 -->
<div v-if="isTemplateView" class="table-workspace-main template-view">
  <div class="template-hint adt-no-print">...</div>
  <div class="excel-host" v-html="templateExcelHtml"></div>
</div>

<!-- 数据视图 -->
<div v-else class="table-workspace-main data-view">
  <div v-if="hasTemplate" class="view-mode-strip adt-no-print">...</div>
  <AdvancedDataTable ... />
</div>
```

需要引入 `useDualView(templateExcelHtml)`，当前组件调用 `useTemplateColumns` 时已返回 `templateExcelHtml` 但未使用。

**3. 修复 fallback 默认列**

当前问题：`defaultHeaders`/`defaultKeys` props 声明了但未使用。无模板时显示"未配置报表模板"，阻断核心功能。

方案：
- 用 `defaultHeaders` + `defaultKeys` 构建 DEFAULT_COLUMNS
- 当 `templateColumns` 为空时使用 DEFAULT_COLUMNS
- 同时用 `adaptTemplateColumns()` 合并模板列和默认列

```javascript
const DEFAULT_COLUMNS = computed(() => {
  if (!props.defaultHeaders.length) return []
  return props.defaultHeaders.map((header, i) => ({
    field: props.defaultKeys[i],
    title: header,
    formatter: emptyDashFormatter,
  }))
})
```

**4. 前端合计行**

B 组（WeekReport/MonthReport/YearReport）数据结构与 DailyReport 完全相同，照搬 DailyReport 的前端合计行逻辑：

```javascript
const dataRows = computed(() => {
  const base = rows.value
  if (base.length <= 1) return base
  return [...base, { entity_name: '合计', ...totals, is_total: true }]
})
```

A 组（MajorBalance/MonthCheck）后端已返回 `is_subtotal` 行，不需要前端再加合计。

**5. rowClassFn**

```javascript
function rowClassFn(row) {
  if (row.is_total) return 'total-row'
  if (row.is_subtotal) return 'subtotal-row'
  return ''
}
```

**6. 偏好系统集成**

照搬 DailyReport/AccountBalance 模式：
- `preferencesVersion` + `touchPreferences()`
- `appliedColumns` = `applyPreferences(tabulatorColumns, getPreferences(TABLE_KEY))`
- `hiddenFields` 计算
- 6 个回调：densityChange、columnWidthChange、columnOrderChange、columnVisibilityChange、preferencesReset

TABLE_KEY 可用 `reportType` prop 直接作为 key（已是唯一标识）。

**7. MONEY_FIELDS 配置**

A 组和 B 组的金额字段不同，需要通过 props 传入或内部自动检测：

| 组 | 金额字段 |
|----|---------|
| A（MajorBalance、MonthCheck） | opening_balance, period_income, period_expense, ending_balance |
| B（WeekReport、MonthReport、YearReport） | opening_balance, total_income, total_expense, net_change, ending_balance |

方案：新增 `moneyKeys` prop，各页面传入对应的金额字段列表。TemplateReport 内部据此构建 `moneyFields` Set 给 `adaptTemplateColumns` 用。

**8. 空模板 fallback 显示**

当 `templateLoaded` 为 true 但 `templateColumns` 为空且没有 `templateExcelHtml` 时：
- 现在：显示"未配置报表模板"（阻断）
- 改为：用 DEFAULT_COLUMNS 渲染 AdvancedDataTable（降级）

只在 DEFAULT_COLUMNS 也为空时才显示"暂无数据，请生成报表"。

### 5.3 不需要新增的文件

以下文件 **不需要创建**：

- ~~`TemplateReportShell.vue`~~ — 已有 TemplateReport.vue，改造即可
- ~~`useTemplateReportViewMode.js`~~ — 已有 `useDualView`
- ~~`useTemplateReportTable.js`~~ — 已有 `useTabulatorTable`（被 AdvancedDataTable 内部使用）

### 5.4 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/composables/TemplateReport.vue` | 全面改造：引入 AdvancedDataTable + useDualView + useColumnAdapter + useAdvancedTablePreferences |
| `frontend/src/views/MajorBalance.vue` | 可能新增 `moneyKeys` prop（如果采用该方案） |
| `frontend/src/views/MonthCheck.vue` | 同上 |
| `frontend/src/views/WeekReport.vue` | 可能新增 `moneyKeys` + `defaultHeaders`/`defaultKeys` props |
| `frontend/src/views/MonthReport.vue` | 同上 |
| `frontend/src/views/YearReport.vue` | 同上 |

---

## 6. 推荐迁移顺序

由于 5 个页面实际是同一个组件，迁移顺序的意义在于**验证顺序**。

### 推荐顺序

| 顺序 | 页面 | 原因 |
|------|------|------|
| 1 | **WeekReport** | B 组最简结构，无 is_subtotal，与 DailyReport 完全同构，可最快验证基础改造是否正确 |
| 2 | **MonthReport** | B 组 + month 日期模式，验证 month 选择器 + 参数传递 |
| 3 | **YearReport** | B 组 + year 日期模式，验证 year 选择器 |
| 4 | **MajorBalance** | A 组，验证 is_subtotal 行 + account_name 列 + 前端合计行是否正确 |
| 5 | **MonthCheck** | A 组 + month 日期模式，验证 A+B 组合 |

实际上改造 TemplateReport.vue 后，只需按顺序验证每个页面的筛选参数和数据展示是否正确。

---

## 7. 每页迁移风险

### 7.1 TemplateReport.vue 整体改造风险

| 风险等级 | 风险点 | 应对方案 |
|---------|--------|---------|
| **高** | defaultHeaders/defaultKeys 未使用，无模板时空白 | 改造时必须实现 DEFAULT_COLUMNS fallback，确保无模板时也能显示数据 |
| **高** | 缺少 `table-workspace-page` 导致高度溢出 | 改造时加上 class，去掉多余 wrapper |
| **中** | 双视图切换引入 templateExcelHtml 后，可能导致未上传 Excel 模板的页面行为变化 | 已有 `useDualView` 逻辑：无 templateExcelHtml 时自动回退到 data 视图 |
| **中** | is_subtotal 行在 Tabulator 中的样式可能不生效 | 已有 rowClassFn 模式（AccountBalance 已用），确认 `.subtotal-row` 样式存在 |
| **低** | MONEY_KEYS 硬编码在 TemplateReport 中，不覆盖 B 组字段 | 改为 props 传入或按 reportType 动态构建 |

### 7.2 各页面特有风险

| 页面 | 风险等级 | 风险点 | 应对方案 |
|------|---------|--------|---------|
| WeekReport | 低 | 未传 defaultHeaders/defaultKeys，需组件内提供默认 | 在 TemplateReport 中硬编码 B 组默认列，或 WeekReport 补传 props |
| MonthReport | 低 | 同 WeekReport | 同上 |
| YearReport | 低 | 同 WeekReport | 同上 |
| MajorBalance | 中 | 导出时 is_subtotal 行被后端过滤（`if not r.get("is_subtotal")`），前端显示有但导出没有 | 这是现有行为，迁移后保持一致即可 |
| MonthCheck | 低 | 数据源实际调用 `account_balance()`，结构与 MajorBalance 相同 | 已确认，无特殊处理 |

### 7.3 特别检查项

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 模板 HTML 和数据 table 混在一个滚动容器 | **否** — 当前 TemplateReport 不使用 templateExcelHtml |
| 外层没有 table-workspace-page 导致高度不对 | **是** — 当前缺少，迁移必须修复 |
| v-html 显示模板后完全挡住数据视图 | **否** — 引入 useDualView 后模板和数据互斥显示 |
| 字段名和模板列字段名不一致 | **可能** — 需验证后端返回的 field_key 与实际数据 key 是否匹配。后端数据用的是 `period_income`/`period_expense`，导出配置也是这些字段名 |
| export_type 与 reportType 不一致 | **否** — 5个页面 exportType === reportType |
| 生成报表后没有 rows 但模板仍显示旧数据 | **当前无此问题** — TemplateReport 不使用 templateExcelHtml |
| 打印区域会把高级表格工具条打印进去 | **已解决** — `.adt-no-print` 类已存在，toolbar 和提示条都有此类 |
| 照抄 DailyReport 会破坏正式模板 | **否** — DailyReport 和 AccountBalance 已验证过双视图模式 |

---

## 8. TABLE-UX-9 实施计划草案

### 目标

将 `TemplateReport.vue` 从原生 table 升级为高级表格体系，使 MajorBalance、MonthCheck、WeekReport、MonthReport、YearReport 5个综合报表页面同时获得：AdvancedDataTable 数据视图、模板视图双视图切换、列偏好持久化、合计/小计行样式。

### 背景

TABLE-UX-7 已完成 DailyReport 和 ExceptionCenter 迁移。TABLE-UX-8 审计确认 5 个综合报表页面全部由 `TemplateReport.vue` 一个组件承载，改造该组件即可完成全部迁移。

### 必须读取文件

- `frontend/src/composables/TemplateReport.vue` — 本次改造的主文件
- `frontend/src/views/DailyReport.vue` — B 组迁移参考
- `frontend/src/views/AccountBalance.vue` — A 组迁移参考（有 is_subtotal）
- `frontend/src/views/common.css` — 布局样式
- `frontend/src/composables/useDualView.js` — 双视图逻辑
- `frontend/src/composables/useColumnAdapter.js` — 列转换
- `frontend/src/composables/useAdvancedTablePreferences.js` — 偏好系统
- `frontend/src/components/workbench/AdvancedDataTable.vue` — 表格组件
- `frontend/src/utils/tabulatorFormatters.js` — 格式化器
- `frontend/src/api/report.js` — API 调用
- `backend/services/report_service.py` — 后端数据结构确认

### 允许修改范围

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/composables/TemplateReport.vue` | 全面改造：模板结构、script 逻辑、style |
| `frontend/src/views/MajorBalance.vue` | 可能补传 moneyKeys/defaultHeaders props |
| `frontend/src/views/MonthCheck.vue` | 同上 |
| `frontend/src/views/WeekReport.vue` | 补传 defaultHeaders/defaultKeys/moneyKeys props |
| `frontend/src/views/MonthReport.vue` | 同上 |
| `frontend/src/views/YearReport.vue` | 同上 |

### 禁止修改范围

- 后端 API 路由和 service 层
- AdvancedDataTable.vue 组件本身
- useTabulatorTable / useDualView / useColumnAdapter / useAdvancedTablePreferences composable
- tabulatorFormatters.js
- common.css 布局样式
- 导出/打印逻辑

### 实施步骤

#### Step 1：改造 TemplateReport.vue 模板结构

1. 去掉 `report-print-root-wrapper`，根容器改为 `div.section.report-print-root.table-workspace-page`
2. 添加双视图区域：
   - `template-view`：template-hint + excel-host（v-html）
   - `data-view`：view-mode-strip + AdvancedDataTable
3. 保留 loading / empty-state 逻辑
4. 确保 adt-no-print 覆盖所有工具条和提示条

**验证**：浏览器打开 WeekReport，确认 flex 布局高度正确、工具条不打印

#### Step 2：改造 TemplateReport.vue script

1. 引入 `useDualView(templateExcelHtml)`（需解构 `useTemplateColumns` 返回的 `templateExcelHtml`）
2. 用 `defaultHeaders`/`defaultKeys` props 构建 DEFAULT_COLUMNS computed
3. 用 `adaptTemplateColumns()` 合并模板列和默认列
4. 引入偏好系统完整集成（preferencesVersion、appliedColumns、hiddenFields、6个回调）
5. rowClassFn：支持 `is_total` + `is_subtotal`
6. 前端合计行：仅 B 组（根据 `moneyKeys` prop 或 reportType 判断）
7. 保留现有的 loadData / doExport / handlePrint 逻辑

**验证**：浏览器打开 WeekReport + MajorBalance，确认数据展示正确

#### Step 3：补全 5 个薄包装页面的 props

1. WeekReport、MonthReport、YearReport：补传 `defaultHeaders`/`defaultKeys`/`moneyKeys`
2. MajorBalance、MonthCheck：确认 props 足够（当前已有 defaultHeaders/defaultKeys，补 moneyKeys）

**验证**：5 个页面逐一打开，确认筛选、生成、展示、导出、打印

#### Step 4：端到端验证

按第 6 节推荐顺序，对每个页面验证：
1. 无模板时是否显示 DEFAULT_COLUMNS 数据视图
2. 有模板时双视图切换是否正常
3. 生成报表后数据是否正确
4. 导出是否正常
5. 打印是否排除工具条
6. is_subtotal 行样式是否正确（MajorBalance、MonthCheck）
7. 列偏好持久化是否正常
8. 三种日期模式筛选是否正确

### 风险点

1. **无模板时空白**：必须在 Step 2 中彻底解决 DEFAULT_COLUMNS fallback
2. **合计行重复**：A 组后端已返回 subtotal，前端不应再加；B 组需要前端加。必须按 reportType 区分
3. **日期参数格式**：MonthCheck/MonthReport 用 year+month，YearReport 用 year，MajorBalance/WeekReport 用 start_date+end_date。TemplateReport 现有逻辑已处理，改造时保持不变

### 测试方式

- 前端开发服务器启动后，浏览器逐一操作
- 无模板场景：可临时用 `?debug_no_template=1` 或删除模板测试
- 有模板场景：上传对应类型模板后测试双视图切换
- 打印测试：Ctrl+P 预览确认工具条不出现

### 验收标准

1. 5 个页面均使用 AdvancedDataTable 展示数据
2. 无模板时降级到 DEFAULT_COLUMNS（不显示"未配置报表模板"）
3. 有 Excel 模板时支持双视图切换
4. 列宽、列序、列可见性、密度偏好持久化
5. is_subtotal 行有特殊样式
6. 打印不包含工具条
7. 导出功能正常
8. git diff 只涉及 TemplateReport.vue + 5 个薄包装页面，无其他文件变更

### 回滚方案

- 改造前先 commit 当前状态
- 如发现问题，`git revert` 即可恢复
- 改造范围仅限前端 6 个文件，无后端变更，风险可控

---

## 9. 是否建议进入开发

### 明确结论：**建议进入 TABLE-UX-9**

理由：
1. 审计发现实际只需改造 1 个组件（TemplateReport.vue），不是 5 个独立页面，工作量小
2. 已有 DailyReport + AccountBalance 两个成熟参考实现
3. 所有高级表格底座能力已就绪，无需补底座
4. 5 个页面数据结构清晰，分为两组（A+B），差异可控
5. 唯一的阻塞问题（无模板时空白）在迁移过程中自然修复
6. 不涉及后端改动，风险范围可控

### 下一步最小可执行任务

1. 创建 feature 分支 `feat/table-ux-9-composite-reports`
2. 按 Step 1-4 实施 TemplateReport.vue 改造
3. 按验证顺序逐页验证
4. 提交 PR

---

## 附录：已读取文件清单

### 基础能力层（9个）

| 文件 | 行数 |
|------|------|
| `frontend/src/components/workbench/AdvancedDataTable.vue` | 505 |
| `frontend/src/composables/useTabulatorTable.js` | 168 |
| `frontend/src/composables/useDualView.js` | 40 |
| `frontend/src/composables/useColumnAdapter.js` | 38 |
| `frontend/src/composables/useAdvancedTablePreferences.js` | 132 |
| `frontend/src/composables/useTemplateColumns.js` | 81 |
| `frontend/src/composables/useReportPrint.js` | 8 |
| `frontend/src/utils/tabulatorFormatters.js` | 81 |
| `frontend/src/views/common.css` | 669 |

### 已迁移参考页（3个）

| 文件 | 行数 |
|------|------|
| `frontend/src/views/DailyReport.vue` | 254 |
| `frontend/src/views/AccountBalance.vue` | 210 |
| `frontend/src/views/ExceptionCenter.vue` | 383 |

### 审计目标页 + 核心组件（6个）

| 文件 | 行数 |
|------|------|
| `frontend/src/views/MajorBalance.vue` | 15 |
| `frontend/src/views/MonthCheck.vue` | 15 |
| `frontend/src/views/WeekReport.vue` | 13 |
| `frontend/src/views/MonthReport.vue` | 13 |
| `frontend/src/views/YearReport.vue` | 13 |
| `frontend/src/composables/TemplateReport.vue` | 178 |

### 后端文件（3个）

| 文件 |
|------|
| `frontend/src/api/report.js` |
| `frontend/src/api/reportTemplate.js` |
| `backend/api/reports.py` |
| `backend/api/export.py`（grep） |
| `backend/services/report_service.py`（grep + 部分读取） |
| `backend/services/export_service.py`（grep） |
