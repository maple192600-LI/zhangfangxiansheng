<template>
  <div class="section">
    <div class="top-bar">
      <button class="btn btn-primary" @click="openForm()">+ 添加配置</button>
    </div>

    <table v-if="configs.length">
      <thead>
        <tr>
          <th>提供商</th><th>名称</th><th>模型</th><th>默认</th><th>状态</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in configs" :key="c.id">
          <td>{{ getProviderLabel(c.provider) }}</td>
          <td>{{ c.display_name }}</td>
          <td>{{ c.model_name || '-' }}</td>
          <td><span class="tag" :class="c.is_default ? 'tag-green' : 'tag-gray'">{{ c.is_default ? '默认' : '-' }}</span></td>
          <td><span class="tag" :class="c.status === 'active' ? 'tag-green' : 'tag-warn'">{{ c.status === 'active' ? '启用' : '停用' }}</span></td>
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
      <div class="modal" style="max-width:540px">
        <h3>{{ editing ? '编辑配置' : '添加配置' }}</h3>

        <div class="form-group">
          <label>提供商</label>
          <select v-model="form.provider" class="filter">
            <option v-for="p in providers" :key="p.code" :value="p.code">{{ p.label }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>显示名称</label>
          <input v-model="form.display_name" class="filter" placeholder="如：智谱 GLM-5 Turbo" />
        </div>

        <div class="form-group" v-if="currentProviderNeedsKey">
          <label>API Key{{ editing ? '（留空不修改）' : '' }}</label>
          <input v-model="form.api_key" type="password" class="filter" placeholder="sk-..." />
        </div>

        <div class="form-group">
          <label>Base URL</label>
          <input v-model="form.base_url" class="filter" :placeholder="currentProviderDefaultUrl || '输入 API 地址'" />
        </div>

        <div class="form-group">
          <label>模型</label>
          <select v-if="availableModels.length" v-model="form.model_name" class="filter">
            <option value="">— 请选择模型 —</option>
            <option v-for="m in availableModels" :key="m.id" :value="m.id">{{ m.name }} — {{ m.desc }}</option>
          </select>
          <input v-else v-model="form.model_name" class="filter" placeholder="输入模型名称" />
        </div>

        <div class="form-group" v-if="form.provider === 'ollama'">
          <button class="btn btn-secondary btn-sm" @click="detectOllama" :disabled="detecting">
            {{ detecting ? '检测中...' : '自动检测本地模型' }}
          </button>
          <span v-if="ollamaModels.length" style="margin-left:8px;color:var(--green);font-size:12px">发现 {{ ollamaModels.length }} 个模型</span>
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
import { ref, computed, watch, onMounted } from 'vue'
import * as api from '@/api/ai'

const providers = ref([])
const configs = ref([])
const showForm = ref(false)
const editing = ref(null)
const testing = ref(null)
const testResult = ref(null)
const detecting = ref(false)
const ollamaModels = ref([])

const form = ref({
  provider: 'zhipu', display_name: '', api_key: '',
  base_url: '', model_name: '', is_default: false,
})

const currentProviderNeedsKey = computed(() => {
  const p = providers.value.find(p => p.code === form.value.provider)
  return p ? p.needs_api_key : true
})

const currentProviderDefaultUrl = computed(() => {
  const p = providers.value.find(p => p.code === form.value.provider)
  return p ? p.base_url : ''
})

const availableModels = computed(() => {
  if (form.value.provider === 'ollama' && ollamaModels.value.length > 0) {
    return ollamaModels.value
  }
  const p = providers.value.find(p => p.code === form.value.provider)
  return p ? p.models : []
})

// 选择提供商时自动预填
watch(() => form.value.provider, (newProvider) => {
  if (editing.value) return
  const p = providers.value.find(p => p.code === newProvider)
  if (p) {
    form.value.base_url = p.base_url || ''
    form.value.display_name = p.label
    if (p.models.length > 0) {
      form.value.model_name = p.models[0].id
    } else {
      form.value.model_name = ''
    }
  }
})

function getProviderLabel(code) {
  const p = providers.value.find(p => p.code === code)
  return p ? p.label : code
}

async function loadProviders() {
  try {
    providers.value = await api.getProviders()
  } catch { providers.value = [] }
}

async function load() {
  try { configs.value = await api.getAIConfigs() } catch(e) { console.error(e) }
}

function openForm(c) {
  testResult.value = null
  ollamaModels.value = []
  if (c) {
    editing.value = c
    form.value = {
      provider: c.provider, display_name: c.display_name, api_key: '',
      base_url: c.base_url || '', model_name: c.model_name || '', is_default: c.is_default,
    }
  } else {
    editing.value = null
    form.value = { provider: 'zhipu', display_name: '', api_key: '', base_url: '', model_name: '', is_default: false }
  }
  showForm.value = true
}

async function detectOllama() {
  detecting.value = true
  try {
    const models = await api.detectOllamaModels()
    ollamaModels.value = models || []
    if (models.length > 0 && !form.value.model_name) {
      form.value.model_name = models[0].id
    }
  } catch {
    ollamaModels.value = []
    alert('未检测到本地 Ollama 服务，请确认已安装并启动 Ollama')
  }
  detecting.value = false
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

onMounted(() => { loadProviders(); load() })
</script>

<style scoped>
@import './common.css';

/* 页面特有样式 */
.test-result { margin-top: 12px; padding: 10px 14px; border-radius: var(--radius-sm); font-size: var(--font-size-sm); }
.test-result.ok { background: var(--ok-bg); color: var(--ok-text); border: 1px solid var(--ok-border); }
.test-result.fail { background: var(--tag-warn-bg); color: var(--tag-warn-text); border: 1px solid var(--tag-warn-border); }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #faf8f3; border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 480px; box-shadow: 0 8px 32px rgba(0,0,0,0.18); }
.modal h3 { margin: 0 0 16px 0; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: var(--font-size-sm); color: var(--muted); margin-bottom: 4px; }
.form-group .filter { width: 100%; box-sizing: border-box; }
</style>
