<template>
  <div class="provider-layout">
    <!-- 左侧：供应商列表 -->
    <div class="provider-sidebar">
      <div class="sidebar-head">
        <h3>模型配置</h3>
        <button class="btn-add" @click="addProvider" title="添加供应商">+</button>
      </div>

      <div class="provider-list">
        <div
          v-for="cfg in configs"
          :key="cfg.id"
          class="provider-item"
          :class="{ active: selectedId === cfg.id }"
          @click="selectProvider(cfg)"
        >
          <span class="provider-icon" :style="{ background: getProviderColor(cfg.provider) }">
            {{ getProviderShort(cfg.provider) }}
          </span>
          <div class="provider-info">
            <div class="provider-name">{{ cfg.display_name }}</div>
            <div class="provider-model">{{ cfg.model_name || '未配置模型' }}</div>
          </div>
          <span class="status-dot" :class="cfg.status === 'active' ? 'on' : 'off'"></span>
        </div>

        <div v-if="!configs.length" class="empty-sidebar">
          <p>尚未配置供应商</p>
          <button class="btn-add-inline" @click="addProvider">+ 添加</button>
        </div>
      </div>

      <div class="sidebar-footer">
        <button class="btn-log" @click="loadCallLogs">调用记录</button>
      </div>
    </div>

    <!-- 右侧：配置表单 -->
    <div class="provider-detail">
      <!-- 未选中 -->
      <div v-if="!selectedId && !isAdding" class="empty-detail">
        <div class="empty-icon">&#9881;</div>
        <p>选择左侧供应商查看配置，或添加新供应商</p>
      </div>

      <!-- 添加/编辑表单 -->
      <div v-if="selectedId || isAdding" class="detail-form">
        <div class="form-scroll">
          <div class="form-section">
            <div class="form-row">
              <div class="form-field">
                <label>供应商名称</label>
                <input v-model="form.display_name" class="field-input" placeholder="如：MiniMax-M2.7" />
              </div>
              <div class="form-field">
                <label>备注</label>
                <input v-model="form.note" class="field-input" placeholder="例如：公司专用账号" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-field">
                <label>官网链接</label>
                <input v-model="form.website_url" class="field-input" placeholder="https://example.com（可选）" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-field">
                <label>API 协议</label>
                <NSelect v-model:value="form.protocol" :options="protocolOptions" class="field-input" />
                <span class="field-desc">选择与供应商 API 兼容的协议类型，大多数供应商使用 OpenAI Completions 格式。</span>
              </div>
            </div>

            <div class="form-row">
              <div class="form-field">
                <label>API 端点</label>
                <input v-model="form.base_url" class="field-input" placeholder="https://api.minimaxi.com/v1" />
                <span class="field-desc">供应商的 API 端点地址。</span>
              </div>
            </div>

            <div class="form-row">
              <div class="form-field">
                <label>API Key</label>
                <div class="key-wrap">
                  <input
                    v-model="form.api_key"
                    :type="showKey ? 'text' : 'password'"
                    class="field-input key-input"
                    placeholder="只需要填这里，下方配置会自动填充"
                  />
                  <button class="key-toggle" @click="showKey = !showKey">{{ showKey ? '隐藏' : '显示' }}</button>
                </div>
                <span class="field-desc" v-if="selectedId">留空不修改</span>
              </div>
            </div>

            <div class="form-row">
              <div class="form-field">
                <label>默认模型</label>
                <NSelect v-if="availableModels.length" v-model:value="form.model_name" :options="modelSelectOptions" placeholder="— 请选择模型 —" clearable class="field-input" />
                <input v-else v-model="form.model_name" class="field-input" placeholder="输入或通过获取模型列表自动填充" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-field">
                <NButton
                  secondary
                  @click="fetchModels"
                  :disabled="fetchingModels || !form.api_key || !form.base_url"
                >
                  {{ fetchingModels ? '获取中...' : '获取模型列表' }}
                </NButton>
                <span v-if="fetchedModels.length" class="fetch-count">发现 {{ fetchedModels.length }} 个模型</span>
                <span v-if="fetchError" class="fetch-error">{{ fetchError }}</span>
              </div>
            </div>

            <!-- 获取到的模型列表 -->
            <div v-if="fetchedModels.length" class="form-row">
              <div class="form-field">
                <label>可用模型（点击选择）</label>
                <div class="model-grid">
                  <div
                    v-for="m in fetchedModels"
                    :key="m.id"
                    class="model-item"
                    :class="{ selected: form.model_name === m.id }"
                    @click="form.model_name = m.id"
                  >
                    <span class="model-radio" :class="{ checked: form.model_name === m.id }"></span>
                    <div class="model-text">
                      <span class="model-name">{{ m.name }}</span>
                      <span v-if="m.desc" class="model-desc">{{ m.desc }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="form-row">
              <div class="form-field">
                <label class="toggle-row">
                  <input type="checkbox" v-model="form.send_user_agent" />
                  <span>发送 User-Agent</span>
                </label>
                <span class="field-desc">部分供应商需要设置 User-Agent 才能正常访问。</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部操作栏 -->
        <div class="form-footer">
          <div class="footer-left">
            <NButton v-if="selectedId" type="error" @click="deleteConfig">删除供应商</NButton>
          </div>
          <div class="footer-right">
            <span v-if="testResult" class="test-result-inline" :class="testResult.connected ? 'ok' : 'fail'">
              {{ testResult.connected ? `连接成功 (${testResult.latency_ms}ms)` : `失败: ${testResult.error}` }}
            </span>
            <NButton v-if="selectedId" tertiary @click="handleTest" :disabled="testing">
              {{ testing ? '测试中...' : '测试连接' }}
            </NButton>
            <NButton tertiary @click="cancelForm">取消</NButton>
            <NButton type="primary" @click="saveForm" :disabled="saving">
              {{ saving ? '保存中...' : '保存' }}
            </NButton>
          </div>
        </div>
      </div>
    </div>

    <!-- 调用记录 -->
    <div v-if="callLogs.length" class="call-log-overlay" @click.self="callLogs = []">
      <div class="call-log-modal">
        <div class="modal-header">
          <h4>最近 AI 调用记录</h4>
          <NButton tertiary size="small" @click="callLogs = []">关闭</NButton>
        </div>
        <table class="log-table">
          <thead><tr><th>时间</th><th>提供商</th><th>模型</th><th>状态</th><th>耗时</th></tr></thead>
          <tbody>
            <tr v-for="log in callLogs" :key="log.id">
              <td>{{ formatTime(log.created_at) }}</td>
              <td>{{ log.provider }}</td>
              <td>{{ log.model || '-' }}</td>
              <td><span class="tag" :class="log.status === 'success' ? 'tag-green' : 'tag-warn'">{{ log.status === 'success' ? '成功' : '失败' }}</span></td>
              <td>{{ log.duration_ms }}ms</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NSelect, NButton } from 'naive-ui'
