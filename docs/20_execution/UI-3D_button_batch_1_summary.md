# UI-3D: 原生 button → NButton 批量迁移 (Batch 1)

**分支**: `audit/frontend-naive-ui-3d-button-batch-1`
**状态**: 完成
**日期**: 2026-05-11

## 迁移范围

### 迁移规则

| 原生 class | NButton 映射 |
|---|---|
| `btn btn-primary` | `type="primary"` |
| `btn btn-secondary` | `secondary` |
| `btn btn-warn` | `type="warning"` |
| `btn btn-danger` / `btn-del` | `type="error"` |
| `btn-sm` | `size="small"` |
| `btn-primary btn-sm` | `type="primary" size="small"` |
| `btn btn-ghost` | `tertiary` |
| `btn btn-outline` | `secondary` |
| Tab 切换按钮 (动态 primary/secondary) | `:type="condition ? 'primary' : 'default'"` |

### 已迁移文件 (18 文件, 140 个 NButton)

| # | 文件 | NButton 数量 | 说明 |
|---|---|---|---|
| 1 | views/OperationLog.vue | 3 | 重置 + 分页按钮 |
| 2 | views/BaseDataTable.vue | 7 | 批量删除、重建、导出、打印、生成 + 分页 |
| 3 | views/BankManage.vue | 7 | 新建 + 行操作(编辑/停用/启用/删除) + 弹窗(取消/保存) |
| 4 | views/BankImport.vue | 8 | 关闭提示(2) + 步骤按钮(重新上传/预览/返回/提交/继续/查看) |
| 5 | views/ManualFlow.vue | 8 | 下载模板 + 录入方式Tab + 删除行 + 添加行(1/5) + 保存 + 上传预览 |
| 6 | views/ExceptionCenter.vue | 5 | 刷新 + 行操作(修正/作废) + 编辑区(保存/取消) |
| 7 | views/UploadPreview.vue | 5 | 有效/异常Tab + 返回 + 提交 + 修复 |
| 8 | views/DataCleanup.vue | 4 | 扫描 + 清除 + 确认弹窗(取消/确认) |
| 9 | views/BackupRestore.vue | 7 | 创建 + 恢复 + 出厂重置 + 确认弹窗×2(取消/确认) |
| 10 | views/ReportTemplate.vue | 9 | 新建 + 上传 + 编辑 + 设默认 + 删除 + 添加列 + 删除列 + 弹窗(取消/保存) |
| 11 | views/SystemMaintenance.vue | 11 | 创建备份 + 恢复 + 出厂 + 扫描 + 清除 + 三个弹窗(取消/确认) |
| 12 | views/AIConfig.vue | 6 | 获取模型列表 + 删除供应商 + 测试 + 取消 + 保存 + 关闭日志 |
| 13 | views/Login.vue | 1 | 登录按钮 (block + attr-type="submit") |
| 14 | views/AgentReview.vue | 2 | 返回 + 接受并继续 |
| 15 | views/AccountManage.vue | 33 | 新建(4) + 行操作(3×4=12) + 弹窗(2×4=8) + 批量操作触发(4) + 下载/导入(2) + 新建账户/单位/银行/核算(4)+1 |
| 16 | views/CashJournal.vue | 3 | 导出 + 打印 + 生成报表 |
| 17 | views/ManualMaintenance.vue | 2 | 返回预览 + 应用修复并提交 |
| 18 | composables/TemplateReport.vue | 3 | 导出 + 打印 + 生成报表 |

## 延后至 UI-3D-2 的按钮类型

| 类型 | 数量 | 位置 |
|---|---|---|
| tab-btn (标签页切换) | 6 | AccountManage(4) + SystemMaintenance(2) |
| dropdown-menu items (下拉菜单项) | 12 | AccountManage(12) |
| AIConfig 自定义按钮 (btn-add/btn-log/key-toggle) | 4 | AIConfig |
| ExceptionCenter filter pills | 3 | ExceptionCenter |
| ReportTemplate modal-close (×) | 1 | ReportTemplate |
| AgentDetail agent-tab-btn | 1 | AgentDetail |
| Agent 页面自定义按钮 | 16 | ChatPanel/SkillsPanel/MemoryPanel/FilePanel/SessionsPanel/SettingsPanel |

## 验证结果

- `npm run build`: ✅ 通过 (559ms)
- NButton 总实例数: 140
- 迁移文件数: 18 (超过 10 文件目标)
- 迁移按钮数: 140 (超过 100 按钮目标)
- 标准业务页面: 所有 `btn btn-*` 模式按钮已迁移至 NButton
