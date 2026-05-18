import http from './index'

export const getPreview = (batchCode) =>
  http.get(`/import-preview/${batchCode}`)

export const updateRow = (batchCode, rowNo, updates) =>
  http.put(`/import-preview/${batchCode}/rows/${rowNo}`, { updates })

export const validateAll = (batchCode) =>
  http.post(`/import-preview/${batchCode}/validate`)

export const commitPreview = (batchCode) =>
  http.post(`/import-preview/${batchCode}/commit`)
