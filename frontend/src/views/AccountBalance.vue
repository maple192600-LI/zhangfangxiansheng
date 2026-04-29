<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>账户余额表</h3>
        <span>各账户期初/本期收入/本期支出/期末汇总</span>
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
      <div v-if="templateLoaded && !templateColumns && !templateExcelHtml" class="empty-state">
        <div class="empty-icon">📋</div>
        <h4>未配置报表模板</h4>
        <p>请先在「系统设置 → 数据中心 → 报表模板管理」中上传账户余额表模板</p>
      </div>
      <div v-else-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>
      <table v-else-if="templateColumns">
        <thead>
          <tr>
            <th v-for="col in templateColumns" :key="col.field_key" :style="{ width: col.width+'px', textAlign: col.align }">{{ col.header_name }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(r, idx) in rows" :key="idx">
            <tr v-if="r.is_subtotal" class="subtotal-row">
              <td v-for="col in templateColumns" :key="col.field_key" :class="colClass(col.field_key)" :style="{ textAlign: col.align }"><strong>{{ cellVal(r, col.field_key) }}</strong></td>
            </tr>
            <tr v-else>
              <td v-for="col in templateColumns" :key="col.field_key" :class="colClass(col.field_key)" :style="{ textAlign: col.align }">{{ cellVal(r, col.field_key) }}</td>
            </tr>
          </template>
          <tr v-if="!rows.length">
            <td :colspan="templateColumns.length" class="empty-cell">暂无数据，请调整查询条件后重试</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">
        <div class="empty-icon">🏦</div>
        <h4>暂无余额数据</h4>
        <p>选择日期范围后点击"查询"</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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
const { templateColumns, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('account_balance')

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
