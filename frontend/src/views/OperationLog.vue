<template>
  <div class="section">
    <div class="section-title">
      <h3>操作日志</h3>
    </div>

    <div class="filters-bar">
      <NSelect v-model:value="filters.module" :options="moduleOptions" placeholder="全部模块" clearable style="max-width:140px" @update:value="loadLogs" />
      <NSelect v-model:value="filters.action" :options="actionOptions" placeholder="全部操作" clearable style="max-width:140px" @update:value="loadLogs" />
      <NDatePicker v-model:value="filters.start_date" type="date" value-format="yyyy-MM-dd" clearable style="max-width:150px" @update:value="loadLogs" />
      <NDatePicker v-model:value="filters.end_date" type="date" value-format="yyyy-MM-dd" clearable style="max-width:150px" @update:value="loadLogs" />
      <NButton secondary @click="resetFilters">重置</NButton>
    </div>

    <table v-if="logs.length">
      <thead>
        <tr><th>时间</th><th>模块</th><th>操作</th><th>批次</th><th>详情</th></tr>
      </thead>
      <tbody>
        <tr v-for="log in logs" :key="log.id">
          <td>{{ log.created_at }}</td>
          <td><span class="tag tag-blue">{{ log.module }}</span></td>
          <td>{{ log.action }}</td>
          <td>{{ log.batch_id || '-' }}</td>
          <td class="detail-cell">{{ formatDetail(log.detail) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty-state">
      <div class="empty-icon">📝</div>
      <h4>暂无日志</h4>
      <p>操作日志将随系统使用自动记录</p>
    </div>

    <div class="bottom-bar" v-if="totalPages > 1">
      <span class="count-info">共 {{ total }} 条 / 第 {{ page }} 页</span>
      <NButton secondary size="small" :disabled="page <= 1" @click="page--; loadLogs()">上一页</NButton>
      <NButton secondary size="small" :disabled="page >= totalPages" @click="page++; loadLogs()">下一页</NButton>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NDatePicker, NSelect, NButton } from 'naive-ui'
import { queryLogs } from '@/api/log'

const logs = ref([])
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)
const filters = ref({ module: null, action: '', start_date: null, end_date: null })

const modules = ['bank_import', 'manual_flow', 'base_data', 'daily_report', 'export', 'backup', 'batch']
const actions = ['batch_upload', 'batch_commit', 'report_rebuild', 'report_generate', 'export_excel', 'backup_create', 'backup_restore', 'batch_rollback']
const moduleOptions = modules.map(m => ({ label: m, value: m }))
const actionOptions = actions.map(a => ({ label: a, value: a }))

onMounted(loadLogs)

async function loadLogs() {
  try {
    const params = { page: page.value, page_size: 30 }
    if (filters.value.module) params.module = filters.value.module
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date

    const data = await queryLogs(params)
    logs.value = data?.items || []
    total.value = data?.total || 0
    totalPages.value = data?.total_pages || 1
  } catch (e) {
    console.error('日志加载失败', e)
  }
}

function resetFilters() {
  filters.value = { module: '', action: '', start_date: '', end_date: '' }
  page.value = 1
  loadLogs()
}

function formatDetail(detail) {
  if (!detail || typeof detail !== 'object') return '-'
  return Object.entries(detail).map(([k, v]) => `${k}=${v}`).join(', ')
}
</script>

<style scoped>
@import './common.css';
.detail-cell { white-space: normal; max-width: 300px; font-size: var(--font-size-xs); color: var(--text-tertiary); }
</style>
