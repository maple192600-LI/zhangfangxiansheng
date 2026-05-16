<template>
  <div class="section table-workspace-page">
    <div class="section-title">
      <h3>操作日志</h3>
    </div>

    <div class="filters-bar">
      <NSelect v-model:value="filters.module" :options="moduleOptions" placeholder="全部模块" clearable filterable class="filter-select-sm" :consistent-menu-width="false" @update:value="loadLogs" />
      <NSelect v-model:value="filters.action" :options="actionOptions" placeholder="全部操作" clearable filterable class="filter-select-sm" :consistent-menu-width="false" @update:value="loadLogs" />
      <NDatePicker v-model:value="filters.start_date" type="date" value-format="yyyy-MM-dd" clearable @update:value="loadLogs" />
      <NDatePicker v-model:value="filters.end_date" type="date" value-format="yyyy-MM-dd" clearable @update:value="loadLogs" />
      <NButton secondary @click="resetFilters">重置</NButton>
    </div>

    <div class="table-workspace-main">
      <AdvancedDataTable
        :columns="columns"
        :data="logs"
        :pagination="false"
        :loading="loading"
        fill-parent
        show-toolbar
        :total-rows="total"
        empty-text="暂无日志"
      />
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
import AdvancedDataTable from '@/components/workbench/AdvancedDataTable.vue'
import { emptyDashFormatter, tagTextFormatter, detailFormatter } from '@/utils/tabulatorFormatters'

const logs = ref([])
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)
const loading = ref(false)
const filters = ref({ module: null, action: '', start_date: null, end_date: null })

const columns = [
  { field: 'created_at', title: '时间', formatter: emptyDashFormatter, width: 180 },
  { field: 'module', title: '模块', formatter: tagTextFormatter, width: 140 },
  { field: 'action', title: '操作', formatter: emptyDashFormatter, width: 160 },
  { field: 'batch_id', title: '批次', formatter: emptyDashFormatter, width: 160 },
  { field: 'detail', title: '详情', formatter: detailFormatter },
]

const modules = ['bank_import', 'manual_flow', 'base_data', 'daily_report', 'export', 'backup', 'batch']
const actions = ['batch_upload', 'batch_commit', 'report_rebuild', 'report_generate', 'export_excel', 'backup_create', 'backup_restore', 'batch_rollback']
const moduleOptions = modules.map(m => ({ label: m, value: m }))
const actionOptions = actions.map(a => ({ label: a, value: a }))

onMounted(loadLogs)

async function loadLogs() {
  try {
    loading.value = true
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
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value = { module: null, action: '', start_date: null, end_date: null }
  page.value = 1
  loadLogs()
}
</script>

<style scoped>
@import './common.css';
</style>
