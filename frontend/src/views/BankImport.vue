<template>
  <div class="section">
    <div class="section-title">
      <h3>银行流水导入</h3>
      <span>上传银行流水文件，AI 自动识别列映射，确认后直接入库</span>
    </div>

    <div class="flow-steps">
      <div class="flow-step" :class="{ active: step >= 1, done: step > 1 }" @click="step > 1 && goToStep(1)">上传</div>
      <div class="flow-line"></div>
      <div class="flow-step" :class="{ active: step >= 2, done: step > 2 }" @click="step > 2 && goToStep(2)">解析</div>
      <div class="flow-line"></div>
      <div class="flow-step" :class="{ active: step >= 3, done: step > 3 }" @click="step > 3 && goToStep(3)">确认</div>
      <div class="flow-line"></div>
      <div class="flow-step" :class="{ active: step >= 4 }">完成</div>
    </div>

    <!-- Step 1: 上传 -->
    <div class="toolbar-row">
      <label>导入账户</label>
      <select v-model="accountCode" class="filter">
        <option value="">请选择账户</option>
        <optgroup v-for="group in accountGroups" :key="group.entity_id" :label="group.entity_name">
          <option v-for="account in group.accounts" :key="account.account_code" :value="account.account_code">
            {{ account.account_code }} {{ account.account_alias }}
          </option>
        </optgroup>
      </select>
      <label>调用智能体</label>
      <select v-model="agentId" class="filter" style="min-width:180px">
        <option :value="null">请选择智能体</option>
        <option v-for="a in agents" :key="a.id" :value="a.id">{{ a.display_name }}</option>
      </select>
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
    </div>

    <!-- Step 2: AI 解析 -->
    <div v-if="step === 2" class="panel" style="margin-top:14px">
      <div class="panel-title">AI 智能解析列映射</div>
      <div v-if="aiParsing" class="pending-line">
        AI 正在分析表头，请稍候...
        <button class="btn btn-secondary btn-sm" style="margin-left:12px" @click="cancelParse">取消</button>
      </div>
      <div v-else-if="aiResult.ok">
        <div class="mapping-info">
          <span class="tag tag-green">识别成功（{{ aiResult.matched_count }}/{{ aiResult.total_columns }} 列，置信度: {{ aiResult.confidence }}）</span>
          <span style="margin-left:8px;color:var(--muted);font-size:12px">建议模板名: {{ aiResult.template_name }}</span>
        </div>
        <table style="margin-top:10px">
          <thead><tr><th>银行列名</th><th>→</th><th>标准字段</th></tr></thead>
          <tbody>
            <tr v-for="(field, col) in aiResult.mapping" :key="col">
              <td>{{ col }}</td>
              <td style="color:var(--green)">→</td>
              <td><strong>{{ fieldLabel(field) }}</strong></td>
            </tr>
          </tbody>
        </table>
        <div class="btn-row" style="margin-top:14px">
          <button class="btn btn-secondary" @click="reset">重新上传</button>
          <button class="btn btn-secondary" @click="aiParse">重新解析</button>
          <button class="btn btn-accent" @click="doSaveAsRule" :disabled="savingRule">
            {{ savingRule ? '保存中...' : '保存为规则' }}
          </button>
          <button class="btn btn-primary" @click="doPreview">预览解析结果</button>
        </div>
      </div>
      <div v-else>
        <div class="hint-panel">
          {{ aiResult.error || 'AI 解析失败' }}
        </div>
        <div class="btn-row" style="margin-top:12px">
          <button class="btn btn-secondary" @click="reset">重新上传</button>
          <button class="btn btn-primary" @click="aiParse">重试解析</button>
        </div>
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
        <button class="btn btn-secondary" @click="step = 2">返回修改</button>
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
        <div><label>导入账户</label><strong>{{ commitResult.account_code }}</strong></div>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as bank from '@/api/bank'
import * as master from '@/api/master'
import http from '@/api/index'

const router = useRouter()
const fileInput = ref(null)
const uploadResult = ref({})
const accountTree = ref([])
const accountCode = ref('')
const agents = ref([])
const agentId = ref(null)
const hint = ref('')
const step = ref(1)
const aiParsing = ref(false)
const aiResult = ref({})
const previewResult = ref({})
const committing = ref(false)
const commitResult = ref({})
const savingRule = ref(false)

const accountGroups = computed(() => accountTree.value || [])

const FIELD_LABELS = {
  business_date: '交易日期',
  income_amount: '收入金额',
  expense_amount: '支出金额',
  counterparty_name: '对方户名',
  summary_text: '摘要/用途',
  balance: '余额',
  business_time: '交易时间',
  counterpart_account: '对方账号',
  counterpart_bank: '对方开户行',
  voucher_no: '凭证号',
  transaction_type: '交易类型',
}

