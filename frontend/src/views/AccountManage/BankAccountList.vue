<template>
  <div>
    <div class="filters-bar">
      <input v-model="bankKeyword" class="filter" placeholder="搜索账户编号/开户银行/银行账号" style="width:220px" />
      <select v-model="filterStatus" class="filter" style="width:90px">
        <option value="">全部状态</option>
        <option value="enabled">启用</option>
        <option value="disabled">停用</option>
      </select>
      <div style="flex:1"></div>
      <div class="btn-row">
        <div class="dropdown" :class="{ open: dropdownOpen }" v-if="selectedIds.length > 0">
          <button class="btn btn-secondary" @click="dropdownOpen = !dropdownOpen">批量操作 ({{ selectedIds.length }})</button>
          <div class="dropdown-menu">
            <button @click="batchAction('enable'); dropdownOpen = false">批量启用</button>
            <button @click="batchAction('disable'); dropdownOpen = false">批量停用</button>
            <button @click="batchAction('delete'); dropdownOpen = false" class="dropdown-item-danger">批量删除</button>
          </div>
        </div>
        <button class="btn btn-primary" @click="openForm()">+ 新建银行账户</button>
      </div>
    </div>

    <div v-if="!filteredBankAccounts.length" style="text-align:center;color:var(--muted);padding:40px 0">
      暂无银行账户数据
    </div>
    <template v-else>
      <div class="table-wrap table-wrap-wide">
        <table>
          <thead>
            <tr>
              <th class="col-ck"><input type="checkbox" :checked="isAllSelected" @change="toggleAll" /></th>
              <th v-for="col in activeColumns" :key="col.key">{{ col.label }}</th>
              <th class="col-action">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in filteredBankAccounts" :key="a.id"
                :class="{ disabled: a.status === 'disabled', selected: selectedIds.includes(a.id) }" @dblclick="openForm(a)">
              <td class="col-ck"><input type="checkbox" :value="a.id" v-model="selectedIds" /></td>
              <td v-for="col in activeColumns" :key="col.key" :class="col.type === 'money' ? 'money' : (col.type === 'code' || col.type === 'text' && (col.key === 'account_number' || col.key === 'account_last_four') ? 'mono' : '')">
                <template v-if="col.type === 'bool'">
                  <span :class="getBoolVal(a, col.key) ? 'bool-yes' : 'bool-no'">{{ getBoolVal(a, col.key) ? '是' : '否' }}</span>
                </template>
                <span v-else-if="col.type === 'tag'" class="tag" :class="col.key === 'account_type' ? 'tag-blue' : 'tag-gray'">{{ a[col.key] || '-' }}</span>
                <span v-else-if="col.type === 'status'" class="tag" :class="a.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ a.status === 'enabled' ? '启用' : '停用' }}</span>
                <template v-else-if="col.type === 'money'">{{ fmtMoney(a[col.key]) }}</template>
                <strong v-else-if="col.type === 'code'">{{ a[col.key] }}</strong>
                <template v-else-if="col.type === 'input_method'">{{ a.input_method === 'bank_import' ? '银行导入' : (a.input_method === 'manual' ? '手工填写' : (a.input_method || '手工填写')) }}</template>
                <template v-else>{{ a[col.key] || '-' }}</template>
              </td>
              <td class="action-cell">
                <button class="btn btn-secondary btn-sm" @click="openForm(a)">编辑</button>
                <button class="btn btn-secondary btn-sm" v-if="a.status==='enabled'" @click="toggleStatus(a,'disabled')">停用</button>
                <button class="btn btn-secondary btn-sm" v-else @click="toggleStatus(a,'enabled')">启用</button>
                <button class="btn btn-warn btn-sm" @click="deleteBank(a)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="bottom-bar">
        <span class="count-info">共 {{ filteredBankAccounts.length }} 条银行账户记录</span>
      </div>
    </template>

    <!-- 银行账户表单弹窗 -->
    <div class="modal-mask" v-if="showForm" @click.self="showForm=false">
      <div class="modal modal-lg">
        <h3>{{ editing ? '编辑银行账户' : '新建银行账户' }}</h3>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">所属单位 *</label>
            <select v-model="form.entity_id" class="form-input">
              <option :value="null" disabled>-- 请选择所属单位 --</option>
              <optgroup v-for="d in divisions" :key="d.id" :label="d.name">
                <option v-for="e in getEntitiesForDivision(d.id)" :key="e.id" :value="e.id">{{ e.short_name }}（{{ e.entity_code }}）</option>
              </optgroup>
              <option v-for="e in ungroupedEntities" :key="e.id" :value="e.id">{{ e.short_name }}（{{ e.entity_code }}）</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">开户银行</label>
            <input v-model="form.bank_name" class="form-input" placeholder="如 中国银行" />
          </div>
          <div class="form-group">
            <label class="form-label">银行账号</label>
            <input v-model="form.account_number" class="form-input" placeholder="完整账号，不加空格" />
          </div>
          <div class="form-group">
            <label class="form-label">开户行名称</label>
            <input v-model="form.branch_name" class="form-input" placeholder="如 中国银行上海浦东支行" />
          </div>
          <div class="form-group">
            <label class="form-label">账户后四位</label>
            <input v-model="form.account_last_four" class="form-input" placeholder="留空自动从银行账号提取" />
          </div>
          <div class="form-group">
            <label class="form-label">账户类型</label>
            <select v-model="form.account_type" class="form-input">
              <option v-for="t in BANK_ACCOUNT_TYPES" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">资金类型</label>
            <select v-model="form.instrument_type" class="form-input">
              <option v-for="t in INSTRUMENT_TYPES" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">是否网银</label>
            <select v-model="form.has_online_banking" class="form-input">
              <option :value="true">是</option>
              <option :value="false">否</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">录入方式</label>
            <select v-model="form.input_method" class="form-input">
              <option value="手工填写">手工填写</option>
              <option value="网银导入">网银导入</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">币种</label>
            <input v-model="form.currency" class="form-input" placeholder="CNY" />
          </div>
          <div class="form-group" v-if="!editing">
            <label class="form-label">期初余额</label>
            <input v-model.number="form.initial_balance" type="number" step="0.01" class="form-input" placeholder="系统起算余额" />
          </div>
          <div class="form-group" v-if="!editing">
            <label class="form-label">余额日期</label>
            <input v-model="form.balance_date" type="date" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">是否纳入日报</label>
            <select v-model="form.include_in_daily_report" class="form-input">
              <option :value="true">是</option>
              <option :value="false">否</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">是否允许手工录入</label>
            <select v-model="form.allow_manual_entry" class="form-input">
              <option :value="true">是</option>
              <option :value="false">否</option>
            </select>
          </div>
          <div class="form-group" v-if="editing">
            <label class="form-label">状态</label>
            <select v-model="form.status" class="form-input">
              <option value="enabled">启用</option>
              <option value="disabled">停用</option>
            </select>
          </div>
          <div class="form-group" style="grid-column:span 2">
            <label class="form-label">备注</label>
            <input v-model="form.notes" class="form-input" placeholder="补充说明" />
          </div>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showForm=false">取消</button>
          <button class="btn btn-primary" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import * as api from '@/api/master'
