# UI-3B 筛选区控件迁移收口报告

## 1. 合并状态

| PR | 文件 | 状态 | 合并 commit | CI |
|----|------|------|-------------|-----|
| #21 AccountBalance | `frontend/src/views/AccountBalance.vue` | ✅ 已合并 | `8bc26d7` | backend-tests SUCCESS |
| #22 DailyReport | `frontend/src/views/DailyReport.vue` | ✅ 已合并 | `1a9c9fa` | backend-tests SUCCESS |
| #23 ExpenseList | `frontend/src/views/ExpenseList.vue` | ✅ 已合并 | `e0db9ea` | backend-tests SUCCESS |
| #24 IncomeList | `frontend/src/views/IncomeList.vue` | ✅ 已合并 | `7694776` | backend-tests SUCCESS |

main 最新 commit：`7694776 feat: migrate IncomeList filters and pagination to Naive UI (Phase UI-3B-4) (#24)`

## 2. 迁移范围总结

UI-3B 完成了以下四个页面的筛选区控件迁移：

- AccountBalance：筛选区（日期 + 下拉 + 按钮）
- DailyReport：筛选区（日期 + 下拉 + 按钮）
- ExpenseList：筛选区（日期 + 下拉 + 按钮）+ 底部分页按钮
- IncomeList：筛选区（日期 + 下拉 + 按钮）+ 底部分页按钮

组件替换：

| 原控件 | Naive UI | 说明 |
|--------|----------|------|
| `input type="date"` | `NDatePicker` | type="date" clearable，width:160px |
| `select` + `option` | `NSelect` | clearable，min-width:160px |
| `button.btn.btn-primary` | `NButton type="primary"` | 生成报表按钮 |
| `button.btn.btn-secondary` | `NButton`（default） | 导出、打印按钮 |
| `button.btn.btn-secondary.btn-sm` | `NButton size="small"` | 上一页、下一页（仅 ExpenseList/IncomeList） |
| `.btn-row` 布局 | `NSpace` | 筛选区按钮组 |

## 3. 日期适配策略

四个文件统一采用同一模式：

| 层 | 类型 | 说明 |
|----|------|------|
| 业务 state（`startDate`/`endDate`） | `string`（YYYY-MM-DD） | 原有 ref，未改动 |
| NDatePicker value | `number | null`（毫秒时间戳） | Naive UI 要求 |
| `dateStringToTs(s)` | string → timestamp | `new Date(y, m-1, d).getTime()` |
| `tsToDateString(ts)` | timestamp → string | `getFullYear/getMonth/getDate` 格式化 |
| `startDateTs` / `endDateTs` | computed get/set | 双向适配层 |
| clear 处理 | `tsToDateString(null)` → `''` | 原有 `|| undefined` 兜底仍有效 |

四个文件适配层代码完全一致，逐文件复制（未抽取公共函数，避免跨文件耦合）。

API 参数验证：四个文件的 `loadReport()` / `loadData()` / `doExport()` 均直接读取 `startDate.value` 和 `endDate.value`，类型始终为 YYYY-MM-DD 字符串，未受 NDatePicker 影响。

## 4. 保留未迁移项

以下内容在本阶段**明确未迁移**，留到后续阶段处理：

| 未迁移项 | 当前状态 | 计划阶段 |
|----------|----------|----------|
| `<table>` / `<thead>` / `<tbody>` / `<tr>` / `<td>` | 原生 HTML table | UI-3C |
| `NDataTable` | 未引入 | UI-3C |
| `templateExcelHtml` / `v-html` | 原样保留 | UI-3C 后评估 |
| `empty-state` | 原样保留 | UI-3C |
| `loading-state` / `error-bar` | 原样保留（仅 DailyReport 有） | UI-3C |
| `total-row`（合计行） | 原样保留（仅 DailyReport 有） | UI-3C |
| `common.css` | 未清理，仍被所有四个文件引用 | UI-4 |
| `alert()` / `confirm()` | 未迁移 | UI-3C 或后续 |
| API 逻辑 | 未改动 | - |
| 分页逻辑（page/total/totalPages） | 未改动，只替换了按钮外观 | - |

