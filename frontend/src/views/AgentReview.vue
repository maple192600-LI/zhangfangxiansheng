<template>
  <div class="review-page">
    <div class="review-header">
      <div>
        <p class="eyebrow">产物审核</p>
        <h2>{{ title }}</h2>
      </div>
      <div class="confidence" :class="confidenceClass">
        <span>{{ confidenceLabel }}</span>
        <strong>{{ confidencePercent }}</strong>
      </div>
    </div>

    <div v-if="loading" class="panel muted-panel">正在读取草稿...</div>
    <div v-else-if="!artifact" class="panel muted-panel">未找到 artifact 草稿</div>

    <template v-else>
      <div class="summary-grid">
        <div class="summary-item">
          <label>名称</label>
          <strong>{{ artifact.name }}</strong>
        </div>
        <div class="summary-item">
          <label>类型</label>
          <strong>{{ typeLabel }}</strong>
        </div>
        <div class="summary-item">
          <label>状态</label>
          <strong>{{ statusText }}</strong>
        </div>
        <div class="summary-item">
          <label>版本</label>
          <strong>v{{ artifact.version || 1 }}</strong>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">样本校验</div>
        <div class="check-grid">
          <div v-for="item in checkItems" :key="item.key" class="check-item">
            <label>{{ item.label }}</label>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">{{ artifactType === 'parser' ? 'Parser 代码' : 'Rule 绑定' }}</div>
        <pre class="code-block">{{ readonlyBody }}</pre>
      </div>

      <div v-if="resultMessage" class="panel result-panel">
        <strong>{{ resultMessage }}</strong>
        <span v-if="commitResult?.inserted_rows != null">入库 {{ commitResult.inserted_rows }} 行</span>
        <span v-if="downloadUrl">报表已生成，可在下载地址查看。</span>
      </div>

      <div class="action-bar">
        <NButton secondary @click="goBack">返回</NButton>
        <NButton type="primary" :disabled="approving || artifact.status === 'active'" @click="approve">
          {{ approving ? '正在接受...' : artifact.status === 'active' ? '已接受' : '接受并继续' }}
        </NButton>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { NButton } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'
import * as artifacts from '@/api/artifacts'
import * as bank from '@/api/bank'
import * as manual from '@/api/manual'

const route = useRoute()
const router = useRouter()

const artifact = ref(null)
const loading = ref(false)
const approving = ref(false)
const resultMessage = ref('')
const commitResult = ref(null)
const downloadUrl = ref('')

const artifactType = computed(() => route.params.type)
const artifactId = computed(() => Number(route.params.id))
const flow = computed(() => route.query.flow || '')

const title = computed(() => artifactType.value === 'parser' ? 'Parser 草稿审核' : 'Rule 草稿审核')
const typeLabel = computed(() => artifactType.value === 'parser' ? `${artifact.value?.kind || ''} parser` : 'template rule')
const statusText = computed(() => artifact.value?.status === 'active' ? '已接受' : '待审核')
const confidence = computed(() => Number(artifact.value?.confidence ?? 0))
const confidencePercent = computed(() => `${Math.round(confidence.value * 100)}%`)
const confidenceClass = computed(() => confidence.value >= 0.85 ? 'high' : confidence.value >= 0.7 ? 'medium' : 'low')
const confidenceLabel = computed(() => confidence.value >= 0.85 ? '建议接受' : confidence.value >= 0.7 ? '需要复核' : '谨慎处理')

const checkItems = computed(() => {
  const log = artifact.value?.sample_check_log || {}
  if (artifactType.value === 'parser') {
    return [
      { key: 'sample_rows', label: '样本行数', value: log.sample_rows ?? 0 },
      { key: 'parsed_rows', label: '解析行数', value: log.parsed_rows ?? 0 },
      { key: 'canonical_violations', label: '12列违规', value: log.canonical_violations ?? 0 },
      { key: 'amount_sum_in', label: '收入小计', value: log.amount_sum_in ?? '0.00' },
      { key: 'amount_sum_out', label: '支出小计', value: log.amount_sum_out ?? '0.00' },
    ]
  }
  return [
    { key: 'placeholder_bound', label: '已绑定', value: log.placeholder_bound ?? 0 },
    { key: 'placeholder_unbound', label: '未绑定', value: log.placeholder_unbound ?? 0 },
    { key: 'placeholder_extra', label: '额外占位符', value: log.placeholder_extra ?? 0 },
    { key: 'amount_match_rate', label: '金额匹配率', value: log.amount_match_rate ?? '-' },
  ]
})

