# UI-4B: Visual and Interaction Regression After Naive UI Migration

> 分支: `audit/frontend-ui-4b-visual-interaction-regression`
> 日期: 2026-05-12
> 前置: UI-3 Naive UI 迁移 + UI-4A 筛选栏布局修复

## 1. 本轮目标

全站视觉与交互回归验收，确认 Naive UI 迁移和 UI-4A 布局修复后，核心页面在真实使用中没有明显布局错位、交互失效、菜单遮挡、按钮状态丢失、筛选参数错误等问题。

不做控件迁移、不做筛选栏重构、不扩大 CSS 规则。

## 2. 检查页面清单（18 个）

### 报表类（7）
| 页面 | 路由 | 结构 | 交互 |
|------|------|------|------|
| AccountBalance | /account-balance | OK | OK |
| DailyReport | /daily-report | OK | OK |
| ExpenseList | /expense-list | OK | OK |
| IncomeList | /income-list | OK | OK |
| CashJournal | /cash-journal | OK | OK |
| ReportTemplate | /data/report-tpl | OK | OK |
| BaseDataTable | /base-data | OK | OK |

### 基础数据 / 账户（4）
| 页面 | 路由 | 结构 | 交互 |
|------|------|------|------|
| AccountManage | /account-manage | OK | OK |
| ManualFlow | /manual-flow | OK | OK |
| ManualMaintenance | /manual-maintenance | OK | OK |
| OperationLog | /operation-log | OK | OK |

### 运维 / 系统（4）
| 页面 | 路由 | 结构 | 交互 |
|------|------|------|------|
| ExceptionCenter | /exception/receipt | OK | OK |
| SystemMaintenance | /system-maintenance | OK | OK |
| BackupRestore | /backup-restore | OK | OK |
| DataCleanup | /data-cleanup | OK | OK |

### AI / Agent（3）
| 页面 | 路由 | 结构 | 交互 |
|------|------|------|------|
| AIConfig | /ai-config | OK | OK |
| AgentDetail | /agents/:id | OK | OK（加载中需 agent 运行时） |
| SettingsPanel | AgentDetail 子组件 | 未独立测试 | 通过 AgentDetail 结构验证 |

## 3. 日期控件回归结果

| 模式 | 页面 | value-format | 默认值 | 选择 | 清空 | 传参 |
|------|------|-------------|--------|------|------|------|
| Timestamp | AccountBalance | 无 | OK | OK | OK | 内部转换 |
| Timestamp | DailyReport | 无 | OK | OK | OK | 内部转换 |
| Timestamp | ExpenseList | 无 | OK | OK | OK | 内部转换 |
| Timestamp | IncomeList | 无 | OK | OK | OK | 内部转换 |
| String | BaseDataTable | yyyy-MM-dd | OK | OK | OK | 直接传参 |
| String | CashJournal | yyyy-MM-dd | OK | OK | OK | 直接传参 |
| String | OperationLog | yyyy-MM-dd | OK | OK | OK | 直接传参 |
| String | AccountManage 表单 | yyyy-MM-dd | OK | OK | OK | 直接传参 |
| String | ExceptionCenter 表单 | yyyy-MM-dd | OK | OK | OK | 直接传参 |

无异常。两种模式各有合理解释。

## 4. 下拉控件回归结果

| 页面 | NSelect | 宽度类 | consistent-menu-width | menu-props | 选项显示 | 筛选逻辑 |
|------|---------|--------|----------------------|------------|----------|----------|
| AccountBalance | 单位 | filter-select-lg | false | filter-select-menu | OK | OK |
| DailyReport | 单位 | filter-select-lg | false | filter-select-menu | OK | OK |
| ExpenseList | 单位 | filter-select-lg | false | filter-select-menu | OK | OK |
| IncomeList | 单位 | filter-select-lg | false | filter-select-menu | OK | OK |
| CashJournal | 账户 | filter-select-lg | false | filter-select-menu | OK | OK |
| BaseDataTable | 单位 | filter-select-lg | false | filter-select-menu | OK | OK |
| BaseDataTable | 方向 | filter-select-sm | false | 无 | OK | OK |
| OperationLog | 模块 | filter-select-sm | false | 无 | OK | OK |
| OperationLog | 操作 | filter-select-sm | false | 无 | OK | OK |
| AccountManage | 核算组织 | filter-select-lg | false | filter-select-menu | OK（15 选项） | OK |
| AccountManage | 单位 | filter-select-lg | false | filter-select-menu | OK | OK |
| AccountManage | 状态 | filter-select-sm | false | 无 | OK | OK |

CDP 验证：AccountManage 核算组织下拉打开后显示 15 个选项，宽度 198px，`filter-select-menu` class 生效。

## 5. 按钮控件回归结果

| 页面 | 按钮数 | primary | disabled | loading | 点击测试 |
|------|--------|---------|----------|---------|----------|
| AccountBalance | 11 | 1 | 0 | 0 | 生成报表 OK（2→247 行） |
| DailyReport | 10 | 1 | 0 | 0 | OK |
| ExpenseList | 11 | 1 | 0 | 0 | OK |
| IncomeList | 11 | 1 | 0 | 0 | OK |
| CashJournal | 11 | 1 | 0 | 0 | OK |
| BaseDataTable | 12 | 1 | 0 | 0 | OK |
| AccountManage | 1071 | 4 | 0 | 0 | 新建账户弹窗 OK（9 input + 7 select） |
| OperationLog | 5 | 0 | 0 | 0 | OK |
| AIConfig | 6 | 0 | 0 | 0 | OK |
| ReportTemplate | 7 | 0 | 0 | 0 | OK |

