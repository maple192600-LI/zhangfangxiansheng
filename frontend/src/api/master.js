/**
 * 主数据 API — 板块 / 法人 / 银行 / 账户 / 别名 / usage / 批量操作
 */
import http from './index'

// ── 板块 ──
export const getDivisions = (status) =>
  http.get('/divisions', { params: { status } })

export const createDivision = (data) =>
  http.post('/divisions', data)

export const updateDivision = (id, data) =>
  http.put(`/divisions/${id}`, data)

export const updateDivisionStatus = (id, status) =>
  http.put(`/divisions/${id}/status`, { status })

export const deleteDivision = (id, force = false) =>
  http.delete(`/divisions/${id}`, { params: { force } })

export const getDivisionUsage = (id) =>
  http.get(`/divisions/${id}/usage`)

export const batchActionDivisions = (ids, action, cascade = false) =>
  http.post('/divisions/batch', { ids, action, cascade })

// ── 法人 ──
export const getEntities = (params) =>
  http.get('/entities', { params })

export const createEntity = (data) =>
  http.post('/entities', data)

export const updateEntity = (id, data) =>
  http.put(`/entities/${id}`, data)

export const updateEntityStatus = (id, status) =>
  http.put(`/entities/${id}/status`, { status })

export const deleteEntity = (id) =>
  http.delete(`/entities/${id}`)

export const getEntityUsage = (id) =>
  http.get(`/entities/${id}/usage`)

export const batchActionEntities = (ids, action, cascade = false) =>
  http.post('/entities/batch', { ids, action, cascade })

// ── 银行 ──
export const getBanks = (params) =>
  http.get('/banks', { params })

export const getBank = (id) =>
  http.get(`/banks/${id}`)

export const createBank = (data) =>
  http.post('/banks', data)

export const updateBank = (id, data) =>
  http.put(`/banks/${id}`, data)

export const updateBankStatus = (id, status) =>
  http.put(`/banks/${id}/status`, { status })

export const deleteBank = (id) =>
  http.delete(`/banks/${id}`)

export const getBankUsage = (id) =>
  http.get(`/banks/${id}/usage`)

export const batchActionBanks = (ids, action) =>
  http.post('/banks/batch', { ids, action })

// ── 账户 ──
export const getAccounts = (params) =>
  http.get('/accounts', { params })

export const getAccountsTree = () =>
  http.get('/accounts/tree')

export const createAccount = (data) =>
  http.post('/accounts', data)

export const updateAccount = (id, data) =>
  http.put(`/accounts/${id}`, data)

export const setInitialBalance = (id, data) =>
  http.post(`/accounts/${id}/initial-balance`, data)

export const batchActionAccounts = (ids, action) =>
  http.post('/accounts/batch', { ids, action })

// ── 别名 ──
export const getAliases = (accountId) =>
  http.get(`/accounts/${accountId}/aliases`)

export const createAlias = (accountId, data) =>
  http.post(`/accounts/${accountId}/aliases`, data)

export const deleteAlias = (accountId, aliasId) =>
  http.delete(`/accounts/${accountId}/aliases/${aliasId}`)

// ── 批量导入 ──
export const downloadAccountTemplate = () =>
  window.open('/api/accounts/template', '_blank')

export const importAccounts = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/accounts/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}
