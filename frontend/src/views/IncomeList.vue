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

      <div v-if="isTemplateView" class="table-workspace-main template-view">
        <div class="template-hint adt-no-print">
          <span class="template-hint-main">
            模板视图 · 当前使用 Excel 模板渲染，保留原始报表版式；高级表格交互未启用。
          </span>
          <button class="view-switch-btn" type="button" @click="setView('data')">切换到数据视图</button>
        </div>
        <div class="excel-host" v-html="templateExcelHtml"></div>
      </div>

      <div v-else class="table-workspace-main data-view">
        <div v-if="hasTemplate" class="view-mode-strip adt-no-print">
          <span>数据视图 · 当前启用高级表格，可调整列宽、排序和切换密度。</span>
          <button class="view-switch-btn" type="button" @click="setView('template')">切换到模板视图</button>
        </div>
        <AdvancedDataTable
          :columns="appliedColumns"
          :data="rows"
          :pagination="false"
          fill-parent
          show-toolbar
          :total-rows="total"
          :density="tableDensity"
          :table-key="TABLE_KEY"
          show-column-settings
          show-reset-preferences
          :is-in-data-view="isDataView"
          :hidden-fields="hiddenFields"
          :all-columns-for-settings="tabulatorColumns"
          empty-text="暂无收入数据"
          @density-change="onDensityChange"
          @column-width-change="onColumnWidthChange"
          @column-order-change="onColumnOrderChange"
          @column-visibility-change="onColumnVisibilityChange"
          @preferences-reset="onPreferencesReset"
        />
      </div>

      <div class="bottom-bar" v-if="total > 0 && isDataView">
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
import { adaptTemplateColumns } from '@/composables/useColumnAdapter'
import { useDualView } from '@/composables/useDualView'
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

const TABLE_KEY = 'income-list'

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

const MONEY_FIELDS = new Set(['amount', 'rolling_balance'])

const DEFAULT_COLUMNS = [
  { field: 'business_date', title: '日期', width: 120, hozAlign: 'center', formatter: emptyDashFormatter },
  { field: 'entity_name', title: '单位简称', width: 120, formatter: emptyDashFormatter },
  { field: 'account_name', title: '账户名称', width: 150, formatter: emptyDashFormatter },
  { field: 'summary_text', title: '摘要', formatter: emptyDashFormatter },
  { field: 'counterparty_name', title: '对方', width: 120, formatter: emptyDashFormatter },
  { field: 'amount', title: '收入金额', width: 130, hozAlign: 'right', formatter: moneyFormatter },
  { field: 'rolling_balance', title: '余额', width: 130, hozAlign: 'right', formatter: moneyFormatter },
]

const tabulatorColumns = computed(() =>
  adaptTemplateColumns(templateColumns.value, DEFAULT_COLUMNS, {
    moneyFields: MONEY_FIELDS,
  })
)

const { hasTemplate, isTemplateView, isDataView, setView } = useDualView(templateExcelHtml)

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
