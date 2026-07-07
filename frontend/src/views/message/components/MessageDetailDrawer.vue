<template>
  <el-drawer
    :model-value="visible"
    size="480px"
    direction="rtl"
    class="neo-drawer"
    @close="$emit('update:visible', false)"
  >
    <template v-if="message">
      <!-- 抽屉头部 -->
      <div class="drawer-header">
        <div class="drawer-header__left">
          <div class="drawer-header__avatar" :style="{ background: avatarBg(message.msg_type) }">
            <el-icon :size="20"><component :is="avatarIcon(message.msg_type)" /></el-icon>
          </div>
          <div class="drawer-header__info">
            <span class="drawer-header__type">{{ msgTypeLabel(message.msg_type) }}</span>
            <span class="drawer-header__time">{{ message.created_at }}</span>
          </div>
        </div>
        <el-button class="btn-neo-ghost btn-neo-sm" @click="$emit('update:visible', false)">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>

      <!-- 标题 -->
      <h3 class="drawer-title">{{ message.title }}</h3>

      <!-- 内容区 -->
      <div class="drawer-content">
        {{ message.content }}
      </div>

      <!-- 发送人 -->
      <div v-if="message.sender_name" class="drawer-sender">
        <el-icon><User /></el-icon>
        <span>发送人：{{ message.sender_name }}</span>
      </div>

      <!-- 操作按钮 -->
      <div class="drawer-actions">
        <el-button
          v-if="!message.is_read"
          class="btn-neo-primary btn-neo-sm"
          @click="handleMarkRead"
        >
          <el-icon><Check /></el-icon>
          <span>标记已读</span>
        </el-button>
        <el-button
          v-if="message.msg_type === 'approve' && message.relation_type === 'schedule'"
          class="btn-neo-warning btn-neo-sm"
          @click="handleJumpSchedule"
        >
          <el-icon><ArrowRight /></el-icon>
          <span>前往审核</span>
        </el-button>
        <el-button
          v-if="message.msg_type === 'schedule' && message.relation_type === 'schedule'"
          class="btn-neo-primary btn-neo-sm"
          @click="handleJumpSchedule"
        >
          <el-icon><Calendar /></el-icon>
          <span>查看排班</span>
        </el-button>
        <el-button
          v-if="message.msg_type === 'swap'"
          class="btn-neo-info btn-neo-sm"
          @click="handleJumpSwap"
        >
          <el-icon><RefreshLeft /></el-icon>
          <span>查看调班申请</span>
        </el-button>
      </div>
    </template>

    <el-empty v-else class="drawer-empty" description="请选择一条消息" />
  </el-drawer>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { markMessageRead } from '@/api/message'
import type { MessageItem } from '@/api/message'
import { useRouter } from 'vue-router'
import {
  Bell, Calendar, RefreshLeft, User, Close, Check, ArrowRight,
} from '@element-plus/icons-vue'
import { useMessageStore } from '@/stores/message'

const messageStore = useMessageStore()
const router = useRouter()

const props = defineProps<{
  visible: boolean
  message: MessageItem | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'marked-read'): void
}>()

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
  approve: Bell,
  system: Bell,
}

const avatarColors: Record<string, string> = {
  schedule: '#3B82F6',
  swap: '#10B981',
  approve: '#F59E0B',
  system: '#3B82F6',
}

const avatarIcon = (type: string) => avatarIcons[type] || Bell
const avatarBg = (type: string) => avatarColors[type] || '#3B82F6'

const handleMarkRead = async () => {
  if (!props.message) return
  try {
    const { data: res } = await markMessageRead(props.message.id)
    if (res.code === 200) {
      ElMessage.success('已标记已读')
      messageStore.fetchUnread()
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
.drawer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* ========== 抽屉头部 ========== */
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #FFFDF5;
  border-bottom: 3px solid #000000;
}

.drawer-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drawer-header__avatar {
  width: 44px;
  height: 44px;
  border: 3px solid #000000;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 3px 3px 0px 0px #000000;
  color: #FFFFFF;
  transition: transform 0.2s ease;
}

.drawer-header:hover .drawer-header__avatar {
  transform: rotate(5deg) scale(1.05);
}

.drawer-header__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.drawer-header__type {
  font-size: 14px;
  font-weight: 700;
  color: #000000;
}

.drawer-header__time {
  font-size: 12px;
  color: #666666;
  font-weight: 600;
}

/* ========== 标题 ========== */
.drawer-title {
  font-size: 18px;
  font-weight: 900;
  color: #000000;
  margin: 16px;
  line-height: 1.4;
}

/* ========== 内容区 ========== */
.drawer-content {
  font-size: 14px;
  color: #000000;
  line-height: 1.8;
  padding: 16px;
  margin: 0 16px 16px;
  background: #FFFDF5;
  border: 3px solid #000000;
  border-radius: 4px;
  white-space: pre-wrap;
  font-weight: 500;
  box-shadow: 2px 2px 0px 0px #000000;
}

/* ========== 发送人 ========== */
.drawer-sender {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #666666;
  margin: 0 16px 16px;
  font-weight: 600;
}

.drawer-sender .el-icon {
  color: #3B82F6;
}

/* ========== 操作按钮 ========== */
.drawer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 16px;
  border-top: 3px solid #000000;
  background: #FFFDF5;
}
</style>
