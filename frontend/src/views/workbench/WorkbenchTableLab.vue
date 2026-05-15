<template>
  <div class="tlab">
    <div class="section">
      <div class="section-title">
        <h3>Table Lab</h3>
        <span>工作台高级表格底座技术验证（内部页面，非正式功能）</span>
      </div>

      <!-- 技术验证声明 -->
      <div class="tlab-notice">
        <strong>内部技术验证页</strong> — 所有数据均为浏览器端模拟数据。
        DuckDB 仅做浏览器端临时分析，<strong>不写入任何正式数据库</strong>，
        查询结果<strong>不代表正式报表结论</strong>。
      </div>

      <!-- 数据量控制 -->
      <div class="tlab-controls">
        <span class="tlab-controls-label">数据行数：</span>
        <NButton
          v-for="size in [50, 5000, 50000]"
          :key="size"
          size="small"
          :type="rowCount === size ? 'primary' : 'default'"
          @click="changeRowSize(size)"
        >
          {{ size.toLocaleString() }}
        </NButton>
        <span class="tlab-controls-info">当前 {{ rows.length.toLocaleString() }} 行</span>
      </div>

      <!-- 主表格 -->
      <div class="tlab-table-section">
        <h4 class="tlab-subtitle">流水预览 (Tabulator)</h4>
        <AdvancedDataTable
          :columns="tableColumns"
          :data="rows"
          height="400px"
          :pagination="true"
          :pagination-size="50"
          :enable-column-resize="true"
          @rowClick="(row) => console.log('[TableLab] rowClick', row)"
          @tableReady="() => console.log('[TableLab] tableReady')"
        />
      </div>

      <!-- DuckDB 控制区 -->
      <div class="tlab-duckdb-section">
        <h4 class="tlab-subtitle">DuckDB 临时分析</h4>

        <div class="tlab-duckdb-controls">
          <NButton
            v-if="dbStatus === 'idle'"
            type="primary"
            size="small"
            @click="doInitDuckDB"
          >
            启用 DuckDB 分析
          </NButton>
          <NButton
            v-if="dbStatus === 'initializing'"
            size="small"
            loading
          >
            初始化中...
          </NButton>
          <NButton
            v-if="dbStatus === 'ready'"
            size="small"
            @click="doCloseDuckDB"
            type="warning"
          >
            关闭 DuckDB
          </NButton>

          <NTag
            :type="dbStatus === 'ready' ? 'success' : dbStatus === 'initializing' ? 'warning' : 'default'"
            size="small"
            style="margin-left: 8px"
          >
            {{ { idle: '未启用', initializing: '初始化中', ready: '就绪' }[dbStatus] || '未启用' }}
          </NTag>
        </div>

        <!-- 预设查询 -->
        <div v-if="dbStatus === 'ready'" class="tlab-presets">
          <span class="tlab-controls-label">预设查询：</span>
          <NButton
            v-for="p in presets"
            :key="p.key"
            size="small"
            @click="runPreset(p)"
            :loading="querying === p.key"
          >
            {{ p.label }}
          </NButton>
        </div>

        <!-- 性能指标 -->
        <div v-if="perfMetrics.length" class="tlab-metrics">
          <div v-for="m in perfMetrics" :key="m.label" class="tlab-metric-item">
            <span class="tlab-metric-label">{{ m.label }}</span>
            <span class="tlab-metric-value" :class="m.cls || ''">{{ m.value }}</span>
          </div>
        </div>

        <!-- 查询错误 -->
        <div v-if="queryError" class="tlab-error">
          {{ queryError }}
        </div>

        <!-- 查询结果 -->
        <div v-if="queryResultColumns.length" class="tlab-query-result">
          <h4 class="tlab-subtitle">查询结果（{{ queryResultRows.length.toLocaleString() }} 行）</h4>
          <AdvancedDataTable
            :columns="queryDisplayColumns"
            :data="queryResultRows"
            height="300px"
            :pagination="true"
            :pagination-size="50"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'
import { generateRows } from './mockTransactionRows.js'
import {
  initDuckDB,
  replaceJsonRows,
  queryReadonly,
  closeDuckDB,
  getDuckDBStatus,
} from '@/services/duckdb'

