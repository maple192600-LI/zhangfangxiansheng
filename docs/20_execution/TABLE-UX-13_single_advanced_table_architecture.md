# TABLE-UX-13：高级表格唯一视图架构重规划

> 状态：架构审计 + 方案设计（未改代码）
> 分支：plan/table-ux-13-single-table-architecture（基于 main/e068d5e）
> 日期：2026-05-16

---

## 1. 当前结论

### 1.1 为什么旧"双视图"方向不继续

旧方向（TABLE-UX-12 之前的遗留）给每个报表页面引入了 `useDualView`，当 Excel 模板存在时默认展示"模板视图"（v-html 渲染），用户需要手动切换到"数据视图"（AdvancedDataTable）。

问题：
- 用户不理解为什么同一个页面有两种完全不同的表格外观
- 模板视图无交互能力（无排序、无列宽调整、无密度切换、无列显隐）
- 打印/导出依赖当前视图状态——如果用户在数据视图下点打印，打印的是高级表格而非正式版式
- 每个页面重复写一遍双视图切换逻辑（viewMode、isTemplateView、isDataView、setView、template-hint、view-mode-strip）

### 1.2 为什么高级表格要成为唯一主视图

- 高级表格已有完整的交互能力：排序、列宽拖动、列显隐、密度切换、分页
- 高级表格已接入偏好系统（localStorage），用户列配置可持续
- 所有数据页面的列定义已经通过 `useColumnAdapter` 从 Excel 模板提取，AdvancedDataTable 已经能"继承"模板的列顺序和列宽
- 用户进入页面应该直接看到可交互的数据表格，不需要理解"模板"概念

### 1.3 为什么 Excel 模板仍然不能删除

- **打印版式**：正式财务报表打印需要保留合并单元格、标题行、页眉页脚等版式，v-html 渲染的模板是打印版式的最直接来源
- **导出版式**：后端 `exportReport` API 依赖模板生成正式 Excel 导出文件
- **列配置**：`useTemplateColumns` 从模板提取 columns，经 `useColumnAdapter` 转为 Tabulator 列定义
- **账簿版式**：CashJournal 的完整账簿版式（合并单元格的标题行/信息行/表头行 + 按账户分块的数据行 + 小计行）无法用普通表格还原

---

## 2. 当前代码审计表

### 2.1 核心组件

| 组件 | 位置 | 职责 |
|------|------|------|
| AdvancedDataTable.vue | components/workbench/ | Tabulator 高级表格封装，工具栏/列设置/密度/选择 |
| useTabulatorTable.js | composables/ | Tabulator 生命周期管理（创建/更新/销毁） |
| useTemplateColumns.js | composables/ | 从后端加载模板（excel-html + columns + layout） |
| useColumnAdapter.js | composables/ | 模板列定义 → Tabulator 列定义转换 |
| useAdvancedTablePreferences.js | composables/ | 列宽/列显隐/列顺序/密度偏好（localStorage） |
| useDualView.js | composables/ | 模板/数据双视图切换逻辑（**本次要消解**） |
| TemplateReport.vue | composables/ | 通用报表壳组件（5 个报表页面共用） |
| tabulatorFormatters.js | utils/ | 金额/状态/操作等 Tabulator 格式化器 |
| useReportPrint.js | composables/ | 打印封装（当前仅 window.print()） |
| common.css | views/ | 表格工作区通用样式（flex 布局、滚动、视图切换） |
| MainLayout.vue | layouts/ | 全局布局（左侧导航 + 右侧内容区 flex 锁高） |

### 2.2 页面级审计

