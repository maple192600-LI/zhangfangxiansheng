import http from './index'

export const login = (data) => http.post('/auth/login', data)
export const changePassword = (data) => http.post('/auth/change-password', data)
export const getMe = () => http.get('/auth/me')
