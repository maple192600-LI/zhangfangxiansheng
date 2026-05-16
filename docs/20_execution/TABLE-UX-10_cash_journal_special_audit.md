# TABLE-UX-10 CashJournal 专项迁移前审计

> 审计日期：2026-05-16
> 审计分支：main（commit 3342239）
> 审计人：Agent（只读审计，未修改任何业务代码）

---

## 1. 当前页面事实

| # | 事实 | 结果 |
|---|------|------|
| 1 | 是否已使用 AdvancedDataTable | **否** — 3 条渲染路径均为原生 HTML table |
| 2 | 是否已使用 useDualView | **否** |
| 3 | 是否已使用 useAdvancedTablePreferences | **否** |
| 4 | 是否已有 templateExcelHtml | **是** — `useTemplateColumns('cash_journal')` 已解构 `templateExcelHtml` |
| 5 | 是否有 table-workspace-page | **否** — 根容器是 `div.report-print-root-wrapper > div.section.report-print-root`，缺少 `table-workspace-page` |
| 6 | 是否有 is_total / is_subtotal | **无前端标记** — 后端不返回 is_total，小计行由前端按 block 生成 |
| 7 | 导出是否走正式 exportReport | **是** — `exportReport({ export_type: 'cash_journal', ... })` |
| 8 | 打印是否走 useReportPrint | **是** — `const { handlePrint } = useReportPrint()` |
| 9 | 是否有 DEFAULT_COLUMNS fallback | **有** — 7 列：日期/单位/账户/摘要/收入/支出/余额 |
| 10 | 是否有 MONEY_KEYS | **有** — `prev_balance, income, expense, day_balance, amount, rolling_balance` |
| 11 | 筛选条件 | 日期范围 + 账户选择（MasterAccountSelect） |
| 12 | 数据加载 | `api.getCashJournal(params)` — 返回 blocks 数组 |
| 13 | 文件行数 | 471 行 |

---

## 2. 当前渲染路径图

CashJournal 有 **3 条互斥渲染路径**，由 `v-if` / `v-else-if` / `v-else` 控制：

```
loading?
  ├─ yes → loading-spinner
  └─ no
      ├─ templateExcelHtml? → 路径 A：原 Excel HTML 渲染
      │                        （v-html 注入完整 Excel 模板）
      ├─ hasFullLayout?     → 路径 B：完整 Excel 布局渲染
      │                        （templateLayout 驱动的多行多列账簿表格）
      └─ displayColumns?    → 路径 C：简化 table fallback
                               （普通表头+平铺 rows）
```

### 路径 A：templateExcelHtml（原 Excel 完整渲染）

- 触发条件：后端返回了 Excel HTML 文件
- 渲染方式：`v-html="templateExcelHtml"`
- 保留优先级：**最高** — 正式账簿样式
- 代码行：L24

### 路径 B：hasFullLayout（完整 Excel 布局渲染）

- 触发条件：templateLayout 存在且含 header + data/title 行
- 渲染方式：复杂原生 table，含合并单元格、签字栏、月初余额行、明细行、小计行
- 关键能力：
  - 固定行（标题/信息/表头）+ 数据行（按 block 循环）+ 小计行
  - 月初余额行（block-start）：显示 entity_name / account_name / opening_balance
  - 明细行：business_date / summary_text / income / expense / day_balance
  - 小计行：total_income / total_expense / ending_balance
  - 空数据时渲染空模板骨架
- 保留优先级：**高** — 完整账簿版式
- 代码行：L27-L118

### 路径 C：简化 table fallback

- 触发条件：无 templateExcelHtml 且无 hasFullLayout，但有 displayColumns
- 渲染方式：简单 thead + tbody，rows 扁平数据
- 代码行：L121-L137

---

## 3. 数据结构说明

### 3.1 后端返回：blocks

```python
blocks = [
  {
    "account_id": 1,
    "account_code": "ZH0001",
    "account_name": "工行基本户",
    "account_bank": "中国农业银行山西省阳曲支行",
    "entity_name": "喜跃发集团",
    "opening_balance": 100000.00,
    "total_income": 50000.00,
    "total_expense": 30000.00,
    "ending_balance": 120000.00,
    "rows": [
      {
        "business_date": "2026-05-01",
        "prev_balance": 100000.00,
        "income": 20000.00,
        "expense": 5000.00,
        "day_balance": 115000.00,
      },
      ...
    ]
  },
  ...
]
```

