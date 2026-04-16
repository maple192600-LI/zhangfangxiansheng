<template>
  <div class="account-manage">
    <!-- 顶部操作栏 -->
    <div class="top-bar">
      <div class="top-left">
        <select v-model="filterDivision" class="filter" @change="loadData">
          <option :value="null">全部板块</option>
          <option v-for="d in divisions" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
        <select v-model="filterEntity" class="filter">
          <option :value="null">全部法人</option>
          <option v-for="e in filteredEntities" :key="e.id" :value="e.id">{{ e.short_name }}</option>
        </select>
        <input v-model="keyword" class="filter" placeholder="搜索编码/别名/银行/账号" style="width:180px" />
        <select v-model="filterStatus" class="filter" style="width:90px">
          <option value="">全部</option>
          <option value="enabled">启用</option>
          <option value="disabled">停用</option>
        </select>
      </div>
      <div class="top-right">
        <button class="btn btn-secondary" @click="downloadTemplate">下载导入模板</button>
        <button class="btn btn-secondary" @click="triggerImport">批量导入</button>
        <input ref="importInput" type="file" accept=".xls,.xlsx" style="display:none" @change="doImport" />
        <button class="btn btn-primary" @click="openForm()">+ 新建账户</button>
      </div>
    </div>

    <!-- Excel 风格平铺表格 -->
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th class="col-id">ID</th>
            <th class="col-code">编码</th>
            <th class="col-alias">别名</th>
            <th class="col-entity">法人</th>
            <th class="col-bank">开户银行</th>
            <th class="col-number">账号</th>
            <th class="col-type">账户类型</th>
            <th class="col-instrument">工具类型</th>
            <th class="col-balance">期初余额</th>
            <th class="col-date">余额日期</th>
            <th class="col-method">录入方式</th>
            <th class="col-status">状态</th>
            <th class="col-notes">备注</th>
            <th class="col-action">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in filteredAccounts" :key="a.id"
              :class="{ disabled: a.status === 'disabled' }"
              @dblclick="openForm(a)">
            <td>{{ a.id }}</td>
            <td><strong>{{ a.account_code }}</strong></td>
            <td>{{ a.account_alias }}</td>
            <td>{{ a.entity_name || '-' }}</td>
            <td>{{ a.bank_name || '-' }}</td>
            <td class="mono">{{ a.account_number || '-' }}</td>
            <td>{{ a.account_type }}</td>
            <td>{{ a.instrument_type }}</td>
            <td class="money">{{ fmtMoney(a.initial_balance) }}</td>
            <td>{{ a.balance_date || '-' }}</td>
            <td>{{ a.input_method === 'bank_import' ? '银行导入' : '手工' }}</td>
            <td><span class="badge" :class="a.status">{{ a.status === 'enabled' ? '启用' : '停用' }}</span></td>
            <td class="ellipsis" :title="a.notes">{{ a.notes || '-' }}</td>
            <td class="action-cell">
              <button class="btn btn-secondary btn-sm" @click="openForm(a)">编辑</button>
              <button class="btn btn-secondary btn-sm" v-if="a.status==='enabled'" @click="toggleStatus(a, 'disabled')">停用</button>
              <button class="btn btn-secondary btn-sm" v-else @click="toggleStatus(a, 'enabled')">启用</button>
            </td>
          </tr>
          <tr v-if="!filteredAccounts.length">
            <td colspan="14" class="empty">暂无账户数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="bottom-bar">
      <span>共 {{ filteredAccounts.length }} 条记录</span>
    </div>

    <!-- ── 账户表单弹窗 ── -->
    <div class="modal-mask" v-if="showForm" @click.self="showForm=false">
      <div class="modal" style="max-width:640px">
        <h3>{{ editing ? '编辑账户' : '新建账户' }}</h3>
        <div class="form-grid">
          <div class="form-group">
            <label>所属法人 *</label>
            <select v-model="form.entity_id" class="filter">
              <option v-for="e in allEntities" :key="e.id" :value="e.id">{{ e.short_name }}（{{ e.entity_code }}）</option>
            </select>
          </div>
          <div class="form-group">
            <label>账户编码 *</label>
            <input v-model="form.account_code" class="filter" placeholder="如 A007" :disabled="!!editing" />
          </div>
          <div class="form-group">
            <label>账户别名 *</label>
            <input v-model="form.account_alias" class="filter" placeholder="如 中行手工户" />
          </div>
          <div class="form-group">
            <label>开户银行</label>
            <input v-model="form.bank_name" class="filter" placeholder="如 中国银行" />
          </div>
          <div class="form-group">
            <label>开户行</label>
            <input v-model="form.branch_name" class="filter" placeholder="如 太原分行" />
          </div>
          <div class="form-group">
            <label>账号</label>
            <input v-model="form.account_number" class="filter" placeholder="银行卡号" />
          </div>
          <div class="form-group">
            <label>账户类型 *</label>
            <select v-model="form.account_type" class="filter">
              <option value="银行账户">银行账户</option>
              <option value="现金">现金</option>
              <option value="票据">票据</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <div class="form-group">
            <label>工具类型 *</label>
            <select v-model="form.instrument_type" class="filter">
              <option value="银行存款">银行存款</option>
              <option value="现金">现金</option>
              <option value="票据">票据</option>
              <option value="受限资金">受限资金</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <div class="form-group">
            <label>录入方式 *</label>
            <select v-model="form.input_method" class="filter">
              <option value="manual">手工录入</option>
              <option value="bank_import">银行导入</option>
            </select>
          </div>
          <div class="form-group">
            <label>币种 *</label>
            <input v-model="form.currency" class="filter" />
          </div>
          <div class="form-group" v-if="!editing">
            <label>期初余额 *</label>
            <input v-model.number="form.initial_balance" type="number" step="0.01" class="filter" />
          </div>
          <div class="form-group" v-if="!editing">
            <label>余额日期 *</label>
            <input v-model="form.balance_date" type="date" class="filter" />
          </div>
          <div class="form-group" v-if="editing">
            <label>状态</label>
            <select v-model="form.status" class="filter">
              <option value="enabled">启用</option>
              <option value="disabled">停用</option>
            </select>
          </div>
          <div class="form-group" style="grid-column:span 2">
            <label>备注</label>
            <input v-model="form.notes" class="filter" />
          </div>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showForm=false">取消</button>
          <button class="btn btn-primary" @click="saveAccount">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as api from '@/api/master'

