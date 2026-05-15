<template>
  <div class="adt-wrap">
    <div v-if="loading" class="adt-loading">{{ loadingText }}</div>
    <div ref="containerRef" class="adt-container" :style="{ height: height || undefined }"></div>
  </div>
</template>

<script setup>
import { ref, watch, toRef } from 'vue'
import 'tabulator-tables/dist/css/tabulator.min.css'
import '@/styles/tabulator-theme.css'
import { useTabulatorTable } from '@/composables/useTabulatorTable'

const props = defineProps({
  columns: { type: Array, required: true },
  data: { type: Array, default: () => [] },
  height: { type: String, default: '' },
  pagination: { type: Boolean, default: true },
  paginationSize: { type: Number, default: 50 },
  loading: { type: Boolean, default: false },
  loadingText: { type: String, default: '加载中...' },
})

const emit = defineEmits(['rowClick'])

const containerRef = ref(null)

const { table, isReady, updateData, updateColumns } = useTabulatorTable(containerRef, {
  get columns() { return props.columns },
  get data() { return props.data },
  pagination: props.pagination,
  paginationSize: props.paginationSize,
  rowClick: (e, row) => {
    emit('rowClick', row.getData())
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

defineExpose({ table, isReady, updateData, updateColumns })
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
</style>
