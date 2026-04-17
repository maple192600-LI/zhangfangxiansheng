import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 300000
})

// 请求拦截器 — 注入 Authorization header
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('zf_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 — 统一处理 code + 401 跳转
http.interceptors.response.use(
  (res) => {
    // blob 响应直接返回（导出模板等）
    if (res.config.responseType === 'blob') {
      return res.data
    }
    const { code, message, data } = res.data
    if (code === 0) {
      return data
    }
    return Promise.reject(new Error(message || '请求失败'))
  },
  (err) => {
    // 401 未认证 — 清除 token 并跳转登录页
    if (err.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('zf_token')
      localStorage.removeItem('zf_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default http
