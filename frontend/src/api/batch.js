import http from './index'

export const listBatches = (params) => http.get('/batches', { params })
export const rollbackBatch = (batchId) => http.post(`/batches/${batchId}/rollback`)
