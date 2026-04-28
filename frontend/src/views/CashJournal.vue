<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>现金日记账</h3>
        <span>现金类资金载体的结果视图</span>
      </div>
      <div class="filters-bar">
        <input v-model="startDate" type="date" class="filter" />
        <span style="color:var(--muted);font-size:13px">至</span>
        <input v-model="endDate" type="date" class="filter" />
        <select v-model="accountId" class="filter">
          <option :value="null">全部账户</option>
          <optgroup v-for="g in entityGroups" :key="g.entity_id" :label="g.entity_name">
            <option v-for="a in g.accounts" :key="a.id" :value="a.id">{{ a.account_code }} {{ a.account_alias }}</option>
          </optgroup>
        </select>
        <div style="flex:1"></div>
        <div class="btn-row">
          <button class="btn btn-secondary" @click="doExport">导出</button>
          <button class="btn btn-secondary" @click="window.print()">打印</button>
          <button class="btn btn-primary" @click="loadReport">生成报表</button>
          <button class="btn btn-accent" @click="smartReport" :disabled="smartReportLoading">
            {{ smartReportLoading ? '生成中...' : '智能报表' }}
          </button>
        </div>
      </div>
      <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
      <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>正在生成报表...</p></div>

      <!-- 优先：原 Excel 完整渲染（保留所有账户块、签字栏、合并单元格等） -->
      <div v-else-if="templateExcelHtml" class="excel-host" v-html="templateExcelHtml"></div>

      <!-- 完整 Excel 布局渲染模式 -->
      <div v-else-if="hasFullLayout" class="excel-layout-wrapper">
        <table class="excel-layout-table" :style="tableStyle">
          <colgroup>
            <col v-for="(w, ci) in templateLayout.col_widths" :key="ci" :style="{ width: w + 'px' }" />
          </colgroup>
          <tbody>
            <!-- 布局固定行：标题/描述/信息/表头 -->
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

            <!-- 数据行（按块渲染） -->
            <template v-for="(block, bi) in blocks" :key="'b'+bi">
              <!-- 月初余额行（block 首行，全列） -->
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
              <!-- 明细行（只显示右侧列） -->
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
              <!-- 小计行 -->
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

            <!-- 无数据时：仍然渲染空的数据行和小计行以显示完整模板 -->
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

      <!-- 简化表头模式（无 layout 或 layout 只有表头） -->
      <table v-else-if="templateColumns">
        <thead>
          <tr>
            <th v-for="col in templateColumns" :key="col.field_key" :style="{ width: col.width+'px', textAlign: col.align }">{{ col.header_name }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="rows.length">
            <tr v-for="(r, idx) in rows" :key="idx">
              <td v-for="col in templateColumns" :key="col.field_key" :class="colClass(col.field_key)" :style="{ textAlign: col.align }">{{ cellVal(r, col.field_key) }}</td>
            </tr>
          </template>
          <tr v-else>
            <td :colspan="templateColumns.length" class="empty-cell">暂无日记账数据，选择日期范围和账户后点击"生成报表"</td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="templateLoaded" class="empty-state">
        <div class="empty-icon">📋</div>
        <h4>未配置报表模板</h4>
        <p>请先在「系统设置 → 报表模板管理」中上传现金日记账模板</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as api from '@/api/report'
import * as master from '@/api/master'
import { fmtAmt } from '@/utils/format'
import { exportReport } from '@/api/export'
import { useTemplateColumns } from '@/composables/useTemplateColumns'
import http from '@/api'

const today = new Date().toISOString().slice(0, 10)
const startDate = ref(today)
const endDate = ref(today)
const accountId = ref(null)
const entities = ref([])
const blocks = ref([])
const rows = ref([])
const loading = ref(false)
const smartReportLoading = ref(false)
const errorMsg = ref('')
const { templateColumns, templateLayout, templateExcelHtml, templateLoaded, loadTemplate } = useTemplateColumns('cash_journal')

const MONEY_KEYS = new Set(['prev_balance', 'income', 'expense', 'day_balance', 'amount', 'rolling_balance'])
function colClass(key) { return MONEY_KEYS.has(key) ? 'money' : '' }
function cellVal(r, key) {
  if (MONEY_KEYS.has(key)) return fmtAmt(r[key])
  if (r[key] === undefined || r[key] === null) return ''
  return r[key]
}

const entityGroups = computed(() => {
  const groups = {}
  for (const e of entities.value) {
    if (!groups[e.entity_id]) groups[e.entity_id] = { entity_id: e.entity_id, entity_name: e.entity_name, accounts: [] }
    groups[e.entity_id].accounts.push(...e.accounts)
  }
  return Object.values(groups)
})

// ── Excel 布局渲染核心 ──────────────────────────────

// 是否有完整布局（>1行，含 title/info/header/data/subtotal）
const hasFullLayout = computed(() => {
  const layout = templateLayout.value
  if (!layout || !layout.rows) return false
  const types = new Set(layout.rows.map(r => r.type))
  return types.has('header') && (types.has('data') || types.has('title'))
})

// 表格总宽度样式
const tableStyle = computed(() => {
  if (!templateLayout.value) return {}
  const totalW = templateLayout.value.col_widths.reduce((s, w) => s + w, 0)
  return { width: totalW + 'px' }
})

// 布局中固定行（标题/描述/信息/表头）
const fixedRows = computed(() => {
  const layout = templateLayout.value
  if (!layout) return []
  return layout.rows.filter(r => ['title', 'info', 'header'].includes(r.type))
})

// 将稀疏 cell 数组转为完整的 col_count 长度数组
// 填充空列，保留 colspan/rowspan 信息
function toFullRow(lr) {
  const layout = templateLayout.value
  if (!layout) return []
  const colCount = layout.col_count
  const result = new Array(colCount).fill(null)
  const skipSet = new Set()

  for (const cell of lr.cells) {
    if (skipSet.has(cell.col)) continue
    result[cell.col] = { ...cell, _skip: false }
    // 标记被 colspan 占用的列
    if (cell.colspan > 1) {
      for (let i = 1; i < cell.colspan; i++) {
        result[cell.col + i] = { col: cell.col + i, _skip: true, text: '', colspan: 1, rowspan: 1, is_placeholder: false, field_key: null }
      }
    }
  }

  // 填充空位
  for (let i = 0; i < colCount; i++) {
    if (!result[i]) {
      result[i] = { col: i, _skip: false, text: '', colspan: 1, rowspan: 1, is_placeholder: false, field_key: null }
    }
  }
  return result
}

// 第一行数据模板（月初余额行），补全为完整12列
const firstRowFull = computed(() => {
  const layout = templateLayout.value
  if (!layout) return []
  const dataRows = layout.rows.filter(r => r.type === 'data')
  if (!dataRows.length) return []
  return toFullRow(dataRows[0])
})

// 明细行模板（第二行数据模板），补全为完整12列
const detailRowFull = computed(() => {
  const layout = templateLayout.value
  if (!layout) return []
  const dataRows = layout.rows.filter(r => r.type === 'data')
  const tpl = dataRows[1] || dataRows[0]
  if (!tpl) return []
  return toFullRow(tpl)
})

// 小计行模板，补全为完整12列
const subtotalRowFull = computed(() => {
  const layout = templateLayout.value
  if (!layout) return []
  const stRows = layout.rows.filter(r => r.type === 'subtotal')
  if (!stRows.length) return []
  return toFullRow(stRows[0])
})

// ── 固定行渲染 ──────────────────────────────

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

// ── 数据行渲染 ──────────────────────────────

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

// 月初余额行文本
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

// 明细行文本
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

// 小计行文本
function subtotalCellText(cell, block) {
  if (!cell.is_placeholder) return cell.text
  const key = cell.field_key
  if (!key) return ''
  if (key === 'income') return fmtAmt(block.total_income)
  if (key === 'expense') return fmtAmt(block.total_expense)
  if (key === 'day_balance') return fmtAmt(block.ending_balance)
  return ''
}

// 无数据时的空行文本（去掉占位符显示空白）
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
    // 扁平化用于简化模式
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
    const blob = await exportReport({ export_type: 'cash_journal', start_date: startDate.value || undefined, end_date: endDate.value || undefined })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `cash_journal.xlsx`; a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert('导出失败: ' + (e.message || e)) }
}

