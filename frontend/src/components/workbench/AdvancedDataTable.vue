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
      <button v-if="showRefresh" class="adt-toolbar-refresh" @click="emit('refresh')" title="刷新数据">↻</button>
    </div>
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
})

const emit = defineEmits([
  'rowClick',
  'rowDblClick',
  'selectionChange',
  'tableReady',
  'tableError',
  'densityChange',
  'refresh',
])

const containerRef = ref(null)

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

const { table, isReady, updateData, updateColumns, destroyTable, getSelectedRows, clearSelection } =
  useTabulatorTable(containerRef, {
    get columns() { return resolvedColumns.value },
    get data() { return props.data },
    pagination: props.pagination,
    paginationSize: props.paginationSize,
    emptyText: props.emptyText,
    rowClick: (e, data) => emit('rowClick', data),
    rowDblClick: (e, data) => emit('rowDblClick', data),
    onSelectionChange: (data) => emit('selectionChange', data),
    onTableReady: () => emit('tableReady'),
    onTableError: (msg) => emit('tableError', msg),
    tabulatorOverrides: {
      index: props.rowKey,
      selectableRows: props.enableSelection ? true : false,
      resizableColumns: props.enableColumnResize || props.showToolbar,
      movableColumns: props.enableColumnMove,
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
</style>
