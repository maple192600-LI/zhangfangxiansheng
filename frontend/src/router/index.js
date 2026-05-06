import { createRouter, createWebHistory } from 'vue-router'

// 通用占位组件 — 所有未实现的页面共用
const Placeholder = () => import('@/views/Placeholder.vue')

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

      // 票据中心
      { path: 'ocr/upload', name: 'ocr-upload', component: Placeholder },
      { path: 'ocr/settings', name: 'ocr-settings', component: Placeholder },
      { path: 'invoice-ledger', name: 'invoice-ledger', component: Placeholder },
      { path: 'contract-ledger', name: 'contract-ledger', component: Placeholder },

      // 贷款管理
      { path: 'loan-ledger', name: 'loan-ledger', component: Placeholder },
      { path: 'loan-interest', name: 'loan-interest', component: Placeholder },
      { path: 'loan-other-ledger', name: 'loan-other-ledger', component: Placeholder },
      { path: 'loan-other', name: 'loan-other', component: Placeholder },

      // 预算管理
      { path: 'budget-plan', name: 'budget-plan', component: Placeholder },

      // AI智能体
      { path: 'agent/review/:type/:id', name: 'agent-review', component: () => import('@/views/AgentReview.vue') },
      { path: 'agents/:id', name: 'agent-detail', component: () => import('@/views/AgentDetail.vue') },
      { path: 'agent/social', name: 'agent-social', component: Placeholder },
      { path: 'agent/daily', name: 'agent-daily', component: Placeholder },
      { path: 'agent/cost', name: 'agent-cost', component: Placeholder },
      { path: 'agent/income', name: 'agent-income', component: Placeholder },
      { path: 'agent/material', name: 'agent-material', component: Placeholder },
      { path: 'agent/tax', name: 'agent-tax', component: Placeholder },
      { path: 'agent/custom', name: 'agent-custom', component: Placeholder },

      // 系统设置 > 数据中心
      { path: 'account-manage', name: 'account-manage', component: () => import('@/views/AccountManage.vue') },
      { path: 'data/report-tpl', name: 'data-report-tpl', component: () => import('@/views/ReportTemplate.vue') },
      { path: 'data/department', name: 'data-department', component: Placeholder },

      // 系统设置 > 规则中心
      { path: 'rule/bank', name: 'rule-bank', component: () => import('@/views/BankRule.vue') },
      { path: 'rule/io', name: 'rule-io', component: Placeholder },
      { path: 'rule/origin', name: 'rule-origin', component: Placeholder },
      { path: 'rule/voucher', name: 'rule-voucher', component: Placeholder },
      { path: 'rule/other', name: 'rule-other', component: Placeholder },

      // 系统设置 > 异常中心
      { path: 'exception/receipt', name: 'exception-receipt', component: () => import('@/views/ExceptionCenter.vue') },
      { path: 'exception/other', name: 'exception-other', component: () => import('@/views/ExceptionCenter.vue') },

      // 系统设置 > 模型配置
      { path: 'ai-config', name: 'ai-config', component: () => import('@/views/AIConfig.vue') },

      // 系统设置 > 用户和权限
      { path: 'perm/admin', name: 'perm-admin', component: Placeholder },
      { path: 'perm/cashier', name: 'perm-cashier', component: Placeholder },
      { path: 'perm/manager', name: 'perm-manager', component: Placeholder },
      { path: 'perm/boss', name: 'perm-boss', component: Placeholder },
      { path: 'perm/accountant', name: 'perm-accountant', component: Placeholder },

      // 系统设置 > 系统维护 / 操作日志
      { path: 'system-maintenance', name: 'system-maintenance', component: () => import('@/views/SystemMaintenance.vue') },
      { path: 'backup-restore', name: 'backup-restore', component: () => import('@/views/SystemMaintenance.vue') },
      { path: 'data-cleanup', name: 'data-cleanup', component: () => import('@/views/SystemMaintenance.vue') },
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