| 页面 | 当前主渲染路径 | 是否 ADT | templateExcelHtml 优先 | 存在视图切换 | useTemplateColumns | useColumnAdapter | useAdvancedTablePreferences | 有打印 | 有导出 | 有合计/小计 | 有行内操作 | 有批量选择 | 有滚动风险 | TABLE-UX-13 策略 | 风险等级 |
|------|---------------|---------|----------------------|-------------|-------------------|-----------------|---------------------------|-------|-------|------------|-----------|-----------|-----------|-----------------|---------|
| ExceptionCenter | AdvancedDataTable（唯一） | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ 修正/作废 | ❌ | 低 | 无需改动 | 低 |
| BaseDataTable | useDualView，模板优先 | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ window.print | ✅ 后端导出 | ❌ | ❌ | ✅ | 低 | 去掉双视图，默认 ADT | 中 |
| IncomeList | useDualView，模板优先 | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 低 | 去掉双视图，默认 ADT | 低 |
| ExpenseList | useDualView，模板优先 | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 低 | 去掉双视图，默认 ADT | 低 |
| AccountBalance | useDualView，模板优先 | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 合计/小计行 | ❌ | ❌ | 低 | 去掉双视图，默认 ADT | 中 |
| DailyReport | useDualView，模板优先 | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 前端合计行 | ❌ | ❌ | 低 | 去掉双视图，默认 ADT | 中 |
| MajorBalance | TemplateReport → useDualView | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 前端合计行 | ❌ | ❌ | 低 | TemplateReport 改造 | 中 |
| WeekReport | TemplateReport → useDualView | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 前端合计行 | ❌ | ❌ | 低 | TemplateReport 改造 | 中 |
| MonthReport | TemplateReport → useDualView | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 前端合计行 | ❌ | ❌ | 低 | TemplateReport 改造 | 中 |
| YearReport | TemplateReport → useDualView | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 前端合计行 | ❌ | ❌ | 低 | TemplateReport 改造 | 中 |
| MonthCheck | TemplateReport → useDualView | ✅ | ✅ | ✅ 模板/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 低 | TemplateReport 改造 | 低 |
| **CashJournal** | 自定义账簿/数据双视图，**账簿优先** | ✅ | ✅ | ✅ 账簿/数据 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 小计行+分块 | ❌ | ❌ | 低 | 专项：ADT 为主+账簿预览入口 | **高** |
| ManualFlow | 原生 table（可编辑） | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ calc(100vh-340px) | 本轮不进入 | — |
| ManualMaintenance | 原生 table | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ calc(100vh-260px) | 本轮不进入 | — |
| AccountManage | 原生 table×4 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ 批量选择 | ⚠️ calc(100vh-300px) | 本轮不进入 | — |
| UploadPreview | 原生 table×2 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ calc(100vh-360px) | 本轮不进入 | — |
| BankImport | 原生 table（预览） | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 低 | 本轮不进入 | — |

### 2.3 关键事实汇总

**事实 1：哪些页面现在是 templateExcelHtml 优先渲染**

CashJournal（账簿视图优先）、BaseDataTable、IncomeList、ExpenseList、AccountBalance、DailyReport、MajorBalance、WeekReport、MonthReport、YearReport、MonthCheck —— 共 11 个页面。

原因：`useDualView` 的 watch 逻辑在模板加载完成后自动将 viewMode 设为 `'template'`（见 `useDualView.js:19`），且 CashJournal 的 viewMode 初始值就是 `'book'`。

**事实 2：哪些页面已接入 AdvancedDataTable**

ExceptionCenter（纯 ADT，无双视图）、BaseDataTable、CashJournal、IncomeList、ExpenseList、AccountBalance、DailyReport、MajorBalance、WeekReport、MonthReport、YearReport、MonthCheck —— 共 12 个页面。

**事实 3：哪些页面存在视图切换**

CashJournal（账簿/数据）、其余使用 useDualView 的 10 个页面（模板/数据）、共 11 个。

**事实 4：哪些页面的 Excel 模板只是列配置来源**

无。所有使用 useTemplateColumns 的页面同时也用 templateExcelHtml 做 v-html 渲染。列配置和渲染版式目前是耦合的。

**事实 5：哪些页面的 Excel 模板是完整 v-html 渲染**

上述 11 个页面全部。CashJournal 额外有 `templateLayout` 驱动的原生 table 账簿版式。

**事实 6：打印/导出与页面渲染的耦合情况**

- 打印：所有页面统一使用 `window.print()`，打印的是当前可见 DOM。模板视图下打印模板，数据视图下打印高级表格。**耦合在视图状态上**。
- 导出：所有报表页面使用后端 `exportReport` API，与页面渲染完全解耦。

**事实 7：合计/小计/行内操作/批量选择分布**

