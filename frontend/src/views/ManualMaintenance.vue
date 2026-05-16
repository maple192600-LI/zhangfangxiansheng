<template>
  <div>
    <div class="section table-workspace-page">
      <div class="section-title">
        <h3>异常行修复</h3>
        <span>修正未匹配的单位或账户</span>
      </div>
      <div class="filters-bar">
        <span style="font-size:var(--font-size-sm)">批次号：<strong>{{ batchCode }}</strong></span>
        <span style="font-size:var(--font-size-sm)">异常行数：<strong style="color:var(--warn)">{{ abnormalRows.length }}</strong></span>
        <div style="flex:1"></div>
        <div class="btn-row">
          <NButton secondary @click="goBack">返回预览</NButton>
          <NButton type="primary" @click="doFix" :disabled="fixing">{{ fixing ? '提交中...' : '应用修复并提交' }}</NButton>
        </div>
      </div>

      <div class="table-workspace-main">
        <AdvancedDataTable
          :columns="tabulatorColumns"
          :data="abnormalRows"
          :rowKey="'_row_no'"
          :pagination="false"
          :showToolbar="true"
          :editable="true"
          :editMode="'cell'"
          :tableKey="'manual-maintenance'"
          :rowClass="rowClassFn"
          :fillParent="true"
          @cellEdited="onCellEdited"
          @tableReady="onTableReady"
        />
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
import { NButton } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'
import * as api from '@/api/manual'
import * as master from '@/api/master'
import { fmtAmt } from '@/utils/format'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'

const route = useRoute()
const router = useRouter()

const batchCode = ref(route.query.batch_code || '')
const abnormalRows = ref([])
const entityList = ref([])
const dirtyRowNos = ref(new Set())
const fixing = ref(false)
const fixResult = ref(null)

const entityOptions = computed(() =>
  entityList.value.map(e => ({ value: e.entity_id, label: e.entity_name }))
)

const flatAccountOptions = computed(() => {
  const opts = []
  for (const e of entityList.value) {
    for (const a of e.accounts || []) {
      opts.push({
        value: a.id,
        label: `${a.account_code} ${a.account_alias || ''}`,
        group: e.entity_name,
      })
    }
  }
  return opts
})

const accountOptionValues = computed(() => flatAccountOptions.value.map(a => a.label))
const accountLabelToId = computed(() => {
  const m = {}
  for (const a of flatAccountOptions.value) {
    m[a.label] = a.value
    m[a.value] = a.value
  }
  return m
})

const tabulatorColumns = computed(() => [
  { field: '_row_no', title: '#', width: 50, headerSort: false, hozAlign: 'center' },
  {
    field: '_fix_entity_id',
    title: '单位简称',
    minWidth: 130,
    editor: 'list',
    editorParams: {
      values: entityOptions.value.map(o => o.label),
      autocomplete: true,
      allowEmpty: true,
      listOnEmpty: true,
      clearable: true,
      defaultValue: '',
    },
    formatter: (cell) => {
      const val = cell.getValue()
      if (!val) return '<span style="color:var(--muted)">未匹配</span>'
      const found = entityOptions.value.find(o => o.value === val)
      if (found) return found.label
      return val
    },
  },
  {
    field: '_fix_account_id',
    title: '账户名称',
    minWidth: 160,
    editor: 'list',
    editorParams: {
      values: accountOptionValues.value,
      autocomplete: true,
      allowEmpty: true,
      listOnEmpty: true,
      clearable: true,
      defaultValue: '',
    },
    formatter: (cell) => {
      const val = cell.getValue()
      if (!val) return '<span style="color:var(--muted)">未匹配</span>'
      const found = flatAccountOptions.value.find(o => o.value === val || o.label === val)
      if (found) return found.label
      return val
    },
    tooltip: '输入账户编码或名称搜索',
  },
  { field: 'business_date', title: '日期', width: 110 },
  { field: 'summary_text', title: '摘要', minWidth: 120 },
  { field: 'counterparty_name', title: '对方', width: 100 },
  {
    field: 'income_amount',
    title: '收入',
    width: 100,
    hozAlign: 'right',
    formatter: (cell) => fmtAmt(cell.getValue()),
  },
  {
    field: 'expense_amount',
    title: '支出',
    width: 100,
    hozAlign: 'right',
    formatter: (cell) => fmtAmt(cell.getValue()),
  },
  {
    field: 'abnormal_code',
    title: '异常代码',
    width: 90,
    hozAlign: 'center',
    formatter: (cell) => `<span class="tabulator-tag tabulator-tag-orange">${cell.getValue() || ''}</span>`,
  },
])

function rowClassFn(rowData) {
  return dirtyRowNos.value.has(rowData._row_no) ? 'adt-row-dirty' : ''
}

function onCellEdited({ field, value, rowData }) {
  const rowNo = rowData?._row_no
  if (rowNo == null) return

  if (field === '_fix_entity_id') {
    const selected = entityOptions.value.find(o => o.label === value)
    if (selected) {
      const row = abnormalRows.value.find(r => r._row_no === rowNo)
      if (row) row._fix_entity_id = selected.value
    }
  }

  if (field === '_fix_account_id') {
    const resolved = accountLabelToId.value[value]
    if (resolved) {
      const row = abnormalRows.value.find(r => r._row_no === rowNo)
      if (row) row._fix_account_id = resolved
    }
  }

  dirtyRowNos.value = new Set([...dirtyRowNos.value, rowNo])
}

function onTableReady() {}

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
</style>
