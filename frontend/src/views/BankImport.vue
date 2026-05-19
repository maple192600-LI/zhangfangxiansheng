<template>
  <div class="section">
    <div class="section-title">
      <h3>银行流水导入</h3>
      <span>上传银行流水文件，匹配已审核解析规则，预览确认后进入上传结果预览</span>
    </div>

    <div class="flow-steps">
      <div class="flow-step" :class="{ active: step >= 1, done: step > 1 }" @click="step > 1 && goToStep(1)">上传</div>
      <div class="flow-line"></div>
      <div class="flow-step" :class="{ active: step >= 2, done: step > 2 }" @click="step > 2 && goToStep(2)">识别解析器</div>
      <div class="flow-line"></div>
      <div class="flow-step" :class="{ active: step >= 3 }">解析预览</div>
    </div>

    <!-- 无匹配规则提示 -->
    <div v-if="noRuleHint" class="hint-panel" style="margin-bottom:14px">
      缺少解析规则，无法预览解析结果，请先创建或启用解析器。
      <NButton secondary size="small" style="margin-left:8px" @click="noRuleHint = false">关闭</NButton>
    </div>

    <!-- 运行时不可用提示 -->
    <div v-if="runtimeError" class="hint-panel" style="margin-bottom:14px">
      {{ runtimeError }}
      <NButton secondary size="small" style="margin-left:8px" @click="runtimeError = ''">关闭</NButton>
    </div>

    <div v-if="step === 1" class="upload-box" @dragover.prevent @drop.prevent="onDrop" @click="triggerFileInput">
      <input ref="fileInput" type="file" accept=".xls,.xlsx,.csv" hidden @change="onFileChange" />
      <div class="upload-icon">+</div>
      <p>点击或拖拽上传银行流水 Excel</p>
      <span>支持 xls / xlsx / csv 格式</span>
    </div>

    <!-- 上传结果 -->
    <div v-if="uploadResult.batch_code && step >= 2" class="panel">
      <div class="panel-title">上传结果</div>
      <div class="summary-grid">
        <div><label>批次号</label><strong>{{ uploadResult.batch_code }}</strong></div>
        <div><label>文件名</label><strong>{{ uploadResult.file_name }}</strong></div>
        <div><label>格式</label><strong>{{ uploadResult.detected_format }}</strong></div>
        <div><label>数据行</label><strong>{{ uploadResult.row_count }}</strong></div>
      </div>
      <div v-if="parserMatch" class="match-banner">
        <span class="tag tag-green">匹配 Parser：{{ parserMatch.name }}</span>
        <span style="margin-left:8px;color:var(--muted);font-size:12px">
          已审核规则已命中，正在使用确定性解析
        </span>
      </div>
    </div>

    <!-- Step 2: Parser 匹配详情 -->
    <div v-if="step === 2 && parserMatch" class="panel" style="margin-top:14px">
      <div class="panel-title">Parser 匹配详情</div>
      <div class="summary-grid">
        <div><label>Parser</label><strong>{{ parserMatch.name }}</strong></div>
        <div><label>类型</label><strong>{{ parserMatch.kind }}</strong></div>
        <div><label>范围</label><strong>{{ parserMatch.account_code || '通用' }}</strong></div>
        <div><label>置信度</label><strong>{{ parserMatch.confidence || '-' }}</strong></div>
      </div>
      <div class="btn-row" style="margin-top:14px">
        <NButton secondary @click="reset">重新上传</NButton>
        <NButton type="primary" @click="doPreview" :disabled="previewing">
          {{ previewing ? '解析中...' : '预览解析结果' }}
        </NButton>
      </div>
    </div>

    <!-- Step 3: 解析预览 + 进入上传结果预览 -->
    <div v-if="step === 3" style="margin-top:14px">
      <div class="bank-preview-header">
        <span>解析预览（有效 {{ previewResult.valid_count || 0 }} 条，异常 {{ previewResult.abnormal_count || 0 }} 条）</span>
      </div>
      <div class="bank-preview-table">
        <AdvancedDataTable
          v-if="previewResult.parsed_rows?.length"
          :columns="previewColumns"
          :data="previewResult.parsed_rows"
          :rowKey="'_idx'"
          :pagination="true"
          :showToolbar="true"
          :tableKey="'bank-import-preview'"
          :fillParent="true"
        />
      </div>
      <div class="btn-row" style="margin-top:14px">
        <NButton secondary @click="step = 2">返回</NButton>
        <NButton type="primary" @click="goUploadPreview">
          进入上传结果预览
        </NButton>
      </div>
    </div>

    <div v-if="hint" class="hint-panel">
      {{ hint }}
      <NButton secondary size="small" style="margin-left:10px" @click="hint = ''">关闭</NButton>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { NButton } from 'naive-ui'
import { useRouter } from 'vue-router'
import * as bank from '@/api/bank'
import { fmtAmt } from '@/utils/format'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'

const router = useRouter()

const fileInput = ref(null)
const uploadResult = ref({})
const hint = ref('')
const step = ref(1)
const parserMatch = ref(null)
const previewResult = ref({})
const previewing = ref(false)
const noRuleHint = ref(false)
const runtimeError = ref('')

const _TECHNICAL_INDICATORS = [
  'Traceback', 'openpyxl', 'InvalidFileException', 'worker setup error',
  'File "', 'SyntaxError', 'IndentationError', 'NameError', 'TypeError',
  'ValueError', 'AttributeError', 'KeyError', 'IndexError',
]

