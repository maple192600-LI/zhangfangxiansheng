# UI-4A: 筛选栏布局标准化修复

> 分支: `audit/frontend-ui-4a-filter-bar-layout-fix`
> 日期: 2026-05-12
> 前置: UI-3 Naive UI 迁移完成后，遗留的内联样式导致筛选栏控件宽度不一致

## 问题

Naive UI 迁移后，9 个页面的筛选栏存在以下遗留问题：

1. **控件宽度不一致** — NDatePicker 有 `width:150px`、`width:160px`；NSelect 有 `min-width:130px`、`min-width:140px`、`min-width:160px`、`min-width:180px`、`max-width:140px`、`max-width:150px`
2. **spacer 不统一** — 使用 `style="flex:1"` 的 inline div 而非 CSS 类
3. **flex-wrap 设置不当** — 部分页面 `flex-wrap: wrap` 导致控件换行
4. **NSelect 下拉菜单宽度** — 固定宽度后，下拉菜单可能被截断，长选项无法完整显示

## 修改内容

### common.css — 统一筛选栏 CSS 规则

| 类名 | 用途 | NDatePicker |
|------|------|-------------|
| `.filters-bar` | 默认单行筛选栏 | 150px |
| `.filters-bar-dense` | 高密度（控件多的页面） | 140px |
| `.filters-bar-multi` | 允许多行（备选） | 150px |

新增 `.filter-spacer` 类替代 `style="flex:1"` 的 inline spacer。
默认改为 `flex-wrap: nowrap`（单行不换行）。

### NSelect 本体宽度与下拉菜单宽度分离策略

**核心思路**：NSelect 控件本体固定宽度（避免撑爆 flex 布局），下拉菜单允许更宽（完整显示选项文本），但限制最大宽度防止无限撑宽页面。

#### 本体宽度类（在 common.css 中，scoped 样式内可用）

| 类名 | 宽度 | 适用场景 |
|------|------|----------|
| `.filter-select` | 180px | 普通筛选（当前未使用，备选） |
| `.filter-select-sm` | 110px | 短枚举（状态、方向、布尔） |
| `.filter-select-lg` | 220px | 长文本（单位、账户、核算组织等用户可命名对象） |

#### 下拉菜单规则（在 theme.css 中，全局生效）

Naive UI 的 Select 下拉菜单通过 teleport 渲染到 body 级别，`<style scoped>` 无法覆盖。因此 `.filter-select-menu` 规则定义在全局的 `frontend/src/styles/theme.css` 中：

```css
.filter-select-menu {
  min-width: 180px !important;
  max-width: 480px !important;
}
```

#### NSelect 分类标准

| 类型 | 数据特征 | 宽度类 | menu-props | 示例 |
|------|----------|--------|------------|------|
| 短枚举 | 固定选项，文本 < 8 字 | `filter-select-sm` | 不需要 | 状态、方向、布尔 |
| 普通 | 动态选项，文本 < 15 字 | `filter-select` | 可选 | 简单分类 |
| 长文本 | 用户命名对象，可能 > 15 字 | `filter-select-lg` | `filter-select-menu` | 单位、账户、核算组织 |

#### consistent-menu-width=false 使用说明

所有筛选栏 NSelect 统一添加 `:consistent-menu-width="false"`，使下拉菜单宽度独立于控件本体宽度：

- 控件本体保持固定宽度 → 布局不跳动
- 下拉菜单根据选项内容自适应宽度 → 长选项完整显示
- 配合 `.filter-select-menu` 的 `max-width: 480px` → 极端长文本截断

#### 极端长文本处理策略

1. 菜单宽度上限 480px（约 30 个中文字符）
2. 超过 480px 的文本由 Naive UI 内部自动省略（ellipsis）
3. 闭合状态下控件本体自动省略超长选中值（NSelect 内置行为）
4. 不额外添加 title/tooltip——Naive UI 的 ellipsis 行为对用户已足够直观

### 页面级修改

