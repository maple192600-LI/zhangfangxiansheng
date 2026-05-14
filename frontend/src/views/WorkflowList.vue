<template>
  <div class="wf-list">
    <div class="wf-list__header">
      <h2>工作流编排</h2>
      <div class="wf-list__actions">
        <NSelect
          v-model:value="statusFilter"
          :options="statusOptions"
          style="width: 140px"
          size="small"
          @update:value="loadList"
        />
        <NButton type="primary" size="small" @click="showCreate = true">新建工作流</NButton>
      </div>
    </div>

    <NSpin :show="loading">
      <div v-if="workflows.length === 0 && !loading" class="wf-list__empty">
        暂无工作流，点击"新建工作流"创建第一个
      </div>
      <div class="wf-list__grid">
        <div
          v-for="wf in workflows"
          :key="wf.id"
          class="wf-list__card"
          @click="goEditor(wf)"
        >
          <div class="wf-list__card-name">{{ wf.name }}</div>
          <div class="wf-list__card-code">{{ wf.workflow_code }}</div>
          <div class="wf-list__card-meta">
            <NTag :type="statusTagType(wf.status)" size="small">{{ statusLabel(wf.status) }}</NTag>
            <span class="wf-list__card-ver">v{{ wf.current_version?.version || 0 }}</span>
          </div>
          <div class="wf-list__card-time">{{ formatTime(wf.updated_at) }}</div>
          <div class="wf-list__card-actions" @click.stop>
            <NButton v-if="wf.status === 'active'" size="tiny" quaternary @click="handleRun(wf)">运行</NButton>
            <NButton v-if="wf.status === 'draft'" size="tiny" quaternary type="primary" @click="handleActivate(wf)">发布</NButton>
            <NButton v-if="wf.status !== 'archived'" size="tiny" quaternary type="error" @click="handleArchive(wf)">归档</NButton>
          </div>
        </div>
      </div>
    </NSpin>

    <!-- 新建弹窗 -->
    <NModal v-model:show="showCreate" preset="card" title="新建工作流" style="width: 460px">
      <NForm label-placement="top">
        <NFormItem label="名称">
          <NInput v-model:value="createForm.name" placeholder="例：资金日报生成" />
        </NFormItem>
        <NFormItem label="描述">
          <NInput v-model:value="createForm.description" type="textarea" :rows="2" placeholder="可选" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCreate = false">取消</NButton>
          <NButton type="primary" :loading="creating" @click="handleCreate">创建</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- 运行弹窗 -->
    <NModal v-model:show="showRun" preset="card" title="运行工作流" style="width: 500px">
      <NForm label-placement="top">
        <NFormItem label="运行参数 (JSON)">
          <NInput v-model:value="runInput" type="textarea" :rows="6" placeholder='{"start_date":"2026-05-01","end_date":"2026-05-14"}' />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showRun = false">取消</NButton>
          <NButton type="primary" :loading="running" @click="doRun">运行</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- 运行结果弹窗 -->
    <NModal v-model:show="showRunResult" preset="card" title="运行结果" style="width: 600px">
      <NDescriptions :column="1" label-placement="left" bordered size="small">
        <NDescriptionsItem label="状态">
          <NTag :type="runResult?.status === 'completed' ? 'success' : runResult?.status === 'failed' ? 'error' : 'warning'" size="small">
            {{ runResult?.status }}
          </NTag>
        </NDescriptionsItem>
        <NDescriptionsItem label="错误信息" v-if="runResult?.error_message">
          {{ runResult.error_message }}
        </NDescriptionsItem>
      </NDescriptions>
      <div v-if="runResult?.steps?.length" style="margin-top:12px">
        <div style="font-weight:600;margin-bottom:6px">步骤执行记录</div>
        <NDataTable :columns="stepColumns" :data="runResult.steps" :bordered="false" size="small" />
      </div>
      <template #footer>
        <NButton @click="showRunResult = false">关闭</NButton>
      </template>
    </NModal>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NSelect, NTag, NSpin, NModal, NForm, NFormItem, NInput, NSpace, NDescriptions, NDescriptionsItem, NDataTable, useMessage, useDialog } from 'naive-ui'
import { listWorkflows, createWorkflow, activateWorkflow, archiveWorkflow, startWorkflowRun, getWorkflow, validateWorkflow } from '@/api/workflow'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const workflows = ref([])
const statusFilter = ref(null)
const showCreate = ref(false)
const creating = ref(false)
const showRun = ref(false)
const runTarget = ref(null)
const runInput = ref('{}')
const running = ref(false)
const showRunResult = ref(false)
const runResult = ref(null)

const createForm = ref({ name: '', description: '' })

const statusOptions = [
  { label: '全部', value: null },
  { label: '草稿', value: 'draft' },
  { label: '已启用', value: 'active' },
  { label: '已归档', value: 'archived' },
]

