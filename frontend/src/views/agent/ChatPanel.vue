<template>
  <div
    class="chat-panel"
    :class="{ 'chat-drag-over': dragOver }"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- 拖拽提示层 -->
    <div v-if="dragOver" class="chat-drop-zone">
      <div class="drop-hint">
        <span class="drop-icon">📥</span>
        <span>释放文件，发送给智能体处理</span>
        <span class="drop-sub">支持图片、Excel、PDF、Word、PPT、CSV 等文件</span>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="chat-empty">
        <div class="empty-icon">💬</div>
        <div class="empty-title">开始和「{{ agent.display_name }}」对话</div>
        <div class="empty-hint">试试上传一个银行流水文件，然后说"帮我解析这个文件"</div>
      </div>

      <div v-for="msg in messages" :key="msg.id" class="chat-msg" :class="'msg-' + msg.role">
        <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
        <div class="msg-body">
          <!-- Folded first user message (system context) -->
          <template v-if="foldFirstUserMsg && msg.role === 'user' && isFirstUserMsg(msg) && !forceUnfoldedMsgIds[msg.id]">
            <div class="msg-bubble msg-folded" @click="unfoldMsg(msg.id)">
              <span class="fold-label">{{ foldLabel }}</span>
              <span class="fold-hint">（点击展开）</span>
            </div>
          </template>
          <!-- Normal message bubble -->
          <template v-else>
            <div v-if="msg.content" class="msg-bubble" v-html="fmtContent(msg.content)"></div>
          </template>

          <!-- 消息操作按钮 -->
          <div v-if="msg.content && !streaming" class="msg-actions" :class="'actions-' + msg.role">
            <NButton v-if="msg.role === 'user'" class="msg-btn" quaternary @click="editMsg(msg)" title="编辑">✏️ 编辑</NButton>
            <NButton class="msg-btn" quaternary @click="copyMsg(msg)" title="复制">📋 {{ copyLabel }}</NButton>
            <NButton v-if="msg.role === 'assistant'" class="msg-btn" quaternary @click="regenerate(msg)" title="重新生成">🔄 重新生成</NButton>
          </div>

          <!-- 编辑框 -->
          <div v-if="editingMsgId === msg.id" class="msg-edit-box">
            <textarea v-model="editText" class="msg-edit-textarea" rows="3"></textarea>
            <div class="msg-edit-btns">
              <NButton class="msg-btn" quaternary @click="cancelEdit">取消</NButton>
              <NButton class="msg-btn msg-btn-ok" quaternary @click="submitEdit">发送</NButton>
            </div>
          </div>

          <!-- 工具调用块 -->
          <div v-if="msg.tool_call_json" class="tool-block" @click="toggleTool(msg.id)">
            <div class="tool-head" :class="toolStatus(msg)">
              <span class="tool-icon">{{ toolIcon(msg) }}</span>
              <span class="tool-name">{{ toolName(msg.tool_call_json) }}</span>
              <span class="tool-toggle">{{ expandedTools[msg.id] ? '收起 ▴' : '展开 ▸' }}</span>
            </div>
            <div v-if="expandedTools[msg.id]" class="tool-detail">
              <div class="tool-section">
                <div class="tool-section-title">参数</div>
                <pre>{{ fmtArgs(msg.tool_call_json) }}</pre>
              </div>
              <div v-if="msg._tool_result" class="tool-section">
                <div class="tool-section-title">结果</div>
                <pre>{{ fmtResult(msg._tool_result) }}</pre>
              </div>
            </div>
          </div>

          <!-- 工具结果（独立显示） -->
          <div v-if="msg.tool_result_json && !msg.tool_call_json" class="tool-result-block">
            <pre>{{ fmtJson(msg.tool_result_json) }}</pre>
          </div>
        </div>
      </div>

      <!-- 流式输入中 -->
      <div v-if="streaming" class="chat-msg msg-assistant">
        <div class="msg-avatar">🤖</div>
        <div class="msg-body">
          <div v-if="streamingText" class="msg-bubble" v-html="fmtContent(streamingText)"></div>
          <div v-else class="msg-bubble typing">正在思考<span>.</span><span>.</span><span>.</span></div>
          <span v-if="streamingText" class="cursor">▊</span>
        </div>
      </div>
    </div>

    <!-- 附件预览 -->
    <div v-if="attachFiles.length > 0 || workspaceRefs.length > 0" class="attach-bar">
      <div v-for="(ref, i) in workspaceRefs" :key="'ws-'+i" class="attach-item attach-ws">
        <svg class="attach-ws-svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7f9b7a" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
        <span class="attach-name">{{ ref.name }}</span>
        <NButton class="attach-del" quaternary @click="removeWsRef(i)">✕</NButton>
      </div>
      <div v-for="(f, i) in attachFiles" :key="'f-'+i" class="attach-item">
        <span class="attach-icon">{{ fileIcon(f.name) }}</span>
        <span class="attach-name">{{ f.name }}</span>
        <NButton class="attach-del" quaternary @click="removeAttach(i)">✕</NButton>
      </div>
    </div>

    <!-- 工具确认 / Agent 提问对话框 -->
    <div v-if="confirmData" class="confirm-overlay">
      <div class="confirm-box">
        <template v-if="confirmData.isAskUser">
          <div class="confirm-icon">💬</div>
          <div class="confirm-title">Agent 提问</div>
          <div class="confirm-msg">{{ confirmData.message }}</div>
          <div class="confirm-input-row">
            <input
              v-model="askUserReply"
              class="confirm-input"
              placeholder="请输入回复..."
              @keydown.enter.prevent="submitAskUser"
            />
            <NButton class="confirm-approve" quaternary @click="submitAskUser">发送回复</NButton>
          </div>
        </template>
        <template v-else>
          <div class="confirm-icon">🔐</div>
          <div class="confirm-title">工具执行确认</div>
          <div class="confirm-msg">{{ confirmData.message }}</div>
          <div class="confirm-tool">工具: {{ confirmData.name }}</div>
          <div class="confirm-btns">
            <NButton class="confirm-reject" quaternary @click="rejectConfirm">拒绝</NButton>
            <NButton class="confirm-approve" quaternary @click="approveConfirm">允许执行</NButton>
          </div>
        </template>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-input-bar">
      <div class="input-left">
        <label class="attach-btn" title="上传文件">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
          <input type="file" @change="handleFileAttach" hidden multiple accept=".xlsx,.xls,.csv,.pdf,.txt,.json,.py,.yaml,.yml,.md,.doc,.docx,.png,.jpg,.jpeg,.gif,.bmp,.webp,.tiff,.tif,.ppt,.pptx,.zip,.rar,.7z" />
        </label>
      </div>
      <textarea
        ref="inputRef"
        v-model="inputText"
        class="chat-textarea"
        placeholder="输入消息，Enter 发送，Shift+Enter 换行"
        rows="3"
        @keydown="handleKey"
        @paste="handlePaste"
      ></textarea>
      <NButton v-if="streaming" class="btn-stop" quaternary @click="stopStream">
        ■ 停止
      </NButton>
      <NButton v-else class="btn-send" quaternary :disabled="!inputText.trim()" @click="send">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        <span>发送</span>
      </NButton>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { NButton } from 'naive-ui'
