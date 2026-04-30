<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>手工流水录入</h3>
        <span>快速录入或 Excel 上传手工流水数据</span>
      </div>
      <div class="filters-bar">
        <select v-model="currentSchemeCode" class="filter" @change="onSchemeChange">
          <option v-for="s in schemes" :key="s.scheme_code" :value="s.scheme_code">{{ s.scheme_name }}</option>
        </select>
        <label style="font-size:13px;color:var(--muted);margin-left:8px">调用智能体</label>
        <select v-model="agentId" class="filter" style="min-width:160px">
          <option :value="null">选择智能体</option>
          <option v-for="a in agents" :key="a.id" :value="a.id">{{ a.display_name }}</option>
        </select>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary" @click="doExportTemplate">下载录入模板</button>
          <button class="btn" :class="tab==='quick'?'btn-primary':'btn-secondary'" @click="tab='quick'">快速录入</button>
          <button class="btn" :class="tab==='upload'?'btn-primary':'btn-secondary'" @click="tab='upload'">Excel 上传</button>
        </div>
      </div>

      <!-- Track A: 快速录入 -->
      <div v-if="tab==='quick'">
        <!-- 批量上下文 -->
        <div class="batch-bar">
          <select v-model="batchCtx.entity_id" class="filter" style="width:140px">
            <option :value="null">批量单位简称（可选）</option>
            <option v-for="e in entities" :key="e.entity_id" :value="e.entity_id">{{ e.entity_name }}</option>
          </select>
          <select v-model="batchCtx.account_id" class="filter" style="width:140px">
            <option :value="null">批量账户名称（可选）</option>
            <optgroup v-for="g in entityGroups" :key="g.entity_id" :label="g.entity_name">
              <option v-for="a in g.accounts" :key="a.id" :value="a.id">{{ a.account_code }} {{ a.account_alias }}</option>
            </optgroup>
          </select>
          <input v-model="batchCtx.date" type="date" class="filter" style="width:130px" title="批量日期" />
        </div>

        <!-- 可编辑表格 -->
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th v-for="col in visibleColumns" :key="col.field_code" :style="{minWidth: col.minWidth}">{{ col.field_name_cn }}</th>
                <th style="width:40px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in editableRows" :key="idx">
                <td v-for="col in visibleColumns" :key="col.field_code">
                  <template v-if="col.field_code === 'entity_match_key'">
                    <select v-model="row[col.field_code]" class="cell-input">
                      <option value="">选择单位简称</option>
                      <option v-for="e in entities" :key="e.entity_id" :value="e.entity_name">{{ e.entity_name }}</option>
                    </select>
                  </template>
                  <template v-else-if="col.field_code === 'account_match_key'">
                    <input v-model="row[col.field_code]" class="cell-input" placeholder="账户编号/名称" />
                  </template>
                  <template v-else-if="col.data_type === 'number'">
                    <input v-model="row[col.field_code]" type="number" step="0.01" class="cell-input" />
                  </template>
                  <template v-else-if="col.field_code === 'business_date'">
                    <input v-model="row[col.field_code]" type="date" class="cell-input" />
                  </template>
                  <template v-else>
                    <input v-model="row[col.field_code]" class="cell-input" :placeholder="col.field_name_cn" />
                  </template>
                </td>
                <td><button class="btn btn-secondary btn-sm" @click="editableRows.splice(idx, 1)" title="删除行">x</button></td>
              </tr>
              <tr v-if="!editableRows.length">
                <td :colspan="visibleColumns.length + 1" style="text-align:center;color:var(--muted);padding:30px">点击下方"添加行"开始录入</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="bottom-bar">
          <button class="btn btn-secondary" @click="addRow()">+ 添加行</button>
          <button class="btn btn-secondary" @click="addRows(5)">+ 添加5行</button>
          <button class="btn btn-primary" @click="doSave" :disabled="saving">{{ saving ? '保存中...' : '保存到暂存区' }}</button>
          <span class="count-info">共 {{ editableRows.length }} 行</span>
        </div>
      </div>

      <!-- Track B: Excel 上传 -->
      <div v-if="tab==='upload'" class="upload-section">
        <div class="upload-zone" @dragover.prevent @drop.prevent="onDrop" @click="$refs.fileInput.click()">
          <div class="upload-icon">+</div>
          <p>将 Excel 文件拖拽到此处，或点击选择文件</p>
          <input ref="fileInput" type="file" accept=".xls,.xlsx,.csv" style="display:none" @change="onFileChange" />
        </div>
        <div v-if="uploadFile" style="display:flex;align-items:center;justify-content:space-between;margin-top:14px;padding:10px 14px;background:var(--ok-bg);border:1px solid var(--ok-border);border-radius:var(--radius-sm)">
          <span>{{ uploadFile.name }} ({{ (uploadFile.size/1024).toFixed(1) }}KB)</span>
          <div style="display:flex;gap:8px">
            <button class="btn btn-secondary" @click="doUpload" :disabled="uploading">{{ uploading ? '上传中...' : '上传预览' }}</button>
            <button class="btn btn-primary" @click="doUploadWithAI" :disabled="uploading || !agentId">{{ uploading ? '解析中...' : 'AI 智能解析' }}</button>
          </div>
        </div>
      </div>

      <!-- AI 解析结果 -->
      <div v-if="aiResult && tab==='upload'" class="section" style="margin-top:14px">
        <div class="panel" v-if="aiResult.ok">
          <div class="panel-title">AI 智能解析结果（{{ aiResult.matched_count }}/{{ aiResult.total_columns }} 列，置信度: {{ aiResult.confidence }}）</div>
          <table style="margin-top:10px">
            <thead><tr><th>Excel 列名</th><th>→</th><th>标准字段</th></tr></thead>
            <tbody>
              <tr v-for="(field, col) in aiResult.mapping" :key="col">
                <td>{{ col }}</td>
                <td style="color:var(--green)">→</td>
                <td><strong>{{ fieldLabel(field) }}</strong></td>
              </tr>
            </tbody>
          </table>
          <div style="display:flex;gap:8px;margin-top:12px;justify-content:flex-end">
            <button class="btn btn-secondary" @click="aiResult = null">取消</button>
            <button class="btn btn-primary" @click="doCommitManualWithMapping" :disabled="committing">{{ committing ? '提交中...' : '确认并提交' }}</button>
          </div>
        </div>
        <div v-else-if="aiResult.error" style="padding:10px 12px;border:1px solid #e6c7b8;background:#fff4ef;color:#8b4f38;border-radius:var(--radius-sm)">
          {{ aiResult.error }}
          <button class="btn btn-secondary btn-sm" style="margin-left:8px" @click="aiResult = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '@/api/manual'