const message = useMessage()

const rowCount = ref(50)
const rows = ref(generateRows(50))
const dbStatus = ref(getDuckDBStatus())
const querying = ref(null)
const queryError = ref('')
const queryTime = ref(null)
const queryResultColumns = ref([])
const queryResultRows = ref([])

// DuckDB 数据脏标记
let duckdbDataDirty = false
// 性能指标
const duckdbInitTime = ref(null)
const duckdbSyncTime = ref(null)

const perfMetrics = computed(() => {
  const items = []
  items.push({ label: '当前行数', value: rows.value.length.toLocaleString() })
  if (duckdbInitTime.value !== null) {
    items.push({ label: 'DuckDB 初始化', value: duckdbInitTime.value + 'ms', cls: 'tlab-metric-green' })
  }
  if (duckdbSyncTime.value !== null) {
    items.push({ label: '数据同步', value: duckdbSyncTime.value + 'ms', cls: 'tlab-metric-green' })
  }
  if (queryTime.value !== null) {
    items.push({ label: '查询耗时', value: queryTime.value + 'ms', cls: 'tlab-metric-green' })
    items.push({ label: '返回行数', value: queryResultRows.value.length.toLocaleString() })
  }
  return items
})

const tableColumns = [
  { title: '#', field: '_row_no', width: 60, hozAlign: 'center' },
  { title: '日期', field: 'business_date', width: 110 },
  { title: '单位', field: 'entity_name', width: 120 },
  { title: '账户', field: 'account_name', width: 160 },
  { title: '摘要', field: 'summary_text', width: 120 },
  { title: '对方', field: 'counterparty_name', width: 120 },
  { title: '收入', field: 'income_amount', width: 110, hozAlign: 'right', formatter: 'money' },
  { title: '支出', field: 'expense_amount', width: 110, hozAlign: 'right', formatter: 'money' },
  { title: '余额', field: 'balance', width: 120, hozAlign: 'right', formatter: 'money' },
  { title: '异常', field: 'abnormal_code', width: 130 },
]

const presets = [
  {
    key: 'total',
    label: '总行数',
    sql: 'SELECT COUNT(*) AS total_rows FROM transactions',
  },
  {
    key: 'abnormal',
    label: '异常行',
    sql: "SELECT * FROM transactions WHERE abnormal_code IS NOT NULL ORDER BY business_date",
  },
  {
    key: 'by_account',
    label: '按账户汇总',
    sql: `SELECT account_name,
            SUM(income_amount) AS total_income,
            SUM(expense_amount) AS total_expense,
            COUNT(*) AS row_count
          FROM transactions
          GROUP BY account_name
          ORDER BY total_income DESC NULLS LAST`,
  },
  {
    key: 'by_date',
    label: '按日期汇总',
    sql: `SELECT business_date,
            SUM(income_amount) AS total_income,
            SUM(expense_amount) AS total_expense,
            COUNT(*) AS row_count
          FROM transactions
          WHERE business_date IS NOT NULL
          GROUP BY business_date
          ORDER BY business_date DESC
          LIMIT 30`,
  },
  {
    key: 'top_income',
    label: '收入 Top 10',
    sql: `SELECT business_date, entity_name, counterparty_name, income_amount
          FROM transactions
          WHERE income_amount IS NOT NULL
          ORDER BY income_amount DESC
          LIMIT 10`,
  },
  {
    key: 'quality',
    label: '数据质量检查',
    sql: `SELECT
            SUM(CASE WHEN income_amount IS NULL AND expense_amount IS NULL THEN 1 ELSE 0 END) AS amount_null_count,
            SUM(CASE WHEN business_date IS NULL THEN 1 ELSE 0 END) AS date_null_count,
            SUM(CASE WHEN account_name IS NULL THEN 1 ELSE 0 END) AS account_null_count,
            SUM(CASE WHEN abnormal_code IS NOT NULL THEN 1 ELSE 0 END) AS abnormal_count,
            COUNT(*) AS total
          FROM transactions`,
  },
]

