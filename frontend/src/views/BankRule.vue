<template>
  <div class="section">
    <div class="section-title">
      <h3>银行流水规则中心</h3>
      <span>上传样本 → 沟通需求 → 查看识别结果 → 保存规则</span>
    </div>

    <div class="tabs-bar" style="margin-bottom: 20px;">
      <button class="tab-btn" :class="{ active: activeTab === 'create' }" @click="activeTab = 'create'">创建规则</button>
      <button class="tab-btn" :class="{ active: activeTab === 'list' }" @click="activeTab = 'list'">历史规则</button>
    </div>

    <!-- ==================== 创建规则 ==================== -->
    <div v-show="activeTab === 'create'">

      <!-- 主布局：左侧样本+结果，右侧聊天 -->
      <div class="rule-layout" v-if="uploadStatus === 'success'">
        <div class="rule-left">
          <!-- 样本信息（紧凑） -->
          <div class="workflow-step compact">
            <div class="step-header" style="margin-bottom:8px;">
              <div class="step-number" style="width:22px;height:22px;font-size:11px;">1</div>
              <div class="step-title" style="font-size:14px;">样本文件</div>
              <NButton size="tiny" quaternary type="error" @click="cancelAndReset" style="margin-left:auto;">
                重新选择
              </NButton>
            </div>
            <div class="step-info" style="padding-left:0;">
              {{ job.filename }} · {{ job.format }} · {{ job.row_count }} 行
              <span :class="'tag tag-' + statusTagClass(job.status)">{{ statusLabel(job.status) }}</span>
            </div>
            <div v-if="job.headers && job.headers.length" style="margin-top:8px;">
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
            </div>
          </div>

          <!-- 识别结果审核区 -->
          <div class="workflow-step">
            <div class="step-header" style="margin-bottom:8px;">
              <div class="step-number" style="width:22px;height:22px;font-size:11px;background:#5a8a5a;">2</div>
              <div class="step-title" style="font-size:14px;">识别结果</div>
            </div>

            <template v-if="!job.candidate_code && !trialResult">
              <div style="font-size:13px;color:#999;">
                等待智能体生成识别方案。请在右侧与智能体沟通，它会自动提交识别方案。
              </div>
            </template>

            <template v-else-if="job.candidate_code && !trialResult">
              <div style="font-size:13px;color:#2f4330;margin-bottom:10px;">
                智能体已生成一版识别方案，请生成识别结果进行审核。
              </div>
              <div class="btn-row">
                <NButton type="primary" @click="runTrial" :loading="trialLoading">生成识别结果</NButton>
                <NButton @click="refreshJob">刷新状态</NButton>
              </div>
            </template>

            <template v-if="trialResult">
              <div v-if="trialResult.error" style="color:#d03050;font-size:13px;margin-bottom:10px;">
                {{ trialResult.error }}
              </div>
              <div v-else-if="trialResult.rows && trialResult.rows.length">
                <div style="margin-bottom:8px;font-size:13px;color:#666;">
                  共识别 {{ trialResult.row_count }} 行
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

                <!-- 结果不满意反馈 -->
                <div style="margin-top:12px;padding:10px 14px;background:#faf8f3;border:1px solid #e7e0d5;border-radius:6px;">
                  <div style="font-size:13px;color:#666;margin-bottom:8px;">
                    如果识别结果不正确，请在右侧继续告诉智能体哪里识别错了，它会修改后重新提交。
                  </div>
                </div>
              </div>
              <div v-else style="color:#999;font-size:13px;">识别完成但没有返回数据</div>
            </template>
          </div>

          <!-- 保存规则 -->
          <div v-if="canSave" class="workflow-step" style="border-color:#d7e5d4;">
            <div class="step-header" style="margin-bottom:8px;">
              <div class="step-number" style="width:22px;height:22px;font-size:11px;">3</div>
              <div class="step-title" style="font-size:14px;">确认并保存</div>
            </div>
            <div style="font-size:13px;color:#666;margin-bottom:10px;">
              确认识别结果正确后，为规则命名并保存。保存后银行导入时可自动匹配使用。
            </div>
            <div class="btn-row" style="align-items:center;">
              <NInput v-model:value="parserName" placeholder="规则名称（如：工商银行标准对账单_v1）" style="max-width: 320px;" />
              <NButton type="primary" @click="saveRule" :loading="saveLoading" :disabled="!parserName">
                确认结果正确，保存为可复用规则
              </NButton>
            </div>
            <div v-if="saveSuccess" style="color:#18a058;font-size:13px;margin-top:8px;">
              规则已保存并启用，银行导入时可自动匹配使用。
            </div>
          </div>

          <!-- 技术调试：候选代码（折叠只读） -->
          <div v-if="job.candidate_code" class="workflow-step" style="opacity:0.7;">
            <div class="step-header" style="margin-bottom:8px;">
              <div class="step-number" style="width:22px;height:22px;font-size:11px;background:#999;">&#9881;</div>
              <div class="step-title" style="font-size:13px;">技术调试信息（一般不用看）</div>
            </div>
            <NCollapse>
              <NCollapseItem title="展开查看识别方案代码" name="code">
                <pre class="code-preview">{{ job.candidate_code }}</pre>
              </NCollapseItem>
            </NCollapse>
          </div>
        </div>

        <!-- 右侧：协作沟通 -->
        <div class="rule-right">
          <!-- 未创建会话：选择智能体 -->
          <template v-if="!agentSession.session_id">
            <div class="workflow-step">
              <div class="step-header" style="margin-bottom:8px;">
                <div class="step-title" style="font-size:14px;">选择协作智能体</div>
              </div>
              <template v-if="agentsLoading">
                <div class="loading-state">
                  <div class="loading-spinner"></div>
                  <p>正在加载智能体...</p>
                </div>
              </template>
              <template v-else-if="agents.length === 0">
                <div style="font-size:13px;color:#999;margin-bottom:8px;">
                  当前没有可用的智能体。请先确认已有智能体已启用并配置 AI 模型。
                </div>
                <NButton @click="loadAgents">刷新智能体列表</NButton>
              </template>
              <template v-else>
                <div class="agent-grid">
                  <div
                    v-for="ag in agents"
                    :key="ag.id"
                    class="agent-card"
                    :class="{ selected: selectedAgentId === ag.id }"
                    @click="selectedAgentId = ag.id"
                  >
                    <div class="agent-card-name">{{ ag.display_name }}</div>
                    <div class="agent-card-code">{{ ag.agent_code }}</div>
                  </div>
                </div>
                <div v-if="selectedAgentId" style="margin-top:8px;font-size:13px;color:#2f4330;">
                  当前选择：<strong>{{ selectedAgentName }}</strong>
                </div>
                <div style="margin-top:10px;" class="btn-row">
                  <NButton
                    type="primary"
                    @click="openAgentSession"
                    :loading="agentLoading"
                    :disabled="!selectedAgentId"
                  >
                    开始协作
                  </NButton>
                </div>
              </template>
            </div>
          </template>

          <!-- 已创建会话：内嵌 ChatPanel -->
          <template v-else>
            <div class="embedded-chat">
              <div class="chat-header">
                <span class="chat-header-name">{{ agentSession.agent_name }}</span>
                <NButton text size="tiny" quaternary @click="goToFullAgentPage" style="margin-left:auto;font-size:12px;">
                  打开完整页面 &rarr;
                </NButton>
              </div>
              <ChatPanel
                ref="chatPanelRef"
                :agent="selectedAgentObject"
                :session-id="agentSession.session_id"
                compact
                fold-first-user-msg
                fold-label="系统已提供样本上下文"
              />
            </div>
          </template>
        </div>
      </div>

      <!-- 未上传样本时：上传区域 -->
      <div v-if="uploadStatus !== 'success'" class="workflow-step">
        <div class="step-header">
          <div class="step-number">1</div>
          <div class="step-title">上传样本文件</div>
        </div>
        <div class="step-body">
          <NUpload
            :max="1"
            accept=".xlsx,.xls,.csv"
            :default-upload="false"
            :disabled="uploadStatus === 'uploading'"
            :file-list="fileList"
            @change="handleFileChange"
            @remove="handleFileRemove"
          >
            <NButton :loading="uploadStatus === 'uploading'">
              {{ uploadStatus === 'uploading' ? '正在读取样本...' : (uploadStatus === 'error' ? '重新选择文件' : '选择文件') }}
            </NButton>
          </NUpload>
          <div v-if="uploadStatus === 'uploading'" class="upload-hint" style="color: #999;">
            正在读取样本文件，请稍候...
          </div>
          <div v-else-if="uploadStatus === 'error'" class="upload-hint" style="color: #d03050;">
            样本读取失败：{{ uploadError }}
            <div style="margin-top:4px;font-size:12px;color:#999;">
              请确认文件未损坏，或另存为 .xlsx 后重试。
            </div>
          </div>
        </div>
      </div>

      <!-- 主数据上下文（折叠） -->
      <div v-if="job.context && uploadStatus === 'success'" class="workflow-step" style="opacity:0.7;margin-top:12px;">
        <NCollapse>
          <NCollapseItem title="主数据上下文（仅供参考，无需操作）" name="ctx">
            <div v-for="b in job.context.banks" :key="b.id" style="font-size:13px;">
              {{ b.bank_name }} <span v-if="b.short_name" style="color:#999;">（{{ b.short_name }}）</span>
            </div>
            <div v-for="e in job.context.entities?.slice(0, 10)" :key="e.entity_code" style="margin-top:6px;font-size:13px;">
              {{ e.entity_code }} · {{ e.name }}
            </div>
          </NCollapseItem>
        </NCollapse>
      </div>
    </div>

    <!-- ==================== 历史规则 ==================== -->
    <div v-show="activeTab === 'list'">
      <NDataTable
        :columns="parserColumns"
        :data="parsers"
        :bordered="false"
        size="small"
        :row-key="r => r.id"
      />

      <!-- 规则详情抽屉 -->
      <NDrawer v-model:show="showDetail" :width="480">
        <NDrawerContent :title="'规则详情 — ' + (detailParser?.name || '')" closable>
          <template v-if="detailParser">
            <div class="detail-row"><span class="detail-label">状态</span> <span :class="'tag tag-' + statusTagClass(detailParser.status)">{{ detailParser.status }}</span></div>
            <div class="detail-row"><span class="detail-label">版本</span> {{ detailParser.version }}</div>
            <div class="detail-row"><span class="detail-label">银行 ID</span> {{ detailParser.bank_id || '-' }}</div>
            <div class="detail-row"><span class="detail-label">格式指纹</span> {{ detailParser.format_key || '-' }}</div>
            <div class="detail-row"><span class="detail-label">创建者</span> {{ detailParser.created_by || '-' }}</div>
            <div class="detail-row"><span class="detail-label">审核时间</span> {{ detailParser.approved_at || '-' }}</div>
            <div class="detail-row"><span class="detail-label">置信度</span> {{ detailParser.confidence != null ? (detailParser.confidence * 100).toFixed(1) + '%' : '-' }}</div>
            <div v-if="detailParser.code" style="margin-top:16px;">
              <div class="detail-label" style="margin-bottom:6px;">解析代码（只读）</div>
              <pre class="code-preview">{{ detailParser.code }}</pre>
            </div>
          </template>
        </NDrawerContent>
      </NDrawer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton, NTag, NUpload, NCollapse, NCollapseItem,
  NInput, NDataTable, NDrawer, NDrawerContent, NPopconfirm,
} from 'naive-ui'
import {
  createTrainingJob, getJob, runCandidate, saveParser,
  listActiveAgents, createAgentSession, listParsers,
  getParserDetail, activateParser, retireParser, deleteParser,
} from '@/api/parserTraining'
import ChatPanel from './agent/ChatPanel.vue'

