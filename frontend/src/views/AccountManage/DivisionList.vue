<template>
  <div>
    <div class="filters-bar">
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
        <button class="btn btn-primary" @click="openForm()">+ 新建核算组织</button>
      </div>
    </div>

    <div v-if="!filteredDivisions.length" class="empty-state">
      <div class="empty-icon">&#x1F4CB;</div>
      <h4>暂无核算组织</h4>
      <p>点击右上角「+ 新建核算组织」添加</p>
    </div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="col-ck"><input type="checkbox" :checked="isAllSelected" @change="toggleAll" /></th>
            <th style="width:50px">ID</th>
            <th style="width:90px">编码</th>
            <th style="min-width:140px">核算组织名称</th>
            <th style="width:70px">排序</th>
            <th style="width:70px">状态</th>
            <th style="width:150px">创建时间</th>
            <th style="width:180px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in filteredDivisions" :key="d.id"
              :class="{ disabled: d.status === 'disabled', selected: selectedIds.includes(d.id) }" @dblclick="openForm(d)">
            <td class="col-ck"><input type="checkbox" :value="d.id" v-model="selectedIds" /></td>
            <td>{{ d.id }}</td>
            <td><strong>{{ d.division_code || '-' }}</strong></td>
            <td>{{ d.name }}</td>
            <td>{{ d.sort_order ?? '-' }}</td>
            <td><span class="tag" :class="d.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ d.status === 'enabled' ? '启用' : '停用' }}</span></td>
            <td>{{ d.created_at ? d.created_at.slice(0, 19).replace('T', ' ') : '-' }}</td>
            <td class="action-cell">
              <button class="btn btn-secondary btn-sm" @click="openForm(d)">编辑</button>
              <button class="btn btn-secondary btn-sm" v-if="d.status==='enabled'" @click="toggleStatus(d,'disabled')">停用</button>
              <button class="btn btn-secondary btn-sm" v-else @click="toggleStatus(d,'enabled')">启用</button>
              <button class="btn btn-warn btn-sm" @click="deleteDiv(d)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 核算组织表单弹窗 -->
    <div class="modal-mask" v-if="showForm" @click.self="showForm=false">
      <div class="modal">
        <h3>{{ editing ? '编辑核算组织' : '新建核算组织' }}</h3>
        <div class="form-grid">
          <div class="form-group" v-if="editing">
            <label class="form-label">编码</label>
            <input :value="editing.division_code" class="form-input" disabled />
          </div>
          <div class="form-group">
            <label class="form-label">名称 *</label>
            <input v-model="form.name" class="form-input" placeholder="核算组织名称" />
          </div>
          <div class="form-group">
            <label class="form-label">排序</label>
            <input v-model.number="form.sort_order" type="number" class="form-input" placeholder="数值越小越靠前" />
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
})
const emit = defineEmits(['refresh'])

const selectedIds = ref([])
const dropdownOpen = ref(false)
const filterStatus = ref('')
const showForm = ref(false)
const editing = ref(null)
const form = ref({ name: '', sort_order: 0, status: 'enabled' })

const filteredDivisions = computed(() => {
  let items = props.divisions
  if (filterStatus.value) items = items.filter(d => d.status === filterStatus.value)
  return items
})

const isAllSelected = computed(() => {
  const list = filteredDivisions.value
  return list.length > 0 && list.every(d => selectedIds.value.includes(d.id))
})

function toggleAll() {
  selectedIds.value = isAllSelected.value ? [] : filteredDivisions.value.map(d => d.id)
}

function openForm(item) {
  if (item) {
    editing.value = item
    form.value = { name: item.name || '', sort_order: item.sort_order ?? 0, status: item.status || 'enabled' }
  } else {
    editing.value = null
    form.value = { name: '', sort_order: 0, status: 'enabled' }
  }
  showForm.value = true
}

async function save() {
  if (!form.value.name.trim()) { alert('请填写核算组织名称'); return }
  try {
    const payload = { name: form.value.name.trim(), sort_order: form.value.sort_order || 0 }
    if (editing.value) {
      payload.status = form.value.status
      await api.updateDivision(editing.value.id, payload)
    } else {
      await api.createDivision(payload)
    }
    showForm.value = false
    emit('refresh')
  } catch (e) { alert(e.message || '保存失败') }
}

async function toggleStatus(item, status) {
  try {
    await api.updateDivisionStatus(item.id, status)
    emit('refresh')
  } catch (e) { alert(e.message) }
}

async function deleteDiv(item) {
  try {
    const usage = await api.getDivisionUsage(item.id)
    const unitCount = usage.unit_count || 0
    if (unitCount > 0) {
      const unitNames = (usage.units || []).map(u => `${u.entity_code} ${u.name || u.short_name}`).join('、')
      alert(`该核算组织下有 ${unitCount} 个单位（${unitNames}），请先删除所有单位后再删除核算组织。`)
      return
    }
    if (!confirm(`确定删除核算组织「${item.name}」？此操作不可撤销。`)) return
    await api.deleteDivision(item.id)
    emit('refresh')
  } catch (e) { alert(e.message || '删除失败') }
}

async function batchAction(action) {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  const labels = { enable: '启用', disable: '停用' }
  if (!confirm(`确定批量${labels[action] || action} ${ids.length} 个核算组织？`)) return
  try {
    const result = await api.batchActionDivisions(ids, action)
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
.modal h3 { margin: 0 0 16px 0; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }
.form-grid .form-input { max-width: none; }
</style>
