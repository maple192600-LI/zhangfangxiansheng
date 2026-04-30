<template>
  <div class="section">
    <div class="top-bar">
      <button class="btn btn-primary" @click="showForm=true">+ 新建规则模板</button>
      <button class="btn btn-danger" v-if="selectedIds.size" @click="doBatchDelete">
        删除选中 ({{ selectedIds.size }})
      </button>
    </div>

    <table v-if="templates.length">
      <thead>
        <tr>
          <th style="width:36px"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
          <th>规则名称</th><th>识别银行</th><th>文件格式</th><th>表头行</th><th>跳过行</th>
          <th>样本表头</th><th>映射字段数</th><th>状态</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in templates" :key="t.id" :class="{ selected: selectedIds.has(t.id) }">
          <td><input type="checkbox" :checked="selectedIds.has(t.id)" @change="toggleSelect(t.id)" /></td>
          <td><strong>{{ t.template_name }}</strong></td>
          <td>
            <div class="bank-tag" v-if="guessBank(t.template_name)">
              {{ guessBank(t.template_name) }}
            </div>
          </td>
          <td>{{ t.file_format }}</td>
          <td>{{ t.header_row }}</td>
          <td>{{ t.skip_rows }}</td>
          <td>
            <div class="tag-list">
              <span class="tag" v-for="h in (t.sample_headers || []).slice(0, 5)" :key="h">{{ h }}</span>
              <span class="tag more" v-if="(t.sample_headers || []).length > 5">+{{ t.sample_headers.length - 5 }}</span>
            </div>
          </td>
          <td>{{ Object.keys(t.mapping_json || {}).length }}</td>
          <td><span class="tag" :class="t.status === 'active' ? 'tag-green' : 'tag-gray'">{{ t.status === 'active' ? '启用' : '停用' }}</span></td>
          <td>
            <div class="btn-row">
              <button class="btn btn-secondary btn-sm" @click="viewDetail(t)">查看</button>
              <button class="btn btn-secondary btn-sm" v-if="t.status==='active'" @click="toggleStatus(t, 'disabled')">停用</button>
              <button class="btn btn-secondary btn-sm" v-else @click="toggleStatus(t, 'active')">启用</button>
              <button class="btn btn-danger btn-sm" @click="doDelete(t)">删除</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else style="color:var(--muted);font-size:14px;padding:20px 0">
      暂无银行流水规则。请在「网银导入」页面上传文件后创建模板，或手动新建。
    </p>

    <!-- 详情弹窗 -->
    <div class="modal-mask" v-if="showDetail" @click.self="showDetail=false">
      <div class="modal detail-modal">
        <h3>{{ detailData.template_name }} — 规则详情</h3>
        <div class="detail-grid">
          <div class="field"><span class="label">文件格式</span><span>{{ detailData.file_format }}</span></div>
          <div class="field"><span class="label">表头行号</span><span>{{ detailData.header_row }}</span></div>
          <div class="field"><span class="label">跳过行数</span><span>{{ detailData.skip_rows }}</span></div>
          <div class="field"><span class="label">状态</span><span class="tag" :class="detailData.status === 'active' ? 'tag-green' : 'tag-gray'">{{ detailData.status === 'active' ? '启用' : '停用' }}</span></div>
        </div>

        <div class="detail-section">
          <h4>样本表头 ({{ (detailData.sample_headers || []).length }} 列)</h4>
          <div class="tag-list-wrap">
            <span class="tag" v-for="h in (detailData.sample_headers || [])" :key="h">{{ h }}</span>
          </div>
        </div>

        <div class="detail-section">
          <h4>列映射 (_columns)</h4>
          <div class="mapping-table-wrap" v-if="mappingColumns && Object.keys(mappingColumns).length">
            <table class="mapping-table">
              <thead><tr><th>原始列名</th><th style="width:40px;text-align:center">→</th><th>标准字段</th></tr></thead>
              <tbody>
                <tr v-for="(v, k) in mappingColumns" :key="k">
                  <td class="col-name">{{ k }}</td>
                  <td style="text-align:center;color:var(--muted)">→</td>
                  <td><span class="field-tag">{{ v }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="empty-hint">无列映射</p>
        </div>

        <div class="detail-section" v-if="postProcessText">
          <h4>后处理规则 (post_process)</h4>
          <pre class="code-block">{{ postProcessText }}</pre>
        </div>

        <div class="detail-section">
          <h4>完整规则 JSON</h4>
          <pre class="code-block">{{ fullJsonText }}</pre>
        </div>

        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showDetail=false">关闭</button>
        </div>
      </div>
    </div>

    <!-- 新建弹窗 -->
    <div class="modal-mask" v-if="showForm" @click.self="showForm=false">
      <div class="modal" style="max-width:560px">
        <h3>新建银行流水规则</h3>
        <div class="form-group">
          <label>模板名称</label>
          <input v-model="form.template_name" class="filter" placeholder="如：招商银行标准模板" />
        </div>
        <div class="form-row">
          <div class="form-group" style="flex:1">
            <label>文件格式</label>
            <select v-model="form.file_format" class="filter">
              <option value="xlsx">xlsx</option>
              <option value="xls">xls</option>
              <option value="csv">csv</option>
            </select>
          </div>
          <div class="form-group" style="width:80px">
            <label>表头行</label>
            <input v-model.number="form.header_row" type="number" class="filter" min="0" />
          </div>
          <div class="form-group" style="width:80px">
            <label>跳过行</label>
            <input v-model.number="form.skip_rows" type="number" class="filter" min="0" />
          </div>
        </div>
        <div class="form-group">
          <label>样本表头（每行一个列名）</label>
          <textarea v-model="form.sample_headers_text" class="filter" rows="3" placeholder="交易日期&#10;收入金额&#10;支出金额&#10;对方户名&#10;摘要"></textarea>
        </div>
        <div class="form-group">
          <label>映射 JSON（银行列名 → 标准字段）</label>
          <textarea v-model="form.mapping_text" class="filter" rows="5" placeholder='{"交易日期":"business_date","收入金额":"income_amount","支出金额":"expense_amount","对方户名":"counterparty_name","摘要":"summary_text"}'></textarea>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showForm=false">取消</button>
          <button class="btn btn-primary" @click="doCreate">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as api from '@/api/bank'

const templates = ref([])
const selectedIds = ref(new Set())
const showDetail = ref(false)
const showForm = ref(false)
const detailData = ref({})

const mappingColumns = computed(() => {
  const mj = detailData.value.mapping_json
  if (!mj) return {}
  if (mj._columns) return mj._columns
  // 如果是扁平结构（旧格式），直接返回
  const flat = { ...mj }
  delete flat.post_process
  return flat
})

const postProcessText = computed(() => {
  const mj = detailData.value.mapping_json
  if (!mj || !mj.post_process) return ''
  return JSON.stringify(mj.post_process, null, 2)
})

const fullJsonText = computed(() => {
  const mj = detailData.value.mapping_json
  if (!mj) return '{}'
  return JSON.stringify(mj, null, 2)
})

const allSelected = computed(() => templates.value.length > 0 && selectedIds.value.size === templates.value.length)

const form = ref({
  template_name: '',
  file_format: 'xlsx',
  header_row: 0,
  skip_rows: 0,
  sample_headers_text: '',
  mapping_text: '',
})

async function loadTemplates() {
  try {
    templates.value = await api.getParserTemplates({ template_type: 'bank' })
  } catch { /* ignore */ }
}

function toggleSelect(id) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id); else s.add(id)
  selectedIds.value = s
}

function toggleAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(templates.value.map(t => t.id))
  }
}

import { guessBank } from '@/utils/bankMap'

function viewDetail(t) {
  detailData.value = t
  showDetail.value = true
}

async function toggleStatus(tpl, status) {
  try {
    await api.updateParserTemplate(tpl.id, { status })
    await loadTemplates()
  } catch (e) { alert('操作失败: ' + e.message) }
}

async function doDelete(tpl) {
  if (!confirm(`确定删除规则「${tpl.template_name}」？`)) return
  try {
    await api.deleteParserTemplate(tpl.id)
    selectedIds.value = new Set([...selectedIds.value].filter(id => id !== tpl.id))
    await loadTemplates()
  } catch (e) { alert('删除失败: ' + e.message) }
}

async function doBatchDelete() {
  if (!confirm(`确定删除选中的 ${selectedIds.value.size} 条规则？`)) return
  try {
    await api.batchDeleteParserTemplates([...selectedIds.value])
    selectedIds.value = new Set()
    await loadTemplates()
  } catch (e) { alert('批量删除失败: ' + e.message) }
}

async function doCreate() {
  const f = form.value
  if (!f.template_name.trim()) { alert('请输入模板名称'); return }
  let mapping = {}
  try { mapping = JSON.parse(f.mapping_text || '{}') } catch { alert('映射 JSON 格式错误'); return }
  const sampleHeaders = f.sample_headers_text.split('\n').map(s => s.trim()).filter(Boolean)
  try {
    await api.createParserTemplate({
      template_name: f.template_name,
      template_type: 'bank',
      file_format: f.file_format,
      header_row: f.header_row,
      skip_rows: f.skip_rows,
      sample_headers: sampleHeaders,
      mapping_json: mapping,
    })
    showForm.value = false
    form.value = { template_name: '', file_format: 'xlsx', header_row: 0, skip_rows: 0, sample_headers_text: '', mapping_text: '' }
    await loadTemplates()
  } catch (e) { alert('创建失败: ' + e.message) }
}