| 页面 | NSelect 分类 | 变更 |
|------|-------------|------|
| AccountBalance | 单位 → lg | 加 class + menu-props + consistent-menu-width |
| DailyReport | 单位 → lg | 同上 |
| ExpenseList | 单位 → lg | 同上 |
| IncomeList | 单位 → lg | 同上 |
| CashJournal | 账户 → lg | 同上 |
| OperationLog | 模块/操作 → sm | 加 class + consistent-menu-width |
| BaseDataTable | 单位 → lg, 方向 → sm | 加 class + menu-props + consistent-menu-width |
| AccountManage tab1 | 核算组织 → lg, 单位 → lg, 状态 → sm | 同上 |
| AccountManage tab2 | 状态 → sm | 加 class + consistent-menu-width |
| AccountManage tab3 | 核算组织 → lg, 状态 → sm | 加 class + menu-props + consistent-menu-width |
| AccountManage tab4 | 状态 → sm | 加 class + consistent-menu-width |

## 验证结果

### Build

`npm run build` 通过，无错误。

### Grep 检查

| 检查项 | 结果 |
|--------|------|
| `style="flex:1"` 在 9 个文件中 | 无匹配（已清理） |
| inline width 约束在筛选栏 NSelect 中 | 无匹配（已替换为 class） |
| 其他文件中的 `style="flex:1"` | 7 个文件（不在本轮范围，未修改） |

### CDP 验证

#### 筛选栏布局（8 个页面）

| 页面 | flexWrap | NSelect 宽度 | filter-spacer | 结果 |
|------|----------|-------------|---------------|------|
| AccountBalance | nowrap | 220px lg | 1162px flex | OK |
| DailyReport | nowrap | 220px lg | 1162px flex | OK |
| ExpenseList | nowrap | 220px lg | 1162px flex | OK |
| IncomeList | nowrap | 220px lg | 1162px flex | OK |
| CashJournal | nowrap | 220px lg | 1166px flex | OK |
| OperationLog | nowrap | 110px sm | 无（不需要） | OK |
| AccountManage (accounts) | nowrap | 220px lg / 110px sm | 885px flex | OK |
| BaseDataTable | nowrap | 220px lg / 110px sm | 808px flex | OK |

#### 下拉菜单宽度验证

| 页面 | 下拉类型 | 控件宽度 | 菜单宽度 | min-width | max-width | filter-select-menu | 结果 |
|------|----------|----------|----------|-----------|-----------|-------------------|------|
| AccountBalance | 单位 (lg) | 220px | 198px | 180px | 480px | 有 | OK |
| AccountManage | 核算组织 (lg) | 220px | 198px | 180px | 480px | 有 | OK |
| AccountManage | 状态 (sm) | 110px | 99px | — | — | 无 | OK |

- lg 类型：菜单 min-width 180px 生效，max-width 480px 限制生效
- sm 类型：无 menu-props，自适应内容宽度，短枚举显示完整

### AccountManage 4 个 tab 检查

| Tab | 筛选栏 | NSelect 分类 | 处理 |
|-----|--------|-------------|------|
| accounts | filters-bar-dense | 核算组织 lg + 单位 lg + 状态 sm | 全部修复 |
| divisions | filters-bar | 状态 sm | 全部修复 |
| entities | filters-bar | 核算组织 lg + 状态 sm | 全部修复 |
| banks | filters-bar | 状态 sm | 全部修复 |

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

1. `frontend/src/views/common.css` — 筛选栏 CSS + NSelect 本体宽度类
2. `frontend/src/styles/theme.css` — NSelect 下拉菜单全局规则
3. `frontend/src/views/AccountBalance.vue`
4. `frontend/src/views/DailyReport.vue`
5. `frontend/src/views/ExpenseList.vue`
6. `frontend/src/views/IncomeList.vue`
7. `frontend/src/views/CashJournal.vue`
8. `frontend/src/views/OperationLog.vue`
9. `frontend/src/views/BaseDataTable.vue`
10. `frontend/src/views/AccountManage.vue`（4 个 tab）
11. `docs/20_execution/UI-4A_filter_bar_layout_fix.md` — 本文档