import { sendMessageStream, toolConfirm } from '@/api/agent'
import { useAgentsStore } from '@/stores/agents'

const props = defineProps({
  agent: Object,
  sessionId: Number,
  compact: { type: Boolean, default: false },
  foldFirstUserMsg: { type: Boolean, default: false },
  foldLabel: { type: String, default: '系统已提供上下文' },
})
const emit = defineEmits(['session-created'])
const store = useAgentsStore()

const messages = ref([])
const inputText = ref('')
const streaming = ref(false)
const streamingText = ref('')
const expandedTools = ref({})
const messagesContainer = ref(null)
const inputRef = ref(null)
const editingMsgId = ref(null)
const editText = ref('')
const copyLabel = ref('复制')
const attachFiles = ref([])
const workspaceRefs = ref([])
const dragOver = ref(false)
const confirmData = ref(null)
const askUserReply = ref('')
const forceUnfoldedMsgIds = ref({})
let streamAbort = null
let dragTimer = null
let _firstUserMsgId = null

function isFirstUserMsg(msg) {
  return msg.id === _firstUserMsgId
}

function unfoldMsg(id) {
  forceUnfoldedMsgIds.value = { ...forceUnfoldedMsgIds.value, [id]: true }
}

function _detectFirstUserMsg() {
  if (!props.foldFirstUserMsg) return
  const first = messages.value.find(m => m.role === 'user' && m.content)
  _firstUserMsgId = first ? first.id : null
}