**关键特征**：
- 按账户分块（block = 一个账户的全部日汇总）
- 每个 block 有元信息（entity_name / account_name / opening_balance）和 rows（日汇总明细）
- 没有 `is_total` / `is_subtotal` 标记
- 小计行（月初余额行 + 小计行）由前端在布局渲染时生成，不是后端数据

### 3.2 前端扁平化：rows

```javascript
// loadReport() 中扁平化
rows = [
  {
    ...row,                    // business_date, prev_balance, income, expense, day_balance
    entity_name: block.entity_name,
    account_name: block.account_name,
    month: 5,
    day: 1,
  },
  ...
]
```

- 扁平化丢弃了 block 结构（opening_balance / total_income / total_expense / ending_balance）
- 用于简化 table fallback（路径 C）
- **数据视图可用** — 每行含 entity_name / account_name / business_date / income / expense / day_balance

### 3.3 templateLayout

```json
{
  "col_count": 12,
  "col_widths": [40, 40, 100, 100, 200, 80, 100, 100, 100, 100, 80, 80],
  "rows": [
    { "type": "title", "cells": [...] },
    { "type": "info", "cells": [...] },
    { "type": "header", "cells": [...] },
    { "type": "data", "cells": [...] },
    { "type": "data", "cells": [...] },
    { "type": "subtotal", "cells": [...] }
  ]
}
```

### 3.4 templateColumns

```json
[
  { "field_key": "business_date", "header_name": "日期", "width": 120, "align": "center" },
  ...
]
```

---

## 4. 可复用能力清单

| 能力 | 文件 | CashJournal 可否复用 |
|------|------|---------------------|
| AdvancedDataTable | `components/workbench/AdvancedDataTable.vue` | ✓ 用于数据视图 |
| useDualView | `composables/useDualView.js` | ✓ 用于账簿视图 / 数据视图切换 |
| useColumnAdapter | `composables/useColumnAdapter.js` | ✓ 用于模板列 → Tabulator 列转换 |
| useAdvancedTablePreferences | `composables/useAdvancedTablePreferences.js` | ✓ 用于列偏好持久化 |
| useTemplateColumns | `composables/useTemplateColumns.js` | ✓ 已在用 |
| tabulatorFormatters | `utils/tabulatorFormatters.js` | ✓ moneyFormatter 可用 |
| table-workspace-page | `views/common.css` | ✓ 补上 class 即可 |
| template-view / data-view | `views/common.css` | ✓ 已有布局样式 |

---

## 5. 不能破坏的账簿能力

| # | 能力 | 原因 |
|---|------|------|
| 1 | templateExcelHtml 渲染（路径 A） | 这是正式账簿的 Excel 原貌渲染，必须保留 |
| 2 | hasFullLayout 完整布局（路径 B） | 包含合并单元格、签字栏、月初余额行等正式账簿版式 |
| 3 | block 按账户分块渲染 | 日记账核心特征：每个账户一个 block，有月初余额 + 明细 + 小计 |
| 4 | 小计行渲染 | 每个 block 末尾的小计行（total_income / total_expense / ending_balance） |
| 5 | 月初余额行 | 每个 block 开头的月初余额行（entity_name / account_name / opening_balance） |
| 6 | 空数据模板骨架 | 无数据时仍渲染空模板结构 |
| 7 | 导出 exportReport | 正式导出路径，不能改 |
| 8 | 打印 handlePrint | 正式打印路径，打印账簿视图而非数据视图 |
| 9 | MasterAccountSelect | 账户选择器（不是 MasterEntitySelect） |
| 10 | 金额格式 fmtAmt | 所有金额显示必须用 fmtAmt |

---

## 6. 建议改造方案

### 6.1 核心思路：三视图 → 账簿视图 + 数据视图

```
改造前（3 条路径）：
  templateExcelHtml → 原始 Excel HTML
  hasFullLayout     → 完整 Excel 布局 table
  displayColumns    → 简化 table fallback

改造后（2 个视图）：
  账簿视图（isBookView）= 路径 A 或 路径 B（保留原样）
  数据视图（isDataView）= AdvancedDataTable（替代路径 C）
```

### 6.2 视图逻辑

```
hasBookView = templateExcelHtml 存在 || hasFullLayout 为 true

默认视图：
  hasBookView → 账簿视图
  !hasBookView → 数据视图

用户可手动切换。
```

### 6.3 useDualView 适配

`useDualView(templateExcelHtml)` 只检测 `templateExcelHtml`，不检测 `hasFullLayout`。需要扩展：

**方案 A（推荐）**：在 CashJournal 中不用 useDualView，自己写 `viewMode` ref + `setView()`。因为 CashJournal 的"有模板"判定比其他页面更复杂（templateExcelHtml OR hasFullLayout）。

