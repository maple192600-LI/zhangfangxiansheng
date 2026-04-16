<template>
  <div class="account-manage">
    <!-- 左侧树形导航 -->
    <aside class="tree-panel">
      <div class="tree-header">
        <h3>账户导航</h3>
        <div class="btn-row">
          <button class="btn btn-primary btn-sm" @click="openDivisionForm()">+ 板块</button>
          <button class="btn btn-secondary btn-sm" @click="openEntityForm()">+ 法人</button>
          <button class="btn btn-secondary btn-sm" @click="openAccountForm()">+ 账户</button>
        </div>
      </div>

      <div class="tree-body">
        <div v-for="div in divisions" :key="'d'+div.id" class="tree-group">
          <button
            class="tree-node root"
            :class="{ active: selectedType==='division' && selectedId===div.id }"
            @click="selectDivision(div)"
          >
            <span class="caret">{{ openDivisions[div.id] ? '▾' : '▸' }}</span>
            {{ div.name }}
            <span class="badge" :class="div.status">{{ div.status === 'enabled' ? '启用' : '停用' }}</span>
          </button>
          <div v-if="openDivisions[div.id]" class="tree-children">
            <div v-for="ent in getEntitiesForDivision(div.id)" :key="'e'+ent.id" class="tree-subgroup">
              <button
                class="tree-node branch"
                :class="{ active: selectedType==='entity' && selectedId===ent.id }"
                @click="selectEntity(ent)"
              >
                <span class="caret">{{ openEntities[ent.id] ? '▾' : '▸' }}</span>
                {{ ent.short_name }}
                <span class="badge" :class="ent.status">{{ ent.status === 'enabled' ? '启用' : '停用' }}</span>
              </button>
              <div v-if="openEntities[ent.id]" class="tree-children">
                <button
                  v-for="acc in getAccountsForEntity(ent.id)"
                  :key="'a'+acc.id"
                  class="tree-node leaf"
                  :class="{ active: selectedType==='account' && selectedId===acc.id }"
                  @click="selectAccount(acc)"
                >
                  {{ acc.account_alias }}
                  <span class="badge" :class="acc.status">{{ acc.status === 'enabled' ? '启用' : '停用' }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧详情面板 -->
    <main class="detail-panel">
      <!-- 板块详情 -->
      <div v-if="selectedType==='division'" class="section">
        <div class="section-title">
          <h3>{{ currentDivision?.name || '板块详情' }}</h3>
          <button class="btn btn-secondary btn-sm" @click="openDivisionForm(currentDivision)">编辑</button>
        </div>
        <div class="detail-grid" v-if="currentDivision">
          <div class="field"><span class="label">板块名称</span><span>{{ currentDivision.name }}</span></div>
          <div class="field"><span class="label">排序</span><span>{{ currentDivision.sort_order }}</span></div>
          <div class="field"><span class="label">状态</span><span class="badge" :class="currentDivision.status">{{ currentDivision.status === 'enabled' ? '启用' : '停用' }}</span></div>
          <div class="field"><span class="label">创建时间</span><span>{{ formatDate(currentDivision.created_at) }}</span></div>
        </div>
      </div>

      <!-- 法人详情 -->
      <div v-if="selectedType==='entity'" class="section">
        <div class="section-title">
          <h3>{{ currentEntity?.name || '法人详情' }}</h3>
          <button class="btn btn-secondary btn-sm" @click="openEntityForm(currentEntity)">编辑</button>
        </div>
        <div class="detail-grid" v-if="currentEntity">
          <div class="field"><span class="label">法人编码</span><span>{{ currentEntity.entity_code }}</span></div>
          <div class="field"><span class="label">法人名称</span><span>{{ currentEntity.name }}</span></div>
          <div class="field"><span class="label">简称</span><span>{{ currentEntity.short_name }}</span></div>
          <div class="field"><span class="label">所属板块</span><span>{{ getDivisionName(currentEntity.division_id) }}</span></div>
          <div class="field"><span class="label">状态</span><span class="badge" :class="currentEntity.status">{{ currentEntity.status === 'enabled' ? '启用' : '停用' }}</span></div>
          <div class="field"><span class="label">创建时间</span><span>{{ formatDate(currentEntity.created_at) }}</span></div>
        </div>
      </div>

      <!-- 账户详情 -->
      <div v-if="selectedType==='account'" class="section">
        <div class="section-title">
          <h3>{{ currentAccount?.account_alias || '账户详情' }}</h3>
          <button class="btn btn-secondary btn-sm" @click="openAccountForm(currentAccount)">编辑</button>
        </div>
        <div class="detail-grid" v-if="currentAccount">
          <div class="field"><span class="label">账户编码</span><span>{{ currentAccount.account_code }}</span></div>
          <div class="field"><span class="label">账户别名</span><span>{{ currentAccount.account_alias }}</span></div>
          <div class="field"><span class="label">所属法人</span><span>{{ currentAccount.entity_name || '-' }}</span></div>
          <div class="field"><span class="label">开户银行</span><span>{{ currentAccount.bank_name || '-' }}</span></div>
          <div class="field"><span class="label">开户行</span><span>{{ currentAccount.branch_name || '-' }}</span></div>
          <div class="field"><span class="label">账号</span><span>{{ currentAccount.account_number || '-' }}</span></div>
          <div class="field"><span class="label">账户类型</span><span>{{ currentAccount.account_type }}</span></div>
          <div class="field"><span class="label">工具类型</span><span>{{ currentAccount.instrument_type }}</span></div>
          <div class="field"><span class="label">录入方式</span><span>{{ currentAccount.input_method }}</span></div>
          <div class="field"><span class="label">币种</span><span>{{ currentAccount.currency }}</span></div>
          <div class="field"><span class="label">期初余额</span><span class="money">{{ formatMoney(currentAccount.initial_balance) }}</span></div>
          <div class="field"><span class="label">余额日期</span><span>{{ currentAccount.balance_date }}</span></div>
          <div class="field"><span class="label">状态</span><span class="badge" :class="currentAccount.status">{{ currentAccount.status === 'enabled' ? '启用' : '停用' }}</span></div>
          <div class="field"><span class="label">备注</span><span>{{ currentAccount.notes || '-' }}</span></div>
        </div>

        <!-- 期初余额 -->
        <div class="section" style="margin-top:14px">
          <div class="section-title">
            <h3>期初余额</h3>
            <button class="btn btn-primary btn-sm" @click="showBalanceModal=true" v-if="currentAccount">修改</button>
          </div>
          <p style="color:var(--muted);font-size:13px">仅当账户无资金流水时可修改期初余额。</p>
        </div>

        <!-- 别名管理 -->
        <div class="section" style="margin-top:14px">
          <div class="section-title">
            <h3>别名管理</h3>
            <button class="btn btn-primary btn-sm" @click="showAliasForm=true" v-if="currentAccount">+ 添加</button>
          </div>
          <table class="data-table" v-if="aliases.length">
            <thead>
              <tr><th>别名</th><th>类型</th><th>操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="a in aliases" :key="a.id">
                <td>{{ a.alias_text }}</td>
                <td>{{ a.alias_type }}</td>
                <td><button class="btn btn-secondary btn-sm" @click="handleDeleteAlias(a.id)">删除</button></td>
              </tr>
            </tbody>
          </table>
          <p v-else style="color:var(--muted);font-size:13px">暂无别名</p>
        </div>
      </div>

      <!-- 默认空状态 -->
      <div v-if="!selectedType" class="section">
        <div class="placeholder">请在左侧导航中选择板块、法人或账户查看详情</div>
      </div>
    </main>

    <!-- ── 板块表单弹窗 ── -->
    <div class="modal-mask" v-if="showDivisionForm" @click.self="showDivisionForm=false">
      <div class="modal">
        <h3>{{ editingDivision ? '编辑板块' : '新建板块' }}</h3>
        <div class="form-group">
          <label>板块名称</label>
          <input v-model="divisionForm.name" class="filter" placeholder="输入板块名称" />
        </div>
        <div class="form-group">
          <label>排序</label>
          <input v-model.number="divisionForm.sort_order" type="number" class="filter" />
        </div>
        <div class="form-group" v-if="editingDivision">
          <label>状态</label>
          <select v-model="divisionForm.status" class="filter">
            <option value="enabled">启用</option>
            <option value="disabled">停用</option>
          </select>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showDivisionForm=false">取消</button>
          <button class="btn btn-primary" @click="saveDivision">保存</button>
        </div>
      </div>
    </div>

    <!-- ── 法人表单弹窗 ── -->
    <div class="modal-mask" v-if="showEntityForm" @click.self="showEntityForm=false">
      <div class="modal">
        <h3>{{ editingEntity ? '编辑法人' : '新建法人' }}</h3>
        <div class="form-group">
          <label>所属板块</label>
          <select v-model="entityForm.division_id" class="filter">
            <option :value="null">无</option>
            <option v-for="d in divisions" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>法人编码</label>
          <input v-model="entityForm.entity_code" class="filter" placeholder="如 E006" :disabled="!!editingEntity" />
        </div>
        <div class="form-group">
          <label>法人名称</label>
          <input v-model="entityForm.name" class="filter" placeholder="全称" />
        </div>
        <div class="form-group">
          <label>简称</label>
          <input v-model="entityForm.short_name" class="filter" placeholder="简称" />
        </div>
        <div class="form-group" v-if="editingEntity">
          <label>状态</label>
          <select v-model="entityForm.status" class="filter">
            <option value="enabled">启用</option>
            <option value="disabled">停用</option>
          </select>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showEntityForm=false">取消</button>
          <button class="btn btn-primary" @click="saveEntity">保存</button>
        </div>
      </div>
    </div>

    <!-- ── 账户表单弹窗 ── -->
    <div class="modal-mask" v-if="showAccountForm" @click.self="showAccountForm=false">
      <div class="modal" style="max-width:640px">
        <h3>{{ editingAccount ? '编辑账户' : '新建账户' }}</h3>
        <div class="form-grid">
          <div class="form-group">
            <label>所属法人</label>
            <select v-model="accountForm.entity_id" class="filter">
              <option v-for="e in allEntities" :key="e.id" :value="e.id">{{ e.short_name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>账户编码</label>
            <input v-model="accountForm.account_code" class="filter" placeholder="如 A007" :disabled="!!editingAccount" />
          </div>
          <div class="form-group">
            <label>账户别名</label>
            <input v-model="accountForm.account_alias" class="filter" />
          </div>
          <div class="form-group">
            <label>开户银行</label>
            <input v-model="accountForm.bank_name" class="filter" />
          </div>
          <div class="form-group">
            <label>开户行</label>
            <input v-model="accountForm.branch_name" class="filter" />
          </div>
          <div class="form-group">
            <label>账号</label>
            <input v-model="accountForm.account_number" class="filter" />
          </div>
          <div class="form-group">
            <label>账户类型</label>
            <input v-model="accountForm.account_type" class="filter" placeholder="如 银行账户" />
          </div>
          <div class="form-group">
            <label>工具类型</label>
            <input v-model="accountForm.instrument_type" class="filter" placeholder="如 银行存款" />
          </div>
          <div class="form-group">
            <label>录入方式</label>
            <select v-model="accountForm.input_method" class="filter">
              <option value="manual">手工录入</option>
              <option value="bank_import">银行导入</option>
            </select>
          </div>
          <div class="form-group">
            <label>币种</label>
            <input v-model="accountForm.currency" class="filter" />
          </div>
          <div class="form-group" v-if="!editingAccount">
            <label>期初余额</label>
            <input v-model.number="accountForm.initial_balance" type="number" step="0.01" class="filter" />
          </div>
          <div class="form-group" v-if="!editingAccount">
            <label>余额日期</label>
            <input v-model="accountForm.balance_date" type="date" class="filter" />
          </div>
          <div class="form-group" v-if="editingAccount">
            <label>状态</label>
            <select v-model="accountForm.status" class="filter">
              <option value="enabled">启用</option>
              <option value="disabled">停用</option>
            </select>
          </div>
          <div class="form-group" style="grid-column:span 2">
            <label>备注</label>
            <input v-model="accountForm.notes" class="filter" />
          </div>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showAccountForm=false">取消</button>
          <button class="btn btn-primary" @click="saveAccount">保存</button>
        </div>
      </div>
    </div>

    <!-- ── 期初余额弹窗 ── -->
    <div class="modal-mask" v-if="showBalanceModal" @click.self="showBalanceModal=false">
      <div class="modal" style="max-width:400px">
        <h3>修改期初余额</h3>
        <div class="form-group">
          <label>期初余额</label>
          <input v-model.number="balanceForm.initial_balance" type="number" step="0.01" class="filter" />
        </div>
        <div class="form-group">
          <label>余额日期</label>
          <input v-model="balanceForm.balance_date" type="date" class="filter" />
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showBalanceModal=false">取消</button>
          <button class="btn btn-primary" @click="saveBalance">保存</button>
        </div>
      </div>
    </div>

    <!-- ── 添加别名弹窗 ── -->
    <div class="modal-mask" v-if="showAliasForm" @click.self="showAliasForm=false">
      <div class="modal" style="max-width:400px">
        <h3>添加别名</h3>
        <div class="form-group">
          <label>别名文本</label>
          <input v-model="aliasForm.alias_text" class="filter" placeholder="如 中行户" />
        </div>
        <div class="form-group">
          <label>别名类型</label>
          <select v-model="aliasForm.alias_type" class="filter">
            <option value="short_name">简称</option>
            <option value="bank_alias">银行别名</option>
            <option value="custom">自定义</option>
          </select>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showAliasForm=false">取消</button>
          <button class="btn btn-primary" @click="saveAlias">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import * as api from '@/api/master'

// ── 数据 ──
const divisions = ref([])
const allEntities = ref([])
const treeData = ref([])
const aliases = ref([])

const selectedType = ref(null)
const selectedId = ref(null)
const currentDivision = ref(null)
const currentEntity = ref(null)
const currentAccount = ref(null)

const openDivisions = reactive({})
const openEntities = reactive({})

// ── 表单状态 ──
const showDivisionForm = ref(false)
const showEntityForm = ref(false)
const showAccountForm = ref(false)
const showBalanceModal = ref(false)
const showAliasForm = ref(false)

const editingDivision = ref(null)
const editingEntity = ref(null)
const editingAccount = ref(null)

const divisionForm = reactive({ name: '', sort_order: 0, status: 'enabled' })
const entityForm = reactive({ division_id: null, entity_code: '', name: '', short_name: '', status: 'enabled' })
const accountForm = reactive({
  entity_id: null, account_code: '', account_alias: '', bank_name: '', branch_name: '',
  account_number: '', account_type: '银行账户', instrument_type: '银行存款',
  input_method: 'manual', currency: 'CNY', initial_balance: 0, balance_date: '', status: 'enabled', notes: ''
})
const balanceForm = reactive({ initial_balance: 0, balance_date: '' })
const aliasForm = reactive({ alias_text: '', alias_type: 'short_name' })

// ── 加载数据 ──
async function loadData() {
  try {
    const [divs, ents, tree] = await Promise.all([
      api.getDivisions(),
      api.getEntities({ page: 1, page_size: 200 }),
      api.getAccountsTree()
    ])
    divisions.value = divs || []
    allEntities.value = ents?.items || []
    treeData.value = tree || []
  } catch (e) {
    console.error('加载数据失败', e)
  }
}

// ── 树形查询 ──
function getEntitiesForDivision(divisionId) {
  return allEntities.value.filter(e => e.division_id === divisionId)
}

function getAccountsForEntity(entityId) {
  const group = treeData.value.find(g => g.entity_id === entityId)
  return group ? group.accounts : []
}

function getDivisionName(divisionId) {
  const d = divisions.value.find(d => d.id === divisionId)
  return d ? d.name : '-'
}

// ── 选择节点 ──
function selectDivision(div) {
  openDivisions[div.id] = !openDivisions[div.id]
  selectedType.value = 'division'
  selectedId.value = div.id
  currentDivision.value = div
  currentEntity.value = null
  currentAccount.value = null
  aliases.value = []
}

function selectEntity(ent) {
  openEntities[ent.id] = !openEntities[ent.id]
  selectedType.value = 'entity'
  selectedId.value = ent.id
  currentEntity.value = ent
  currentDivision.value = null
  currentAccount.value = null
  aliases.value = []
}

async function selectAccount(acc) {
  selectedType.value = 'account'
  selectedId.value = acc.id
  currentAccount.value = null
  currentEntity.value = null
  currentDivision.value = null
  try {
    const detail = await api.getAccounts({ entity_id: acc.entity_id, page_size: 200 })
    const found = (detail?.items || []).find(a => a.id === acc.id)
    if (found) currentAccount.value = found
    const al = await api.getAliases(acc.id)
    aliases.value = al || []
  } catch (e) {
    console.error('加载账户详情失败', e)
  }
}

// ── 板块 CRUD ──
function openDivisionForm(div) {
  editingDivision.value = div || null
  if (div) {
    divisionForm.name = div.name
    divisionForm.sort_order = div.sort_order
    divisionForm.status = div.status
  } else {
    divisionForm.name = ''
    divisionForm.sort_order = 0
    divisionForm.status = 'enabled'
  }
  showDivisionForm.value = true
}

async function saveDivision() {
  try {
    if (editingDivision.value) {
      await api.updateDivision(editingDivision.value.id, {
        name: divisionForm.name,
        sort_order: divisionForm.sort_order,
        status: divisionForm.status
      })
    } else {
      await api.createDivision({
        name: divisionForm.name,
        sort_order: divisionForm.sort_order
      })
    }
    showDivisionForm.value = false
    await loadData()
  } catch (e) {
    alert(e.message || '保存失败')
  }
}

// ── 法人 CRUD ──
function openEntityForm(ent) {
  editingEntity.value = ent || null
  if (ent) {
    entityForm.division_id = ent.division_id
    entityForm.entity_code = ent.entity_code
    entityForm.name = ent.name
    entityForm.short_name = ent.short_name
    entityForm.status = ent.status
  } else {
    entityForm.division_id = null
    entityForm.entity_code = ''
    entityForm.name = ''
    entityForm.short_name = ''
    entityForm.status = 'enabled'
  }
  showEntityForm.value = true
}

async function saveEntity() {
  try {
    const payload = {
      division_id: entityForm.division_id,
      entity_code: entityForm.entity_code,
      name: entityForm.name,
      short_name: entityForm.short_name,
    }
    if (editingEntity.value) {
      payload.status = entityForm.status
      await api.updateEntity(editingEntity.value.id, payload)
    } else {
      await api.createEntity(payload)
    }
    showEntityForm.value = false
    await loadData()
  } catch (e) {
    alert(e.message || '保存失败')
  }
}

// ── 账户 CRUD ──
function openAccountForm(acc) {
  editingAccount.value = acc || null
  if (acc) {
    accountForm.entity_id = acc.entity_id
    accountForm.account_code = acc.account_code
    accountForm.account_alias = acc.account_alias
    accountForm.bank_name = acc.bank_name || ''
    accountForm.branch_name = acc.branch_name || ''
    accountForm.account_number = acc.account_number || ''
    accountForm.account_type = acc.account_type
    accountForm.instrument_type = acc.instrument_type
    accountForm.input_method = acc.input_method
    accountForm.currency = acc.currency
    accountForm.status = acc.status
    accountForm.notes = acc.notes || ''
  } else {
    accountForm.entity_id = null
    accountForm.account_code = ''
    accountForm.account_alias = ''
    accountForm.bank_name = ''
    accountForm.branch_name = ''
    accountForm.account_number = ''
    accountForm.account_type = '银行账户'
    accountForm.instrument_type = '银行存款'
    accountForm.input_method = 'manual'
    accountForm.currency = 'CNY'
    accountForm.initial_balance = 0
    accountForm.balance_date = new Date().toISOString().slice(0, 10)
    accountForm.status = 'enabled'
    accountForm.notes = ''
  }
  showAccountForm.value = true
}

async function saveAccount() {
  try {
    const payload = {
      entity_id: accountForm.entity_id,
      account_code: accountForm.account_code,
      account_alias: accountForm.account_alias,
      bank_name: accountForm.bank_name,
      branch_name: accountForm.branch_name,
      account_number: accountForm.account_number,
      account_type: accountForm.account_type,
      instrument_type: accountForm.instrument_type,
      input_method: accountForm.input_method,
      currency: accountForm.currency,
      notes: accountForm.notes,
    }
    if (editingAccount.value) {
      payload.status = accountForm.status
      await api.updateAccount(editingAccount.value.id, payload)
    } else {
      payload.initial_balance = accountForm.initial_balance
      payload.balance_date = accountForm.balance_date
      await api.createAccount(payload)
    }
    showAccountForm.value = false
    await loadData()
    if (editingAccount.value && selectedType.value === 'account') {
      await selectAccount({ id: editingAccount.value.id, entity_id: editingAccount.value.entity_id })
    }
  } catch (e) {
    alert(e.message || '保存失败')
  }
}

// ── 期初余额 ──
async function saveBalance() {
  if (!currentAccount.value) return
  try {
    await api.setInitialBalance(currentAccount.value.id, {
      initial_balance: balanceForm.initial_balance,
      balance_date: balanceForm.balance_date,
    })
    showBalanceModal.value = false
    await selectAccount({ id: currentAccount.value.id, entity_id: currentAccount.value.entity_id })
  } catch (e) {
    alert(e.message || '保存失败')
  }
}

// ── 别名 ──
async function saveAlias() {
  if (!currentAccount.value) return
  try {
    await api.createAlias(currentAccount.value.id, {
      alias_text: aliasForm.alias_text,
      alias_type: aliasForm.alias_type,
    })
    showAliasForm.value = false
    aliasForm.alias_text = ''
    aliasForm.alias_type = 'short_name'
    const al = await api.getAliases(currentAccount.value.id)
    aliases.value = al || []
  } catch (e) {
    alert(e.message || '保存失败')
  }
}

async function handleDeleteAlias(aliasId) {
  if (!currentAccount.value || !confirm('确认删除此别名？')) return
  try {
    await api.deleteAlias(currentAccount.value.id, aliasId)
    const al = await api.getAliases(currentAccount.value.id)
    aliases.value = al || []
  } catch (e) {
    alert(e.message || '删除失败')
  }
}

// ── 工具函数 ──
function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}

function formatMoney(v) {
  if (v == null) return '-'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ── 初始化 ──
onMounted(loadData)
</script>

<style scoped>
.account-manage {
  display: flex;
  gap: 16px;
  height: calc(100vh - 80px);
}

/* 左侧树 */
.tree-panel {
  width: 300px;
  min-width: 260px;
  background: rgba(251,250,247,0.95);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.tree-header {
  padding: 14px;
  border-bottom: 1px solid var(--line);
}
.tree-header h3 { margin: 0 0 10px 0; font-size: 16px; }
.tree-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.tree-group { margin-bottom: 2px; }
.tree-subgroup { margin-left: 16px; }
.tree-children { margin-left: 20px; }

.tree-node {
  display: flex;
  align-items: center;
  width: 100%;
  background: none;
  border: none;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  color: #435046;
  text-align: left;
  gap: 6px;
}
.tree-node:hover { background: #f0ede6; }
.tree-node.active { background: #e2ded4; font-weight: 600; }
.tree-node.root { font-weight: 600; font-size: 15px; }
.tree-node.leaf { font-size: 13px; padding-left: 14px; }
.caret { font-size: 12px; color: #9a958b; min-width: 14px; }

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 11px;
  margin-left: auto;
}
.badge.enabled { background: #edf4ea; color: #3f5b3d; }
.badge.disabled { background: #f5ece5; color: #8a6e52; }

/* 右侧详情 */
.detail-panel {
  flex: 1;
  overflow-y: auto;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.field {
  background: #fff;
  border: 1px solid #e7e0d5;
  border-radius: 12px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field .label { color: var(--muted); font-size: 12px; }
.field .money { font-weight: 700; font-size: 18px; color: #3f5b3d; }

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  font-weight: 500;
}
.data-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #f0ede6;
}

/* 弹窗 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #faf8f3;
  border-radius: 16px;
  padding: 24px;
  width: 90%;
  max-width: 520px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal h3 { margin: 0 0 16px 0; font-size: 18px; }

.form-group {
  margin-bottom: 12px;
}
.form-group label {
  display: block;
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 4px;
}
.form-group .filter {
  width: 100%;
  box-sizing: border-box;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.btn-sm {
  padding: 6px 10px;
  font-size: 13px;
}

@media (max-width: 900px) {
  .account-manage { flex-direction: column; height: auto; }
  .tree-panel { width: 100%; min-width: auto; max-height: 300px; }
  .detail-grid { grid-template-columns: 1fr; }
  .form-grid { grid-template-columns: 1fr; }
}
</style>