onMounted(loadTemplates)
</script>

<style scoped>
@import './common.css';

.tag-list { display: flex; flex-wrap: wrap; gap: 4px; }
.tag-list .tag {
  padding: 2px 8px; font-size: var(--font-size-xs);
}
.tag-list .tag.more { background: #e2ded4; color: #8a6e52; }

.bank-tag {
  display: inline-block; padding: 3px 10px; border-radius: var(--radius-sm); font-size: var(--font-size-xs);
  background: var(--tag-green-bg); color: var(--tag-green-text); font-weight: 500;
}

.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #faf8f3; border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 520px; box-shadow: 0 8px 32px rgba(0,0,0,0.18); }
.modal h3 { margin: 0 0 16px 0; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: var(--font-size-sm); color: var(--muted); margin-bottom: 4px; }
.form-group .filter { width: 100%; box-sizing: border-box; }
.form-row { display: flex; gap: 12px; }
textarea.filter { font-family: inherit; resize: vertical; line-height: 1.6; }

.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.field { background: #fff; border: 1px solid #e7e0d5; border-radius: var(--radius-sm); padding: 10px 12px; }
.field .label { display: block; font-size: var(--font-size-xs); color: var(--muted); margin-bottom: 4px; }

tr.selected { background: #fdf6ec; }

.detail-modal {
  max-width: 900px !important;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.detail-section {
  margin-top: 14px;
}
.detail-section h4 {
  margin: 0 0 6px;
  font-size: 14px;
  color: var(--text);
  font-weight: 600;
}
.tag-list-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-height: 120px;
  overflow-y: auto;
  padding: 6px;
  background: #fff;
  border: 1px solid #e7e0d5;
  border-radius: var(--radius-sm);
}
.mapping-table-wrap {
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid #e7e0d5;
  border-radius: var(--radius-sm);
}
.mapping-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-xs);
}
.mapping-table th {
  position: sticky;
  top: 0;
  background: #f5f0e8;
  padding: 6px 10px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid #e7e0d5;
}
.mapping-table td {
  padding: 5px 10px;
  border-bottom: 1px solid #f0ebe3;
}
.mapping-table .col-name {
  max-width: 280px;
  word-break: break-all;
}
.field-tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: var(--radius-sm);
  background: var(--tag-green-bg, #e8f5e9);
  color: var(--tag-green-text, #2e7d32);
  font-size: 12px;
  font-family: monospace;
}
.code-block {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 14px 16px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.6;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  max-height: 320px;
  overflow: auto;
  white-space: pre;
  margin: 0;
}
.empty-hint {
  color: var(--muted);
  font-size: 13px;
  margin: 0;
  padding: 10px;
  background: #fff;
  border: 1px solid #e7e0d5;
  border-radius: var(--radius-sm);
}

.btn-danger {
  background: #c0392b; color: #fff; border: 1px solid #a93226;
  padding: 5px 14px; border-radius: var(--radius-sm); cursor: pointer; font-size: 13px;
}
.btn-danger:hover { background: #e74c3c; }
.btn-danger.btn-sm { padding: 3px 10px; font-size: 12px; }
</style>