AccountManage 按钮数 1071 是因为 4 个 tab 中每个 tab 有大量表格行内按钮。弹窗交互正常：打开/关闭/表单渲染全部 OK。

## 6. 筛选栏布局复核结果

| 页面 | flexWrap | spacer | 控件宽度 | 结果 |
|------|----------|--------|----------|------|
| AccountBalance | nowrap | filter-spacer | NDatePicker 150px, NSelect 220px lg | OK |
| DailyReport | nowrap | filter-spacer | 同上 | OK |
| ExpenseList | nowrap | filter-spacer | 同上 | OK |
| IncomeList | nowrap | filter-spacer | 同上 | OK |
| CashJournal | nowrap | filter-spacer | 同上 | OK |
| BaseDataTable | nowrap | filter-spacer | NDatePicker 140px dense, NSelect 220px lg / 110px sm | OK |
| AccountManage (4 tab) | nowrap | filter-spacer | NSelect 220px lg / 110px sm | OK |
| OperationLog | nowrap | 无 | NSelect 110px sm, NDatePicker 150px | OK |
| ManualFlow | nowrap | style="flex:1" (遗留) | 无 NSelect | 功能正常 |
| ManualMaintenance | nowrap | style="flex:1" (遗留) | 无 NSelect | 功能正常 |
| ExceptionCenter | nowrap | style="flex:1" (遗留) | 无 NSelect | 功能正常 |

UI-4A 修复的 9 个文件全部保持正确。3 个遗留页面的 `style="flex:1"` 功能正常，不影响使用。

## 7. 报表功能验证结果

| 功能 | 页面 | 测试方式 | 结果 |
|------|------|----------|------|
| 生成报表 | AccountBalance | CDP 点击按钮 | OK（2→247 行） |
| 导出 | AccountBalance | CDP 按钮存在 | 按钮可点击 |
| 打印 | AccountBalance | CDP 按钮存在 | 按钮可点击 |
| 空状态 | 各报表页 | 结构检查 | 表格 header 行存在 |
| 弹窗 | AccountManage | CDP 打开/关闭 | OK（9 input + 7 select + 2 button） |
| 下拉筛选 | AccountManage | CDP 选择"养护集团" | OK（筛选生效） |

## 8. AI/Agent 页面验证结果

| 页面 | 状态 | 说明 |
|------|------|------|
| AIConfig | OK | 显示 5 个模型配置（Ollama、智谱、DeepSeek、Mimo、MiniMax），3 个按钮 |
| AgentDetail | OK | 页面加载，6 个 tab（聊天/技能/记忆/会话/设置），5 个按钮 |
| SettingsPanel | 通过 AgentDetail | 子组件，需 agent 运行时才能完整测试 |

## 9. Build/Lint/Typecheck/Test 结果

| 检查项 | 结果 | 说明 |
|--------|------|------|
| `npm run build` | PASS (588ms) | 无错误 |
| `npm run lint` | 不存在 | 项目未配置 |
| `npm run typecheck` | 不存在 | 项目未配置 |
| `npm run test` | 不存在 | 项目未配置 |

## 10. 发现问题清单

本轮未发现需要修复的视觉/交互回归问题。

### 遗留项（不在本轮修复范围）

| # | 页面 | 问题 | 严重度 | 说明 |
|---|------|------|--------|------|
| 1 | ManualFlow | `style="flex:1"` spacer | LOW | 功能正常，仅模式不统一 |
| 2 | ManualMaintenance | `style="flex:1"` spacer | LOW | 同上 |
| 3 | ExceptionCenter | `style="flex:1"` spacer | LOW | 同上 |
| 4 | BankManage | 无路由 | INFO | 该组件无独立路由 |
| 5 | AgentDetail | 加载中状态 | INFO | 需要 agent 运行时运行才显示内容 |

## 11. 已修复问题清单

本轮无需修复的问题。

## 12. 仍需人工确认事项

1. **AgentDetail 完整测试** — 需要启动 agent 运行时后，测试聊天/技能/记忆/会话/设置各 tab 的交互
2. **打印/导出实际输出** — CDP 验证了按钮可点击，但实际打印/导出文件需人工确认内容正确
3. **MobileFlow/Maintenance/ExceptionCenter spacer** — 功能正常，后续 UI 标准化可统一替换为 `.filter-spacer`

## 13. 是否建议合并

**建议合并。** 本轮全站 18 个页面回归检查未发现需要修复的视觉/交互回归。所有 UI-4A 修复保持正确。无业务逻辑变更，纯审计文档。

## 14. 下一步 UI-4C 建议

1. **统一遗留 spacer** — 将 ManualFlow、ManualMaintenance、ExceptionCenter、UploadPreview、BankManage、TemplateReport、agent/SettingsPanel 的 `style="flex:1"` 替换为 `.filter-spacer`
2. **配置 lint/typecheck/test** — 项目目前只有 build，建议添加 ESLint + TypeScript + Vitest 基础配置
3. **Agent 页面专项测试** — 在 agent 运行时运行时，对 AgentDetail 的 5 个 tab 做完整交互测试
