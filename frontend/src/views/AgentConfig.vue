<template>
  <div class="section">
    <table v-if="agents.length">
      <thead>
        <tr><th>Agent</th><th>类型</th><th>绑定 AI 配置</th><th>状态</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="a in agents" :key="a.id">
          <td>
            <strong>{{ a.agent_name }}</strong>
            <span style="color:var(--muted);font-size:12px;margin-left:8px">{{ a.agent_code }}</span>
          </td>
          <td>{{ a.agent_type }}</td>
          <td>
            <select class="filter" style="width:auto;display:inline-block;padding:4px 8px;font-size:12px" :value="a.ai_config_id || ''" @change="bindAI(a.id, $event)">
              <option value="">未绑定</option>
              <option v-for="c in aiConfigs" :key="c.id" :value="c.id">{{ c.display_name }}</option>
            </select>
          </td>
          <td><span class="tag" :class="a.status === 'active' ? 'tag-green' : 'tag-gray'">{{ a.status === 'active' ? '启用' : '停用' }}</span></td>
          <td>
            <button class="btn btn-secondary btn-sm" v-if="a.status==='active'" @click="toggleStatus(a.id, 'disabled')">停用</button>
            <button class="btn btn-primary btn-sm" v-else @click="toggleStatus(a.id, 'active')">启用</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else style="color:var(--muted)">暂无 Agent 配置</p>

    <div class="section" style="margin-top:14px">
      <div class="section-title"><h3>工作空间目录</h3></div>
      <div class="ws-list">
        <div class="ws-item" v-for="d in workspaceDirs" :key="d">
          <span style="font-size:14px">📁</span>
          <span>agents/{{ d }}/</span>
          <span style="margin-left:auto;color:var(--muted);font-size:12px">{{ getFileCount(d) }} 个文件</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as api from '@/api/ai'

const agents = ref([])
const aiConfigs = ref([])
const workspaceDirs = ['shared', 'master', 'parser-assistant', 'custom']
const fileCounts = { shared: 3, master: 7, 'parser-assistant': 7, custom: 0 }
function getFileCount(d) { return fileCounts[d] || 0 }

async function load() {
  try {
    const [a, c] = await Promise.all([api.getAgentConfigs(), api.getAIConfigs()])
    agents.value = a || []
    aiConfigs.value = c || []
  } catch(e) { console.error(e) }
}

async function bindAI(agentId, event) {
  const val = event.target.value
  try {
    await api.updateAgentConfig(agentId, { ai_config_id: val ? Number(val) : null })
    await load()
  } catch(e) { alert(e.message) }
}

async function toggleStatus(agentId, status) {
  try {
    await api.updateAgentConfig(agentId, { status })
    await load()
  } catch(e) { alert(e.message) }
}

onMounted(load)
</script>

<style scoped>
@import './common.css';

/* 页面特有样式 */
.ws-list { display: flex; flex-direction: column; gap: 8px; }
.ws-item { display: flex; align-items: center; gap: 8px; font-size: var(--font-size-sm); padding: 8px 12px; background: #fff; border: 1px solid #e7e0d5; border-radius: var(--radius-sm); }
</style>
