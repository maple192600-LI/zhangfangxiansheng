# 聊天窗口升级计划 — 对标 ChatGPT/Codex 体验

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将账房先生的智能体聊天窗口升级到 ChatGPT/Codex 级别的交互体验：恢复被误删的按钮、Markdown 渲染、代码块高亮、对话历史侧边栏、新建对话、输入框自适应增高。

**Architecture:** 以 `ChatPanel.vue` 为核心，提取 `MessageActions.vue`（按钮栏）、`MessageBubble.vue`（Markdown 渲染）为子组件。在 `AgentDetail.vue` 中增加左侧对话列表侧边栏。Markdown 渲染使用 `marked` 库 + `highlight.js` 语法高亮。

**Tech Stack:** Vue 3 + Naive UI + marked (Markdown 解析) + highlight.js (代码高亮) + 现有 session API

---

## File Structure

```
frontend/src/
├── views/agent/
│   ├── ChatPanel.vue              # 主聊天面板（改造）
│   ├── ChatPanel/
│   │   ├── ToolCallBlock.vue      # 已有 - 工具调用展示
│   │   ├── ConfirmDialog.vue      # 已有 - 确认对话框
│   │   ├── MessageBubble.vue      # 新建 - Markdown 消息气泡
│   │   └── MessageActions.vue     # 新建 - 编辑/复制/重新生成按钮
│   ├── AgentDetail.vue            # 改造 - 增加对话侧边栏
│   └── SessionsPanel.vue          # 已有 - 会话管理
├── composables/
│   └── useMarkdown.js             # 新建 - Markdown 渲染 composable
└── package.json                   # 添加 marked + highlight.js
```

---

### Task 1: 恢复被误删的消息操作按钮

**Files:**
- Modify: `frontend/src/views/agent/ChatPanel.vue:29-30`

在 `msg-bubble` 结束标签后、`ToolCallBlock` 之前，插入消息操作按钮和编辑框 HTML。

- [ ] **Step 1: 插入消息操作按钮和编辑框**

在 `ChatPanel.vue` 第 30 行（`<div v-if="msg.content" ...>` 结束后）插入：

```html
          <!-- 消息操作按钮 -->
          <div v-if="msg.content && !streaming" class="msg-actions" :class="'actions-' + msg.role">
            <button v-if="msg.role === 'user'" class="msg-btn" @click="editMsg(msg)" title="编辑">✏️ 编辑</button>
            <button class="msg-btn" @click="copyMsg(msg)" title="复制">📋 {{ copyLabel }}</button>
            <button v-if="msg.role === 'assistant'" class="msg-btn" @click="regenerate(msg)" title="重新生成">🔄 重新生成</button>
          </div>

          <!-- 编辑框 -->
          <div v-if="editingMsgId === msg.id" class="msg-edit-box">
            <textarea v-model="editText" class="msg-edit-textarea" rows="3"></textarea>
            <div class="msg-edit-btns">
              <button class="msg-btn" @click="cancelEdit">取消</button>
              <button class="msg-btn msg-btn-ok" @click="submitEdit">发送</button>
            </div>
          </div>
```

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: `✓ built in XXXms`

---

### Task 2: 安装 Markdown 和代码高亮依赖

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装 marked 和 highlight.js**

Run: `cd frontend && npm install marked highlight.js`

- [ ] **Step 2: 验证安装**

Run: `cd frontend && npm run build`
Expected: `✓ built in XXXms`

---

### Task 3: 创建 Markdown 渲染 composable

**Files:**
- Create: `frontend/src/composables/useMarkdown.js`

- [ ] **Step 1: 创建 useMarkdown.js**

```js
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

marked.setOptions({
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true,
})

export function useMarkdown() {
  function renderMarkdown(text) {
    if (!text) return ''
    return marked.parse(text)
  }

  return { renderMarkdown }
}
```

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: `✓ built`

---

### Task 4: 创建 MessageBubble 子组件

