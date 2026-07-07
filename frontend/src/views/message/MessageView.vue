<template>
  <div class="message-page">
    <!-- 顶部工具栏 -->
    <div class="page-header">
      <div class="page-header__left">
        <h1 class="page-title">消息中心</h1>
        <span v-if="unreadTotal > 0" class="neo-badge neo-badge--active">{{ unreadTotal }} 条未读</span>
      </div>
      <div class="page-header__actions">
        <el-button class="btn-neo-primary btn-neo-sm" @click="handleMarkAllRead">
          <el-icon><Check /></el-icon>
          <span>全部已读</span>
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar neo-card">
      <div class="filter-bar__search">
        <el-input
          v-model="keyword"
          placeholder="搜索消息内容..."
          clearable
          class="filter-bar__input"
          @input="debounceFetch"
        />
      </div>
      <div class="filter-bar__filters">
        <el-select v-model="statusFilter" placeholder="全部消息" class="filter-bar__select" @change="onFilterChange">
          <el-option label="全部消息" value="all" />
          <el-option label="未读消息" value="unread" />
          <el-option label="已读消息" value="read" />
        </el-select>
        <el-select v-model="typeFilter" placeholder="全部类型" class="filter-bar__select" @change="onFilterChange">
          <el-option label="全部类型" value="all" />
          <el-option label="系统通知" value="system" />
          <el-option label="排班通知" value="schedule" />
          <el-option label="调班申请" value="swap" />
          <el-option label="审批通知" value="approve" />
        </el-select>
      </div>
    </div>

    <!-- 分类 Tab + 内容 -->
    <el-card shadow="never" class="message-card">
      <div class="message-tabs-wrapper">
        <el-tabs v-model="activeTab" class="message-tabs neo-tabs">
          <el-tab-pane label="全部" name="all" />
          <el-tab-pane label="排班通知" name="schedule" />
          <el-tab-pane label="调班通知" name="swap" />
          <el-tab-pane label="排班审核" name="approve" />
          <el-tab-pane label="公告" name="announcement" />
        </el-tabs>
        <div class="toolbar-actions">
          <el-badge :value="unreadTotal" :hidden="unreadTotal === 0" :max="99">
            <el-icon :size="20" class="toolbar-icon"><Bell /></el-icon>
          </el-badge>
        </div>
      </div>

      <div class="message-page__content">
        <MessageList
          v-if="activeTab !== 'announcement'"
          ref="messageListRef"
          :msg-type="activeTab === 'all' ? undefined : activeTab"
          :highlight-id="highlightId"
          :status-filter="statusFilter"
          :type-filter="typeFilter"
          :keyword="keyword"
          @open-detail="handleOpenDetail"
          @refresh-unread="fetchUnreadCount"
        />
        <AnnouncementSection
          v-else
          ref="announcementListRef"
          :highlight-id="highlightId"
        />
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
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bell, Check } from '@element-plus/icons-vue'
import MessageList from './components/MessageList.vue'
import MessageDetailDrawer from './components/MessageDetailDrawer.vue'
import AnnouncementSection from './components/AnnouncementSection.vue'
import { getUnreadCount } from '@/api/message'
import { markAllMessagesRead } from '@/api/message'
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
const announcementListRef = ref<InstanceType<typeof AnnouncementSection> | null>(null)
const route = useRoute()
const router = useRouter()

// 筛选条件
const keyword = ref('')
const statusFilter = ref('all')
const typeFilter = ref('all')

// Tab 切换时重置筛选条件，避免筛选条件在不同 Tab 间残留
watch(activeTab, () => {
  statusFilter.value = 'all'
  typeFilter.value = 'all'
  keyword.value = ''
})

const highlightId = computed(() => {
  const id = route.query.noticeId
  return id ? Number(id) : undefined
})

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
}

const handleMarkedRead = () => {
  fetchUnreadCount()
  messageStore.fetchUnread()
  messageListRef.value?.refresh()
}

const handleMarkAllRead = async () => {
  try {
    const { data: res } = await markAllMessagesRead()
    if (res.code === 200) {
      unreadTotal.value = 0
      fetchUnreadCount()
      messageStore.fetchUnread()
      messageListRef.value?.refresh()
    }
  } catch {
    // 静默失败
  }
}

