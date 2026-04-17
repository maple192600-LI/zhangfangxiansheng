import http from './index'

export const getOverview = () => http.get('/home/overview')
export const getTodos = () => http.get('/home/todos')
export const getQuickLinks = () => http.get('/home/quick-links')
export const getSystemStatus = () => http.get('/home/system-status')