const route = useRoute()
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
const agentsLoading = ref(true)
const selectedAgentId = ref(null)
const showDetail = ref(false)
const detailParser = ref(null)
const chatPanelRef = ref(null)

const uploadStatus = ref('idle')
const uploadError = ref('')
const fileList = ref([])

let pollTimer = null

const selectedAgentName = computed(() => {
  if (!selectedAgentId.value) return ''
  const a = agents.value.find(a => a.id === selectedAgentId.value)
  return a ? a.display_name : ''
})

const selectedAgentObject = computed(() => {
  if (!selectedAgentId.value) return null
  return agents.value.find(a => a.id === selectedAgentId.value) || null
})

const canSave = computed(() => {
  return trialResult.value
    && trialResult.value.rows
    && trialResult.value.rows.length > 0
    && !trialResult.value.error
    && !saveSuccess.value
})

function statusTagClass(status) {
  const map = { active: 'green', draft: 'warn', retired: 'gray', sample_uploaded: 'blue', candidate_ready: 'warn', trial_success: 'green', trial_failed: 'warn', active_parser_saved: 'green' }
  return map[status] || 'gray'
}

function statusLabel(status) {
  const map = { sample_uploaded: '已上传', candidate_ready: '识别方案就绪', trial_success: '试运行成功', trial_failed: '试运行失败', active_parser_saved: '已保存' }
  return map[status] || status
}

