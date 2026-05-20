import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getUnreadCount } from '@/api/message'

export const useMessageStore = defineStore('message', () => {
  const unreadCount = ref(0)
  const byType = ref<Record<string, number>>({})
  let timer: ReturnType<typeof setInterval> | null = null

  const fetchUnread = async () => {
    try {
      const { data: res } = await getUnreadCount()
      if (res.code === 200) {
        unreadCount.value = res.data.total
        byType.value = res.data.by_type || {}
      }
    } catch {
      // 静默
    }
  }

  const startPolling = (interval = 30000) => {
    fetchUnread()
    if (timer) clearInterval(timer)
    timer = setInterval(fetchUnread, interval)
  }

  const stopPolling = () => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return { unreadCount, byType, fetchUnread, startPolling, stopPolling }
})
