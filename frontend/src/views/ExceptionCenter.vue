<template>
  <div>
    <div class="section">
      <div class="section-title">
        <div>
          <h3>异常中心</h3>
          <span>集中处理待确认和异常流水，处理结果写入操作日志</span>
        </div>
        <div class="status-pills">
          <span class="tag tag-blue">待确认 {{ summary.pending_count || 0 }}</span>
          <span class="tag tag-warn">异常 {{ summary.abnormal_count || 0 }}</span>
        </div>
      </div>

      <div class="filters-bar">
        <NButton class="filter" :class="{ active: filters.state === '' }" quaternary @click="setState('')">全部</NButton>
        <NButton class="filter" :class="{ active: filters.state === '待确认' }" quaternary @click="setState('待确认')">待确认</NButton>
        <NButton class="filter" :class="{ active: filters.state === '异常' }" quaternary @click="setState('异常')">异常</NButton>
        <input v-model="filters.keyword" class="filter keyword-input" placeholder="搜索摘要/对方" @keyup.enter="reload" />
        <div style="flex:1"></div>
        <NButton secondary @click="reload" :disabled="loading">{{ loading ? '刷新中...' : '刷新' }}</NButton>
      </div>

      <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>正在加载异常流水...</p>
      </div>
      <table v-else>
        <thead>
          <tr>
            <th>日期</th>
            <th>单位</th>
            <th>账户</th>
            <th>摘要</th>
            <th>对方</th>
            <th class="money">收入</th>
            <th class="money">支出</th>
            <th>状态</th>
            <th>来源</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" :class="{ selected: editing?.id === row.id }">
            <td>{{ row.business_date }}</td>
            <td>{{ row.entity_name }}</td>
            <td>{{ row.account_name }}</td>
            <td>{{ row.summary }}</td>
            <td>{{ row.counterparty }}</td>
            <td class="money">{{ fmtAmt(row.amount_in) }}</td>
            <td class="money">{{ fmtAmt(row.amount_out) }}</td>
            <td><span class="tag" :class="row.state === '异常' ? 'tag-warn' : 'tag-blue'">{{ row.state }}</span></td>
            <td>{{ row.source }}</td>
            <td>
              <div class="btn-row compact">
                <NButton secondary size="small" @click="startEdit(row)">修正</NButton>
                <NButton type="warning" size="small" @click="voidRow(row)">作废</NButton>
              </div>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="10" class="empty-cell">暂无待处理异常流水</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="section" v-if="editing">
      <div class="section-title">
        <h3>修正流水</h3>
        <span>#{{ editing.id }} · 标记正常前可补齐摘要、对方、金额和余额</span>
      </div>
      <div class="edit-grid">
        <label>
          <span>业务日期</span>
          <NDatePicker v-model:value="form.business_date" type="date" value-format="yyyy-MM-dd" style="width:100%" />
        </label>
        <label>
          <span>摘要</span>
          <input v-model="form.summary" class="form-input" />
        </label>
        <label>
          <span>对方</span>
          <input v-model="form.counterparty" class="form-input" />
        </label>
        <label>
          <span>收入</span>
          <input v-model.number="form.amount_in" type="number" step="0.01" class="form-input" />
        </label>
        <label>
          <span>支出</span>
          <input v-model.number="form.amount_out" type="number" step="0.01" class="form-input" />
        </label>
        <label>
          <span>滚动余额</span>
          <input v-model.number="form.rolling_balance" type="number" step="0.01" class="form-input" />
        </label>
        <label class="wide">
          <span>处理备注</span>
          <input v-model="note" class="form-input" placeholder="可填写补录依据或处理说明" />
        </label>
      </div>
      <div class="btn-row">
        <NButton type="primary" @click="resolveRow" :disabled="saving">{{ saving ? '保存中...' : '保存并标记正常' }}</NButton>
        <NButton secondary @click="cancelEdit">取消</NButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { NDatePicker, NButton } from 'naive-ui'
import { getPendingEvents, resolveEvent, voidEvent } from '@/api/events'
import { fmtAmt } from '@/utils/format'

const rows = ref([])
const summary = ref({ pending_count: 0, abnormal_count: 0 })
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const saving = ref(false)
const errorMsg = ref('')
const editing = ref(null)
const note = ref('')
const filters = ref({ state: '', keyword: '' })
const form = ref({})

function setState(state) {
  filters.value.state = state
  page.value = 1
  reload()
}

async function reload() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { page: page.value, page_size: 50 }
    if (filters.value.state) params.state = filters.value.state
    if (filters.value.keyword) params.keyword = filters.value.keyword
    const result = await getPendingEvents(params)
    rows.value = result.items || []
    summary.value = result.summary || { pending_count: 0, abnormal_count: 0 }
    total.value = result.total || 0
  } catch (e) {
    errorMsg.value = e.message || '异常流水加载失败'
  } finally {
    loading.value = false
  }
}

function startEdit(row) {
  editing.value = row
  note.value = ''
  form.value = {
    business_date: row.business_date,
    summary: row.summary,
    counterparty: row.counterparty,
    amount_in: row.amount_in,
    amount_out: row.amount_out,
    rolling_balance: row.rolling_balance,
  }
}

function cancelEdit() {
  editing.value = null
  form.value = {}
  note.value = ''
}

async function resolveRow() {
  if (!editing.value) return
  saving.value = true
  errorMsg.value = ''
  try {
    await resolveEvent(editing.value.id, { fixes: form.value, note: note.value })
    cancelEdit()
    await reload()
  } catch (e) {
    errorMsg.value = e.message || '异常流水处理失败'
  } finally {
    saving.value = false
  }
}

async function voidRow(row) {
  const reason = window.prompt(`请输入作废原因：${row.summary || row.id}`)
  if (reason === null) return
  saving.value = true
  errorMsg.value = ''
  try {
    await voidEvent(row.id, { reason })
    if (editing.value?.id === row.id) cancelEdit()
    await reload()
  } catch (e) {
    errorMsg.value = e.message || '异常流水作废失败'
  } finally {
    saving.value = false
  }
}

onMounted(reload)
</script>

<style scoped>
@import './common.css';

.status-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.keyword-input {
  min-width: 180px;
}

.compact {
  flex-wrap: nowrap;
}

tr.selected {
  background: #f8f5ef;
}

.edit-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.edit-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

.edit-grid .wide {
  grid-column: span 3;
}

.form-input {
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--panel-2);
  font: inherit;
  color: var(--text);
  min-width: 0;
}

.form-input:focus {
  outline: 2px solid rgba(127, 155, 122, .24);
  border-color: var(--green);
}

.empty-cell {
  text-align: center;
  color: var(--muted);
  padding: 30px;
}

@media (max-width: 980px) {
  .edit-grid {
    grid-template-columns: 1fr;
  }
  .edit-grid .wide {
    grid-column: auto;
  }
}
</style>