function sendExternal(text) {
  inputText.value = text
  send()
}
defineExpose({ sendExternal })

watch(() => props.sessionId, sid => { if (sid) loadMsgs() })
onMounted(() => { if (props.sessionId) loadMsgs() })

async function loadMsgs() {
  try {
    const msgs = await store.getMessages(props.sessionId)
    const linked = []
    for (const m of msgs) {
      if (m.role === 'tool') {
        if (linked.length > 0) {
          const last = linked[linked.length - 1]
          if (last.role === 'assistant' && last.tool_call_json) {
            last._tool_result = m.tool_result_json
            continue
          }
        }
      }
      linked.push(m)
    }
    messages.value = linked
    _detectFirstUserMsg()
    scrollEnd()
  } catch (e) { console.error(e) }
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
}

function handlePaste(e) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (file) {
        const named = new File([file], `paste_${Date.now()}.png`, { type: file.type })
        attachFiles.value = [...attachFiles.value, named]
      }
      return
    }
  }
}

async function send() {
  let text = inputText.value.trim()
  if (streaming.value) return
  if (!text && attachFiles.value.length === 0 && workspaceRefs.value.length === 0) return

  // Handle attached files — upload first
  const uploadedNames = []
  for (const f of attachFiles.value) {
    try {
      await store.uploadFile(props.agent.id, f, 'inbox')
      uploadedNames.push(f.name)
    } catch (e) {
      console.error('上传失败:', e)
    }
  }
  attachFiles.value = []

  let fullText = text
  if (uploadedNames.length > 0) {
    fullText += `\n\n[已上传文件: ${uploadedNames.join(', ')}]`
  }
  if (workspaceRefs.value.length > 0) {
    const refs = workspaceRefs.value.map(r => r.path || r.name)
    if (!text) {
      text = `请帮我解析文件: ${refs.join(', ')}`
    }
    fullText = text + `\n\n请使用 file_parse 工具解析以下工作区文件:\n${refs.map(p => `- ${p}`).join('\n')}`
    workspaceRefs.value = []
  }

  messages.value.push({ id: Date.now(), role: 'user', content: fullText })
  inputText.value = ''
  streaming.value = true
  streamingText.value = ''
  scrollEnd()

  let lastToolMsg = null

  const handle = sendMessageStream(props.sessionId, fullText, {
    onText(c) { streamingText.value += c; scrollEnd() },
    onToolStart(d) {
      streamingText.value = ''
      lastToolMsg = { id: Date.now(), role: 'assistant', content: '', tool_call_json: JSON.stringify(d), _tool_result: null }
      messages.value.push(lastToolMsg)
      scrollEnd()
    },
    onToolEnd(d) {
      if (lastToolMsg) {
        lastToolMsg._tool_result = JSON.stringify(d)
      }
      scrollEnd()
    },
    onConfirmRequest(d) {
      confirmData.value = {
        tool_call_id: d.tool_call_id || d.name,
        name: d.name,
        message: d.message || `确认允许执行工具「${d.name}」？`,
        args: d.args || {},
      }
      scrollEnd()
    },
    onAskUser(d) {
      // Agent 向用户提问 — 复用 confirm 机制，将用户回复作为 reason 传回
      confirmData.value = {
        tool_call_id: d.tool_call_id || '',
        name: 'ask_user',
        message: d.question || 'Agent 正在提问...',
        args: {},
        isAskUser: true,
      }
      scrollEnd()
    },
    onDone() {
      if (streamingText.value) {
        messages.value.push({ id: Date.now() + 2, role: 'assistant', content: streamingText.value })
      }
      streaming.value = false; streamingText.value = ''; streamAbort = null
      loadMsgs()
    },
    onError(err) {
      streaming.value = false; streamingText.value = ''; streamAbort = null
      messages.value.push({ id: Date.now() + 3, role: 'assistant', content: `[错误] ${err}` })
      scrollEnd()
    },
  })
  streamAbort = handle.abort
}

