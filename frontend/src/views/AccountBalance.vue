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
          <option :value="null">全部法人</option>
          <option v-for="e in entities" :key="e.entity_id" :value="e.entity_id">{{ e.entity_name }}</option>
        </select>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary">导出</button>
          <button class="btn btn-secondary">打印</button>
          <button class="btn btn-primary" @click="loadReport">查询</button>
        </div>
      </div>
      <table v-if="rows.length">
        <thead>
          <tr>
            <th>法人</th><th>账户</th><th>期初余额</th><th>本期收入</th><th>本期支出</th><th>期末余额</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(r, idx) in rows" :key="idx">
            <tr v-if="r.is_subtotal" class="subtotal-row">
              <td colspan="2"><strong>{{ r.entity_name }}</strong></td>
              <td class="money"><strong>{{ fmtAmt(r.opening_balance) }}</strong></td>
              <td class="money inc"><strong>{{ fmtAmt(r.period_income) }}</strong></td>
              <td class="money exp"><strong>{{ fmtAmt(r.period_expense) }}</strong></td>
              <td class="money balance"><strong>{{ fmtAmt(r.ending_balance) }}</strong></td>
            </tr>
            <tr v-else>
              <td>{{ r.entity_name }}</td>
              <td>{{ r.account_name || '-' }}</td>
              <td class="money">{{ fmtAmt(r.opening_balance) }}</td>
              <td class="money inc">{{ fmtAmt(r.period_income) }}</td>
              <td class="money exp">{{ fmtAmt(r.period_expense) }}</td>
              <td class="money balance">{{ fmtAmt(r.ending_balance) }}</td>
            </tr>
          </template>
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

const today = new Date().toISOString().slice(0, 10)
const startDate = ref(today)
const endDate = ref(today)
const entityId = ref(null)
const entities = ref([])
const rows = ref([])

async function loadReport() {
  try {
    const params = { start_date: startDate.value, end_date: endDate.value }
    if (entityId.value) params.entity_id = entityId.value
    rows.value = await api.getAccountBalance(params) || []
  } catch (e) { alert('查询失败: ' + (e.message || e)) }
}

onMounted(async () => {
  try { entities.value = (await master.getAccountsTree()) || [] } catch (e) {}
})
</script>

<style scoped>
@import './common.css';
</style>
