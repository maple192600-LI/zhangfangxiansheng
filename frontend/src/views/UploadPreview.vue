<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>流水预览</h3>
        <span>确认提交前检查数据质量</span>
      </div>

      <!-- 指标条 -->
      <div class="metric-strip" style="margin-bottom:var(--space-lg)">
        <div class="metric">
          <div class="label">批次号</div>
          <div class="value" style="font-size:var(--font-size-md)">{{ batchCode }}</div>
        </div>
        <div class="metric">
          <div class="label">总行数</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="metric">
          <div class="label">有效</div>
          <div class="value text-green">{{ validCount }}</div>
        </div>
        <div class="metric">
          <div class="label">异常</div>
          <div class="value text-warn">{{ abnormalCount }}</div>
        </div>
      </div>

      <!-- Tab -->
      <div class="filters-bar">
        <button class="btn" :class="activeTab==='valid'?'btn-primary':'btn-secondary'" @click="activeTab='valid'">有效行 ({{ validCount }})</button>
        <button class="btn" :class="activeTab==='abnormal'?'btn-primary':'btn-secondary'" @click="activeTab='abnormal'" v-if="abnormalCount">异常行 ({{ abnormalCount }})</button>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary" @click="$router.push('/manual-flow')">返回录入</button>
          <button class="btn btn-primary" @click="doCommit" :disabled="committing">{{ committing ? '提交中...' : '提交有效行到基础数据' }}</button>
        </div>
      </div>

      <!-- 有效行表格 -->
      <div class="table-wrap" v-if="activeTab==='valid'">
        <table>
          <thead>
            <tr>
              <th>#</th><th>单位简称</th><th>账户名称</th><th>日期</th><th>摘要</th><th>对方</th>
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
              <td class="money inc">{{ fmtAmt(r.income_amount) }}</td>
              <td class="money exp">{{ fmtAmt(r.expense_amount) }}</td>
              <td><span class="tag tag-green">有效</span></td>
            </tr>
            <tr v-if="!validRows.length"><td colspan="9" style="text-align:center;color:var(--muted);padding:30px">暂无有效行</td></tr>
          </tbody>
        </table>
      </div>

      <!-- 异常行表格 -->
      <div class="table-wrap" v-if="activeTab==='abnormal'">
        <table>
          <thead>
            <tr>
              <th>#</th><th>单位编码</th><th>账户编号</th><th>日期</th><th>摘要</th>
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
              <td class="money inc">{{ fmtAmt(r.income_amount) }}</td>
              <td class="money exp">{{ fmtAmt(r.expense_amount) }}</td>
              <td><span class="tag tag-warn">{{ r.abnormal_code }}</span></td>
              <td>
                <button class="btn btn-secondary btn-sm" @click="goFix(r._row_no)">修复</button>
              </td>
            </tr>
            <tr v-if="!abnormalRows.length"><td colspan="9" style="text-align:center;color:var(--muted);padding:30px">暂无异常行</td></tr>
          </tbody>
        </table>
      </div>

      <!-- 提交结果 -->
      <div v-if="commitResult" style="margin-top:var(--space-md)">
        <div style="background:var(--ok-bg);border:1px solid var(--ok-border);border-radius:var(--radius-sm);padding:var(--space-md);color:var(--ok-text)" v-if="commitResult.committed_count > 0">
          提交成功！已写入 {{ commitResult.committed_count }} 条资金事件。
          <span v-if="commitResult.abnormal_count > 0">仍有 {{ commitResult.abnormal_count }} 条异常未处理。</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as api from '@/api/manual'
import { fmtAmt } from '@/utils/format'

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

onMounted(loadPreview)
</script>

<style scoped>
@import './common.css';

/* 页面特有样式 */
.table-wrap {
  overflow: auto;
  max-height: calc(100vh - 360px);
}

tr.abnormal-row { background: #fef9f0; }
</style>
