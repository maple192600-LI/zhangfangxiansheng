<template>
  <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>加载中...</p></div>
  <template v-else>
  <div class="section">
    <div class="section-title">
      <h3>待办追踪</h3>
      <span>共 {{ totalCount }} 项待处理</span>
    </div>
    <div class="kanban">
      <div class="kanban-col">
        <h5>待导入 ({{ todos.counts?.import || 0 }})</h5>
        <div v-for="t in todos.to_import" :key="t.batch_code" class="task">
          <strong>{{ t.source_name }}</strong>
          <div>{{ t.row_count }} 行</div>
        </div>
        <div v-if="!todos.to_import?.length" class="empty-hint">无待导入</div>
      </div>
      <div class="kanban-col">
        <h5>待确认 ({{ todos.counts?.confirm || 0 }})</h5>
        <div v-for="t in todos.to_confirm" :key="t.id" class="task">
          <strong>{{ t.summary }}</strong>
          <span class="tag tag-warn" v-if="t.abnormal_code">{{ t.abnormal_code }}</span>
        </div>
        <div v-if="!todos.to_confirm?.length" class="empty-hint">无待确认</div>
      </div>
      <div class="kanban-col">
        <h5>待生成 ({{ todos.counts?.generate || 0 }})</h5>
        <div v-for="t in todos.to_generate" :key="t" class="task">{{ t }}</div>
        <div v-if="!todos.to_generate?.length" class="empty-hint">全部就绪</div>
      </div>
    </div>
  </div>
  </template>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getTodos } from '@/api/home'

const loading = ref(true)
const todos = ref({ to_import: [], to_confirm: [], to_generate: [], counts: {} })

const totalCount = computed(() => {
  const c = todos.value.counts || {}
  return (c.import || 0) + (c.confirm || 0) + (c.generate || 0)
})

onMounted(async () => {
  try {
    todos.value = await getTodos() || {}
  } catch (e) {
    console.error('待办加载失败', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
@import './common.css';
.empty-hint { color: var(--muted); font-size: var(--font-size-xs); padding: 16px; text-align: center; }
</style>
