<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>基础数据表</h3>
        <span>所有后续报表的统一底座</span>
      </div>
      <div class="filters-bar">
        <input v-model="filters.date_from" type="date" class="filter" />
        <span style="color:var(--muted);font-size:13px">至</span>
        <input v-model="filters.date_to" type="date" class="filter" />
        <select v-model="filters.entity_id" class="filter">
          <option :value="null">全部单位</option>
          <option v-for="e in entities" :key="e.entity_id" :value="e.entity_id">{{ e.entity_name }}</option>
        </select>
        <select v-model="filters.direction" class="filter">
          <option :value="null">全部方向</option>
          <option value="income">收入</option>
          <option value="expense">支出</option>
        </select>
        <input v-model="filters.keyword" class="filter" placeholder="搜索摘要/对方" style="width:140px" />
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary" @click="doRebuild" :disabled="rebuilding">{{ rebuilding ? '重建中...' : '重建余额' }}</button>
          <button class="btn btn-secondary" @click="doExport('base_data')">导出</button>
          <button class="btn btn-secondary" @click="window.print()">打印</button>
          <button class="btn btn-primary" @click="page = 1; loadData()">生成报表</button>
        </div>
      </div>
      <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
      <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在加载数据...</p></div>

      <!-- 优先：Excel 原表完整渲染 -->
      <div v-else-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>

      <!-- 有模板列时的渲染 -->
      <table v-else-if="templateColumns && templateColumns.length">
        <thead>
          <tr>
            <th v-for="col in templateColumns" :key="col.field_key" :style="{ width: col.width+'px', textAlign: col.align }">{{ col.header_name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td v-for="col in templateColumns" :key="col.field_key" :class="colClass(col.field_key)" :style="{ textAlign: col.align }">{{ cellVal(r, col.field_key) }}</td>
          </tr>
          <tr v-if="!rows.length"><td :colspan="templateColumns.length" class="empty-cell">暂无数据，请先录入或导入流水</td></tr>
        </tbody>
      </table>

      <!-- 兜底：无模板时有数据也显示基础表 -->
      <template v-else-if="rows.length">
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th>方向</th>
              <th>摘要</th>
              <th>对方</th>
              <th class="money">收入金额</th>
              <th class="money">支出金额</th>
              <th class="money">余额</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.id">
              <td>{{ r.business_date }}</td>
              <td>{{ r.direction === 'income' ? '收入' : '支出' }}</td>
              <td>{{ r.summary_text }}</td>
              <td>{{ r.counterparty_name }}</td>
              <td class="money">{{ fmtAmt(r.income_amount) }}</td>
              <td class="money">{{ fmtAmt(r.expense_amount) }}</td>
              <td class="money">{{ fmtAmt(r.rolling_balance) }}</td>
            </tr>
          </tbody>
        </table>
      </template>

      <!-- 真正无数据时的提示 -->
      <div v-else-if="templateLoaded" class="empty-state">
        <div class="empty-icon">📋</div>
        <h4>暂无数据</h4>
        <p>请先通过网银导入或手工录入流水数据</p>
      </div>
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

const entities = ref([])
const rows = ref([])
const total = ref(0)
const page = ref(1)
const totalPages = ref(1)
const rebuilding = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const { templateColumns, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('base_data')

const MONEY_KEYS_BD = new Set(['income_amount', 'expense_amount', 'rolling_balance'])
function colClass(key) { return MONEY_KEYS_BD.has(key) ? 'money' : '' }
function cellVal(r, key) {
  if (key === 'abnormal_code') return r.abnormal_code || '正常'
  if (MONEY_KEYS_BD.has(key)) return fmtAmt(r[key])
  if (r[key] === undefined || r[key] === null) return ''
  return r[key]
}

const filters = ref({ date_from: '', date_to: '', entity_id: null, direction: null, keyword: '' })

async function loadData() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { page: page.value, page_size: 50 }
    const f = filters.value
    if (f.date_from) params.date_from = f.date_from
    if (f.date_to) params.date_to = f.date_to
    if (f.entity_id) params.entity_id = f.entity_id
    if (f.direction) params.direction = f.direction
    if (f.keyword) params.keyword = f.keyword
    const result = await api.getBaseData(params)
    rows.value = result.items || []
    total.value = result.total || 0
    page.value = result.page || 1
    totalPages.value = result.total_pages || 1
  } catch (e) {
    errorMsg.value = '加载数据失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function doRebuild() {
  rebuilding.value = true
  try {
    const r = await api.rebuildBalance()
    alert(`余额重建完成：${r.affected_accounts} 个账户，${r.updated_events} 条记录`)
    loadData()
  } catch (e) { alert('重建失败: ' + (e.message || e)) }
  rebuilding.value = false
}

async function doExport(exportType) {
  try {
    const f = filters.value
    const blob = await exportReport({ export_type: exportType, start_date: f.date_from || undefined, end_date: f.date_to || undefined, entity_id: f.entity_id || undefined })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${exportType}_${f.date_from || 'all'}_${f.date_to || 'all'}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert('导出失败: ' + (e.message || e)) }
}

onMounted(async () => {
  try { entities.value = (await master.getAccountsTree()) || [] } catch (e) {}
  loadTemplate()
  loadData()
})
</script>

<style scoped>
@import './common.css';
</style>
