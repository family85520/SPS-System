<template>
  <div class="message-list-container">
    <!-- 消息列表 -->
    <div v-loading="loading" element-loading-text="加载中..." class="message-items">
      <div
        v-for="(msg, index) in messageList"
        :key="msg.id"
        :data-id="msg.id"
        :style="{ animationDelay: `${index * 0.04}s` }"
        class="message-item neo-list-item"
        :class="{
          'is-unread': !msg.is_read,
          'is-highlighted': highlightedId === msg.id,
          'neo-list-item--clickable': true,
        }"
        @click="$emit('open-detail', msg)"
      >
        <!-- 未读指示条 -->
        <div class="message-item__unread-bar" v-if="!msg.is_read" />

        <!-- 图标头像 -->
        <div class="message-item__avatar" :style="{ background: avatarBg(msg.msg_type) }">
          <el-icon :size="20"><component :is="avatarIcon(msg.msg_type)" /></el-icon>
        </div>

        <!-- 内容区 -->
        <div class="message-item__body">
          <div class="message-item__header">
            <span class="message-item__title">{{ msg.title }}</span>
            <div class="message-item__badges">
              <span class="neo-badge message-item__type-badge" :style="{ background: badgeBg(msg.msg_type) }">
                {{ msgTypeLabel(msg.msg_type) }}
              </span>
              <span v-if="!msg.is_read" class="neo-badge neo-badge--active message-item__status-badge">
                未读
              </span>
            </div>
          </div>
          <div class="message-item__excerpt">
            {{ truncate(msg.content, 100) }}
          </div>
          <div class="message-item__footer">
            <span class="message-item__time">{{ formatRelativeTime(msg.created_at) }}</span>
            <span v-if="msg.sender_name" class="message-item__sender">
              来自 {{ msg.sender_name }}
            </span>
          </div>
        </div>

        <!-- 展开箭头 -->
        <div class="message-item__arrow">
          <el-icon :size="18"><ArrowRight /></el-icon>
        </div>
      </div>

      <div v-if="!loading && messageList.length === 0" class="empty-state">
        <el-icon :size="48"><Bell /></el-icon>
        <p>暂无消息</p>
      </div>
    </div>

    <!-- 分页 -->
    <div class="message-pagination" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchMessages"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Bell,
  Calendar,
  RefreshLeft,
  Promotion,
  CircleCheckFilled,
  ArrowRight,
} from '@element-plus/icons-vue'
import { getMessages, markAllMessagesRead } from '@/api/message'
import type { MessageItem } from '@/api/message'

const props = defineProps<{
  msgType?: string
  highlightId?: number
  statusFilter?: string
  typeFilter?: string
  keyword?: string
}>()

const emit = defineEmits<{
  (e: 'open-detail', msg: MessageItem): void
  (e: 'refresh-unread'): void
}>()

