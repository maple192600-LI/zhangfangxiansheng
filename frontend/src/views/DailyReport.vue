<template>
  <div class="section report-print-root table-workspace-page">
    <div class="section-title">
      <h3>资金日报</h3>
      <span>按单位汇总：期初/收入/支出/净变动/期末</span>
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
        <NButton type="primary" @click="loadReport">生成报表</NButton>
      </NSpace>
    </div>

    <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>

    <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在生成日报...</p></div>

    <div v-else-if="displayColumns.length" class="table-workspace-main">
      <AdvancedDataTable
        :columns="appliedColumns"
        :data="dataRows"
        :pagination="false"
        fill-parent
        show-toolbar
        :density="tableDensity"
        :table-key="TABLE_KEY"
        show-column-settings
        show-reset-preferences
        :is-in-data-view="true"
        :hidden-fields="hiddenFields"
        :all-columns-for-settings="tabulatorColumns"
        empty-text="暂无数据，请调整查询条件后重试"
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
      <h4>暂无日报数据</h4>
      <p>选择日期范围后点击"生成报表"</p>
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
import * as api from '@/api/report'
import * as master from '@/api/master'
import { exportReport } from '@/api/export'
import { useTemplateColumns } from '@/composables/useTemplateColumns'
import { getReportFilename } from '@/utils/reportFilename'

const TABLE_KEY = 'daily-report'

const { handlePrint } = useReportPrint()

const today = new Date().toISOString().slice(0, 10)
const startDate = ref(today)
const endDate = ref(today)
const entityId = ref(null)
const entities = ref([])
const rows = ref([])
const loading = ref(false)
const errorMsg = ref('')
const { templateColumns, loadTemplate } = useTemplateColumns('daily_report')

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

const MONEY_FIELDS = new Set(['opening_balance', 'total_income', 'total_expense', 'net_change', 'ending_balance'])

const DEFAULT_COLUMNS = [
  { field: 'entity_name', title: '单位简称', width: 150, formatter: emptyDashFormatter, headerSort: false },
  { field: 'opening_balance', title: '期初余额', width: 140, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'total_income', title: '收入合计', width: 140, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'total_expense', title: '支出合计', width: 140, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'net_change', title: '净变动', width: 140, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'ending_balance', title: '期末余额', width: 140, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
]

const tabulatorColumns = computed(() =>
  adaptTemplateColumns(templateColumns.value, DEFAULT_COLUMNS, {
    moneyFields: MONEY_FIELDS,
  })
)

const displayColumns = computed(() => templateColumns.value || DEFAULT_COLUMNS)

const preferencesVersion = ref(0)
const tableDensity = ref(getPreferences(TABLE_KEY).density || 'default')

function touchPreferences() { preferencesVersion.value++ }

const appliedColumns = computed(() => {
  preferencesVersion.value
  return applyPreferences(tabulatorColumns.value, getPreferences(TABLE_KEY))
})

const hiddenFields = computed(() => {
  preferencesVersion.value
  const prefs = getPreferences(TABLE_KEY)
  const visibility = prefs.visibility || {}
  return Object.entries(visibility).filter(([, v]) => !v).map(([f]) => f)
})

function onDensityChange(value) {
  tableDensity.value = value
  saveDensity(TABLE_KEY, value)
}

function onColumnWidthChange({ field, width }) {
  saveColumnWidth(TABLE_KEY, field, width)
}

function onColumnOrderChange(order) {
  saveColumnOrder(TABLE_KEY, order)
}

function onColumnVisibilityChange({ field, visible }) {
  saveColumnVisibility(TABLE_KEY, field, visible)
  touchPreferences()
}

function onPreferencesReset() {
  resetPreferences(TABLE_KEY)
  tableDensity.value = 'default'
  touchPreferences()
}

function rowClassFn(row) {
  if (row.is_total) return 'total-row'
  return ''
}

const totalOpening = computed(() => rows.value.reduce((s, r) => s + r.opening_balance, 0))
const totalIncome = computed(() => rows.value.reduce((s, r) => s + r.total_income, 0))
const totalExpense = computed(() => rows.value.reduce((s, r) => s + r.total_expense, 0))
const totalNet = computed(() => rows.value.reduce((s, r) => s + r.net_change, 0))
const totalEnding = computed(() => rows.value.reduce((s, r) => s + r.ending_balance, 0))

const dataRows = computed(() => {
  const base = rows.value
  if (base.length <= 1) return base
  return [
    ...base,
    {
      entity_id: '__total__',
      entity_name: '合计',
      opening_balance: totalOpening.value,
      total_income: totalIncome.value,
      total_expense: totalExpense.value,
      net_change: totalNet.value,
      ending_balance: totalEnding.value,
      is_total: true,
    },
  ]
})

async function loadReport() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { start_date: startDate.value, end_date: endDate.value }
    if (entityId.value) params.entity_id = entityId.value
    rows.value = await api.getDailyReport(params) || []
  } catch (e) {
    errorMsg.value = '生成日报失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function doExport() {
  try {
    const blob = await exportReport({ export_type: 'daily_report', start_date: startDate.value || undefined, end_date: endDate.value || undefined, entity_id: entityId.value || undefined })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = getReportFilename('daily_report', { startDate: startDate.value, endDate: endDate.value }); a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert('导出失败: ' + (e.message || e)) }
}

onMounted(async () => {
  try { entities.value = (await master.getAccountsTree()) || [] } catch (e) {}
  loadTemplate()
})
</script>

<style scoped>
@import './common.css';
</style>
