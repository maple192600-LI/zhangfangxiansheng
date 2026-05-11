<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>异常行修复</h3>
        <span>修正未匹配的单位或账户</span>
      </div>
      <div class="filters-bar">
        <span style="font-size:var(--font-size-sm)">批次号：<strong>{{ batchCode }}</strong></span>
        <span style="font-size:var(--font-size-sm)">异常行数：<strong style="color:var(--warn)">{{ abnormalRows.length }}</strong></span>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary" @click="goBack">返回预览</button>
          <button class="btn btn-primary" @click="doFix" :disabled="fixing">{{ fixing ? '提交中...' : '应用修复并提交' }}</button>
        </div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th><th>单位简称</th><th>账户名称</th><th>日期</th><th>摘要</th>
              <th>对方</th><th>收入</th><th>支出</th><th>异常代码</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in abnormalRows" :key="r._row_no" class="abnormal-row">
              <td>{{ r._row_no }}</td>
              <td>
                <NSelect v-model:value="r._fix_entity_id" :options="entityFixOptions" placeholder="未匹配" clearable size="tiny" />
              </td>
              <td>
                <NSelect v-model:value="r._fix_account_id" :options="accountFixOptions" placeholder="未匹配" clearable size="tiny" />
              </td>
              <td>{{ r.business_date || '-' }}</td>
              <td>{{ r.summary_text || '-' }}</td>
              <td>{{ r.counterparty_name || '-' }}</td>
              <td class="money">{{ fmtAmt(r.income_amount) }}</td>
              <td class="money">{{ fmtAmt(r.expense_amount) }}</td>
              <td><span class="tag tag-warn">{{ r.abnormal_code }}</span></td>
            </tr>
            <tr v-if="!abnormalRows.length">
              <td colspan="9" style="text-align:center;color:var(--muted);padding:30px">无异常行</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="fixResult" style="margin-top:var(--space-md)">
        <div style="background:var(--ok-bg);border:1px solid var(--ok-border);border-radius:var(--radius-sm);padding:var(--space-md);color:var(--ok-text)">
          修复提交成功！已提交 {{ fixResult.committed_count }} 条。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NSelect } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'
import * as api from '@/api/manual'
import * as master from '@/api/master'
import { fmtAmt } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const batchCode = ref(route.query.batch_code || '')
const abnormalRows = ref([])
const entityList = ref([])
const entityFixOptions = computed(() => entityList.value.map(e => ({ label: e.entity_name, value: e.entity_id })))
const accountFixOptions = computed(() => {
  return entityGroups.value.map(g => ({
    type: 'group',
    label: g.entity_name,
    key: g.entity_id,
    children: g.accounts.map(a => ({ label: `${a.account_code} ${a.account_alias}`, value: a.id }))
  }))
})
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

onMounted(loadData)
</script>

<style scoped>
@import './common.css';

/* 页面特有样式 */
.table-wrap {
  overflow: auto;
  max-height: calc(100vh - 260px);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}

tr.abnormal-row { background: #fef9f0; }
tr.abnormal-row:hover { background: #fdf3e3; }

.cell-input {
  width: 100%; border: 1px solid #d0c9bc; background: #fff;
  padding: 4px 6px; font-size: var(--font-size-xs); border-radius: var(--radius-sm);
}
select.cell-input { min-width: 100px; }
</style>
