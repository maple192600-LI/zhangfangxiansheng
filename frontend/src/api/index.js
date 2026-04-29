import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 300000
})

// 请求拦截器 — 注入 Authorization header + 防 GET 缓存
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('zf_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // 给所有 GET 请求加时间戳，避免浏览器/代理缓存返回旧数据
  // （删除/上传模板后，业务页面立即拉到最新数据）
  if ((config.method || 'get').toLowerCase() === 'get') {
    config.params = { ...(config.params || {}), _t: Date.now() }
    config.headers['Cache-Control'] = 'no-cache'
    config.headers['Pragma'] = 'no-cache'
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
    if (err.response?.data?.message) {
      return Promise.reject(new Error(err.response.data.message))
    }
    return Promise.reject(err)
  }
)

export default http