const divisions = ref([])
const allEntities = ref([])
const accounts = ref([])
const importInput = ref(null)

const filterDivision = ref(null)
const filterEntity = ref(null)
const filterStatus = ref('')
const keyword = ref('')

const showForm = ref(false)
const editing = ref(null)
const form = ref({
  entity_id: null, account_code: '', account_alias: '', bank_name: '', branch_name: '',
  account_number: '', account_type: '银行账户', instrument_type: '银行存款',
  input_method: 'manual', currency: 'CNY', initial_balance: 0, balance_date: '',
  status: 'enabled', notes: '',
})

const filteredEntities = computed(() => {
  if (!filterDivision.value) return allEntities.value
  return allEntities.value.filter(e => e.division_id === filterDivision.value)
})

const filteredAccounts = computed(() => {
  let list = accounts.value
  if (filterEntity.value) list = list.filter(a => a.entity_id === filterEntity.value)
  if (filterStatus.value) list = list.filter(a => a.status === filterStatus.value)
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(a =>
      (a.account_code || '').toLowerCase().includes(kw) ||
      (a.account_alias || '').toLowerCase().includes(kw) ||
      (a.bank_name || '').toLowerCase().includes(kw) ||
      (a.account_number || '').toLowerCase().includes(kw) ||
      (a.entity_name || '').toLowerCase().includes(kw)
    )
  }
  return list
})

async function loadData() {
  try {
    const [divs, ents, accs] = await Promise.all([
      api.getDivisions(),
      api.getEntities({ page: 1, page_size: 200 }),
      api.getAccounts({ page: 1, page_size: 500 }),
    ])
    divisions.value = divs || []
    allEntities.value = ents?.items || []
    accounts.value = accs?.items || []
  } catch (e) { console.error(e) }
}

function openForm(acc) {
  if (acc) {
    editing.value = acc
    form.value = {
      entity_id: acc.entity_id, account_code: acc.account_code, account_alias: acc.account_alias,
      bank_name: acc.bank_name || '', branch_name: acc.branch_name || '',
      account_number: acc.account_number || '', account_type: acc.account_type,
      instrument_type: acc.instrument_type, input_method: acc.input_method,
      currency: acc.currency, initial_balance: acc.initial_balance,
      balance_date: acc.balance_date, status: acc.status, notes: acc.notes || '',
    }
  } else {
    editing.value = null
    form.value = {
      entity_id: null, account_code: '', account_alias: '', bank_name: '', branch_name: '',
      account_number: '', account_type: '银行账户', instrument_type: '银行存款',
      input_method: 'manual', currency: 'CNY', initial_balance: 0,
      balance_date: new Date().toISOString().slice(0, 10), status: 'enabled', notes: '',
    }
  }
  showForm.value = true
}

