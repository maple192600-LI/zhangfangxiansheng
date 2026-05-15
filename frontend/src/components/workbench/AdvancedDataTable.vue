<template>
  <div class="adt-wrap" :class="densityClass">
    <div v-if="errorText" class="adt-error">
      {{ errorText }}
    </div>
    <div v-else-if="loading" class="adt-loading">{{ loadingText }}</div>
    <div
      v-show="!errorText && !loading"
      ref="containerRef"
      class="adt-container"
      :style="{ height: height || undefined }"
    ></div>
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
})

const emit = defineEmits([
  'rowClick',
  'rowDblClick',
  'selectionChange',
  'tableReady',
  'tableError',
])

const containerRef = ref(null)

const densityClass = computed(() => {
  if (props.density === 'compact') return 'adt-density-compact'
  if (props.density === 'comfortable') return 'adt-density-comfortable'
  return ''
})

const { table, isReady, updateData, updateColumns, destroyTable, getSelectedRows, clearSelection } =
  useTabulatorTable(containerRef, {
    get columns() { return props.columns },
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
      ...(props.height ? { height: props.height } : {}),
    },
  })

watch(() => props.data, (newData) => {
  if (isReady.value) {
    updateData(newData)
  }
})

watch(() => props.columns, (newCols) => {
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
  } catch { /* ignore */ }
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

.adt-container {
  width: 100%;
  min-height: 200px;
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

/* density: compact */
.adt-density-compact :deep(.tabulator .tabulator-header .tabulator-col .tabulator-col-content) {
  padding: 5px 6px;
}
.adt-density-compact :deep(.tabulator .tabulator-tableHolder .tabulator-table .tabulator-row .tabulator-cell) {
  padding: 3px 6px;
}

/* density: comfortable */
.adt-density-comfortable :deep(.tabulator .tabulator-header .tabulator-col .tabulator-col-content) {
  padding: 12px 14px;
}
.adt-density-comfortable :deep(.tabulator .tabulator-tableHolder .tabulator-table .tabulator-row .tabulator-cell) {
  padding: 10px 14px;
}
</style>
