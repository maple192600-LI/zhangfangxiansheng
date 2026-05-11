<template>
  <div class="sessions-page">
    <div class="sessions-main">
      <div class="sessions-block">
        <div class="block-head">
          <h3>会话历史</h3>
          <div class="block-actions">
            <span class="block-count">{{ sessions.length }} 个会话</span>
            <NButton class="btn-new" quaternary @click="handleCreate">新建会话</NButton>
          </div>
        </div>

        <div v-if="sessions.length === 0" class="sessions-empty">
          <div class="empty-icon">💬</div>
          <div class="empty-text">暂无会话记录</div>
          <div class="empty-hint">发送第一条消息后将自动创建会话</div>
        </div>

        <div v-for="s in sessions" :key="s.id" class="session-card" @click="handleOpen(s)">
          <div class="session-left">
            <span class="session-icon">💬</span>
            <div class="session-info">
              <div class="session-title">{{ s.title || '未命名会话' }}</div>
              <div class="session-time">{{ fmtTime(s.last_active_at || s.created_at) }}</div>
            </div>
          </div>
          <NButton class="btn-del" quaternary @click.stop="handleDelete(s)" title="删除会话">删除</NButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { NButton } from 'naive-ui'
import { useAgentsStore } from '@/stores/agents'

const props = defineProps({ agentId: Number })
const emit = defineEmits(['open-session', 'session-created'])
const store = useAgentsStore()
const sessions = ref([])

onMounted(() => load())
watch(() => props.agentId, () => load())

async function load() {
  try {
    sessions.value = await store.listSessions(props.agentId)
  } catch { sessions.value = [] }
}

async function handleCreate() {
  try {
    const s = await store.createSession(props.agentId, '新会话')
    sessions.value.unshift(s)
    emit('session-created', s.id)
  } catch {}
}

function handleOpen(s) {
  emit('open-session', s.id)
}

async function handleDelete(s) {
  if (!confirm(`确定删除会话「${s.title || '未命名'}」？`)) return
  try {
    await store.deleteSession(props.agentId, s.id)
    sessions.value = sessions.value.filter(x => x.id !== s.id)
  } catch {}
}

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const pad = n => String(n).padStart(2, '0')
  const dateStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  const timeStr = `${pad(d.getHours())}:${pad(d.getMinutes())}`
  const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
  return dateStr === todayStr ? `今天 ${timeStr}` : `${dateStr} ${timeStr}`
}
</script>

<style scoped>
.sessions-page {
  height: 100%;
  overflow-y: auto;
}

.sessions-block {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e7e0d5;
  padding: 24px 28px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid #ede8df;
}
.block-head h3 { margin: 0; font-size: 16px; font-weight: 700; color: #333; }

.block-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}
.block-count { font-size: 13px; color: #aaa; }

.btn-new {
  padding: 6px 16px;
  border-radius: 8px;
  background: #eef3ec;
  color: #2f4330;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid #d7e5d4;
  font-family: inherit;
  transition: background .15s;
}
.btn-new:hover { background: #d7e5d4; }

.sessions-empty {
  text-align: center;
  padding: 40px 20px;
  color: #8c8680;
}
.empty-icon { font-size: 36px; opacity: .35; margin-bottom: 10px; }
.empty-text { font-size: 15px; font-weight: 600; color: #555; margin-bottom: 6px; }
.empty-hint { font-size: 13px; color: #aaa; }

.session-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid #ede8df;
  border-radius: 12px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: background .15s;
}
.session-card:hover { background: #faf8f3; }

.session-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-icon {
  width: 38px; height: 38px;
  border-radius: 10px;
  background: #eef3ec;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.session-info { min-width: 0; }
.session-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-time {
  font-size: 12px;
  color: #aaa;
  margin-top: 3px;
}

.btn-del {
  padding: 4px 12px;
  border-radius: 6px;
  background: transparent;
  color: #c0392b;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid transparent;
  font-family: inherit;
  opacity: 0;
  transition: all .15s;
}
.session-card:hover .btn-del { opacity: 1; }
.btn-del:hover { background: #fdf2f2; border-color: #f0c9c9; }
</style>
