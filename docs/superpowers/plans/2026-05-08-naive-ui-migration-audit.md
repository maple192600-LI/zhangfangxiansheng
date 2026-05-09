# 前端升级代码审计与 BUG 查找计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 审计「替换 Ant Design Vue → Naive UI + 双皮肤 + 拆分大文件」变更，找出 BUG、逻辑遗漏、样式丢失、安全隐患。

**Architecture:** 本次变更涉及 9 个修改文件 + 8 个新增文件。审计按 4 条链路展开：主题链路（App.vue → theme store → theme 文件 → MainLayout 切换按钮）、AccountManage 拆分链路（index.vue → 4 个子组件 → 路由）、ChatPanel 拆分链路（主文件 → ToolCallBlock + ConfirmDialog）、以及全局影响（构建产物、未清理的残留引用）。

**Tech Stack:** Vue 3 + Vite 8 + Naive UI + Pinia + CSS Variables

---

## Task 1: 审计主题链路（App.vue → theme store → theme 配置 → MainLayout 切换按钮）

**Files:**
- `frontend/src/App.vue` (全文)
- `frontend/src/stores/theme.js` (全文)
- `frontend/src/theme/zhangfang.js` (全文)
- `frontend/src/theme/naive-default.js` (全文)
- `frontend/src/layouts/MainLayout.vue` (变更部分)

审计项：

- [ ] **Step 1: 检查 App.vue 中 NConfigProvider 的正确性**
  - 验证 `themeOverrides` 是否正确绑定
  - 验证 `NMessageProvider` 是否在 `NConfigProvider` 内部
  - 验证 Naive UI 的 `useMessage` 是否能在子组件中正常使用（需确认 `NMessageProvider` 是必要的）
  - 检查是否有 `NDialogProvider` 等其他 Provider 缺失

- [ ] **Step 2: 检查 theme store 逻辑**
  - 验证 `computed` 返回的 themeOverrides 是否响应式
  - 验证 `localStorage` 读写是否正确（键名 `skin`，值 `zhangfang`/`naive`）
  - 验证默认值（首次访问无 localStorage 时）是否为 `zhangfang`
  - 验证 `toggleSkin` 切换逻辑是否只在两个皮肤之间切换

- [ ] **Step 3: 检查 zhangfang.js 主题映射完整性**
  - 对比 `theme.css` 中所有 CSS 变量，确认每个变量都有对应的 Naive UI 映射
  - 重点检查：警告色、成功色、信息色是否完整映射
  - 检查 Naive UI 的 `themeOverrides` 属性名是否拼写正确（参考 Naive UI 官方文档的 Token 列表）

- [ ] **Step 4: 检查 MainLayout.vue 中皮肤切换按钮**
  - 验证 `useThemeStore` 是否正确引入和初始化
  - 验证 `toggleSkin` 绑定是否正确
  - 验证 `.skin-toggle` 样式是否有 `!important` 冲突
  - 检查按钮是否在所有路由页面都可见（因为 MainLayout 是所有页面的父布局）

- [ ] **Step 5: 记录发现的 BUG**
  - 用表格格式列出：BUG编号、严重程度（CRITICAL/HIGH/MEDIUM/LOW）、描述、所在文件:行号

---

## Task 2: 审计 AccountManage 拆分链路（index.vue → 4 个子组件 → 路由 → API 调用）

**Files:**
- `frontend/src/views/AccountManage/index.vue` (全文)
- `frontend/src/views/AccountManage/AccountList.vue` (全文)
- `frontend/src/views/AccountManage/DivisionList.vue` (全文)
- `frontend/src/views/AccountManage/EntityList.vue` (全文)
- `frontend/src/views/AccountManage/BankAccountList.vue` (全文)
- `frontend/src/router/index.js` (AccountManage 行)
- `frontend/src/api/master.js` (检查 API 引用是否存在)

审计项：

- [ ] **Step 1: 检查 index.vue 数据加载和传递**
  - 验证 `loadAll()` 加载 divisions、entities、accounts 三组数据是否完整
  - 对比原始 `AccountManage.vue` 的 `loadAll()`：原版还加载了 `banks`，新版是否遗漏
  - 验证 `v-if` 替代 `v-show` 是否影响子组件生命周期（每次切 tab 都会重新挂载/销毁）
  - 检查 `@refresh="loadAll"` 是否在所有子组件的 emit 中正确绑定

- [ ] **Step 2: 检查 AccountList.vue 数据流**
  - 验证 props 定义类型是否正确（Array、default () => []）
  - 验证 `filteredEntities` 计算属性是否使用 `props.allEntities` 而非直接引用
  - 检查 `emit('refresh')` 是否在所有数据变更操作后触发（save、toggleStatus、batchAction、doImport）
  - 检查 `filterDivision` 变更时的 `@change="$emit('refresh')"` 是否合理——筛选操作不应触发重新加载

- [ ] **Step 3: 检查 DivisionList.vue 和 EntityList.vue**
  - 验证删除操作（deleteDiv、deleteEnt）后的 emit('refresh') 是否存在
  - 检查批量操作后的 selectedIds 清空逻辑

