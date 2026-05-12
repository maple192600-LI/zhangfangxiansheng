<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>银行维护</h3>
        <span>管理所有银行的基础信息</span>
      </div>
      <div class="filters-bar">
        <input v-model="keyword" class="filter" placeholder="搜索银行编码/名称/联行号" style="width:220px" />
        <NSelect filterable v-model:value="filterStatus" :options="statusFilterOptions" placeholder="全部状态" clearable style="width:110px" />
        <div style="flex:1"></div>
        <NButton type="primary" @click="openForm()">+ 新建银行</NButton>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-id">ID</th>
              <th class="col-code">银行编码</th>
              <th class="col-name">银行名称</th>
              <th class="col-short">简称</th>
              <th class="col-cnaps">联行号</th>
              <th class="col-phone">客服电话</th>
              <th class="col-status">状态</th>
              <th class="col-action">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in filteredList" :key="b.id"
                :class="{ disabled: b.status === 'disabled' }"
                @dblclick="openForm(b)">
              <td>{{ b.id }}</td>
              <td><strong>{{ b.bank_code }}</strong></td>
              <td>{{ b.bank_name || '-' }}</td>
              <td>{{ b.short_name || '-' }}</td>
              <td class="mono">{{ b.cnaps_code || '-' }}</td>
              <td>{{ b.contact_phone || '-' }}</td>
              <td><span class="tag" :class="b.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ b.status === 'enabled' ? '启用' : '停用' }}</span></td>
              <td class="action-cell">
                <NButton secondary size="small" @click="openForm(b)">编辑</NButton>
                <NButton secondary size="small" v-if="b.status==='enabled'" @click="toggleStatus(b, 'disabled')">停用</NButton>
                <NButton secondary size="small" v-else @click="toggleStatus(b, 'enabled')">启用</NButton>
                <NButton type="warning" size="small" @click="handleDelete(b)">删除</NButton>
              </td>
            </tr>
            <tr v-if="!filteredList.length">
              <td colspan="8" style="text-align:center;color:var(--muted);padding:30px">暂无银行数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="bottom-bar" v-if="filteredList.length">
      <span class="count-info">共 {{ filteredList.length }} 条记录</span>
    </div>

    <!-- 弹窗 -->
    <div class="modal-mask" v-if="showForm" @click.self="showForm=false">
      <div class="modal modal-lg">
        <h3>{{ editing ? '编辑银行' : '新建银行' }}</h3>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">银行编码 *</label>
            <input v-model="form.bank_code" class="form-input" placeholder="如 BOC" :disabled="!!editing" />
          </div>
          <div class="form-group">
            <label class="form-label">银行名称 *</label>
            <input v-model="form.bank_name" class="form-input" placeholder="如 中国银行" />
          </div>
          <div class="form-group">
            <label class="form-label">简称</label>
            <input v-model="form.short_name" class="form-input" placeholder="如 中行" />
          </div>
          <div class="form-group">
            <label class="form-label">联行号</label>
            <input v-model="form.cnaps_code" class="form-input" placeholder="12位联行号" />
          </div>
          <div class="form-group">
            <label class="form-label">客服电话</label>
            <input v-model="form.contact_phone" class="form-input" placeholder="如 95566" />
          </div>
          <div class="form-group">
            <label class="form-label">网站</label>
            <input v-model="form.website" class="form-input" placeholder="https://..." />
          </div>
          <div class="form-group">
            <label class="form-label">排序</label>
            <input v-model.number="form.sort_order" type="number" class="form-input" placeholder="数值越小越靠前" />
          </div>
          <div class="form-group" v-if="editing">
            <label class="form-label">状态</label>
            <NSelect filterable v-model:value="form.status" :options="statusOptions" class="form-input" />
          </div>
          <div class="form-group" style="grid-column:span 2">
            <label class="form-label">备注</label>
            <input v-model="form.notes" class="form-input" placeholder="补充说明" />
          </div>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <NButton secondary @click="showForm=false">取消</NButton>
          <NButton type="primary" @click="save">保存</NButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NSelect, NButton } from 'naive-ui'
import * as api from '@/api/master'

