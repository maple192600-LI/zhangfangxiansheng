<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>账户余额表</h3>
        <span>各账户期初/本期收入/本期支出/期末汇总</span>
      </div>
      <div class="filters-bar">
        <NDatePicker :value="startDateTs" @update:value="v => startDateTs = v" type="date" clearable />
        <span style="color:var(--muted);font-size:13px">至</span>
        <NDatePicker :value="endDateTs" @update:value="v => endDateTs = v" type="date" clearable />
        <NSelect v-model:value="entityId" :options="entityOptions" placeholder="全部单位" clearable />
        <div class="filter-spacer"></div>
        <NSpace>
          <NButton @click="doExport">导出</NButton>
          <NButton @click="window.print()">打印</NButton>
          <NButton type="primary" @click="loadReport">生成报表</NButton>
        </NSpace>
      </div>
      <div v-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>
      <table v-else-if="displayColumns.length">
        <thead>
          <tr>
            <th v-for="col in displayColumns" :key="col.field_key" :style="{ width: col.width+'px', textAlign: col.align }">{{ col.header_name }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(r, idx) in rows" :key="idx">
            <tr v-if="r.is_subtotal" class="subtotal-row">
              <td v-for="col in displayColumns" :key="col.field_key" :class="colClass(col.field_key)" :style="{ textAlign: col.align }"><strong>{{ cellVal(r, col.field_key) }}</strong></td>
            </tr>
            <tr v-else>
              <td v-for="col in displayColumns" :key="col.field_key" :class="colClass(col.field_key)" :style="{ textAlign: col.align }">{{ cellVal(r, col.field_key) }}</td>
            </tr>
          </template>
          <tr v-if="!rows.length">
            <td :colspan="displayColumns.length" class="empty-cell">暂无数据，请调整查询条件后重试</td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!loading" class="empty-state">
        <div class="empty-icon">🏦</div>
        <h4>暂无余额数据</h4>
        <p>选择日期范围后点击"生成报表"</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NDatePicker, NSelect, NButton, NSpace } from 'naive-ui'
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
const { templateColumns, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('account_balance')

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

const entityOptions = computed(() => [
  { label: '全部单位', value: null },
  ...entities.value.map(e => ({ label: e.entity_name, value: e.entity_id }))
])

const DEFAULT_COLUMNS = [
  { field_key: 'entity_name', header_name: '单位简称', width: 150, align: 'left' },
  { field_key: 'account_name', header_name: '账户名称', width: 180, align: 'left' },
  { field_key: 'opening_balance', header_name: '期初余额', width: 140, align: 'right' },
  { field_key: 'period_income', header_name: '本期收入', width: 140, align: 'right' },
  { field_key: 'period_expense', header_name: '本期支出', width: 140, align: 'right' },
  { field_key: 'ending_balance', header_name: '期末余额', width: 140, align: 'right' },
]

const displayColumns = computed(() => templateColumns.value || DEFAULT_COLUMNS)

const MONEY_KEYS = new Set(['opening_balance', 'period_income', 'period_expense', 'ending_balance'])
function colClass(key) { return MONEY_KEYS.has(key) ? 'money' : '' }
function cellVal(r, key) {
  if (MONEY_KEYS.has(key)) return fmtAmt(r[key])
  if (r[key] === undefined || r[key] === null) return ''
  return r[key]
}

async function loadReport() {
  try {
    const params = { start_date: startDate.value, end_date: endDate.value }
    if (entityId.value) params.entity_id = entityId.value
    rows.value = await api.getAccountBalance(params) || []
  } catch (e) { alert('查询失败: ' + (e.message || e)) }
}

async function doExport() {
  try {
    const blob = await exportReport({ export_type: 'account_balance', start_date: startDate.value || undefined, end_date: endDate.value || undefined, entity_id: entityId.value || undefined })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `account_balance.xlsx`; a.click()
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
