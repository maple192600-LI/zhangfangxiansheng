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
      <div v-if="activeTab === 'files' && agent" class="tab-full">
        <FilePanel :agent-id="agent.id" class="file-panel-full" />
      </div>
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

const tabs = [
  { key: 'chat', label: '聊天' },
  { key: 'files', label: '文件' },
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
    const sessions = await agentsStore.listSessions(id)
    if (sessions.length > 0) {
      currentSessionId.value = sessions[0].id
    } else {
      const s = await agentsStore.createSession(id, '新会话')
      currentSessionId.value = s.id
    }
  } catch (e) { console.error('加载 agent 失败:', e) }
}

function onSessionCreated(sid) { currentSessionId.value = sid; activeTab.value = 'chat' }
function onOpenSession(sid) { currentSessionId.value = sid; activeTab.value = 'chat' }
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

/* 聊天布局：左侧聊天 + 右侧文件 */
.chat-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 16px;
  height: 100%;
}

.chat-main { min-width: 0; overflow: hidden; }
.chat-side { overflow: hidden; }

.tab-full {
  height: 100%;
  overflow-y: auto;
}

.file-panel-full {
  max-width: 600px;
}

@media (max-width: 900px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }
  .chat-side { display: none; }
}
</style>
