import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const { response } = error
    if (response) {
      switch (response.status) {
        case 401:
          const authStore = useAuthStore()
          authStore.logout()
          ElMessage.error('登录已过期，请重新登录')
          break
        case 403:
          ElMessage.error('没有权限执行此操作')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        default: {
          const detail = response.data?.detail
          let msg = '服务器错误'
          if (Array.isArray(detail)) {
            msg = detail.map((d: any) => {
              const m = d.msg || JSON.stringify(d)
              return translateValidationError(m)
            }).join('；')
          } else if (typeof detail === 'string') {
            msg = detail
          }
          ElMessage.error(msg)
        }
      }
    } else {
      ElMessage.error('网络连接失败')
    }
    return Promise.reject(error)
  }
)

function translateValidationError(msg: string): string {
  const map: Record<string, string> = {
    'String should have at least 4 characters': '内容不能少于4个字符',
    'String should have at least 2 characters': '内容不能少于2个字符',
    'String should have at least 6 characters': '内容不能少于6个字符',
    'String should have at most 50 characters': '内容不能超过50个字符',
    'String should have at most 100 characters': '内容不能超过100个字符',
    'Field required': '必填项不能为空',
    'value is not a valid string': '请输入有效内容',
  }
  return map[msg] || msg
}


export default api
