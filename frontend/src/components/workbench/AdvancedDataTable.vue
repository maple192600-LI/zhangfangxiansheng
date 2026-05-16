<template>
  <div class="adt-wrap" :class="[densityClass, { 'adt-fill': isFillMode }]">
    <div v-if="showToolbar" class="adt-toolbar adt-no-print">
      <span class="adt-toolbar-label"><span class="adt-toolbar-dot"></span>高级表格</span>
      <span class="adt-toolbar-count">{{ rowCountText }}</span>
      <span class="adt-toolbar-sep"></span>
      <span class="adt-toolbar-density">
        <button :class="{ active: currentDensity === 'compact' }" @click="setDensity('compact')">紧凑</button>
        <button :class="{ active: currentDensity === 'default' }" @click="setDensity('default')">默认</button>
        <button :class="{ active: currentDensity === 'comfortable' }" @click="setDensity('comfortable')">舒适</button>
      </span>
      <span class="adt-toolbar-hint">↔ 拖动列边界调整宽度</span>
      <button v-if="showColumnSettings" ref="columnBtnRef" class="adt-toolbar-action" @click="toggleColumnPanel" title="列设置">☰ 列</button>
      <button v-if="showResetPreferences" class="adt-toolbar-action adt-toolbar-action-reset" @click="emit('preferencesReset')" title="恢复默认设置">↺ 重置</button>
      <button v-if="showRefresh" class="adt-toolbar-refresh" @click="emit('refresh')" title="刷新数据">↻</button>
    </div>

    <!-- 列设置面板（Teleport 到 body 避免 overflow:hidden 裁剪） -->
    <Teleport to="body">
      <div v-if="columnPanelOpen" class="adt-col-panel-overlay adt-no-print" @click="columnPanelOpen = false"></div>
      <div v-if="columnPanelOpen && showColumnSettings" class="adt-col-panel adt-no-print" :style="panelStyle">
        <div class="adt-col-panel-title">列显示设置</div>
        <label v-for="col in configurableColumns" :key="col.field" class="adt-col-item">
          <input type="checkbox" :checked="isColumnVisible(col.field)" :disabled="visibleCount <= 1 && isColumnVisible(col.field)" @change="toggleColumnVisibility(col.field, $event)" />
          <span>{{ col.title }}</span>
        </label>
      </div>
    </Teleport>

    <div ref="containerRef" class="adt-container" :style="containerStyle"></div>
    <div v-if="loading && !errorText" class="adt-loading">{{ loadingText }}</div>
    <div v-if="errorText" class="adt-error">
      {{ errorText }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import 'tabulator-tables/dist/css/tabulator.min.css'
import '@/styles/tabulator-theme.css'
import { useTabulatorTable } from '@/composables/useTabulatorTable'

const props = defineProps({
  columns: { type: Array, required: true },
  data: { type: Array, default: () => [] },
  rowKey: { type: String, default: 'id' },
  height: { type: String, default: '' },
  fillParent: { type: Boolean, default: false },
  pagination: { type: Boolean, default: true },
  paginationSize: { type: Number, default: 50 },
  loading: { type: Boolean, default: false },
  loadingText: { type: String, default: '加载中...' },
  emptyText: { type: String, default: '暂无数据' },
  errorText: { type: String, default: '' },
  enableSelection: { type: Boolean, default: false },
  selectedRowKeys: { type: Array, default: () => [] },
  enableColumnResize: { type: Boolean, default: false },
  enableColumnMove: { type: Boolean, default: false },
  density: { type: String, default: 'default' },
  showToolbar: { type: Boolean, default: false },
  showRefresh: { type: Boolean, default: false },
  totalRows: { type: Number, default: 0 },
  rowClass: { type: Function, default: null },
  tableKey: { type: String, default: '' },
  showColumnSettings: { type: Boolean, default: false },
  showResetPreferences: { type: Boolean, default: false },

  hiddenFields: { type: Array, default: () => [] },
  allColumnsForSettings: { type: Array, default: () => [] },

  editable: { type: Boolean, default: false },
  editMode: { type: String, default: 'none' },
  enableClipboard: { type: Boolean, default: false },
  enableKeyboardNav: { type: Boolean, default: false },
  rowIdField: { type: String, default: '_row_id' },
})

const emit = defineEmits([
  'rowClick',
  'rowDblClick',
  'selectionChange',
  'tableReady',
  'tableError',
  'densityChange',
  'refresh',
  'columnSettingsOpen',
  'columnVisibilityChange',
  'columnOrderChange',
  'columnWidthChange',
  'preferencesReset',
  'cellClick',
  'cellEdited',
  'rowsChanged',
  'rowAdded',
  'rowDeleted',
  'paste',
])

const containerRef = ref(null)
const columnPanelOpen = ref(false)
const columnBtnRef = ref(null)
const panelStyle = ref({})

const currentDensity = ref(props.density)

watch(() => props.density, (v) => { currentDensity.value = v })

function setDensity(value) {
  currentDensity.value = value
  emit('densityChange', value)
}

const rowCountText = computed(() => {
  const total = props.totalRows
  const current = props.data.length
  if (total && total !== current) {
    return `共 ${total} 条，当前页 ${current} 条`
  }
  return `共 ${current} 行`
})

const isFillMode = computed(() => props.fillParent || props.height === '100%')

const containerStyle = computed(() => {
  if (isFillMode.value) return {}
  if (props.height) return { height: props.height }
  return {}
})

const SELECTION_COL = {
  formatter: 'rowSelection',
  titleFormatter: 'rowSelection',
  hozAlign: 'center',
  headerSort: false,
  width: 40,
  frozen: true,
}

const densityClass = computed(() => {
  if (currentDensity.value === 'compact') return 'adt-density-compact'
  if (currentDensity.value === 'comfortable') return 'adt-density-comfortable'
  return ''
})

const resolvedColumns = computed(() => {
  const cols = props.columns || []
  return props.enableSelection ? [SELECTION_COL, ...cols] : cols
})

const tabulatorHeight = computed(() => {
  if (isFillMode.value) return '100%'
  if (props.height) return props.height
  return ''
})

// Columns available for show/hide configuration (all columns, including hidden ones)
const configurableColumns = computed(() => {
  const source = props.allColumnsForSettings?.length
    ? props.allColumnsForSettings
    : props.columns
  return source.filter(c => c.field)
})

const hiddenFieldsSet = computed(() => new Set(props.hiddenFields))

const visibleCount = computed(() =>
  configurableColumns.value.filter(c => !hiddenFieldsSet.value.has(c.field)).length
)

function isColumnVisible(field) {
  return !hiddenFieldsSet.value.has(field)
}

function toggleColumnVisibility(field, event) {
  const visible = event.target.checked
  emit('columnVisibilityChange', { field, visible })
}

function toggleColumnPanel() {
  columnPanelOpen.value = !columnPanelOpen.value
  if (columnPanelOpen.value) {
    emit('columnSettingsOpen')
    const btn = columnBtnRef.value
    if (btn) {
      const rect = btn.getBoundingClientRect()
      panelStyle.value = {
        position: 'fixed',
        top: `${rect.bottom + 4}px`,
        right: `${window.innerWidth - rect.right}px`,
      }
    }
  }
}

const { table, isReady, updateData, updateColumns, destroyTable, getSelectedRows, clearSelection, addRow, addRows, deleteRow, getData, clearData } =
  useTabulatorTable(containerRef, {
    get columns() { return resolvedColumns.value },
    get data() { return props.data },
    pagination: props.pagination,
    paginationSize: props.paginationSize,
    emptyText: props.emptyText,
    editable: props.editable,
    clipboard: props.enableClipboard,
    rowClick: (e, data) => emit('rowClick', data),
    rowDblClick: (e, data) => emit('rowDblClick', data),
    onSelectionChange: (data) => emit('selectionChange', data),
    onTableReady: () => emit('tableReady'),
    onTableError: (msg) => emit('tableError', msg),
    onColumnResized: ({ field, width }) => emit('columnWidthChange', { field, width }),
    onColumnMoved: (order) => emit('columnOrderChange', order),
    onColumnVisibilityChanged: ({ field, visible }) => emit('columnVisibilityChange', { field, visible }),
    cellClick: (e, cell) => emit('cellClick', { event: e, cell, rowData: cell.getRow()?.getData(), field: cell.getColumn()?.getField() }),
    onCellEdited: ({ field, value, rowData }) => emit('cellEdited', { field, value, rowData }),
    onPaste: (rowsData) => emit('paste', rowsData),
    tabulatorOverrides: {
      index: props.rowKey || (props.editable ? props.rowIdField : 'id'),
      selectableRows: props.enableSelection ? true : false,
      resizableColumns: props.enableColumnResize || props.showToolbar,
      movableColumns: props.enableColumnMove || props.showColumnSettings,
      ...(tabulatorHeight.value ? { height: tabulatorHeight.value } : {}),
      ...(props.rowClass ? {
        rowFormatter: (row) => {
          const el = row.getElement()
          const prev = el.dataset.adtCustomClasses
          if (prev) prev.split(/\s+/).filter(Boolean).forEach(c => el.classList.remove(c))
          const cls = props.rowClass(row.getData())
          if (cls) {
            const classes = cls.split(/\s+/).filter(Boolean)
            el.classList.add(...classes)
            el.dataset.adtCustomClasses = classes.join(' ')
          } else {
            delete el.dataset.adtCustomClasses
          }
        }
      } : {}),
    },
  })

watch(() => props.data, (newData, oldData) => {
  if (isReady.value && newData !== oldData) {
    updateData(newData)
  }
})

watch(resolvedColumns, (newCols) => {
  if (isReady.value) {
    updateColumns(newCols)
  }
})

watch(() => props.selectedRowKeys, (keys) => {
  if (!table.value || !isReady.value || !props.enableSelection) return
  try {
    if (keys && keys.length > 0) {
      table.value.selectRow(keys)
    } else {
      table.value.deselectRow()
    }
  } catch (e) { console.warn('[AdvancedDataTable] selectedRowKeys sync failed:', e) }
})



defineExpose({
  table,
  isReady,
  updateData,
  updateColumns,
  destroyTable,
  getSelectedRows,
  clearSelection,
  addRow,
  addRows,
  deleteRow,
  getData,
  clearData,
})
</script>

<style scoped>
.adt-wrap {
  position: relative;
  width: 100%;
}

.adt-wrap.adt-fill {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.adt-wrap.adt-fill > .adt-toolbar {
  flex-shrink: 0;
}

.adt-wrap.adt-fill > .adt-container {
  flex: 1;
  min-height: 0;
}

.adt-container {
  width: 100%;
  min-height: 200px;
}

.adt-wrap.adt-fill > .adt-container {
  min-height: 0;
}

.adt-loading {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  color: var(--muted);
  font-size: var(--font-size-base);
  border-radius: var(--radius-sm);
}

.adt-error {
  padding: var(--space-lg);
  background: var(--warn-bg);
  border: 1px solid var(--warn-border);
  border-radius: var(--radius-sm);
  color: var(--warn-text);
  font-size: var(--font-size-sm);
  text-align: center;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.adt-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 6px 12px;
  border-bottom: 1px solid var(--line-table);
  background: var(--thead-bg);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  font-size: var(--font-size-sm);
  user-select: none;
  flex-shrink: 0;
}

.adt-toolbar-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--text-secondary);
}

