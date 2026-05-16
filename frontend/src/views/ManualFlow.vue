<template>
  <div class="section table-workspace-page">
    <div class="section-title">
      <h3>手工流水录入</h3>
      <span>快速录入或 Excel 上传手工流水数据</span>
    </div>
    <div class="filters-bar">
      <div style="flex:1"></div>
      <div class="btn-row">
        <NButton secondary @click="doExportTemplate">下载录入模板</NButton>
        <NButton :type="tab==='quick'?'primary':'default'" @click="tab='quick'">快速录入</NButton>
        <NButton :type="tab==='upload'?'primary':'default'" @click="tab='upload'">Excel 上传</NButton>
      </div>
    </div>

    <!-- Track A: 快速录入 -->
    <div v-if="tab==='quick'" class="mf-edit-area">
      <div class="mf-toolbar adt-no-print">
        <span class="mf-toolbar-label"><span class="adt-toolbar-dot"></span>可编辑表格</span>
        <span class="mf-toolbar-count">{{ rowCountText }}</span>
        <span class="adt-toolbar-sep"></span>
        <NButton secondary size="small" @click="onAddRow">+ 添加行</NButton>
        <NButton secondary size="small" @click="onAddRows(5)">+ 添加5行</NButton>
        <NButton secondary size="small" @click="onClearData" :disabled="rowCount === 0">清空</NButton>
        <span style="flex:1"></span>
        <span class="mf-toolbar-hint">可从 Excel 复制粘贴多行数据</span>
        <NButton type="primary" size="small" @click="doSave" :disabled="saving || rowCount === 0">{{ saving ? '保存中...' : '保存到暂存区' }}</NButton>
      </div>

      <div class="mf-table-main">
        <AdvancedDataTable
          ref="adtRef"
          :columns="tabulatorColumns"
          :data="[]"
          :rowKey="rowIdField"
          :pagination="false"
          :showToolbar="false"
          :editable="true"
          :editMode="'cell'"
          :enableClipboard="true"
          :emptyText="'点击上方「添加行」开始录入，或直接从 Excel 复制粘贴数据'"
          :height="'100%'"
          :fillParent="true"
          @cellEdited="onCellEdited"
          @paste="onPaste"
          @tableReady="onTableReady"
        />
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
          <NButton type="primary" @click="doUpload" :disabled="uploading">{{ uploading ? '上传中...' : '上传预览' }}</NButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NButton } from 'naive-ui'
import { useRouter } from 'vue-router'
import * as api from '@/api/manual'
import * as master from '@/api/master'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'

const router = useRouter()
const rowIdField = '_row_id'
let idCounter = 0

const schemes = ref([])
const fieldPool = ref([])
const currentSchemeCode = ref('manual_multi_subject_basic')
const entities = ref([])
const entityOptions = computed(() => entities.value.map(e => e.entity_name))
const tab = ref('quick')
const saving = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const dirtyRowIds = ref(new Set())
const adtRef = ref(null)
const rowCount = ref(0)

const currentScheme = computed(() => schemes.value.find(s => s.scheme_code === currentSchemeCode.value))

const visibleColumns = computed(() => {
  if (!currentScheme.value) return []
  return currentScheme.value.selected_fields
    .map(fc => fieldPool.value.find(f => f.field_code === fc))
    .filter(Boolean)
})

const tabulatorColumns = computed(() => {
  const cols = visibleColumns.value.map(f => {
    const col = {
      field: f.field_code,
      title: f.field_name_cn,
      minWidth: f.is_core ? 120 : 90,
      resizable: true,
    }

    if (f.field_code === 'entity_match_key') {
      col.editor = 'list'
      col.editorParams = {
        values: entityOptions.value,
        autocomplete: true,
        allowEmpty: true,
        listOnEmpty: true,
        clearable: true,
        defaultValue: '',
      }
      col.formatter = 'plaintext'
    } else if (f.field_code === 'business_date') {
      col.editor = 'input'
      col.formatter = 'plaintext'
    } else if (f.data_type === 'number') {
      col.editor = 'number'
      col.editorParams = { step: 0.01 }
      col.hozAlign = 'right'
      col.formatter = 'plaintext'
    } else {
      col.editor = 'input'
      col.formatter = 'plaintext'
    }

    return col
  })

  cols.push({
    field: '__action',
    title: '',
    width: 50,
    hozAlign: 'center',
    headerSort: false,
    resizable: false,
    formatter: () => '<button class="mf-row-del" title="删除行">✕</button>',
    cellClick: (_e, cell) => {
      const rowId = cell.getRow()?.getData()?.[rowIdField]
      if (rowId != null) {
        onDeleteRow(rowId)
      }
    },
  })

  return cols
})

