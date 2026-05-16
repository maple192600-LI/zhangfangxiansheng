<template>
  <div class="section report-print-root table-workspace-page">
    <div class="section-title">
      <h3>{{ title }}</h3>
      <span>{{ subtitle }}</span>
    </div>

    <div class="filters-bar">
      <template v-if="dateMode === 'range'">
        <NDatePicker :value="startDateTs" @update:value="v => startDateTs = v" type="date" clearable style="width:150px" />
        <span style="color:var(--muted);font-size:13px">至</span>
        <NDatePicker :value="endDateTs" @update:value="v => endDateTs = v" type="date" clearable style="width:150px" />
      </template>
      <template v-else-if="dateMode === 'year'">
        <NSelect v-model:value="selYear" :options="yearSelectOptions" filterable style="width:100px" />
      </template>
      <template v-else>
        <NSelect v-model:value="selYear" :options="yearSelectOptions" filterable style="width:100px" />
        <NSelect v-model:value="selMonth" :options="monthSelectOptions" filterable style="width:80px" />
      </template>
      <MasterEntitySelect v-model="entityId" :entities="entities" />
      <div style="flex:1"></div>
      <div class="btn-row">
        <NButton secondary @click="doExport">导出</NButton>
        <NButton secondary @click="handlePrint">打印</NButton>
        <NButton type="primary" @click="loadData">生成报表</NButton>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>正在加载...</p>
    </div>

    <div v-else-if="hasColumns" class="table-workspace-main">
      <AdvancedDataTable
        :columns="appliedColumns"
        :data="displayRows"
        :pagination="false"
        fill-parent
        show-toolbar
        :density="tableDensity"
        :table-key="effectiveTableKey"
        show-column-settings
        show-reset-preferences
        :hidden-fields="hiddenFields"
        :all-columns-for-settings="tabulatorColumns"
        empty-text="暂无数据，请调整查询条件后重试"
        :row-key="'__row_key'"
        :row-class="rowClassFn"
        @density-change="onDensityChange"
        @column-width-change="onColumnWidthChange"
        @column-order-change="onColumnOrderChange"
        @column-visibility-change="onColumnVisibilityChange"
        @preferences-reset="onPreferencesReset"
      />
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">📊</div>
      <h4 v-if="!templateLoaded">正在加载...</h4>
      <template v-else>
        <h4>暂无报表数据</h4>
        <p>选择条件后点击"生成报表"</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NDatePicker, NSelect, NButton } from 'naive-ui'
import MasterEntitySelect from '@/components/MasterEntitySelect.vue'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'
import { useReportPrint } from '@/composables/useReportPrint'
import { emptyDashFormatter, moneyFormatter } from '@/utils/tabulatorFormatters'
import { adaptTemplateColumns } from '@/composables/useColumnAdapter'
import {
  getPreferences,
  applyPreferences,
  saveColumnWidth,
  saveColumnVisibility,
  saveColumnOrder,
  saveDensity,
  resetPreferences,
} from '@/composables/useAdvancedTablePreferences'
import * as reportApi from '@/api/report'
import * as master from '@/api/master'
import { exportReport } from '@/api/export'
import { useTemplateColumns } from '@/composables/useTemplateColumns'
import { getReportFilename } from '@/utils/reportFilename'

const props = defineProps({
  title: String,
  subtitle: { type: String, default: '' },
  reportType: String,
  exportType: String,
  dateMode: { type: String, default: 'range' },
  defaultHeaders: { type: Array, default: () => [] },
  defaultKeys: { type: Array, default: () => [] },
  moneyKeys: { type: Array, default: () => [] },
  tableKey: { type: String, default: '' },
  addFrontendTotal: { type: Boolean, default: false },
})

const { handlePrint } = useReportPrint()

const today = new Date()
const todayStr = today.toISOString().slice(0, 10)
const startDate = ref(todayStr)
const endDate = ref(todayStr)
const selYear = ref(today.getFullYear())
const selMonth = ref(today.getMonth() + 1)
const entityId = ref(null)
const entities = ref([])
const rows = ref([])
const loading = ref(false)

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

