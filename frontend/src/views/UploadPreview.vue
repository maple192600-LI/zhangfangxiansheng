<template>
  <div>
    <div class="section table-workspace-page">
      <div class="section-title">
        <h3>流水预览</h3>
        <span>确认提交前检查数据质量</span>
      </div>

      <!-- 指标条 -->
      <div class="metric-strip" style="margin-bottom:var(--space-lg)">
        <div class="metric">
          <div class="label">批次号</div>
          <div class="value" style="font-size:var(--font-size-md)">{{ batchCode }}</div>
        </div>
        <div class="metric">
          <div class="label">总行数</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="metric">
          <div class="label">有效</div>
          <div class="value text-green">{{ validCount }}</div>
        </div>
        <div class="metric">
          <div class="label">异常</div>
          <div class="value text-warn">{{ abnormalCount }}</div>
        </div>
      </div>

      <!-- Tab -->
      <div class="filters-bar">
        <NButton :type="activeTab==='valid'?'primary':'default'" @click="activeTab='valid'">有效行 ({{ validCount }})</NButton>
        <NButton :type="activeTab==='abnormal'?'primary':'default'" @click="activeTab='abnormal'" v-if="abnormalCount">异常行 ({{ abnormalCount }})</NButton>
        <div style="flex:1"></div>
        <div class="btn-row">
          <NButton secondary @click="$router.push('/manual-flow')">返回录入</NButton>
          <NButton type="primary" @click="doCommit" :disabled="committing">{{ committing ? '提交中...' : '提交有效行到基础数据' }}</NButton>
        </div>
      </div>

      <!-- 有效行表格 -->
      <div v-if="activeTab==='valid'" class="table-workspace-main">
        <AdvancedDataTable
          :columns="validColumns"
          :data="validRows"
          :rowKey="'_row_no'"
          :pagination="true"
          :showToolbar="true"
          :tableKey="'upload-preview-valid'"
          :fillParent="true"
        />
      </div>

      <!-- 异常行表格 -->
      <div v-if="activeTab==='abnormal'" class="table-workspace-main">
        <AdvancedDataTable
          :columns="abnormalColumns"
          :data="abnormalRows"
          :rowKey="'_row_no'"
          :pagination="true"
          :showToolbar="true"
          :tableKey="'upload-preview-abnormal'"
          :fillParent="true"
        />
      </div>

      <!-- 提交结果 -->
      <div v-if="commitResult" style="margin-top:var(--space-md)">
        <div style="background:var(--ok-bg);border:1px solid var(--ok-border);border-radius:var(--radius-sm);padding:var(--space-md);color:var(--ok-text)" v-if="commitResult.committed_count > 0">
          提交成功！已写入 {{ commitResult.committed_count }} 条资金事件。
          <span v-if="commitResult.abnormal_count > 0">仍有 {{ commitResult.abnormal_count }} 条异常未处理。</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NButton } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'
import * as api from '@/api/manual'
import { fmtAmt } from '@/utils/format'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'

const route = useRoute()
const router = useRouter()

const batchCode = ref(route.query.batch_code || '')
const activeTab = ref('valid')
const validRows = ref([])
const abnormalRows = ref([])
const committing = ref(false)
const commitResult = ref(null)

const total = computed(() => validRows.value.length + abnormalRows.value.length)
const validCount = computed(() => validRows.value.length)
const abnormalCount = computed(() => abnormalRows.value.length)

const validColumns = [
  { field: '_row_no', title: '#', width: 50, headerSort: false, hozAlign: 'center' },
  { field: '_entity_name', title: '单位简称', minWidth: 100, formatter: (cell) => cell.getValue() || '-' },
  { field: '_account_name', title: '账户名称', minWidth: 120, formatter: (cell) => cell.getValue() || '-' },
  { field: 'business_date', title: '日期', width: 110 },
  { field: 'summary_text', title: '摘要', minWidth: 120 },
  { field: 'counterparty_name', title: '对方', width: 100, formatter: (cell) => cell.getValue() || '-' },
  {
    field: 'income_amount', title: '收入', width: 110, hozAlign: 'right',
    formatter: (cell) => {
      const v = cell.getValue()
      return v ? `<span style="color:var(--ok-text)">${fmtAmt(v)}</span>` : ''
    },
  },
  {
    field: 'expense_amount', title: '支出', width: 110, hozAlign: 'right',
    formatter: (cell) => {
      const v = cell.getValue()
      return v ? `<span style="color:var(--warn-text)">${fmtAmt(v)}</span>` : ''
    },
  },
  {
    field: 'status', title: '状态', width: 70, hozAlign: 'center',
    formatter: () => '<span class="tabulator-tag tabulator-tag-green">有效</span>',
  },
]

const abnormalColumns = [
  { field: '_row_no', title: '#', width: 50, headerSort: false, hozAlign: 'center' },
  { field: 'entity_match_key', title: '单位编码', width: 100, formatter: (cell) => cell.getValue() || '-' },
  { field: 'account_match_key', title: '账户编号', width: 100, formatter: (cell) => cell.getValue() || '-' },
  { field: 'business_date', title: '日期', width: 110, formatter: (cell) => cell.getValue() || '-' },
  { field: 'summary_text', title: '摘要', minWidth: 120, formatter: (cell) => cell.getValue() || '-' },
  {
    field: 'income_amount', title: '收入', width: 110, hozAlign: 'right',
    formatter: (cell) => {
      const v = cell.getValue()
      return v ? `<span style="color:var(--ok-text)">${fmtAmt(v)}</span>` : ''
    },
  },
  {
    field: 'expense_amount', title: '支出', width: 110, hozAlign: 'right',
    formatter: (cell) => {
      const v = cell.getValue()
      return v ? `<span style="color:var(--warn-text)">${fmtAmt(v)}</span>` : ''
    },
  },
  {
    field: 'abnormal_code', title: '异常代码', width: 90, hozAlign: 'center',
    formatter: (cell) => `<span class="tabulator-tag tabulator-tag-orange">${cell.getValue() || ''}</span>`,
  },
  {
    field: '__action', title: '操作', width: 70, hozAlign: 'center', headerSort: false,
    formatter: () => '<button class="exc-action-btn" title="修复">修复</button>',
    cellClick: (_e, cell) => {
      const rowNo = cell.getRow()?.getData()?._row_no
      if (rowNo != null) goFix(rowNo)
    },
  },
]

async function loadPreview() {
  if (!batchCode.value) return
  try {
    const result = await api.previewManual({ batch_code: batchCode.value })
    validRows.value = result.parsed_rows || []
    abnormalRows.value = result.abnormal_rows || []
    if (abnormalRows.value.length) activeTab.value = 'abnormal'
  } catch (e) { alert('加载预览失败: ' + (e.message || e)) }
}

async function doCommit() {
  committing.value = true
  try {
    const result = await api.commitManual({ batch_code: batchCode.value })
    commitResult.value = result
  } catch (e) { alert('提交失败: ' + (e.message || e)) }
  committing.value = false
}

function goFix(rowNo) {
  router.push({ path: '/manual-maintenance', query: { batch_code: batchCode.value, row_no: rowNo } })
}

onMounted(loadPreview)
</script>

<style scoped>
@import './common.css';
</style>