function newEmptyRow() {
  idCounter++
  const row = { [rowIdField]: idCounter }
  for (const col of visibleColumns.value) {
    if (col.field_code === 'business_date') {
      row[col.field_code] = new Date().toISOString().slice(0, 10)
    } else {
      row[col.field_code] = ''
    }
  }
  return row
}

function refreshRowCount() {
  if (adtRef.value?.isReady) {
    rowCount.value = adtRef.value.getData().length
  }
}

function onTableReady() {
  refreshRowCount()
}

function onAddRow() {
  if (!adtRef.value?.isReady) return
  adtRef.value.addRow(newEmptyRow(), 'bottom')
  refreshRowCount()
}

function onAddRows(n) {
  if (!adtRef.value?.isReady) return
  for (let i = 0; i < n; i++) {
    const row = newEmptyRow()
    adtRef.value.addRow(row, 'bottom')
  }
  refreshRowCount()
}

function onDeleteRow(rowId) {
  if (!adtRef.value?.isReady) return
  dirtyRowIds.value.delete(rowId)
  dirtyRowIds.value = new Set(dirtyRowIds.value)
  adtRef.value.deleteRow(rowId)
  refreshRowCount()
}

function onClearData() {
  if (!adtRef.value?.isReady) return
  adtRef.value.clearData()
  dirtyRowIds.value = new Set()
  rowCount.value = 0
}

function onCellEdited({ rowData }) {
  const rowId = rowData?.[rowIdField]
  if (rowId != null) {
    dirtyRowIds.value = new Set([...dirtyRowIds.value, rowId])
  }
  refreshRowCount()
}

function onPaste() {
  refreshRowCount()
}

const rowCountText = computed(() => {
  const dirty = dirtyRowIds.value.size
  if (dirty > 0) return `共 ${rowCount.value} 行，${dirty} 行已编辑`
  return `共 ${rowCount.value} 行`
})

function validateRows(rows) {
  const errors = []
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i]
    const allEmpty = Object.entries(r).every(([k, v]) => k === rowIdField || k === '__action' || v === '' || v == null)
    if (allEmpty) continue

    const rowNum = i + 1
    if (r.business_date && !/^\d{4}-\d{2}-\d{2}$/.test(String(r.business_date))) {
      errors.push(`第 ${rowNum} 行：日期格式错误，应为 yyyy-MM-dd`)
    }
    const numericFields = ['income_amount', 'expense_amount', 'previous_balance_input', 'ending_balance_input']
    for (const f of numericFields) {
      if (r[f] !== '' && r[f] != null) {
        const num = Number(r[f])
        if (isNaN(num)) {
          errors.push(`第 ${rowNum} 行：${f} 必须是数字`)
        }
      }
    }
  }
  return errors
}

async function doSave() {
  if (!adtRef.value?.isReady) return

  const allRows = adtRef.value.getData()
  const nonEmptyRows = allRows.filter(r => {
    return Object.entries(r).some(([k, v]) => k !== rowIdField && k !== '__action' && v !== '' && v != null)
  })

  if (!nonEmptyRows.length) {
    alert('请至少录入一条有效数据')
    return
  }

  const errors = validateRows(nonEmptyRows)
  if (errors.length) {
    alert('数据校验失败：\n' + errors.join('\n'))
    return
  }

  saving.value = true
  try {
    const rows = nonEmptyRows.map(r => {
      const obj = {}
      for (const [k, v] of Object.entries(r)) {
        if (k === rowIdField || k === '__action') continue
        if (['income_amount', 'expense_amount', 'previous_balance_input', 'ending_balance_input'].includes(k)) {
          obj[k] = v === '' || v == null ? null : Number(v)
        } else {
          obj[k] = v
        }
      }
      return obj
    })
    const result = await api.saveQuickEntry({ scheme_code: currentSchemeCode.value, rows })
    alert(`保存成功！共 ${result.inserted_rows} 条记录已保存`)
    onClearData()
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
  alert('手工 Excel 解析器生成将在后续阶段接入通用 Agent，目前请使用快速录入或模板导出。')
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

onMounted(() => { loadData() })
</script>

<style scoped>
@import './common.css';

.mf-edit-area {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mf-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--line-table);
  background: var(--thead-bg);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  font-size: var(--font-size-sm);
  user-select: none;
  flex-shrink: 0;
}

.mf-toolbar-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--text-secondary);
}

.mf-toolbar-count {
  color: var(--muted);
  font-size: var(--font-size-xs);
}

.mf-toolbar-hint {
  color: var(--muted);
  font-size: var(--font-size-xs);
}

.mf-table-main {
  flex: 1;
  min-height: 300px;
  overflow: hidden;
}

.upload-section { padding: 20px 0; }
</style>
