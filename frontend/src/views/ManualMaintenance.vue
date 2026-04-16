<template>
  <div class="manual-maint">
    <!-- 信息栏 -->
    <div class="info-bar">
      <span>批次号：<strong>{{ batchCode }}</strong></span>
      <span>异常行数：<strong>{{ abnormalRows.length }}</strong></span>
    </div>

    <!-- 异常行可编辑表格 -->
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th><th>法人</th><th>账户</th><th>日期</th><th>摘要</th>
            <th>对方</th><th>收入</th><th>支出</th><th>异常代码</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in abnormalRows" :key="r._row_no" class="abnormal-row">
            <td>{{ r._row_no }}</td>
            <td>
              <select v-model="r._fix_entity_id" class="cell-input">
                <option :value="null">未匹配</option>
                <option v-for="e in entityList" :key="e.entity_id" :value="e.entity_id">{{ e.entity_name }}</option>
              </select>
            </td>
            <td>
              <select v-model="r._fix_account_id" class="cell-input">
                <option :value="null">未匹配</option>
                <optgroup v-for="g in entityGroups" :key="g.entity_id" :label="g.entity_name">
                  <option v-for="a in g.accounts" :key="a.id" :value="a.id">{{ a.account_code }} {{ a.account_alias }}</option>
                </optgroup>
              </select>
            </td>
            <td>{{ r.business_date || '-' }}</td>
            <td>{{ r.summary_text || '-' }}</td>
            <td>{{ r.counterparty_name || '-' }}</td>
            <td class="money">{{ fmtAmt(r.income_amount) }}</td>
            <td class="money">{{ fmtAmt(r.expense_amount) }}</td>
            <td><span class="badge err">{{ r.abnormal_code }}</span></td>
          </tr>
          <tr v-if="!abnormalRows.length"><td colspan="9" class="empty">无异常行</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 底部操作 -->
    <div class="bottom-bar">
      <button class="btn btn-secondary" @click="goBack">返回预览</button>
      <button class="btn btn-primary" @click="doFix" :disabled="fixing">
        {{ fixing ? '提交中...' : '应用修复并提交' }}
      </button>
    </div>

    <div class="result-msg" v-if="fixResult">
      <div class="ok-box">修复提交成功！已提交 {{ fixResult.committed_count }} 条。</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as api from '@/api/manual'
import * as master from '@/api/master'

const route = useRoute()
const router = useRouter()

const batchCode = ref(route.query.batch_code || '')
const abnormalRows = ref([])
const entityList = ref([])
const fixing = ref(false)
const fixResult = ref(null)

const entityGroups = computed(() => {
  const groups = {}
  for (const e of entityList.value) {
    if (!groups[e.entity_id]) groups[e.entity_id] = { entity_id: e.entity_id, entity_name: e.entity_name, accounts: [] }
    groups[e.entity_id].accounts.push(...e.accounts)
  }
  return Object.values(groups)
})

async function loadData() {
  try {
    const tree = await master.getAccountsTree()
    entityList.value = tree || []
  } catch (e) { console.error(e) }

  if (!batchCode.value) return
  try {
    const result = await api.previewManual({ batch_code: batchCode.value })
    abnormalRows.value = (result.abnormal_rows || []).map(r => ({
      ...r,
      _fix_entity_id: r._entity_id || null,
      _fix_account_id: r._account_id || null,
    }))
  } catch (e) { alert('加载失败: ' + (e.message || e)) }
}

async function doFix() {
  fixing.value = true
  const fixes = abnormalRows.value
    .filter(r => r._fix_entity_id || r._fix_account_id)
    .map(r => ({
      _row_no: r._row_no,
      entity_id: r._fix_entity_id,
      account_id: r._fix_account_id,
      entity_name: entityList.value.find(e => e.entity_id === r._fix_entity_id)?.entity_name || '',
      account_name: '',
    }))

  try {
    const result = await api.commitManual({ batch_code: batchCode.value, fixes })
    fixResult.value = result
  } catch (e) { alert('修复失败: ' + (e.message || e)) }
  fixing.value = false
}

function goBack() {
  router.push({ path: '/upload-preview', query: { batch_code: batchCode.value } })
}

function fmtAmt(v) {
  if (v == null) return '-'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

onMounted(loadData)
</script>

<style scoped>
.manual-maint { display: flex; flex-direction: column; height: calc(100vh - 80px); }

.info-bar {
  display: flex; gap: 16px; padding: 10px 14px;
  background: rgba(251,250,247,0.95); border: 1px solid var(--line);
  border-radius: var(--radius); margin-bottom: 12px; font-size: 14px;
}
.info-bar strong { color: #3f5b3d; }

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
.data-table td { padding: 5px 8px; border-bottom: 1px solid #f0ede6; }
.data-table tr.abnormal-row { background: #fef9f0; }
.data-table tr.abnormal-row:hover { background: #fdf3e3; }
.data-table .money { text-align: right; font-weight: 600; color: #3f5b3d; }
.data-table .empty { text-align: center; color: var(--muted); padding: 30px; font-size: 14px; }

.cell-input {
  width: 100%; border: 1px solid #d0c9bc; background: #fff;
  padding: 4px 6px; font-size: 12px; border-radius: 6px;
}
select.cell-input { min-width: 100px; }

.badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.badge.err { background: #f5ece5; color: #8a6e52; }

.bottom-bar { display: flex; gap: 8px; padding: 10px 0; }

.result-msg { margin-top: 10px; }
.ok-box { background: #edf4ea; border: 1px solid #d9e6d4; border-radius: 12px; padding: 14px; color: #3f5b3d; font-size: 14px; }
</style>
