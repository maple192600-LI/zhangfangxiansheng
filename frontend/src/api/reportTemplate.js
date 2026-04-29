import http from './index'

const BASE = '/report-templates'

export function getReportTypes() {
  return http.get(`${BASE}/types`)
}

export function getTemplates(params) {
  return http.get(BASE, { params })
}

export function getTemplate(id) {
  return http.get(`${BASE}/${id}`)
}

export function getDefaultTemplate(reportType) {
  return http.get(`${BASE}/default/${reportType}`)
}

export function createTemplate(data) {
  return http.post(BASE, data)
}

export function updateTemplate(id, data) {
  return http.put(`${BASE}/${id}`, data)
}

export function deleteTemplate(id) {
  return http.delete(`${BASE}/${id}`)
}

export function setDefaultTemplate(id) {
  return http.put(`${BASE}/${id}/set-default`)
}

export function uploadExcel(file, reportType, opts = {}) {
  const formData = new FormData()
  formData.append('file', file)
  const params = {}
  if (reportType) params.report_type = reportType
  if (opts.template_name) params.template_name = opts.template_name
  if (opts.save === false) params.save = false
  return http.post(`${BASE}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params,
    timeout: 120000,
  })
}