**方案 B**：给 useDualView 增加第二个参数 `extraCondition`。但这改动公共 composable，不推荐。

### 6.4 具体实施

#### 模板结构改动

```html
<div class="section report-print-root table-workspace-page">
  <!-- section-title / filters-bar 保持不变 -->

  <!-- loading / error 保持不变 -->

  <!-- 账簿视图：路径 A + 路径 B 合并 -->
  <div v-if="isBookView" class="table-workspace-main template-view">
    <div class="template-hint adt-no-print">
      <span>账簿视图 · 当前显示正式账簿版式</span>
      <button @click="setView('data')">切换到数据视图</button>
    </div>
    <!-- 路径 A：原 Excel HTML -->
    <div v-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>
    <!-- 路径 B：完整 Excel 布局 table（保持不变） -->
    <div v-else-if="hasFullLayout" class="excel-layout-wrapper">
      ...（完全保持现状）
    </div>
  </div>

  <!-- 数据视图：AdvancedDataTable -->
  <div v-else-if="hasColumns" class="table-workspace-main data-view">
    <div v-if="hasBookView" class="view-mode-strip adt-no-print">
      <span>数据视图 · 当前启用高级表格</span>
      <button @click="setView('book')">切换到账簿视图</button>
    </div>
    <AdvancedDataTable ... />
  </div>

  <!-- 空状态 -->
  <div v-else class="empty-state">...</div>
</div>
```

#### script 改动

1. **根容器**：去掉 `report-print-root-wrapper`，加上 `table-workspace-page`
2. **视图状态**：
   ```javascript
   const hasBookView = computed(() => !!templateExcelHtml.value || hasFullLayout.value)
   const viewMode = ref('book')
   const isBookView = computed(() => viewMode.value === 'book' && hasBookView.value)
   const isDataView = computed(() => !isBookView.value)
   function setView(mode) { viewMode.value = mode }
   ```
3. **列定义**：
   ```javascript
   const tabulatorColumns = computed(() =>
     adaptTemplateColumns(templateColumns.value, DEFAULT_TABULATOR_COLUMNS, { moneyFields: MONEY_KEYS })
   )
   ```
4. **偏好系统**：照搬 TemplateReport/DailyReport 模式
5. **DEFAULT_TABULATOR_COLUMNS**：用 `field`（不是 `field_key`），适配 Tabulator 格式

#### 数据视图行数据

用已扁平化的 `rows` ref，但需增加：
- 每行加 `__row_key`
- **不加前端合计行** — 日记账的 block 结构在小计里已有汇总，扁平化后不适合加总计

#### rowClassFn

```javascript
// 数据视图不需要复杂的 rowClassFn
// 扁平化 rows 没有 is_total / is_subtotal
// 不需要特殊行样式
function rowClassFn(row) { return '' }
```

### 6.5 DEFAULT_TABULATOR_COLUMNS

```javascript
const DEFAULT_TABULATOR_COLUMNS = [
  { field: 'business_date', title: '日期', width: 120, hozAlign: 'center', formatter: emptyDashFormatter },
  { field: 'entity_name', title: '单位', width: 120, formatter: emptyDashFormatter },
  { field: 'account_name', title: '账户', width: 150, formatter: emptyDashFormatter },
  { field: 'summary_text', title: '摘要', width: 200, formatter: emptyDashFormatter },
  { field: 'income', title: '收入', width: 130, hozAlign: 'right', formatter: moneyFormatter },
  { field: 'expense', title: '支出', width: 130, hozAlign: 'right', formatter: moneyFormatter },
  { field: 'day_balance', title: '余额', width: 130, hozAlign: 'right', formatter: moneyFormatter },
]
```

---

## 7. 不建议方案

| # | 不建议方案 | 原因 |
|---|-----------|------|
| 1 | 把路径 B（完整布局）替换成 AdvancedDataTable | 丢失合并单元格、签字栏、月初余额行等正式账簿版式 |
| 2 | 用 AdvancedDataTable 模拟 block 分组 | Tabulator 不支持"按账户分块+月初余额行+小计行"的复杂分组，硬做会破坏版式 |
| 3 | 在扁平化 rows 中插入 __is_block_start 标记 | 改变了数据语义，增加后端耦合 |
| 4 | 修改 useDualView 适配 hasFullLayout | 改公共 composable 影响其他页面 |
| 5 | 给数据视图加前端合计行 | 日记账按账户分块，加总合计没有实际意义（不同账户的余额不能简单相加） |
| 6 | 改 MasterAccountSelect 为 MasterEntitySelect | 日记账按账户筛选，不是按单位筛选 |

