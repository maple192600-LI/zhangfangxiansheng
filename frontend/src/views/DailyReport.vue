<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>资金日报</h3>
        <span>按单位汇总：期初/收入/支出/净变动/期末</span>
      </div>
      <div class="filters-bar">
        <input v-model="startDate" type="date" class="filter" />
        <span style="color:var(--muted);font-size:13px">至</span>
        <input v-model="endDate" type="date" class="filter" />
        <select v-model="entityId" class="filter">
          <option :value="null">全部单位</option>
          <option v-for="e in entities" :key="e.entity_id" :value="e.entity_id">{{ e.entity_name }}</option>
        </select>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary" @click="doExport">导出</button>
          <button class="btn btn-secondary" @click="window.print()">打印</button>
          <button class="btn btn-primary" @click="loadReport">生成报表</button>
        </div>
      </div>
      <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
      <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在生成日报...</p></div>
      <div v-else-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>
      <table v-else-if="displayColumns.length">
        <thead>
          <tr>
            <th v-for="col in displayColumns" :key="col.field_key" :style="{ width: col.width+'px', textAlign: col.align }">{{ col.header_name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.entity_id">
            <td v-for="col in displayColumns" :key="col.field_key" :class="moneyClass(col.field_key)" :style="{ textAlign: col.align }">{{ cellValue(r, col.field_key) }}</td>
          </tr>
          <tr v-if="!rows.length">
            <td :colspan="displayColumns.length" class="empty-cell">暂无数据，请调整查询条件后重试</td>
          </tr>
          <tr class="total-row" v-if="rows.length > 1">
            <td v-for="(col, idx) in displayColumns" :key="'t'+col.field_key" class="money"><strong>{{ idx === 0 ? '合计' : fmtAmt(totalMap[col.field_key]) }}</strong></td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!loading" class="empty-state">
        <div class="empty-icon">📊</div>
        <h4>暂无日报数据</h4>
        <p>选择日期范围后点击"生成报表"</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as api from '@/api/report'
import * as master from '@/api/master'
import { fmtAmt } from '@/utils/format'
import { exportReport } from '@/api/export'
import { useTemplateColumns } from '@/composables/useTemplateColumns'

const today = new Date().toISOString().slice(0, 10)
const startDate = ref(today)
const endDate = ref(today)
const entityId = ref(null)
const entities = ref([])
const rows = ref([])
const loading = ref(false)
const errorMsg = ref('')
const { templateColumns, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('daily_report')

const DEFAULT_COLUMNS = [
  { field_key: 'entity_name', header_name: '单位简称', width: 150, align: 'left' },
  { field_key: 'opening_balance', header_name: '期初余额', width: 140, align: 'right' },
  { field_key: 'total_income', header_name: '收入合计', width: 140, align: 'right' },
  { field_key: 'total_expense', header_name: '支出合计', width: 140, align: 'right' },
  { field_key: 'net_change', header_name: '净变动', width: 140, align: 'right' },
  { field_key: 'ending_balance', header_name: '期末余额', width: 140, align: 'right' },
]

const displayColumns = computed(() => templateColumns.value || DEFAULT_COLUMNS)

const MONEY_KEYS = new Set(['opening_balance', 'total_income', 'total_expense', 'net_change', 'ending_balance'])
function isMoneyKey(key) { return MONEY_KEYS.has(key) }
function moneyClass(key) { return isMoneyKey(key) ? 'money' : '' }
function cellValue(r, key) {
  if (isMoneyKey(key)) return fmtAmt(r[key])
  if (r[key] === undefined || r[key] === null) return ''
  return r[key]
}

const totalMap = computed(() => ({
  entity_name: '合计',
  opening_balance: totalOpening.value,
  total_income: totalIncome.value,
  total_expense: totalExpense.value,
  net_change: totalNet.value,
  ending_balance: totalEnding.value,
}))

const totalOpening = computed(() => rows.value.reduce((s, r) => s + r.opening_balance, 0))
const totalIncome = computed(() => rows.value.reduce((s, r) => s + r.total_income, 0))
const totalExpense = computed(() => rows.value.reduce((s, r) => s + r.total_expense, 0))
const totalNet = computed(() => rows.value.reduce((s, r) => s + r.net_change, 0))
const totalEnding = computed(() => rows.value.reduce((s, r) => s + r.ending_balance, 0))

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
    a.href = url; a.download = `daily_report.xlsx`; a.click()
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