function _isTechnicalError(msg) {
  return _TECHNICAL_INDICATORS.some(ind => msg.includes(ind))
}

const previewColumns = [
  { field: 'business_date', title: '日期', width: 110 },
  { field: 'summary_text', title: '摘要', minWidth: 140 },
  { field: 'counterparty_name', title: '对方', width: 120, formatter: (cell) => cell.getValue() || '-' },
  {
    field: 'income_amount', title: '收入', width: 110, hozAlign: 'right',
    formatter: (cell) => {
      const v = cell.getValue()
      return v ? `<span style="color:var(--ok-text)">${fmtAmt(v)}</span>` : ''
    },
  },
  {
    field: 'expense_amount', title: '支出', width: 110, hozAlign: 'right',
    formatter: (cell) => {
      const v = cell.getValue()
      return v ? `<span style="color:var(--warn-text)">${fmtAmt(v)}</span>` : ''
    },
  },
  {
    field: 'balance', title: '余额', width: 120, hozAlign: 'right',
    formatter: (cell) => fmtAmt(cell.getValue()),
  },
]

function triggerFileInput() { fileInput.value?.click() }

function goToStep(n) { step.value = n }

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (file) upload(file)
}

function onDrop(event) {
  const file = event.dataTransfer.files?.[0]
  if (file) upload(file)
}

async function upload(file) {
  hint.value = ''
  noRuleHint.value = false
  runtimeError.value = ''
  try {
    uploadResult.value = await bank.uploadBankFile(file)
    parserMatch.value = uploadResult.value.parser_match || null
    if (parserMatch.value) {
      step.value = 2
    } else {
      noRuleHint.value = true
    }
  } catch (e) {
    hint.value = e.message || '上传失败'
  }
}

async function doPreview() {
  hint.value = ''
  runtimeError.value = ''
  if (!parserMatch.value?.parser_artifact_id) {
    noRuleHint.value = true
    step.value = 1
    return
  }
  previewing.value = true
  try {
    previewResult.value = await bank.previewBankImport({
      batch_code: uploadResult.value.batch_code,
      parser_artifact_id: parserMatch.value.parser_artifact_id,
    })
    if (previewResult.value.parsed_rows) {
      previewResult.value.parsed_rows = previewResult.value.parsed_rows.map((r, i) => ({
        ...r,
        _idx: i,
      }))
    }
    step.value = 3
  } catch (e) {
    const msg = e.response?.data?.message || e.message || ''
    if (msg.includes('未实现') || msg.includes('NotImplemented') || msg.includes('运行时')) {
      runtimeError.value = '解析器运行时不可用/未实现，无法预览解析结果'
    } else if (_isTechnicalError(msg)) {
      hint.value = '解析器运行失败，请回到规则中心调整识别方案后重试。'
    } else {
      hint.value = msg || '预览失败'
    }
  } finally {
    previewing.value = false
  }
}

function goUploadPreview() {
  router.push({ path: '/upload-preview', query: { batch_code: uploadResult.value.batch_code } })
}

function reset() {
  step.value = 1
  uploadResult.value = {}
  previewResult.value = {}
  parserMatch.value = null
  hint.value = ''
  noRuleHint.value = false
  runtimeError.value = ''
}
</script>

<style scoped>
@import './common.css';

.flow-steps { display: flex; align-items: center; margin-bottom: 16px; }
.flow-step {
  min-width: 54px;
  height: 28px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--muted);
  cursor: default;
}
.flow-step.active { color: #fff; background: var(--green); border-color: var(--green); }
.flow-step.done { color: var(--green); border-color: var(--green); cursor: pointer; }
.flow-line { flex: 1; height: 1px; background: var(--line); }
.upload-box {
  border: 2px dashed #d7cec1;
  border-radius: var(--radius-sm);
  background: #fff;
  padding: 36px 24px;
  text-align: center;
  cursor: pointer;
}
.upload-box:hover { border-color: var(--green); }
.upload-icon { font-size: 34px; line-height: 1; color: var(--green); }
.upload-box p { margin: 10px 0 4px; font-weight: 600; color: #2d2a26; }
.upload-box span { color: var(--muted); font-size: 13px; }
.panel { margin-top: 14px; border: 1px solid var(--line); background: #fff; border-radius: var(--radius-sm); padding: 14px; }
.panel-title { font-weight: 600; margin-bottom: 10px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.summary-grid div { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 10px; }
.summary-grid label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.summary-grid strong { font-size: 13px; }
.hint-panel { margin-top: 12px; padding: 10px 12px; border: 1px solid #e6c7b8; background: #fff4ef; color: #8b4f38; border-radius: var(--radius-sm); display: flex; align-items: center; }
.match-banner { margin-top: 10px; padding: 8px 12px; background: #f0f9f4; border: 1px solid #c8e6d0; border-radius: var(--radius-sm); display: flex; align-items: center; }
.btn-row { display: flex; gap: 10px; justify-content: flex-end; }

.bank-preview-header {
  padding: 8px 12px;
  font-weight: 600;
  font-size: var(--font-size-sm);
  border: 1px solid var(--line);
  border-bottom: none;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  background: var(--thead-bg);
}

.bank-preview-table {
  height: 400px;
  border: 1px solid var(--line);
  border-top: none;
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
  overflow: hidden;
}

@media (max-width: 900px) {
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
