<template>
  <div class="agent-page">
    <!-- 顶部标题栏 -->
    <div class="agent-topbar">
      <div class="topbar-left">
        <span class="agent-avatar">{{ (agent?.display_name || '?')[0] }}</span>
        <div class="agent-info">
          <h3>{{ agent?.display_name || '加载中...' }}</h3>
          <span v-if="agent?.ai_config" class="model-tag">
            {{ agent.ai_config.model_name || agent.ai_config.display_name }}
          </span>
        </div>
      </div>
      <div class="agent-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="agent-tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >{{ tab.label }}</button>
      </div>
    </div>

    <!-- 内容区：根据 tab 切换 -->
    <div class="agent-content">
      <div v-if="activeTab === 'chat' && agent" class="chat-layout">
        <div class="chat-sessions">
          <button class="btn-new-session" @click="newSession">+ 新建对话</button>
          <div class="session-list">
            <div
              v-for="s in sessions"
              :key="s.id"
              class="session-item"
              :class="{ active: s.id === currentSessionId }"
              @click="switchSession(s.id)"
            >
              <span class="session-title">{{ s.title || '未命名' }}</span>
              <span class="session-time">{{ fmtTime(s.created_at) }}</span>
              <button class="session-del" @click.stop="delSession(s.id)" title="删除">✕</button>
            </div>
          </div>
        </div>
        <div class="chat-main">
          <ChatPanel
            ref="chatPanelRef"
            :agent="agent"
            :session-id="currentSessionId"
            @session-created="onSessionCreated"
          />
        </div>
        <div class="chat-side">
          <FilePanel :agent-id="agent.id" />
        </div>
      </div>
      <SkillsPanel
        v-if="activeTab === 'skills' && agent"
        :agent-id="agent.id"
        @start-teach="onStartTeach"
      />
      <MemoryPanel
        v-if="activeTab === 'memory' && agent"
        :agent-id="agent.id"
      />
      <SessionsPanel
        v-if="activeTab === 'sessions' && agent"
        :agent-id="agent.id"
        @open-session="onOpenSession"
        @session-created="onSessionCreated"
      />
      <SettingsPanel
        v-if="activeTab === 'settings' && agent"
        :agent="agent"
        @updated="onAgentUpdated"
        @deleted="onAgentDeleted"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentsStore } from '@/stores/agents'
import ChatPanel from './agent/ChatPanel.vue'
import FilePanel from './agent/FilePanel.vue'
import SessionsPanel from './agent/SessionsPanel.vue'
import SkillsPanel from './agent/SkillsPanel.vue'
import MemoryPanel from './agent/MemoryPanel.vue'
import SettingsPanel from './agent/SettingsPanel.vue'

const route = useRoute()
const router = useRouter()
const agentsStore = useAgentsStore()

const agent = ref(null)
const activeTab = ref('chat')
const currentSessionId = ref(null)
const chatPanelRef = ref(null)
const sessions = ref([])

const tabs = [
  { key: 'chat', label: '聊天' },
  { key: 'skills', label: '技能' },
  { key: 'memory', label: '记忆' },
  { key: 'sessions', label: '会话' },
  { key: 'settings', label: '设置' },
]

onMounted(() => loadAgent())
watch(() => route.params.id, () => { if (route.name === 'agent-detail') loadAgent() })

async function loadAgent() {
  const id = Number(route.params.id)
  if (!id) return
  try {
    agent.value = await agentsStore.getAgent(id)
    sessions.value = await agentsStore.listSessions(id)
    if (sessions.value.length > 0) {
      currentSessionId.value = sessions.value[0].id
    } else {
      const s = await agentsStore.createSession(id, '新会话')
      sessions.value.unshift(s)
      currentSessionId.value = s.id
    }
  } catch (e) { console.error('加载 agent 失败:', e) }
}

function onSessionCreated(sid) {
  currentSessionId.value = sid
  activeTab.value = 'chat'
  loadSessions()
}
function onOpenSession(sid) { currentSessionId.value = sid; activeTab.value = 'chat' }

