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
          <button class="btn btn-primary" @click="page = 1; loadData()">查询</button>
        </div>
      </div>
      <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
      <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在加载数据...</p></div>
      <table v-else>
        <thead>
          <tr>
            <th>日期</th><th>单位简称</th><th>账户名称</th><th>摘要</th><th>对方</th>
            <th>收入</th><th>支出</th><th>余额</th><th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.business_date }}</td>
            <td>{{ r.entity_name || '-' }}</td>
            <td>{{ r.account_name || '-' }}</td>
            <td>{{ r.summary_text }}</td>
            <td>{{ r.counterparty_name || '-' }}</td>
            <td class="money inc">{{ fmtAmt(r.income_amount) }}</td>
            <td class="money exp">{{ fmtAmt(r.expense_amount) }}</td>
            <td class="money balance">{{ fmtAmt(r.rolling_balance) }}</td>
            <td>
              <span v-if="r.abnormal_code" class="tag tag-warn">{{ r.abnormal_code }}</span>
              <span v-else class="tag tag-green">正常</span>
            </td>
          </tr>
          <tr v-if="!rows.length"><td colspan="9" style="text-align:center;color:var(--muted);padding:30px">暂无数据，请先录入或导入流水</td></tr>
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

const entities = ref([])
const rows = ref([])
const total = ref(0)
const page = ref(1)
const totalPages = ref(1)
const rebuilding = ref(false)
const loading = ref(false)
const errorMsg = ref('')

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
  loadData()
})
</script>

<style scoped>
@import './common.css';
</style>
