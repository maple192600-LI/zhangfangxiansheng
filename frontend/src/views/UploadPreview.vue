<template>
  <div class="upload-preview">
    <!-- 指标条 -->
    <div class="metric-bar">
      <div class="metric"><span class="label">批次号</span><strong>{{ batchCode }}</strong></div>
      <div class="metric"><span class="label">总行数</span><strong>{{ total }}</strong></div>
      <div class="metric good"><span class="label">有效</span><strong>{{ validCount }}</strong></div>
      <div class="metric warn"><span class="label">异常</span><strong>{{ abnormalCount }}</strong></div>
    </div>

    <!-- Tab -->
    <div class="tab-bar">
      <button class="btn" :class="activeTab==='valid'?'btn-primary':'btn-secondary'" @click="activeTab='valid'">有效行 ({{ validCount }})</button>
      <button class="btn" :class="activeTab==='abnormal'?'btn-primary':'btn-secondary'" @click="activeTab='abnormal'" v-if="abnormalCount">异常行 ({{ abnormalCount }})</button>
    </div>

    <!-- 有效行表格 -->
    <div class="table-wrap" v-if="activeTab==='valid'">
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th><th>法人</th><th>账户</th><th>日期</th><th>摘要</th><th>对方</th>
            <th>收入</th><th>支出</th><th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in validRows" :key="r._row_no">
            <td>{{ r._row_no }}</td>
            <td>{{ r._entity_name || '-' }}</td>
            <td>{{ r._account_name || '-' }}</td>
            <td>{{ r.business_date }}</td>
            <td>{{ r.summary_text }}</td>
            <td>{{ r.counterparty_name || '-' }}</td>
            <td class="money">{{ fmtAmt(r.income_amount) }}</td>
            <td class="money">{{ fmtAmt(r.expense_amount) }}</td>
            <td><span class="badge ok">有效</span></td>
          </tr>
          <tr v-if="!validRows.length"><td colspan="9" class="empty">暂无有效行</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 异常行表格 -->
    <div class="table-wrap" v-if="activeTab==='abnormal'">
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th><th>法人键</th><th>账户键</th><th>日期</th><th>摘要</th>
            <th>收入</th><th>支出</th><th>异常代码</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in abnormalRows" :key="r._row_no" class="abnormal-row">
            <td>{{ r._row_no }}</td>
            <td>{{ r.entity_match_key || '-' }}</td>
            <td>{{ r.account_match_key || '-' }}</td>
            <td>{{ r.business_date || '-' }}</td>
            <td>{{ r.summary_text || '-' }}</td>
            <td class="money">{{ fmtAmt(r.income_amount) }}</td>
            <td class="money">{{ fmtAmt(r.expense_amount) }}</td>
            <td><span class="badge err">{{ r.abnormal_code }}</span></td>
            <td>
              <button class="btn btn-secondary btn-sm" @click="goFix(r._row_no)">修复</button>
            </td>
          </tr>
          <tr v-if="!abnormalRows.length"><td colspan="9" class="empty">暂无异常行</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 底部操作 -->
    <div class="bottom-bar">
      <button class="btn btn-secondary" @click="$router.push('/manual-flow')">返回录入</button>
      <button class="btn btn-primary" @click="doCommit" :disabled="committing">
        {{ committing ? '提交中...' : '提交有效行到基础数据' }}
      </button>
    </div>

    <!-- 提交结果 -->
    <div class="result-msg" v-if="commitResult">
      <div class="ok-box" v-if="commitResult.committed_count > 0">
        提交成功！已写入 {{ commitResult.committed_count }} 条资金事件。
        <span v-if="commitResult.abnormal_count > 0">仍有 {{ commitResult.abnormal_count }} 条异常未处理。</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as api from '@/api/manual'

const route = useRoute()
const router = useRouter()

const batchCode = ref(route.query.batch_code || '')
const activeTab = ref('valid')
const validRows = ref([])
const abnormalRows = ref([])
const committing = ref(false)
const commitResult = ref(null)

const total = computed(() => validRows.value.length + abnormalRows.value.length)
const validCount = computed(() => validRows.value.length)
const abnormalCount = computed(() => abnormalRows.value.length)

async function loadPreview() {
  if (!batchCode.value) return
  try {
    const result = await api.previewManual({ batch_code: batchCode.value })
    validRows.value = result.parsed_rows || []
    abnormalRows.value = result.abnormal_rows || []
    if (abnormalRows.value.length) activeTab.value = 'abnormal'
  } catch (e) { alert('加载预览失败: ' + (e.message || e)) }
}

async function doCommit() {
  committing.value = true
  try {
    const result = await api.commitManual({ batch_code: batchCode.value })
    commitResult.value = result
  } catch (e) { alert('提交失败: ' + (e.message || e)) }
  committing.value = false
}

function goFix(rowNo) {
  router.push({ path: '/manual-maintenance', query: { batch_code: batchCode.value, row_no: rowNo } })
}

function fmtAmt(v) {
  if (v == null) return '-'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

onMounted(loadPreview)
</script>

<style scoped>
.upload-preview { display: flex; flex-direction: column; height: calc(100vh - 80px); }

.metric-bar {
  display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;
}
.metric {
  background: #fff; border: 1px solid #e7e0d5; border-radius: 12px;
  padding: 10px 16px; display: flex; flex-direction: column; min-width: 90px;
}
.metric .label { font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.metric strong { font-size: 20px; }
.metric.good strong { color: #3f5b3d; }
.metric.warn strong { color: #8a6e52; }

.tab-bar { display: flex; gap: 8px; margin-bottom: 10px; }

.table-wrap {
  flex: 1; overflow: auto; background: #fff;
  border: 1px solid var(--line); border-radius: var(--radius);
}

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
.data-table th {
  position: sticky; top: 0; z-index: 2; background: #f5f2eb;
  text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--line);
  color: #5b635e; font-weight: 600; font-size: 12px;
}
.data-table td { padding: 7px 10px; border-bottom: 1px solid #f0ede6; }
.data-table tr:hover { background: #faf8f3; }
.data-table tr.abnormal-row { background: #fef9f0; }
.data-table .money { text-align: right; font-weight: 600; color: #3f5b3d; }
.data-table .empty { text-align: center; color: var(--muted); padding: 30px; font-size: 14px; }

.badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.badge.ok { background: #edf4ea; color: #3f5b3d; }
.badge.err { background: #f5ece5; color: #8a6e52; }

.bottom-bar { display: flex; gap: 8px; padding: 10px 0; }

.result-msg { margin-top: 10px; }
.ok-box { background: #edf4ea; border: 1px solid #d9e6d4; border-radius: 12px; padding: 14px; color: #3f5b3d; font-size: 14px; }

.btn-sm { padding: 4px 8px; font-size: 12px; }
</style>