import * as api from '@/api/ai'

const configs = ref([])
const providers = ref([])
const protocols = ref([])
const protocolOptions = computed(() => protocols.value.map(p => ({ label: p.label, value: p.code })))
const modelSelectOptions = computed(() => availableModels.value.map(m => ({ label: `${m.name}${m.desc ? ' · ' + m.desc : ''}`, value: m.id })))
const selectedId = ref(null)
const isAdding = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)
const showKey = ref(false)
const fetchingModels = ref(false)
const fetchedModels = ref([])
const fetchError = ref('')
const callLogs = ref([])

const form = ref({
  display_name: '', note: '', website_url: '',
  protocol: 'openai', base_url: '', api_key: '',
  model_name: '', send_user_agent: false, is_default: false,
  privacy_mode: 'standard',
})

const availableModels = computed(() => fetchedModels.value)

const PROVIDER_COLORS = {
  zhipu: '#4e7ff1', minimax: '#e8593c', kimi: '#6c5ce7', qwen: '#f39c12',
  doubao: '#3498db', ernie: '#2ecc71', openai: '#10a37f', anthropic: '#d4a373',
  ollama: '#6b7280', deepseek: '#4a90d9', xiaomimimo: '#ff6900', openai_compatible: '#8b5cf6',
}
const PROVIDER_SHORTS = {
  zhipu: '智', minimax: 'MM', kimi: 'K', qwen: '通',
  doubao: '豆', ernie: '文', openai: 'OA', anthropic: 'CL',
  ollama: 'OL', deepseek: 'DS', xiaomimimo: '米', openai_compatible: 'OC',
}
function getProviderColor(code) { return PROVIDER_COLORS[code] || '#7f9b7a' }
function getProviderShort(code) { return PROVIDER_SHORTS[code] || code?.[0]?.toUpperCase() || '?' }

