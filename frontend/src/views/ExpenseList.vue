<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>支出明细表</h3>
        <span>按账户、日期汇总的支出明细视图</span>
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
          <button class="btn btn-primary" @click="page = 1; loadData()">生成报表</button>
        </div>
      </div>
      <div v-if="templateLoaded && !templateColumns && !templateExcelHtml" class="empty-state">
        <div class="empty-icon">📋</div>
        <h4>未配置报表模板</h4>
        <p>请先在「系统设置 → 数据中心 → 报表模板管理」中上传支出明细表模板</p>
      </div>
      <div v-else-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>
      <table v-else-if="templateColumns">
        <thead>
          <tr>
            <th v-for="col in templateColumns" :key="col.field_key" :style="{ width: col.width+'px', textAlign: col.align }">{{ col.header_name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td v-for="col in templateColumns" :key="col.field_key" :class="colClass(col.field_key)" :style="{ textAlign: col.align }">{{ cellVal(r, col.field_key) }}</td>
          </tr>
          <tr v-if="!rows.length"><td :colspan="templateColumns.length" class="empty-cell">暂无支出数据</td></tr>
        </tbody>
      </table>
    </div>

    <div class="bottom-bar" v-if="total > 0">
      <span class="count-info">共 {{ total }} 条，第 {{ page }} / {{ totalPages }} 页</span>
      <button class="btn btn-secondary btn-sm" :disabled="page <= 1" @click="page--; loadData()">上一页</button>
      <button class="btn btn-secondary btn-sm" :disabled="page >= totalPages" @click="page++; loadData()">下一页</button>
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
const total = ref(0)
const page = ref(1)
const totalPages = ref(1)
const { templateColumns, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('expense_list')

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
    a.href = url; a.download = `expense_list.xlsx`; a.click()
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