const queryDisplayColumns = computed(() => {
  return queryResultColumns.value.map((col) => {
    const isMoney = ['income_amount', 'expense_amount', 'balance', 'total_income', 'total_expense'].includes(col)
    const isNumber = ['total_rows', 'row_count', 'amount_null_count', 'date_null_count', 'account_null_count', 'abnormal_count', 'total'].includes(col)
    return {
      title: col,
      field: col,
      hozAlign: isMoney || isNumber ? 'right' : 'left',
      formatter: isMoney || isNumber ? 'money' : undefined,
      width: isMoney || isNumber ? 130 : undefined,
    }
  })
})

function changeRowSize(size) {
  rowCount.value = size
  rows.value = generateRows(size)
  queryResultColumns.value = []
  queryResultRows.value = []
  queryError.value = ''
  queryTime.value = null
  duckdbSyncTime.value = null
  if (dbStatus.value === 'ready') {
    duckdbDataDirty = true
  }
}

async function doInitDuckDB() {
  dbStatus.value = 'initializing'
  try {
    const start = performance.now()
    await initDuckDB()
    duckdbInitTime.value = Math.round(performance.now() - start)
    dbStatus.value = getDuckDBStatus()

    const syncStart = performance.now()
    await replaceJsonRows('transactions', rows.value)
    duckdbSyncTime.value = Math.round(performance.now() - syncStart)
    duckdbDataDirty = false

    message.success('DuckDB 已就绪，数据已注册')
  } catch (e) {
    dbStatus.value = getDuckDBStatus()
    message.error(e.message || 'DuckDB 初始化失败')
  }
}

async function doCloseDuckDB() {
  await closeDuckDB()
  dbStatus.value = getDuckDBStatus()
  queryResultColumns.value = []
  queryResultRows.value = []
  queryTime.value = null
  queryError.value = ''
  duckdbInitTime.value = null
  duckdbSyncTime.value = null
  duckdbDataDirty = false
  message.info('DuckDB 已关闭')
}

async function syncIfNeeded() {
  if (!duckdbDataDirty) return
  const syncStart = performance.now()
  await replaceJsonRows('transactions', rows.value)
  duckdbSyncTime.value = Math.round(performance.now() - syncStart)
  duckdbDataDirty = false
}

async function runPreset(preset) {
  querying.value = preset.key
  queryError.value = ''
  queryTime.value = null

  try {
    await syncIfNeeded()

    const start = performance.now()
    const result = await queryReadonly(preset.sql)
    const elapsed = Math.round(performance.now() - start)

    queryResultColumns.value = result.columns
    queryResultRows.value = result.rows
    queryTime.value = elapsed
  } catch (e) {
    queryError.value = e.message || '查询失败'
    queryResultColumns.value = []
    queryResultRows.value = []
  } finally {
    querying.value = null
  }
}

onUnmounted(async () => {
  await closeDuckDB()
})
</script>

<style scoped>
@import '../common.css';

.tlab {
  max-width: 1200px;
}

.tlab-notice {
  background: #fef9f0;
  border: 1px solid #e8d9be;
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  font-size: var(--font-size-sm);
  color: #7a6a4f;
  line-height: 1.7;
  margin-bottom: 16px;
}

.tlab-controls {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}

.tlab-controls-label {
  font-size: var(--font-size-sm);
  color: var(--muted);
  font-weight: 500;
  margin-right: 4px;
}

.tlab-controls-info {
  font-size: var(--font-size-xs);
  color: var(--muted);
  margin-left: 8px;
}

.tlab-subtitle {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.tlab-table-section {
  margin-bottom: 20px;
}

.tlab-duckdb-section {
  border-top: 1px solid var(--line);
  padding-top: 16px;
}

.tlab-duckdb-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.tlab-presets {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.tlab-metrics {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  padding: 8px 12px;
  background: var(--panel-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
}

.tlab-metric-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tlab-metric-label {
  font-size: var(--font-size-xs);
  color: var(--muted);
}

.tlab-metric-value {
  font-size: var(--font-size-sm);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.tlab-metric-green {
  color: var(--green);
}

.tlab-error {
  font-size: var(--font-size-sm);
  color: var(--warn-text);
  background: var(--warn-bg);
  border: 1px solid var(--warn-border);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  margin-bottom: 10px;
}

.tlab-query-result {
  margin-top: 12px;
}
</style>
