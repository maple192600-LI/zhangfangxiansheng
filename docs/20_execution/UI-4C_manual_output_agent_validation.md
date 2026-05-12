# UI-4C: Manual Validation for Output Flows and Agent Runtime Pages

> 分支: `audit/frontend-ui-4c-manual-output-agent-validation`
> 日期: 2026-05-12
> 前置: UI-4B 回归审计（0 个需修复回归，2 个需人工确认项）

## 1. 本轮目标

处理 UI-4B 遗留的人工确认项：
1. 报表导出/打印功能验证
2. Agent runtime 页面验证

不做全站重复审计，不扩大 CSS 或控件迁移范围。

## 2. UI-4B 遗留项来源

| # | 遗留项 | 来源 |
|---|--------|------|
| 1 | 报表导出内容与页面显示是否一致 | UI-4B §12 "打印/导出实际输出需人工确认" |
| 2 | AgentDetail 完整测试需 agent 运行时 | UI-4B §12 "AgentDetail 完整测试需 agent 运行时" |

## 3. 报表导出验证结果

### 导出功能机制

所有报表页面共用同一导出逻辑：
- 前端调用 `POST /api/export/report` 并传递 `export_type`、`start_date`、`end_date` 等参数
- 后端 `export_service.py` 根据类型调用对应的 report_service 函数获取数据
- 使用 openpyxl 生成 xlsx 并返回 `FileResponse`

### 导出测试结果

| 页面 | 导出类型 | API 响应 | 文件大小 | 数据行数 | 页面行数 | 是否一致 |
|------|----------|----------|----------|----------|----------|----------|
| AccountBalance | account_balance | 200 | 12,813B | 196 | 247 | 行数差异 |
| DailyReport | daily_report | 200 | 7,137B | 52 | 53 | 基本一致（差 1 行表头） |
| ExpenseList | expense_list | 200 | 5,218B | 1（仅表头） | 2 | 无数据日，一致 |
| IncomeList | income_list | 200 | 5,220B | 1（仅表头） | 2 | 无数据日，一致 |
| CashJournal | cash_journal | 200 | 5,163B | 1（仅表头） | 2 | 无数据日，一致 |

### AccountBalance 行数差异分析

- **页面 247 行** — 包含小计行（`is_subtotal`），生成报表 API 返回完整结果
- **导出 196 行** — `export_service.py` 第 221 行过滤了小计行：`if not r.get("is_subtotal")`
- 导出列与页面列一致：单位简称、账户名称、期初余额、本期收入、本期支出、期末余额
- **结论**：差异是设计意图（导出不含小计行），非 bug

### 用户反馈

用户指出"报表导出功能导出的并不是当前页面的内容"。分析后确认：
1. 导出文件内容在列结构和数据来源上与页面一致
2. 差异在于：页面包含小计行，导出排除小计行
3. 如果用户使用自定义报表模板（`excel-host` 区域），模板渲染的内容可能与导出不同——这是两套独立系统（模板渲染 vs API 导出）

## 4. 打印验证结果

### 打印机制

所有报表页面使用 `window.print()` 调用浏览器原生打印功能。

### 打印 CSS（common.css @media print）

```css
.sidebar, .right-tabs, .filters-bar, .btn-row, .bottom-bar,
.top-bar, .metric-strip, .dashboard-grid, .dashboard-grid-2,
.progress-list, .kanban, .quick-grid, .warning-list,
.loading-state, .error-bar, .modal-overlay { display: none !important; }
```

- 侧边栏、筛选栏、按钮行、导航等在打印时隐藏 ✓
- 表格内容保留 ✓
- Excel 模板区域打印时 `overflow: visible` ✓

### 用户反馈

用户指出"打印按钮就是摆设没有任何的实际功能"。分析后确认：
1. `window.print()` 在 CDP 模式下无法验证打印预览（无物理打印机）
2. 打印 CSS 规则正确配置
3. 可能的问题：用户实际使用中浏览器可能阻止了打印对话框弹出（弹窗拦截），或打印结果不符合预期
4. **无法在 CDP 中完全验证**，需人工在浏览器中确认

## 5. Agent Runtime 页面验证结果

