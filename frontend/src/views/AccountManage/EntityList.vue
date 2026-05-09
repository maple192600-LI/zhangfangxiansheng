<template>
  <div>
    <div class="filters-bar">
      <select v-model="filterDiv" class="filter">
        <option :value="null">全部核算组织</option>
        <option v-for="d in divisions" :key="d.id" :value="d.id">{{ d.name }}</option>
      </select>
      <input v-model="entKeyword" class="filter" placeholder="搜索单位编码/名称" style="width:200px" />
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
          </div>
        </div>
        <button class="btn btn-primary" @click="openForm()">+ 新建单位</button>
      </div>
    </div>

    <div v-if="!filteredEntities.length" class="empty-state">
      <div class="empty-icon">&#x1F3E2;</div>
      <h4>暂无单位</h4>
      <p>点击右上角「+ 新建单位」添加，或通过账户列表批量导入</p>
    </div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="col-ck"><input type="checkbox" :checked="isAllSelected" @change="toggleAll" /></th>
            <th style="width:50px">ID</th>
            <th style="min-width:120px">所属核算组织</th>
            <th style="width:90px">单位编码</th>
            <th style="min-width:160px">单位全称</th>
            <th style="width:100px">单位简称</th>
            <th style="width:70px">状态</th>
            <th style="width:150px">创建时间</th>
            <th style="width:180px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in filteredEntities" :key="e.id"
              :class="{ disabled: e.status === 'disabled', selected: selectedIds.includes(e.id) }" @dblclick="openForm(e)">
            <td class="col-ck"><input type="checkbox" :value="e.id" v-model="selectedIds" /></td>
            <td>{{ e.id }}</td>
            <td>{{ e.division_name || '-' }}</td>
            <td><strong>{{ e.entity_code }}</strong></td>
            <td>{{ e.name || '-' }}</td>
            <td>{{ e.short_name || '-' }}</td>
            <td><span class="tag" :class="e.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ e.status === 'enabled' ? '启用' : '停用' }}</span></td>
            <td>{{ e.created_at ? e.created_at.slice(0, 19).replace('T', ' ') : '-' }}</td>
            <td class="action-cell">
              <button class="btn btn-secondary btn-sm" @click="openForm(e)">编辑</button>
              <button class="btn btn-secondary btn-sm" v-if="e.status==='enabled'" @click="toggleStatus(e,'disabled')">停用</button>
              <button class="btn btn-secondary btn-sm" v-else @click="toggleStatus(e,'enabled')">启用</button>
              <button class="btn btn-warn btn-sm" @click="deleteEnt(e)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 单位表单弹窗 -->
    <div class="modal-mask" v-if="showForm" @click.self="showForm=false">
      <div class="modal modal-lg">
        <h3>{{ editing ? '编辑单位' : '新建单位' }}</h3>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">所属核算组织 *</label>
            <select v-model="form.division_id" class="form-input">
              <option :value="null" disabled>-- 请选择核算组织 --</option>
              <option v-for="d in divisions" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">单位编码</label>
            <input v-if="editing" :value="editing.entity_code" class="form-input" disabled />
            <input v-else v-model="form.entity_code" class="form-input" placeholder="留空自动生成" />
          </div>
          <div class="form-group">
            <label class="form-label">单位全称 *</label>
            <input v-model="form.name" class="form-input" placeholder="单位全称" />
          </div>
          <div class="form-group">
            <label class="form-label">单位简称 *</label>
            <input v-model="form.short_name" class="form-input" placeholder="单位简称" />
          </div>
          <div class="form-group" v-if="editing">
            <label class="form-label">状态</label>
            <select v-model="form.status" class="form-input">
              <option value="enabled">启用</option>
              <option value="disabled">停用</option>
            </select>
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

const props = defineProps({
  divisions: { type: Array, default: () => [] },
  allEntities: { type: Array, default: () => [] },
})
const emit = defineEmits(['refresh'])

const selectedIds = ref([])
const dropdownOpen = ref(false)
const filterDiv = ref(null)
const filterStatus = ref('')
const entKeyword = ref('')
const showForm = ref(false)
const editing = ref(null)
const form = ref({ division_id: null, entity_code: '', name: '', short_name: '', status: 'enabled' })

