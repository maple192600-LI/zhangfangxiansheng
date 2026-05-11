# UI-3C: 原生 date/select 控件批量迁移至 Naive UI

## 目标

将 `frontend/src` 内所有原生 `<input type="date">` 和原生 `<select>` 迁移为 Naive UI 的 `NDatePicker` 和 `NSelect`，实现两类控件在业务页面中零残留。

## 迁移文件清单

### date input 迁移（6 个文件 + 1 个 composable）

| 文件 | 迁移内容 |
|------|---------|
| `views/BaseDataTable.vue` | `filters.date_from`, `filters.date_to` |
| `views/CashJournal.vue` | `startDate`, `endDate` |
| `views/AccountManage.vue` | `accountForm.balance_date`, `bankForm.balance_date` |
| `views/ExceptionCenter.vue` | `form.business_date` |
| `views/ManualFlow.vue` | 表格行内 `business_date` 字段 |
| `views/OperationLog.vue` | `filters.start_date`, `filters.end_date` |
| `composables/TemplateReport.vue` | `startDate`, `endDate` |

### select 迁移（10 个文件 + 1 个 composable）

| 文件 | 迁移数量 |
|------|---------|
| `views/AccountManage.vue` | 20+ 个（筛选栏 7 个 + 表单弹窗 13+ 个） |
| `views/BaseDataTable.vue` | 2 个（entity_id, direction） |
| `views/CashJournal.vue` | 1 个（accountId，含 optgroup → 分组 options） |
| `views/ManualFlow.vue` | 1 个（entity_match_key，表格行内） |
| `views/OperationLog.vue` | 2 个（module, action） |
| `views/AIConfig.vue` | 2 个（protocol, model_name） |
| `views/BankManage.vue` | 2 个（filterStatus, form.status） |
| `views/ManualMaintenance.vue` | 2 个（entity, account，含 optgroup） |
| `views/ReportTemplate.vue` | 2 个（report_type, align） |
| `views/agent/SettingsPanel.vue` | 2 个（ai_config_id, tool permissions） |
| `composables/TemplateReport.vue` | 4 个（year, month, entity, year） |

## 迁移结果

### date input

- **原生 `<input type="date">` 残留：0**
- 全部使用 `NDatePicker` + `value-format="yyyy-MM-dd"` 保持字符串格式兼容
- 已迁入文件中 NDatePicker 的 `type="date"` 属性是组件配置，非原生 input

### select

- **原生 `<select>` / `<option>` 残留：0**
- 含 optgroup 的复杂选择器转换为 NSelect 分组 options 格式
- boolean 类型 value（true/false）保持原类型
- 筛选类 select 使用 clearable + placeholder 替代空选项

## 构建结果

- `npm run build` ✅ 成功（561ms）
- 无编译错误、无类型警告

## Ant Design 残留

- `frontend/src` 内零匹配 ✅

## Button 残留统计（UI-3D 准备）

共 26 个文件、约 220+ 个原生 `<button>`：

| 页面类型 | 文件 | 预估数量 |
|---------|------|---------|
| 主数据管理 | AccountManage | ~49 |
| 系统维护 | SystemMaintenance | ~18 |
| Agent | ChatPanel, SettingsPanel, SkillsPanel, MemoryPanel, FilePanel, SessionsPanel | ~42 |
| AI 配置 | AIConfig | ~13 |
| 报表模板 | ReportTemplate | ~10 |
| 备份恢复 | BackupRestore | ~10 |
| 银行导入 | BankImport | ~9 |
| 手工流水 | ManualFlow, ManualMaintenance | ~10 |
| 异常中心 | ExceptionCenter | ~8 |
| 基础数据/日记账 | BaseDataTable, CashJournal, OperationLog | ~13 |
| 银行维护 | BankManage | ~7 |
| 布局/导航 | MainLayout | ~7 |
| 其他 | Login, UploadPreview, AgentDetail, AgentReview, DataCleanup, TemplateReport | ~19 |

### UI-3D 建议

- 按页面类型分批：先低风险页面（筛选按钮、分页按钮），再高风险页面（表单弹窗、Agent 交互）
- 优先使用 `NButton` 替换
- 需特别注意按钮样式保持一致（主色、次色、危险色）
- Agent 相关页面（ChatPanel、SettingsPanel 等）按钮交互复杂，建议最后处理

## 风险说明

1. **NDatePicker clear 行为差异**：清除后值为 `null` 而非空字符串 `""`，所有 API 参数检查已兼容（`if (value)` 对 null 和 "" 都为 falsy）
2. **NSelect 分组选项格式**：optgroup 转为 NSelect group 格式，子选项结构 `{ type: 'group', label, key, children }` 已验证构建通过
3. **表格行内 NSelect/NDatePicker**：ManualFlow 和 ManualMaintenance 的行内控件使用 `size="tiny"` 保持紧凑
4. **AccountManage.vue 表单复杂度**：20+ 个 select 的选项类型（string/boolean/number）已逐一保持原类型
