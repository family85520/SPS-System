<template>
  <div class="message-list-container">
    <!-- 顶部工具栏 -->
    <div class="message-toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索消息标题或内容"
        prefix-icon="Search"
        clearable
        style="width: 260px"
        @input="debounceFetch"
      />
      <el-button type="primary" text @click="handleMarkAllRead">
        全部已读
      </el-button>
    </div>

    <!-- 消息列表 -->
    <div v-loading="loading" class="message-items">
      <div
        v-for="msg in messageList"
        :key="msg.id"
        class="message-item"
        :class="{ 'is-unread': !msg.is_read }"
        @click="$emit('open-detail', msg)"
      >
        <div class="message-item__dot" v-if="!msg.is_read" />
        <div class="message-item__body">
          <div class="message-item__header">
            <span class="message-item__title">{{ msg.title }}</span>
            <el-tag
              :type="msgTypeTagType(msg.msg_type)"
              size="small"
              class="message-item__tag"
            >
              {{ msgTypeLabel(msg.msg_type) }}
            </el-tag>
          </div>
          <div class="message-item__excerpt">
            {{ truncate(msg.content, 80) }}
          </div>
          <div class="message-item__footer">
            <span class="message-item__time">{{ formatRelativeTime(msg.created_at) }}</span>
            <span v-if="msg.sender_name" class="message-item__sender">
              来自 {{ msg.sender_name }}
            </span>
          </div>
        </div>
      </div>

      <el-empty v-if="!loading && messageList.length === 0" description="暂无消息" />
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
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getMessages, markAllMessagesRead } from '@/api/message'
import type { MessageItem } from '@/api/message'

const props = defineProps<{
  msgType?: string
}>()

const emit = defineEmits<{
  (e: 'open-detail', msg: MessageItem): void
  (e: 'refresh-unread'): void
}>()

const messageList = ref<MessageItem[]>([])
const loading = ref(false)
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

let debounceTimer: ReturnType<typeof setTimeout> | null = null

const msgTypeLabels: Record<string, string> = {
  schedule: '排班通知',
  swap: '调班通知',
  approve: '审批提醒',
  system: '系统消息',
}

const msgTypeTagType = (type: string) => {
  const map: Record<string, string> = {
    schedule: '',
    swap: 'success',
    approve: 'warning',
    system: 'info',
  }
  return map[type] || 'info'
}

const msgTypeLabel = (type: string) => msgTypeLabels[type] || type

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
  loading.value = true
  try {
    const { data: res } = await getMessages({
      msg_type: props.msgType || undefined,
      keyword: keyword.value || undefined,
      page: currentPage.value,
      size: pageSize.value,
    })
    if (res.code === 200) {
      messageList.value = res.data.list
      total.value = res.data.total
    }
  } catch {
    ElMessage.error('获取消息列表失败')
  } finally {
    loading.value = false
  }
}

const debounceFetch = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    currentPage.value = 1
    fetchMessages()
  }, 300)
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

watch(() => props.msgType, () => {
  currentPage.value = 1
  fetchMessages()
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

.message-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 16px 0;
}

.message-items {
  flex: 1;
  overflow-y: auto;
}

.message-item {
  display: flex;
  align-items: flex-start;
  padding: 14px 16px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
}

.message-item:hover {
  background: #f5f7fa;
}

.message-item.is-unread {
  background: #f0f6ff;
}

.message-item__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #0A63D8;
  flex-shrink: 0;
  margin-top: 6px;
  margin-right: 12px;
}

.message-item__body {
  flex: 1;
  min-width: 0;
}

.message-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.message-item__title {
  font-size: 14px;
  font-weight: 500;
  color: #1F2D3D;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-item__tag {
  flex-shrink: 0;
  margin-left: 8px;
}

.message-item__excerpt {
  font-size: 13px;
  color: #556173;
  line-height: 1.5;
  margin-bottom: 6px;
}

.message-item__footer {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #8492a6;
}

.message-pagination {
  display: flex;
  justify-content: center;
  padding-top: 16px;
}
</style>
