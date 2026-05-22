import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '',
  timeout: 30000,
})

// 请求拦截器：自动携带 Token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response) {
      const { status, data } = error.response

      // 处理 blob 类型的错误响应（导出接口返回 JSON 错误时，data 是 Blob）
      let detail = ''
      if (data instanceof Blob && data.type?.includes('application/json')) {
        try {
          const text = await data.text()
          const json = JSON.parse(text)
          detail = json.detail || json.message || ''
        } catch {
          // 解析失败，忽略
        }
      } else {
        detail = data?.detail || data?.message || ''
      }

      if (status === 401) {
        localStorage.removeItem('token')
        router.push('/login')
        ElMessage.error('登录已过期，请重新登录')
      } else if (status === 403) {
        if (detail.includes('权限')) {
          ElMessage.warning(detail)
        } else {
          ElMessage.warning('您没有该操作的权限，如需请联系管理员')
        }
      } else if (status === 500) {
        ElMessage.error('服务器错误')
      } else {
        ElMessage.error(detail || '请求失败')
      }
    } else {
      ElMessage.error('网络连接失败')
    }
    return Promise.reject(error)
  }
)

export default request
