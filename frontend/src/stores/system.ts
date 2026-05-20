import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getSystemConfig } from '@/api/system'

export const useSystemStore = defineStore('system', () => {
  const systemName = ref<string>(localStorage.getItem('systemName') || '排班管理系统')
  const orgName = ref<string>(localStorage.getItem('orgName') || '')
  const swapApprovalEnabled = ref<boolean>(localStorage.getItem('swapApproval') !== 'false')

  async function fetchConfig() {
    try {
      const res = await getSystemConfig()
      systemName.value = res.system_name
      orgName.value = res.org_name
      swapApprovalEnabled.value = res.swap_approval_enabled
      localStorage.setItem('systemName', res.system_name)
      localStorage.setItem('orgName', res.org_name)
      localStorage.setItem('swapApproval', String(res.swap_approval_enabled))
    } catch (e) {
      // 使用默认值
    }
  }

  return {
    systemName,
    orgName,
    swapApprovalEnabled,
    fetchConfig,
  }
})
