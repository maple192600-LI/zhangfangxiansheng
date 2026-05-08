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
          <MessageBubble v-if="msg.content" :content="msg.content" :role="msg.role" />

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

          <ToolCallBlock
            v-if="msg.tool_call_json"
            :tool-call-json="msg.tool_call_json"
            :tool-result="msg._tool_result"
            :expanded="!!expandedTools[msg.id]"
            @toggle="toggleTool(msg.id)"
          />

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
          <MessageBubble v-if="streamingText" :content="streamingText" role="assistant" />
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

    <ConfirmDialog
      v-if="confirmData"
      :is-ask-user="confirmData.isAskUser"
      :message="confirmData.message"
      :tool-name="confirmData.name"
      v-model:reply-text="askUserReply"
      @approve="approveConfirm"
      @reject="rejectConfirm"
      @submit-reply="submitAskUser"
    />

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
        @input="autoResize"
      ></textarea>
      <button v-if="streaming" class="btn-stop" @click="stopStream">
        ■ 停止
      </button>
      <button v-else class="btn-send" :disabled="!inputText.trim()" @click="send">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        <span>发送</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch, onBeforeUnmount } from 'vue'
import { sendMessageStream, toolConfirm } from '@/api/agent'
import { useAgentsStore } from '@/stores/agents'
import ToolCallBlock from './ChatPanel/ToolCallBlock.vue'
import ConfirmDialog from './ChatPanel/ConfirmDialog.vue'
import MessageBubble from './ChatPanel/MessageBubble.vue'

const props = defineProps({ agent: Object, sessionId: Number })
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
let streamAbort = null
let dragTimer = null

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
    scrollEnd()
  } catch (e) { console.error(e) }
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
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
  if (inputRef.value) inputRef.value.style.height = 'auto'
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

function scrollEnd() {
  nextTick(() => { if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight })
}

function toggleTool(id) { expandedTools.value[id] = !expandedTools.value[id] }
function fmtJson(j) {
  try { return JSON.stringify(JSON.parse(j), null, 2) } catch { return j || '' }
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
.msg-assistant .msg-bubble {
  background: #f7f4ee;
  border: 1px solid #e7e0d5;
  border-bottom-left-radius: 4px;
  color: #333;
}

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
</style>
