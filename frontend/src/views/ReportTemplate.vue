<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">报表模板管理</h2>
      <p class="page-desc">上传Excel模板定义报表格式，对应报表页面按模板格式展示</p>
    </div>

    <div class="template-layout">
      <!-- 左侧：报表类型列表 -->
      <div class="type-panel">
        <div class="type-title">报表类型</div>
        <div class="type-list">
          <div
            v-for="t in reportTypes"
            :key="t.code"
            :class="['type-item', { active: currentType === t.code }]"
            @click="selectType(t.code)"
          >
            <span class="type-name">{{ t.name }}</span>
            <span class="type-badge" v-if="typeDefaultMap[t.code]">默认</span>
          </div>
        </div>
      </div>

      <!-- 右侧：模板管理区 -->
      <div class="main-panel">
        <div class="toolbar">
          <button class="btn btn-primary" @click="openCreateForm">新建模板</button>
          <button class="btn btn-outline" @click="triggerUpload">上传Excel解析</button>
          <input ref="fileInput" type="file" accept=".xlsx,.xls" style="display:none" @change="handleUpload" />
        </div>

        <!-- 模板列表 -->
        <div class="template-list" v-if="templates.length">
          <div v-for="tpl in templates" :key="tpl.id" class="template-card" :class="{ 'is-default': tpl.is_default }">
            <div class="tpl-header">
              <span class="tpl-code">{{ tpl.template_code }}</span>
              <span class="tpl-name">{{ tpl.template_name }}</span>
              <span class="tpl-badge" v-if="tpl.is_default">默认</span>
              <span class="tpl-status" :class="tpl.status">{{ statusLabel(tpl.status) }}</span>
            </div>
            <div class="tpl-meta">
              {{ tpl.columns.length }} 列 · 创建于 {{ formatDate(tpl.created_at) }}
            </div>
            <div class="tpl-columns">
              <span v-for="col in tpl.columns.filter(c => c.visible).slice(0, 6)" :key="col.field_key" class="col-tag">
                {{ col.header_name }}({{ col.width }}px)
              </span>
              <span v-if="tpl.columns.filter(c => c.visible).length > 6" class="col-more">
                +{{ tpl.columns.filter(c => c.visible).length - 6 }} 列
              </span>
            </div>
            <div class="tpl-actions">
              <button class="btn-sm" @click="openEditForm(tpl)">编辑</button>
              <button class="btn-sm" v-if="!tpl.is_default && tpl.status === 'active'" @click="handleSetDefault(tpl)">设为默认</button>
              <button class="btn-sm danger" @click="handleDelete(tpl)">删除</button>
            </div>
          </div>
        </div>
        <div class="empty-state" v-else>
          <p>当前报表类型暂无模板</p>
          <p class="hint">点击"新建模板"手动创建，或上传Excel文件自动解析表头</p>
        </div>
      </div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <div class="modal-overlay" v-if="showForm" @click.self="showForm = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingId ? '编辑模板' : '新建模板' }}</h3>
          <button class="modal-close" @click="showForm = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <label>模板名称</label>
            <input v-model="form.template_name" placeholder="输入模板名称" />
          </div>
          <div class="form-row" v-if="!editingId">
            <label>报表类型</label>
            <select v-model="form.report_type">
              <option v-for="t in reportTypes" :key="t.code" :value="t.code">{{ t.name }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>
              <input type="checkbox" v-model="form.is_default" /> 设为默认模板
            </label>
          </div>
          <div class="form-row">
            <label>备注</label>
            <input v-model="form.remark" placeholder="可选" />
          </div>
          <div class="columns-section">
            <div class="columns-header">
              <span>列配置 ({{ form.columns.length }} 列)</span>
              <button class="btn-sm" @click="addColumn">添加列</button>
            </div>
            <div class="column-list">
              <div v-for="(col, idx) in form.columns" :key="idx" class="column-row">
                <input v-model="col.field_key" placeholder="字段名" class="col-input" style="width:120px" />
                <input v-model="col.header_name" placeholder="表头名" class="col-input" style="width:120px" />
                <input v-model.number="col.width" type="number" placeholder="宽度" class="col-input" style="width:70px" />
                <select v-model="col.align" class="col-input" style="width:70px">
                  <option value="left">左</option>
                  <option value="center">中</option>
                  <option value="right">右</option>
                </select>
                <label class="col-check"><input type="checkbox" v-model="col.visible" /> 显示</label>
                <button class="btn-sm danger" @click="removeColumn(idx)" title="删除">x</button>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="showForm = false">取消</button>
          <button class="btn btn-primary" @click="saveForm">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '@/api/reportTemplate'
import * as fund from '@/api/fund'

const router = useRouter()
const reportTypes = ref([])
const templates = ref([])
const currentType = ref('')
const typeDefaultMap = reactive({})
const showForm = ref(false)
const editingId = ref(null)
const fileInput = ref(null)

const form = reactive({
  template_name: '',
  report_type: '',
  columns: [],
  is_default: false,
  remark: '',
})

onMounted(async () => {
  try {
    const res = await api.getReportTypes()
    if (Array.isArray(res) && res.length) {
      reportTypes.value = res
      currentType.value = res[0].code
      form.report_type = res[0].code
      await loadTemplates()
    }
  } catch (e) {
    console.error('加载报表类型失败', e)
  }
})

function selectType(code) {
  currentType.value = code
  form.report_type = code
  loadTemplates()
}

async function loadTemplates() {
  try {
    const res = await api.getTemplates({ report_type: currentType.value })
    const list = Array.isArray(res) ? res : []
    templates.value = list
    typeDefaultMap[currentType.value] = list.some(t => t.is_default)
  } catch (e) {
    templates.value = []
  }
}

function openCreateForm() {
  editingId.value = null
  Object.assign(form, {
    template_name: '',
    report_type: currentType.value,
    columns: [{ field_key: '', header_name: '', width: 100, align: 'left', visible: true, format: null, sort_order: 1 }],
    is_default: false,
    remark: '',
  })
  showForm.value = true
}

function openEditForm(tpl) {
  editingId.value = tpl.id
  Object.assign(form, {
    template_name: tpl.template_name,
    report_type: tpl.report_type,
    columns: JSON.parse(JSON.stringify(tpl.columns)),
    is_default: tpl.is_default,
    remark: tpl.remark || '',
  })
  showForm.value = true
}

function addColumn() {
  form.columns.push({
    field_key: '',
    header_name: '',
    width: 100,
    align: 'left',
    visible: true,
    format: null,
    sort_order: form.columns.length + 1,
  })
}

function removeColumn(idx) {
  form.columns.splice(idx, 1)
}

async function saveForm() {
  if (!form.template_name) {
    alert('请输入模板名称')
    return
  }
  const validCols = form.columns.filter(c => c.field_key && c.header_name)
  if (!validCols.length) {
    alert('至少需要一列有效配置')
    return
  }
  const mappedCols = validCols.map((c, i) => ({ ...c, sort_order: i + 1 }))

  const payload = {
    template_name: form.template_name,
    report_type: form.report_type,
    columns: mappedCols,
    is_default: form.is_default,
    remark: form.remark || null,
  }

  try {
    if (editingId.value) {
      await api.updateTemplate(editingId.value, payload)
    } else {
      await api.createTemplate(payload)
    }
    showForm.value = false
    await loadTemplates()
  } catch (e) {
    alert(e.message || '保存失败')
  }
}

async function handleSetDefault(tpl) {
  await api.setDefaultTemplate(tpl.id)
  await loadTemplates()
}

async function handleDelete(tpl) {
  if (!confirm(`确认删除模板"${tpl.template_name}"？`)) return
  await api.deleteTemplate(tpl.id)
  await loadTemplates()
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (!currentType.value) {
    alert('请先在左侧选择报表类型')
    e.target.value = ''
    return
  }
  try {
    const res = await api.uploadExcel(file, currentType.value)
    const tpl = res?.saved_template
    if (tpl) {
      alert(`模板已上传保存：${tpl.template_name}（${tpl.template_code}），共解析 ${tpl.columns?.length || 0} 列。`)
      await loadTemplates()
    } else {
      alert('解析成功，但未保存（请检查报表类型）')
    }
  } catch (err) {
    alert('模板上传失败：' + (err.message || err))
  }
  e.target.value = ''
}

function statusLabel(s) {
  return { active: '启用', deleted: '已删除', disabled: '停用' }[s] || s
}

function formatDate(d) {
  return d ? new Date(d).toLocaleDateString('zh-CN') : ''
}
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 18px; font-weight: 600; color: #2D2A26; margin: 0; }
.page-desc { font-size: 13px; color: #8C8680; margin: 4px 0 0; }

.template-layout { display: flex; gap: 20px; min-height: 500px; }

.type-panel { width: 220px; flex-shrink: 0; background: #FDFAF5; border-radius: 10px; padding: 16px 0; border: 1px solid #F0EADF; }
.type-title { font-size: 13px; font-weight: 600; color: #8C8680; padding: 0 16px 10px; border-bottom: 1px solid #F0EADF; }
.type-list { padding: 4px 0; }
.type-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; cursor: pointer; transition: all 0.15s; }
.type-item:hover { background: #F7F4EE; }
.type-item.active { background: #E8E0D4; color: #2D2A26; font-weight: 500; }
.type-name { font-size: 14px; }
.type-badge { font-size: 10px; background: #8B7E6A; color: #fff; border-radius: 8px; padding: 1px 6px; }

.main-panel { flex: 1; }
.toolbar { display: flex; gap: 10px; margin-bottom: 16px; }

.btn { padding: 7px 18px; border-radius: 6px; font-size: 13px; cursor: pointer; border: 1px solid #E0D9D0; transition: all 0.15s; }
.btn-primary { background: #8B7E6A; color: #fff; border-color: #8B7E6A; }
.btn-primary:hover { background: #7A6E5C; }
.btn-outline { background: #fff; color: #5C564E; }
.btn-outline:hover { background: #F7F4EE; }
.btn-sm { padding: 3px 10px; font-size: 12px; border-radius: 4px; border: 1px solid #E0D9D0; background: #fff; cursor: pointer; }
.btn-sm:hover { background: #F7F4EE; }
.btn-sm.danger { color: #C0392B; border-color: #E6B0AA; }
.btn-sm.danger:hover { background: #FDEDEB; }

.template-list { display: flex; flex-direction: column; gap: 10px; }
.template-card { background: #fff; border: 1px solid #F0EADF; border-radius: 8px; padding: 14px 16px; }
.template-card.is-default { border-left: 3px solid #8B7E6A; }
.tpl-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.tpl-code { font-size: 11px; color: #B0A99F; font-family: monospace; }
.tpl-name { font-size: 14px; font-weight: 500; }
.tpl-badge { font-size: 10px; background: #8B7E6A; color: #fff; border-radius: 8px; padding: 1px 6px; }
.tpl-status { font-size: 11px; color: #8C8680; margin-left: auto; }
.tpl-status.active { color: #27AE60; }
.tpl-meta { font-size: 12px; color: #B0A99F; margin-bottom: 8px; }
.tpl-columns { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }
.col-tag { font-size: 11px; background: #F7F4EE; padding: 2px 6px; border-radius: 3px; color: #5C564E; }
.col-more { font-size: 11px; color: #B0A99F; }
.tpl-actions { display: flex; gap: 6px; }

.empty-state { text-align: center; padding: 60px 20px; color: #B0A99F; }
.empty-state .hint { font-size: 12px; margin-top: 8px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 680px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 8px 32px rgba(0,0,0,0.12); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid #F0EADF; }
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-close { background: none; border: none; font-size: 20px; cursor: pointer; color: #8C8680; }
.modal-body { padding: 16px 20px; overflow-y: auto; flex: 1; }
.modal-footer { padding: 12px 20px; border-top: 1px solid #F0EADF; display: flex; justify-content: flex-end; gap: 10px; }

.form-row { margin-bottom: 12px; }
.form-row label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; color: #5C564E; }
.form-row input[type="text"], .form-row input[type="number"], .form-row input:not([type]), .form-row select {
  width: 100%; padding: 6px 10px; border: 1px solid #E0D9D0; border-radius: 6px; font-size: 13px;
}
.form-row input[type="checkbox"] { margin-right: 4px; }

.columns-section { margin-top: 16px; border: 1px solid #F0EADF; border-radius: 8px; padding: 12px; }
.columns-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px; font-weight: 500; }
.column-list { display: flex; flex-direction: column; gap: 6px; }
.column-row { display: flex; gap: 6px; align-items: center; }
.col-input { padding: 4px 6px; border: 1px solid #E0D9D0; border-radius: 4px; font-size: 12px; }
.col-check { font-size: 12px; display: flex; align-items: center; gap: 2px; }
</style>
