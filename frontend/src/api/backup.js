import http from './index'

export const listBackups = () => http.get('/backups')
export const createBackup = () => http.post('/backups/create')
export const restoreBackup = (filename) => http.post('/backups/restore', { filename })
