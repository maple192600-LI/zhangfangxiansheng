import http from './index'

// 基础数据
export const getBaseData = (params) =>
  http.get('/base-data', { params })

export const rebuildBalance = () =>
  http.post('/base-data/rebuild')

export const batchDeleteBaseData = (ids) =>
  http.post('/base-data/batch-delete', { ids })

// 报表
export const getDailyReport = (params) =>
  http.get('/reports/daily', { params })

export const getCashJournal = (params) =>
  http.get('/reports/cash-journal', { params })

export const getAccountBalance = (params) =>
  http.get('/reports/account-balance', { params })

export const getIncomeList = (params) =>
  http.get('/reports/income-list', { params })

export const getExpenseList = (params) =>
  http.get('/reports/expense-list', { params })

// 综合报表
const REPORT_PATH_MAP = {
  major_balance: '/reports/major-balance',
  month_check: '/reports/month-check',
  week_report: '/reports/week-report',
  month_report: '/reports/month-report',
  year_report: '/reports/year-report',
}

export const getReport = (reportType, params) => {
  const path = REPORT_PATH_MAP[reportType]
  if (!path) return Promise.reject(new Error(`Unknown report type: ${reportType}`))
  return http.get(path, { params })
}
