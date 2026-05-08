import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // 登录页 — 顶层路由，不走 MainLayout
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      // 首页
      { path: '', name: 'home', component: () => import('@/views/HomeDashboard.vue') },
      { path: 'home/tasks', name: 'home-tasks', component: () => import('@/views/HomeTasks.vue') },
      { path: 'home/quick', name: 'home-quick', component: () => import('@/views/HomeQuick.vue') },
      { path: 'home/system', name: 'home-system', component: () => import('@/views/HomeSystem.vue') },

      // 资金板块 > 工作台
      { path: 'bank-import', name: 'bank-import', component: () => import('@/views/BankImport.vue') },
      { path: 'manual-flow', name: 'manual-flow', component: () => import('@/views/ManualFlow.vue') },
      { path: 'manual-maintenance', name: 'manual-maintenance', component: () => import('@/views/ManualMaintenance.vue') },
      { path: 'upload-preview', name: 'upload-preview', component: () => import('@/views/UploadPreview.vue') },

      // 资金板块 > 资金日报表
      { path: 'daily-report', name: 'daily-report', component: () => import('@/views/DailyReport.vue') },
      { path: 'base-data', name: 'base-data', component: () => import('@/views/BaseDataTable.vue') },
      { path: 'cash-journal', name: 'cash-journal', component: () => import('@/views/CashJournal.vue') },
      { path: 'account-balance', name: 'account-balance', component: () => import('@/views/AccountBalance.vue') },
      { path: 'income-list', name: 'income-list', component: () => import('@/views/IncomeList.vue') },
      { path: 'expense-list', name: 'expense-list', component: () => import('@/views/ExpenseList.vue') },

      // 资金板块 > 资金综合报表
      { path: 'major-balance', name: 'major-balance', component: () => import('@/views/MajorBalance.vue') },
      { path: 'month-check', name: 'month-check', component: () => import('@/views/MonthCheck.vue') },
      { path: 'week-report', name: 'week-report', component: () => import('@/views/WeekReport.vue') },
      { path: 'month-report', name: 'month-report', component: () => import('@/views/MonthReport.vue') },
      { path: 'year-report', name: 'year-report', component: () => import('@/views/YearReport.vue') },

      // AI 智能体
      { path: 'agent/review/:type/:id', name: 'agent-review', component: () => import('@/views/AgentReview.vue') },
      { path: 'agents/:id', name: 'agent-detail', component: () => import('@/views/AgentDetail.vue') },

      // 系统设置 > 数据中心
      { path: 'account-manage', name: 'account-manage', component: () => import('@/views/AccountManage.vue') },
      { path: 'data/report-tpl', name: 'data-report-tpl', component: () => import('@/views/ReportTemplate.vue') },

      // 系统设置 > 规则中心
      { path: 'rules', name: 'rules', component: () => import('@/views/BankRule.vue') },

      // 系统设置 > 异常中心
      { path: 'exception', name: 'exception', component: () => import('@/views/ExceptionCenter.vue') },

      // 系统设置 > 模型配置
      { path: 'ai-config', name: 'ai-config', component: () => import('@/views/AIConfig.vue') },

      // 系统设置 > 系统维护 / 操作日志
      { path: 'system-maintenance', name: 'system-maintenance', component: () => import('@/views/SystemMaintenance.vue') },
      { path: 'operation-log', name: 'operation-log', component: () => import('@/views/OperationLog.vue') },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 导航守卫 — 未登录跳转 /login
router.beforeEach((to) => {
  const token = localStorage.getItem('zf_token')
  if (!token && to.name !== 'login') {
    return { name: 'login' }
  }
  if (token && to.name === 'login') {
    return { name: 'home' }
  }
})

export default router