const messageList = ref<MessageItem[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const highlightedId = ref<number | null>(null)
let requestVersion = 0  // 防止旧请求覆盖新结果

const msgTypeLabels: Record<string, string> = {
  schedule: '排班通知',
  swap: '调班通知',
  approve: '审批提醒',
  system: '系统消息',
}

const msgTypeLabel = (type: string) => msgTypeLabels[type] || type

const avatarIcons: Record<string, any> = {
  schedule: Calendar,
  swap: RefreshLeft,
  approve: Promotion,
  system: Bell,
}

const avatarColors: Record<string, string> = {
  schedule: '#3B82F6',
  swap: '#10B981',
  approve: '#F59E0B',
  system: '#3B82F6',
}

const badgeColors: Record<string, string> = {
  schedule: '#3B82F6',
  swap: '#10B981',
  approve: '#F59E0B',
  system: '#3B82F6',
}

const avatarIcon = (type: string) => avatarIcons[type] || Bell
const avatarBg = (type: string) => avatarColors[type] || '#3B82F6'
const badgeBg = (type: string) => badgeColors[type] || '#3B82F6'

const truncate = (text: string | null, len: number) => {
  if (!text) return ''
  return text.length > len ? text.slice(0, len) + '...' : text
}

const formatRelativeTime = (timeStr: string | null): string => {
  if (!timeStr) return ''
  const now = new Date()
  const time = new Date(timeStr)
  const diff = now.getTime() - time.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return timeStr.slice(0, 10)
}

const fetchMessages = async () => {
  const thisVersion = ++requestVersion  // 每次请求递增版本号，防止竞态覆盖
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      size: pageSize.value,
    }
    if (props.msgType) params.msg_type = props.msgType
    // typeFilter 仅在 Tab 为 "all" 时生效（避免与 Tab 的 msg_type 冲突）
    if (!props.msgType && props.typeFilter && props.typeFilter !== 'all') {
      params.msg_type = props.typeFilter
    }
    if (props.keyword && props.keyword.trim()) params.keyword = props.keyword.trim()
    // statusFilter: all/unread/read
    // 传 'true'/'false' 字符串 — FastAPI 已改为手动解析，避免原始 Query(bool) 对 "false" 的错误解析
    if (props.statusFilter && props.statusFilter !== 'all') {
      params.is_read = props.statusFilter === 'read' ? 'true' : 'false'
    }

    const { data: res } = await getMessages(params)
    if (res.code === 200) {
      if (thisVersion === requestVersion) {
        messageList.value = res.data.list
        total.value = res.data.total
      }
    }
  } catch {
    ElMessage.error('获取消息列表失败')
  } finally {
    if (thisVersion === requestVersion) {
      loading.value = false
    }
  }
}

const handleMarkAllRead = async () => {
  try {
    const { data: res } = await markAllMessagesRead()
    if (res.code === 200) {
      ElMessage.success(res.message)
      fetchMessages()
      emit('refresh-unread')
    }
  } catch {
    ElMessage.error('操作失败')
  }
}

const refresh = () => {
  fetchMessages()
}

const scrollToHighlighted = () => {
  if (highlightedId.value == null) return
  const el = document.querySelector(`.message-item[data-id="${highlightedId.value}"]`) as HTMLElement | null
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setTimeout(() => { highlightedId.value = null }, 2000)
  }
}

watch(() => props.msgType, () => {
  currentPage.value = 1
  fetchMessages()
})

watch(() => props.keyword, () => {
  currentPage.value = 1
  fetchMessages()
})

watch(() => props.statusFilter, () => {
  currentPage.value = 1
  fetchMessages()
})

watch(() => props.typeFilter, () => {
  currentPage.value = 1
  fetchMessages()
})

watch(() => props.highlightId, (newId) => {
  if (newId != null && messageList.value.length > 0) {
    highlightedId.value = newId
    setTimeout(scrollToHighlighted, 300)
  }
})

onMounted(fetchMessages)

defineExpose({ refresh })
</script>

<style scoped>
.message-list-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.message-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* ========== 消息项 ========== */
.message-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  margin-bottom: 6px;
  border: 3px solid #000000;
  border-radius: 4px;
  background: #FFFFFF;
  box-shadow: 3px 3px 0px 0px #000000;
  cursor: pointer;
  transition: all 0.15s ease;
  animation: slide-in-left 0.3s ease both;
}

.message-item:hover {
  background: #FFFDF5;
  box-shadow: 5px 5px 0px 0px #000000;
  transform: translate(-2px, -2px);
}

/* 未读消息 */
.message-item.is-unread {
  background: #EFF6FF;
  border-color: #000000;
  box-shadow: 3px 3px 0px 0px #000000;
}

.message-item.is-unread:hover {
  background: #DBEAFE;
  box-shadow: 5px 5px 0px 0px #000000;
}

/* 未读指示条 */
.message-item__unread-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  background: #3B82F6;
  border-radius: 4px 0 0 4px;
}