import * as fund from '@/api/fund'
import * as master from '@/api/master'
import http from '@/api/index'

const router = useRouter()

const schemes = ref([])
const fieldPool = ref([])
const currentSchemeCode = ref('manual_multi_subject_basic')
const entities = ref([])
const agents = ref([])
const agentId = ref(null)
const tab = ref('quick')
const editableRows = ref([])
const saving = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const fileInput = ref(null)
const uploadResult = ref(null)
const aiResult = ref(null)
const committing = ref(false)

const batchCtx = ref({ entity_id: null, account_id: null, date: new Date().toISOString().slice(0, 10) })

const currentScheme = computed(() => schemes.value.find(s => s.scheme_code === currentSchemeCode.value))
const visibleColumns = computed(() => {
  if (!currentScheme.value) return []
  return currentScheme.value.selected_fields
    .map(fc => fieldPool.value.find(f => f.field_code === fc))
    .filter(Boolean)
    .map(f => ({ ...f, minWidth: f.is_core ? '100px' : '80px' }))
})

const entityGroups = computed(() => {
  const groups = {}
  for (const e of entities.value) {
    if (!groups[e.entity_id]) groups[e.entity_id] = { entity_id: e.entity_id, entity_name: e.entity_name, accounts: [] }
    groups[e.entity_id].accounts.push(...e.accounts)
  }
  return Object.values(groups)
})

function addRow(count = 1) {
  for (let i = 0; i < count; i++) {
    const row = {}
    for (const col of visibleColumns.value) {
      if (col.field_code === 'entity_match_key') {
        const ent = entities.value.find(e => e.entity_id === batchCtx.value.entity_id)
        row[col.field_code] = ent ? ent.entity_name : ''
      } else if (col.field_code === 'business_date') {
        row[col.field_code] = batchCtx.value.date || ''
      } else {
        row[col.field_code] = ''
      }
    }
    editableRows.value.push(row)
  }
}
function addRows(n) { addRow(n) }

async function loadData() {
  try {
    const [pool, schemeList, tree] = await Promise.all([
      api.getFieldPool(),
      api.getSchemes(),
      master.getAccountsTree(),
    ])
    fieldPool.value = pool || []
    schemes.value = schemeList || []
    entities.value = tree || []
  } catch (e) { console.error(e) }
}

async function loadAgents() {
  try {
    agents.value = await http.get('/agent/agents')
    if (agents.value.length && !agentId.value) agentId.value = agents.value[0].id
  } catch { agents.value = [] }
}

