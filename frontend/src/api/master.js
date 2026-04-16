/**
 * 主数据 API — 板块 / 法人 / 账户 / 别名
 */
import http from './index'

// ── 板块 ──
export const getDivisions = (status) =>
  http.get('/divisions', { params: { status } })

export const createDivision = (data) =>
  http.post('/divisions', data)

export const updateDivision = (id, data) =>
  http.put(`/divisions/${id}`, data)

// ── 法人 ──
export const getEntities = (params) =>
  http.get('/entities', { params })

export const createEntity = (data) =>
  http.post('/entities', data)

export const updateEntity = (id, data) =>
  http.put(`/entities/${id}`, data)

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