const list = ref([])
const filterStatus = ref(null)
const statusFilterOptions = [
  { label: '启用', value: 'enabled' },
  { label: '停用', value: 'disabled' },
]
const statusOptions = [
  { label: '启用', value: 'enabled' },
  { label: '停用', value: 'disabled' },
]
const keyword = ref('')
const showForm = ref(false)
const editing = ref(null)
const form = ref({
  bank_code: '',
  bank_name: '',
  short_name: '',
  cnaps_code: '',
  contact_phone: '',
  website: '',
  sort_order: 0,
  notes: '',
  status: 'enabled',
})

const filteredList = computed(() => {
  let items = list.value
  if (filterStatus.value) items = items.filter(b => b.status === filterStatus.value)
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    items = items.filter(b =>
      (b.bank_code || '').toLowerCase().includes(kw) ||
      (b.bank_name || '').toLowerCase().includes(kw) ||
      (b.cnaps_code || '').toLowerCase().includes(kw)
    )
  }
  return items
})

async function loadData() {
  try {
    const res = await api.getBanks({ page: 1, page_size: 500 })
    list.value = Array.isArray(res) ? res : (res?.items || [])
  } catch (e) {
    console.error(e)
  }
}

function openForm(item) {
  if (item) {
    editing.value = item
    form.value = {
      bank_code: item.bank_code || '',
      bank_name: item.bank_name || '',
      short_name: item.short_name || '',
      cnaps_code: item.cnaps_code || '',
      contact_phone: item.contact_phone || '',
      website: item.website || '',
      sort_order: item.sort_order ?? 0,
      notes: item.notes || '',
      status: item.status || 'enabled',
    }
  } else {
    editing.value = null
    form.value = {
      bank_code: '',
      bank_name: '',
      short_name: '',
      cnaps_code: '',
      contact_phone: '',
      website: '',
      sort_order: 0,
      notes: '',
      status: 'enabled',
    }
  }
  showForm.value = true
}

async function save() {
  if (!form.value.bank_code.trim()) {
    alert('请填写银行编码')
    return
  }
  if (!form.value.bank_name.trim()) {
    alert('请填写银行名称')
    return
  }
  try {
    const payload = {
      bank_code: form.value.bank_code.trim(),
      bank_name: form.value.bank_name.trim(),
      short_name: form.value.short_name.trim(),
      cnaps_code: form.value.cnaps_code.trim(),
      contact_phone: form.value.contact_phone.trim(),
      website: form.value.website.trim(),
      sort_order: form.value.sort_order || 0,
      notes: form.value.notes.trim(),
    }
    if (editing.value) {
      payload.status = form.value.status
      await api.updateBank(editing.value.id, payload)
    } else {
      await api.createBank(payload)
    }
    showForm.value = false
    await loadData()
  } catch (e) {
    alert(e.message || '保存失败')
  }
}

async function toggleStatus(item, status) {
  try {
    await api.updateBankStatus(item.id, status)
    await loadData()
  } catch (e) {
    alert(e.message || '操作失败')
  }
}

async function handleDelete(item) {
  const msg = item.status === 'enabled'
    ? `银行「${item.bank_name}」当前为启用状态，删除后关联的账户数据将受影响。确定删除？`
    : `确定删除银行「${item.bank_name}」？删除后不可恢复。`
  if (!confirm(msg)) return
  try {
    await api.deleteBank(item.id)
    await loadData()
  } catch (e) {
    alert(e.message || '删除失败，可能存在引用关联')
  }
}

onMounted(loadData)
</script>

<style scoped>
@import './common.css';

.table-wrap {
  flex: 1;
  overflow: auto;
  max-height: calc(100vh - 260px);
}

tr.disabled { opacity: 0.55; }

.col-id { width: 50px; }
.col-code { width: 90px; }
.col-name { min-width: 140px; }
.col-short { width: 80px; }
.col-cnaps { width: 130px; }
.col-phone { width: 100px; }
.col-status { width: 70px; }
.col-action { width: 180px; }

.mono { font-family: monospace; font-size: 12px; }
.action-cell { white-space: nowrap; }

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
}
.modal-lg { max-width: 780px; }
.modal h3 { margin: 0 0 16px 0; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }
.form-grid .form-input { max-width: none; }

@media (max-width: 1000px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
