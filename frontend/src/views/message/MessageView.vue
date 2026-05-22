<template>
  <div class="message-page">
    <el-card shadow="never" class="message-card">
      <!-- 分类 Tab + 操作 -->
      <div class="message-page__toolbar">
        <el-tabs v-model="activeTab" class="message-tabs">
          <el-tab-pane label="全部" name="all" />
          <el-tab-pane label="排班通知" name="schedule" />
          <el-tab-pane label="调班通知" name="swap" />
          <el-tab-pane label="排班审核" name="approve" />
          <el-tab-pane label="公告" name="announcement" />
        </el-tabs>
        <div class="toolbar-actions">
          <el-badge :value="unreadTotal" :hidden="unreadTotal === 0" :max="99">
            <el-icon :size="20" style="cursor: default"><Bell /></el-icon>
          </el-badge>
        </div>
      </div>

      <!-- 消息列表 / 公告模块 -->
      <div class="message-page__content">
        <MessageList
          v-if="activeTab !== 'announcement'"
          ref="messageListRef"
          :msg-type="activeTab === 'all' ? undefined : activeTab"
          @open-detail="handleOpenDetail"
          @refresh-unread="fetchUnreadCount"
        />
        <AnnouncementSection v-else />
      </div>
    </el-card>

    <!-- 消息详情抽屉 -->
    <MessageDetailDrawer
      v-model:visible="drawerVisible"
      :message="currentMessage"
      @marked-read="handleMarkedRead"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import MessageList from './components/MessageList.vue'
import MessageDetailDrawer from './components/MessageDetailDrawer.vue'
import AnnouncementSection from './components/AnnouncementSection.vue'
import { getUnreadCount } from '@/api/message'
import { useMessageStore } from '@/stores/message'
import { useAuthStore } from '@/stores/auth'
import type { MessageItem } from '@/api/message'

const activeTab = ref('all')
const drawerVisible = ref(false)
const currentMessage = ref<MessageItem | null>(null)
const messageStore = useMessageStore()
const authStore = useAuthStore()
const unreadTotal = ref(0)
const messageListRef = ref<InstanceType<typeof MessageList> | null>(null)

let refreshTimer: ReturnType<typeof setInterval> | null = null

const fetchUnreadCount = async () => {
  if (!authStore.hasPermission('message', 'read')) return
  try {
    const { data: res } = await getUnreadCount()
    if (res.code === 200) {
      unreadTotal.value = res.data.total
    }
  } catch {
    // 静默失败
  }
}

const handleOpenDetail = (msg: MessageItem) => {
  currentMessage.value = msg
  drawerVisible.value = true
  // 如果该消息未读，标记已读后刷新角标
  if (!msg.is_read) {
    // 详情抽屉中标记已读后会触发 marked-read 事件
  }
}

const handleMarkedRead = () => {
  fetchUnreadCount()
  messageStore.fetchUnread()  // 立即刷新全局角标
  messageListRef.value?.refresh()
}

// 轮询方案（5 秒刷新一次未读数，关闭页面后停止）
const startPolling = () => {
  if (refreshTimer) return
  refreshTimer = setInterval(() => {
    fetchUnreadCount()
    messageStore.fetchUnread()
  }, 5000)
}

onMounted(() => {
  if (!authStore.hasPermission('message', 'read')) return
  fetchUnreadCount()
  startPolling()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
.message-page {
  padding: 0;
}

.message-card {
  border-radius: 6px;
}

.message-page__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.message-tabs {
  flex: 1;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 4px;
}

.message-page__content {
  min-height: 400px;
}
</style>