.adt-toolbar-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--green);
  flex-shrink: 0;
}

.adt-toolbar-count {
  color: var(--muted);
  font-size: var(--font-size-xs);
}

.adt-toolbar-sep {
  width: 1px;
  height: 14px;
  background: var(--line);
  margin: 0 4px;
}

.adt-toolbar-density {
  display: flex;
  gap: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.adt-toolbar-density button {
  padding: 2px 10px;
  font-size: var(--font-size-xs);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
  line-height: 1.5;
}

.adt-toolbar-density button + button {
  border-left: 1px solid var(--line);
}

.adt-toolbar-density button.active {
  background: var(--green);
  color: #fff;
}

.adt-toolbar-density button:not(.active):hover {
  background: var(--green-3);
}

.adt-toolbar-hint {
  margin-left: auto;
  color: var(--muted);
  font-size: var(--font-size-xs);
}

.adt-toolbar-action {
  padding: 2px 10px;
  font-size: var(--font-size-xs);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
  white-space: nowrap;
}

.adt-toolbar-action:hover {
  background: var(--green-3);
  color: var(--green);
  border-color: var(--green);
}

.adt-toolbar-action-reset {
  color: var(--muted);
}

.adt-toolbar-action-reset:hover {
  color: var(--warn);
  border-color: var(--warn);
  background: var(--tag-warn-bg, #fffbeb);
}

.adt-toolbar-refresh {
  padding: 2px 8px;
  font-size: 16px;
  line-height: 1;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.adt-toolbar-refresh:hover {
  background: var(--green-3);
  color: var(--green);
  border-color: var(--green);
}

/* 列设置面板 */
.adt-col-panel-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
}

.adt-col-panel {
  z-index: 9999;
  min-width: 200px;
  max-width: 280px;
  max-height: 320px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  padding: 8px 0;
}

.adt-col-panel-title {
  padding: 4px 12px 8px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--line);
  margin-bottom: 4px;
}

.adt-col-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  font-size: var(--font-size-sm);
  color: var(--text);
  cursor: pointer;
  transition: background 0.1s;
}

.adt-col-item:hover {
  background: var(--green-3);
}

.adt-col-item input[type="checkbox"] {
  width: 15px;
  height: 15px;
  cursor: pointer;
  accent-color: var(--green);
}

.adt-col-item input[type="checkbox"]:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
