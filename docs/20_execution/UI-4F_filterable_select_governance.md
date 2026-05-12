# UI-4F：全仓下拉筛选框文字搜索统一治理

> 阶段：UI-4F | 分支：`audit/frontend-ui-4d-print-masterdata-linkage-fix` | 日期：2026-05-12

## 背景

所有下拉型筛选框依赖被动选择，选项多时（51 个单位、195 个账户、9 种账户类型等）用户无法快速定位。Naive UI 的 `filterable` prop 默认只匹配 label，但很多场景需要搜索隐藏字段（全称、编号、银行名等）。

## 核心原则

- 选项 >3 的 NSelect 必须支持 filterable
- 选项 ≤3 的统一加 filterable，不破坏交互
- label 只显示单位全称（不混入简称）
- 搜索覆盖隐藏字段时，必须使用自定义 `:filter` 函数

## 统一搜索组件

### MasterEntitySelect（`frontend/src/components/MasterEntitySelect.vue`）

- 用途：所有报表页的单位筛选（6 个日报表页 + 5 个综合报表页 via TemplateReport）
- label：显示单位全称 `entity_full_name`
- 搜索范围（自定义 filter）：
  - `entity_full_name`（单位全称）
  - `entity_display_name`（UI 展示名）
  - `entity_name`（向后兼容字段）
  - `entity_short_name`（单位简称）
- 搜索规则：`toLowerCase().includes(pattern)`

### MasterAccountSelect（`frontend/src/components/MasterAccountSelect.vue`）

- 用途：CashJournal 账户筛选（后续其他账户筛选也可复用）
- 分组：按单位全称分组
- 子项 label：`account_code + account_alias`
- 搜索范围（自定义 filter）：
  - 分组层：单位全称、entity_display_name、entity_name
  - 子项层：account_code、account_alias、account_type、bank_name、单位全称
- 搜索规则：`toLowerCase().includes(pattern)`

## 自定义 filter 的页面内 NSelect

### AccountManage.vue（3 处 entityNameFilter）

| 位置 | 绑定 | label 内容 |
|------|------|-----------|
| 账户列表 → 单位筛选 | `entityFilterSelectOptions` + `:filter="entityNameFilter"` | 单位全称 |
| 新建/编辑账户 → 所属单位 | `entityGroupOptions` + `:filter="entityNameFilter"` | 全称（编码） |
| 新建/编辑银行账户 → 所属单位 | `entityGroupOptions` + `:filter="entityNameFilter"` | 全称（编码） |

`entityNameFilter` 搜索范围：`e.name`（全称）+ `e.short_name`（简称）

## 仅默认 label 搜索的 NSelect

这些 NSelect 的 label 已包含所有可搜索信息，无需自定义 filter：

| 页面 | 下拉 | 选项数 |
|------|------|--------|
| OperationLog | 模块筛选 | 7 |
| OperationLog | 操作筛选 | 8 |
| AccountManage | 核算组织筛选（3处） | 动态 |
| AccountManage | 状态筛选（4处） | 3 |
| AccountManage | 账户类型（2处） | 9/4 |
| AccountManage | 资金类型（2处） | 6/4 |
| AccountManage | 是否/录入方式（8处） | 2 |
| BaseDataTable | 方向筛选 | 2 |
| TemplateReport | 年份/月份 | 4/12 |
| BankManage | 状态筛选 | 3 |
| ManualFlow | 单位选择 | 动态 |
| ManualMaintenance | 单位/账户修复 | 动态 |
| AgentCreateModal | 模板/AI配置 | 3/动态 |
| AIConfig | 协议/模型 | 3/动态 |
| SettingsPanel | AI配置/工具权限 | 动态/3 |
| ReportTemplate | 报表类型/对齐 | 8/3 |

## 文件清单

### 新增
- `frontend/src/components/MasterAccountSelect.vue`

### 修改
- `frontend/src/components/MasterEntitySelect.vue` — filterable + 自定义 filter + label 改全称
- `frontend/src/views/CashJournal.vue` — NSelect → MasterAccountSelect
- `frontend/src/views/OperationLog.vue` — module/action 加 filterable
- `frontend/src/views/AccountManage.vue` — 26 处 NSelect 加 filterable + 3 处自定义 filter + label 改全称
- `frontend/src/views/BaseDataTable.vue` — 方向加 filterable
- `frontend/src/composables/TemplateReport.vue` — 年份/月份加 filterable
- `frontend/src/views/BankManage.vue` — 状态加 filterable
- `frontend/src/views/ManualFlow.vue` — 单位加 filterable
- `frontend/src/views/ManualMaintenance.vue` — 单位/账户加 filterable
- `frontend/src/components/agent/AgentCreateModal.vue` — 模板/AI配置加 filterable
- `frontend/src/views/AIConfig.vue` — 协议/模型加 filterable
- `frontend/src/views/agent/SettingsPanel.vue` — AI配置/权限加 filterable
- `frontend/src/views/ReportTemplate.vue` — 报表类型/对齐加 filterable

## 验证结果

| 验证项 | 方法 | 结果 |
|--------|------|------|
| 全仓 NSelect = filterable | grep 计数 | 47 = 47，零遗漏 |
| 前端构建 | `npx vite build` | 通过 |
| MasterEntitySelect 显示全称 | CDP 检查选项文本 | "山西喜跃发道路建设养护集团有限公司" |
| 单位简称搜索（养护） | CDP 直接调 filter 函数 | filter("养护", option) = true |
| 单位全称搜索（山西） | CDP 直接调 filter 函数 | filter("山西", option) = true |
| 账户编号搜索（ZH） | CDP 直接调 filter 函数 | filter("ZH", option) = true |
| 账户别名搜索 | CDP 直接调 filter 函数 | filter(alias前3字, option) = true |
| 账户类型搜索 | CDP 直接调 filter 函数 | filter("基本户", option) = true |
| 单位全称搜账户 | CDP 直接调 filter 函数 | filter(全称前4字, option) = true |
| AccountManage 单位下拉显示全称 | CDP 检查选项文本 | "山西喜跃发..."（非简称） |
| AccountManage 3 处 entityNameFilter | 代码审查 | 已绑定 :filter="entityNameFilter" |
