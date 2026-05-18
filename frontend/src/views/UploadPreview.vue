<template>
  <div>
    <div class="section table-workspace-page">
      <div class="section-title">
        <h3>上传结果预览</h3>
        <span>检查数据质量，编辑异常行，确认无误后提交到基础数据</span>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" style="padding:40px;text-align:center;color:var(--muted)">加载中...</div>

      <!-- 解析器不可用提示 -->
      <div v-if="parserMessage" class="hint-panel" style="margin-bottom:14px">
        {{ parserMessage }}
      </div>

      <!-- 批次信息 -->
      <div v-if="!loading" class="metric-strip" style="margin-bottom:var(--space-lg)">
        <div class="metric">
          <div class="label">批次号</div>
          <div class="value" style="font-size:var(--font-size-md)">{{ batchInfo.batch_code }}</div>
        </div>
        <div class="metric">
          <div class="label">来源</div>
          <div class="value">{{ sourceLabel }}</div>
        </div>
        <div class="metric">
          <div class="label">文件名</div>
          <div class="value" style="font-size:var(--font-size-sm)">{{ batchInfo.source_name || '-' }}</div>
        </div>
        <div class="metric">
          <div class="label">总行数</div>
          <div class="value">{{ totalCount }}</div>
        </div>
        <div class="metric">
          <div class="label">有效</div>
          <div class="value text-green" @click="goToFirstAbnormal" style="cursor:pointer">{{ validCount }}</div>
        </div>
        <div class="metric">
          <div class="label" @click="goToFirstAbnormal" style="cursor:pointer">异常</div>
          <div class="value text-warn" @click="goToFirstAbnormal" style="cursor:pointer">{{ abnormalCount }}</div>
        </div>
      </div>

      <!-- 操作栏 -->
      <div v-if="!loading && allRows.length" class="filters-bar">
        <NButton secondary @click="$router.back()">返回</NButton>
        <NButton secondary @click="doValidate" :disabled="validating">{{ validating ? '校验中...' : '重新校验全部' }}</NButton>
        <div style="flex:1"></div>
        <NButton
          type="primary"
          @click="doCommit"
          :disabled="committing || abnormalCount > 0 || parserStatus === 'unavailable' || totalCount === 0"
        >
          {{ committing ? '提交中...' : '提交到基础数据' }}
        </NButton>
      </div>

      <!-- 统一表格 -->
      <div v-if="!loading && allRows.length" class="table-workspace-main">
        <AdvancedDataTable
          ref="adtRef"
          :columns="previewColumns"
          :data="allRows"
          :rowKey="'_row_no'"
          :pagination="true"
          :showToolbar="true"
          :tableKey="'upload-preview-unified'"
          :fillParent="true"
          :editable="true"
          :editMode="'cell'"
          :rowClass="rowClassFn"
          @cellEdited="onCellEdited"
          @tableReady="onTableReady"
        />
      </div>

      <!-- 无数据提示 -->
      <div v-if="!loading && !allRows.length && !parserMessage" style="padding:40px;text-align:center;color:var(--muted)">
        没有预览数据
      </div>

      <!-- 提交成功 -->
      <div v-if="commitResult" style="margin-top:var(--space-md)">
        <div style="background:var(--ok-bg);border:1px solid var(--ok-border);border-radius:var(--radius-sm);padding:var(--space-md);color:var(--ok-text)">
          提交成功！已将 {{ commitResult.committed_count }} 条数据写入基础数据表。
          <NButton type="primary" size="small" style="margin-left:12px" @click="$router.push({ name: 'base-data' })">查看基础数据表</NButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'
import * as previewApi from '@/api/importPreview'
import { fmtAmt } from '@/utils/format'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const batchCode = ref(route.query.batch_code || '')
const loading = ref(false)
const validating = ref(false)
const committing = ref(false)
const commitResult = ref(null)
const adtRef = ref(null)