const yearSelectOptions = computed(() => {
  const y = today.getFullYear()
  return [y - 2, y - 1, y, y + 1].map(v => ({ label: `${v}年`, value: v }))
})
const monthSelectOptions = Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1}月`, value: i + 1 }))

const { templateColumns, templateLoaded, loadTemplate } = useTemplateColumns(props.reportType, { loadExcelHtml: false })

const moneyFieldsSet = new Set(props.moneyKeys)

const DEFAULT_COLUMNS = computed(() => {
  if (!props.defaultHeaders.length || !props.defaultKeys.length) return []
  if (props.defaultHeaders.length !== props.defaultKeys.length) {
    console.warn(`[TemplateReport] defaultHeaders and defaultKeys length mismatch for "${props.reportType}"`)
    return []
  }
  return props.defaultHeaders.map((header, i) => {
    const field = props.defaultKeys[i]
    const isMoney = moneyFieldsSet.has(field)
    return {
      field,
      title: header,
      width: isMoney ? 140 : 160,
      hozAlign: isMoney ? 'right' : undefined,
      formatter: isMoney ? moneyFormatter : emptyDashFormatter,
      headerSort: false,
    }
  })
})

const tabulatorColumns = computed(() => {
  const cols = adaptTemplateColumns(templateColumns.value, DEFAULT_COLUMNS.value, {
    moneyFields: moneyFieldsSet,
  })
  return cols.map(col => ({ ...col, headerSort: false }))
})

const hasColumns = computed(() => tabulatorColumns.value.length > 0)

const effectiveTableKey = props.tableKey || `template-report-${props.reportType}`

const preferencesVersion = ref(0)
const tableDensity = ref(getPreferences(effectiveTableKey).density || 'default')

function touchPreferences() { preferencesVersion.value++ }

const appliedColumns = computed(() => {
  preferencesVersion.value
  return applyPreferences(tabulatorColumns.value, getPreferences(effectiveTableKey))
})

const hiddenFields = computed(() => {
  preferencesVersion.value
  const prefs = getPreferences(effectiveTableKey)
  const visibility = prefs.visibility || {}
  return Object.entries(visibility).filter(([, v]) => !v).map(([f]) => f)
})

function onDensityChange(value) {
  tableDensity.value = value
  saveDensity(effectiveTableKey, value)
}

function onColumnWidthChange({ field, width }) {
  saveColumnWidth(effectiveTableKey, field, width)
}

function onColumnOrderChange(order) {
  saveColumnOrder(effectiveTableKey, order)
}

function onColumnVisibilityChange({ field, visible }) {
  saveColumnVisibility(effectiveTableKey, field, visible)
  touchPreferences()
}

function onPreferencesReset() {
  resetPreferences(effectiveTableKey)
  tableDensity.value = 'default'
  touchPreferences()
}

function rowClassFn(row) {
  if (row.is_total) return 'total-row'
  if (row.is_subtotal) return 'subtotal-row'
  return ''
}

const displayRows = computed(() => {
  const base = rows.value.map((r, idx) => ({
    ...r,
    __row_key: r.__row_key || `${props.reportType}-${idx}`,
  }))
  if (!props.addFrontendTotal || base.length <= 1) return base
  const totals = {}
  for (const key of props.moneyKeys) {
    totals[key] = base.reduce((sum, r) => sum + (Number(r[key]) || 0), 0)
  }
  return [...base, { entity_name: '合计', ...totals, is_total: true, __row_key: `${props.reportType}-__total__` }]
})

async function loadData() {
  loading.value = true
  try {
    let res
    if (props.dateMode === 'year') {
      res = await reportApi.getReport(props.reportType, { year: selYear.value, entity_id: entityId.value })
    } else if (props.dateMode === 'month') {
      res = await reportApi.getReport(props.reportType, { year: selYear.value, month: selMonth.value, entity_id: entityId.value })
    } else {
      const params = { start_date: startDate.value, end_date: endDate.value }
      if (entityId.value) params.entity_id = entityId.value
      res = await reportApi.getReport(props.reportType, params)
    }
    rows.value = res || []
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function doExport() {
  try {
    const params = { export_type: props.exportType }
    if (props.dateMode === 'year') {
      params.year = selYear.value
    } else if (props.dateMode === 'month') {
      params.year = selYear.value
      params.month = selMonth.value
    } else {
      params.start_date = startDate.value
      params.end_date = endDate.value
    }
    if (entityId.value) params.entity_id = entityId.value
    const blob = await exportReport(params)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = getReportFilename(props.exportType, {
      startDate: startDate.value,
      endDate: endDate.value,
      year: props.dateMode === 'year' || props.dateMode === 'month' ? selYear.value : undefined,
      month: props.dateMode === 'month' ? selMonth.value : undefined,
    })
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert('导出失败: ' + (e.message || e)) }
}

onMounted(async () => {
  try { entities.value = (await master.getAccountsTree()) || [] } catch {}
  loadTemplate()
  loadData()
})
</script>

<style scoped>
@import '../views/common.css';
</style>