const onFilterChange = () => {
  messageListRef.value?.refresh()
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null

const debounceFetch = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    onFilterChange()
  }, 300)
}

watch(highlightId, (newId) => {
  if (newId != null) {
    const tab = route.query.tab as string | undefined
    if (tab === 'announcement') {
      activeTab.value = 'announcement'
    }
    setTimeout(() => {
      if (route.query.noticeId) {
        router.replace({ query: {} })
      }
    }, 3000)
  }
})

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

  const noticeId = route.query.noticeId
  const tab = route.query.tab as string | undefined
  if (noticeId && tab === 'announcement') {
    activeTab.value = 'announcement'
  }
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
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 0;
}

/* ========== 页面顶部 ========== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 0 0;
}

.page-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 24px;
  font-weight: 900;
  color: #000000;
  margin: 0;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

/* ========== 筛选栏 ========== */
.filter-bar {
  background: #FFFFFF;
  border: 4px solid #000000;
  border-radius: 4px;
  box-shadow: 8px 8px 0px 0px #000000;
  padding: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  transition: all 0.2s ease;
}

.filter-bar:hover {
  box-shadow: 10px 10px 0px 0px #000000;
  transform: translate(-1px, -1px);
}

.filter-bar__search {
  flex: 1;
  min-width: 200px;
}

.filter-bar__input {
  width: 100% !important;
}

.filter-bar__input :deep(.el-input__wrapper) {
  border: 3px solid #000000 !important;
  box-shadow: 3px 3px 0px 0px #000000 !important;
  border-radius: 4px !important;
  background: #FFFFFF !important;
  height: 44px !important;
  padding: 0 12px !important;
}

.filter-bar__input :deep(.el-input__inner) {
  font-weight: 600 !important;
  color: #000000 !important;
}

.filter-bar__filters {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-bar__select {
  width: 150px;
}

.filter-bar__select :deep(.el-select__wrapper) {
  border: 3px solid #000000 !important;
  box-shadow: 3px 3px 0px 0px #000000 !important;
  border-radius: 4px !important;
  background: #FFFFFF !important;
  height: 44px !important;
  font-weight: 600 !important;
}

.filter-bar__select :deep(.el-select__selected-item) {
  font-weight: 600 !important;
  color: #000000 !important;
}

/* ========== 主卡片 ========== */
.message-card {
  border: 3px solid #000000 !important;
  border-radius: 4px !important;
  box-shadow: 4px 4px 0px 0px #000000 !important;
  background: #FFFFFF !important;
  overflow: visible !important;
}

.message-card :deep(.el-card__body) {
  padding: 0 !important;
}

/* ========== Tabs + 内容 ========== */
.message-tabs-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px 16px 0;
  border-bottom: 3px solid #000000;
  background: #FFFDF5;
}

.message-tabs {
  flex: 1;
}

.message-tabs :deep(.el-tabs__header) {
  margin: 0 !important;
}

.message-tabs :deep(.el-tabs__active-bar) {
  background: #3B82F6 !important;
  height: 3px !important;
}

.message-tabs :deep(.el-tabs__nav-wrap::after) {
  background: #000000 !important;
  height: 3px !important;
}

.message-tabs :deep(.el-tabs__item) {
  font-weight: 700 !important;
  color: #000000 !important;
  border: 2px solid transparent !important;
  border-radius: 4px 4px 0 0 !important;
  padding: 0 16px !important;
  height: 44px !important;
  line-height: 44px !important;
  transition: all 0.15s ease !important;
}

.message-tabs :deep(.el-tabs__item:hover) {
  background: #FFFDF5 !important;
}

.message-tabs :deep(.el-tabs__item.is-active) {
  color: #3B82F6 !important;
  background: #FFFFFF !important;
  border-color: #000000 !important;
  border-bottom-color: #FFFDF5 !important;
  font-weight: 900 !important;
  position: relative !important;
  z-index: 1 !important;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 4px;
  margin-left: 16px;
}

.toolbar-icon {
  cursor: pointer;
  color: #000000;
  border: 2px solid #000000;
  border-radius: 4px;
  background: #FFD93D;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2px 2px 0px 0px #000000;
  transition: all 0.1s ease;
}

.toolbar-icon:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0px 0px #000000;
}

.message-page__content {
  min-height: 400px;
  padding: 0;
}
</style>
