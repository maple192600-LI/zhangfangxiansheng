import http from './index'

// 字段池
export const getFieldPool = () =>
  http.get('/manual-flow/field-pool')

// 方案
export const getSchemes = () =>
  http.get('/manual-flow/schemes')

export const createScheme = (data) =>
  http.post('/manual-flow/schemes', data)

export const updateScheme = (id, data) =>
  http.put(`/manual-flow/schemes/${id}`, data)

// 快速录入
export const saveQuickEntry = (data) =>
  http.post('/manual-flow/quick-entry/save', data)

// Excel 上传
export const uploadManualWorkbook = (file, schemeCode) => {
  const form = new FormData()
  form.append('file', file)
  form.append('scheme_code', schemeCode || 'manual_multi_subject_basic')
  return http.post('/manual-flow/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

// 预览与提交
export const previewManual = (data) =>
  http.post('/manual-flow/preview', data)

export const commitManual = (data) =>
  http.post('/manual-flow/commit', data)

// 导出模板
export const exportManualTemplate = (schemeCode) =>
  http.post('/manual-flow/export-template', { scheme_code: schemeCode }, { responseType: 'blob' })