function fieldLabel(code) { return FIELD_LABELS[code] || code }

function triggerFileInput() { fileInput.value?.click() }

function goToStep(n) { step.value = n }

function cancelParse() { aiParsing.value = false; step.value = 1 }

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
  if (!accountCode.value) {
    hint.value = '请先选择导入账户'
    return
  }
  try {
    uploadResult.value = await bank.uploadBankFile(file)
    step.value = 2
    await aiParse()
  } catch (e) {
    hint.value = e.message || '上传失败'
  }
}

async function aiParse() {
  if (!agentId.value) {
    aiResult.value = { ok: false, error: '请先选择要调用的 AI 智能体' }
    return
  }
  aiParsing.value = true
  aiResult.value = {}
  try {
    aiResult.value = await bank.aiParseHeaders({
      headers: uploadResult.value.headers,
      sample_rows: uploadResult.value.sample_rows,
      agent_id: agentId.value,
    })
  } catch (e) {
    aiResult.value = { ok: false, error: e.message || 'AI 解析失败，请点击重试或重新上传文件' }
  } finally {
    aiParsing.value = false
  }
}

async function doPreview() {
  hint.value = ''
  try {
    previewResult.value = await bank.previewBankImport({
      batch_code: uploadResult.value.batch_code,
      mapping: aiResult.value.mapping,
    })
    step.value = 3
  } catch (e) {
    hint.value = e.message || '预览失败'
  }
}

// 从文件名推断银行名 + "流水规则"
function inferRuleName() {
  const BANK_MAP = {
    '招商': '招商银行', '招行': '招商银行',
    '农业': '农业银行', '农行': '农业银行',
    '工商': '工商银行', '工行': '工商银行',
    '建设': '建设银行', '建行': '建设银行',
    '中国银行': '中国银行', '中行': '中国银行',
    '交通': '交通银行', '交行': '交通银行',
    '广发': '广发银行', '民生': '民生银行',
    '浦发': '浦发银行', '中信': '中信银行',
    '光大': '光大银行', '华夏': '华夏银行',
    '邮储': '邮储银行', '兴业': '兴业银行',
    '平安': '平安银行', '农商': '农商银行',
    '信用社': '信用社', '网商': '网商银行',
    '微众': '微众银行',
  }
  const name = uploadResult.value.file_name || ''
  for (const [kw, bankName] of Object.entries(BANK_MAP)) {
    if (name.includes(kw)) return bankName + '流水规则'
  }
  // fallback: 用 AI 建议的模板名
  return aiResult.value.template_name || '银行流水规则'
}

async function doSaveAsRule() {
  savingRule.value = true
  hint.value = ''
  try {
    await bank.saveAsTemplate({
      template_name: inferRuleName(),
      file_format: uploadResult.value.detected_format || 'xlsx',
      header_row: uploadResult.value.header_row || 0,
      skip_rows: 0,
      sample_headers: uploadResult.value.headers || [],
      mapping_json: aiResult.value.mapping,
    })
    hint.value = '已保存为规则，可在「规则中心 → 银行流水规则」中查看'
  } catch (e) {
    hint.value = '保存规则失败: ' + (e.message || e)
  } finally {
    savingRule.value = false
  }
}

async function doCommit() {
  committing.value = true
  hint.value = ''
  try {
    commitResult.value = await http.post('/bank-import/commit-by-mapping', {
      batch_code: uploadResult.value.batch_code,
      account_code: accountCode.value,
      mapping: aiResult.value.mapping,
      template_name: aiResult.value.template_name,
      sample_headers: uploadResult.value.headers,
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
  aiResult.value = {}
  previewResult.value = {}
  commitResult.value = {}
  hint.value = ''
}

async function loadAccounts() {
  try {
    accountTree.value = await master.getAccountsTree()
    const first = accountTree.value?.flatMap(group => group.accounts || [])[0]
    if (first?.account_code) accountCode.value = first.account_code
  } catch {
    accountTree.value = []
  }
}

async function loadAgents() {
  try {
    agents.value = await bank.getAgents()
    if (agents.value.length && !agentId.value) agentId.value = agents.value[0].id
  } catch {
    agents.value = []
  }
}

onMounted(() => { loadAccounts(); loadAgents() })
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
.toolbar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.toolbar-row label { font-size: 13px; color: var(--muted); }
.toolbar-row .filter { min-width: 280px; }
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
.btn-row { display: flex; gap: 10px; justify-content: flex-end; }
@media (max-width: 900px) {
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .toolbar-row { align-items: stretch; flex-direction: column; }
  .toolbar-row .filter { min-width: 0; width: 100%; }
}
</style>
