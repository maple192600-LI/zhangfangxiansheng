<template>
  <div class="section">
    <div class="section-title">
      <h3>银行流水规则中心</h3>
    </div>

    <n-tabs v-model:value="activeTab" type="line">
      <n-tab-pane name="create" tab="创建规则">
        <n-space vertical :size="16">
          <!-- 1. 样本上传 -->
          <n-card title="上传样本文件" size="small">
            <n-upload
              :max="1"
              accept=".xlsx,.xls,.csv"
              :default-upload="false"
              @change="handleFileChange"
            >
              <n-button>选择文件</n-button>
            </n-upload>
            <div v-if="job.filename" style="margin-top:8px;font-size:13px;color:#666;">
              {{ job.filename }} · {{ job.format }} · {{ job.row_count }} 行
            </div>
          </n-card>

          <!-- 2. 样本预览 -->
          <n-card v-if="job.headers && job.headers.length" title="样本结构" size="small">
            <div style="overflow-x:auto;">
              <table class="preview-table">
                <thead>
                  <tr><th v-for="h in job.headers" :key="h">{{ h }}</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row, i) in job.sample_rows" :key="i">
                    <td v-for="(cell, j) in row" :key="j">{{ cell }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </n-card>

          <!-- 3. 主数据上下文 -->
          <n-card v-if="job.context" title="主数据上下文" size="small">
            <n-collapse>
              <n-collapse-item title="银行列表" name="banks">
                <div v-for="b in job.context.banks" :key="b.id" style="font-size:13px;">
                  {{ b.bank_name }} <span v-if="b.short_name" style="color:#999;">（{{ b.short_name }}）</span>
                </div>
              </n-collapse-item>
              <n-collapse-item title="单位列表" name="entities">
                <div v-for="e in job.context.entities" :key="e.entity_code" style="font-size:13px;">
                  {{ e.entity_code }} · {{ e.name }}
                </div>
              </n-collapse-item>
              <n-collapse-item title="账户列表" name="accounts">
                <div v-for="a in job.context.accounts" :key="a.account_code" style="font-size:13px;">
                  {{ a.account_code }} · {{ a.account_alias }}
                  <span style="color:#999;">后四位: {{ a.account_last_four || '无' }}</span>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-card>

          <!-- 4. Agent 入口 -->
          <n-card title="规则生成" size="small">
            <n-space>
              <n-button type="primary" @click="openAgentSession" :loading="agentLoading">
                启动规则智能体
              </n-button>
              <n-button v-if="agentSession.session_id" @click="goToAgent">
                继续修正规则
              </n-button>
            </n-space>
            <div v-if="agentSession.session_id" style="margin-top:8px;font-size:13px;color:#666;">
              已关联智能体会话 #{{ agentSession.session_id }}
            </div>
          </n-card>

          <!-- 5. 候选代码试运行 -->
          <n-card title="候选解析规则" size="small">
            <n-input
              v-model:value="candidateCode"
              type="textarea"
              placeholder="粘贴候选 parser 代码（定义 parse(wb, ctx) 函数）"
              :rows="10"
              style="font-family:monospace;font-size:13px;"
            />
            <n-space style="margin-top:8px;">
              <n-button @click="runTrial" :loading="trialLoading" :disabled="!candidateCode || !job.file_path">
                试运行
              </n-button>
            </n-space>
          </n-card>

          <!-- 6. 试运行结果 -->
          <n-card v-if="trialResult" :title="trialResult.error ? '试运行失败' : '解析结果预览'" size="small">
            <div v-if="trialResult.error" style="color:#d03050;font-size:13px;">{{ trialResult.error }}</div>
            <div v-else-if="trialResult.rows && trialResult.rows.length">
              <div style="margin-bottom:8px;font-size:13px;color:#666;">
                共解析 {{ trialResult.row_count }} 行
              </div>
              <div style="overflow-x:auto;">
                <table class="preview-table">
                  <thead>
                    <tr>
                      <th>日期</th><th>摘要</th><th>收入</th><th>支出</th>
                      <th>余额</th><th>对方</th><th>单位</th><th>账户</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, i) in trialResult.rows.slice(0, 50)" :key="i">
                      <td>{{ row.business_date || '' }}</td>
                      <td>{{ row.summary || '' }}</td>
                      <td>{{ row.amount_in || '' }}</td>
                      <td>{{ row.amount_out || '' }}</td>
                      <td>{{ row.rolling_balance || '' }}</td>
                      <td>{{ row.counterparty || '' }}</td>
                      <td>{{ row.entity_name || '' }}</td>
                      <td>{{ row.account_name || '' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div v-else style="color:#999;font-size:13px;">试运行完成但没有返回数据</div>
          </n-card>

          <!-- 7. 保存规则 -->
          <n-card v-if="trialResult && trialResult.rows && trialResult.rows.length && !trialResult.error" title="保存规则" size="small">
            <n-space vertical>
              <n-input v-model:value="parserName" placeholder="规则名称（如：工商银行标准对账单_v1）" />
              <n-space>
                <n-button type="primary" @click="saveRule" :loading="saveLoading" :disabled="!parserName">
                  保存并启用规则
                </n-button>
              </n-space>
              <div v-if="saveSuccess" style="color:#18a058;font-size:13px;">
                规则已保存并启用，银行导入时可自动匹配使用。
              </div>
            </n-space>
          </n-card>
        </n-space>
      </n-tab-pane>

      <n-tab-pane name="list" tab="历史规则">
        <n-data-table
          :columns="parserColumns"
          :data="parsers"
          :bordered="false"
          size="small"
          :row-key="r => r.id"
        />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag } from 'naive-ui'
import {
  createTrainingJob, runCandidate, saveParser,
  getAgentSession, getParserContext, listParsers
} from '@/api/parserTraining'

const router = useRouter()
const activeTab = ref('create')

const job = ref({})
const candidateCode = ref('')
const trialResult = ref(null)
const trialLoading = ref(false)
const saveLoading = ref(false)
const saveSuccess = ref(false)
const agentLoading = ref(false)
const agentSession = ref({})
const parserName = ref('')
const parsers = ref([])

const parserColumns = [
  { title: '名称', key: 'name' },
  { title: '版本', key: 'version', width: 60 },
  {
    title: '状态', key: 'status', width: 80,
    render(row) {
      const map = { active: 'success', draft: 'warning', retired: 'default' }
      return h(NTag, { type: map[row.status] || 'default', size: 'small' }, { default: () => row.status })
    }
  },
  { title: '银行ID', key: 'bank_id', width: 70 },
  { title: '格式指纹', key: 'format_key', width: 120 },
  { title: '创建者', key: 'created_by', width: 90 },
  { title: '置信度', key: 'confidence', width: 70,
    render(row) { return row.confidence != null ? (row.confidence * 100).toFixed(1) + '%' : '-' }
  },
]

async function handleFileChange({ file }) {
  if (!file?.file) return
  const fd = new FormData()
  fd.append('file', file.file)
  try {
    const res = await createTrainingJob(fd)
    if (res.data?.code === 0) {
      job.value = res.data.data
      trialResult.value = null
      saveSuccess.value = false
      parserName.value = ''
    }
  } catch (e) {
    console.error('上传失败', e)
  }
}

async function runTrial() {
  trialLoading.value = true
  trialResult.value = null
  try {
    const res = await runCandidate({
      file_path: job.value.file_path,
      code: candidateCode.value,
    })
    if (res.data?.code === 0) {
      trialResult.value = res.data.data
    }
  } catch (e) {
    trialResult.value = { error: e.message, rows: [] }
  } finally {
    trialLoading.value = false
  }
}

async function saveRule() {
  if (!parserName.value) return
  saveLoading.value = true
  try {
    const res = await saveParser({
      name: parserName.value,
      code: candidateCode.value,
      bank_id: job.value.identity_hints?.bank_id || null,
      format_key: job.value.format_fingerprint || null,
      sample_check_log: { sample_rows: job.value.sample_rows?.length || 0 },
      confidence: trialResult.value?.rows?.length ? 0.8 : null,
      primitives_imports: [],
    })
    if (res.data?.code === 0) {
      saveSuccess.value = true
      loadParsers()
    }
  } catch (e) {
    console.error('保存失败', e)
  } finally {
    saveLoading.value = false
  }
}

async function openAgentSession() {
  if (!job.value.job_id) return
  agentLoading.value = true
  try {
    const res = await getAgentSession({ job_id: job.value.job_id })
    if (res.data?.code === 0) {
      agentSession.value = res.data.data
    }
  } catch (e) {
    console.error('创建会话失败', e)
  } finally {
    agentLoading.value = false
  }
}

function goToAgent() {
  if (agentSession.value.agent_id) {
    router.push({ name: 'agent-detail', params: { id: agentSession.value.agent_id } })
  }
}

async function loadParsers() {
  try {
    const res = await listParsers({ kind: 'bank' })
    if (res.data?.code === 0) {
      parsers.value = res.data.data || []
    }
  } catch (e) {
    console.error('加载规则列表失败', e)
  }
}

onMounted(() => {
  loadParsers()
})
</script>

<style scoped>
@import './common.css';

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.preview-table th {
  background: #f5f4f0;
  padding: 6px 10px;
  text-align: left;
  border-bottom: 1px solid #e5e5e5;
  white-space: nowrap;
}
.preview-table td {
  padding: 4px 10px;
  border-bottom: 1px solid #f0f0f0;
  white-space: nowrap;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
