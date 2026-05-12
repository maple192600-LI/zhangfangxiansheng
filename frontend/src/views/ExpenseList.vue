<template>
  <div class="report-print-root-wrapper">
    <div class="section report-print-root">
      <div class="section-title">
        <h3>支出明细表</h3>
        <span>按账户、日期汇总的支出明细视图</span>
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
      <div v-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>
      <table v-else-if="displayColumns.length">
        <thead>
          <tr>
            <th v-for="col in displayColumns" :key="col.field_key" :style="{ width: col.width+'px', textAlign: col.align }">{{ col.header_name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td v-for="col in displayColumns" :key="col.field_key" :class="colClass(col.field_key)" :style="{ textAlign: col.align }">{{ cellVal(r, col.field_key) }}</td>
          </tr>
          <tr v-if="!rows.length"><td :colspan="displayColumns.length" class="empty-cell">暂无支出数据</td></tr>
        </tbody>
      </table>
    </div>

    <div class="bottom-bar" v-if="total > 0">
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
import { useReportPrint } from '@/composables/useReportPrint'
import * as api from '@/api/report'
import * as master from '@/api/master'
import { fmtAmt } from '@/utils/format'
import { exportReport } from '@/api/export'
import { useTemplateColumns } from '@/composables/useTemplateColumns'

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
const { templateColumns, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('expense_list')

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

const DEFAULT_COLUMNS = [
  { field_key: 'business_date', header_name: '日期', width: 120, align: 'center' },
  { field_key: 'entity_name', header_name: '单位简称', width: 120, align: 'left' },
  { field_key: 'account_name', header_name: '账户名称', width: 150, align: 'left' },
  { field_key: 'summary_text', header_name: '摘要', width: 200, align: 'left' },
  { field_key: 'counterparty_name', header_name: '对方', width: 120, align: 'left' },
  { field_key: 'amount', header_name: '支出金额', width: 130, align: 'right' },
  { field_key: 'rolling_balance', header_name: '余额', width: 130, align: 'right' },
]

const displayColumns = computed(() => templateColumns.value || DEFAULT_COLUMNS)

const MONEY_KEYS = new Set(['amount', 'rolling_balance'])
function colClass(key) { return MONEY_KEYS.has(key) ? 'money' : '' }
function cellVal(r, key) {
  if (MONEY_KEYS.has(key)) return fmtAmt(r[key])
  if (r[key] === undefined || r[key] === null) return ''
  return r[key]
}

async function loadData() {
  try {
    const params = { start_date: startDate.value, end_date: endDate.value, page: page.value, page_size: 50 }
    if (entityId.value) params.entity_id = entityId.value
    const result = await api.getExpenseList(params)
    rows.value = result.items || []
    total.value = result.total || 0
    page.value = result.page || 1
    totalPages.value = result.total_pages || 1
  } catch (e) { console.error(e) }
}

async function doExport() {
  try {
    const blob = await exportReport({ export_type: 'expense_list', start_date: startDate.value || undefined, end_date: endDate.value || undefined, entity_id: entityId.value || undefined })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `支出明细表_${startDate.value}_${endDate.value}.xlsx`; a.click()
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