- 合计行：AccountBalance（is_total + is_subtotal）、DailyReport（前端合计行）、MajorBalance/WeekReport/MonthReport/YearReport（前端合计行）
- 小计行：CashJournal（按账户分块的小计）
- 行内操作：ExceptionCenter（修正/作废按钮）、AccountManage（编辑/停用/删除）
- 批量选择：BaseDataTable（批量删除）、AccountManage（批量启用/停用/删除）

**事实 8：useColumnAdapter 使用**

11 个报表页面 + TemplateReport 均使用 `adaptTemplateColumns` 将模板列转为 Tabulator 列定义。

**事实 9：useAdvancedTablePreferences 使用**

12 个页面全部使用（ExceptionCenter 直接用，其余通过页面或 TemplateReport 间接用）。

**事实 10：原生 table 页面**

ManualFlow、ManualMaintenance、AccountManage（4 个 tab 各一个 table）、UploadPreview（2 个 tab）、BankImport —— 共 5 个页面。本轮不进入改造范围。

**事实 11：滚动容器风险**

- 5 个原生 table 页面使用 `calc(100vh - Npx)` 魔法值，有溢出风险
- 12 个已接入 ADT 的页面使用 `.table-workspace-page` + `.table-workspace-main` 的 flex 布局，无魔法值，低风险

**事实 12：旧分支 fix/table-ux-13-view-mode-copy 改了什么**

8 个文件、35 行增/70 行删，全部是：
1. 将视图切换按钮文案从"切换到数据视图"改为"切换到高级表格"
2. 将模板提示文案从"当前使用 Excel 模板渲染"改为"保留 Excel 模板版式，适合正式打印和导出"
3. CashJournal 和 ExceptionCenter 的 DatePicker 从 computed 包装改为 v-model:value + value-format="yyyy-MM-dd"

其中 DatePicker 修复已由 PR #46 在 main 上完成。文案修改未合入。**不采用旧分支**。

---

## 3. 新架构说明

### 3.1 页面主渲染路径（改造后）

```
Excel 模板（后端）
    ↓ useTemplateColumns.loadTemplate()
    ↓ templateColumns (列定义)
    ↓ useColumnAdapter.adaptTemplateColumns()
    ↓ tabulatorColumns (Tabulator 格式)
    ↓ useAdvancedTablePreferences.applyPreferences()
    ↓ appliedColumns (应用用户偏好)
    ↓
AdvancedDataTable ← 页面主表格（唯一主视图）
```

### 3.2 打印/导出路径（独立于页面渲染）

```
                    ┌── window.print() → 打印当前可见 DOM
                    │   （高级表格打印模式，或
                    │    账簿预览模式的打印）
                    │
页面主表格 ────────┤
(AdvancedDataTable) │
                    │   ┌── 后端 exportReport API → 正式 Excel 导出
                    └──┤
                       └── 账簿预览弹窗/面板（仅 CashJournal 等
                            复杂账簿需要） → 打印正式版式
```

### 3.3 核心变更

1. **useDualView 废弃**：不再有"模板视图/数据视图"的页面级切换
2. **viewMode 默认值改为 'data'**：如不删除 useDualView，则修改其默认行为（不再自动切到 template）
3. **templateExcelHtml 不再用于页面主渲染**：只保留给打印预览弹窗使用
4. **template-hint / view-mode-strip 移除**：用户不再看到视图切换提示
5. **打印保持独立**：打印继续使用 `window.print()`；但 CashJournal 等需要提供"正式账簿预览"入口，该入口打开一个弹窗/面板显示 v-html 内容并触发打印
6. **TemplateReport.vue 改造**：作为 5 个报表页面的共享壳，需同步移除双视图逻辑

---

## 4. 组件改造建议

### 4.1 需要新增的组件

#### useReportPrintPreview.js（打印预览 composable）

- **负责**：在弹窗中展示 templateExcelHtml 的 v-html 内容，提供"打印此版式"按钮
- **不负责**：页面主渲染、列定义、数据加载
- **触发方式**：页面工具栏的"正式版式打印"按钮（仅当 templateExcelHtml 存在时显示）
- **弹窗行为**：全屏或大弹窗，展示 v-html 内容，点击打印按钮调用 window.print()

#### ReportPrintPreviewDialog.vue（可选）

- 如果需要更精细的打印预览 UI（如页边距提示、纸张方向提示），可单独抽组件
- **负责**：渲染 templateExcelHtml 的弹窗 UI
- **不负责**：数据逻辑

