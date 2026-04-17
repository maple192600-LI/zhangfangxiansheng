import http from './index'

export const exportReport = (data) => http.post('/export/report', data, { responseType: 'blob' })
