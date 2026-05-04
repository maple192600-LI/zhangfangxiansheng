import http from './index'

export const listBackups = () => http.get('/backups')
export const createBackup = () => http.post('/backups/create')
export const restoreBackup = (filename) => http.post('/backups/restore', { filename })
export const factoryReset = () => http.post('/reset/factory')
export const getCleanupPreview = () => http.get('/backups/cleanup/preview')
export const executeCleanup = () => http.post('/backups/cleanup/execute')