const readonlyBody = computed(() => {
  if (!artifact.value) return ''
  if (artifactType.value === 'parser') return artifact.value.code || ''
  return JSON.stringify({
    placeholder_bindings: artifact.value.placeholder_bindings || {},
    loop_config: artifact.value.loop_config || {},
  }, null, 2)
})

async function loadArtifact() {
  loading.value = true
  try {
    artifact.value = artifactType.value === 'parser'
      ? await artifacts.getParserArtifact(artifactId.value)
      : await artifacts.getRuleArtifact(artifactId.value)
  } catch (e) {
    alert(e.message || '读取草稿失败')
  } finally {
    loading.value = false
  }
}

async function approve() {
  approving.value = true
  resultMessage.value = ''
  commitResult.value = null
  try {
    if (artifactType.value === 'parser') {
      await artifacts.approveParserArtifact(artifactId.value)
      if (flow.value === 'bank' && route.query.batch_code) {
        commitResult.value = await bank.commitBankImport({
          batch_code: route.query.batch_code,
          parser_artifact_id: artifactId.value,
        })
        resultMessage.value = '已接受 Parser，银行流水已入库。'
      } else if (flow.value === 'manual' && route.query.batch_code) {
        commitResult.value = await manual.commitManual({
          batch_code: route.query.batch_code,
          parser_artifact_id: artifactId.value,
        })
        resultMessage.value = '已接受 Parser，手工 Excel 流水已入库。'
      } else {
        resultMessage.value = '已接受 Parser。'
      }
    } else {
      await artifacts.approveRuleArtifact(artifactId.value)
      resultMessage.value = '已接受 Rule，后续生成报表将走 Runtime。'
    }
    await loadArtifact()
  } catch (e) {
    alert(e.message || '接受失败')
  } finally {
    approving.value = false
  }
}

function goBack() {
  if (flow.value === 'bank') router.push('/bank-import')
  else if (flow.value === 'manual') router.push('/manual-flow')
  else router.push('/data/report-tpl')
}

onMounted(loadArtifact)
</script>

<style scoped>
@import './common.css';

.review-page { display: flex; flex-direction: column; gap: 14px; }
.review-header {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  gap: 16px;
}
.review-header h2 { margin: 0; font-size: 20px; color: #2d2a26; }
.eyebrow { margin: 0 0 4px; font-size: 12px; color: var(--muted); }
.confidence {
  min-width: 132px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  background: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-end;
}
.confidence span { font-size: 12px; color: var(--muted); }
.confidence strong { font-size: 22px; }
.confidence.high strong { color: var(--green); }
.confidence.medium strong { color: #9a7a2f; }
.confidence.low strong { color: #b65c3b; }
.summary-grid, .check-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.summary-item, .check-item {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: var(--radius-sm);
  padding: 12px;
}
.summary-item label, .check-item label {
  display: block;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 4px;
}
.summary-item strong, .check-item strong { font-size: 14px; color: #2d2a26; }
.panel {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: var(--radius-sm);
  padding: 14px;
}
.muted-panel { color: var(--muted); }
.panel-title { font-weight: 600; margin-bottom: 10px; color: #3f4d42; }
.code-block {
  max-height: 420px;
  overflow: auto;
  margin: 0;
  padding: 12px;
  border: 1px solid #ede6dc;
  background: #faf8f3;
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.result-panel {
  display: flex;
  gap: 14px;
  align-items: center;
  background: var(--ok-bg);
  border-color: var(--ok-border);
}
.action-bar { display: flex; justify-content: flex-end; gap: 10px; }
@media (max-width: 900px) {
  .summary-grid, .check-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .review-header { flex-direction: column; }
  .confidence { align-items: flex-start; }
}
</style>