- [ ] **Step 4: 检查 BankAccountList.vue**
  - 验证银行账户的筛选逻辑是否与原版一致
  - 检查 `BANK_ACCOUNT_TYPE_FILTER` 常量是否与原版 `BANK_ACCOUNT_TYPES` 一致
  - 验证删除操作调用 `api.batchActionAccounts` 而非 `api.deleteAccount` 是否正确

- [ ] **Step 5: 检查路由配置**
  - 验证 `import('@/views/AccountManage/index.vue')` 路径是否正确
  - 确认旧文件 `AccountManage.vue` 已删除
  - 检查是否有其他文件引用旧路径 `AccountManage.vue`

- [ ] **Step 6: 检查 API 引用完整性**
  - 在所有 5 个新文件中 grep 所有 `api.xxx` 调用
  - 验证 `frontend/src/api/master.js` 中是否存在对应的导出函数
  - 检查 `fmtAmt` 和 `todayLocalDate` 工具函数是否存在

- [ ] **Step 7: 记录发现的 BUG**

---

## Task 3: 审计 ChatPanel 拆分链路（主文件 → ToolCallBlock → ConfirmDialog）

**Files:**
- `frontend/src/views/agent/ChatPanel.vue` (全文)
- `frontend/src/views/agent/ChatPanel/ToolCallBlock.vue` (全文)
- `frontend/src/views/agent/ChatPanel/ConfirmDialog.vue` (全文)

审计项：

- [ ] **Step 1: 检查 ToolCallBlock.vue 接口正确性**
  - 验证 props 名称和类型是否与主文件传参一致
  - 验证 `@toggle` 事件的 emit 是否正确
  - 检查 `parsedCall` 在 JSON 解析失败时的 fallback
  - 检查 `fmtResult` 在 `props.toolResult` 为 null 时的行为

- [ ] **Step 2: 检查 ConfirmDialog.vue 接口正确性**
  - 验证 v-model:reply-text 的双向绑定语法是否正确
  - 检查 `@submit-reply` 事件是否正确绑定到 Enter 键
  - 检查输入框的 input 事件处理 `$emit('update:replyText', $event.target.value)` 是否正确

- [ ] **Step 3: 检查 ChatPanel.vue 主文件的清理完整性**
  - 搜索是否还残留已迁移到子组件的函数（toolName、toolIcon、toolStatus、fmtArgs、fmtResult）
  - 搜索是否还残留已迁移到子组件的 CSS 类（.tool-block、.confirm-overlay 等）
  - 验证 import 路径 `'./ChatPanel/ToolCallBlock.vue'` 和 `'./ChatPanel/ConfirmDialog.vue'` 是否正确

- [ ] **Step 4: 检查 ChatPanel.vue 中被修改的模板区域**
  - 验证 ToolCallBlock 替换区域的上下文 HTML 结构是否完整
  - 验证 ConfirmDialog 替换区域是否有标签缺失或多余
  - 检查 `<!-- 输入区 -->` 注释后的 `<div class="chat-input-bar">` 标签是否正确

- [ ] **Step 5: 记录发现的 BUG**

---

## Task 4: 全局影响审计（残留引用、构建产物、安全检查）

**Files:**
- `frontend/package.json`
- `frontend/src/main.js`
- `frontend/src/styles/theme.css`
- 构建产物（dist/）

审计项：

- [ ] **Step 1: 搜索 Ant Design Vue 残留引用**
  - grep 整个 frontend/src 目录中的 `ant-design-vue`、`ant-`、`Antd`、`a-button`、`a-table` 等关键词
  - 检查 package.json 中是否已完全移除 ant-design-vue 依赖

- [ ] **Step 2: 检查构建产物**
  - 验证 `npm run build` 无报错
  - 对比迁移前后的包体积，确认 ant-design-vue 相关代码已被移除
  - 检查是否有新的 chunk 体积异常

- [ ] **Step 3: 安全检查**
  - 验证 theme store 中 localStorage 的键名和值没有敏感信息泄露
  - 检查 Naive UI 的 `NConfigProvider` 是否有任何已知的安全问题
  - 验证 `themeOverrides` 注入不会导致 XSS（如果值来自用户输入）

- [ ] **Step 4: 运行项目 guard 检查**
  - 执行 `check_no_parallel_implementations.py`（确保没有重复实现）
  - 执行 `check_product_purity.py`（确保没有混入不该有的代码）
  - 执行 `check_api_inventory.py`（确保 API 路由完整）

- [ ] **Step 5: 记录发现的 BUG**

---

## Task 5: 汇总审计报告并修复所有发现的问题

- [ ] **Step 1: 汇总所有 BUG 列表**
  - 按 CRITICAL > HIGH > MEDIUM > LOW 排序
  - 标注每个 BUG 的修复方案

- [ ] **Step 2: 修复所有 CRITICAL 和 HIGH 级别 BUG**
  - 逐个修复，每个修复后运行 `npm run build` 验证

- [ ] **Step 3: 修复所有 MEDIUM 级别 BUG**

- [ ] **Step 4: 最终构建验证**
  - `npm run build` 确认无报错
  - `npm run dev` 启动确认页面可正常访问

- [ ] **Step 5: 输出最终审计报告**
