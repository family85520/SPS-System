<template>
  <el-drawer
    :model-value="visible"
    title="消息详情"
    direction="rtl"
    size="420px"
    @close="$emit('update:visible', false)"
  >
    <template v-if="message">
      <div class="detail-header">
        <el-tag
          :type="msgTypeTagType(message.msg_type)"
          size="small"
        >
          {{ msgTypeLabel(message.msg_type) }}
        </el-tag>
        <span class="detail-time">{{ message.created_at }}</span>
      </div>

      <h3 class="detail-title">{{ message.title }}</h3>

      <div class="detail-content">
        {{ message.content }}
      </div>

      <div v-if="message.sender_name" class="detail-sender">
        发送人：{{ message.sender_name }}
      </div>

      <div class="detail-actions">
        <el-button
          v-if="!message.is_read"
          type="primary"
          @click="handleMarkRead"
        >
          标记已读
        </el-button>
        <el-button
          v-if="message.msg_type === 'approve' && message.relation_type === 'schedule'"
          type="warning"
          @click="handleJumpSchedule"
        >
          前往审核
        </el-button>
        <el-button
          v-if="message.msg_type === 'schedule' && message.relation_type === 'schedule'"
          @click="handleJumpSchedule"
        >
          查看排班
        </el-button>
        <el-button
          v-if="message.msg_type === 'swap'"
          @click="handleJumpSwap"
        >
          查看调班申请
        </el-button>
      </div>
    </template>

    <el-empty v-else description="请选择一条消息" />
  </el-drawer>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { markMessageRead } from '@/api/message'
import type { MessageItem } from '@/api/message'
import { useRouter } from 'vue-router'

const props = defineProps<{
  visible: boolean
  message: MessageItem | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'marked-read'): void
}>()

const router = useRouter()

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

import { useMessageStore } from '@/stores/message'

const messageStore = useMessageStore()

const handleMarkRead = async () => {
  if (!props.message) return
  try {
    const { data: res } = await markMessageRead(props.message.id)
    if (res.code === 200) {
      ElMessage.success('已标记已读')
      messageStore.fetchUnread()  // 立即刷新全局角标
      emit('marked-read')
    }
  } catch {
    ElMessage.error('操作失败')
  }
}

const handleJumpSchedule = () => {
  if (!props.message) return
  const relationId = props.message.relation_id
  if (relationId) {
    router.push({ path: '/schedule', query: { highlight: String(relationId) } })
  } else {
    router.push('/schedule')
  }
  emit('update:visible', false)
}

const handleJumpSwap = () => {
  if (!props.message) return
  const relationId = props.message.relation_id
  if (relationId) {
    router.push({ path: '/swap', query: { highlight: String(relationId) } })
  } else {
    router.push('/swap')
  }
  emit('update:visible', false)
}
</script>

<style scoped>
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.detail-time {
  font-size: 13px;
  color: #8492a6;
}

.detail-title {
  font-size: 18px;
  font-weight: 600;
  color: #1F2D3D;
  margin-bottom: 16px;
  line-height: 1.4;
}

.detail-content {
  font-size: 14px;
  color: #556173;
  line-height: 1.8;
  padding: 16px;
  background: #f9fafb;
  border-radius: 6px;
  margin-bottom: 16px;
  white-space: pre-wrap;
}

.detail-sender {
  font-size: 13px;
  color: #8492a6;
  margin-bottom: 24px;
}

.detail-actions {
  display: flex;
  gap: 8px;
}
</style>
