import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 300000
})

// 响应拦截器 — 统一处理 code
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
    return Promise.reject(err)
  }
)

export default http
