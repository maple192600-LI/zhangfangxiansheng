import http from './index'

export const getMetrics = (params) => http.get('/dashboard/metrics', { params })
export const getTrends = (params) => http.get('/dashboard/trends', { params })
export const getComposition = () => http.get('/dashboard/composition')
