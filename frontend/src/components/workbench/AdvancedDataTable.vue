<template>
  <div class="adt-wrap" :class="[densityClass, { 'adt-fill': isFillMode }]">
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
  rowClass: { type: Function, default: null },
})

const emit = defineEmits([
  'rowClick',
  'rowDblClick',
  'selectionChange',
  'tableReady',
  'tableError',
])

const containerRef = ref(null)

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
  if (props.density === 'compact') return 'adt-density-compact'
  if (props.density === 'comfortable') return 'adt-density-comfortable'
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
      resizableColumns: props.enableColumnResize,
      movableColumns: props.enableColumnMove,
      ...(tabulatorHeight.value ? { height: tabulatorHeight.value } : {}),
      ...(props.rowClass ? {
        rowFormatter: (row) => {
          const cls = props.rowClass(row.getData())
          if (cls) row.getElement().classList.add(...cls.split(/\s+/).filter(Boolean))
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
}

.adt-wrap.adt-fill > .adt-container {
  height: 100%;
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
</style>
