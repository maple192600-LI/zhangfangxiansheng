<template>
  <div class="chat-panel">
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
          <div v-if="msg.content" class="msg-bubble" v-html="fmtContent(msg.content)"></div>

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

    <!-- 输入区 -->
    <div class="chat-input-bar">
      <textarea
        ref="inputRef"
        v-model="inputText"
        class="chat-textarea"
        placeholder="输入消息，Enter 发送，Shift+Enter 换行"
        rows="3"
        @keydown="handleKey"
      ></textarea>
      <button class="btn-send" :disabled="!inputText.trim() || streaming" @click="send">
        <span class="send-icon">➤</span>
        <span>发送</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { sendMessageStream } from '@/api/agent'
import { useAgentsStore } from '@/stores/agents'

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
    // 关联 tool_call 和 tool_result
    const linked = []
    for (const m of msgs) {
      if (m.role === 'tool') {
        // 把 tool result 挂到前一条 assistant 消息上
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

async function send() {
  const text = inputText.value.trim()
  if (!text || streaming.value) return
  messages.value.push({ id: Date.now(), role: 'user', content: text })
  inputText.value = ''
  streaming.value = true
  streamingText.value = ''
  scrollEnd()

  let lastToolMsg = null

  sendMessageStream(props.sessionId, text, {
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
    onDone() {
      if (streamingText.value) {
        messages.value.push({ id: Date.now() + 2, role: 'assistant', content: streamingText.value })
      }
      streaming.value = false; streamingText.value = ''
      loadMsgs()
    },
    onError(err) {
      streaming.value = false; streamingText.value = ''
      messages.value.push({ id: Date.now() + 3, role: 'assistant', content: `[错误] ${err}` })
      scrollEnd()
    },
  })
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
}

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
  gap: 12px;
  align-items: flex-end;
  padding: 16px 24px 20px;
  border-top: 1px solid #e7e0d5;
  background: #faf8f3;
  flex-shrink: 0;
}

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
.send-icon { font-size: 16px; }
</style>