function selectProvider(cfg) {
  isAdding.value = false
  selectedId.value = cfg.id
  testResult.value = null
  fetchedModels.value = []
  fetchError.value = ''
  showKey.value = false
  form.value = {
    display_name: cfg.display_name || '',
    note: cfg.note || '',
    website_url: cfg.website_url || '',
    protocol: cfg.protocol || 'openai',
    base_url: cfg.base_url || '',
    api_key: '',
    model_name: cfg.model_name || '',
    send_user_agent: cfg.send_user_agent || false,
    is_default: cfg.is_default || false,
    privacy_mode: cfg.privacy_mode || 'standard',
  }
}

function addProvider() {
  selectedId.value = null
  isAdding.value = true
  testResult.value = null
  fetchedModels.value = []
  fetchError.value = ''
  showKey.value = false
  form.value = {
    display_name: '', note: '', website_url: '',
    protocol: 'openai', base_url: '', api_key: '',
    model_name: '', send_user_agent: false, is_default: false,
    privacy_mode: 'standard',
  }
}

function cancelForm() {
  selectedId.value = null
  isAdding.value = false
  testResult.value = null
  fetchedModels.value = []
}

async function fetchModels() {
  if (!form.value.api_key || !form.value.base_url) return
  fetchingModels.value = true
  fetchError.value = ''
  try {
    const models = await api.fetchRemoteModels({
      base_url: form.value.base_url,
      api_key: form.value.api_key,
      protocol: form.value.protocol,
    })
    fetchedModels.value = models || []
  } catch(e) {
    fetchError.value = e.message || '获取失败'
    fetchedModels.value = []
  }
  fetchingModels.value = false
}

async function saveForm() {
  saving.value = true
  try {
    const data = {
      provider: guessProviderFromUrl(form.value.base_url),
      display_name: form.value.display_name,
      base_url: form.value.base_url,
      model_name: form.value.model_name,
      protocol: form.value.protocol,
      note: form.value.note,
      website_url: form.value.website_url,
      send_user_agent: form.value.send_user_agent,
      is_default: form.value.is_default,
      privacy_mode: form.value.privacy_mode,
    }
    if (form.value.api_key) data.api_key = form.value.api_key

    if (selectedId.value) {
      await api.updateAIConfig(selectedId.value, data)
    } else {
      await api.createAIConfig(data)
    }
    cancelForm()
    await load()
  } catch(e) { alert(e.message || '保存失败') }
  finally { saving.value = false }
}

function guessProviderFromUrl(url) {
  if (!url) return 'openai_compatible'
  const map = {
    'bigmodel': 'zhipu', 'z.ai': 'zhipu',
    'minimaxi': 'minimax', 'minimax.io': 'minimax',
    'moonshot': 'kimi',
    'dashscope': 'qwen', 'aliyuncs': 'qwen',
    'volces': 'doubao', 'ark': 'doubao',
    'qianfan': 'ernie', 'baidubce': 'ernie',
    'openai.com': 'openai',
    'anthropic.com': 'anthropic',
    'localhost:11434': 'ollama',
    'deepseek': 'deepseek',
    'xiaomimimo': 'xiaomimimo',
  }
  for (const [keyword, provider] of Object.entries(map)) {
    if (url.includes(keyword)) return provider
  }
  return 'openai_compatible'
}

async function handleTest() {
  if (!selectedId.value) return
  testing.value = true
  testResult.value = null
  try {
    const r = await api.testAIConnection(selectedId.value)
    testResult.value = r
  } catch(e) {
    testResult.value = { connected: false, error: e.message }
  }
  testing.value = null
}

