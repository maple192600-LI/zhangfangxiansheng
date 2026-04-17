<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>收入明细表</h3>
        <span>按账户、日期汇总的收入明细视图</span>
      </div>
      <div class="filters-bar">
        <input v-model="startDate" type="date" class="filter" />
        <span style="color:var(--muted);font-size:13px">至</span>
        <input v-model="endDate" type="date" class="filter" />
        <select v-model="entityId" class="filter">
          <option :value="null">全部法人</option>
          <option v-for="e in entities" :key="e.entity_id" :value="e.entity_id">{{ e.entity_name }}</option>
        </select>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary">导出</button>
          <button class="btn btn-secondary">打印</button>
          <button class="btn btn-primary" @click="page = 1; loadData()">查询</button>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>日期</th><th>法人</th><th>账户</th><th>摘要</th><th>对方</th><th>收入金额</th><th>余额</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.business_date }}</td>
            <td>{{ r.entity_name || '-' }}</td>
            <td>{{ r.account_name || '-' }}</td>
            <td>{{ r.summary_text }}</td>
            <td>{{ r.counterparty_name || '-' }}</td>
            <td class="money inc">{{ fmtAmt(r.amount) }}</td>
            <td class="money balance">{{ fmtAmt(r.rolling_balance) }}</td>
          </tr>
          <tr v-if="!rows.length"><td colspan="7" style="text-align:center;color:var(--muted);padding:30px">暂无收入数据</td></tr>
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

const today = new Date().toISOString().slice(0, 10)
const startDate = ref(today)
const endDate = ref(today)
const entityId = ref(null)
const entities = ref([])
const rows = ref([])
const total = ref(0)
const page = ref(1)
const totalPages = ref(1)

async function loadData() {
  try {
    const params = { start_date: startDate.value, end_date: endDate.value, page: page.value, page_size: 50 }
    if (entityId.value) params.entity_id = entityId.value
    const result = await api.getIncomeList(params)
    rows.value = result.items || []
    total.value = result.total || 0
    page.value = result.page || 1
    totalPages.value = result.total_pages || 1
  } catch (e) { console.error(e) }
}

onMounted(async () => {
  try { entities.value = (await master.getAccountsTree()) || [] } catch (e) {}
  loadData()
})
</script>

<style scoped>
@import './common.css';
</style>
