<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>账户数据管理</h3>
        <span>管理所有核算组织下的单位账户</span>
      </div>
      <div class="filters-bar">
        <select v-model="filterDivision" class="filter" @change="loadData">
          <option :value="null">全部核算组织</option>
          <option v-for="d in divisions" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
        <select v-model="filterEntity" class="filter">
          <option :value="null">全部单位</option>

          <option v-for="e in filteredEntities" :key="e.id" :value="e.id">{{ e.short_name }}</option>
        </select>
        <input v-model="keyword" class="filter" placeholder="搜索账户编号/账户名称/银行/账号" style="width:220px" />
        <select v-model="filterStatus" class="filter" style="width:90px">
          <option value="">全部</option>
          <option value="enabled">启用</option>
          <option value="disabled">停用</option>
        </select>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary" @click="downloadTemplate">下载导入模板</button>
          <button class="btn btn-secondary" @click="triggerImport">批量导入</button>
          <input ref="importInput" type="file" accept=".xls,.xlsx" style="display:none" @change="doImport" />
          <button class="btn btn-primary" @click="openForm()">+ 新建账户</button>
        </div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-id">ID</th>
              <th class="col-code">账户编号</th>
              <th class="col-alias">账户名称</th>
              <th class="col-entity">单位简称</th>
              <th class="col-bank">开户银行</th>
              <th class="col-number">银行账号</th>
              <th class="col-type">账户类型</th>
              <th class="col-instrument">资金类型</th>
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
              <td><span class="tag tag-blue">{{ a.account_type }}</span></td>
              <td><span class="tag tag-gray">{{ a.instrument_type }}</span></td>
              <td class="money">{{ fmtMoney(a.initial_balance) }}</td>
              <td>{{ a.balance_date || '-' }}</td>
              <td>{{ a.input_method === 'bank_import' ? '银行导入' : '手工' }}</td>
              <td><span class="tag" :class="a.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ a.status === 'enabled' ? '启用' : '停用' }}</span></td>
              <td class="ellipsis" :title="a.notes">{{ a.notes || '-' }}</td>
              <td class="action-cell">
                <button class="btn btn-secondary btn-sm" @click="openForm(a)">编辑</button>
                <button class="btn btn-secondary btn-sm" v-if="a.status==='enabled'" @click="toggleStatus(a, 'disabled')">停用</button>
                <button class="btn btn-secondary btn-sm" v-else @click="toggleStatus(a, 'enabled')">启用</button>
              </td>
            </tr>
            <tr v-if="!filteredAccounts.length">
              <td colspan="14" style="text-align:center;color:var(--muted);padding:30px">暂无账户数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="bottom-bar" v-if="filteredAccounts.length">
      <span class="count-info">共 {{ filteredAccounts.length }} 条记录</span>
    </div>

    <!-- 账户表单弹窗 -->
    <div class="modal-mask" v-if="showForm" @click.self="showForm=false">
      <div class="modal modal-lg">
        <h3>{{ editing ? '编辑账户' : '新建账户' }}</h3>
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
            <label class="form-label">账户编号 *</label>
            <input v-model="form.account_code" class="form-input" placeholder="如 ZH0001" :disabled="!!editing" />
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
            <input v-model="form.account_last_four" class="form-input" placeholder="银行账号后四位" />
          </div>
          <div class="form-group">
            <label class="form-label">账户类型 *</label>
            <select v-model="form.account_type" class="form-input">
              <option value="" disabled>-- 请选择 --</option>
              <option value="基本户">基本户</option>
              <option value="一般户">一般户</option>
              <option value="临时户">临时户</option>
              <option value="现金账户">现金账户</option>
              <option value="农民工工资专用账户">农民工工资专用账户</option>
              <option value="票据账户">票据账户</option>
              <option value="信用证账户">信用证账户</option>
              <option value="贷款账户">贷款账户</option>
              <option value="其他账户">其他账户</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">资金类型 *</label>
            <select v-model="form.instrument_type" class="form-input">
              <option value="" disabled>-- 请选择 --</option>
              <option value="银行存款">银行存款</option>
              <option value="现金">现金</option>
              <option value="票据">票据</option>
              <option value="信用证">信用证</option>
              <option value="保证金">保证金</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">是否网银 *</label>
            <select v-model="form.has_online_banking" class="form-input">
              <option :value="true">是</option>
              <option :value="false">否</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">录入方式 *</label>
            <select v-model="form.input_method" class="form-input">
              <option value="网银导入">网银导入</option>
              <option value="手工填写">手工填写</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">币种</label>
            <input v-model="form.currency" class="form-input" placeholder="CNY" />
          </div>
          <div class="form-group" v-if="!editing">
            <label class="form-label">期初余额 *</label>
            <input v-model.number="form.initial_balance" type="number" step="0.01" class="form-input" placeholder="系统起算余额" />
          </div>
          <div class="form-group" v-if="!editing">
            <label class="form-label">余额日期 *</label>
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
          <button class="btn btn-primary" @click="saveAccount">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as api from '@/api/master'