## 5. 验证结果

### 构建验证

- `npm run build`：✅ 通过（562ms）

### Naive UI 组件搜索

四个文件合计：
- `NDatePicker`：8 处（每文件 2 个，start + end）
- `NSelect`：4 处（每文件 1 个）
- `NSpace`：4 处（每文件 1 个）
- `NButton`：14 处（AccountBalance/DailyReport 各 3，ExpenseList/IncomeList 各 5，含分页按钮）
- `import`：4 处（每文件 1 行）

### 旧控件残留

- `input type="date"`：0 处（搜索结果仅 NDatePicker 自身的 `type="date"` 属性）
- `<select>`：0 处
- `<option>`：0 处
- `btn-primary`：0 处
- `btn-secondary`：0 处
- `btn-sm`：0 处

### Ant Design 残留

- 全 `frontend/src` 零匹配

### 浏览器验证概况

| 页面 | 页面打开 | 日期显示 | 生成报表 | 导出 | 打印 | Console |
|------|----------|----------|----------|------|------|---------|
| AccountBalance | ✅ | ✅ 2026-05-11 | ✅ | ✅ | ✅ | 零 warning |
| DailyReport | ✅ | ✅ 2026-05-11 | ✅ | ✅ | ✅ | 零 warning |
| ExpenseList | ✅ | ✅ 2026-05-11 | ✅ | ✅ | ✅ | 零 warning |
| IncomeList | ✅ | ✅ 2026-05-11 | ✅ | ✅ | ✅ | 零 warning |

## 6. 已知未完全覆盖的人工验证

以下场景因测试环境数据不足，无法在本次迁移中完整验证：

| 待验证项 | 原因 | 建议 |
|----------|------|------|
| ExpenseList 分页 disabled 样式 | `total=0`，分页栏不显示 | 有支出数据后复验 |
| ExpenseList 翻页 page 变化 | 同上 | 有支出数据后复验 |
| IncomeList 分页 disabled 样式 | `total=0`，分页栏不显示 | 有收入数据后复验 |
| IncomeList 翻页 page 变化 | 同上 | 有收入数据后复验 |
| NSelect 多单位实体筛选 | `accounts-tree` API 返回空数组 | 创建账户/单位数据后复验 |

## 7. 下一阶段建议

**不要直接执行 UI-3C。建议先做 UI-3C 前置审计，不改代码。**

### UI-3C 候选方向

| 方向 | 涉及页面 | 风险 | 说明 |
|------|----------|------|------|
| 表格 → NDataTable | 4 个文件 | 高 | 涉及列配置、合计行、subtotal、v-html 模板渲染 |
| 状态标签 → NTag | HomeQuick 等 | 低 | UI-3A 已部分完成 |
| loading/empty 补齐 | DailyReport 等 | 低 | 已有 loading-state，可迁移为 NSpin/NEmpty |
| alert → useMessage | 4 个文件 | 中 | 需要获取 Naive UI message 实例 |

### 表格迁移注意事项

NDataTable 与现有原生 `<table>` 差异较大：

1. **列配置**：现有用 `displayColumns` 数组驱动 `<th>/<td>` 循环，NDataTable 需要 `columns` + `data` props
2. **合计行**：DailyReport 有 `total-row`，需要 NDataTable 的 `summary` 插槽
3. **小计行**：AccountBalance 有 `subtotal-row`（`r.is_subtotal`），NDataTable 无原生支持
4. **v-html 模板**：当 `templateExcelHtml` 存在时完全跳过 table，这部分不受影响
5. **分页**：ExpenseList/IncomeList 有分页，需配合 NDataTable 的分页或保持独立

### 建议下一步

1. **UI-3C 审计文档**：逐页面评估表格迁移复杂度和风险
2. **优先迁移低风险页面**：选择无合计行、无小计行的页面先做
3. **common.css 清理**（UI-4）：等所有控件迁移完成后再统一清理