### 4.2 需要改造的组件

#### useDualView.js

两个选择：
- **方案 A（推荐）：删除 useDualView**，所有页面不再引入。每个页面直接展示 AdvancedDataTable。
- **方案 B：保留但修改默认值**，viewMode 初始值改为 `'data'`，删除自动切到 template 的 watch 逻辑。保留 setView 方法给打印预览用。

推荐方案 A，因为改造完成后没有任何页面需要"在模板和 ADT 之间切换"。

#### TemplateReport.vue

- 移除 `useDualView` 引用
- 移除模板视图的 `v-else-if="isTemplateView"` 分支
- 移除 `view-mode-strip` 和 `template-hint` DOM
- 保留 `useTemplateColumns`（仍需从模板提取列配置）
- 保留 `templateExcelHtml` ref（传给打印预览 composable 使用）
- AdvancedDataTable 成为唯一表格渲染路径

#### 各独立页面（BaseDataTable、IncomeList、ExpenseList、AccountBalance、DailyReport）

同 TemplateReport 的改造模式：
- 移除 `useDualView`
- 移除模板视图分支和视图切换 UI
- AdvancedDataTable 成为唯一主视图
- `templateExcelHtml` 保留，传给打印预览

#### CashJournal.vue

专项处理（见第 5 节第三批）

### 4.3 不需要新增的组件

- **不需要 ReportTableShell.vue**：TemplateReport.vue 已经是报表壳，改造它即可
- **不需要 useReportTableConfig.js**：`useColumnAdapter` + `useAdvancedTablePreferences` 已经覆盖列配置逻辑
- **不需要 useReportPrintPreview.js**（如果用方案 B 保留 useDualView）：打印预览只需在页面级处理

---

## 5. 页面改造顺序

### 第一批：低风险页面（TABLE-UX-13C）

| 页面 | 理由 |
|------|------|
| ExceptionCenter | 已是纯 ADT，无需改动，作为对照基线 |
| IncomeList | 简单列表页，无合计/小计，无行内操作 |
| ExpenseList | 同 IncomeList |
| BaseDataTable | 有批量选择，略复杂但无合计行 |
| AccountBalance | 有合计/小计行，需要验证 rowClassFn 在 ADT 中正常 |

改造内容统一为：
1. 移除 `useDualView` 引入和使用
2. 移除 `isTemplateView` / `isDataView` / `setView` 相关代码
3. 移除模板视图 `<div>` 分支（template-hint + excel-host v-html）
4. 移除数据视图中的 view-mode-strip
5. ADT 的 `isInDataView` prop 移除（永远在数据视图）
6. 添加"正式版式打印"按钮（条件：templateExcelHtml 存在时显示）

### 第二批：报表页（TABLE-UX-13D）

改造 TemplateReport.vue 即可覆盖 5 个页面：
- DailyReport（有前端合计行）
- MajorBalance
- WeekReport
- MonthReport
- YearReport
- MonthCheck

改造内容同第一批，但由于 TemplateReport 是共享组件，需一次性验证所有 5 个使用方的数据正确性。

### 第三批：CashJournal 专项（TABLE-UX-13E）

CashJournal 是最复杂的页面：

1. **账簿视图**：有完整 Excel 布局渲染（templateLayout 驱动的原生 table，含合并单元格、标题行、按账户分块的数据行、小计行），还有 templateExcelHtml 的 v-html 渲染
2. **数据视图**：AdvancedDataTable 展示平铺后的所有行（失去分块结构）
3. **改造策略**：
   - 页面默认展示 AdvancedDataTable（唯一主视图）
   - 工具栏增加"正式账簿预览"按钮（仅当 hasBookView 时显示）
   - 点击后打开弹窗，渲染原有账簿版式（保留完整的 templateLayout 渲染逻辑）
   - 弹窗中提供"打印"按钮
   - 导出保持不变（后端 exportReport API）

**不删除**：
- CashJournal 中的 `templateLayout` 相关计算属性（fixedRows、firstRowFull、detailRowFull、subtotalRowFull 等）
- 账簿版式渲染函数（toFullRow、fixedCellText、detailCellText、subtotalCellText 等）
- 这些逻辑移到弹窗组件中，或通过 prop 传递

