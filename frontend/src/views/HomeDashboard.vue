<template>
  <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>加载中...</p></div>
  <template v-else>
  <div class="section">
    <div class="metric-strip">
      <div class="metric">
        <div class="label">待处理任务</div>
        <div class="value" :class="overview.pending_tasks > 0 ? 'text-warn' : 'text-green'">{{ overview.pending_tasks || 0 }}</div>
        <div class="sub">异常 {{ overview.abnormal_count || 0 }} 条</div>
      </div>
      <div class="metric">
        <div class="label">今日生成状态</div>
        <div class="value" :class="overview.today_generated ? 'text-green' : 'text-warn'">{{ overview.today_generated ? '已完成' : '未完成' }}</div>
        <div class="sub">{{ overview.report_info }}</div>
      </div>
      <div class="metric">
        <div class="label">总收入</div>
        <div class="value text-green">{{ fmtAmt(metrics.total_income) }}</div>
        <div class="sub">所选区间</div>
      </div>
      <div class="metric">
        <div class="label">总支出</div>
        <div class="value text-warn">{{ fmtAmt(metrics.total_expense) }}</div>
        <div class="sub">净变动 {{ fmtAmt(metrics.net_change) }}</div>
      </div>
    </div>
  </div>

  <div class="dashboard-grid">
    <div class="section">
      <div class="section-title">
        <h3>今日处理进度</h3>
      </div>
      <div class="progress-list">
        <div class="progress-row" v-for="(label, key) in progressLabels" :key="key">
          <div>{{ label }}</div>
          <div class="progress-bar"><span :style="{ width: (overview.progress?.[key] || 0) + '%' }"></span></div>
          <div>{{ overview.progress?.[key] || 0 }}%</div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">
        <h3>系统提醒</h3>
      </div>
      <div class="warning-list">
        <div v-for="(r, i) in status.reminders" :key="i" class="warning" :class="r.type">
          <span class="warning-dot"></span>
          <span>{{ r.message }}</span>
        </div>
        <div v-if="!status.reminders?.length" class="empty-hint">暂无提醒</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">
      <h3>收支趋势（近 30 天）</h3>
    </div>
    <div ref="trendChart" style="height: 300px;"></div>
  </div>

  <div class="dashboard-grid-2">
    <div class="section">
      <div class="section-title"><h3>账户余额分布</h3></div>
      <div ref="pieChart" style="height: 280px;"></div>
    </div>
    <div class="section">
      <div class="section-title"><h3>重点账户</h3></div>
      <table v-if="overview.account_changes?.length">
        <thead><tr><th>账户名称</th><th>法人简称</th><th class="money">余额</th></tr></thead>
        <tbody>
          <tr v-for="a in overview.account_changes" :key="a.account_name">
            <td>{{ a.account_name }}</td>
            <td>{{ a.entity_name }}</td>
            <td class="money">{{ fmtAmt(a.balance) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-hint">暂无账户数据</div>
    </div>
  </div>
  </template>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getOverview, getSystemStatus } from '@/api/home'
import { getMetrics, getTrends, getComposition } from '@/api/dashboard'
import { fmtAmt } from '@/utils/format'

const loading = ref(true)
const overview = ref({})
const metrics = ref({})
const status = ref({})
const trendChart = ref(null)
const pieChart = ref(null)

const progressLabels = {
  bank_import: '网银导入',
  manual_flow: '手工流水',
  abnormal_fix: '异常处理',
  base_data: '基础数据表',
  daily_report: '日报生成',
}

onMounted(async () => {
  try {
    const [ov, mt, st, tr, cp] = await Promise.all([
      getOverview(), getMetrics({}), getSystemStatus(), getTrends({ days: 30 }), getComposition(),
    ])
    overview.value = ov || {}
    metrics.value = mt || {}
    status.value = st || {}

    // 先关闭 loading 让 DOM 渲染图表容器，再初始化 ECharts
    loading.value = false
    await nextTick()
    renderTrendChart(tr)
    renderPieChart(cp)
  } catch (e) {
    console.error('首页加载失败', e)
    loading.value = false
  }
})

function renderTrendChart(data) {
  if (!trendChart.value || !data?.dates?.length) return
  const chart = echarts.init(trendChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['收入', '支出'], top: 0 },
    grid: { top: 36, left: 50, right: 20, bottom: 30 },
    xAxis: { type: 'category', data: data.dates, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    series: [
      { name: '收入', type: 'line', smooth: true, data: data.income, itemStyle: { color: '#7f9b7a' }, areaStyle: { color: 'rgba(127,155,122,.12)' } },
      { name: '支出', type: 'line', smooth: true, data: data.expense, itemStyle: { color: '#c47a5a' }, areaStyle: { color: 'rgba(196,122,90,.1)' } },
    ],
  })
  window.addEventListener('resize', () => chart.resize())
}

function renderPieChart(data) {
  if (!pieChart.value || !data?.items?.length) return
  const chart = echarts.init(pieChart.value)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      label: { fontSize: 11 },
      data: data.items.map(it => ({ name: it.name, value: it.value })),
      itemStyle: { borderRadius: 6, borderColor: '#fbfaf7', borderWidth: 2 },
      color: ['#7f9b7a', '#a8bfa4', '#c47a5a', '#d4a574', '#6b8fad', '#8faabc'],
    }],
  })
  window.addEventListener('resize', () => chart.resize())
}
</script>

<style scoped>
@import './common.css';
.empty-hint { color: var(--muted); font-size: var(--font-size-sm); padding: 20px; text-align: center; }
</style>
