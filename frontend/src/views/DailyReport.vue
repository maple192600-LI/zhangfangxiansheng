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
          <button class="btn btn-primary" @click="loadReport">生成日报</button>
        </div>
      </div>
      <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
      <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在生成日报...</p></div>
      <table v-else-if="rows.length">
        <thead>
          <tr>
            <th>单位简称</th><th>期初余额</th><th>收入合计</th><th>支出合计</th><th>净变动</th><th>期末余额</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.entity_id">
            <td>{{ r.entity_name }}</td>
            <td class="money">{{ fmtAmt(r.opening_balance) }}</td>
            <td class="money inc">{{ fmtAmt(r.total_income) }}</td>
            <td class="money exp">{{ fmtAmt(r.total_expense) }}</td>
            <td class="money" :class="r.net_change >= 0 ? 'inc' : 'exp'">{{ fmtAmt(r.net_change) }}</td>
            <td class="money balance">{{ fmtAmt(r.ending_balance) }}</td>
          </tr>
          <tr class="total-row" v-if="rows.length > 1">
            <td><strong>合计</strong></td>
            <td class="money"><strong>{{ fmtAmt(totalOpening) }}</strong></td>
            <td class="money inc"><strong>{{ fmtAmt(totalIncome) }}</strong></td>
            <td class="money exp"><strong>{{ fmtAmt(totalExpense) }}</strong></td>
            <td class="money"><strong>{{ fmtAmt(totalNet) }}</strong></td>
            <td class="money balance"><strong>{{ fmtAmt(totalEnding) }}</strong></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">
        <div class="empty-icon">📊</div>
        <h4>暂无日报数据</h4>
        <p>选择日期范围后点击"生成日报"</p>
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

const today = new Date().toISOString().slice(0, 10)
const startDate = ref(today)
const endDate = ref(today)
const entityId = ref(null)
const entities = ref([])
const rows = ref([])
const loading = ref(false)
const errorMsg = ref('')

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
})
</script>

<style scoped>
@import './common.css';
</style>