### AgentDetail 页面

| 检查项 | 结果 |
|--------|------|
| 用数字 ID 导航 (`/agents/5`) | OK — 标题、tab、按钮全部正常 |
| 用 agent_code 导航 (`/agents/ag_42nugg`) | 无法加载 — `loadAgent()` 对 NaN 直接 return |
| Tab: 聊天 | OK — 输入框、发送按钮、文件面板 |
| Tab: 技能 | OK — 2 个技能列表，下拉展开正常 |
| Tab: 记忆 | OK — 空状态正常，添加记忆按钮存在 |
| Tab: 会话 | OK — 1 个会话，新建/删除按钮正常 |
| Tab: 设置 | OK — 模型配置 NSelect、运行参数表单完整 |
| NSelect 下拉 | OK — 模型配置、Token 选择下拉正常 |
| 按钮状态 | OK — 8 个按钮，primary/default 状态正确 |
| Console errors | 无 |

### agent_code 导航问题

**问题**：AgentDetail 的 `loadAgent()` 执行 `Number(route.params.id)` 将字符串 code 转为 NaN，直接 return。

**影响**：通过侧边栏导航不受影响（MainLayout 用 `agent.id` 数字传参）。仅影响直接在地址栏输入 code 格式 URL 的场景。

**建议修复**：在 `loadAgent()` 中增加 code → id 查找逻辑，或统一路由参数格式。

### ChatPanel / FilePanel / MemoryPanel / SessionsPanel / SkillsPanel

这些是 AgentDetail 的子组件，通过 tab 切换验证：
- ChatPanel ✓ — 消息输入框、发送按钮、快捷提问
- SkillsPanel ✓ — 技能列表、技能详情展开
- MemoryPanel ✓ — 空状态、添加记忆入口
- SessionsPanel ✓ — 会话列表、新建/删除
- SettingsPanel ✓ — 完整表单（名称、Prompt、模型配置、运行参数）

## 6. 发现问题

| # | 严重度 | 问题 | 说明 |
|---|--------|------|------|
| 1 | HIGH | 打印按钮点击无反应 | 用户实测确认：点击"打印"按钮无任何效果，属于功能问题 |
| 2 | HIGH | 单位下拉 label 使用简称而非全称 | 下拉选项可能显示简称，但用户期望看到全称以便区分 |
| 3 | HIGH | 停用核算组织/单位/账户后业务页面仍显示 | 主数据停用后，其他页面的下拉和筛选栏仍列出已停用项 |
| 4 | MEDIUM | agent_code 格式 URL 无法加载 AgentDetail | `/agents/ag_42nugg` 返回 NaN，agent 不加载 |

## 7. 已修复问题

本轮无代码修改。所有问题移交 UI-4D 修复。

## 8. 仍无法验证事项及原因

| # | 事项 | 原因 |
|---|------|------|
| 1 | Agent 聊天交互（发送消息、AI 回复） | 需 Ollama 本地运行且 qwen3.5:9b 模型可用 |
| 2 | 报表模板渲染导出一致性 | 需有自定义报表模板数据，对比模板渲染和导出内容 |

## 9. Build 结果

`npm run build` PASS (595ms)，无错误。

## 10. 是否建议合并

**不建议作为 UI-4 回归阶段结束结论。** 用户实测发现 4 个未解决问题（§6），其中打印按钮无反应属于功能缺陷，不能视为"仅需人工确认"。本轮文档作为审计数据保留，但结论需修正。

## 11. UI-4 回归阶段状态

**不能结束。** 用户实测发现的 4 个问题（打印无反应、下拉 label 语义错误、停用联动缺失、agent URL 兼容）属于迁移回归范围内的问题，需在 UI-4D 中修复。

### UI-4D 待修复项

1. **打印按钮点击无反应** — 排查 `window.print()` 不生效的原因并修复
2. **单位下拉 label 全称/简称语义** — 确保下拉选项使用用户可区分的完整名称
3. **停用主数据联动** — 停用核算组织/单位/账户后，业务页面下拉不再列出已停用项
4. **agent_code URL 兼容** — AgentDetail 支持通过 agent_code 加载