function resetCurrentJob() {
  job.value = {}
  trialResult.value = null
  saveSuccess.value = false
  parserName.value = ''
  agentSession.value = {}
  selectedAgentId.value = null
  uploadStatus.value = 'idle'
  uploadError.value = ''
  fileList.value = []
  stopPolling()
  // Clear URL query
  router.replace({ query: {} })
}

function handleFileRemove() {
  resetCurrentJob()
}

function cancelAndReset() {
  resetCurrentJob()
}

async function handleFileChange({ file, fileList: newFileList }) {
  if (!file?.file) return
  fileList.value = newFileList || []
  uploadStatus.value = 'uploading'
  uploadError.value = ''
  const fd = new FormData()
  fd.append('file', file.file)
  try {
    const data = await createTrainingJob(fd)
    if (data) {
      job.value = data
      trialResult.value = null
      saveSuccess.value = false
      parserName.value = ''
      uploadStatus.value = 'success'
      // Save job_code to URL for state recovery
      router.replace({ query: { job_code: data.job_code } })
    }
  } catch (e) {
    console.error('上传失败', e)
    uploadError.value = e.message || '样本文件读取失败'
    uploadStatus.value = 'error'
  }
}

async function refreshJob() {
  if (!job.value.job_code) return
  try {
    const data = await getJob(job.value.job_code)
    if (data) {
      job.value = data
      if (data.trial_result && !trialResult.value) {
        trialResult.value = data.trial_result
      }
      // Restore agent session if present
      if (data.agent_id && data.agent_session_id && !agentSession.value.session_id) {
        const agent = agents.value.find(a => a.id === data.agent_id)
        if (agent) {
          selectedAgentId.value = data.agent_id
          agentSession.value = {
            agent_id: data.agent_id,
            agent_code: agent.agent_code,
            agent_name: agent.display_name,
            session_id: data.agent_session_id,
          }
        }
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
  agentsLoading.value = true
  try {
    const data = await listActiveAgents()
    if (Array.isArray(data)) {
      agents.value = data
    }
  } catch (e) {
    console.error('加载智能体列表失败', e)
  } finally {
    agentsLoading.value = false
  }
}

async function openAgentSession() {
  if (!job.value.job_code || !selectedAgentId.value) return
  agentLoading.value = true
  try {
    const data = await createAgentSession(job.value.job_code, { agent_id: selectedAgentId.value })
    if (data) {
      agentSession.value = data
      // Auto-send initial message after ChatPanel mounts
      nextTick(() => {
        setTimeout(() => {
          if (chatPanelRef.value) {
            chatPanelRef.value.sendExternal(
              '请根据当前上传的银行流水样本，先生成一版识别方案。生成后提交到规则中心，我会审核识别结果表。'
            )
          }
        }, 500)
      })
      // Start polling for candidate_ready
      startPolling()
    }
  } catch (e) {
    console.error('创建会话失败', e)
  } finally {
    agentLoading.value = false
  }
}

function goToFullAgentPage() {
  if (agentSession.value.agent_id && agentSession.value.session_id) {
    router.push({
      name: 'agent-detail',
      params: { id: agentSession.value.agent_id },
      query: { session_id: agentSession.value.session_id },
    })
  }
}

// Polling for job status changes
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!job.value.job_code) return
    const prevStatus = job.value.status
    await refreshJob()
    // If status changed to candidate_ready and no trial result yet, notify user
    if (job.value.status === 'candidate_ready' && prevStatus !== 'candidate_ready') {
      // The UI will reactively show the "生成识别结果" button
    }
  }, 4000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// URL-based state recovery
async function restoreFromUrl() {
  const jobCode = route.query.job_code
  if (!jobCode) return

  try {
    const data = await getJob(jobCode)
    if (data) {
      job.value = data
      uploadStatus.value = 'success'

      if (data.trial_result) {
        trialResult.value = data.trial_result
      }

      // Restore agent session if saved in job
      if (data.agent_id && data.agent_session_id) {
        // Agents may not be loaded yet, wait for them
        await loadAgents()
        const agent = agents.value.find(a => a.id === data.agent_id)
        if (agent) {
          selectedAgentId.value = data.agent_id
          agentSession.value = {
            agent_id: data.agent_id,
            agent_code: agent.agent_code,
            agent_name: agent.display_name,
            session_id: data.agent_session_id,
          }
          startPolling()
        }
      }
    }
  } catch (e) {
    console.error('恢复任务状态失败', e)
  }
}

async function openDetail(id) {
  try {
    const data = await getParserDetail(id)
    if (data) {
      detailParser.value = data
      showDetail.value = true
    }
  } catch (e) {
    console.error('获取规则详情失败', e)
  }
}

async function doActivate(id) {
  try {
    await activateParser(id)
    await loadParsers()
  } catch (e) {
    console.error('启用失败', e)
  }
}

async function doRetire(id) {
  try {
    await retireParser(id)
    await loadParsers()
  } catch (e) {
    console.error('停用失败', e)
  }
}

async function doDelete(id) {
  try {
    await deleteParser(id)
    await loadParsers()
  } catch (e) {
    console.error('删除失败', e)
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

const parserColumns = [
  { title: '名称', key: 'name', width: 200 },
  { title: '版本', key: 'version', width: 60 },
  {
    title: '状态', key: 'status', width: 80,
    render(row) {
      const map = { active: 'success', draft: 'warning', retired: 'default' }
      return h(NTag, { type: map[row.status] || 'default', size: 'small' }, { default: () => row.status })
    }
  },
  { title: '银行 ID', key: 'bank_id', width: 70 },
  { title: '格式指纹', key: 'format_key', width: 120 },
  { title: '创建者', key: 'created_by', width: 80 },
  { title: '审核时间', key: 'approved_at', width: 150 },
  {
    title: '操作', key: 'actions', width: 240,
    render(row) {
      const btns = []
      btns.push(h(NButton, { size: 'tiny', quaternary: true, onClick: () => openDetail(row.id) }, { default: () => '查看' }))
      if (row.status === 'active') {
        btns.push(h(NPopconfirm, { onPositiveClick: () => doRetire(row.id) }, {
          trigger: () => h(NButton, { size: 'tiny', quaternary: true, type: 'warning' }, { default: () => '停用' }),
          default: () => '确定停用该规则？停用后银行导入将不再自动匹配使用。'
        }))
      }
      if (row.status === 'retired' || row.status === 'draft') {
        btns.push(h(NButton, { size: 'tiny', quaternary: true, type: 'success', onClick: () => doActivate(row.id) }, { default: () => '启用' }))
        btns.push(h(NPopconfirm, { onPositiveClick: () => doDelete(row.id) }, {
          trigger: () => h(NButton, { size: 'tiny', quaternary: true, type: 'error' }, { default: () => '删除' }),
          default: () => '确定删除该规则？删除后不可恢复。'
        }))
      }
      return h('div', { style: 'display:flex;gap:4px;flex-wrap:wrap;' }, btns)
    }
  },
]

import { h } from 'vue'

onMounted(() => {
  loadParsers()
  loadAgents().then(() => restoreFromUrl())
})

onUnmounted(() => {
  stopPolling()
})

// Watch for route query changes (back/forward navigation)
watch(() => route.query.job_code, (newCode) => {
  if (newCode && (!job.value.job_code || job.value.job_code !== newCode)) {
    restoreFromUrl()
  }
})
</script>

<style scoped>
@import './common.css';

/* Rule layout: left sample+results, right chat */
.rule-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 16px;
  align-items: start;
}
.rule-left {
  min-width: 0;
}
.rule-right {
  position: sticky;
  top: 16px;
}

@media (max-width: 1100px) {
  .rule-layout {
    grid-template-columns: 1fr;
  }
  .rule-right {
    position: static;
  }
}

/* Embedded chat */
.embedded-chat {
  display: flex;
  flex-direction: column;
  height: 520px;
  border: 1px solid #e7e0d5;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}
.chat-header {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  background: #faf8f3;
  border-bottom: 1px solid #e7e0d5;
  flex-shrink: 0;
}
.chat-header-name {
  font-size: 14px;
  font-weight: 600;
  color: #2f4330;
}
.embedded-chat :deep(.chat-panel) {
  border: none;
  border-radius: 0;
  flex: 1;
  min-height: 0;
}

/* Workflow step (same as before) */
.workflow-step {
  background: var(--panel-2);
  border: 1px solid #e7e0d5;
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-md);
  transition: box-shadow .15s;
}
.workflow-step:hover {
  box-shadow: var(--shadow-card-subtle);
}
.workflow-step.compact {
  padding: 14px 16px;
}
.step-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--green);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}
.step-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}
.step-body {
  padding-left: 38px;
}
.step-info {
  margin-top: 8px;
  font-size: 13px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.upload-hint {
  margin-top: 8px;
  font-size: 13px;
}

/* Tab bar */
.tabs-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--line-soft);
  padding-bottom: 0;
  margin-bottom: 16px;
}
.tab-btn {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 8px 18px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: inherit;
  transition: all .15s;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active {
  color: var(--green);
  border-bottom-color: var(--green);
  font-weight: 600;
}

/* Agent cards */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 8px;
}
.agent-card {
  background: #fff;
  border: 2px solid #e7e0d5;
  border-radius: var(--radius-md);
  padding: 10px 12px;
  cursor: pointer;
  transition: all .15s ease;
}
.agent-card:hover {
  border-color: var(--green);
  box-shadow: var(--shadow-card-subtle);
  transform: translateY(-1px);
}
.agent-card.selected {
  border-color: var(--green);
  background: var(--green-2);
}
.agent-card-name { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 2px; }
.agent-card-code { font-size: 11px; color: var(--muted); }

/* Preview table */
.preview-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.preview-table th { background: var(--thead-bg); padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--line); white-space: nowrap; font-weight: 600; }
.preview-table td { padding: 4px 10px; border-bottom: 1px solid #f0f0f0; white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }

/* Detail */
.detail-row { display: flex; gap: 10px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #f5f0e8; align-items: center; }
.detail-label { color: #999; min-width: 70px; font-weight: 500; }

/* Code preview */
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

.btn-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.loading-state {
  text-align: center;
  padding: 24px;
  color: #8c8680;
}
</style>
