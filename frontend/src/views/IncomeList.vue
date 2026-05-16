<template>
  <div class="section report-print-root table-workspace-page">
      <div class="section-title">
        <h3>收入明细表</h3>
        <span>按账户、日期汇总的收入明细视图</span>
      </div>
      <div class="filters-bar">
        <NDatePicker :value="startDateTs" @update:value="v => startDateTs = v" type="date" clearable />
        <span style="color:var(--muted);font-size:13px">至</span>
        <NDatePicker :value="endDateTs" @update:value="v => endDateTs = v" type="date" clearable />
        <MasterEntitySelect v-model="entityId" :entities="entities" />
        <div class="filter-spacer"></div>
        <NSpace>
          <NButton @click="doExport">导出</NButton>
          <NButton @click="handlePrint">打印</NButton>
          <NButton type="primary" @click="page = 1; loadData()">生成报表</NButton>
        </NSpace>
      </div>

      <div v-if="templateExcelHtml" class="table-workspace-main template-view">
        <div class="template-hint adt-no-print">
          当前使用 Excel 模板渲染，保留原始报表版式；高级表格交互未启用。
        </div>
        <div class="excel-host" v-html="templateExcelHtml"></div>
      </div>

      <div v-else class="table-workspace-main">
        <AdvancedDataTable
          :columns="tabulatorColumns"
          :data="rows"
          :pagination="false"
          fill-parent
          show-toolbar
          :total-rows="total"
          empty-text="暂无收入数据"
        />
      </div>

      <div class="bottom-bar" v-if="total > 0 && !templateExcelHtml">
        <span class="count-info">共 {{ total }} 条，第 {{ page }} / {{ totalPages }} 页</span>
        <NButton size="small" :disabled="page <= 1" @click="page--; loadData()">上一页</NButton>
        <NButton size="small" :disabled="page >= totalPages" @click="page++; loadData()">下一页</NButton>
      </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NDatePicker, NButton, NSpace } from 'naive-ui'
import MasterEntitySelect from '@/components/MasterEntitySelect.vue'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'
import { useReportPrint } from '@/composables/useReportPrint'
import { emptyDashFormatter, moneyFormatter } from '@/utils/tabulatorFormatters'
import * as api from '@/api/report'
import * as master from '@/api/master'
import { exportReport } from '@/api/export'
import { useTemplateColumns } from '@/composables/useTemplateColumns'
import { getReportFilename } from '@/utils/reportFilename'

const { handlePrint } = useReportPrint()

const today = new Date().toISOString().slice(0, 10)
const startDate = ref(today)
const endDate = ref(today)
const entityId = ref(null)
const entities = ref([])
const rows = ref([])
const total = ref(0)
const page = ref(1)
const totalPages = ref(1)
const { templateColumns, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('income_list')

function dateStringToTs(s) {
  if (!s) return null
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d).getTime()
}
function tsToDateString(ts) {
  if (ts == null) return ''
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const startDateTs = computed({
  get: () => dateStringToTs(startDate.value),
  set: (v) => { startDate.value = tsToDateString(v) }
})
const endDateTs = computed({
  get: () => dateStringToTs(endDate.value),
  set: (v) => { endDate.value = tsToDateString(v) }
})

const MONEY_FIELD_SET = new Set(['amount', 'rolling_balance'])

const DEFAULT_COLUMNS = [
  { field: 'business_date', title: '日期', width: 120, hozAlign: 'center', formatter: emptyDashFormatter },
  { field: 'entity_name', title: '单位简称', width: 120, formatter: emptyDashFormatter },
  { field: 'account_name', title: '账户名称', width: 150, formatter: emptyDashFormatter },
  { field: 'summary_text', title: '摘要', formatter: emptyDashFormatter },
  { field: 'counterparty_name', title: '对方', width: 120, formatter: emptyDashFormatter },
  { field: 'amount', title: '收入金额', width: 130, hozAlign: 'right', formatter: moneyFormatter },
  { field: 'rolling_balance', title: '余额', width: 130, hozAlign: 'right', formatter: moneyFormatter },
]

const tabulatorColumns = computed(() => {
  if (templateColumns.value?.length) {
    return templateColumns.value.map(col => {
      const def = { field: col.field_key, title: col.header_name }
      if (col.width) def.width = col.width
      if (col.align) def.hozAlign = col.align
      if (MONEY_FIELD_SET.has(col.field_key)) def.formatter = moneyFormatter
      else def.formatter = emptyDashFormatter
      return def
    })
  }
  return DEFAULT_COLUMNS
})

async function loadData() {
  try {
    const params = { start_date: startDate.value, end_date: endDate.value, page: page.value, page_size: 50 }
    if (entityId.value) params.entity_id = entityId.value
    const result = await api.getIncomeList(params)
    rows.value = result.items || []
    total.value = result.total || 0
    page.value = result.page || 1
    totalPages.value = result.total_pages || 1
  } catch (e) { console.error(e) }
}

async function doExport() {
  try {
    const blob = await exportReport({ export_type: 'income_list', start_date: startDate.value || undefined, end_date: endDate.value || undefined, entity_id: entityId.value || undefined })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = getReportFilename('income_list', { startDate: startDate.value, endDate: endDate.value }); a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert('导出失败: ' + (e.message || e)) }
}

onMounted(async () => {
  try { entities.value = (await master.getAccountsTree()) || [] } catch (e) {}
  loadData()
  loadTemplate()
})
</script>

<style scoped>
@import './common.css';
</style>
