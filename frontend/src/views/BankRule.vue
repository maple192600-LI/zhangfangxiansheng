<template>
  <div class="section">
    <div class="section-title">
      <h3>银行流水规则中心</h3>
      <span>上传样本 → 沟通需求 → 试运行 → 审核结果 → 保存规则</span>
    </div>

    <div class="tabs-bar" style="margin-bottom: 20px;">
      <button class="tab-btn" :class="{ active: activeTab === 'create' }" @click="activeTab = 'create'">创建规则</button>
      <button class="tab-btn" :class="{ active: activeTab === 'list' }" @click="activeTab = 'list'">历史规则</button>
    </div>

    <!-- ==================== 创建规则 ==================== -->
    <div v-show="activeTab === 'create'">

      <!-- Step 1: 上传样本 -->
      <div class="workflow-step">
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
            @change="handleFileChange"
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
          <div v-if="uploadStatus === 'success'" class="upload-hint" style="color: #18a058;">
            样本已读取
          </div>
          <div v-if="job.job_code" class="step-info">
            任务 {{ job.job_code }} · {{ job.filename }} · {{ job.format }} · {{ job.row_count }} 行
            <span :class="'tag tag-' + statusTagClass(job.status)">{{ statusLabel(job.status) }}</span>
          </div>
          <div v-if="job.headers && job.headers.length" style="margin-top:12px;">
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
      </div>

      <!-- Step 2: 主数据上下文（折叠） -->
      <div v-if="job.context" class="workflow-step">
        <div class="step-header">
          <div class="step-number">2</div>
          <div class="step-title">系统已自动获取的主数据（仅供参考，无需操作）</div>
        </div>
        <div class="step-body">
          <NCollapse>
            <NCollapseItem title="银行列表" name="banks">
              <div v-for="b in job.context.banks" :key="b.id" style="font-size:13px;">
                {{ b.bank_name }} <span v-if="b.short_name" style="color:#999;">（{{ b.short_name }}）</span>
              </div>
            </NCollapseItem>
            <NCollapseItem title="单位列表" name="entities">
              <div v-for="e in job.context.entities?.slice(0, 10)" :key="e.entity_code" style="font-size:13px;">
                {{ e.entity_code }} · {{ e.name }}
              </div>
              <div v-if="job.context.entities?.length > 10" style="font-size:12px;color:#999;">
                ... 共 {{ job.context.entities.length }} 个单位
              </div>
            </NCollapseItem>
            <NCollapseItem title="账户列表" name="accounts">
              <div v-for="a in job.context.accounts?.slice(0, 10)" :key="a.account_code" style="font-size:13px;">
                {{ a.account_code }} · {{ a.account_alias }}
                <span v-if="a.account_last_four" style="color:#999;">后四位: {{ a.account_last_four }}</span>
              </div>
              <div v-if="job.context.accounts?.length > 10" style="font-size:12px;color:#999;">
                ... 共 {{ job.context.accounts.length }} 个账户
              </div>
            </NCollapseItem>
          </NCollapse>
        </div>
      </div>

      <!-- Step 3: 选择协作智能体 + 创建会话 -->
      <div class="workflow-step">
        <div class="step-header">
          <div class="step-number">{{ job.context ? '3' : '2' }}</div>
          <div class="step-title">选择已有协作智能体</div>
        </div>
        <div class="step-body">
          <template v-if="agentsLoading">
            <div class="loading-state">
              <div class="loading-spinner"></div>
              <p>正在加载协作智能体...</p>
            </div>
          </template>
          <template v-else-if="agents.length === 0">
            <div style="font-size:13px;color:#999;margin-bottom:8px;">
              当前没有可用的协作智能体。请先在左侧「AI智能体」模块确认已有智能体已启用并配置 AI 模型，然后回到本页刷新列表。
            </div>
            <NButton @click="loadAgents">刷新智能体列表</NButton>
          </template>
          <template v-else>
            <div class="agent-grid">
              <div
                v-for="agent in agents"
                :key="agent.id"
                class="agent-card"
                :class="{ selected: selectedAgentId === agent.id }"
                @click="selectedAgentId = agent.id"
              >
                <div class="agent-card-name">{{ agent.display_name }}</div>
                <div class="agent-card-code">{{ agent.agent_code }}</div>
              </div>
            </div>
            <div v-if="selectedAgentId" style="margin-top:10px;font-size:13px;color:#2f4330;">
              当前选择：<strong>{{ selectedAgentName }}</strong>
            </div>
            <div v-if="!agentSession.session_id" style="margin-top:10px;" class="btn-row">
              <NButton
                type="primary"
                @click="openAgentSession"
                :loading="agentLoading"
                :disabled="!selectedAgentId || !job.job_code"
              >
                创建协作会话
              </NButton>
            </div>
            <div v-if="uploadStatus === 'error' && !agentSession.session_id" style="font-size:12px;color:#d03050;margin-top:6px;">
              样本读取失败，不能创建协作会话。请重新上传样本文件。
            </div>
            <div v-else-if="uploadStatus !== 'success' && uploadStatus !== 'idle' && !job.job_code && !agentSession.session_id" style="font-size:12px;color:#999;margin-top:6px;">
              请先上传样本文件
            </div>
            <div v-else-if="uploadStatus === 'success' && job.job_code && !selectedAgentId && !agentSession.session_id" style="font-size:12px;color:#999;margin-top:6px;">
              请选择协作智能体
            </div>
          </template>

          <!-- 协作会话信息 -->
          <div v-if="agentSession.session_id" style="margin-top:14px;padding-top:12px;border-top:1px dashed #e7e0d5;">
            <div style="font-size:13px;color:#2f4330;margin-bottom:8px;">
              已创建协作会话：<strong>{{ agentSession.agent_name }}</strong>
              <span style="color:#999;margin-left:6px;">会话 #{{ agentSession.session_id }}</span>
            </div>
            <div style="font-size:12px;color:#999;margin-bottom:10px;">
              请在协作会话里告诉智能体：哪些列识别错了、表头在哪一行、日期/收入/支出/余额/摘要应该怎么取。
              智能体修改后会提交候选规则；回到本页点击刷新候选规则，再试运行查看结果。
            </div>
            <div class="btn-row">
              <NButton type="primary" @click="goToAgent">打开协作会话</NButton>
              <NButton @click="refreshJob">刷新候选规则</NButton>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 4: 候选规则试运行 -->
      <div class="workflow-step" v-if="agentSession.session_id">
        <div class="step-header">
          <div class="step-number">{{ stepNumberOf('trial') }}</div>
          <div class="step-title">试运行候选规则并审核解析结果</div>
        </div>
        <div class="step-body">
          <template v-if="!job.candidate_code">
            <div style="font-size:13px;color:#999;">
              等待智能体提交候选规则。请在协作会话中与智能体沟通，让它生成并提交候选规则。
              <NButton text type="primary" @click="refreshJob" style="margin-left:8px;">刷新候选规则</NButton>
            </div>
          </template>
          <template v-else>
            <div style="font-size:13px;color:#2f4330;margin-bottom:10px;">
              智能体已提交候选规则，试运行查看解析结果。用户审核的是识别结果，不是代码。
            </div>
            <div class="btn-row" style="margin-bottom:12px;">
              <NButton type="primary" @click="runTrial" :loading="trialLoading">试运行候选规则</NButton>
              <NButton @click="refreshJob">刷新候选规则</NButton>
            </div>

            <!-- 试运行结果 -->
            <div v-if="trialResult">
              <div v-if="trialResult.error" style="color:#d03050;font-size:13px;margin-bottom:10px;">
                {{ trialResult.error }}
              </div>
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
                <!-- 结果不满意反馈 -->
                <div style="margin-top:12px;padding:10px 14px;background:#faf8f3;border:1px solid #e7e0d5;border-radius:6px;">
                  <div style="font-size:13px;color:#666;margin-bottom:8px;">
                    如果识别结果不正确，请回到协作会话继续反馈，智能体会修改后重新提交。
                  </div>
                  <div class="btn-row">
                    <NButton @click="goToAgent">结果不对，回到协作会话继续反馈</NButton>
                  </div>
                </div>
              </div>
              <div v-else style="color:#999;font-size:13px;">试运行完成但没有返回数据</div>
            </div>
          </template>
        </div>
      </div>

      <!-- Step 5: 保存规则 -->
      <div v-if="trialResult && trialResult.rows && trialResult.rows.length && !trialResult.error" class="workflow-step">
        <div class="step-header">
          <div class="step-number">{{ stepNumberOf('save') }}</div>
          <div class="step-title">确认结果正确并保存规则</div>
        </div>
        <div class="step-body">
          <div style="font-size:13px;color:#666;margin-bottom:10px;">
            确认解析结果正确后，为规则命名并保存。保存后银行导入时可自动匹配使用。
          </div>
          <div class="btn-row" style="align-items:center;">
            <NInput v-model:value="parserName" placeholder="规则名称（如：工商银行标准对账单_v1）" style="max-width: 360px;" />
            <NButton type="primary" @click="saveRule" :loading="saveLoading" :disabled="!parserName">
              确认结果并保存规则
            </NButton>
          </div>
          <div v-if="saveSuccess" style="color:#18a058;font-size:13px;margin-top:8px;">
            规则已保存并启用，银行导入时可自动匹配使用。
          </div>
        </div>
      </div>

      <!-- 技术调试：候选代码（折叠只读） -->
      <div v-if="job.candidate_code" class="workflow-step" style="opacity:0.7;">
        <div class="step-header">
          <div class="step-number" style="background:#999;">&#9881;</div>
          <div class="step-title">技术调试信息（只读）</div>
        </div>
        <div class="step-body">
          <NCollapse>
            <NCollapseItem title="展开查看候选代码" name="code">
              <pre class="code-preview">{{ job.candidate_code }}</pre>
            </NCollapseItem>
          </NCollapse>
        </div>
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
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NTag, NUpload, NCollapse, NCollapseItem,
  NInput, NDataTable, NDrawer, NDrawerContent, NPopconfirm,
} from 'naive-ui'
import {
  createTrainingJob, getJob, runCandidate, saveParser,
  listActiveAgents, createAgentSession, listParsers,
  getParserDetail, activateParser, retireParser, deleteParser,
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
const agentsLoading = ref(true)
const selectedAgentId = ref(null)
const showDetail = ref(false)
const detailParser = ref(null)

const uploadStatus = ref('idle') // idle | uploading | success | error
const uploadError = ref('')

const selectedAgentName = computed(() => {
  if (!selectedAgentId.value) return ''
  const a = agents.value.find(a => a.id === selectedAgentId.value)
  return a ? a.display_name : ''
})

function stepNumberOf(step) {
  const hasContext = !!job.value.context
  const base = (hasContext ? 3 : 2) + 1
  if (step === 'save') return base + 1
  return base
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

function statusTagClass(status) {
  const map = { active: 'green', draft: 'warn', retired: 'gray', sample_uploaded: 'blue', candidate_ready: 'warn', trial_success: 'green', trial_failed: 'warn', active_parser_saved: 'green' }
  return map[status] || 'gray'
}

function statusLabel(status) {
  const map = { sample_uploaded: '已上传', candidate_ready: '候选就绪', trial_success: '试运行成功', trial_failed: '试运行失败', active_parser_saved: '已保存' }
  return map[status] || status
}

async function handleFileChange({ file }) {
  if (!file?.file) return
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
    }
  } catch (e) {
    console.error('创建会话失败', e)
  } finally {
    agentLoading.value = false
  }
}

function goToAgent() {
  if (agentSession.value.agent_id && agentSession.value.session_id) {
    router.push({
      name: 'agent-detail',
      params: { id: agentSession.value.agent_id },
      query: { session_id: agentSession.value.session_id },
    })
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

onMounted(() => {
  loadParsers()
  loadAgents()
})
</script>

<style scoped>
@import './common.css';

/* 流程步骤 */
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
}
.upload-hint {
  margin-top: 8px;
  font-size: 13px;
}

/* Tab 栏 */
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

/* 智能体卡片 */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}
.agent-card {
  background: #fff;
  border: 2px solid #e7e0d5;
  border-radius: var(--radius-md);
  padding: 14px 16px;
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
.agent-card-name { font-size: 14px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
.agent-card-code { font-size: 12px; color: var(--muted); }

/* 预览表格 */
.preview-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.preview-table th { background: var(--thead-bg); padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--line); white-space: nowrap; font-weight: 600; }
.preview-table td { padding: 4px 10px; border-bottom: 1px solid #f0f0f0; white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }

/* 规则详情 */
.detail-row { display: flex; gap: 10px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #f5f0e8; align-items: center; }
.detail-label { color: #999; min-width: 70px; font-weight: 500; }

/* 候选代码 */
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
