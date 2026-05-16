<template>
  <div class="section report-print-root table-workspace-page">
    <div class="section-title">
      <h3>现金日记账</h3>
      <span>现金类资金载体的结果视图</span>
    </div>
    <div class="filters-bar">
      <NDatePicker :value="startDateTs" @update:value="v => startDateTs = v" type="date" clearable />
      <span style="color:var(--muted);font-size:13px">至</span>
      <NDatePicker :value="endDateTs" @update:value="v => endDateTs = v" type="date" clearable />
      <MasterAccountSelect v-model="accountId" :entities="entities" />
      <div class="filter-spacer"></div>
      <div class="btn-row">
        <NButton v-if="hasBookView" secondary @click="togglePreview">{{ previewOpen ? '关闭预览' : '账簿预览' }}</NButton>
        <NButton secondary @click="doExport">导出</NButton>
        <NButton secondary @click="handlePrint">{{ previewOpen ? '打印账簿' : '页面打印' }}</NButton>
        <NButton type="primary" @click="loadReport">生成报表</NButton>
      </div>
    </div>
    <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
    <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在生成报表...</p></div>

    <!-- 账簿预览面板 -->
    <template v-else>
      <div v-if="previewOpen" class="table-workspace-main book-preview">
        <div class="preview-note adt-no-print">
          <span>账簿预览 · 正式账簿以导出文件为准</span>
          <button class="view-switch-btn" type="button" @click="previewOpen = false">关闭预览</button>
        </div>
        <!-- 路径 A：原 Excel 完整渲染 -->
        <div v-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>
        <!-- 路径 B：完整 Excel 布局渲染 -->
        <div v-else-if="hasFullLayout" class="excel-layout-wrapper">
          <table class="excel-layout-table" :style="tableStyle">
            <colgroup>
              <col v-for="(w, ci) in templateLayout.col_widths" :key="ci" :style="{ width: w + 'px' }" />
            </colgroup>
            <tbody>
              <tr v-for="(lr, lri) in fixedRows" :key="'f'+lri" :class="rowClass(lr)">
                <td
                  v-for="cell in toFullRow(lr)"
                  :key="cell.col"
                  v-show="!cell._skip"
                  :colspan="cell.colspan > 1 ? cell.colspan : undefined"
                  :rowspan="cell.rowspan > 1 ? cell.rowspan : undefined"
                  :class="fixedCellClass(lr, cell)"
                  :style="fixedCellStyle(lr, cell)"
                >{{ fixedCellText(cell) }}</td>
              </tr>
              <template v-for="(block, bi) in blocks" :key="'b'+bi">
                <tr class="data-row block-start">
                  <td
                    v-for="cell in firstRowFull"
                    :key="cell.col"
                    v-show="!cell._skip"
                    :colspan="cell.colspan > 1 ? cell.colspan : undefined"
                    :class="dataCellClass(cell)"
                    :style="dataCellStyle(cell)"
                  >{{ firstRowCellText(cell, block) }}</td>
                </tr>
                <tr v-for="(r, ri) in block.rows" :key="'r'+ri" class="data-row">
                  <td
                    v-for="cell in detailRowFull"
                    :key="cell.col"
                    v-show="!cell._skip"
                    :colspan="cell.colspan > 1 ? cell.colspan : undefined"
                    :class="dataCellClass(cell)"
                    :style="dataCellStyle(cell)"
                  >{{ detailCellText(cell, r) }}</td>
                </tr>
                <tr class="subtotal-row">
                  <td
                    v-for="cell in subtotalRowFull"
                    :key="cell.col"
                    v-show="!cell._skip"
                    :colspan="cell.colspan > 1 ? cell.colspan : undefined"
                    :class="subtotalCellClass(cell)"
                    :style="dataCellStyle(cell)"
                  >{{ subtotalCellText(cell, block) }}</td>
                </tr>
              </template>
              <template v-if="!blocks.length">
                <tr class="data-row block-start">
                  <td
                    v-for="cell in firstRowFull"
                    :key="cell.col"
                    v-show="!cell._skip"
                    :colspan="cell.colspan > 1 ? cell.colspan : undefined"
                    :class="dataCellClass(cell)"
                    :style="dataCellStyle(cell)"
                  >{{ emptyCellText(cell) }}</td>
                </tr>
                <tr v-for="n in 3" :key="'empty'+n" class="data-row">
                  <td
                    v-for="cell in detailRowFull"
                    :key="cell.col"
                    v-show="!cell._skip"
                    :colspan="cell.colspan > 1 ? cell.colspan : undefined"
                    :class="dataCellClass(cell)"
                    :style="dataCellStyle(cell)"
                  > </td>
                </tr>
                <tr class="subtotal-row">
                  <td
                    v-for="cell in subtotalRowFull"
                    :key="cell.col"
                    v-show="!cell._skip"
                    :colspan="cell.colspan > 1 ? cell.colspan : undefined"
                    :class="subtotalCellClass(cell)"
                    :style="dataCellStyle(cell)"
                  >{{ cell.text || ' ' }}</td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ADT 主视图 -->
      <div v-else-if="hasColumns" class="table-workspace-main">
        <AdvancedDataTable
          :columns="appliedColumns"
          :data="displayRows"
          :pagination="false"
          fill-parent
          show-toolbar
          :density="tableDensity"
          :table-key="TABLE_KEY"
          show-column-settings
          show-reset-preferences
          :hidden-fields="hiddenFields"
          :all-columns-for-settings="tabulatorColumns"
          empty-text="暂无日记账数据，选择日期范围和账户后点击'生成报表'"
          :row-key="'__row_key'"
          @density-change="onDensityChange"
          @column-width-change="onColumnWidthChange"
          @column-order-change="onColumnOrderChange"
          @column-visibility-change="onColumnVisibilityChange"
          @preferences-reset="onPreferencesReset"
        />
      </div>

      <div v-else class="empty-state">
        <div class="empty-icon">📊</div>
        <h4>暂无日记账数据</h4>
        <p>选择日期范围和账户后点击"生成报表"</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NDatePicker, NButton } from 'naive-ui'
