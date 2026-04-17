import http from './index'

export const queryLogs = (params) => http.get('/logs', { params })