const stepColumns = [
  { title: '节点', key: 'node_id', width: 100 },
  { title: '类型', key: 'node_type', width: 140 },
  { title: '状态', key: 'status', width: 80, render: (row) => h(NTag, { size: 'small', type: row.status === 'completed' ? 'success' : row.status === 'failed' ? 'error' : 'warning' }, () => row.status) },
  { title: '错误', key: 'error_message', ellipsis: { tooltip: true } },
]

function statusLabel(s) {
  return { draft: '草稿', active: '已启用', archived: '已归档' }[s] || s
}

function statusTagType(s) {
  return { draft: 'default', active: 'success', archived: 'info' }[s] || 'default'
}

function formatTime(t) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

async function loadList() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    workflows.value = await listWorkflows(params)
  } catch (e) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!createForm.value.name.trim()) {
    message.warning('请输入名称')
    return
  }
  creating.value = true
  try {
    const wf = await createWorkflow({
      workflow_code: 'wf_' + Date.now().toString(36),
      name: createForm.value.name.trim(),
      description: createForm.value.description.trim() || undefined,
      graph: {
        nodes: [
          { id: 'start', type: 'control.start', params: {}, position: { x: 100, y: 200 } },
          { id: 'end', type: 'control.end', params: {}, position: { x: 500, y: 200 } },
        ],
        edges: [{ from: 'start', to: 'end' }],
      },
    })
    showCreate.value = false
    createForm.value = { name: '', description: '' }
    message.success('创建成功')
    router.push({ name: 'workflow-editor', params: { id: wf.id } })
  } catch (e) {
    message.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

function goEditor(wf) {
  router.push({ name: 'workflow-editor', params: { id: wf.id } })
}

async function handleActivate(wf) {
  try {
    const detail = await getWorkflow(wf.id)
    const graph = detail.current_version?.graph
    if (!graph) {
      message.error('无法获取工作流图，请先在编辑器中保存')
      return
    }
    const result = await validateWorkflow(wf.id, graph)
    if (!result.valid) {
      const errSummary = (result.errors || []).map((e) => e.message).join('；')
      message.error(`校验未通过：${errSummary}`)
      return
    }
    const hasWarnings = result.warnings?.length > 0
    const doActivate = async () => {
      try {
        await activateWorkflow(wf.id)
        message.success('已发布')
        loadList()
      } catch (e) {
        message.error(e.message || '发布失败')
      }
    }
    if (hasWarnings) {
      dialog.warning({
        title: '校验警告',
        content: (result.warnings || []).map((w) => w.message).join('；'),
        positiveText: '仍然发布',
        negativeText: '取消',
        onPositiveClick: doActivate,
      })
    } else {
      dialog.warning({
        title: '确认发布',
        content: `确定要发布「${wf.name}」吗？发布后可执行。`,
        positiveText: '发布',
        negativeText: '取消',
        onPositiveClick: doActivate,
      })
    }
  } catch (e) {
    message.error(e.message || '校验失败')
  }
}

async function handleArchive(wf) {
  dialog.warning({
    title: '确认归档',
    content: `确定要归档「${wf.name}」吗？归档后不可执行。`,
    positiveText: '归档',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await archiveWorkflow(wf.id)
        message.success('已归档')
        loadList()
      } catch (e) {
        message.error(e.message || '归档失败')
      }
    },
  })
}

function handleRun(wf) {
  runTarget.value = wf
  runInput.value = '{}'
  showRun.value = true
}

async function doRun() {
  if (!runTarget.value) return
  let input = {}
  try {
    input = JSON.parse(runInput.value)
  } catch {
    message.error('JSON 格式错误')
    return
  }
  running.value = true
  try {
    const result = await startWorkflowRun(runTarget.value.id, input)
    showRun.value = false
    runResult.value = result
    showRunResult.value = true
  } catch (e) {
    message.error(e.message || '运行失败')
  } finally {
    running.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.wf-list {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.wf-list__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e8e5df;
  flex-shrink: 0;
}
.wf-list__header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.wf-list__actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.wf-list__empty {
  padding: 60px 20px;
  text-align: center;
  color: #909399;
}
.wf-list__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
  padding: 16px 20px;
  overflow: auto;
  flex: 1;
}
.wf-list__card {
  background: #fff;
  border: 1px solid #e8e5df;
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: box-shadow .15s;
}
.wf-list__card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,.1);
}
.wf-list__card-name {
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 4px;
}
.wf-list__card-code {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}
.wf-list__card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.wf-list__card-ver {
  font-size: 12px;
  color: #909399;
}
.wf-list__card-time {
  font-size: 11px;
  color: #b0b0b0;
}
.wf-list__card-actions {
  display: flex;
  gap: 4px;
  margin-top: 8px;
}
</style>
