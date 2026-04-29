<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>单位维护</h3>
        <span>管理所有核算组织下的法人单位信息</span>
      </div>
      <div class="filters-bar">
        <select v-model="filterDivision" class="filter" @change="onDivisionChange">
          <option :value="null">全部核算组织</option>
          <option v-for="d in divisions" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
        <input v-model="keyword" class="filter" placeholder="搜索单位编码/名称" style="width:200px" />
        <select v-model="filterStatus" class="filter" style="width:90px">
          <option value="">全部状态</option>
          <option value="enabled">启用</option>
          <option value="disabled">停用</option>
        </select>
        <div style="flex:1"></div>
        <button class="btn btn-primary" @click="openForm()">+ 新建单位</button>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-id">ID</th>
              <th class="col-division">所属核算组织</th>
              <th class="col-code">单位编码</th>
              <th class="col-fullname">单位全称</th>
              <th class="col-shortname">单位简称</th>
              <th class="col-status">状态</th>
              <th class="col-date">创建时间</th>
              <th class="col-action">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in filteredList" :key="e.id"
                :class="{ disabled: e.status === 'disabled' }"
                @dblclick="openForm(e)">
              <td>{{ e.id }}</td>
              <td>{{ e.division_name || '-' }}</td>
              <td><strong>{{ e.entity_code }}</strong></td>
              <td>{{ e.full_name || '-' }}</td>
              <td>{{ e.short_name || '-' }}</td>
              <td><span class="tag" :class="e.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ e.status === 'enabled' ? '启用' : '停用' }}</span></td>
              <td>{{ e.created_at ? e.created_at.slice(0, 19).replace('T', ' ') : '-' }}</td>
              <td class="action-cell">
                <button class="btn btn-secondary btn-sm" @click="openForm(e)">编辑</button>
                <button class="btn btn-secondary btn-sm" v-if="e.status==='enabled'" @click="toggleStatus(e, 'disabled')">停用</button>
                <button class="btn btn-secondary btn-sm" v-else @click="toggleStatus(e, 'enabled')">启用</button>
                <button class="btn btn-warn btn-sm" @click="handleDelete(e)">删除</button>
              </td>
            </tr>
            <tr v-if="!filteredList.length">
              <td colspan="8" style="text-align:center;color:var(--muted);padding:30px">暂无单位数据</td>
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
            <label class="form-label">单位编码 *</label>
            <input v-model="form.entity_code" class="form-input" placeholder="如 DW0001" :disabled="!!editing" />
          </div>
          <div class="form-group">
            <label class="form-label">单位全称 *</label>
            <input v-model="form.full_name" class="form-input" placeholder="单位全称" />
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
import { ref, computed, onMounted } from 'vue'
import * as api from '@/api/master'

const divisions = ref([])
const entities = ref([])
const filterDivision = ref(null)
const filterStatus = ref('')
const keyword = ref('')
const showForm = ref(false)
const editing = ref(null)
const form = ref({
  division_id: null,
  entity_code: '',
  full_name: '',
  short_name: '',
  status: 'enabled',
})

const filteredList = computed(() => {
  let items = entities.value
  if (filterDivision.value) items = items.filter(e => e.division_id === filterDivision.value)
  if (filterStatus.value) items = items.filter(e => e.status === filterStatus.value)
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    items = items.filter(e =>
      (e.entity_code || '').toLowerCase().includes(kw) ||
      (e.full_name || '').toLowerCase().includes(kw) ||
      (e.short_name || '').toLowerCase().includes(kw)
    )
  }
  return items
})

async function loadData() {
  try {
    const [divs, ents] = await Promise.all([
      api.getDivisions(),
      api.getEntities({ page: 1, page_size: 500 }),
    ])
    divisions.value = Array.isArray(divs) ? divs : (divs?.items || [])
    entities.value = ents?.items || []
  } catch (e) {
    console.error(e)
  }
}

function onDivisionChange() {
  // 筛选由 computed 处理，此处仅触发重渲染
}

function getDivisionName(divisionId) {
  const d = divisions.value.find(item => item.id === divisionId)
  return d ? d.name : '-'
}

function openForm(item) {
  if (item) {
    editing.value = item
    form.value = {
      division_id: item.division_id || null,
      entity_code: item.entity_code || '',
      full_name: item.full_name || '',
      short_name: item.short_name || '',
      status: item.status || 'enabled',
    }
  } else {
    editing.value = null
    form.value = {
      division_id: null,
      entity_code: '',
      full_name: '',
      short_name: '',
      status: 'enabled',
    }
  }
  showForm.value = true
}

async function save() {
  if (!form.value.entity_code.trim()) {
    alert('请填写单位编码')
    return
  }
  if (!form.value.full_name.trim()) {
    alert('请填写单位全称')
    return
  }
  if (!form.value.short_name.trim()) {
    alert('请填写单位简称')
    return
  }
  try {
    const payload = {
      division_id: form.value.division_id,
      entity_code: form.value.entity_code.trim(),
      name: form.value.full_name.trim(),
      short_name: form.value.short_name.trim(),
    }
    if (editing.value) {
      payload.status = form.value.status
      await api.updateEntity(editing.value.id, payload)
    } else {
      await api.createEntity(payload)
    }
    showForm.value = false
    await loadData()
  } catch (e) {
    alert(e.message || '保存失败')
  }
}

async function toggleStatus(item, status) {
  try {
    await api.updateEntityStatus(item.id, status)
    await loadData()
  } catch (e) {
    alert(e.message || '操作失败')
  }
}

async function handleDelete(item) {
  const msg = item.status === 'enabled'
    ? `单位「${item.short_name || item.full_name}」当前为启用状态，删除后关联的账户数据将受影响。确定删除？`
    : `确定删除单位「${item.short_name || item.full_name}」？删除后不可恢复。`
  if (!confirm(msg)) return
  try {
    await api.deleteEntity(item.id)
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
.col-division { min-width: 120px; }
.col-code { width: 90px; }
.col-fullname { min-width: 160px; }
.col-shortname { width: 100px; }
.col-status { width: 70px; }
.col-date { width: 150px; }
.col-action { width: 180px; }

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
