<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>{{ title }}</h3>
        <span>{{ subtitle }}</span>
      </div>
      <div class="filters-bar">
        <template v-if="dateMode === 'range'">
          <NDatePicker v-model:value="startDate" type="date" value-format="yyyy-MM-dd" clearable style="width:150px" />
          <span style="color:var(--muted);font-size:13px">至</span>
          <NDatePicker v-model:value="endDate" type="date" value-format="yyyy-MM-dd" clearable style="width:150px" />
        </template>
        <template v-else-if="dateMode === 'year'">
          <NSelect v-model:value="selYear" :options="yearSelectOptions" style="width:100px" />
        </template>
        <template v-else>
          <NSelect v-model:value="selYear" :options="yearSelectOptions" style="width:100px" />
          <NSelect v-model:value="selMonth" :options="monthSelectOptions" style="width:80px" />
        </template>
        <NSelect v-model:value="entityId" :options="entityFilterOptions" placeholder="全部单位" clearable style="min-width:140px" />
        <div style="flex:1"></div>
        <div class="btn-row">
          <NButton secondary @click="doExport">导出</NButton>
          <NButton secondary @click="window.print()">打印</NButton>
          <NButton type="primary" @click="loadData">生成报表</NButton>
        </div>
      </div>
      <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在加载...</p></div>
      <div v-else-if="templateLoaded && !templateColumns" class="empty-state">
        <div class="empty-icon">📋</div>
        <h4>未配置报表模板</h4>
        <p>请先在「系统设置 → 报表模板管理」中上传{{ title }}模板</p>
      </div>
      <table v-else-if="templateColumns">
        <thead>
          <tr>
            <th v-for="col in templateColumns" :key="col.field_key" :style="{ width: col.width+'px', textAlign: col.align }">{{ col.header_name }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(r, idx) in rows" :key="idx">
            <tr v-if="r.is_subtotal" class="subtotal-row">
              <td v-for="(col, ci) in templateColumns" :key="col.field_key" :class="moneyClass(col.field_key)" :style="{ textAlign: col.align }">
                <strong>{{ ci === 0 ? r.entity_name : cellVal(r, col.field_key) }}</strong>
              </td>
            </tr>
            <tr v-else>
              <td v-for="col in templateColumns" :key="col.field_key" :class="moneyClass(col.field_key)" :style="{ textAlign: col.align }">{{ cellVal(r, col.field_key) }}</td>
            </tr>
          </template>
          <tr v-if="!rows.length">
            <td :colspan="templateColumns.length" class="empty-cell">暂无数据，请调整查询条件后重试</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">
        <div class="empty-icon">📊</div>
        <h4>正在加载模板...</h4>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NDatePicker, NSelect, NButton } from 'naive-ui'
import * as reportApi from '@/api/report'
import * as master from '@/api/master'
import { fmtAmt } from '@/utils/format'
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
const startDate = ref(today.toISOString().slice(0, 10))
const endDate = ref(today.toISOString().slice(0, 10))
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
const yearSelectOptions = computed(() => yearOptions.value.map(y => ({ label: `${y}年`, value: y })))
const monthSelectOptions = Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1}月`, value: i + 1 }))
const entityFilterOptions = computed(() => entities.value.map(e => ({ label: e.entity_name, value: e.entity_id })))

const { templateColumns, templateLoaded, loadTemplate } = useTemplateColumns(props.reportType)

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
