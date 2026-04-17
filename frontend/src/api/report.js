import http from './index'

// 基础数据
export const getBaseData = (params) =>
  http.get('/base-data', { params })

export const rebuildBalance = () =>
  http.post('/base-data/rebuild')

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