import { fmtAmt } from '@/utils/format'
import { todayLocalDate } from '@/utils/date'

const props = defineProps({
  divisions: { type: Array, default: () => [] },
  allEntities: { type: Array, default: () => [] },
  accounts: { type: Array, default: () => [] },
})
const emit = defineEmits(['refresh'])

const BANK_ACCOUNT_TYPES = ['银行账户', '现金', '票据', '其他']
const INSTRUMENT_TYPES = ['银行存款', '现金', '票据', '受限资金']
const BANK_ACCOUNT_TYPE_FILTER = ['银行账户', '基本户', '一般户', '临时户', '农民工工资专用账户', '信用证账户', '贷款账户']

const DEFAULT_COLUMNS = [
  { key: 'entity_name', label: '所属单位', type: 'text' },
  { key: 'account_code', label: '账户编号', type: 'code' },
  { key: 'bank_name', label: '开户银行', type: 'text' },
  { key: 'account_number', label: '银行账号', type: 'text' },
  { key: 'branch_name', label: '开户行名称', type: 'text' },
  { key: 'account_type', label: '账户类型', type: 'tag' },
  { key: 'instrument_type', label: '资金类型', type: 'tag' },
  { key: 'has_online_banking', label: '网银', type: 'bool' },
  { key: 'initial_balance', label: '期初余额', type: 'money' },
  { key: 'status', label: '状态', type: 'status' },
]

