<template>
  <div class="section report-print-root table-workspace-page">
    <div class="section-title">
      <h3>现金日记账</h3>
      <span>现金类资金载体的结果视图</span>
    </div>
    <div class="filters-bar">
      <NDatePicker :value="startDateTs" @update:value="v => startDateTs = v" type="date" clearable />
      <span style="color:var(--muted);font-size:13px">至</span>
      <NDatePicker :value="endDateTs" @update:value="v => endDateTs = v" type="date" clearable />
      <MasterAccountSelect v-model="accountId" :entities="entities" />
      <div class="filter-spacer"></div>
      <div class="btn-row">
        <NButton secondary @click="doExport">导出</NButton>
        <NButton secondary @click="handlePrint">打印</NButton>
        <NButton type="primary" @click="loadReport">生成报表</NButton>
      </div>
    </div>
    <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
    <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在生成报表...</p></div>

    <div v-else-if="hasColumns" class="table-workspace-main">
      <AdvancedDataTable
        :columns="appliedColumns"
        :data="displayRows"
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
        empty-text="暂无日记账数据，选择日期范围和账户后点击'生成报表'"
        :row-key="'__row_key'"
        @density-change="onDensityChange"
        @column-width-change="onColumnWidthChange"
        @column-order-change="onColumnOrderChange"
        @column-visibility-change="onColumnVisibilityChange"
        @preferences-reset="onPreferencesReset"
      />
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">📊</div>
      <h4>暂无日记账数据</h4>
      <p>选择日期范围和账户后点击"生成报表"</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NDatePicker, NButton } from 'naive-ui'
import MasterAccountSelect from '@/components/MasterAccountSelect.vue'
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

const { handlePrint } = useReportPrint()

const TABLE_KEY = 'cash-journal'

const today = new Date()
const todayStr = today.toISOString().slice(0, 10)
const startDate = ref(todayStr)
const endDate = ref(todayStr)
const accountId = ref(null)

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

const entities = ref([])
const rows = ref([])
const loading = ref(false)
const errorMsg = ref('')
const { templateColumns, templateLoaded, loadTemplate } = useTemplateColumns('cash_journal')

const MONEY_KEYS = new Set(['prev_balance', 'income', 'expense', 'day_balance', 'amount', 'rolling_balance'])

const DEFAULT_TABULATOR_COLUMNS = [
  { field: 'business_date', title: '日期', width: 120, hozAlign: 'center', formatter: emptyDashFormatter, headerSort: false },
  { field: 'entity_name', title: '单位', width: 120, formatter: emptyDashFormatter, headerSort: false },
  { field: 'account_name', title: '账户', width: 150, formatter: emptyDashFormatter, headerSort: false },
  { field: 'summary_text', title: '摘要', width: 200, formatter: emptyDashFormatter, headerSort: false },
  { field: 'prev_balance', title: '上日余额', width: 130, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'income', title: '收入', width: 130, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'expense', title: '支出', width: 130, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'day_balance', title: '本日余额', width: 130, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
]

const tabulatorColumns = computed(() =>
  adaptTemplateColumns(templateColumns.value, DEFAULT_TABULATOR_COLUMNS, {
    moneyFields: MONEY_KEYS,
  }).map(col => ({ ...col, headerSort: false }))
)

const hasColumns = computed(() => tabulatorColumns.value.length > 0)

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

const displayRows = computed(() =>
  rows.value.map((r, idx) => ({
    ...r,
    __row_key: `cj-${idx}`,
  }))
)

async function loadReport() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { start_date: startDate.value, end_date: endDate.value }
    if (accountId.value) params.account_id = accountId.value
    const raw = await api.getCashJournal(params) || []
    const result = []
    for (const block of raw) {
      for (const row of (block.rows || [])) {
        result.push({
          ...row,
          entity_name: block.entity_name || '',
          account_name: block.account_name || '',
        })
      }
    }
    rows.value = result
  } catch (e) {
    errorMsg.value = '查询失败: ' + (e.message || e)
  } finally {
    loading.value = false
  }
}

async function doExport() {
  try {
    const params = { export_type: 'cash_journal', start_date: startDate.value || undefined, end_date: endDate.value || undefined }
    if (accountId.value) params.account_id = accountId.value
    const blob = await exportReport(params)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = getReportFilename('cash_journal', { startDate: startDate.value, endDate: endDate.value }); a.click()
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
