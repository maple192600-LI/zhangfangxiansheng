<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>核算组织维护</h3>
        <span>管理所有核算组织（板块）的基础信息</span>
      </div>
      <div class="filters-bar">
        <select v-model="filterStatus" class="filter" style="width:90px">
          <option value="">全部状态</option>
          <option value="enabled">启用</option>
          <option value="disabled">停用</option>
        </select>
        <div style="flex:1"></div>
        <button class="btn btn-primary" @click="openForm()">+ 新建核算组织</button>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-id">ID</th>
              <th class="col-name">核算组织名称</th>
              <th class="col-sort">排序</th>
              <th class="col-status">状态</th>
              <th class="col-date">创建时间</th>
              <th class="col-action">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in filteredList" :key="d.id"
                :class="{ disabled: d.status === 'disabled' }"
                @dblclick="openForm(d)">
              <td>{{ d.id }}</td>
              <td><strong>{{ d.name }}</strong></td>
              <td>{{ d.sort_order ?? '-' }}</td>
              <td><span class="tag" :class="d.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ d.status === 'enabled' ? '启用' : '停用' }}</span></td>
              <td>{{ d.created_at ? d.created_at.slice(0, 19).replace('T', ' ') : '-' }}</td>
              <td class="action-cell">
                <button class="btn btn-secondary btn-sm" @click="openForm(d)">编辑</button>
                <button class="btn btn-secondary btn-sm" v-if="d.status==='enabled'" @click="toggleStatus(d, 'disabled')">停用</button>
                <button class="btn btn-secondary btn-sm" v-else @click="toggleStatus(d, 'enabled')">启用</button>
                <button class="btn btn-warn btn-sm" @click="handleDelete(d)">删除</button>
              </td>
            </tr>
            <tr v-if="!filteredList.length">
              <td colspan="6" style="text-align:center;color:var(--muted);padding:30px">暂无核算组织数据</td>
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
      <div class="modal">
        <h3>{{ editing ? '编辑核算组织' : '新建核算组织' }}</h3>
        <div class="form-grid">
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
import { ref, computed, onMounted } from 'vue'
import * as api from '@/api/master'

const list = ref([])
const filterStatus = ref('')
const showForm = ref(false)
const editing = ref(null)
const form = ref({ name: '', sort_order: 0, status: 'enabled' })

const filteredList = computed(() => {
  let items = list.value
  if (filterStatus.value) items = items.filter(d => d.status === filterStatus.value)
  return items
})

async function loadData() {
  try {
    const res = await api.getDivisions()
    list.value = Array.isArray(res) ? res : (res?.items || [])
  } catch (e) {
    console.error(e)
  }
}

function openForm(item) {
  if (item) {
    editing.value = item
    form.value = {
      name: item.name || '',
      sort_order: item.sort_order ?? 0,
      status: item.status || 'enabled',
    }
  } else {
    editing.value = null
    form.value = { name: '', sort_order: 0, status: 'enabled' }
  }
  showForm.value = true
}

async function save() {
  if (!form.value.name.trim()) {
    alert('请填写核算组织名称')
    return
  }
  try {
    const payload = {
      name: form.value.name.trim(),
      sort_order: form.value.sort_order || 0,
    }
    if (editing.value) {
      payload.status = form.value.status
      await api.updateDivision(editing.value.id, payload)
    } else {
      await api.createDivision(payload)
    }
    showForm.value = false
    await loadData()
  } catch (e) {
    alert(e.message || '保存失败')
  }
}

async function toggleStatus(item, status) {
  try {
    await api.updateDivisionStatus(item.id, status)
    await loadData()
  } catch (e) {
    alert(e.message || '操作失败')
  }
}

async function handleDelete(item) {
  const msg = item.status === 'enabled'
    ? `核算组织「${item.name}」当前为启用状态，删除后关联的单位、账户数据将受影响。确定删除？`
    : `确定删除核算组织「${item.name}」？删除后不可恢复。`
  if (!confirm(msg)) return
  try {
    await api.deleteDivision(item.id)
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
.col-name { min-width: 140px; }
.col-sort { width: 70px; }
.col-status { width: 70px; }
.col-date { width: 150px; }
.col-action { width: 180px; }

.action-cell { white-space: nowrap; }

.modal-mask {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal {
  background: #faf8f3;
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 90%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal h3 { margin: 0 0 16px 0; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }
.form-grid .form-input { max-width: none; }

@media (max-width: 1000px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
