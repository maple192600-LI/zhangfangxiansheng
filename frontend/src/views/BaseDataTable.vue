<template>
  <div class="report-print-root-wrapper">
  <div class="section report-print-root table-workspace-page">
    <div class="section-title">
      <h3>基础数据表</h3>
      <span>所有后续报表的统一底座</span>
    </div>

    <div class="filters-bar filters-bar-dense">
      <NDatePicker v-model:value="filters.date_from" type="date" value-format="yyyy-MM-dd" clearable />
      <span style="color:var(--muted);font-size:13px">至</span>
      <NDatePicker v-model:value="filters.date_to" type="date" value-format="yyyy-MM-dd" clearable />
      <MasterEntitySelect v-model="filters.entity_id" :entities="entities" />
      <NSelect v-model:value="filters.direction" :options="directionOptions" placeholder="全部方向" clearable filterable class="filter-select-sm" :consistent-menu-width="false" />
      <input v-model="filters.keyword" class="filter" placeholder="搜索摘要/对方" style="width:140px" />
      <div class="filter-spacer"></div>
      <div class="btn-row">
        <NButton v-if="selectedIds.length" type="error" @click="doBatchDelete">删除选中 ({{ selectedIds.length }})</NButton>
        <NButton secondary @click="doRebuild" :disabled="rebuilding">{{ rebuilding ? '重建中...' : '重建余额' }}</NButton>
        <NButton secondary @click="doExport('base_data')">导出</NButton>
        <NButton secondary @click="handlePrint">打印</NButton>
        <NButton type="primary" @click="page = 1; loadData()">生成报表</NButton>
      </div>
    </div>

    <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
    <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在加载数据...</p></div>

    <div v-else-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>

    <div v-else class="table-workspace-main">
      <AdvancedDataTable
        ref="tableRef"
        :columns="tabulatorColumns"
        :data="rows"
        :pagination="false"
        :loading="false"
        :enable-selection="true"
        row-key="id"
        fill-parent
        empty-text="暂无数据，请先录入或导入流水"
        @selection-change="onSelectionChange"
      />
    </div>

    <div class="bottom-bar" v-if="total > 0 && !templateExcelHtml && !loading">
      <span class="count-info">共 {{ total }} 条，第 {{ page }} / {{ totalPages }} 页</span>
      <NButton secondary size="small" :disabled="page <= 1" @click="page--; loadData()">上一页</NButton>
      <NButton secondary size="small" :disabled="page >= totalPages" @click="page++; loadData()">下一页</NButton>
    </div>
  </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NDatePicker, NSelect, NButton } from 'naive-ui'
import MasterEntitySelect from '@/components/MasterEntitySelect.vue'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'
import { useReportPrint } from '@/composables/useReportPrint'
import { emptyDashFormatter, moneyFormatter, directionFormatter, abnormalCodeFormatter } from '@/utils/tabulatorFormatters'
import * as api from '@/api/report'
import * as master from '@/api/master'
import { exportReport } from '@/api/export'
import { useTemplateColumns } from '@/composables/useTemplateColumns'
import { getReportFilename } from '@/utils/reportFilename'

const { handlePrint } = useReportPrint()

const entities = ref([])
const rows = ref([])
const total = ref(0)
const page = ref(1)
const totalPages = ref(1)
const rebuilding = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const selectedIds = ref([])
const tableRef = ref(null)
const { templateColumns, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('base_data')

const MONEY_FIELD_SET = new Set(['income_amount', 'expense_amount', 'rolling_balance'])

const FALLBACK_COLUMNS = [
  { field: 'business_date', title: '日期', width: 110, formatter: emptyDashFormatter },
  { field: 'direction', title: '方向', width: 70, formatter: directionFormatter },
  { field: 'summary_text', title: '摘要', formatter: emptyDashFormatter },
  { field: 'counterparty_name', title: '对方', formatter: emptyDashFormatter },
  { field: 'income_amount', title: '收入金额', width: 120, hozAlign: 'right', formatter: moneyFormatter },
  { field: 'expense_amount', title: '支出金额', width: 120, hozAlign: 'right', formatter: moneyFormatter },
  { field: 'rolling_balance', title: '余额', width: 120, hozAlign: 'right', formatter: moneyFormatter },
]

const tabulatorColumns = computed(() => {
  if (templateColumns.value?.length) {
    return templateColumns.value.map(col => {
      const def = { field: col.field_key, title: col.header_name }
      if (col.width) def.width = col.width
      if (col.align) def.hozAlign = col.align
      if (col.field_key === 'direction') def.formatter = directionFormatter
      else if (MONEY_FIELD_SET.has(col.field_key)) def.formatter = moneyFormatter
      else if (col.field_key === 'abnormal_code') def.formatter = abnormalCodeFormatter
      else def.formatter = emptyDashFormatter
      return def
    })
  }
  return FALLBACK_COLUMNS
})

function onSelectionChange(data) {
  selectedIds.value = data.map(r => r.id)
}

async function doBatchDelete() {
  if (!selectedIds.value.length) return
  if (!confirm(`确定删除选中的 ${selectedIds.value.length} 条数据？此操作不可撤销。`)) return
  try {
    const result = await api.batchDeleteBaseData(selectedIds.value)
    alert(`成功删除 ${result.deleted} 条`)
    selectedIds.value = []
    tableRef.value?.clearSelection()
    loadData()
  } catch (e) { alert('删除失败: ' + (e.message || '')) }
}

const directionOptions = [
  { label: '收入', value: 'income' },
  { label: '支出', value: 'expense' },
]
const filters = ref({ date_from: null, date_to: null, entity_id: null, direction: null, keyword: '' })

async function loadData() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { page: page.value, page_size: 50 }
    const f = filters.value
    if (f.date_from) params.date_from = f.date_from
    if (f.date_to) params.date_to = f.date_to
    if (f.entity_id) params.entity_id = f.entity_id
    if (f.direction) params.direction = f.direction
    if (f.keyword) params.keyword = f.keyword
    const result = await api.getBaseData(params)
    rows.value = result.items || []
    total.value = result.total || 0
    page.value = result.page || 1
    totalPages.value = result.total_pages || 1
  } catch (e) {
    errorMsg.value = '加载数据失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function doRebuild() {
  rebuilding.value = true
  try {
    const r = await api.rebuildBalance()
    alert(`余额重建完成：${r.affected_accounts} 个账户，${r.updated_events} 条记录`)
    loadData()
  } catch (e) { alert('重建失败: ' + (e.message || e)) }
  rebuilding.value = false
}

async function doExport(exportType) {
  try {
    const f = filters.value
    const blob = await exportReport({ export_type: exportType, start_date: f.date_from || undefined, end_date: f.date_to || undefined, entity_id: f.entity_id || undefined })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = getReportFilename('base_data', { startDate: f.date_from, endDate: f.date_to })
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert('导出失败: ' + (e.message || e)) }
}

onMounted(async () => {
  try { entities.value = (await master.getAccountsTree()) || [] } catch (e) {}
  loadTemplate()
  loadData()
})
</script>

<style scoped>
@import './common.css';
</style>