const batchInfo = ref({})
const validRows = ref([])
const abnormalRows = ref([])
const parserStatus = ref(null)
const parserMessage = ref('')

const allRows = computed(() => {
  const rows = [...validRows.value, ...abnormalRows.value]
  rows.sort((a, b) => (a._row_no || 0) - (b._row_no || 0))
  return rows
})

const totalCount = computed(() => batchInfo.value.total_count || allRows.value.length)
const validCount = computed(() => batchInfo.value.valid_count ?? validRows.value.length)
const abnormalCount = computed(() => batchInfo.value.abnormal_count ?? abnormalRows.value.length)

const sourceLabel = computed(() => {
  const t = batchInfo.value.source_type
  if (t === 'bank') return '网银导入'
  if (t === 'manual_quick') return '手工快速录入'
  if (t === 'manual_excel' || t === 'manual_file') return '手工 Excel 上传'
  return t || '-'
})

const previewColumns = computed(() => [
  { field: '_row_no', title: '#', width: 50, headerSort: false, hozAlign: 'center', editable: false },
  {
    field: 'entity_code', title: '单位编码', minWidth: 100, editor: 'input',
    formatter: (c) => errorWrap(c, 'ENTITY_MATCH_FAILED', c.getValue() || ''),
  },
  { field: 'entity_name', title: '单位名称', minWidth: 100, editable: false, formatter: (c) => c.getValue() || '-' },
  {
    field: 'account_code', title: '账户编号', minWidth: 100, editor: 'input',
    formatter: (c) => errorWrap(c, 'ACCOUNT_MATCH_FAILED', c.getValue() || ''),
  },
  { field: 'account_name', title: '账户名称', minWidth: 100, editable: false, formatter: (c) => c.getValue() || '-' },
  {
    field: 'business_date', title: '日期', width: 110, editor: 'input',
    formatter: (c) => errorWrap(c, 'DATE_INVALID', c.getValue() || ''),
  },
  {
    field: 'summary_text', title: '摘要', minWidth: 120, editor: 'input',
  },
  {
    field: 'counterparty_name', title: '对方', width: 100, editor: 'input',
    formatter: (c) => c.getValue() || '-',
  },
  {
    field: 'income_amount', title: '收入', width: 110, hozAlign: 'right', editor: 'number',
    editorParams: { step: 0.01 },
    formatter: (c) => {
      const v = c.getValue()
      const val = v ? `<span style="color:var(--ok-text)">${fmtAmt(v)}</span>` : ''
      return errorWrap(c, 'AMOUNT_INVALID', val)
    },
  },
  {
    field: 'expense_amount', title: '支出', width: 110, hozAlign: 'right', editor: 'number',
    editorParams: { step: 0.01 },
    formatter: (c) => {
      const v = c.getValue()
      return v ? `<span style="color:var(--warn-text)">${fmtAmt(v)}</span>` : ''
    },
  },
  {
    field: 'abnormal_code', title: '状态', width: 120, hozAlign: 'center', editable: false,
    formatter: (c) => {
      const v = c.getValue()
      if (!v) return '<span class="tabulator-tag tabulator-tag-green">有效</span>'
      return `<span class="tabulator-tag tabulator-tag-orange">${v}</span>`
    },
  },
])

function hasError(cell, code) {
  const data = cell.getRow()?.getData()
  return data?._errors?.includes(code)
}

function errorWrap(cell, code, content) {
  if (hasError(cell, code)) {
    return `<span style="border:2px solid #e74c3c;border-radius:2px;padding:0 2px">${content}</span>`
  }
  return content
}

function rowClassFn(row) {
  if (row._errors && row._errors.length > 0) return 'row-abnormal'
  if (row.abnormal_code) return 'row-abnormal'
  return ''
}

function onTableReady() {}

