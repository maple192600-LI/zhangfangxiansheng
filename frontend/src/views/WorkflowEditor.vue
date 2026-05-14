<template>
  <div class="wf-editor">
    <!-- 顶部工具栏 -->
    <div class="wf-editor__toolbar">
      <div class="wf-editor__toolbar-left">
        <NButton quaternary size="small" @click="goBack">← 返回</NButton>
        <span class="wf-editor__title">{{ workflow?.name || '' }}</span>
        <NTag :type="statusTagType" size="small">{{ statusLabel }}</NTag>
        <span v-if="workflow?.current_version" class="wf-editor__ver">v{{ workflow.current_version.version }}</span>
      </div>
      <div class="wf-editor__toolbar-right">
        <NButton size="small" @click="doValidate" :loading="validating">校验</NButton>
        <NButton size="small" type="primary" @click="doSave" :loading="saving">保存</NButton>
        <NButton v-if="workflow?.status === 'draft'" size="small" type="warning" @click="doActivate" :loading="activating">发布</NButton>
        <NButton v-if="workflow?.status === 'active'" size="small" type="success" @click="showRunModal = true">运行</NButton>
      </div>
    </div>

    <div class="wf-editor__body">
      <!-- 左侧节点库 -->
      <div class="wf-editor__sidebar">
        <div class="wf-editor__sidebar-title">节点库</div>
        <div v-for="(items, cat) in groupedNodes" :key="cat" class="wf-editor__node-group">
          <div class="wf-editor__node-cat">{{ cat }}</div>
          <div
            v-for="t in items"
            :key="t"
            class="wf-editor__node-item"
            draggable="true"
            @dragstart="(e) => onDragStart(e, t)"
          >
            <span class="wf-editor__node-dot" :style="{ background: getMeta(t).color }"></span>
            {{ getMeta(t).label }}
          </div>
        </div>
      </div>

      <!-- 中间画布 -->
      <div class="wf-editor__canvas" @drop="onDrop" @dragover.prevent>
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          fit-view-on-init
          :snap-to-grid="true"
          :snap-grid="[20, 20]"
          @node-click="onNodeClick"
          @pane-click="selectedNode = null"
          @connect="onConnect"
          @edges-change="onEdgesChange"
          @nodes-change="onNodesChange"
        >
          <Background />
          <Controls />
          <MiniMap />
        </VueFlow>
      </div>

      <!-- 右侧属性面板 -->
      <div class="wf-editor__props" v-if="selectedNode">
        <div class="wf-editor__props-title">节点属性</div>
        <div class="wf-editor__props-row"><span class="wf-editor__props-label">ID</span> {{ selectedNode.id }}</div>
        <div class="wf-editor__props-row"><span class="wf-editor__props-label">类型</span> {{ selectedNode.data?.nodeType }}</div>
        <div class="wf-editor__props-row"><span class="wf-editor__props-label">名称</span> {{ getMeta(selectedNode.data?.nodeType).label }}</div>
        <div class="wf-editor__props-row wf-editor__props-row--top">
          <span class="wf-editor__props-label">参数 (JSON)</span>
          <NInput
            type="textarea"
            :rows="8"
            v-model:value="paramsDraft"
            placeholder="{}"
            size="small"
            monospace
          />
          <NButton size="tiny" type="primary" @click="applyParams" style="margin-top:4px">应用参数</NButton>
        </div>
        <NButton size="small" type="error" quaternary @click="deleteSelectedNode" style="margin-top:8px">删除节点</NButton>
      </div>
    </div>

    <!-- 校验结果面板 -->
    <div class="wf-editor__validation" v-if="validationResult">
      <div v-if="validationResult.valid" class="wf-editor__val-ok">校验通过</div>
      <div v-else class="wf-editor__val-err">
        <div v-for="e in validationResult.errors" :key="e.code" class="wf-editor__val-item wf-editor__val-item--err">
          ✗ {{ e.message }}
        </div>
      </div>
      <div v-if="validationResult.warnings?.length" class="wf-editor__val-warn">
        <div v-for="w in validationResult.warnings" :key="w.code" class="wf-editor__val-item wf-editor__val-item--warn">
          ⚠ {{ w.message }}
        </div>
      </div>
      <NButton quaternary size="tiny" @click="validationResult = null" style="margin-left:auto">关闭</NButton>
    </div>

    <!-- 运行弹窗 -->
    <NModal v-model:show="showRunModal" preset="card" title="运行工作流" style="width: 500px">
      <NForm label-placement="top">
        <NFormItem label="运行参数 (JSON)">
          <NInput v-model:value="runInput" type="textarea" :rows="6" placeholder='{"start_date":"2026-05-01","end_date":"2026-05-14"}' />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showRunModal = false">取消</NButton>
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
        <NDescriptionsItem label="错误信息" v-if="runResult?.error_message">{{ runResult.error_message }}</NDescriptionsItem>
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
import { ref, computed, watch, onMounted, h, markRaw, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import {
  NButton, NTag, NModal, NForm, NFormItem, NInput, NSpace,
  NDescriptions, NDescriptionsItem, NDataTable, useMessage, useDialog,
} from 'naive-ui'
import {
  getWorkflow, patchWorkflowGraph, validateWorkflow, activateWorkflow,
  startWorkflowRun, listNodes,
} from '@/api/workflow'
import { getNodeMeta } from '@/components/workflow/nodeMeta'
import WorkflowNode from '@/components/workflow/WorkflowNode.vue'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const dialog = useDialog()

const workflow = ref(null)
const nodes = ref([])
const edges = ref([])
const selectedNode = ref(null)
const nodeTypes = ref({ workflowNode: markRaw(WorkflowNode) })
const paramsDraft = ref('{}')
const validationResult = ref(null)
const saving = ref(false)
const validating = ref(false)
const activating = ref(false)
const showRunModal = ref(false)
const showRunResult = ref(false)
const runResult = ref(null)
const runInput = ref('{}')
const running = ref(false)
const availableTypes = ref([])

let nextNodeId = 1

const stepColumns = [
  { title: '节点', key: 'node_id', width: 100 },
  { title: '类型', key: 'node_type', width: 140 },
  { title: '状态', key: 'status', width: 80, render: (row) => h(NTag, { size: 'small', type: row.status === 'completed' ? 'success' : row.status === 'failed' ? 'error' : 'warning' }, () => row.status) },
  { title: '错误', key: 'error_message', ellipsis: { tooltip: true } },
]

function getMeta(type) { return getNodeMeta(type) }

const statusTagType = computed(() => {
  const s = workflow.value?.status
  return { draft: 'default', active: 'success', archived: 'info' }[s] || 'default'
})
const statusLabel = computed(() => {
  const s = workflow.value?.status
  return { draft: '草稿', active: '已启用', archived: '已归档' }[s] || s
})

watch(selectedNode, (node) => {
  if (node?.data?.params) {
    paramsDraft.value = JSON.stringify(node.data.params, null, 2)
  } else {
    paramsDraft.value = '{}'
  }
})

const groupedNodes = computed(() => {
  const groups = {}
  for (const t of availableTypes.value) {
    const m = getMeta(t)
    if (!groups[m.category]) groups[m.category] = []
    groups[m.category].push(t)
  }
  return groups
})

// ── Graph conversion ──

function backendToVueFlow(graph) {
  const vfNodes = (graph.nodes || []).map((n) => ({
    id: n.id,
    type: 'workflowNode',
    position: n.position || { x: 100, y: 100 },
    data: { nodeType: n.type, params: n.params || {}, id: n.id },
  }))
  const vfEdges = (graph.edges || []).map((e) => ({
    id: `${e.from}-${e.to}`,
    source: e.from,
    target: e.to,
    type: 'smoothstep',
    animated: true,
  }))
  return { vfNodes, vfEdges }
}

function vueFlowToBackend() {
  const backendNodes = nodes.value.map((n) => ({
    id: n.id,
    type: n.data.nodeType,
    params: n.data.params || {},
    position: { x: Math.round(n.position?.x || 0), y: Math.round(n.position?.y || 0) },
  }))
  const backendEdges = edges.value
    .filter((e) => e.source && e.target)
    .map((e) => ({ from: e.source, to: e.target }))
  return { nodes: backendNodes, edges: backendEdges }
}

// ── Data loading ──

async function loadWorkflow() {
  const id = route.params.id
  try {
    const data = await getWorkflow(id)
    workflow.value = data
    const graph = data.current_version?.graph || { nodes: [], edges: [] }
    const { vfNodes, vfEdges } = backendToVueFlow(graph)
    nodes.value = vfNodes
    edges.value = vfEdges
    // Track highest numeric id suffix for new node naming
    const ids = vfNodes.map((n) => n.id).filter((id) => id.startsWith('node_'))
    const nums = ids.map((id) => parseInt(id.replace('node_', ''), 10)).filter((n) => !isNaN(n))
    nextNodeId = nums.length ? Math.max(...nums) + 1 : 1
  } catch (e) {
    message.error(e.message || '加载工作流失败')
  }
}

async function loadNodeTypes() {
  try {
    const data = await listNodes()
    availableTypes.value = data.items || []
  } catch {
    // Silently fail — node library will be empty
  }
}

// ── Drag & Drop ──

let dragType = ''

function onDragStart(e, type) {
  dragType = type
  e.dataTransfer.effectAllowed = 'move'
}

function onDrop(e) {
  if (!dragType) return
  const bounds = e.currentTarget.getBoundingClientRect()
  const x = e.clientX - bounds.left
  const y = e.clientY - bounds.top
  const id = `node_${nextNodeId++}`
  nodes.value = [
    ...nodes.value,
    {
      id,
      type: 'workflowNode',
      position: { x: Math.round(x), y: Math.round(y) },
      data: { nodeType: dragType, params: {}, id },
    },
  ]
  dragType = ''
}

// ── Interactions ──

function onNodeClick({ node }) {
  selectedNode.value = node
}

function onConnect(params) {
  const existing = edges.value.find((e) => e.source === params.source && e.target === params.target)
  if (existing) return
  edges.value = [
    ...edges.value,
    {
      id: `${params.source}-${params.target}`,
      source: params.source,
      target: params.target,
      type: 'smoothstep',
      animated: true,
    },
  ]
}

function onEdgesChange(changes) {
  // Vue Flow passes change objects; we just need to handle removals
  for (const c of changes) {
    if (c.type === 'remove') {
      edges.value = edges.value.filter((e) => e.id !== c.id)
    }
  }
}

function onNodesChange(changes) {
  for (const c of changes) {
    if (c.type === 'remove') {
      nodes.value = nodes.value.filter((n) => n.id !== c.id)
      if (selectedNode.value?.id === c.id) selectedNode.value = null
    }
  }
}

function applyParams() {
  if (!selectedNode.value) return
  try {
    const parsed = JSON.parse(paramsDraft.value)
    selectedNode.value.data.params = parsed
    message.success('参数已应用')
  } catch {
    message.error('JSON 格式错误，请修正后再应用')
  }
}

function deleteSelectedNode() {
  if (!selectedNode.value) return
  const id = selectedNode.value.id
  nodes.value = nodes.value.filter((n) => n.id !== id)
  edges.value = edges.value.filter((e) => e.source !== id && e.target !== id)
  selectedNode.value = null
}

// ── Actions ──

async function doSave() {
  saving.value = true
  try {
    const graph = vueFlowToBackend()
    await patchWorkflowGraph(workflow.value.id, graph)
    message.success('保存成功')
    await loadWorkflow()
  } catch (e) {
    message.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function doValidate() {
  validating.value = true
  try {
    const graph = vueFlowToBackend()
    const result = await validateWorkflow(workflow.value.id, graph)
    validationResult.value = result
  } catch (e) {
    message.error(e.message || '校验失败')
  } finally {
    validating.value = false
  }
}

async function doActivate() {
  validating.value = true
  try {
    const graph = vueFlowToBackend()
    const result = await validateWorkflow(workflow.value.id, graph)
    validationResult.value = result
    if (!result.valid) {
      message.error('校验未通过，请修复后再发布')
      return
    }
    const hasWarnings = result.warnings?.length > 0
    const proceed = async () => {
      activating.value = true
      try {
        await patchWorkflowGraph(workflow.value.id, graph, 'publish graph from canvas')
        await loadWorkflow()
        await activateWorkflow(workflow.value.id)
        message.success('发布成功')
        await loadWorkflow()
      } catch (e) {
        message.error(e.message || '发布失败')
      } finally {
        activating.value = false
      }
    }
    if (hasWarnings) {
      dialog.warning({
        title: '校验警告',
        content: result.warnings.map((w) => w.message).join('；'),
        positiveText: '仍然发布',
        negativeText: '取消',
        onPositiveClick: () => proceed(),
      })
    } else {
      await proceed()
    }
  } catch (e) {
    message.error(e.message || '校验失败')
  } finally {
    validating.value = false
  }
}

async function doRun() {
  let input = {}
  try {
    input = JSON.parse(runInput.value)
  } catch {
    message.error('JSON 格式错误')
    return
  }
  running.value = true
  try {
    const result = await startWorkflowRun(workflow.value.id, input)
    showRunModal.value = false
    runResult.value = result
    showRunResult.value = true
  } catch (e) {
    message.error(e.message || '运行失败')
  } finally {
    running.value = false
  }
}

function goBack() {
  router.push({ name: 'workflow-list' })
}

onMounted(() => {
  loadNodeTypes()
  loadWorkflow()
})
</script>

<style scoped>
.wf-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f5f3ee;
}

/* toolbar */
.wf-editor__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #e8e5df;
  background: #fff;
  flex-shrink: 0;
  z-index: 10;
}
.wf-editor__toolbar-left,
.wf-editor__toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.wf-editor__title {
  font-weight: 600;
  font-size: 15px;
}
.wf-editor__ver {
  font-size: 12px;
  color: #909399;
}

/* body layout */
.wf-editor__body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

/* sidebar */
.wf-editor__sidebar {
  width: 200px;
  border-right: 1px solid #e8e5df;
  background: #fff;
  overflow-y: auto;
  padding: 12px;
  flex-shrink: 0;
}
.wf-editor__sidebar-title {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 10px;
  color: #606266;
}
.wf-editor__node-cat {
  font-size: 11px;
  color: #909399;
  margin: 10px 0 4px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.wf-editor__node-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  margin-bottom: 3px;
  border-radius: 4px;
  font-size: 12px;
  cursor: grab;
  background: #faf9f5;
  border: 1px solid #ece9e1;
  transition: background .1s;
}
.wf-editor__node-item:hover {
  background: #f0ede4;
}
.wf-editor__node-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* canvas */
.wf-editor__canvas {
  flex: 1;
  min-width: 0;
}

/* props panel */
.wf-editor__props {
  width: 240px;
  border-left: 1px solid #e8e5df;
  background: #fff;
  padding: 12px;
  overflow-y: auto;
  flex-shrink: 0;
}
.wf-editor__props-title {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 12px;
  color: #606266;
}
.wf-editor__props-row {
  margin-bottom: 8px;
  font-size: 12px;
}
.wf-editor__props-row--top {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.wf-editor__props-label {
  display: inline-block;
  width: 50px;
  color: #909399;
  font-size: 11px;
  flex-shrink: 0;
}

/* validation bar */
.wf-editor__validation {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 16px;
  background: #fff;
  border-top: 1px solid #e8e5df;
  font-size: 12px;
  flex-shrink: 0;
}
.wf-editor__val-ok {
  color: #67c23a;
  font-weight: 600;
}
.wf-editor__val-item {
  margin-bottom: 2px;
}
.wf-editor__val-item--err {
  color: #f56c6c;
}
.wf-editor__val-item--warn {
  color: #e6a23c;
}
</style>