async function smartReport() {
  smartReportLoading.value = true
  try {
    const agents = await http.get('/agent_v2/agents')
    const agent = (agents || [])[0]
    if (!agent) {
      alert('请先创建一个智能体')
      return
    }
    const res = await http.post(`/agent_v2/agents/${agent.id}/skill-run`, {
      skill_code: 'gen_report',
      report_type: 'cash_journal',
      start_date: startDate.value || undefined,
      end_date: endDate.value || undefined,
    })
    const inner = res?.result || res
    if (inner && inner.ok) {
      alert(`报表已生成: ${inner.report_name}，${inner.row_count} 行数据，文件: ${inner.file_path}`)
    } else {
      alert('报表生成失败: ' + (inner?.error || '未知错误'))
    }
  } catch (e) {
    alert('智能报表失败: ' + (e.message || e))
  } finally {
    smartReportLoading.value = false
  }
}

onMounted(async () => {
  try { entities.value = (await master.getAccountsTree()) || [] } catch (e) {}
  loadTemplate()
})
</script>

<style scoped>
@import './common.css';

/* Excel 布局专用样式 */
.excel-layout-wrapper {
  overflow-x: auto;
  margin-top: 8px;
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
.empty-cell { text-align: center; color: #8C8680; padding: 40px 20px; font-size: 14px; }
</style>