function fieldLabel(code) {
  const f = fieldPool.value.find(x => x.field_code === code)
  return f ? f.field_name_cn : code
}

function onSchemeChange() {
  editableRows.value = []
}

async function doSave() {
  if (!editableRows.value.length) { alert('请先添加行'); return }
  saving.value = true
  try {
    const rows = editableRows.value.map(r => {
      const obj = {}
      for (const [k, v] of Object.entries(r)) {
        if (k === 'income_amount' || k === 'expense_amount' || k === 'previous_balance_input' || k === 'ending_balance_input') {
          obj[k] = v === '' || v == null ? null : Number(v)
        } else {
          obj[k] = v
        }
      }
      return obj
    })
    const result = await api.saveQuickEntry({ scheme_code: currentSchemeCode.value, rows })
    alert(`保存成功！共 ${result.total_count} 条，有效 ${result.saved_count} 条，异常 ${result.abnormal_count} 条`)
    editableRows.value = []
    router.push({ path: '/upload-preview', query: { batch_code: result.batch_code } })
  } catch (e) { alert('保存失败: ' + (e.message || e)) }
  saving.value = false
}

function onFileChange(e) {
  uploadFile.value = e.target.files[0] || null
}
function onDrop(e) {
  const f = e.dataTransfer.files[0]
  if (f) uploadFile.value = f
}

async function doUpload() {
  if (!uploadFile.value) { alert('请先选择文件'); return }
  uploading.value = true
  try {
    const result = await api.uploadManualWorkbook(uploadFile.value, currentSchemeCode.value)
    const draft = await fund.invokeFundSkill('parser.manual', {
      batch_code: result.batch_code,
      scheme_code: currentSchemeCode.value,
      privacy_mode: 'standard',
    })
    router.push({
      name: 'agent-review',
      params: { type: 'parser', id: draft.artifact_id },
      query: { flow: 'manual', batch_code: result.batch_code },
    })
  } catch (e) { alert('上传失败: ' + (e.message || e)) }
  uploading.value = false
}

async function doUploadWithAI() {
  if (!uploadFile.value) { alert('请先选择文件'); return }
  if (!agentId.value) { alert('请先选择要调用的智能体'); return }
  uploading.value = true
  aiResult.value = null
  try {
    // 1. 上传文件获取 headers
    const result = await api.uploadManualWorkbook(uploadFile.value, currentSchemeCode.value)
    uploadResult.value = result
    // 2. AI 解析 headers
    aiResult.value = await http.post('/manual-flow/ai-parse', {
      headers: result.headers,
      sample_rows: [],
      agent_id: agentId.value,
      scheme_code: currentSchemeCode.value,
    })
  } catch (e) {
    aiResult.value = { ok: false, error: e.message || 'AI 解析失败' }
  }
  uploading.value = false
}

async function doCommitManualWithMapping() {
  if (!uploadResult.value || !aiResult.value?.mapping) return
  committing.value = true
  try {
    const result = await api.uploadManualWorkbook(uploadFile.value, currentSchemeCode.value)
    alert(`手工流水 AI 解析提交成功！批次号: ${result.batch_code}`)
    aiResult.value = null
    uploadResult.value = null
    uploadFile.value = null
  } catch (e) {
    alert('提交失败: ' + (e.message || e))
  }
  committing.value = false
}

function doExportTemplate() {
  api.exportManualTemplate(currentSchemeCode.value).then(blob => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `手工流水模板_${currentSchemeCode.value}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  }).catch(e => alert('下载失败: ' + (e.message || e)))
}

onMounted(() => { loadData(); loadAgents() })
</script>

<style scoped>
@import './common.css';

/* 页面特有样式 */
.batch-bar {
  display: flex; gap: var(--space-sm); margin-bottom: var(--space-lg); flex-wrap: wrap;
}

.table-wrap {
  overflow: auto;
  max-height: calc(100vh - 340px);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}

.cell-input {
  width: 100%; border: 1px solid transparent; background: transparent;
  padding: 4px 6px; font-size: var(--font-size-sm); border-radius: var(--radius-sm);
}
.cell-input:focus { border-color: var(--green); outline: none; background: #fff; }
select.cell-input { font-size: var(--font-size-xs); }

.panel { border: 1px solid var(--line); background: #fff; border-radius: var(--radius-sm); padding: 14px; }
.panel-title { font-weight: 600; margin-bottom: 10px; }

.upload-section { padding: 20px 0; }

@media (max-width: 800px) {
  .batch-bar { flex-direction: column; }
}
</style>
