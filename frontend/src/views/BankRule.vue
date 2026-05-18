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
            <div v-if="job.job_code" style="margin-top:8px;font-size:13px;color:#666;">
              任务 {{ job.job_code }} · {{ job.filename }} · {{ job.format }} · {{ job.row_count }} 行
              <n-tag :type="statusTagType(job.status)" size="small" style="margin-left:6px;">{{ statusLabel(job.status) }}</n-tag>
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
                <div v-for="e in job.context.entities?.slice(0, 10)" :key="e.entity_code" style="font-size:13px;">
                  {{ e.entity_code }} · {{ e.name }}
                </div>
                <div v-if="job.context.entities?.length > 10" style="font-size:12px;color:#999;">
                  ... 共 {{ job.context.entities.length }} 个单位
                </div>
              </n-collapse-item>
              <n-collapse-item title="账户列表" name="accounts">
                <div v-for="a in job.context.accounts?.slice(0, 10)" :key="a.account_code" style="font-size:13px;">
                  {{ a.account_code }} · {{ a.account_alias }}
                  <span v-if="a.account_last_four" style="color:#999;">后四位: {{ a.account_last_four }}</span>
                </div>
                <div v-if="job.context.accounts?.length > 10" style="font-size:12px;color:#999;">
                  ... 共 {{ job.context.accounts.length }} 个账户
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-card>

          <!-- 4. AI 协作 -->
          <n-card title="AI 协作生成规则" size="small">
            <template v-if="agents.length === 0">
              <div style="font-size:13px;color:#999;margin-bottom:8px;">
                当前没有可用的协作智能体。请先在左侧「AI智能体」模块确认已有智能体已启用并配置 AI 模型，然后回到本页刷新列表。
              </div>
              <n-button @click="loadAgents">刷新智能体列表</n-button>
            </template>
            <template v-else>
              <n-space vertical>
                <n-select
                  v-model:value="selectedAgentId"
                  :options="agentOptions"
                  placeholder="选择协作智能体"
                  style="max-width: 300px;"
                />
                <n-space>
                  <n-button
                    type="primary"
                    @click="openAgentSession"
                    :loading="agentLoading"
                    :disabled="!selectedAgentId || !job.job_code"
                  >
                    让该智能体协助生成规则
                  </n-button>
                  <n-button v-if="agentSession.session_id" @click="goToAgent">
                    打开会话
                  </n-button>
                </n-space>
              </n-space>
            </template>
            <div v-if="agentSession.session_id" style="margin-top:8px;font-size:13px;color:#666;">
              已创建协作会话：{{ agentSession.agent_name }}
            </div>
          </n-card>

          <!-- 5. 试运行 -->
          <n-card title="候选规则试运行" size="small">
            <template v-if="!job.candidate_code">
              <div style="font-size:13px;color:#999;">
                候选规则为空。请先通过 AI 协作生成候选规则，或
                <n-button text type="primary" @click="refreshJob">刷新任务状态</n-button>
              </div>
            </template>
            <template v-else>
              <n-space>
                <n-button
                  type="primary"
                  @click="runTrial"
                  :loading="trialLoading"
                >
                  试运行候选规则
                </n-button>
                <n-button @click="refreshJob">刷新状态</n-button>
              </n-space>
            </template>
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
                  确认结果并保存规则
                </n-button>
              </n-space>
              <div v-if="saveSuccess" style="color:#18a058;font-size:13px;">
                规则已保存并启用，银行导入时可自动匹配使用。
              </div>
            </n-space>
          </n-card>

          <!-- 8. 技术调试：查看候选代码 -->
          <n-collapse v-if="job.candidate_code">
            <n-collapse-item title="技术调试：查看候选代码" name="code">
              <pre class="code-preview">{{ job.candidate_code }}</pre>
            </n-collapse-item>
          </n-collapse>
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
  createTrainingJob, getJob, runCandidate, saveParser,
  listActiveAgents, createAgentSession, getParserContext, listParsers
} from '@/api/parserTraining'

const router = useRouter()
const activeTab = ref('create')

const job = ref({})
const trialResult = ref(null)
const trialLoading = ref(false)
const saveLoading = ref(false)
const saveSuccess = ref(false)
const agentLoading = ref(false)
const agentSession = ref({})
const parserName = ref('')
const parsers = ref([])
const agents = ref([])
const selectedAgentId = ref(null)

const agentOptions = ref([])

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

function statusTagType(status) {
  const map = { sample_uploaded: 'info', candidate_ready: 'warning', trial_success: 'success', trial_failed: 'error', active_parser_saved: 'success' }
  return map[status] || 'default'
}

function statusLabel(status) {
  const map = { sample_uploaded: '已上传', candidate_ready: '候选就绪', trial_success: '试运行成功', trial_failed: '试运行失败', active_parser_saved: '已保存' }
  return map[status] || status
}

async function handleFileChange({ file }) {
  if (!file?.file) return
  const fd = new FormData()
  fd.append('file', file.file)
  try {
    const data = await createTrainingJob(fd)
    if (data) {
      job.value = data
      trialResult.value = null
      saveSuccess.value = false
      parserName.value = ''
    }
  } catch (e) {
    console.error('上传失败', e)
  }
}

async function refreshJob() {
  if (!job.value.job_code) return
  try {
    const data = await getJob(job.value.job_code)
    if (data) {
      job.value = data
      if (job.value.trial_result && !trialResult.value) {
        trialResult.value = job.value.trial_result
      }
    }
  } catch (e) {
    console.error('刷新失败', e)
  }
}

async function runTrial() {
  if (!job.value.job_code) return
  trialLoading.value = true
  trialResult.value = null
  try {
    const data = await runCandidate(job.value.job_code)
    if (data) {
      trialResult.value = data
      await refreshJob()
    }
  } catch (e) {
    trialResult.value = { error: e.message, rows: [] }
  } finally {
    trialLoading.value = false
  }
}

async function saveRule() {
  if (!parserName.value || !job.value.job_code) return
  saveLoading.value = true
  try {
    const data = await saveParser(job.value.job_code, { name: parserName.value })
    if (data) {
      saveSuccess.value = true
      loadParsers()
      await refreshJob()
    }
  } catch (e) {
    console.error('保存失败', e)
  } finally {
    saveLoading.value = false
  }
}

async function loadAgents() {
  try {
    const data = await listActiveAgents()
    if (Array.isArray(data)) {
      agents.value = data
      agentOptions.value = agents.value.map(a => ({
        label: a.display_name,
        value: a.id,
      }))
    }
  } catch (e) {
    console.error('加载智能体列表失败', e)
  }
}

async function openAgentSession() {
  if (!job.value.job_code || !selectedAgentId.value) return
  agentLoading.value = true
  try {
    const data = await createAgentSession(job.value.job_code, { agent_id: selectedAgentId.value })
    if (data) {
      agentSession.value = data
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
    const data = await listParsers({ kind: 'bank' })
    if (Array.isArray(data)) {
      parsers.value = data
    }
  } catch (e) {
    console.error('加载规则列表失败', e)
  }
}

onMounted(() => {
  loadParsers()
  loadAgents()
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
.code-preview {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
}
</style>
