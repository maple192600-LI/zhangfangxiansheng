<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>现金日记账</h3>
        <span>现金类资金载体的结果视图</span>
      </div>
      <div class="filters-bar">
        <input v-model="startDate" type="date" class="filter" />
        <span style="color:var(--muted);font-size:13px">至</span>
        <input v-model="endDate" type="date" class="filter" />
        <select v-model="accountId" class="filter">
          <option :value="null">全部账户</option>
          <optgroup v-for="g in entityGroups" :key="g.entity_id" :label="g.entity_name">
            <option v-for="a in g.accounts" :key="a.id" :value="a.id">{{ a.account_code }} {{ a.account_alias }}</option>
          </optgroup>
        </select>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary" @click="doExport">导出</button>
          <button class="btn btn-secondary" @click="window.print()">打印</button>
          <button class="btn btn-primary" @click="loadReport">查询</button>
        </div>
      </div>
      <div v-if="blocks.length">
        <div v-for="block in blocks" :key="block.account_id" style="margin-bottom:14px">
          <div style="padding:8px 14px;font-weight:600;font-size:13px;background:var(--thead-bg);border:1px solid var(--line);border-radius:var(--radius-sm) var(--radius-sm) 0 0;color:var(--ok-text)">
            {{ block.entity_name }} — {{ block.account_name }}
          </div>
          <table>
            <thead><tr><th>日期</th><th>上日余额</th><th>收入</th><th>支出</th><th>本日余额</th></tr></thead>
            <tbody>
              <tr v-for="r in block.rows" :key="r.business_date">
                <td>{{ r.business_date }}</td>
                <td class="money">{{ fmtAmt(r.prev_balance) }}</td>
                <td class="money inc">{{ fmtAmt(r.income) }}</td>
                <td class="money exp">{{ fmtAmt(r.expense) }}</td>
                <td class="money balance">{{ fmtAmt(r.day_balance) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else class="empty-state">
        <div class="empty-icon">📒</div>
        <h4>暂无日记账数据</h4>
        <p>选择日期范围和账户后点击"查询"</p>
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
const accountId = ref(null)
const entities = ref([])
const blocks = ref([])
const loading = ref(false)
const errorMsg = ref('')

const entityGroups = computed(() => {
  const groups = {}
  for (const e of entities.value) {
    if (!groups[e.entity_id]) groups[e.entity_id] = { entity_id: e.entity_id, entity_name: e.entity_name, accounts: [] }
    groups[e.entity_id].accounts.push(...e.accounts)
  }
  return Object.values(groups)
})

async function loadReport() {
  try {
    const params = { start_date: startDate.value, end_date: endDate.value }
    if (accountId.value) params.account_id = accountId.value
    blocks.value = await api.getCashJournal(params) || []
  } catch (e) { alert('查询失败: ' + (e.message || e)) }
}

async function doExport() {
  try {
    const blob = await exportReport({ export_type: 'cash_journal', start_date: startDate.value || undefined, end_date: endDate.value || undefined })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `cash_journal.xlsx`; a.click()
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