---

## 8. 风险点

| # | 风险 | 等级 | 应对 |
|---|------|------|------|
| 1 | 账簿视图（路径 B）的 table 被 `table-workspace-main template-view` 的 `overflow: hidden` 裁剪 | **中** | 需测试路径 B 在 template-view 容器内是否正常。如果 layout table 宽度超出容器，需要让 `.excel-layout-wrapper` 正常 `overflow-x: auto` |
| 2 | `hasBookView` 初始化时机 — templateLayout 是异步加载的 | **低** | `hasFullLayout` 是 computed，会自动响应 templateLayout 变化 |
| 3 | 数据视图和账簿视图的切换会清空 Tabulator 实例 | **低** | `v-if` / `v-else` 会导致 AdvancedDataTable 重新挂载，但 rows 数据不会丢失 |
| 4 | 打印时数据视图的工具条不应打印 | **低** | 已有 `.adt-no-print` 类，template-hint 和 view-mode-strip 都加 `adt-no-print` |
| 5 | 路径 B 的 scoped CSS 可能和 common.css 冲突 | **低** | 路径 B 的 CSS 全部是 `.excel-*` 前缀，不与 common.css 冲突 |
| 6 | 根容器从 `report-print-root-wrapper > section` 改为 `section.table-workspace-page` 可能影响打印样式 | **低** | `report-print-root` 仍保留，打印样式只看 `report-print-root` |

---

## 9. 验收标准

### 9.1 代码标准

| # | 标准 |
|---|------|
| 1 | npm run build 通过 |
| 2 | git diff 只涉及 `CashJournal.vue`，无其他文件变更 |
| 3 | 不改后端 API / report_service.py |
| 4 | 不改导出逻辑 |
| 5 | 不改打印逻辑 |

### 9.2 功能标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | templateExcelHtml 路径 A 正常渲染 | 有 Excel 模板时，显示原貌 HTML |
| 2 | hasFullLayout 路径 B 正常渲染 | 有 layout 但无 Excel HTML 时，显示完整账簿表格 |
| 3 | 简化 table 被数据视图替代 | 无模板无 layout 时，显示 AdvancedDataTable |
| 4 | 账簿视图 / 数据视图可切换 | 有模板或 layout 时，有切换按钮 |
| 5 | 无模板无 layout 时自动数据视图 | 不显示"未配置报表模板" |
| 6 | 数据视图 AdvancedDataTable 可见 | 工具栏、密度切换、列设置正常 |
| 7 | 金额格式正确 | income/expense/day_balance 显示千分位 |
| 8 | 导出正常 | 点击导出按钮下载文件 |
| 9 | 打印正常 | 打印预览显示账簿视图，不含工具条 |
| 10 | 无双纵向滚动条 | JS 检查 |
| 11 | 控制台 0 error | 浏览器检查 |

---

## 10. 下一步实施任务包（TABLE-UX-10B）

### 10.1 实施范围

| 文件 | 改动 |
|------|------|
| `frontend/src/views/CashJournal.vue` | 全面改造 |

### 10.2 实施步骤

#### Step 1：根容器修复

- 去掉 `report-print-root-wrapper` 外层
- 加上 `table-workspace-page` class
- 保留 `report-print-root` class

#### Step 2：引入视图状态

- 不用 `useDualView`（原因：CashJournal 的 hasBookView 判定更复杂）
- 自行管理 `viewMode` ref + `isBookView` / `isDataView` computed
- `hasBookView = templateExcelHtml || hasFullLayout`

#### Step 3：模板结构改造

- 账簿视图区域：包裹路径 A + 路径 B，加 `template-hint`
- 数据视图区域：新增 `data-view` + AdvancedDataTable
- 空状态保持

#### Step 4：列定义适配

- 新增 `DEFAULT_TABULATOR_COLUMNS`（field 格式，适配 Tabulator）
- 用 `adaptTemplateColumns()` 合并模板列
- `displayColumns` 计算从 `field_key` 格式转为 `field` 格式

#### Step 5：偏好系统集成

- 引入 `useAdvancedTablePreferences`
- `preferencesVersion` + `appliedColumns` + `hiddenFields` + 6 个回调
- `tableKey = 'cash-journal'`

#### Step 6：数据行处理

- `rows` 扁平数据保持不变
- 给每行加 `__row_key`
- 不加前端合计行

#### Step 7：浏览器验证