**Files:**
- Create: `frontend/src/views/agent/ChatPanel/MessageBubble.vue`

- [ ] **Step 1: 创建 MessageBubble.vue**

封装 Markdown 渲染 + 代码块复制按钮。

```vue
<template>
  <div class="msg-bubble" :class="bubbleClass">
    <div v-if="role === 'user'" v-html="renderedContent"></div>
    <div v-else class="markdown-body" v-html="renderedContent"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useMarkdown } from '@/composables/useMarkdown'

const props = defineProps({
  content: { type: String, default: '' },
  role: { type: String, required: true },
})

const { renderMarkdown } = useMarkdown()

const bubbleClass = computed(() => ({
  'msg-user-bubble': props.role === 'user',
}))

const renderedContent = computed(() => {
  if (props.role === 'user') {
    // 用户消息：简单转义 + 换行
    return (props.content || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
  }
  // AI 消息：Markdown 渲染
  return renderMarkdown(props.content)
})
</script>

<style scoped>
.msg-user-bubble {
  background: #7f9b7a;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-bubble:not(.msg-user-bubble) {
  background: #f7f4ee;
  border: 1px solid #e7e0d5;
  border-bottom-left-radius: 4px;
  color: #333;
}

.markdown-body {
  line-height: 1.7;
  word-break: break-word;
}
.markdown-body :deep(p) { margin: 0 0 8px 0; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 4px 0; padding-left: 20px; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(a) { color: #5a8a55; text-decoration: underline; }

.markdown-body :deep(pre) {
  position: relative;
  background: #1e1e2e;
  border-radius: 8px;
  padding: 16px;
  margin: 8px 0;
  overflow-x: auto;
}
.markdown-body :deep(pre code) {
  font-size: 13px;
  line-height: 1.5;
  color: #cdd6f4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
.markdown-body :deep(code:not(pre code)) {
  background: #f0ede5;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #7f4b32;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid #e7e0d5;
  padding: 6px 10px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #f7f4ee;
  font-weight: 600;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid #7f9b7a;
  padding-left: 12px;
  margin: 8px 0;
  color: #5b635e;
}
</style>
```

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: `✓ built`

---

### Task 5: 创建 MessageActions 子组件

**Files:**
- Create: `frontend/src/views/agent/ChatPanel/MessageActions.vue`

- [ ] **Step 1: 创建 MessageActions.vue**

```vue
<template>
  <div v-if="show" class="msg-actions" :class="'actions-' + role">
    <button v-if="role === 'user'" class="msg-btn" @click="$emit('edit')" title="编辑">✏️ 编辑</button>
    <button class="msg-btn" @click="handleCopy" title="复制">📋 {{ copyLabel }}</button>
    <button v-if="role === 'assistant'" class="msg-btn" @click="$emit('regenerate')" title="重新生成">🔄 重新生成</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  show: { type: Boolean, default: true },
  role: { type: String, required: true },
  content: { type: String, default: '' },
})
defineEmits(['edit', 'regenerate'])

const copyLabel = ref('复制')

async function handleCopy() {
  try {
    await navigator.clipboard.writeText(props.content)
    copyLabel.value = '已复制'
    setTimeout(() => { copyLabel.value = '复制' }, 1500)
  } catch {
    copyLabel.value = '复制'
  }
}
</script>

<style scoped>
.msg-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  opacity: 0;
  transition: opacity .15s;
}
.msg-btn {
  padding: 2px 8px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #8c8680;
  font-size: 12px;
  cursor: pointer;
  transition: background .15s;
  font-family: inherit;
}
.msg-btn:hover { background: #f0ede5; color: #555; }
.actions-user { justify-content: flex-end; }
.actions-assistant { justify-content: flex-start; }
</style>
```

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: `✓ built`

---

### Task 6: 改造 ChatPanel.vue 使用新子组件

**Files:**
- Modify: `frontend/src/views/agent/ChatPanel.vue`

