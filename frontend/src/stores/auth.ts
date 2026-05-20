import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getUserInfo as getUserInfoApi } from '@/api/auth'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userId = ref<number>(0)
  const username = ref<string>('')
  const roles = ref<string[]>([])
  const permissions = ref<Record<string, any>>({})
  const staffName = ref<string>('')
  const mustChangePassword = ref<boolean>(false)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => roles.value.includes('admin'))

  async function login(usernameInput: string, password: string) {
    const res: any = await loginApi({ username: usernameInput, password })
    token.value = res.access_token
    userId.value = res.user_id
    username.value = res.username
    roles.value = res.roles
    mustChangePassword.value = res.must_change_password || false
    localStorage.setItem('token', res.access_token)
    if (mustChangePassword.value) {
      // 不持久化，刷新即回到登录页
    } else {
      await fetchUserInfo()
    }
  }

  async function fetchUserInfo() {
    const res: any = await getUserInfoApi()
    userId.value = res.id
    username.value = res.username
    roles.value = res.roles
    permissions.value = res.permissions
    staffName.value = res.staff_name || ''
    // 后端同步校验强制改密状态
    if (res.must_change_password) {
      // 后端返回需要改密，强制登出，回到登录页
      logout()
    }
  }

  function logout() {
    token.value = ''
    userId.value = 0
    username.value = ''
    roles.value = []
    permissions.value = {}
    staffName.value = ''
    mustChangePassword.value = false
    localStorage.removeItem('token')
    router.push('/login')
  }

  function hasRole(role: string): boolean {
    return isAdmin.value || roles.value.includes(role)
  }

  function hasPermission(resource: string, action: string): boolean {
    if (isAdmin.value || permissions.value.all) return true
    const resourcePerms = permissions.value[resource]
    return Array.isArray(resourcePerms) && resourcePerms.includes(action)
  }

  function hasAnyPermission(resource: string): boolean {
    if (isAdmin.value || permissions.value.all) return true
    const resourcePerms = permissions.value[resource]
    return Array.isArray(resourcePerms) && resourcePerms.length > 0
  }

  return {
    token, userId, username, roles, permissions, staffName,
    isAuthenticated, isAdmin, mustChangePassword,
    login, fetchUserInfo, logout, hasRole, hasPermission, hasAnyPermission,
  }
})
