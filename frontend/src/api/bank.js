/**
 * 银行导入 API
 */
import http from './index'

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