/* 高亮消息 */
.message-item.is-highlighted {
  background: #FFD93D;
  border-color: #000000;
  box-shadow: 4px 4px 0px 0px #000000;
  animation: pulse-highlight 1s ease-in-out 3, slide-in-left 0.3s ease both;
}

@keyframes pulse-highlight {
  0%, 100% { box-shadow: 4px 4px 0px 0px #000000; }
  50%      { box-shadow: 8px 8px 0px 0px #000000; }
}

/* ========== 头像图标 ========== */
.message-item__avatar {
  width: 40px;
  height: 40px;
  border: 3px solid #000000;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 2px 2px 0px 0px #000000;
  color: #FFFFFF;
  transition: transform 0.2s ease;
}

.message-item:hover .message-item__avatar {
  transform: rotate(3deg) scale(1.05);
}

/* ========== 内容区 ========== */
.message-item__body {
  flex: 1;
  min-width: 0;
}

.message-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.message-item__title {
  font-size: 14px;
  font-weight: 700;
  color: #000000;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.message-item__badges {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.message-item__type-badge {
  font-size: 10px !important;
  padding: 1px 6px !important;
  color: #FFFFFF !important;
}

.message-item__status-badge {
  font-size: 10px !important;
  padding: 1px 6px !important;
  background: #3B82F6 !important;
  color: #FFFFFF !important;
}

.message-item__excerpt {
  font-size: 13px;
  color: #333333;
  line-height: 1.5;
  margin-bottom: 6px;
  font-weight: 500;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.message-item__footer {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #666666;
  font-weight: 600;
}

.message-item__arrow {
  flex-shrink: 0;
  color: #999999;
  display: flex;
  align-items: center;
  transition: all 0.15s ease;
  margin-top: 4px;
}

.message-item:hover .message-item__arrow {
  color: #000000;
  transform: translateX(2px);
}

/* ========== 空状态 ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #999999;
  gap: 12px;
}

.empty-state .el-icon {
  color: #CCCCCC;
  border: 2px solid #E0E0E0;
  border-radius: 4px;
  padding: 8px;
  box-shadow: 2px 2px 0px 0px #E0E0E0;
}

.empty-state p {
  font-size: 14px;
  font-weight: 600;
  color: #999999;
}

/* ========== 分页 ========== */
.message-pagination {
  display: flex;
  justify-content: center;
  padding: 16px 8px 8px;
  border-top: 3px solid #000000;
  margin: 8px -8px 0;
  background: #FFFDF5;
}

.message-pagination :deep(.el-pagination) {
  gap: 4px;
}

.message-pagination :deep(.el-pager li) {
  background: #FFFFFF !important;
  border: 2px solid #000000 !important;
  border-radius: 4px !important;
  font-weight: 700 !important;
  box-shadow: 2px 2px 0px 0px #000000 !important;
  transition: all 0.1s ease !important;
  min-width: 36px !important;
  height: 36px !important;
  line-height: 32px !important;
}

.message-pagination :deep(.el-pager li:hover) {
  background: #FFD93D !important;
  transform: translate(-1px, -1px) !important;
}

.message-pagination :deep(.el-pager li.is-active) {
  background: #3B82F6 !important;
  color: #FFFFFF !important;
  box-shadow: 3px 3px 0px 0px #000000 !important;
}

.message-pagination :deep(.el-pagination button) {
  background: #FFFFFF !important;
  border: 2px solid #000000 !important;
  border-radius: 4px !important;
  box-shadow: 2px 2px 0px 0px #000000 !important;
  font-weight: 700 !important;
  transition: all 0.1s ease !important;
  min-width: 36px !important;
  height: 36px !important;
}

.message-pagination :deep(.el-pagination button:hover:not(:disabled)) {
  background: #FFD93D !important;
  transform: translate(-1px, -1px) !important;
}

.message-pagination :deep(.el-pagination button:active:not(:disabled)) {
  transform: translate(1px, 1px) !important;
  box-shadow: 1px 1px 0px 0px #000000 !important;
}

.message-pagination :deep(.el-pagination button:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