function stopStream() {
  if (streamAbort) {
    streamAbort()
    if (streamingText.value) {
      messages.value.push({ id: Date.now(), role: 'assistant', content: streamingText.value + '\n\n[已停止]' })
    }
    streaming.value = false
    streamingText.value = ''
    streamAbort = null
  }
}

function editMsg(msg) {
  editingMsgId.value = msg.id
  editText.value = msg.content
}

function cancelEdit() {
  editingMsgId.value = null
  editText.value = ''
}

function submitEdit() {
  const text = editText.value.trim()
  if (!text) return
  editingMsgId.value = null
  editText.value = ''
  inputText.value = text
  send()
}

async function approveConfirm() {
  if (!confirmData.value) return
  const { tool_call_id } = confirmData.value
  confirmData.value = null
  try {
    await toolConfirm(props.sessionId, tool_call_id, true)
  } catch {}
}

async function rejectConfirm() {
  if (!confirmData.value) return
  const { tool_call_id } = confirmData.value
  confirmData.value = null
  try {
    await toolConfirm(props.sessionId, tool_call_id, false, '用户拒绝')
  } catch {}
  streaming.value = false
  streamingText.value = ''
  streamAbort = null
  messages.value.push({ id: Date.now(), role: 'assistant', content: '操作已取消。' })
  scrollEnd()
}

async function submitAskUser() {
  if (!confirmData.value) return
  const reply = askUserReply.value.trim()
  if (!reply) return
  const { tool_call_id } = confirmData.value
  confirmData.value = null
  askUserReply.value = ''
  try {
    await toolConfirm(props.sessionId, tool_call_id, true, reply)
  } catch {}
}

async function regenerate(msg) {
  // Find the user message before this assistant message
  const idx = messages.value.findIndex(m => m.id === msg.id)
  if (idx < 1) return
  let userText = ''
  for (let i = idx - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user' && messages.value[i].content) {
      userText = messages.value[i].content
      break
    }
  }
  if (!userText) return
  inputText.value = userText
  send()
}

async function copyMsg(msg) {
  try {
    await navigator.clipboard.writeText(msg.content)
    copyLabel.value = '已复制'
    setTimeout(() => { copyLabel.value = '复制' }, 1500)
  } catch {
    copyLabel.value = '复制'
  }
}

function handleFileAttach(e) {
  const newFiles = Array.from(e.target.files || [])
  attachFiles.value = [...attachFiles.value, ...newFiles]
  e.target.value = ''
}

function onDragOver() {
  dragOver.value = true
  clearTimeout(dragTimer)
}
function onDragLeave() {
  clearTimeout(dragTimer)
  dragTimer = setTimeout(() => { dragOver.value = false }, 100)
}
function onDrop(e) {
  dragOver.value = false
  const wsData = e.dataTransfer.getData('application/x-workspace-file')
  if (wsData) {
    try {
      const ref = JSON.parse(wsData)
      workspaceRefs.value = [...workspaceRefs.value, ref]
      nextTick(() => send())
      return
    } catch {}
  }
  const newFiles = Array.from(e.dataTransfer.files || [])
  attachFiles.value = [...attachFiles.value, ...newFiles]
}