---

## 6. 验收标准

### 6.1 功能验收

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 页面主数据区默认显示 AdvancedDataTable | 浏览器打开每个页面，确认看到高级表格工具栏 |
| 2 | 用户无需理解"模板视图/数据视图"切换 | 确认页面无视图切换按钮 |
| 3 | Excel 模板删除时，页面仍显示高级表格（用 DEFAULT_COLUMNS） | 后端删除模板后刷新页面 |
| 4 | Excel 模板存在时，高级表格列顺序/列宽/标题/格式受模板影响 | 上传模板后刷新，对比列定义 |
| 5 | 打印/导出不受列显隐/列顺序/密度影响 | 隐藏若干列后导出，确认导出仍完整 |
| 6 | 列宽/列显隐/列顺序/密度偏好继续可用 | 调整后刷新页面，确认持久化 |
| 7 | 合计/小计行不丢失 | AccountBalance、DailyReport 等确认有合计行 |
| 8 | 行内操作不丢失 | ExceptionCenter 修正/作废按钮正常 |
| 9 | 分页不丢失 | BaseDataTable 分页正常 |
| 10 | 左侧导航不随右侧滚动 | MainLayout flex 锁高正常 |
| 11 | 只有数据区滚动 | 确认无 body 级滚动 |
| 12 | 无双纵向滚动条 | 确认 Tabulator 和外层无重复滚动条 |

### 6.2 工程验收

| # | 标准 |
|---|------|
| 1 | `npm run build` 通过 |
| 2 | 浏览器控制台 0 error / 0 warning |
| 3 | 所有 12 个报表/数据页面逐一验证 |

---

## 7. 禁止项

1. **禁止继续复制双视图逻辑** —— 不再新增 useDualView 引用
2. **禁止删除模板系统** —— useTemplateColumns、useColumnAdapter、templateExcelHtml 必须保留
3. **禁止把正式导出改成前端临时导出** —— 后端 exportReport API 是正式导出路径
4. **禁止把打印内容变成当前列显隐后的表格** —— 打印应使用正式版式
5. **禁止为单页写死字段** —— 列定义必须走 DEFAULT_COLUMNS → adaptTemplateColumns 路径
6. **禁止新增散落的高度 calc 魔法值** —— 使用 flex 布局
7. **禁止顺手改后端** —— 本轮不改后端数据结构、API、数据库
8. **禁止顺手做 DuckDB** —— 不在本轮范围
9. **禁止顺手做可编辑表格** —— 不在本轮范围
10. **禁止把旧分支直接 merge** —— fix/table-ux-13-view-mode-copy 仅做对比参考

---

## 8. 后续实施拆包

### TABLE-UX-13A：架构文档与审计（本次 PR）

- 本文档
- 旧分支对比记录
- 无代码改动

### TABLE-UX-13B：统一改造基础设施

- useDualView 处理方案（删除或改造）
- 打印预览 composable/组件
- common.css 清理（template-hint、view-mode-strip 等样式保留但标记为打印预览用）
- 验证：npm run build + 12 个页面均无报错

### TABLE-UX-13C：第一批页面收敛

- IncomeList、ExpenseList、BaseDataTable、AccountBalance
- ExceptionCenter 作为基线对照（无改动）
- 验证：4 个页面逐一浏览器操作 + 导出 + 打印

### TABLE-UX-13D：第二批报表页收敛

- TemplateReport.vue 改造 → 覆盖 DailyReport、MajorBalance、WeekReport、MonthReport、YearReport、MonthCheck
- 验证：6 个页面逐一浏览器操作 + 导出 + 打印

### TABLE-UX-13E：CashJournal 专项收敛

- CashJournal 自定义账簿/数据双视图改为 ADT 唯一主视图 + 账簿预览弹窗
- 验证：账簿预览弹窗显示完整版式 + 打印 + 导出

### TABLE-UX-13F：全局滚动与打印/导出回归验收

- 12 个页面全量回归
- 滚动行为确认（无双滚动条、导航不跟滚）
- 打印输出确认（正式版式）
- 导出文件确认（后端 API，不受前端列显隐影响）
- npm run build 通过
- 控制台 0 error / 0 warning