const selectedIds = ref([])
const dropdownOpen = ref(false)
const bankKeyword = ref('')
const filterStatus = ref('')

const showForm = ref(false)
const editing = ref(null)
const form = ref(makeForm())

function makeForm() {
  return {
    entity_id: null, account_code: '', bank_name: '', branch_name: '',
    account_number: '', account_last_four: '', account_type: '银行账户',
    instrument_type: '银行存款', has_online_banking: false, input_method: '手工填写',
    currency: 'CNY', include_in_daily_report: true, allow_manual_entry: true,
    initial_balance: 0, balance_date: '', status: 'enabled', notes: '',
  }
}

const ungroupedEntities = computed(() => props.allEntities.filter(e => !e.division_id))
function getEntitiesForDivision(divisionId) { return props.allEntities.filter(e => e.division_id === divisionId) }

const filteredBankAccounts = computed(() => {
  let items = props.accounts.filter(a =>
    a.bank_name ||
    BANK_ACCOUNT_TYPE_FILTER.includes(a.account_type) ||
    a.instrument_type === '银行存款'
  )
  if (filterStatus.value) items = items.filter(a => a.status === filterStatus.value)
  if (bankKeyword.value) {
    const kw = bankKeyword.value.toLowerCase()
    items = items.filter(a =>
      (a.account_code || '').toLowerCase().includes(kw) ||
      (a.bank_name || '').toLowerCase().includes(kw) ||
      (a.account_number || '').toLowerCase().includes(kw)
    )
  }
  return items
})

const activeColumns = computed(() => {
  const accs = filteredBankAccounts.value
  if (!accs.length) return []
  return DEFAULT_COLUMNS.filter(col => {
    return accs.some(a => {
      const v = a[col.key]
      return v !== null && v !== undefined && !(typeof v === 'string' && v.trim() === '')
    })
  })
})

const isAllSelected = computed(() => {
  const list = filteredBankAccounts.value
  return list.length > 0 && list.every(a => selectedIds.value.includes(a.id))
})

function toggleAll() { selectedIds.value = isAllSelected.value ? [] : filteredBankAccounts.value.map(a => a.id) }
function getBoolVal(account, key) { return account[key] !== false }
function fmtMoney(v) { return fmtAmt(v) }

function openForm(item) {
  if (item) {
    editing.value = item
    form.value = {
      entity_id: item.entity_id || null, account_code: item.account_code || '',
      bank_name: item.bank_name || '', branch_name: item.branch_name || '',
      account_number: item.account_number || '', account_last_four: item.account_last_four || '',
      account_type: item.account_type || '银行账户', instrument_type: item.instrument_type || '银行存款',
      has_online_banking: item.has_online_banking || false,
      input_method: item.input_method === 'bank_import' ? '网银导入' : '手工填写',
      currency: item.currency || 'CNY', include_in_daily_report: item.include_in_daily_report !== false,
      allow_manual_entry: item.allow_manual_entry !== false,
      initial_balance: item.initial_balance || 0, balance_date: item.balance_date || '',
      status: item.status || 'enabled', notes: item.notes || '',
    }
  } else {
    editing.value = null
    form.value = { ...makeForm(), balance_date: todayLocalDate() }
  }
  showForm.value = true
}

