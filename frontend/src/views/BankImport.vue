<template>
  <div class="section">
    <!-- 步骤指示器 -->
    <div class="steps">
      <div class="step" :class="{ active: step >= 1, done: step > 1 }">
        <span class="step-num">1</span><span>上传文件</span>
      </div>
      <div class="step-line" :class="{ done: step > 1 }"></div>
      <div class="step" :class="{ active: step >= 2, done: step > 2 }">
        <span class="step-num">2</span><span>模板匹配</span>
      </div>
      <div class="step-line" :class="{ done: step > 2 }"></div>
      <div class="step" :class="{ active: step >= 3, done: step > 3 }">
        <span class="step-num">3</span><span>预览确认</span>
      </div>
      <div class="step-line" :class="{ done: step > 3 }"></div>
      <div class="step" :class="{ active: step >= 4 }">
        <span class="step-num">4</span><span>提交完成</span>
      </div>
    </div>

    <!-- Step 1: 上传 -->
    <div v-if="step === 1" class="upload-area">
      <div class="upload-box" @click="triggerFileInput" @dragover.prevent @drop.prevent="onDrop">
        <div class="upload-icon">+</div>
        <p>点击或拖拽上传银行流水文件</p>
        <span>支持 xls / xlsx / csv 格式</span>
        <input ref="fileInput" type="file" accept=".xls,.xlsx,.csv" style="display:none" @change="onFileChange" />
      </div>
    </div>

    <!-- Step 2: 上传结果 + 模板选择 -->
    <div v-if="step === 2" class="upload-result">
      <div class="info-grid">
        <div class="info-item">
          <label>批次号</label>
          <strong>{{ uploadResult.batch_code }}</strong>
        </div>
        <div class="info-item">
          <label>文件名</label>
          <span>{{ uploadResult.file_name }}</span>
        </div>
        <div class="info-item">
          <label>文件格式</label>
          <span>{{ uploadResult.detected_format }}</span>
        </div>
        <div class="info-item">
          <label>数据行数</label>
          <span>{{ uploadResult.row_count }}</span>
        </div>
      </div>

      <div class="template-section">
        <h4>模板匹配</h4>
        <div v-if="uploadResult.template_match && uploadResult.template_match.matched" class="warning ok">
          已自动匹配模板：<strong>{{ uploadResult.template_match.template_name }}</strong>
          (置信度: {{ uploadResult.template_match.confidence }})
        </div>
        <div v-else class="warning warn">
          未匹配到已有模板，请手动选择模板或配置映射。
        </div>

        <div class="form-row">
          <label>选择模板</label>
          <select v-model="selectedTemplateId" class="filter" @change="onTemplateChange">
            <option :value="null">不使用模板</option>
            <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.template_name }}</option>
          </select>
        </div>

        <div class="form-row">
          <label>表头行号 (0起)</label>
          <input v-model.number="headerRow" type="number" class="filter" style="width:80px" min="0" />
        </div>

        <div class="btn-row" style="margin-top:14px">
          <button class="btn btn-secondary" @click="resetUpload">重新上传</button>
          <button class="btn btn-primary" @click="doPreview" :disabled="previewing">
            {{ previewing ? '解析中...' : '预览解析结果' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Step 3: 预览 -->
    <div v-if="step === 3" class="preview-area">
      <div class="metric-strip" style="margin-bottom:14px">
        <div class="metric">
          <div class="label">总行数</div>
          <div class="value">{{ previewResult.total_count }}</div>
        </div>
        <div class="metric">
          <div class="label">有效行</div>
          <div class="value" style="color:var(--green)">{{ previewResult.valid_count }}</div>
        </div>
        <div class="metric">
          <div class="label">异常行</div>
          <div class="value" style="color:#c25e3a">{{ previewResult.abnormal_count }}</div>
        </div>
        <div class="metric">
          <div class="label">批次号</div>
          <div class="value" style="font-size:14px">{{ previewResult.batch_code }}</div>
        </div>
      </div>

      <!-- 有效行表格 -->
      <div v-if="previewResult.parsed_rows.length" class="table-wrap">
        <h4>有效数据 ({{ previewResult.valid_count }} 行)</h4>
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>行号</th>
                <th>交易日期</th>
                <th>收入</th>
                <th>支出</th>
                <th>对方户名</th>
                <th>摘要</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in previewResult.parsed_rows" :key="idx">
                <td>{{ row._row_no }}</td>
                <td>{{ row.business_date }}</td>
                <td style="color:#3f5b3d">{{ row.income_amount }}</td>
                <td style="color:#c25e3a">{{ row.expense_amount }}</td>
                <td>{{ row.counterparty_name }}</td>
                <td>{{ row.summary_text }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 异常行 -->
      <div v-if="previewResult.abnormal_rows.length" class="table-wrap" style="margin-top:14px">
        <h4 style="color:#c25e3a">异常数据 ({{ previewResult.abnormal_count }} 行)</h4>
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>行号</th>
                <th>交易日期</th>
                <th>收入</th>
                <th>支出</th>
                <th>对方户名</th>
                <th>摘要</th>
                <th>异常码</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in previewResult.abnormal_rows" :key="idx" style="background:#fdf6f2">
                <td>{{ row._row_no }}</td>
                <td>{{ row.business_date }}</td>
                <td>{{ row.income_amount }}</td>
                <td>{{ row.expense_amount }}</td>
                <td>{{ row.counterparty_name }}</td>
                <td>{{ row.summary_text }}</td>
                <td><span class="badge err">{{ (row._errors || []).join(', ') }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="btn-row" style="margin-top:14px">
        <button class="btn btn-secondary" @click="step = 2">返回修改</button>
        <button class="btn btn-primary" @click="doCommit" :disabled="committing">
          {{ committing ? '提交中...' : '确认提交 (' + previewResult.valid_count + ' 行)' }}
        </button>
      </div>
    </div>

    <!-- Step 4: 完成 -->
    <div v-if="step === 4" class="done-area">
      <div class="warning ok" style="font-size:15px">
        <strong>导入完成!</strong>
        批次 {{ commitResult.batch_code }}: 提交 {{ commitResult.committed_count }} 行,
        异常 {{ commitResult.abnormal_count }} 行
      </div>
      <div class="btn-row" style="margin-top:14px">
        <button class="btn btn-primary" @click="resetUpload">继续导入</button>
      </div>
    </div>

    <!-- 模板管理区 -->
    <div class="section" style="margin-top:14px" v-if="step === 1">
      <div class="top-bar">
        <button class="btn btn-secondary" style="font-size:12px" @click="showTemplateForm = true">+ 新建规则</button>
      </div>
      <table class="data-table" v-if="templates.length">
        <thead>
          <tr><th>模板名称</th><th>类型</th><th>格式</th><th>表头行</th><th>状态</th></tr>
        </thead>
        <tbody>
          <tr v-for="t in templates" :key="t.id">
            <td><strong>{{ t.template_name }}</strong></td>
            <td>{{ t.template_type }}</td>
            <td>{{ t.file_format }}</td>
            <td>{{ t.header_row }}</td>
            <td><span class="badge" :class="t.status">{{ t.status === 'active' ? '启用' : '停用' }}</span></td>
          </tr>
        </tbody>
      </table>
      <p v-else style="color:var(--muted);font-size:13px">暂无银行流水规则</p>
    </div>

    <!-- 新建模板弹窗 -->
    <div class="modal-mask" v-if="showTemplateForm" @click.self="showTemplateForm = false">
      <div class="modal">
        <h3>新建银行流水规则</h3>
        <div class="form-group">
          <label>规则名称（中文，如：招商银行标准流水）</label>
          <input v-model="tplForm.template_name" class="filter" placeholder="如：招商银行标准流水" />
        </div>
        <div class="form-group">
          <label>文件格式</label>
          <select v-model="tplForm.file_format" class="filter">
            <option value="xlsx">xlsx</option>
            <option value="xls">xls</option>
            <option value="csv">csv</option>
          </select>
        </div>
        <div class="form-group">
          <label>表头行号 (0起)</label>
          <input v-model.number="tplForm.header_row" type="number" class="filter" min="0" />
        </div>
        <div class="form-group">
          <label>跳过行数</label>
          <input v-model.number="tplForm.skip_rows" type="number" class="filter" min="0" />
        </div>
        <div class="form-group">
          <label>样本表头 (每行一个列名)</label>
          <textarea v-model="tplForm.sample_headers_text" class="filter" rows="3" placeholder="交易日期&#10;收入金额&#10;支出金额"></textarea>
        </div>
        <div class="form-group">
          <label>映射 JSON (银行列名 → 标准字段)</label>
          <textarea v-model="tplForm.mapping_text" class="filter" rows="5" placeholder='{"交易日期":"business_date","收入金额":"income_amount","支出金额":"expense_amount","对方户名":"counterparty_name","摘要":"summary_text"}'></textarea>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showTemplateForm = false">取消</button>
          <button class="btn btn-primary" @click="doCreateTemplate">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as api from '@/api/bank'

const step = ref(1)
const fileInput = ref(null)
const uploadResult = ref({})
const previewResult = ref({})
const commitResult = ref({})
const templates = ref([])
const selectedTemplateId = ref(null)
const headerRow = ref(0)
const previewing = ref(false)
const committing = ref(false)
const showTemplateForm = ref(false)

const tplForm = ref({
  template_name: '',
  file_format: 'xlsx',
  header_row: 0,
  skip_rows: 0,
  sample_headers_text: '',
  mapping_text: '',
})

function triggerFileInput() {
  fileInput.value.click()
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) doUpload(file)
}

function onDrop(e) {
  const file = e.dataTransfer.files[0]
  if (file) doUpload(file)
}

async function doUpload(file) {
  try {
    const result = await api.uploadBankFile(file)
    uploadResult.value = result
    headerRow.value = result.header_row || 0
    if (result.template_match && result.template_match.template_id) {
      selectedTemplateId.value = result.template_match.template_id
    }
    step.value = 2
  } catch (e) {
    alert('上传失败: ' + e.message)
  }
}

function onTemplateChange() {
  const tpl = templates.value.find(t => t.id === selectedTemplateId.value)
  if (tpl) {
    headerRow.value = tpl.header_row
  }
}

async function doPreview() {
  previewing.value = true
  try {
    const data = {
      batch_code: uploadResult.value.batch_code,
      template_id: selectedTemplateId.value,
      header_row: headerRow.value,
    }
    const result = await api.previewBankImport(data)
    previewResult.value = result
    step.value = 3
  } catch (e) {
    alert('预览失败: ' + e.message)
  } finally {
    previewing.value = false
  }
}

async function doCommit() {
  committing.value = true
  try {
    const data = {
      batch_code: previewResult.value.batch_code,
      parsed_rows: [
        ...previewResult.value.parsed_rows,
        ...previewResult.value.abnormal_rows,
      ],
    }
    const result = await api.commitBankImport(data)
    commitResult.value = result
    step.value = 4
  } catch (e) {
    alert('提交失败: ' + e.message)
  } finally {
    committing.value = false
  }
}

function resetUpload() {
  step.value = 1
  uploadResult.value = {}
  previewResult.value = {}
  commitResult.value = {}
  selectedTemplateId.value = null
  headerRow.value = 0
  if (fileInput.value) fileInput.value.value = ''
}

async function doCreateTemplate() {
  const form = tplForm.value
  if (!form.template_name.trim()) {
    alert('请输入模板名称')
    return
  }
  let mapping = {}
  try {
    mapping = JSON.parse(form.mapping_text || '{}')
  } catch {
    alert('映射 JSON 格式错误，请检查')
    return
  }
  const sampleHeaders = form.sample_headers_text
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean)

  try {
    await api.createParserTemplate({
      template_name: form.template_name,
      template_type: 'bank',
      file_format: form.file_format,
      header_row: form.header_row,
      skip_rows: form.skip_rows,
      sample_headers: sampleHeaders,
      mapping_json: mapping,
    })
    showTemplateForm.value = false
    tplForm.value = {
      template_name: '', file_format: 'xlsx', header_row: 0, skip_rows: 0,
      sample_headers_text: '', mapping_text: '',
    }
    await loadTemplates()
  } catch (e) {
    alert('创建失败: ' + e.message)
  }
}

async function loadTemplates() {
  try {
    templates.value = await api.getParserTemplates({ template_type: 'bank' })
  } catch { /* ignore */ }
}

onMounted(loadTemplates)
</script>

<style scoped>
@import './common.css';

/* 步骤条 */
.steps {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 18px;
  padding: 0 10px;
}
.step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--muted);
}
.step.active { color: #435046; font-weight: 600; }
.step.done { color: var(--green); }
.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f0ede6;
  font-size: 12px;
  font-weight: 700;
}
.step.active .step-num { background: var(--green); color: #fff; }
.step.done .step-num { background: #b5d1b0; color: #fff; }
.step-line {
  flex: 1;
  height: 2px;
  background: #e7e0d5;
  margin: 0 8px;
}
.step-line.done { background: #b5d1b0; }

/* 上传区 */
.upload-area { display: flex; justify-content: center; padding: 20px 0; }
.upload-box {
  width: 100%;
  max-width: 500px;
  border: 2px dashed #d5cfc3;
  border-radius: 16px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
}
.upload-box:hover { border-color: var(--green); }
.upload-icon { font-size: 36px; color: var(--green); margin-bottom: 8px; }
.upload-box p { margin: 8px 0 4px; color: #435046; font-size: 15px; }
.upload-box span { color: var(--muted); font-size: 13px; }

/* 上传结果 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.info-item {
  background: #fff;
  border: 1px solid #e7e0d5;
  border-radius: 12px;
  padding: 12px;
}
.info-item label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.info-item strong, .info-item span { font-size: 14px; }

.template-section {
  background: #fff;
  border: 1px solid #e7e0d5;
  border-radius: 12px;
  padding: 14px;
}
.template-section h4 { margin: 0 0 10px; font-size: 14px; }
.form-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}
.form-row label { font-size: 13px; color: var(--muted); white-space: nowrap; }

/* 表格 */
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th {
  text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line);
  color: var(--muted); font-weight: 500; white-space: nowrap;
}
.data-table td { padding: 8px 10px; border-bottom: 1px solid #f0ede6; }
.table-wrap { background: #fff; border: 1px solid #e7e0d5; border-radius: 12px; padding: 14px; }
.table-wrap h4 { margin: 0 0 10px; font-size: 14px; }
.table-scroll { overflow-x: auto; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.badge.active { background: #edf4ea; color: #3f5b3d; }
.badge.err { background: #fdf0ec; color: #7f4b32; }

/* 弹窗 */
.modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: #faf8f3; border-radius: 16px; padding: 24px;
  width: 90%; max-width: 520px; box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal h3 { margin: 0 0 16px 0; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 4px; }
.form-group .filter { width: 100%; box-sizing: border-box; }
textarea.filter { font-family: inherit; resize: vertical; line-height: 1.6; }

.done-area { padding: 20px 0; }
</style>