const filteredEntities = computed(() => {
  let items = props.allEntities
  if (filterDiv.value) items = items.filter(e => e.division_id === filterDiv.value)
  if (filterStatus.value) items = items.filter(e => e.status === filterStatus.value)
  if (entKeyword.value) {
    const kw = entKeyword.value.toLowerCase()
    items = items.filter(e =>
      (e.entity_code || '').toLowerCase().includes(kw) ||
      (e.name || '').toLowerCase().includes(kw) ||
      (e.short_name || '').toLowerCase().includes(kw)
    )
  }
  return items
})

const isAllSelected = computed(() => {
  const list = filteredEntities.value
  return list.length > 0 && list.every(e => selectedIds.value.includes(e.id))
})

function toggleAll() {
  selectedIds.value = isAllSelected.value ? [] : filteredEntities.value.map(e => e.id)
}

function openForm(item) {
  if (item) {
    editing.value = item
    form.value = {
      division_id: item.division_id || null,
      entity_code: item.entity_code || '',
      name: item.name || item.full_name || '',
      short_name: item.short_name || '',
      status: item.status || 'enabled',
    }
  } else {
    editing.value = null
    form.value = { division_id: null, entity_code: '', name: '', short_name: '', status: 'enabled' }
  }
  showForm.value = true
}

async function save() {
  if (!form.value.name.trim()) { alert('请填写单位全称'); return }
  if (!form.value.short_name.trim()) { alert('请填写单位简称'); return }
  try {
    const payload = {
      division_id: form.value.division_id,
      entity_code: form.value.entity_code.trim() || null,
      name: form.value.name.trim(),
      short_name: form.value.short_name.trim(),
    }
    if (editing.value) {
      payload.status = form.value.status
      await api.updateEntity(editing.value.id, payload)
    } else {
      await api.createEntity(payload)
    }
    showForm.value = false
    emit('refresh')
  } catch (e) { alert(e.message || '保存失败') }
}

async function toggleStatus(item, status) {
  try {
    await api.updateEntityStatus(item.id, status)
    emit('refresh')
  } catch (e) { alert(e.message) }
}

async function deleteEnt(item) {
  try {
    const usage = await api.getEntityUsage(item.id)
    const accountCount = usage.account_count || 0
    if (accountCount > 0) {
      const accNames = (usage.accounts || []).map(a => `${a.account_code} ${a.account_alias}（${a.account_type}）`).join('、')
      alert(`单位「${item.short_name || item.name}」下有 ${accountCount} 个银行账户（${accNames}），请先到「账户管理」中删除所有账户后再删除单位。`)
      return
    }
    if (!confirm(`确定删除单位「${item.short_name || item.name}」？此操作不可撤销。`)) return
    await api.deleteEntity(item.id)
    emit('refresh')
  } catch (e) { alert(e.message || '删除失败') }
}

async function batchAction(action) {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  const labels = { enable: '启用', disable: '停用' }
  if (!confirm(`确定批量${labels[action] || action} ${ids.length} 个单位？`)) return
  try {
    const result = await api.batchActionEntities(ids, action)
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
tr.disabled { opacity: 0.55; }
tr.selected { background: #f0f5ef; }
.col-ck { width: 36px; text-align: center; }
.col-ck input[type="checkbox"] { cursor: pointer; }
.action-cell { white-space: nowrap; }
.empty-state { text-align: center; padding: 60px 20px; color: var(--muted); }
.empty-state .empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state h4 { margin: 0 0 8px 0; color: var(--text); font-size: 16px; }
.empty-state p { margin: 0; font-size: 13px; }
.dropdown { position: relative; display: inline-block; }
.dropdown-menu { display: none; position: absolute; right: 0; top: 100%; background: white; border: 1px solid #ddd; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 100; min-width: 120px; }
.dropdown-menu button { display: block; width: 100%; padding: 8px 16px; border: none; background: none; text-align: left; cursor: pointer; font-size: 13px; }
.dropdown-menu button:hover { background: #f5f5f5; }
.dropdown.open .dropdown-menu { display: block; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; overflow-y: auto; }
.modal { background: #faf8f3; border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 640px; max-height: 90vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.18); position: relative; z-index: 1001; }
.modal-lg { max-width: 780px; }
.modal h3 { margin: 0 0 16px 0; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }
.form-grid .form-input { max-width: none; }
@media (max-width: 1000px) { .form-grid { grid-template-columns: 1fr; } }
</style>
