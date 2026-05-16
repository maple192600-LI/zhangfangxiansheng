<template>
  <div>
    <div class="section table-workspace-page">
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
        <input v-model="filters.keyword" class="filter keyword-input" placeholder="搜索摘要/对方" @keyup.enter="onKeywordEnter" />
        <div style="flex:1"></div>
        <NButton secondary @click="reload" :disabled="loading">{{ loading ? '刷新中...' : '刷新' }}</NButton>
      </div>

      <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>正在加载异常流水...</p>
      </div>
      <div v-else class="table-workspace-main data-view">
        <AdvancedDataTable
          ref="tableRef"
          :columns="appliedColumns"
          :data="rows"
          :pagination="false"
          fill-parent
          show-toolbar
          :density="tableDensity"
          :table-key="TABLE_KEY"
          show-column-settings
          show-reset-preferences
          :row-class="rowClassFn"
          :row-key="'id'"
          empty-text="暂无待处理异常流水"
          @density-change="onDensityChange"
          @column-width-change="onColumnWidthChange"
          @column-order-change="onColumnOrderChange"
          @column-visibility-change="onColumnVisibilityChange"
          @preferences-reset="onPreferencesReset"
          @cell-click="onCellClick"
        />
        <div class="bottom-bar">
          <span class="count-info">共 {{ total }} 条</span>
          <button class="btn btn-secondary btn-sm" :disabled="page <= 1" @click="prevPage">上一页</button>
          <span style="font-size:var(--font-size-xs);color:var(--muted)">第 {{ page }} 页</span>
          <button class="btn btn-secondary btn-sm" :disabled="page * 50 >= total" @click="nextPage">下一页</button>
        </div>
      </div>
    </div>

    <div class="section" v-if="editing">
      <div class="section-title">
        <h3>修正流水</h3>
        <span>#{{ editing.id }} · 标记正常前可补齐摘要、对方、金额和余额</span>
      </div>
      <div class="edit-grid">
        <label>
          <span>业务日期</span>
          <NDatePicker :value="businessDateTs" @update:value="v => businessDateTs = v" type="date" style="width:100%" />
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
import { onMounted, ref, computed, watch, nextTick } from 'vue'
import { NDatePicker, NButton } from 'naive-ui'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'
import { getPendingEvents, resolveEvent, voidEvent } from '@/api/events'
import {
  emptyDashFormatter,
  moneyFormatter,
  exceptionStateFormatter,
  exceptionActionFormatter,
} from '@/utils/tabulatorFormatters'
import {
  getPreferences,
  applyPreferences,
  saveColumnWidth,
  saveColumnVisibility,
  saveColumnOrder,
  saveDensity,
  resetPreferences,
} from '@/composables/useAdvancedTablePreferences'

const TABLE_KEY = 'exception-center'

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
const tableRef = ref(null)
const businessDateTs = ref(null)

function dateStringToTs(s) {
  if (!s) return null
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d).getTime()
}
function tsToDateString(ts) {
  if (ts == null) return ''
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const DEFAULT_COLUMNS = [
  { field: 'business_date', title: '日期', width: 110, formatter: emptyDashFormatter },
  { field: 'entity_name', title: '单位', width: 120, formatter: emptyDashFormatter },
  { field: 'account_name', title: '账户', width: 140, formatter: emptyDashFormatter },
  { field: 'summary', title: '摘要', width: 160, formatter: emptyDashFormatter },
  { field: 'counterparty', title: '对方', width: 120, formatter: emptyDashFormatter },
  { field: 'amount_in', title: '收入', width: 120, hozAlign: 'right', formatter: moneyFormatter },
  { field: 'amount_out', title: '支出', width: 120, hozAlign: 'right', formatter: moneyFormatter },
  { field: 'state', title: '状态', width: 90, hozAlign: 'center', formatter: exceptionStateFormatter },
  { field: 'source', title: '来源', width: 100, formatter: emptyDashFormatter },
  {
    field: '_actions',
    title: '操作',
    width: 140,
    hozAlign: 'center',
    headerSort: false,
    frozen: true,
    formatter: exceptionActionFormatter,
  },
]

const preferencesVersion = ref(0)
const tableDensity = ref(getPreferences(TABLE_KEY).density || 'default')

function touchPreferences() { preferencesVersion.value++ }

const appliedColumns = computed(() => {
  preferencesVersion.value
  return applyPreferences(DEFAULT_COLUMNS, getPreferences(TABLE_KEY))
})

function onDensityChange(value) {
  tableDensity.value = value
  saveDensity(TABLE_KEY, value)
}

function onColumnWidthChange({ field, width }) {
  saveColumnWidth(TABLE_KEY, field, width)
}

function onColumnOrderChange(order) {
  saveColumnOrder(TABLE_KEY, order)
}

function onColumnVisibilityChange({ field, visible }) {
  saveColumnVisibility(TABLE_KEY, field, visible)
  touchPreferences()
}

function onPreferencesReset() {
  resetPreferences(TABLE_KEY)
  tableDensity.value = 'default'
  touchPreferences()
}

function rowClassFn(row) {
  if (editing.value && row.id === editing.value.id) return 'editing-row'
  return ''
}

function onCellClick({ event, rowData }) {
  const btn = event.target.closest('[data-action]')
  if (!btn) return
  const action = btn.dataset.action
  if (action === 'edit') {
    startEdit(rowData)
  } else if (action === 'void') {
    voidRow(rowData)
  }
}

function setState(state) {
  filters.value.state = state
  page.value = 1
  reload()
}

function onKeywordEnter() {
  page.value = 1
  reload()
}

function prevPage() {
  if (page.value > 1) {
    page.value--
    reload()
  }
}

function nextPage() {
  if (page.value * 50 < total.value) {
    page.value++
    reload()
  }
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
  businessDateTs.value = dateStringToTs(row.business_date)
  triggerRedraw()
}

function cancelEdit() {
  editing.value = null
  form.value = {}
  note.value = ''
  businessDateTs.value = null
  triggerRedraw()
}

async function resolveRow() {
  if (!editing.value) return
  saving.value = true
  errorMsg.value = ''
  try {
    const payload = { ...form.value, business_date: tsToDateString(businessDateTs.value) }
    await resolveEvent(editing.value.id, { fixes: payload, note: note.value })
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

function triggerRedraw() {
  nextTick(() => {
    try {
      const t = tableRef.value?.table
      if (t) {
        t.redraw(true)
      }
    } catch (e) {
      rows.value = [...rows.value]
    }
  })
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
