<template>
  <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>加载中...</p></div>
  <template v-else>
  <div class="section">
    <div class="section-title"><h3>系统提醒</h3></div>
    <div class="warning-list">
      <div v-for="(r, i) in status.reminders" :key="i" class="warning" :class="r.type">
        <span class="warning-dot"></span>
        <span>{{ r.message }}</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title"><h3>最近操作</h3></div>
    <table v-if="status.recent_actions?.length">
      <thead>
        <tr><th>操作</th><th>模块</th><th>时间</th></tr>
      </thead>
      <tbody>
        <tr v-for="(a, i) in status.recent_actions" :key="i">
          <td>{{ a.action }}</td>
          <td>{{ a.module }}</td>
          <td>{{ a.time }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty-hint">暂无操作记录</div>
  </div>
  </template>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSystemStatus } from '@/api/home'

const loading = ref(true)
const status = ref({ reminders: [], recent_actions: [] })

onMounted(async () => {
  try {
    status.value = await getSystemStatus() || {}
  } catch (e) {
    console.error('系统状态加载失败', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
@import './common.css';
.empty-hint { color: var(--muted); font-size: var(--font-size-sm); padding: 20px; text-align: center; }
</style>