async function deleteConfig() {
  const cfg = configs.value.find(c => c.id === selectedId.value)
  if (!cfg) return
  if (!confirm(`确认删除「${cfg.display_name}」？`)) return
  try {
    await api.deleteAIConfig(cfg.id)
    cancelForm()
    await load()
  } catch(e) { alert(e.message || '删除失败') }
}

async function load() {
  try { configs.value = await api.getAIConfigs() } catch(e) { console.error(e) }
}
async function loadCallLogs() {
  try { callLogs.value = await api.getAICallLogs({ limit: 50 }) || [] }
  catch(e) { alert(e.message || '读取调用记录失败') }
}
function formatTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

onMounted(async () => {
  try { providers.value = await api.getProviders() } catch {}
  try { protocols.value = await api.getApiProtocols() } catch {}
  await load()
})
</script>

<style scoped>
.provider-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 0;
  height: 100%;
  overflow: hidden;
  background: #fff;
}

/* ── 左侧 ── */
.provider-sidebar {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--line-soft);
  background: #faf8f3;
}
.sidebar-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 14px 12px; border-bottom: 1px solid var(--line-soft);
}
.sidebar-head h3 { margin: 0; font-size: var(--font-size-md); font-weight: 700; }
.btn-add {
  width: 28px; height: 28px; border: 1px dashed var(--line); border-radius: 7px;
  background: transparent; color: var(--green); font-size: 17px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all .15s;
}
.btn-add:hover { background: var(--green-2); border-color: var(--green); }