- [ ] **Step 1: 替换消息气泡和操作按钮**

在 ChatPanel.vue 中：
1. 导入 MessageBubble 和 MessageActions
2. 将 `<div v-if="msg.content" class="msg-bubble" v-html="fmtContent(msg.content)"></div>` 替换为 `<MessageBubble :content="msg.content" :role="msg.role" />`
3. 将操作按钮 HTML 替换为 `<MessageActions :show="!!msg.content && !streaming" :role="msg.role" :content="msg.content" @edit="editMsg(msg)" @regenerate="regenerate(msg)" />`
4. 删除 `fmtContent` 函数和相关的 `.msg-bubble` 样式（已迁移到 MessageBubble）
5. 删除 `.msg-actions`、`.msg-btn` 样式（已迁移到 MessageActions）

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: `✓ built`

---

### Task 7: 输入框自动增高

**Files:**
- Modify: `frontend/src/views/agent/ChatPanel.vue`

- [ ] **Step 1: 添加自动增高逻辑**

在 ChatPanel.vue 的 textarea 上添加 `@input="autoResize"` 方法：

```js
function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}
```

将 textarea 的 `rows="3"` 保持为最小高度，`max-height: 160px` 由 CSS 控制（已有）。

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: `✓ built`

---

### Task 8: AgentDetail 增加对话侧边栏 + 新建对话

**Files:**
- Modify: `frontend/src/views/AgentDetail.vue`

- [ ] **Step 1: 在 AgentDetail.vue 的聊天区域左侧添加对话列表**

改造 AgentDetail.vue 的布局：当 `activeTab === 'chat'` 时，在 ChatPanel 左侧显示一个窄的对话列表面板，包含：
- 当前 agent 的所有会话列表（标题 + 时间）
- 当前会话高亮
- 顶部有"新建对话"按钮
- 点击切换会话

利用已有的 `agentsStore.listSessions`、`agentsStore.createSession`、`agentsStore.deleteSession` API。

- [ ] **Step 2: 添加新建对话功能**

点击"新建对话"按钮：
1. 调用 `agentsStore.createSession(agent.id, '新会话')`
2. 切换到新会话
3. ChatPanel 自动加载空状态

- [ ] **Step 3: 构建验证**

Run: `cd frontend && npm run build`
Expected: `✓ built`

---

### Task 9: 改进上传文件/图片预览

**Files:**
- Modify: `frontend/src/views/agent/ChatPanel.vue`

当前问题：附件预览只有 emoji 图标 + 截断文件名，无缩略图/大小/图片预览。粘贴图片无预览。消息中上传文件只显示 `[已上传文件: xxx.png]` 文字。

- [ ] **Step 1: 增加图片预览和文件大小辅助函数**

在 ChatPanel.vue `<script setup>` 中添加：

```js
import { ref, nextTick, onMounted, watch, onBeforeUnmount } from 'vue'

function isImageFile(name) {
  return /\.(png|jpg|jpeg|gif|bmp|webp|tiff|tif)$/i.test(name)
}

function fmtSize(bytes) {
  if (!bytes || bytes <= 0) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const attachPreviews = ref({})

function generatePreviews() {
  // 清理旧的 ObjectURL
  Object.values(attachPreviews.value).forEach(url => URL.revokeObjectURL(url))

  const previews = {}
  for (const f of attachFiles.value) {
    if (isImageFile(f.name)) {
      previews[f.name + '_' + f.lastModified] = URL.createObjectURL(f)
    }
  }
  attachPreviews.value = previews
}

watch(attachFiles, () => generatePreviews(), { deep: true })
onBeforeUnmount(() => {
  Object.values(attachPreviews.value).forEach(url => URL.revokeObjectURL(url))
})
```

- [ ] **Step 2: 改进附件预览模板**

替换 `attach-bar` 区域（第 58-69 行）：