async function loadSessions() {
  if (!agent.value) return
  try { sessions.value = await agentsStore.listSessions(agent.value.id) } catch {}
}

async function newSession() {
  if (!agent.value) return
  try {
    const s = await agentsStore.createSession(agent.value.id, '新会话')
    sessions.value.unshift(s)
    currentSessionId.value = s.id
  } catch {}
}

function switchSession(sid) { currentSessionId.value = sid }

async function delSession(sid) {
  if (!agent.value) return
  try {
    await agentsStore.deleteSession(agent.value.id, sid)
    sessions.value = sessions.value.filter(s => s.id !== sid)
    if (currentSessionId.value === sid) {
      currentSessionId.value = sessions.value.length > 0 ? sessions.value[0].id : null
    }
  } catch {}
}

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const pad = n => String(n).padStart(2, '0')
  if (d.toDateString() === now.toDateString()) return `${pad(d.getHours())}:${pad(d.getMinutes())}`
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
function onStartTeach(prompt) {
  activeTab.value = 'chat'
  setTimeout(() => {
    if (chatPanelRef.value) chatPanelRef.value.sendExternal(prompt)
  }, 300)
}
async function onAgentUpdated() { agent.value = await agentsStore.getAgent(agent.value.id) }
function onAgentDeleted() { router.push({ name: 'home' }) }
</script>

<style scoped>
.agent-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 0px);
  background: #f7f4ee;
  overflow: hidden;
}

.agent-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: #faf8f3;
  border-bottom: 1px solid #e7e0d5;
  flex-shrink: 0;
  gap: 12px;
  flex-wrap: wrap;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.agent-avatar {
  width: 42px; height: 42px;
  border-radius: 50%;
  background: #eef3ec;
  color: #30422f;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700;
  font-size: 18px;
}

.agent-info h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #333;
}

.model-tag {
  display: inline-block;
  background: #eef3ec;
  color: #2f4330;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  margin-top: 2px;
}

.agent-tabs {
  display: flex;
  gap: 4px;
}

.agent-tab-btn {
  padding: 7px 18px;
  border: 1px solid #e7e0d5;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  color: #6b726c;
  transition: all .15s;
  font-family: inherit;
}
.agent-tab-btn:hover { background: #f4f1ea; }
.agent-tab-btn.active {
  background: #eef3ec;
  border-color: #d7e5d4;
  color: #2f4330;
  font-weight: 600;
}

.agent-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 16px 24px 24px;
}

/* 聊天布局：左侧对话列表 + 中间聊天 + 右侧文件 */
.chat-layout {
  display: grid;
  grid-template-columns: 200px 1fr 280px;
  gap: 16px;
  height: 100%;
}

/* 对话侧边栏 */
.chat-sessions {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e7e0d5;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.btn-new-session {
  margin: 12px;
  padding: 8px;
  border: 1px dashed #c5d4c2;
  border-radius: 10px;
  background: #f7f9f6;
  color: #4a6b48;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s;
  font-family: inherit;
}
.btn-new-session:hover { background: #eef3ec; border-color: #7f9b7a; }

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 8px;
}
.session-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .12s;
  position: relative;
  margin-bottom: 2px;
}
.session-item:hover { background: #f4f1ea; }
.session-item.active { background: #eef3ec; }
.session-title {
  font-size: 13px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 16px;
}
.session-time { font-size: 11px; color: #aaa; }
.session-del {
  position: absolute;
  top: 6px; right: 6px;
  border: none; background: transparent;
  color: #ccc; font-size: 11px; cursor: pointer;
  padding: 2px 4px; border-radius: 4px;
}
.session-del:hover { color: #c0392b; background: #fde; }

.chat-main { min-width: 0; overflow: hidden; }
.chat-side { overflow: hidden; }

.tab-full {
  height: 100%;
  overflow-y: auto;
}

.file-panel-full {
  max-width: 600px;
}

@media (max-width: 1100px) {
  .chat-layout {
    grid-template-columns: 1fr 280px;
  }
  .chat-sessions { display: none; }
}
@media (max-width: 900px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }
  .chat-side { display: none; }
}
</style>
