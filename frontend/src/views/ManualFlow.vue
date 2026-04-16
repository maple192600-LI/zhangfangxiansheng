<template>
  <div class="manual-flow">
    <!-- 顶部操作栏 -->
    <div class="top-bar">
      <div class="top-left">
        <select v-model="currentSchemeCode" class="filter" @change="onSchemeChange">
          <option v-for="s in schemes" :key="s.scheme_code" :value="s.scheme_code">{{ s.scheme_name }}</option>
        </select>
        <button class="btn btn-secondary" @click="doExportTemplate">下载录入模板</button>
      </div>
      <div class="top-right">
        <button class="btn" :class="tab==='quick'?'btn-primary':'btn-secondary'" @click="tab='quick'">快速录入</button>
        <button class="btn" :class="tab==='upload'?'btn-primary':'btn-secondary'" @click="tab='upload'">Excel 上传</button>
      </div>
    </div>

    <!-- Track A: 快速录入 -->
    <div v-if="tab==='quick'" class="quick-section">
      <!-- 批量上下文 -->
      <div class="batch-bar">
        <select v-model="batchCtx.entity_id" class="filter" style="width:140px">
          <option :value="null">批量法人（可选）</option>
          <option v-for="e in entities" :key="e.entity_id" :value="e.entity_id">{{ e.entity_name }}</option>
        </select>
        <select v-model="batchCtx.account_id" class="filter" style="width:140px">
          <option :value="null">批量账户（可选）</option>
          <optgroup v-for="g in entityGroups" :key="g.entity_id" :label="g.entity_name">
            <option v-for="a in g.accounts" :key="a.id" :value="a.id">{{ a.account_code }} {{ a.account_alias }}</option>
          </optgroup>
        </select>
        <input v-model="batchCtx.date" type="date" class="filter" style="width:130px" title="批量日期" />
      </div>

      <!-- 可编辑表格 -->
      <div class="table-wrap">
        <table class="data-table">
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
                    <option value="">选法人</option>
                    <option v-for="e in entities" :key="e.entity_id" :value="e.entity_name">{{ e.entity_name }}</option>
                  </select>
                </template>
                <template v-else-if="col.field_code === 'account_match_key'">
                  <input v-model="row[col.field_code]" class="cell-input" placeholder="编码/别名" />
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
              <td><button class="btn btn-secondary btn-sm" @click="editableRows.splice(idx,1)" title="删除行">x</button></td>
            </tr>
            <tr v-if="!editableRows.length">
              <td :colspan="visibleColumns.length + 1" class="empty">点击下方"添加行"开始录入</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="bottom-bar">
        <button class="btn btn-secondary" @click="addRow">+ 添加行</button>
        <button class="btn btn-secondary" @click="addRows(5)">+ 添加5行</button>
        <button class="btn btn-primary" @click="doSave" :disabled="saving">{{ saving ? '保存中...' : '保存到暂存区' }}</button>
        <span class="count-info">共 {{ editableRows.length }} 行</span>
      </div>
    </div>

    <!-- Track B: Excel 上传 -->
    <div v-if="tab==='upload'" class="upload-section">
      <div class="upload-area" @dragover.prevent @drop.prevent="onDrop">
        <div class="upload-icon">+</div>
        <p>将 Excel 文件拖拽到此处，或点击选择文件</p>
        <input ref="fileInput" type="file" accept=".xls,.xlsx,.csv" style="display:none" @change="onFileChange" />
        <button class="btn btn-secondary" @click="$refs.fileInput.click()">选择文件</button>
      </div>
      <div v-if="uploadFile" class="file-info">
        <span>{{ uploadFile.name }} ({{ (uploadFile.size/1024).toFixed(1) }}KB)</span>
        <button class="btn btn-primary" @click="doUpload" :disabled="uploading">{{ uploading ? '上传中...' : '上传并预览' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '@/api/manual'
import * as master from '@/api/master'

const router = useRouter()

const schemes = ref([])
const fieldPool = ref([])
const currentSchemeCode = ref('manual_multi_subject_basic')
const entities = ref([])
const tab = ref('quick')
const editableRows = ref([])
const saving = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const fileInput = ref(null)

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
    router.push({ path: '/upload-preview', query: { batch_code: result.batch_code } })
  } catch (e) { alert('上传失败: ' + (e.message || e)) }
  uploading.value = false
}

function doExportTemplate() {
  // 使用blob下载
  api.exportManualTemplate(currentSchemeCode.value).then(blob => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `手工流水模板_${currentSchemeCode.value}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  }).catch(e => alert('下载失败: ' + (e.message || e)))
}

onMounted(loadData)
</script>

<style scoped>
.manual-flow { display: flex; flex-direction: column; height: calc(100vh - 80px); }

.top-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: rgba(251,250,247,0.95);
  border: 1px solid var(--line); border-radius: var(--radius);
  margin-bottom: 10px; gap: 10px; flex-wrap: wrap;
}
.top-left, .top-right { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

.batch-bar {
  display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap;
}

.table-wrap { flex: 1; overflow: auto; background: #fff; border: 1px solid var(--line); border-radius: var(--radius); }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
.data-table th {
  position: sticky; top: 0; z-index: 2; background: #f5f2eb;
  text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--line);
  color: #5b635e; font-weight: 600; font-size: 12px;
}
.data-table td { padding: 4px 6px; border-bottom: 1px solid #f0ede6; }
.data-table tr:hover { background: #faf8f3; }

.cell-input {
  width: 100%; border: 1px solid transparent; background: transparent;
  padding: 4px 6px; font-size: 13px; border-radius: 6px;
}
.cell-input:focus { border-color: var(--green); outline: none; background: #fff; }
select.cell-input { font-size: 12px; }

.bottom-bar {
  display: flex; gap: 8px; align-items: center; padding: 10px 0; flex-wrap: wrap;
}
.count-info { color: var(--muted); font-size: 12px; margin-left: auto; }

.upload-section { padding: 40px 20px; }
.upload-area {
  border: 2px dashed #d0c9bc; border-radius: 16px; padding: 60px 20px;
  text-align: center; color: var(--muted); background: #faf8f3; cursor: pointer;
}
.upload-area:hover { border-color: var(--green); }
.upload-icon { font-size: 40px; color: var(--green); margin-bottom: 10px; }
.file-info {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 14px; padding: 10px 14px; background: #edf4ea; border-radius: 10px;
}

.btn-sm { padding: 4px 8px; font-size: 12px; }
.empty { text-align: center; color: var(--muted); padding: 30px; font-size: 14px; }

@media (max-width: 800px) {
  .top-bar { flex-direction: column; align-items: flex-start; }
  .batch-bar { flex-direction: column; }
}
</style>
