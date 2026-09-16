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
      const msg =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail[0]?.msg ?? '请求参数错误'
            : error.message ?? '网络错误'
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  },
)

export default client