import MasterAccountSelect from '@/components/MasterAccountSelect.vue'
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'
import { useReportPrint } from '@/composables/useReportPrint'
import { emptyDashFormatter, moneyFormatter } from '@/utils/tabulatorFormatters'
import { adaptTemplateColumns } from '@/composables/useColumnAdapter'
import {
  getPreferences,
  applyPreferences,
  saveColumnWidth,
  saveColumnVisibility,
  saveColumnOrder,
  saveDensity,
  resetPreferences,
} from '@/composables/useAdvancedTablePreferences'
import * as api from '@/api/report'
import * as master from '@/api/master'
import { fmtAmt } from '@/utils/format'
import { exportReport } from '@/api/export'
import { useTemplateColumns } from '@/composables/useTemplateColumns'
import { getReportFilename } from '@/utils/reportFilename'

const { handlePrint } = useReportPrint()

const TABLE_KEY = 'cash-journal'

const today = new Date()
const todayStr = today.toISOString().slice(0, 10)
const startDate = ref(todayStr)
const endDate = ref(todayStr)
const accountId = ref(null)

function dateStringToTs(s) {
  if (!s) return null
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d).getTime()
}
function tsToDateString(ts) {
  if (ts == null) return ''
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const startDateTs = computed({
  get: () => dateStringToTs(startDate.value),
  set: (v) => { startDate.value = tsToDateString(v) }
})
const endDateTs = computed({
  get: () => dateStringToTs(endDate.value),
  set: (v) => { endDate.value = tsToDateString(v) }
})

const entities = ref([])
const blocks = ref([])
const rows = ref([])
const loading = ref(false)
const errorMsg = ref('')
const { templateColumns, templateLayout, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('cash_journal')

// ── 视图状态 ──────────────────────────────

const previewOpen = ref(false)

const hasFullLayout = computed(() => {
  const layout = templateLayout.value
  if (!layout || !layout.rows) return false
  const types = new Set(layout.rows.map(r => r.type))
  return types.has('header') && (types.has('data') || types.has('title'))
})

const hasBookView = computed(() => !!templateExcelHtml.value || hasFullLayout.value)

function togglePreview() {
  previewOpen.value = !previewOpen.value
}

// ── 数据视图列定义 ──────────────────────────────

const MONEY_KEYS = new Set(['prev_balance', 'income', 'expense', 'day_balance', 'amount', 'rolling_balance'])

const DEFAULT_TABULATOR_COLUMNS = [
  { field: 'business_date', title: '日期', width: 120, hozAlign: 'center', formatter: emptyDashFormatter, headerSort: false },
  { field: 'entity_name', title: '单位', width: 120, formatter: emptyDashFormatter, headerSort: false },
  { field: 'account_name', title: '账户', width: 150, formatter: emptyDashFormatter, headerSort: false },
  { field: 'summary_text', title: '摘要', width: 200, formatter: emptyDashFormatter, headerSort: false },
  { field: 'prev_balance', title: '上日余额', width: 130, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'income', title: '收入', width: 130, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'expense', title: '支出', width: 130, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
  { field: 'day_balance', title: '本日余额', width: 130, hozAlign: 'right', formatter: moneyFormatter, headerSort: false },
]

const tabulatorColumns = computed(() =>
  adaptTemplateColumns(templateColumns.value, DEFAULT_TABULATOR_COLUMNS, {
    moneyFields: MONEY_KEYS,
  }).map(col => ({ ...col, headerSort: false }))
)

const hasColumns = computed(() => tabulatorColumns.value.length > 0)

// ── 偏好系统 ──────────────────────────────

const preferencesVersion = ref(0)
const tableDensity = ref(getPreferences(TABLE_KEY).density || 'default')

function touchPreferences() { preferencesVersion.value++ }

const appliedColumns = computed(() => {
  preferencesVersion.value
  return applyPreferences(tabulatorColumns.value, getPreferences(TABLE_KEY))
})

const hiddenFields = computed(() => {
  preferencesVersion.value
  const prefs = getPreferences(TABLE_KEY)
  const visibility = prefs.visibility || {}
  return Object.entries(visibility).filter(([, v]) => !v).map(([f]) => f)
})

function onDensityChange(value) {
  tableDensity.value = value
  saveDensity(TABLE_KEY, value)
}

function onColumnWidthChange({ field, width }) {
  saveColumnWidth(TABLE_KEY, field, width)
}

function onColumnOrderChange(order) {
  saveColumnOrder(TABLE_KEY, order)
}

function onColumnVisibilityChange({ field, visible }) {
  saveColumnVisibility(TABLE_KEY, field, visible)
  touchPreferences()
}

function onPreferencesReset() {
  resetPreferences(TABLE_KEY)
  tableDensity.value = 'default'
  touchPreferences()
}

// ── 数据行 ──────────────────────────────

const displayRows = computed(() =>
  rows.value.map((r, idx) => ({
    ...r,
    __row_key: `cj-${idx}`,
  }))
)

// ── Excel 布局渲染核心（账簿视图专用，保持不变） ──────────────────────────────

const tableStyle = computed(() => {
  if (!templateLayout.value) return {}
  const totalW = templateLayout.value.col_widths.reduce((s, w) => s + w, 0)
  return { width: totalW + 'px' }
})

const fixedRows = computed(() => {
  const layout = templateLayout.value
  if (!layout) return []
  return layout.rows.filter(r => ['title', 'info', 'header'].includes(r.type))
})

function toFullRow(lr) {
  const layout = templateLayout.value
  if (!layout) return []
  const colCount = layout.col_count
  const result = new Array(colCount).fill(null)
  const skipSet = new Set()

  for (const cell of lr.cells) {
    if (skipSet.has(cell.col)) continue
    result[cell.col] = { ...cell, _skip: false }
    if (cell.colspan > 1) {
      for (let i = 1; i < cell.colspan; i++) {
        result[cell.col + i] = { col: cell.col + i, _skip: true, text: '', colspan: 1, rowspan: 1, is_placeholder: false, field_key: null }
      }
    }
  }

  for (let i = 0; i < colCount; i++) {
    if (!result[i]) {
      result[i] = { col: i, _skip: false, text: '', colspan: 1, rowspan: 1, is_placeholder: false, field_key: null }
    }
  }
  return result
}

const firstRowFull = computed(() => {
  const layout = templateLayout.value
  if (!layout) return []
  const dataRows = layout.rows.filter(r => r.type === 'data')
  if (!dataRows.length) return []
  return toFullRow(dataRows[0])
})

const detailRowFull = computed(() => {
  const layout = templateLayout.value
  if (!layout) return []
  const dataRows = layout.rows.filter(r => r.type === 'data')
  const tpl = dataRows[1] || dataRows[0]
  if (!tpl) return []
  return toFullRow(tpl)
})

const subtotalRowFull = computed(() => {
  const layout = templateLayout.value
  if (!layout) return []
  const stRows = layout.rows.filter(r => r.type === 'subtotal')
  if (!stRows.length) return []
  return toFullRow(stRows[0])
})

function rowClass(lr) {
  if (lr.type === 'header') return 'excel-header-row'
  if (lr.type === 'title') return 'excel-title-row'
  return ''
}

function fixedCellClass(lr, cell) {
  const cls = []
  if (lr.type === 'header') cls.push('excel-header-cell')
  if (lr.type === 'title') cls.push('excel-title-cell')
  return cls
}

function fixedCellStyle(lr, cell) {
  const s = {}
  if (cell.colspan > 1) s.textAlign = 'left'
  if (lr.type === 'header') s.textAlign = 'center'
  return s
}

function fixedCellText(cell) {
  if (cell.is_placeholder) {
    if (cell.text && cell.text.includes('{{报表标题}}')) {
      return '现金日记账    ' + startDate.value + '—' + endDate.value
    }
    return cell.text.replace(/\{\{报表标题\}\}/g, '现金日记账')
      .replace(/\{\{开始期间\}\}/g, startDate.value)
      .replace(/\{\{结束期间\}\}/g, endDate.value)
  }
  return cell.text
}

function dataCellClass(cell) {
  const cls = ['excel-data-cell']
  if (cell.field_key && MONEY_KEYS.has(cell.field_key)) cls.push('money')
  return cls
}

function dataCellStyle(cell) {
  const s = {}
  if (cell.field_key && MONEY_KEYS.has(cell.field_key)) s.textAlign = 'right'
  return s
}

function subtotalCellClass(cell) {
  return ['excel-subtotal-cell']
}

function firstRowCellText(cell, block) {
  if (!cell.is_placeholder) return cell.text
  const key = cell.field_key
  if (!key) return ''
  if (key === 'entity_name') return block.entity_name || ''
  if (key === 'account_name') return block.account_name || ''
  if (key === 'account_bank') return block.account_bank || ''
  if (key === 'account_code') return block.account_code || ''
  if (key === 'month') {
    if (block.rows && block.rows.length) {
      const parts = (block.rows[0].business_date || '').split('-')
      return parts[1] ? parseInt(parts[1], 10) : ''
    }
    return ''
  }
  if (key === 'prev_balance') return fmtAmt(block.opening_balance)
  return ''
}

function detailCellText(cell, r) {
  if (!cell.is_placeholder) return cell.text
  const key = cell.field_key
  if (!key) return ''
  if (key === 'month') {
    const parts = (r.business_date || '').split('-')
    return parts[1] ? parseInt(parts[1], 10) : ''
  }
  if (key === 'day') {
    const parts = (r.business_date || '').split('-')
    return parts[2] ? parseInt(parts[2], 10) : ''
  }
  if (key === 'summary_text') return r.summary_text || ''
  if (key === 'income') return fmtAmt(r.income)
  if (key === 'expense') return fmtAmt(r.expense)
  if (key === 'day_balance') return fmtAmt(r.day_balance)
  return r[key] != null ? r[key] : ''
}

function subtotalCellText(cell, block) {
  if (!cell.is_placeholder) return cell.text
  const key = cell.field_key
  if (!key) return ''
  if (key === 'income') return fmtAmt(block.total_income)
  if (key === 'expense') return fmtAmt(block.total_expense)
  if (key === 'day_balance') return fmtAmt(block.ending_balance)
  return ''
}

function emptyCellText(cell) {
  if (!cell.is_placeholder) return cell.text
  return ''
}

// ── 数据加载 ──────────────────────────────

async function loadReport() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { start_date: startDate.value, end_date: endDate.value }
    if (accountId.value) params.account_id = accountId.value
    const raw = await api.getCashJournal(params) || []
    blocks.value = raw
    const result = []
    for (const block of raw) {
      for (const row of (block.rows || [])) {
        const parts = (row.business_date || '').split('-')
        result.push({
          ...row,
          entity_name: block.entity_name || '',
          account_name: block.account_name || '',
          month: parts[1] ? parseInt(parts[1], 10) : '',
          day: parts[2] ? parseInt(parts[2], 10) : '',
        })
      }
    }
    rows.value = result
  } catch (e) {
    errorMsg.value = '查询失败: ' + (e.message || e)
  } finally {
    loading.value = false
  }
}

async function doExport() {
  try {
    const params = { export_type: 'cash_journal', start_date: startDate.value || undefined, end_date: endDate.value || undefined }
    if (accountId.value) params.account_id = accountId.value
    const blob = await exportReport(params)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = getReportFilename('cash_journal', { startDate: startDate.value, endDate: endDate.value }); a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert('导出失败: ' + (e.message || e)) }
}

onMounted(async () => {
  try { entities.value = (await master.getAccountsTree()) || [] } catch (e) {}
  loadTemplate()
})
</script>

<style scoped>
@import './common.css';

/* CashJournal 账簿预览本地样式 */

.preview-note {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  padding: 8px 14px;
  background: var(--info-bg, #eff6ff);
  border: 1px solid var(--info-border, #bfdbfe);
  border-radius: var(--radius-sm);
  color: var(--info-text, #1e40af);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  margin-bottom: var(--space-sm);
}

.view-switch-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex-shrink: 0;
  padding: 4px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-2);
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.view-switch-btn:hover {
  background: var(--green-3);
  border-color: var(--green);
  color: var(--green);
}

.table-workspace-main.book-preview {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.table-workspace-main.book-preview > .preview-note {
  flex-shrink: 0;
}

.table-workspace-main.book-preview > .excel-host {
  flex: 1;
  min-height: 0;
  overflow: auto;
  margin-top: 0;
}

.excel-host {
  overflow-x: auto;
  margin-top: 8px;
}

.excel-host .excel-template-wrap {
  display: inline-block;
  min-width: 100%;
}

.excel-host .excel-template-table td {
  border: 1px solid #c8c2b5;
  padding: 4px 6px;
  word-break: break-word;
}

/* Excel 布局专用样式 */
.excel-layout-wrapper {
  overflow-x: auto;
  margin-top: 0;
}
.excel-layout-table {
  border-collapse: collapse;
  font-size: 13px;
  border: 1px solid #c0b9ae;
}
.excel-layout-table th,
.excel-layout-table td {
  border: 1px solid #c0b9ae;
  padding: 4px 8px;
  white-space: nowrap;
  vertical-align: middle;
}
.excel-title-row td {
  font-weight: 700;
  font-size: 15px;
  padding: 8px 10px;
  background: #faf8f3;
}
.excel-header-row td {
  background: #e8e2d6;
  font-weight: 600;
  text-align: center;
  padding: 6px 8px;
}
.excel-subtotal-cell {
  font-weight: 600;
  background: #f0ede6;
}
.excel-data-cell {
  padding: 3px 8px;
}
.block-start td {
  border-top: 2px solid #a09888;
}
</style>