- 无模板时数据视图
- 有 layout 时账簿视图 → 数据视图切换
- 导出、打印、密度、列设置

### 10.3 Claude Code 执行提示词草案

```
你现在在账房先生项目中执行 TABLE-UX-10B：CashJournal 数据视图改造。

背景：
TABLE-UX-10 审计已完成，审计文档在 docs/20_execution/TABLE-UX-10_cash_journal_special_audit.md。
当前仓库状态：main 分支，commit 3342239，工作树干净。

本次只改一个文件：frontend/src/views/CashJournal.vue

必须读取：
- docs/20_execution/TABLE-UX-10_cash_journal_special_audit.md
- frontend/src/views/CashJournal.vue
- frontend/src/composables/TemplateReport.vue（参考偏好系统写法）
- frontend/src/views/DailyReport.vue（参考双视图写法）
- frontend/src/views/common.css

改造要求：
1. 根容器：去掉 report-print-root-wrapper，改为 section.report-print-root.table-workspace-page
2. 不用 useDualView，自行管理 viewMode（因为 hasBookView = templateExcelHtml || hasFullLayout）
3. 账簿视图 = 路径 A（templateExcelHtml）+ 路径 B（hasFullLayout），包裹在 template-view + template-hint 中
4. 数据视图 = AdvancedDataTable，包裹在 data-view + view-mode-strip 中
5. 数据视图使用 rows 扁平数据
6. DEFAULT_TABULATOR_COLUMNS 使用 field 格式（不是 field_key）
7. 用 adaptTemplateColumns 合并模板列
8. 偏好系统：tableKey = 'cash-journal'
9. 金额字段：income / expense / day_balance 用 moneyFormatter
10. 不加前端合计行
11. 不改后端 API
12. 不改导出/打印逻辑
13. 路径 B 的完整 Excel 布局渲染代码必须保留（100+ 行），只在外层包裹 template-view
14. 路径 A 的 templateExcelHtml v-html 渲染必须保留
15. 打印时工具条不打印（adt-no-print）

禁止：
- 不改后端
- 不改导出/打印
- 不删 templateExcelHtml
- 不删 hasFullLayout
- 不删路径 B 的 table 渲染代码
- 不改 MasterAccountSelect
- 不引入 DuckDB
- 不用 mock 数据

验收标准：
1. npm run build 通过
2. 账簿视图（路径 A + 路径 B）正常
3. 数据视图 AdvancedDataTable 正常
4. 视图切换正常
5. 导出不坏
6. 打印不包含工具条
7. 无双滚动条
8. 控制台 0 error
9. git diff 只涉及 CashJournal.vue
```

---

## 附录

### 已读取文件清单

| 文件 | 状态 |
|------|------|
| `frontend/src/views/CashJournal.vue` | 完整读取（471 行） |
| `frontend/src/views/DailyReport.vue` | 前轮已读 |
| `frontend/src/composables/TemplateReport.vue` | 前轮已读 |
| `frontend/src/components/workbench/AdvancedDataTable.vue` | 前轮已读 |
| `frontend/src/composables/useDualView.js` | 前轮已读 |
| `frontend/src/composables/useTemplateColumns.js` | 前轮已读 |
| `frontend/src/composables/useColumnAdapter.js` | 前轮已读 |
| `frontend/src/composables/useAdvancedTablePreferences.js` | 前轮已读 |
| `frontend/src/composables/useReportPrint.js` | 前轮已读 |
| `frontend/src/views/common.css` | 前轮已读 |
| `frontend/src/styles/theme.css` | 部分读取（前 50 行变量） |
| `frontend/src/api/report.js` | 前轮已读 |
| `frontend/src/api/export.js` | 完整读取（3 行） |
| `backend/services/report_service.py` | grep 读取 cash_journal 函数（L95-L165） |
| `backend/services/report_template_service.py` | 未单独读取（通过 useTemplateColumns 间接了解） |
| `docs/20_execution/14_base_data_and_report_execution.md` | 未读取（非阻塞，审计依据已足够） |

### 当前分支和状态

- **分支**：main
- **git status**：clean，本地领先 origin/main 1 commit（3342239）
- **是否建议 push**：由用户决定，不擅自 push

### 是否建议进入 TABLE-UX-10B 实施

**建议进入**。

理由：
1. CashJournal 是唯一未接入高级表格体系的报表页面
2. 改造范围可控（单文件），且路径 A/B 完整保留
3. 数据视图仅替代路径 C（简化 table fallback），风险极低
4. 审计已识别所有风险点和注意事项
