# UI-3 通用组件迁移审计

> 审计日期：2026-05-11
> 审计分支：`feat/frontend-naive-ui-forms-buttons-audit`（从 main `fd6d42e` 检出，未提交）
> 审计范围：仅检测和规划，不修改代码

---

## 1. 当前基础状态

| 检查项 | 结果 |
|--------|------|
| main 最新 commit | `fd6d42e` — feat: migrate modals to Naive UI (Phase UI-2) (#19) |
| 当前分支 | `feat/frontend-naive-ui-forms-buttons-audit` |
| `npm run build` | ✅ 通过（560ms） |
| UI-1 已合并 | ✅ NLayout + NMenu + 双皮肤系统 |
| UI-2 已合并 | ✅ 2 个弹窗迁移完成（NModal + NForm + NInput + NButton + NSelect） |
| Ant Design 残留 | ✅ 零匹配 |
| Naive UI 组件使用 | ✅ MainLayout + AgentCreateModal 已使用 NModal/NForm/NFormItem/NInput/NSelect/NButton/NSpace/useMessage |
| `common.css` 引用 | 25 个文件通过 `@import './common.css'` 引入公共样式 |

---

## 2. 组件残留统计

### 2.1 按类型统计

| 类型 | 搜索关键词 | 匹配文件数 | 总匹配数 | 高密度文件 |
|------|------------|-----------|---------|-----------|
| 自定义按钮 | `class="btn"` | 29 个文件 | ~250 处 | AccountManage(45), SystemMaintenance(16), BankImport(11), ChatPanel(10) |
| 表单组 | `form-group` / `form-input` / `form-label` | 6 个文件 | ~164 处 | AccountManage(128), Login(11), BankManage(28) |
| 筛选控件 | `class="filter"` | 14 个文件 | ~59 处 | AccountManage(14), TemplateReport(7), BaseDataTable(6) |
| 原生 select | `<select` | 19 个文件 | ~50 处 | AccountManage(26), AIConfig(2), BankManage(2) |
| 原生 input | `<input` | 21 个文件 | ~100 处 | AccountManage(36), BankManage(9), ReportTemplate(8) |
| 原生 textarea | `<textarea` | 3 个文件 | ~3 处 | ChatPanel, SkillsPanel, MemoryPanel/FilePanel |
| 状态标签 | `status-pill` / `badge` / `tag` | 17 个文件 | ~47 处 | AccountManage(6), ExceptionCenter(5), ReportTemplate(5) |
| loading | `loading` / `spinner` | 20 个文件 | ~76 处 | 散布广泛 |
| empty state | `empty` / `no-data` | 24 个文件 | ~89 处 | 散布广泛 |
| alert() | `alert(` | 17 个文件 | ~73 处 | AccountManage(27), ReportTemplate(7), ManualFlow(6) |
| confirm() | `confirm(` | 10 个文件 | ~17 处 | AccountManage(7), FilePanel(2) |
| common.css 引用 | `@import` | 25 个文件 | 25 处 | 全部页面 |

### 2.2 页面规模分布

| 页面类别 | 文件 | 行数 | 按钮数 | 表单 | 风险 |
|---------|------|------|--------|------|------|
| **占位/极简** | Placeholder(17), MajorBalance(14), MonthCheck(15), WeekReport(12), YearReport(13) | 17-17 | 0 | 0 | 极低 |
| **简单展示** | HomeQuick(43), HomeSystem(54), HomeTasks(62), OperationLog(96) | 43-96 | 3-6 | 2-4 | 低 |
| **报表页** | AccountBalance(115), ExpenseList(117), IncomeList(117), DailyReport(138) | 115-138 | 6 | 3-4 | 低 |
| **中等页面** | ManualMaintenance(154), BackupRestore(179), HomeDashboard(185), DataCleanup(202) | 154-202 | 3-16 | 2-5 | 低-中 |
| **报表+模板** | BankRule(25), CashJournal(478), BaseDataTable(478), TemplateReport | 25-478 | 4-8 | 4-7 | 中 |
| **复杂业务** | BankManage(~600), BankImport(~500), ManualFlow(~500), UploadPreview(~400) | 400-600 | 8-11 | 5-14 | 中-高 |
| **Agent 页面** | ChatPanel, FilePanel, MemoryPanel, SkillsPanel, SessionsPanel, SettingsPanel | 200-500 | 4-10 | 5-10 | 中 |
| **最复杂** | AccountManage(~1400), AIConfig(~400), ReportTemplate(~400), AgentDetail, AgentReview | 400-1400 | 9-45 | 20-50 | 高 |

---

## 3. 页面风险分层

### 低风险（建议第一批）

| 文件 | 行数 | 内容 | 改动量 |
|------|------|------|--------|
| HomeQuick | 43 | 快捷入口卡片，无表单无按钮 | loading → NSpin |
| HomeSystem | 54 | 系统提醒 + 最近操作表格 | loading → NSpin, empty → NEmpty |
| HomeTasks | 62 | 待办看板 + tag | loading → NSpin, tag → NTag, empty → NEmpty |
| OperationLog | 96 | 筛选区 + 表格 + 分页按钮 | select → NSelect, input → NDatePicker, btn → NButton, tag → NTag |
| AccountBalance | 115 | 日期筛选 + 下拉 + 报表按钮 | filter → NDatePicker/NSelect, btn → NButton |
| ExpenseList | 117 | 同上模式 | 同上 |
| IncomeList | 117 | 同上模式 | 同上 |
| DailyReport | 138 | 同上模式 | 同上 |

### 中风险（建议第二批）

| 文件 | 行数 | 原因 |
|------|------|------|
| DataCleanup | 202 | 确认弹窗 + 列表 + 按钮 |
| BackupRestore | 179 | 2 个确认弹窗 + 操作按钮 |
| HomeDashboard | 185 | 看板 + 卡片 + 多个 loading |
| ManualMaintenance | 154 | 修正操作 + select + 按钮 |
| CashJournal | 478 | 筛选 + 报表 + 导出 + 分页 |
| BaseDataTable | 478 | 通用数据表模板（被多页复用） |
| ExceptionCenter | ~300 | 异常处理 + 复杂筛选 |
| UploadPreview | ~400 | 预览 + 提交 + 状态 |
| BankImport | ~500 | 上传流程 + 预览 + 提交 |
| BankManage | ~600 | 表单弹窗 + 列表 + CRUD |
| ManualFlow | ~500 | 手工流水 + 多种输入 |

### 高风险（建议最后）

| 文件 | 行数 | 原因 |
|------|------|------|
| AccountManage | ~1400 | 4 个表单弹窗 + 复杂 CRUD + 大量 alert |
| AIConfig | ~400 | 配置管理 + JSON 编辑 + 多个确认 |
| ReportTemplate | ~400 | 模板编辑器 + 上传 + 复杂表单 |
| AgentDetail | ~300 | Agent 全功能页面 |
| AgentReview | ~300 | Artifact 审核流程 |
| Agent 子面板 ×6 | 200-500 | Agent 内部操作面板 |
| Login | ~100 | 登录表单（独立样式系统） |

---

## 4. UI-3 推荐迁移范围

### UI-3 允许迁移

1. **按钮 → NButton**：仅限低风险页面的筛选区按钮、导出/打印按钮、分页按钮
2. **日期输入 → NDatePicker**：报表页的 `<input type="date">`
3. **下拉选择 → NSelect**：报表页和 OperationLog 的 `<select class="filter">`
4. **状态标签 → NTag**：OperationLog、HomeTasks 的 `class="tag"`
5. **loading → NSpin**：首页子页面的 `<div class="loading-state">`
6. **empty state → NEmpty**：OperationLog、首页子页面的 `<div class="empty-state">`

### UI-3 不允许迁移

1. **表格 → NDataTable**（留到 UI-4）
2. **上传 → NUpload**（留到 UI-4）
3. **AccountManage** 4 个表单弹窗（留到 UI-4）
4. **AIConfig** JSON 编辑（留到 UI-4）
5. **ReportTemplate** 编辑器（留到 UI-4）
6. **common.css 大清理**（留到 UI-5）
7. **alert/confirm 全量替换**（留到 UI-5）
8. **Login 页面**（独立样式系统，留到 UI-5）
9. **Agent 内部面板**（留到 UI-4）
10. **Backend 代码**（不动）

---

## 5. 推荐拆 PR 策略

### UI-3A：首页子页面 loading + empty

范围：HomeQuick、HomeSystem、HomeTasks
改动：`loading-state` → NSpin，`empty-hint/empty-state` → NEmpty
风险：极低，3 个页面，无表单无提交

### UI-3B：报表页筛选区 + 操作按钮

范围：AccountBalance、ExpenseList、IncomeList、DailyReport
改动：`<input type="date">` → NDatePicker，`<select class="filter">` → NSelect，`btn` → NButton
风险：低，4 个页面结构几乎相同，纯筛选不涉及提交

### UI-3C：OperationLog 全面迁移

范围：OperationLog
改动：select → NSelect，input date → NDatePicker，btn → NButton，tag → NTag，empty → NEmpty，分页按钮 → NButton
风险：低，单页面，结构简单

### UI-3D：CashJournal 筛选区（如有余力）

范围：CashJournal 筛选区 + 底部分页
改动：同 3B 模式
风险：低-中，只改筛选区和分页，不动表格

### UI-3E 及以后留到后续阶段

- DataCleanup / BackupRestore 确认弹窗 → useDialog
- alert() → useMessage 批量替换
- 复杂表单弹窗
- Agent 面板
- common.css 清理

---

## 6. 第一批建议迁移文件

### UI-3A：首页 loading/empty（最推荐先做）

| 文件 | 当前问题 | 建议迁移组件 | 风险 | 验证方式 |
|------|----------|--------------|------|----------|
| HomeQuick.vue (43行) | `loading-state` + `loading-spinner` 手写 | NSpin | 极低 | 打开首页→快捷入口 tab |
| HomeSystem.vue (54行) | `loading-state` + `empty-hint` 手写 | NSpin + NEmpty | 极低 | 打开首页→系统提醒 tab |
| HomeTasks.vue (62行) | `loading-state` + `tag tag-warn` + `empty-hint` 手写 | NSpin + NTag + NEmpty | 极低 | 打开首页→待办追踪 tab |

### UI-3B：报表页筛选区

| 文件 | 当前问题 | 建议迁移组件 | 风险 | 验证方式 |
|------|----------|--------------|------|----------|
| AccountBalance.vue (115行) | 2 个 `<input type="date">` + 1 个 `<select>` + 3 个 `<button>` | NDatePicker + NSelect + NButton | 低 | 资金日报表→账户余额表→选日期+生成 |
| ExpenseList.vue (117行) | 同上 | 同上 | 低 | 资金日报表→支出明细表 |
| IncomeList.vue (117行) | 同上 | 同上 | 低 | 资金日报表→收入明细表 |
| DailyReport.vue (138行) | 同上 | 同上 | 低 | 资金日报表→现金日记账 |

### UI-3C：OperationLog

| 文件 | 当前问题 | 建议迁移组件 | 风险 | 验证方式 |
|------|----------|--------------|------|----------|
| OperationLog.vue (96行) | 2 个 `<select>` + 2 个 `<input date>` + 5 个 `<button>` + `tag-blue` + `empty-state` + 分页 | NSelect + NDatePicker + NButton + NTag + NEmpty | 低 | 系统设置→操作日志→筛选+翻页 |

---

## 7. 验证命令

```bash
cd F:/zhangfangxiansheng/frontend && npm run build

cd F:/zhangfangxiansheng
rg "<n-button|NButton|<n-input|NInput|<n-select|NSelect|<n-tag|NTag|<n-spin|NSpin|<n-empty|NEmpty|NDatePicker" frontend/src

rg "ant-design-vue|@ant-design|<a-[a-zA-Z]|a-button|a-modal|a-layout|ant-btn|ant-table|ant-form|\.ant-" frontend/src
```

---

## 8. 是否建议开始 UI-3

### ✅ 建议立即开始

**理由：**
1. UI-0/1/2 合并状态完好，基础稳固
2. 第一批目标（首页 3 个子页面）极低风险，无表单无提交
3. 第二批（4 个报表页）结构高度雷同，可批量迁移

**建议执行顺序：**
1. UI-3A（首页 3 页 loading/empty）→ 立即开始
2. UI-3B（4 个报表页筛选区）→ 紧跟
3. UI-3C（OperationLog）→ 第三步

**必须留到后续阶段：**

| 内容 | 建议阶段 |
|------|---------|
| 表格 → NDataTable | UI-4 |
| 上传 → NUpload | UI-4 |
| 复杂表单弹窗（AccountManage 等） | UI-4 |
| Agent 面板迁移 | UI-4 |
| alert() → useMessage 批量替换 | UI-5 |
| confirm() → useDialog 批量替换 | UI-5 |
| common.css 清理 | UI-5 |
| Login 页面迁移 | UI-5 |
