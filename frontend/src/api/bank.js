/**
 * 银行导入 + 解析模板 API
 */
import http from './index'

// ── 银行导入 ──
export const uploadBankFile = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/bank-import/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

export const previewBankImport = (data) =>
  http.post('/bank-import/preview', data)

export const commitBankImport = (data) =>
  http.post('/bank-import/commit', data)

// ── 解析模板 ──
export const getParserTemplates = (params) =>
  http.get('/parser-templates', { params })

export const createParserTemplate = (data) =>
  http.post('/parser-templates', data)

export const updateParserTemplate = (id, data) =>
  http.put(`/parser-templates/${id}`, data)

export const deleteParserTemplate = (id) =>
  http.delete(`/parser-templates/${id}`)

export const batchDeleteParserTemplates = (ids) =>
  http.post('/parser-templates/batch-delete', { ids })

// ── AI 智能解析 ──
export const aiParseHeaders = (data) =>
  http.post('/bank-import/ai-parse', data)

// ── 获取可用智能体列表 ──
export const getAgents = () =>
  http.get('/agent/agents')

export const saveAsTemplate = (data) =>
  http.post('/bank-import/save-template', data)