async function save() {
  if (!form.value.bank_name.trim() && !form.value.account_number.trim()) {
    alert('请至少填写开户银行或银行账号'); return
  }
  try {
    const payload = {
      entity_id: form.value.entity_id,
      account_code: form.value.account_code?.trim() || undefined,
      bank_name: form.value.bank_name.trim(), branch_name: form.value.branch_name.trim(),
      account_number: form.value.account_number.trim(),
      account_last_four: form.value.account_last_four || (form.value.account_number ? form.value.account_number.slice(-4) : ''),
      account_type: form.value.account_type, instrument_type: form.value.instrument_type,
      has_online_banking: form.value.has_online_banking,
      input_method: form.value.input_method === '网银导入' ? 'bank_import' : 'manual',
      currency: form.value.currency, include_in_daily_report: form.value.include_in_daily_report,
      allow_manual_entry: form.value.allow_manual_entry, notes: form.value.notes.trim(),
    }
    if (editing.value) {
      payload.status = form.value.status
      await api.updateAccount(editing.value.id, payload)
    } else {
      payload.initial_balance = form.value.initial_balance
      payload.balance_date = form.value.balance_date
      await api.createAccount(payload)
    }
    showForm.value = false
    emit('refresh')
  } catch (e) { alert(e.message || '保存失败') }
}

async function toggleStatus(item, status) {
  try {
    await api.updateAccount(item.id, { status })
    emit('refresh')
  } catch (e) { alert(e.message) }
}

async function deleteBank(item) {
  if (!confirm(`确定删除银行账户「${item.account_code} ${item.bank_name || ''}」？此操作不可撤销。`)) return
  try {
    await api.batchActionAccounts([item.id], 'delete')
    emit('refresh')
  } catch (e) { alert(e.message || '删除失败') }
}

async function batchAction(action) {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  const labels = { enable: '启用', disable: '停用', delete: '删除' }
  if (!confirm(`确定批量${labels[action] || action} ${ids.length} 个银行账户？${action === 'delete' ? '此操作不可撤销！' : ''}`)) return
  try {
    const result = await api.batchActionAccounts(ids, action)
    const failedCount = result.failed?.length || 0
    if (failedCount > 0) {
      const msgs = result.failed.map(f => f.message).join('\n')
      alert(`${result.success} 条成功，${failedCount} 条失败：\n${msgs}`)
    }
    selectedIds.value = []
    emit('refresh')
  } catch (e) { alert(e.message || '批量操作失败') }
}
</script>

<style scoped>
@import '../../views/common.css';

.table-wrap { flex: 1; overflow: auto; max-height: calc(100vh - 300px); }
.table-wrap-wide { overflow-x: auto; }
tr.disabled { opacity: 0.55; }
tr.selected { background: #f0f5ef; }
.col-ck { width: 36px; text-align: center; }
.col-ck input[type="checkbox"] { cursor: pointer; }
.col-action { width: 120px; }
.action-cell { white-space: nowrap; }
.mono { font-family: monospace; font-size: 12px; }
.bool-yes { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 500; background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
.bool-no { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 500; background: #f5f5f5; color: #9e9e9e; border: 1px solid #e0e0e0; }
.dropdown { position: relative; display: inline-block; }
.dropdown-menu { display: none; position: absolute; right: 0; top: 100%; background: white; border: 1px solid #ddd; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 100; min-width: 120px; }
.dropdown-menu button { display: block; width: 100%; padding: 8px 16px; border: none; background: none; text-align: left; cursor: pointer; font-size: 13px; }
.dropdown-menu button:hover { background: #f5f5f5; }
.dropdown.open .dropdown-menu { display: block; }
.dropdown-item-danger { color: #9b3d2f; }
.dropdown-item-danger:hover { background: #fdf2ef !important; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; overflow-y: auto; }
.modal { background: #faf8f3; border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 640px; max-height: 90vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.18); position: relative; z-index: 1001; }
.modal-lg { max-width: 780px; }
.modal h3 { margin: 0 0 16px 0; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }
.form-grid .form-input { max-width: none; }
@media (max-width: 1000px) { .form-grid { grid-template-columns: 1fr; } }
</style>
