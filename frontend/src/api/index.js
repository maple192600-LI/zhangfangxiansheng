import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 响应拦截器 — 统一处理 code
http.interceptors.response.use(
  (res) => {
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