.provider-list { flex: 1; overflow-y: auto; padding: 6px; }
.provider-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 10px; border-radius: 9px; cursor: pointer;
  transition: all .12s; margin-bottom: 2px;
}
.provider-item:hover { background: #f0ede5; }
.provider-item.active { background: var(--green-2); border: 1px solid #cfe1cc; padding: 9px 9px; }

.provider-icon {
  width: 34px; height: 34px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 12px; font-weight: 700; flex-shrink: 0;
}
.provider-info { flex: 1; min-width: 0; }
.provider-name { font-size: var(--font-size-sm); font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.provider-model { font-size: 11px; color: var(--muted); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.status-dot.on { background: #5cb85c; }
.status-dot.off { background: #ccc; }

.empty-sidebar { text-align: center; padding: 28px 14px; color: var(--muted); font-size: var(--font-size-sm); }
.btn-add-inline { background: transparent; border: 1px dashed var(--line); border-radius: 7px; padding: 5px 12px; color: var(--green); font-size: var(--font-size-sm); cursor: pointer; font-family: inherit; }
.sidebar-footer { padding: 8px 14px; border-top: 1px solid var(--line-soft); }
.btn-log { background: transparent; border: none; color: var(--muted); font-size: var(--font-size-sm); cursor: pointer; font-family: inherit; }
.btn-log:hover { color: var(--text); }

/* ── 右侧 ── */
.provider-detail { display: flex; flex-direction: column; overflow: hidden; }
.empty-detail { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; color: var(--muted); gap: 10px; }
.empty-icon { font-size: 44px; opacity: .22; }
.empty-detail p { font-size: var(--font-size-sm); }

/* ── 表单 ── */
.detail-form { display: flex; flex-direction: column; height: 100%; }
.form-scroll { flex: 1; overflow-y: auto; padding: 22px 32px 12px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 2px; }
.form-field { margin-bottom: 12px; }
.form-field > label {
  display: block; font-size: var(--font-size-sm); font-weight: 600;
  color: var(--text); margin-bottom: 5px;
}
.field-input {
  width: 100%; padding: 8px 13px;
  border: 1px solid var(--line); border-radius: 8px;
  font-size: var(--font-size-base); font-family: inherit; color: var(--text);
  background: #faf8f3; outline: none; box-sizing: border-box;
  transition: border-color .2s, box-shadow .2s;
}
.field-input:focus { border-color: var(--green); box-shadow: 0 0 0 3px rgba(127,155,122,.12); }
.field-desc { display: block; font-size: 12px; color: var(--muted); margin-top: 4px; line-height: 1.5; }

.key-wrap { display: flex; }
.key-input { flex: 1; border-top-right-radius: 0; border-bottom-right-radius: 0; }
.key-toggle {
  padding: 0 11px; border: 1px solid var(--line); border-left: none;
  border-radius: 0 8px 8px 0; background: #f0ede5; color: var(--text-tertiary);
  font-size: 12px; cursor: pointer; font-family: inherit; white-space: nowrap;
}
.key-toggle:hover { background: #e8e4da; }

.toggle-row { display: flex !important; align-items: center; gap: 8px; cursor: pointer; font-weight: 400 !important; }
.toggle-row input { cursor: pointer; }

.fetch-count { margin-left: 10px; color: var(--green); font-size: 12px; }
.fetch-error { margin-left: 10px; color: var(--warn); font-size: 12px; }

/* 模型网格 */
.model-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 6px; }
.model-item {
  display: flex; align-items: flex-start; gap: 7px;
  padding: 8px 10px; border: 1px solid var(--line-soft); border-radius: 7px;
  cursor: pointer; transition: all .12s;
}
.model-item:hover { background: #faf8f2; }
.model-item.selected { background: var(--green-2); border-color: #cfe1cc; }
.model-radio {
  width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--line);
  flex-shrink: 0; margin-top: 2px; position: relative; transition: all .12s;
}
.model-radio.checked { border-color: var(--green); }
.model-radio.checked::after { content: ''; position: absolute; top: 2px; left: 2px; width: 6px; height: 6px; border-radius: 50%; background: var(--green); }
.model-text { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.model-name { font-size: 12px; font-weight: 600; color: var(--text); word-break: break-all; }
.model-desc { font-size: 11px; color: var(--muted); }

/* 底部操作栏 */
.form-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 32px; border-top: 1px solid var(--line-soft);
  background: #faf8f3;
}
.footer-left, .footer-right { display: flex; align-items: center; gap: 8px; }
.test-result-inline { font-size: 12px; }
.test-result-inline.ok { color: var(--ok-text); }
.test-result-inline.fail { color: var(--warn-text); }

/* ── 按钮 ── */
.btn {
  border: none; border-radius: 7px; padding: 7px 15px; cursor: pointer;
  font-size: var(--font-size-sm); font-family: inherit; transition: all .15s;
  display: inline-flex; align-items: center; gap: 5px;
}
.btn-sm { padding: 4px 10px; font-size: var(--font-size-xs); }
.btn-primary { background: var(--green); color: #fff; font-weight: 600; }
.btn-primary:hover:not(:disabled) { background: var(--green-hover); }
.btn-primary:disabled { opacity: .45; cursor: not-allowed; }
.btn-secondary { background: var(--panel-2); color: #435046; border: 1px solid var(--line); }
.btn-secondary:hover:not(:disabled) { background: #f5f2ec; }
.btn-ghost { background: transparent; color: var(--muted); border: 1px solid transparent; }
.btn-ghost:hover { background: #f5f2ec; color: var(--text); }
.btn-danger { color: #9b3d2f; border-color: #e0b8ad; }
.btn-danger:hover { background: #fdf2ef; }

/* ── 标签 ── */
.tag { display: inline-block; padding: 3px 7px; border-radius: var(--radius-pill); font-size: 11px; font-weight: 500; }
.tag-green { background: var(--tag-green-bg); color: var(--tag-green-text); }
.tag-warn { background: var(--tag-warn-bg); color: var(--tag-warn-text); }

/* ── 调用记录 ── */
.call-log-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.3); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.call-log-modal { background: #faf8f3; border-radius: 14px; padding: 22px; width: 90%; max-width: 640px; box-shadow: 0 8px 32px rgba(0,0,0,.15); max-height: 80vh; overflow-y: auto; }
.modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.modal-header h4 { margin: 0; font-size: var(--font-size-base); }
.log-table { font-size: var(--font-size-xs); }

@media (max-width: 900px) {
  .provider-layout { grid-template-columns: 1fr; margin: -12px; }
  .provider-sidebar { border-right: none; border-bottom: 1px solid var(--line-soft); max-height: 200px; }
  .form-row { grid-template-columns: 1fr; }
  .model-grid { grid-template-columns: 1fr; }
}
</style>
