<template>
  <div>
    <div class="section">
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
      <div v-if="tab==='quick'">
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
                    <NSelect filterable v-model:value="row[col.field_code]" :options="entitySelectOptions" placeholder="选择单位简称" size="tiny" />
                  </template>
                  <template v-else-if="col.field_code === 'account_match_key'">
                    <input v-model="row[col.field_code]" class="cell-input" placeholder="账户编号/名称" />
                  </template>
                  <template v-else-if="col.data_type === 'number'">
                    <input v-model="row[col.field_code]" type="number" step="0.01" class="cell-input" />
                  </template>
                  <template v-else-if="col.field_code === 'business_date'">
                    <NDatePicker v-model:value="row[col.field_code]" type="date" value-format="yyyy-MM-dd" size="tiny" style="width:100%" />
                  </template>
                  <template v-else>
                    <input v-model="row[col.field_code]" class="cell-input" :placeholder="col.field_name_cn" />
                  </template>
                </td>
                <td><NButton secondary size="small" @click="editableRows.splice(idx, 1)" title="删除行">x</NButton></td>
              </tr>
              <tr v-if="!editableRows.length">
                <td :colspan="visibleColumns.length + 1" style="text-align:center;color:var(--muted);padding:30px">点击下方"添加行"开始录入</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="bottom-bar">
          <NButton secondary @click="addRow()">+ 添加行</NButton>
          <NButton secondary @click="addRows(5)">+ 添加5行</NButton>
          <NButton type="primary" @click="doSave" :disabled="saving">{{ saving ? '保存中...' : '保存到暂存区' }}</NButton>
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
            <NButton type="primary" @click="doUpload" :disabled="uploading">{{ uploading ? '上传中...' : '上传预览' }}</NButton>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NDatePicker, NSelect, NButton } from 'naive-ui'
import { useRouter } from 'vue-router'
import * as api from '@/api/manual'
import * as master from '@/api/master'

const router = useRouter()

const schemes = ref([])
const fieldPool = ref([])
const currentSchemeCode = ref('manual_multi_subject_basic')
const entities = ref([])
const entitySelectOptions = computed(() => entities.value.map(e => ({ label: e.entity_name, value: e.entity_name })))
const tab = ref('quick')
const editableRows = ref([])
const saving = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const uploadResult = ref(null)

const currentScheme = computed(() => schemes.value.find(s => s.scheme_code === currentSchemeCode.value))
const visibleColumns = computed(() => {
  if (!currentScheme.value) return []
  return currentScheme.value.selected_fields
    .map(fc => fieldPool.value.find(f => f.field_code === fc))
    .filter(Boolean)
    .map(f => ({ ...f, minWidth: f.is_core ? '100px' : '80px' }))
})

function addRow(count = 1) {
  for (let i = 0; i < count; i++) {
    const row = {}
    for (const col of visibleColumns.value) {
      if (col.field_code === 'entity_match_key') {
        row[col.field_code] = ''
      } else if (col.field_code === 'business_date') {
        row[col.field_code] = new Date().toISOString().slice(0, 10)
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
    alert(`保存成功！共 ${result.inserted_rows} 条记录已保存`)
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

onMounted(() => { loadData() })
</script>

<style scoped>
@import './common.css';

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

.upload-section { padding: 20px 0; }
</style>
