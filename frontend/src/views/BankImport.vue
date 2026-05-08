<template>
  <div class="section">
    <div class="section-title">
      <h3>银行流水导入</h3>
      <span>上传银行流水文件，匹配已审核解析规则，预览确认后入库</span>
    </div>

    <div class="flow-steps">
      <div class="flow-step" :class="{ active: step >= 1, done: step > 1 }" @click="step > 1 && goToStep(1)">上传</div>
      <div class="flow-line"></div>
      <div class="flow-step" :class="{ active: step >= 2, done: step > 2 }" @click="step > 2 && goToStep(2)">匹配规则</div>
      <div class="flow-line"></div>
      <div class="flow-step" :class="{ active: step >= 3, done: step > 3 }" @click="step > 3 && goToStep(3)">确认</div>
      <div class="flow-line"></div>
      <div class="flow-step" :class="{ active: step >= 4 }">完成</div>
    </div>

    <!-- 无匹配规则提示 -->
    <div v-if="noRuleHint" class="hint-panel" style="margin-bottom:14px">
      未匹配到可用解析规则。请先由 Agent 创建并审核 Parser，再回到这里导入。
      <strong style="cursor:pointer;color:var(--green);margin-left:6px" @click="$router.push('/agent')">去创建规则</strong>
      <button class="btn btn-secondary btn-sm" style="margin-left:10px" @click="noRuleHint = false">关闭</button>
    </div>

    <div v-if="step === 1" class="upload-box" @dragover.prevent @drop.prevent="onDrop" @click="triggerFileInput">
      <input ref="fileInput" type="file" accept=".xls,.xlsx,.csv" hidden @change="onFileChange" />
      <div class="upload-icon">+</div>
      <p>点击或拖拽上传银行流水 Excel</p>
      <span>支持 xls / xlsx / csv 格式</span>
    </div>

    <!-- 上传结果（step >= 2 时持续显示） -->
    <div v-if="uploadResult.batch_code && step >= 2" class="panel">
      <div class="panel-title">上传结果</div>
      <div class="summary-grid">
        <div><label>批次号</label><strong>{{ uploadResult.batch_code }}</strong></div>
        <div><label>文件名</label><strong>{{ uploadResult.file_name }}</strong></div>
        <div><label>格式</label><strong>{{ uploadResult.detected_format }}</strong></div>
        <div><label>数据行</label><strong>{{ uploadResult.row_count }}</strong></div>
      </div>
      <!-- 规则匹配结果提示 -->
      <div v-if="parserMatch" class="match-banner">
        <span class="tag tag-green">匹配 Parser：{{ parserMatch.name }}</span>
        <span style="margin-left:8px;color:var(--muted);font-size:12px">
          已审核规则已命中，正在使用确定性解析
        </span>
      </div>
    </div>

    <!-- Step 2: Parser 匹配详情（有规则时自动进入预览，此区域仅作为回看） -->
    <div v-if="step === 2 && parserMatch" class="panel" style="margin-top:14px">
      <div class="panel-title">Parser 匹配详情</div>
      <div class="summary-grid">
        <div><label>Parser</label><strong>{{ parserMatch.name }}</strong></div>
        <div><label>类型</label><strong>{{ parserMatch.kind }}</strong></div>
        <div><label>范围</label><strong>{{ parserMatch.account_code || '通用' }}</strong></div>
        <div><label>样本校验</label><strong>{{ parserCheckStatus }}</strong></div>
      </div>
      <div class="btn-row" style="margin-top:14px">
        <button class="btn btn-secondary" @click="reset">重新上传</button>
        <button class="btn btn-primary" @click="doPreview">预览解析结果</button>
      </div>
    </div>

    <!-- Step 3: 预览确认 -->
    <div v-if="step === 3" class="panel" style="margin-top:14px">
      <div class="panel-title">解析预览（有效 {{ previewResult.valid_count }} 条，异常 {{ previewResult.abnormal_count }} 条）</div>
      <div v-if="previewResult.parsed_rows?.length" style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th>摘要</th>
              <th>对方</th>
              <th class="money">收入</th>
              <th class="money">支出</th>
              <th class="money">余额</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in previewResult.parsed_rows.slice(0, 20)" :key="i">
              <td>{{ row.business_date }}</td>
              <td>{{ row.summary_text }}</td>
              <td>{{ row.counterparty_name }}</td>
              <td class="money">{{ row.income_amount || '' }}</td>
              <td class="money">{{ row.expense_amount || '' }}</td>
              <td class="money">{{ row.balance || '' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="previewResult.parsed_rows.length > 20" style="color:var(--muted);font-size:12px;padding:4px 0">
          仅显示前 20 条，共 {{ previewResult.parsed_rows.length }} 条有效记录
        </div>
      </div>
      <div class="btn-row" style="margin-top:14px">
        <button class="btn btn-secondary" @click="step = 2">返回</button>
        <button class="btn btn-primary" :disabled="committing" @click="doCommit">
          {{ committing ? '提交中...' : `确认提交 ${previewResult.valid_count} 条记录` }}
        </button>
      </div>
    </div>

    <!-- Step 4: 完成 -->
    <div v-if="step === 4" class="panel" style="margin-top:14px">
      <div class="panel-title">导入完成</div>
      <div class="summary-grid" style="grid-template-columns: repeat(3, minmax(0, 1fr))">
        <div><label>批次号</label><strong>{{ commitResult.batch_code }}</strong></div>
        <div><label>Parser</label><strong>{{ parserMatch?.name || commitResult.parser_artifact_id }}</strong></div>
        <div><label>入库行数</label><strong>{{ commitResult.inserted_rows }}</strong></div>
      </div>
      <div class="btn-row" style="margin-top:14px">
        <button class="btn btn-secondary" @click="reset">继续导入</button>
        <button class="btn btn-primary" @click="$router.push({ name: 'base-data' })">查看基础数据表</button>
      </div>
    </div>

    <div v-if="hint" class="hint-panel">
      {{ hint }}
      <button class="btn btn-secondary btn-sm" style="margin-left:10px" @click="hint = ''">关闭</button>
    </div>
  </div>
</template>

<script setup>
import * as bank from '@/api/bank'
import { computed, ref } from 'vue'
const fileInput = ref(null)
const uploadResult = ref({})
const hint = ref('')
const step = ref(1)
const parserMatch = ref(null)
const previewResult = ref({})
const committing = ref(false)
const commitResult = ref({})
const noRuleHint = ref(false)

const parserCheckStatus = computed(() => {
  const log = parserMatch.value?.sample_check_log || {}
  if (log.ok === false) return '需复核'
  return '已通过'
})

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
  try {
    uploadResult.value = await bank.uploadBankFile(file)
    step.value = 2

    const match = uploadResult.value.parser_match
    if (match && match.matched && match.parser_artifact_id) {
      parserMatch.value = match
      await doPreview()
    } else {
      // 无匹配规则 → 提示去 Agent 创建
      parserMatch.value = null
      step.value = 1
      noRuleHint.value = true
    }
  } catch (e) {
    hint.value = e.message || '上传失败'
  }
}

async function doPreview() {
  hint.value = ''
  if (!parserMatch.value?.parser_artifact_id) {
    noRuleHint.value = true
    step.value = 1
    return
  }
  try {
    previewResult.value = await bank.previewBankImport({
      batch_code: uploadResult.value.batch_code,
      parser_artifact_id: parserMatch.value.parser_artifact_id,
    })
    step.value = 3
  } catch (e) {
    hint.value = e.message || '预览失败'
  }
}

async function doCommit() {
  committing.value = true
  hint.value = ''
  try {
    commitResult.value = await bank.commitBankImport({
      batch_code: uploadResult.value.batch_code,
      parser_artifact_id: parserMatch.value.parser_artifact_id,
    })
    step.value = 4
  } catch (e) {
    hint.value = e.message || '提交失败，请重试'
  } finally {
    committing.value = false
  }
}

function reset() {
  step.value = 1
  uploadResult.value = {}
  previewResult.value = {}
  commitResult.value = {}
  parserMatch.value = null
  hint.value = ''
  noRuleHint.value = false
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
.pending-line { margin-top: 12px; color: var(--muted); font-size: 13px; display: flex; align-items: center; }
.hint-panel { margin-top: 12px; padding: 10px 12px; border: 1px solid #e6c7b8; background: #fff4ef; color: #8b4f38; border-radius: var(--radius-sm); display: flex; align-items: center; }
.mapping-info { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.match-banner { margin-top: 10px; padding: 8px 12px; background: #f0f9f4; border: 1px solid #c8e6d0; border-radius: var(--radius-sm); display: flex; align-items: center; }
.btn-row { display: flex; gap: 10px; justify-content: flex-end; }
@media (max-width: 900px) {
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
