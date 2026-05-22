import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/index'

export const useSystemStore = defineStore('system', () => {
  const systemName = ref<string>(localStorage.getItem('systemName') || '排班管理系统')
  const orgName = ref<string>(localStorage.getItem('orgName') || '')
  const swapApprovalEnabled = ref<boolean>(localStorage.getItem('swapApproval') !== 'false')

  async function fetchConfig() {
    try {
      const res: any = await api.get('/system/config/overview')
      const data = res.data || res
      systemName.value = data.system_name || systemName.value
      orgName.value = data.org_name ?? orgName.value
      swapApprovalEnabled.value = data.swap_approval_enabled ?? swapApprovalEnabled.value
      localStorage.setItem('systemName', systemName.value)
      localStorage.setItem('orgName', orgName.value)
      localStorage.setItem('swapApproval', String(swapApprovalEnabled.value))
    } catch (e) {
      // 使用 localStorage 缓存的默认值
    }
  }

  return {
    systemName,
    orgName,
    swapApprovalEnabled,
    fetchConfig,
  }
})