async function onCellEdited({ field, value, rowData }) {
  if (!rowData?._row_no) return
  try {
    const result = await previewApi.updateRow(batchCode.value, rowData._row_no, { [field]: value })
    // Update local data
    const updated = result.row
    if (updated._errors && updated._errors.length > 0) {
      // Move to abnormal if was valid
      const vi = validRows.value.findIndex(r => r._row_no === rowData._row_no)
      if (vi >= 0) {
        validRows.value.splice(vi, 1)
        abnormalRows.value.push(updated)
        abnormalRows.value.sort((a, b) => a._row_no - b._row_no)
      } else {
        const ai = abnormalRows.value.findIndex(r => r._row_no === rowData._row_no)
        if (ai >= 0) abnormalRows.value[ai] = updated
      }
    } else {
      // Move to valid if was abnormal
      const ai = abnormalRows.value.findIndex(r => r._row_no === rowData._row_no)
      if (ai >= 0) {
        abnormalRows.value.splice(ai, 1)
        validRows.value.push(updated)
        validRows.value.sort((a, b) => a._row_no - b._row_no)
      } else {
        const vi = validRows.value.findIndex(r => r._row_no === rowData._row_no)
        if (vi >= 0) validRows.value[vi] = updated
      }
    }
    _updateCounts()
  } catch (e) {
    message.error('更新失败: ' + (e.message || e))
  }
}

function _updateCounts() {
  batchInfo.value = {
    ...batchInfo.value,
    valid_count: validRows.value.length,
    abnormal_count: abnormalRows.value.length,
    total_count: validRows.value.length + abnormalRows.value.length,
  }
}

async function loadPreview() {
  if (!batchCode.value) {
    message.warning('缺少批次号')
    return
  }
  loading.value = true
  try {
    const result = await previewApi.getPreview(batchCode.value)
    batchInfo.value = result
    validRows.value = result.parsed_rows || []
    abnormalRows.value = result.abnormal_rows || []
    parserStatus.value = result.parser_status || null
    parserMessage.value = result.parser_message || ''
    commitResult.value = null
  } catch (e) {
    message.error('加载预览失败: ' + (e.message || e))
  }
  loading.value = false
}

async function doValidate() {
  validating.value = true
  try {
    const result = await previewApi.validateAll(batchCode.value)
    batchInfo.value = {
      ...batchInfo.value,
      valid_count: result.valid_count,
      abnormal_count: result.abnormal_count,
    }
    if (result.abnormal_count === 0) {
      message.success('校验通过，所有数据均有效')
    } else {
      message.warning(`发现 ${result.abnormal_count} 条异常行`)
    }
    // Reload to refresh row states
    await loadPreview()
  } catch (e) {
    message.error('校验失败: ' + (e.message || e))
  }
  validating.value = false
}

async function doCommit() {
  if (abnormalCount.value > 0) {
    message.warning('存在异常行，请先处理')
    return
  }
  committing.value = true
  try {
    const result = await previewApi.commitPreview(batchCode.value)
    commitResult.value = result
    message.success('提交成功！')
  } catch (e) {
    message.error('提交失败: ' + (e.message || e))
  }
  committing.value = false
}

function goToFirstAbnormal() {
  if (!adtRef.value?.table) return
  const rows = adtRef.value.table.getRows()
  for (const row of rows) {
    const data = row.getData()
    if (data._errors?.length || data.abnormal_code) {
      adtRef.value.table.scrollToRow(row)
      break
    }
  }
}

onMounted(loadPreview)
</script>

<style scoped>
@import './common.css';

.row-abnormal :deep(.tabulator-cell) {
  background: #fff5f5 !important;
}

.cell-error {
  border: 2px solid #e74c3c !important;
  border-radius: 2px;
}

.hint-panel {
  padding: 10px 12px;
  border: 1px solid #e6c7b8;
  background: #fff4ef;
  color: #8b4f38;
  border-radius: var(--radius-sm);
}
</style>