import { fmtAmt } from '@/utils/format'

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
  entity_id: null, account_code: '', bank_name: '', branch_name: '',
  account_number: '', account_last_four: '', account_type: '', instrument_type: '',
  has_online_banking: false, input_method: '手工填写', currency: 'CNY',
  include_in_daily_report: true, allow_manual_entry: true,
  initial_balance: 0, balance_date: '',
  status: 'enabled', notes: '',
})

const filteredEntities = computed(() => {
  if (!filterDivision.value) return allEntities.value
  return allEntities.value.filter(e => e.division_id === filterDivision.value)
})

const getEntitiesForDivision = (divisionId) => {
  return allEntities.value.filter(e => e.division_id === divisionId)
}

const ungroupedEntities = computed(() => {
  return allEntities.value.filter(e => !e.division_id)
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
      entity_id: acc.entity_id, account_code: acc.account_code,
      bank_name: acc.bank_name || '', branch_name: acc.branch_name || '',
      account_number: acc.account_number || '', account_last_four: acc.account_last_four || '',
      account_type: acc.account_type || '', instrument_type: acc.instrument_type || '',
      has_online_banking: acc.has_online_banking || false,
      input_method: acc.input_method === 'bank_import' ? '网银导入' : '手工填写',
      currency: acc.currency, include_in_daily_report: acc.include_in_daily_report !== false,
      allow_manual_entry: acc.allow_manual_entry !== false,
      initial_balance: acc.initial_balance, balance_date: acc.balance_date,
      status: acc.status, notes: acc.notes || '',
    }
  } else {
    editing.value = null
    form.value = {
      entity_id: null, account_code: '', bank_name: '', branch_name: '',
      account_number: '', account_last_four: '', account_type: '', instrument_type: '',
      has_online_banking: false, input_method: '手工填写', currency: 'CNY',
      include_in_daily_report: true, allow_manual_entry: true,
      initial_balance: 0, balance_date: new Date().toISOString().slice(0, 10),
      status: 'enabled', notes: '',
    }
  }
  showForm.value = true
}

async function saveAccount() {
  try {
    const payload = {
      entity_id: form.value.entity_id, account_code: form.value.account_code,
      account_alias: form.value.account_type || form.value.account_code,
      bank_name: form.value.bank_name, branch_name: form.value.branch_name,
      account_number: form.value.account_number,
      account_last_four: form.value.account_last_four || (form.value.account_number ? form.value.account_number.slice(-4) : ''),
      account_type: form.value.account_type, instrument_type: form.value.instrument_type,
      has_online_banking: form.value.has_online_banking,
      input_method: form.value.input_method === '网银导入' ? 'bank_import' : 'manual',
      include_in_daily_report: form.value.include_in_daily_report,
      allow_manual_entry: form.value.allow_manual_entry,
      currency: form.value.currency, notes: form.value.notes,
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
  return fmtAmt(v)
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
    const d = await master.importAccounts(file)
    let msg = `导入完成！\n创建核算组织: ${d.created_divisions}\n创建单位: ${d.created_entities}\n创建账户: ${d.created_accounts}`
    if (d.error_count > 0) msg += `\n\n${d.error_count} 条错误：\n${d.errors.join('\n')}`
    alert(msg)
    await loadData()
  } catch (e) { alert('导入出错: ' + e.message) }
  e.target.value = ''
}

onMounted(loadData)
</script>

<style scoped>
@import './common.css';

/* 页面特有样式 — 仅保留 common.css 未覆盖的部分 */

/* 表格滚动区 */
.table-wrap {
  flex: 1;
  overflow: auto;
  max-height: calc(100vh - 260px);
}

/* 禁用行 */
tr.disabled { opacity: 0.55; }

/* 列宽控制 */
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

/* 等宽字体用于账号 */
.mono { font-family: monospace; font-size: 12px; }

/* 长文本省略 */
.ellipsis { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }

/* 操作列不换行 */
.action-cell { white-space: nowrap; }

/* 弹窗 */
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  overflow-y: auto;
}
.modal {
  background: #faf8f3;
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 90%;
  max-width: 640px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  position: relative;
  z-index: 1001;
}
.modal-lg { max-width: 780px; }
.modal h3 { margin: 0 0 16px 0; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }
.form-grid .form-input { max-width: none; }

/* 响应式 */
@media (max-width: 1000px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