async function saveAccount() {
  try {
    const payload = {
      entity_id: form.value.entity_id, account_code: form.value.account_code,
      account_alias: form.value.account_alias, bank_name: form.value.bank_name,
      branch_name: form.value.branch_name, account_number: form.value.account_number,
      account_type: form.value.account_type, instrument_type: form.value.instrument_type,
      input_method: form.value.input_method, currency: form.value.currency,
      notes: form.value.notes,
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
    await loadData()
  } catch (e) { alert(e.message || '保存失败') }
}

async function toggleStatus(acc, status) {
  try {
    await api.updateAccount(acc.id, { status })
    await loadData()
  } catch (e) { alert(e.message) }
}

function fmtMoney(v) {
  if (v == null) return '-'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function downloadTemplate() {
  window.open('/api/accounts/template', '_blank')
}

function triggerImport() {
  importInput.value.click()
}

async function doImport(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const fd = new FormData()
    fd.append('file', file)
    const resp = await fetch('/api/accounts/import', { method: 'POST', body: fd })
    const result = await resp.json()
    if (result.code === 0) {
      const d = result.data
      let msg = `导入完成！\n创建板块: ${d.created_divisions}\n创建法人: ${d.created_entities}\n创建账户: ${d.created_accounts}`
      if (d.error_count > 0) msg += `\n\n${d.error_count} 条错误：\n${d.errors.join('\n')}`
      alert(msg)
      await loadData()
    } else {
      alert('导入失败: ' + result.message)
    }
  } catch (e) { alert('导入出错: ' + e.message) }
  e.target.value = ''
}

onMounted(loadData)
</script>

<style scoped>
.account-manage {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 80px);
}

/* 顶部操作栏 */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(251,250,247,0.95);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  margin-bottom: 10px;
  gap: 10px;
  flex-wrap: wrap;
}
.top-left { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.top-right { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

/* 表格 */
.table-wrap {
  flex: 1;
  overflow: auto;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  white-space: nowrap;
}
.data-table th {
  position: sticky; top: 0; z-index: 2;
  background: #f5f2eb;
  text-align: left;
  padding: 8px 10px;
  border-bottom: 2px solid var(--line);
  color: #5b635e;
  font-weight: 600;
  font-size: 12px;
}
.data-table td {
  padding: 7px 10px;
  border-bottom: 1px solid #f0ede6;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.data-table tr:hover { background: #faf8f3; }
.data-table tr.disabled { opacity: 0.55; }

.data-table .money { font-weight: 600; color: #3f5b3d; text-align: right; }
.data-table .mono { font-family: monospace; font-size: 12px; }
.data-table .ellipsis { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
.data-table .action-cell { white-space: nowrap; }
.data-table .empty { text-align: center; color: var(--muted); padding: 40px; font-size: 14px; }

/* 列宽 */
.col-id { width: 40px; }
.col-code { width: 70px; }
.col-alias { width: 100px; }
.col-entity { width: 80px; }
.col-bank { width: 80px; }
.col-number { width: 130px; }
.col-type { width: 70px; }
.col-instrument { width: 70px; }
.col-balance { width: 90px; text-align: right; }
.col-date { width: 90px; }
.col-method { width: 70px; }
.col-status { width: 55px; }
.col-notes { min-width: 100px; }
.col-action { width: 120px; }

/* 底部 */
.bottom-bar {
  padding: 8px 14px;
  color: var(--muted);
  font-size: 12px;
}

/* 徽章 */
.badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.badge.enabled { background: #edf4ea; color: #3f5b3d; }
.badge.disabled { background: #f5ece5; color: #8a6e52; }

/* 按钮 */
.btn-sm { padding: 4px 8px; font-size: 12px; }

/* 弹窗 */
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #faf8f3; border-radius: 16px; padding: 24px; width: 90%; max-width: 520px; box-shadow: 0 8px 32px rgba(0,0,0,0.18); }
.modal h3 { margin: 0 0 16px 0; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 12px; color: #5b635e; margin-bottom: 3px; }
.form-group .filter { width: 100%; box-sizing: border-box; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }

/* 响应式 */
@media (max-width: 1000px) {
  .top-bar { flex-direction: column; align-items: flex-start; }
  .form-grid { grid-template-columns: 1fr; }
}
</style>