function removeAttach(i) {
  attachFiles.value.splice(i, 1)
}

function removeWsRef(i) {
  workspaceRefs.value.splice(i, 1)
}

function fileIcon(name) {
  const ext = name.split('.').pop().toLowerCase()
  const map = { xlsx: '📊', xls: '📊', csv: '📋', pdf: '📕', png: '🖼', jpg: '🖼', jpeg: '🖼', gif: '🖼', bmp: '🖼', webp: '🖼', tiff: '🖼', tif: '🖼', txt: '📄', json: '🔧', py: '🐍', doc: '📘', docx: '📘', ppt: '📊', pptx: '📊', zip: '📦', rar: '📦', '7z': '📦', md: '📝' }
  return map[ext] || '📄'
}

function scrollEnd() {
  nextTick(() => { if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight })
}

function toggleTool(id) { expandedTools.value[id] = !expandedTools.value[id] }

function toolName(j) {
  try { return JSON.parse(j).name || '?' } catch { return '?' }
}

function toolIcon(msg) {
  if (msg._tool_result) {
    try {
      const r = JSON.parse(msg._tool_result)
      return r.ok ? '✅' : '❌'
    } catch {}
  }
  return '🔧'
}

function toolStatus(msg) {
  if (msg._tool_result) {
    try {
      const r = JSON.parse(msg._tool_result)
      return r.ok ? 'tool-ok' : 'tool-err'
    } catch {}
  }
  return 'tool-running'
}

function fmtArgs(j) {
  try {
    const d = JSON.parse(j)
    return JSON.stringify(d.arguments || d, null, 2)
  } catch { return j }
}

function fmtResult(j) {
  try {
    const d = JSON.parse(j)
    return JSON.stringify(d.result || d, null, 2)
  } catch { return j }
}

function fmtJson(j) {
  try { return JSON.stringify(JSON.parse(j), null, 2) } catch { return j || '' }
}

