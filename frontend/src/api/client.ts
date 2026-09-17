import axios from 'axios'
import { ElMessage } from 'element-plus'

export const TOKEN_KEY = 'labflow_token'
export const USER_KEY = 'labflow_user'

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    if (!error.config?.silent) {
      const detail = error.response?.data?.detail
      let msg: string
      if (typeof detail === 'string') {
        msg = detail
      } else if (detail && typeof detail === 'object' && 'message' in detail) {
        // structured AI errors: {code, message}
        msg = (detail as { message: string }).message
      } else if (Array.isArray(detail)) {
        msg = detail[0]?.msg ?? '请求参数错误'
      } else {
        msg = error.message ?? '网络错误'
      }
      ElMessage.error(msg)
    }
    error.handledCode = error.response?.data?.detail?.code
    return Promise.reject(error)
  },
)

export default client
