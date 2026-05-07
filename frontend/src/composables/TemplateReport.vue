<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>{{ title }}</h3>
        <span>{{ subtitle }}</span>
      </div>
      <div class="filters-bar">
        <template v-if="dateMode === 'range'">
          <input v-model="startDate" type="date" class="filter" />
          <span style="color:var(--muted);font-size:13px">至</span>
          <input v-model="endDate" type="date" class="filter" />
        </template>
        <template v-else-if="dateMode === 'year'">
          <select v-model.number="selYear" class="filter">
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
          </select>
        </template>
        <template v-else>
          <select v-model.number="selYear" class="filter">
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
          </select>
          <select v-model.number="selMonth" class="filter">
            <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
          </select>
        </template>
        <select v-model="entityId" class="filter">
          <option :value="null">全部单位</option>
          <option v-for="e in entities" :key="e.entity_id" :value="e.entity_id">{{ e.entity_name }}</option>
        </select>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary" @click="doExport">导出</button>
          <button class="btn btn-secondary" @click="window.print()">打印</button>
          <button class="btn btn-primary" @click="loadData">生成报表</button>
        </div>
      </div>
      <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在加载...</p></div>
      <table v-else-if="displayColumns.length">
        <thead>
          <tr>
            <th v-for="col in displayColumns" :key="col.field_key" :style="{ width: col.width+'px', textAlign: col.align }">{{ col.header_name }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(r, idx) in rows" :key="idx">
            <tr v-if="r.is_subtotal" class="subtotal-row">
              <td v-for="(col, ci) in displayColumns" :key="col.field_key" :class="moneyClass(col.field_key)" :style="{ textAlign: col.align }">
                <strong>{{ ci === 0 ? r.entity_name : cellVal(r, col.field_key) }}</strong>
              </td>
            </tr>
            <tr v-else>
              <td v-for="col in displayColumns" :key="col.field_key" :class="moneyClass(col.field_key)" :style="{ textAlign: col.align }">{{ cellVal(r, col.field_key) }}</td>
            </tr>
          </template>
          <tr v-if="!rows.length">
            <td :colspan="displayColumns.length" class="empty-cell">暂无数据，请调整查询条件后重试</td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!loading" class="empty-state">
        <div class="empty-icon">📊</div>
        <h4>暂无数据</h4>
        <p>选择查询条件后点击"生成报表"</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as reportApi from '@/api/report'
import * as master from '@/api/master'
import { fmtAmt } from '@/utils/format'
import { todayLocalDate } from '@/utils/date'
import { exportReport } from '@/api/export'
import { useTemplateColumns } from '@/composables/useTemplateColumns'

const props = defineProps({
  title: String,
  subtitle: { type: String, default: '' },
  reportType: String,
  exportType: String,
  dateMode: { type: String, default: 'range' },
  defaultHeaders: { type: Array, default: () => [] },
  defaultKeys: { type: Array, default: () => [] },
})

const today = new Date()
const startDate = ref(todayLocalDate())
const endDate = ref(todayLocalDate())
const selYear = ref(today.getFullYear())
const selMonth = ref(today.getMonth() + 1)
const entityId = ref(null)
const entities = ref([])
const rows = ref([])
const loading = ref(false)

const yearOptions = computed(() => {
  const y = today.getFullYear()
  return [y - 2, y - 1, y, y + 1]
})

const { templateColumns, templateLoaded, loadTemplate } = useTemplateColumns(props.reportType)

const DEFAULT_COLUMNS_MAP = {
  week_report: [
    { field_key: 'entity_name', header_name: '单位简称', width: 150, align: 'left' },
    { field_key: 'week_start', header_name: '周开始日期', width: 120, align: 'center' },
    { field_key: 'week_end', header_name: '周结束日期', width: 120, align: 'center' },
    { field_key: 'opening_balance', header_name: '期初余额', width: 140, align: 'right' },
    { field_key: 'total_income', header_name: '收入合计', width: 140, align: 'right' },
    { field_key: 'total_expense', header_name: '支出合计', width: 140, align: 'right' },
    { field_key: 'net_change', header_name: '净变动', width: 140, align: 'right' },
    { field_key: 'ending_balance', header_name: '期末余额', width: 140, align: 'right' },
  ],
  month_report: [
    { field_key: 'entity_name', header_name: '单位简称', width: 150, align: 'left' },
    { field_key: 'opening_balance', header_name: '期初余额', width: 140, align: 'right' },
    { field_key: 'total_income', header_name: '收入合计', width: 140, align: 'right' },
    { field_key: 'total_expense', header_name: '支出合计', width: 140, align: 'right' },
    { field_key: 'net_change', header_name: '净变动', width: 140, align: 'right' },
    { field_key: 'ending_balance', header_name: '期末余额', width: 140, align: 'right' },
  ],
  year_report: [
    { field_key: 'entity_name', header_name: '单位简称', width: 150, align: 'left' },
    { field_key: 'opening_balance', header_name: '期初余额', width: 140, align: 'right' },
    { field_key: 'total_income', header_name: '收入合计', width: 140, align: 'right' },
    { field_key: 'total_expense', header_name: '支出合计', width: 140, align: 'right' },
    { field_key: 'net_change', header_name: '净变动', width: 140, align: 'right' },
    { field_key: 'ending_balance', header_name: '期末余额', width: 140, align: 'right' },
  ],
  major_balance: [
    { field_key: 'entity_name', header_name: '单位简称', width: 150, align: 'left' },
    { field_key: 'account_name', header_name: '账户名称', width: 180, align: 'left' },
    { field_key: 'opening_balance', header_name: '期初余额', width: 140, align: 'right' },
    { field_key: 'period_income', header_name: '本期收入', width: 140, align: 'right' },
    { field_key: 'period_expense', header_name: '本期支出', width: 140, align: 'right' },
    { field_key: 'ending_balance', header_name: '期末余额', width: 140, align: 'right' },
  ],
  month_check: [
    { field_key: 'entity_name', header_name: '单位简称', width: 150, align: 'left' },
    { field_key: 'account_name', header_name: '账户名称', width: 180, align: 'left' },
    { field_key: 'opening_balance', header_name: '期初余额', width: 140, align: 'right' },
    { field_key: 'period_income', header_name: '本期收入', width: 140, align: 'right' },
    { field_key: 'period_expense', header_name: '本期支出', width: 140, align: 'right' },
    { field_key: 'ending_balance', header_name: '期末余额', width: 140, align: 'right' },
  ],
}

const displayColumns = computed(() => templateColumns.value || DEFAULT_COLUMNS_MAP[props.reportType] || [])

const MONEY_KEYS = new Set(['opening_balance', 'total_income', 'total_expense', 'net_change', 'ending_balance', 'period_income', 'period_expense', 'amount', 'rolling_balance'])

function moneyClass(key) { return MONEY_KEYS.has(key) ? 'money' : '' }
function cellVal(r, key) {
  if (MONEY_KEYS.has(key)) return fmtAmt(r[key])
  if (r[key] === undefined || r[key] === null) return ''
  return r[key]
}

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
    a.download = `${props.exportType}.xlsx`
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
.subtotal-row { background: #F7F4EE; font-weight: 600; }
.empty-cell { text-align: center; color: #8C8680; padding: 40px 20px; font-size: 14px; }
</style>
