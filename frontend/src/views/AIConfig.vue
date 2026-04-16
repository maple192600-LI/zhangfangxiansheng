<template>
  <div class="section">
    <div class="section-title">
      <h3>API KEY 配置</h3>
      <button class="btn btn-primary" @click="openForm()">+ 添加配置</button>
    </div>

    <table class="data-table" v-if="configs.length">
      <thead>
        <tr>
          <th>提供商</th><th>名称</th><th>模型</th><th>默认</th><th>状态</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in configs" :key="c.id">
          <td>{{ c.provider }}</td>
          <td>{{ c.display_name }}</td>
          <td>{{ c.model_name || '-' }}</td>
          <td><span class="badge" :class="c.is_default ? 'enabled' : 'disabled'">{{ c.is_default ? '默认' : '-' }}</span></td>
          <td><span class="badge" :class="c.status">{{ c.status === 'active' ? '启用' : '停用' }}</span></td>
          <td class="btn-row">
            <button class="btn btn-secondary btn-sm" @click="handleTest(c.id)" :disabled="testing===c.id">
              {{ testing===c.id ? '测试中...' : '测试连接' }}
            </button>
            <button class="btn btn-secondary btn-sm" @click="openForm(c)">编辑</button>
            <button class="btn btn-secondary btn-sm" v-if="!c.is_default" @click="setDefault(c.id)">设为默认</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else style="color:var(--muted);font-size:14px;padding:20px 0">尚未配置 AI 提供商，请点击右上角添加。</p>

    <div v-if="testResult" class="test-result" :class="testResult.connected ? 'ok' : 'fail'">
      <strong>{{ testResult.connected ? '连接成功' : '连接失败' }}</strong>
      <span v-if="testResult.connected"> — 延迟 {{ testResult.latency_ms }}ms，模型 {{ testResult.model_info }}</span>
      <span v-else> — {{ testResult.error }}</span>
    </div>

    <div class="modal-mask" v-if="showForm" @click.self="showForm=false">
      <div class="modal">
        <h3>{{ editing ? '编辑配置' : '添加配置' }}</h3>
        <div class="form-group">
          <label>提供商</label>
          <select v-model="form.provider" class="filter">
            <option value="zhipu">智谱 (GLM)</option>
            <option value="kimi">Kimi (月之暗面)</option>
            <option value="qwen">通义千问</option>
            <option value="openai_compatible">OpenAI 兼容</option>
            <option value="ollama">Ollama (本地)</option>
          </select>
        </div>
        <div class="form-group">
          <label>显示名称</label>
          <input v-model="form.display_name" class="filter" placeholder="如：智谱 GLM-4" />
        </div>
        <div class="form-group">
          <label>API Key{{ editing ? '（留空不修改）' : '' }}</label>
          <input v-model="form.api_key" type="password" class="filter" placeholder="sk-..." />
        </div>
        <div class="form-group">
          <label>Base URL（可选）</label>
          <input v-model="form.base_url" class="filter" placeholder="留空使用默认地址" />
        </div>
        <div class="form-group">
          <label>模型名称</label>
          <input v-model="form.model_name" class="filter" placeholder="如：glm-4-flash" />
        </div>
        <div class="form-group">
          <label><input type="checkbox" v-model="form.is_default" /> 设为默认</label>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showForm=false">取消</button>
          <button class="btn btn-primary" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as api from '@/api/ai'

const configs = ref([])
const showForm = ref(false)
const editing = ref(null)
const testing = ref(null)
const testResult = ref(null)
const form = ref({ provider: 'zhipu', display_name: '', api_key: '', base_url: '', model_name: '', is_default: false })

async function load() {
  try { configs.value = await api.getAIConfigs() } catch(e) { console.error(e) }
}

function openForm(c) {
  testResult.value = null
  if (c) {
    editing.value = c
    form.value = { provider: c.provider, display_name: c.display_name, api_key: '', base_url: c.base_url || '', model_name: c.model_name || '', is_default: c.is_default }
  } else {
    editing.value = null
    form.value = { provider: 'zhipu', display_name: '', api_key: '', base_url: '', model_name: '', is_default: false }
  }
  showForm.value = true
}

async function save() {
  try {
    const data = { ...form.value }
    if (editing.value) {
      if (!data.api_key) delete data.api_key
      await api.updateAIConfig(editing.value.id, data)
    } else {
      await api.createAIConfig(data)
    }
    showForm.value = false
    await load()
  } catch(e) { alert(e.message || '保存失败') }
}

async function handleTest(id) {
  testing.value = id
  testResult.value = null
  try {
    const r = await api.testAIConnection(id)
    testResult.value = r
  } catch(e) {
    testResult.value = { connected: false, error: e.message }
  }
  testing.value = null
}

async function setDefault(id) {
  try {
    await api.updateAIConfig(id, { is_default: true })
    await load()
  } catch(e) { alert(e.message) }
}

onMounted(load)
</script>

<style scoped>
@import './common.css';
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); color: var(--muted); font-weight: 500; }
.data-table td { padding: 8px 10px; border-bottom: 1px solid #f0ede6; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.badge.enabled { background: #edf4ea; color: #3f5b3d; }
.badge.disabled { background: #f5ece5; color: #8a6e52; }
.badge.active { background: #edf4ea; color: #3f5b3d; }
.btn-sm { padding: 5px 10px; font-size: 12px; }
.test-result { margin-top: 12px; padding: 10px 14px; border-radius: 10px; font-size: 13px; }
.test-result.ok { background: #edf4ea; color: #3f5b3d; border: 1px solid #d9e6d4; }
.test-result.fail { background: #fdf0ec; color: #7f4b32; border: 1px solid #ebd0c2; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #faf8f3; border-radius: 16px; padding: 24px; width: 90%; max-width: 480px; box-shadow: 0 8px 32px rgba(0,0,0,0.18); }
.modal h3 { margin: 0 0 16px 0; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 4px; }
.form-group .filter { width: 100%; box-sizing: border-box; }
</style>