function fmtContent(t) {
  if (!t) return ''
  return t
    .replace(/<think[\s\S]*?<\/think>/gi, '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e7e0d5;
  overflow: hidden;
  position: relative;
  transition: border-color .2s, box-shadow .2s;
}
.chat-panel.compact {
  border-radius: 10px;
}
.chat-panel.compact .chat-messages {
  padding: 12px 16px;
}
.chat-panel.compact .chat-input-bar {
  padding: 10px 14px 8px;
}
.chat-panel.compact .chat-textarea {
  min-height: 48px;
  max-height: 80px;
  padding: 8px 12px;
  font-size: 13px;
}
.chat-panel.compact .btn-send,
.chat-panel.compact .btn-stop {
  height: 38px;
  min-width: 70px;
  font-size: 13px;
}
.chat-panel.compact .chat-empty {
  padding: 30px 14px;
}
.chat-panel.compact .empty-icon { font-size: 28px; }
.chat-panel.compact .empty-title { font-size: 14px; }
.chat-panel.chat-drag-over {
  border-color: #7f9b7a;
  box-shadow: 0 0 0 3px rgba(127,155,122,.15);
}

.chat-drop-zone {
  position: absolute;
  inset: 0;
  background: rgba(238, 243, 236, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  border-radius: 14px;
}
.drop-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #2f4330;
  font-size: 16px;
  font-weight: 600;
}
.drop-icon { font-size: 36px; }
.drop-sub { font-size: 12px; color: #8c8680; font-weight: 400; }

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 28px;
}

.chat-empty {
  text-align: center;
  padding: 60px 20px;
  color: #8c8680;
}
.empty-icon { font-size: 44px; opacity: .35; margin-bottom: 12px; }
.empty-title { font-size: 16px; font-weight: 600; color: #555; margin-bottom: 6px; }
.empty-hint { font-size: 13px; color: #aaa; }

.chat-msg { display: flex; gap: 10px; margin-bottom: 14px; }
.msg-user { flex-direction: row-reverse; }

.msg-avatar {
  width: 34px; height: 34px;
  border-radius: 50%;
  background: #eef3ec;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; font-size: 16px;
}
.msg-user .msg-avatar { background: #e8e4da; }

.msg-body { max-width: 75%; min-width: 60px; }

.msg-bubble {
  padding: 10px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.msg-user .msg-bubble {
  background: #7f9b7a; color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-assistant .msg-bubble {
  background: #f7f4ee;
  border: 1px solid #e7e0d5;
  border-bottom-left-radius: 4px;
  color: #333;
}

/* Folded system context message */
.msg-folded {
  background: #f5f3ee !important;
  border: 1px dashed #d7d0c5 !important;
  cursor: pointer;
  font-size: 12px;
  color: #8c8680;
  max-width: 280px;
}
.msg-folded:hover {
  border-color: #b8ccb5 !important;
  color: #555;
}
.fold-label { font-weight: 500; }
.fold-hint { font-size: 11px; margin-left: 4px; opacity: 0.7; }

/* 消息操作按钮 */
.msg-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  opacity: 0;
  transition: opacity .15s;
}
.chat-msg:hover .msg-actions { opacity: 1; }
.actions-user { justify-content: flex-end; }
.actions-assistant { justify-content: flex-start; }

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
.msg-btn-ok { color: #2f4330; font-weight: 600; }
.msg-btn-ok:hover { background: #d7e5d4; }

/* 编辑框 */
.msg-edit-box {
  margin-top: 6px;
  padding: 8px;
  background: #faf8f3;
  border: 1px solid #e7e0d5;
  border-radius: 8px;
}
.msg-edit-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #e7e0d5;
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  line-height: 1.5;
}
.msg-edit-textarea:focus { border-color: #b8ccb5; }
.msg-edit-btns { display: flex; gap: 6px; margin-top: 6px; justify-content: flex-end; }

.cursor { animation: blink 1s step-end infinite; color: #7f9b7a; font-size: 14px; margin-left: 2px; }
@keyframes blink { 50% { opacity: 0; } }

.typing span { animation: dot 1.4s infinite; color: #999; }
.typing span:nth-child(2) { animation-delay: .2s; }
.typing span:nth-child(3) { animation-delay: .4s; }
@keyframes dot { 0%,60%,100% { opacity: 0; } 30% { opacity: 1; } }

/* 工具块 */
.tool-block {
  margin-top: 6px;
  border-radius: 10px;
  overflow: hidden;
  font-size: 13px;
  cursor: pointer;
}
.tool-head {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px;
  transition: background .15s;
}
.tool-head.tool-running { background: #eef5f8; border: 1px solid #d0e4ea; }
.tool-head.tool-ok { background: #eef3ec; border: 1px solid #d7e5d4; }
.tool-head.tool-err { background: #fdf2ef; border: 1px solid #e0b8ad; }
.tool-block:hover .tool-head { filter: brightness(.97); }

.tool-icon { font-size: 14px; }
.tool-name { font-weight: 600; flex: 1; }
.tool-running .tool-name { color: #1a7a8a; }
.tool-ok .tool-name { color: #2f5e2e; }
.tool-err .tool-name { color: #9b3d2f; }
.tool-toggle { color: #8c8680; font-size: 12px; }

.tool-detail {
  border-top: 1px solid #ede8df;
  background: #faf8f3;
}
.tool-section {
  padding: 8px 12px;
}
.tool-section + .tool-section {
  border-top: 1px dashed #e7e0d5;
}
.tool-section-title {
  font-size: 11px;
  font-weight: 600;
  color: #8c8680;
  margin-bottom: 4px;
  text-transform: uppercase;
}
.tool-detail pre {
  margin: 0; padding: 6px 8px;
  background: #fff; border-radius: 6px;
  font-size: 12px; overflow: auto;
  max-height: 200px; line-height: 1.5;
  border: 1px solid #ede8df;
}

.tool-result-block pre {
  margin: 6px 0 0;
  padding: 8px 12px;
  background: #f0faf0;
  border: 1px solid #d4e8d4;
  border-radius: 8px;
  font-size: 12px;
  overflow: auto;
  max-height: 160px;
}

/* 输入区 */
.chat-input-bar {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding: 16px 24px 12px;
  border-top: 1px solid #e7e0d5;
  background: #faf8f3;
  flex-shrink: 0;
}

.input-left { flex-shrink: 0; display: flex; align-items: center; }

.attach-btn {
  width: 40px; height: 40px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e7e0d5;
  font-size: 18px;
  cursor: pointer;
  transition: background .15s;
}
.attach-btn:hover { background: #f0ede5; }

.chat-textarea {
  flex: 1;
  min-height: 72px;
  max-height: 160px;
  padding: 12px 16px;
  border: 1px solid #e7e0d5;
  border-radius: 12px;
  font-size: 14px;
  resize: none;
  outline: none;
  font-family: inherit;
  line-height: 1.6;
  background: #fff;
  color: #333;
}
.chat-textarea:focus {
  border-color: #7f9b7a;
  box-shadow: 0 0 0 3px rgba(127,155,122,.12);
}

.btn-send {
  height: 48px;
  min-width: 90px;
  border: none;
  border-radius: 12px;
  background: #7f9b7a;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: background .15s;
  font-family: inherit;
}
.btn-send:hover:not(:disabled) { background: #3d6b3a; }
.btn-send:disabled { opacity: .45; cursor: not-allowed; }
.btn-stop {
  height: 48px;
  min-width: 90px;
  border: 2px solid #c0392b;
  border-radius: 12px;
  background: #fff;
  color: #c0392b;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: background .15s;
  font-family: inherit;
}
.btn-stop:hover { background: #fdf2ef; }

/* 附件预览 */
.attach-bar {
  display: flex;
  gap: 8px;
  padding: 10px 24px;
  background: #faf8f3;
  flex-shrink: 0;
  flex-wrap: wrap;
  border-top: 1px solid #e7e0d5;
}
.attach-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #fff;
  border: 1px solid #e7e0d5;
  border-radius: 8px;
  font-size: 12px;
  color: #435046;
}
.attach-ws { border-color: #d7e5d4; background: #f2f7f0; }
.attach-ws-svg { flex-shrink: 0; }
.attach-icon { font-size: 14px; }
.attach-name { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.attach-del {
  border: none; background: transparent; cursor: pointer;
  color: #aaa; font-size: 12px; padding: 0 2px;
}
.attach-del:hover { color: #c0392b; }

/* 确认对话框 */
.confirm-overlay {
  position: absolute; inset: 0;
  background: rgba(0,0,0,.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 30; border-radius: 14px;
}
.confirm-box {
  background: #fff; border-radius: 16px; padding: 28px 32px;
  max-width: 420px; width: 90%; text-align: center;
  box-shadow: 0 20px 60px rgba(0,0,0,.2);
}
.confirm-icon { font-size: 36px; margin-bottom: 12px; }
.confirm-title { font-size: 17px; font-weight: 700; color: #333; margin-bottom: 10px; }
.confirm-msg { font-size: 14px; color: #555; line-height: 1.6; margin-bottom: 8px; }
.confirm-tool { font-size: 13px; color: #8c8680; margin-bottom: 18px; }
.confirm-btns { display: flex; gap: 10px; justify-content: center; }
.confirm-reject {
  padding: 8px 24px; border-radius: 10px; border: 1px solid #e7e0d5;
  background: #fff; color: #8c8680; font-size: 14px; cursor: pointer; font-family: inherit;
}
.confirm-reject:hover { background: #fdf2ef; border-color: #e0b8ad; color: #9b3d2f; }
.confirm-approve {
  padding: 8px 24px; border-radius: 10px; border: none;
  background: #7f9b7a; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.confirm-approve:hover { background: #3d6b3a; }
</style>