```html
    <!-- 附件预览 -->
    <div v-if="attachFiles.length > 0 || workspaceRefs.length > 0" class="attach-bar">
      <div v-for="(ref, i) in workspaceRefs" :key="'ws-'+i" class="attach-item attach-ws">
        <svg class="attach-ws-svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7f9b7a" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
        <span class="attach-name">{{ ref.name }}</span>
        <button class="attach-del" @click="removeWsRef(i)">✕</button>
      </div>
      <div v-for="(f, i) in attachFiles" :key="'f-'+i" class="attach-item" :class="{ 'attach-img-item': isImageFile(f.name) }">
        <img v-if="attachPreviews[f.name + '_' + f.lastModified]" :src="attachPreviews[f.name + '_' + f.lastModified]" class="attach-thumb" />
        <span v-else class="attach-icon">{{ fileIcon(f.name) }}</span>
        <div class="attach-info">
          <span class="attach-name">{{ f.name }}</span>
          <span v-if="f.size" class="attach-size">{{ fmtSize(f.size) }}</span>
        </div>
        <button class="attach-del" @click="removeAttach(i)">✕</button>
      </div>
    </div>
```

- [ ] **Step 3: 添加附件预览样式**

替换 `.attach-bar` 和 `.attach-item` 相关样式：

```css
/* 附件预览 */
.attach-bar {
  display: flex;
  gap: 8px;
  padding: 10px 24px;
  background: #faf8f3;
  flex-shrink: 0;
  flex-wrap: wrap;
  border-top: 1px solid #e7e0d5;
  align-items: flex-end;
}
.attach-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #fff;
  border: 1px solid #e7e0d5;
  border-radius: 10px;
  font-size: 12px;
  color: #435046;
  max-width: 240px;
  transition: border-color .15s;
}
.attach-item:hover { border-color: #b8ccb5; }
.attach-ws { border-color: #d7e5d4; background: #f2f7f0; }
.attach-ws-svg { flex-shrink: 0; }
.attach-icon { font-size: 14px; flex-shrink: 0; }
.attach-img-item { padding: 4px; }
.attach-thumb {
  width: 48px; height: 48px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
}
.attach-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.attach-name { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.attach-size { font-size: 11px; color: #8c8680; }
.attach-del {
  border: none; background: transparent; cursor: pointer;
  color: #aaa; font-size: 12px; padding: 0 2px; flex-shrink: 0;
}
.attach-del:hover { color: #c0392b; }
```

- [ ] **Step 4: 构建验证**

Run: `cd frontend && npm run build`
Expected: `✓ built`

---

### Task 10: 浏览器端到端验证

- [ ] **Step 1: 启动服务并登录**

Run: `cd backend && venv/Scripts/python.exe -m uvicorn main:app --port 8000`
Run: `cd frontend && npx vite --port 5173`

- [ ] **Step 2: 验证消息操作按钮**
- 打开任意智能体对话
- 发送一条消息
- 确认 AI 回复下方显示「复制」「重新生成」按钮
- 确认用户消息下方显示「编辑」「复制」按钮
- 点击编辑，修改内容后发送

- [ ] **Step 3: 验证 Markdown 渲染**
- 让 AI 回复包含代码块、列表、表格、加粗的消息
- 确认代码块有语法高亮
- 确认列表和表格正确渲染

- [ ] **Step 4: 验证对话侧边栏**
- 确认聊天界面左侧显示对话列表
- 点击不同对话切换
- 点击"新建对话"创建新会话

- [ ] **Step 5: 验证输入框自适应**
- 在输入框输入多行文本
- 确认输入框随内容自动增高，最高不超过 160px

- [ ] **Step 6: 验证上传文件预览**
- 点击上传按钮选择图片文件
- 确认附件预览区显示图片缩略图 + 文件名 + 文件大小
- 点击上传按钮选择文档文件（Excel/PDF）
- 确认附件预览区显示文件类型图标 + 文件名 + 文件大小
- 在输入框中粘贴截图
- 确认粘贴的图片显示缩略图预览
