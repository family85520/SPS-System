<template>
  <div class="dashboard-page" v-loading="loading">
    <!-- 第一行：排班概览 + 今日值班 -->
    <el-row :gutter="16" class="dashboard-row">
      <el-col :span="14">
        <el-card shadow="never" class="dashboard-card card-schedule-overview">
          <template #header>
            <div class="card-header">
              <span class="card-title">排班概览</span>
              <el-tag
                :type="statusTagType"
                size="small"
              >
                {{ statusLabel }}
              </el-tag>
            </div>
          </template>
          <div class="overview-grid">
            <div class="overview-stat">
              <div class="stat-value" style="color: #0A63D8">{{ overview.org_count }}</div>
              <div class="stat-label">组织数量</div>
            </div>
            <div class="overview-stat">
              <div class="stat-value" style="color: #28A745">{{ overview.staff_count }}</div>
              <div class="stat-label">人员总数</div>
            </div>
            <div class="overview-stat">
              <div class="stat-value" style="color: #17A2B8">{{ overview.active_rules_count }}</div>
              <div class="stat-label">启用规则</div>
            </div>
            <div
              class="overview-stat clickable"
              @click="router.push('/schedule/calendar')"
            >
              <div class="stat-value" style="color: #DC3545">
                {{ overview.constraint_warnings }}
              </div>
              <div class="stat-label">约束冲突</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never" class="dashboard-card card-today-duty">
          <template #header>
            <div class="card-header">
              <span class="card-title">今日值班</span>
              <span class="card-date">{{ todayStr }}</span>
            </div>
          </template>
          <div v-if="overview.today_duty.length > 0" class="duty-list">
            <div
              v-for="(duty, idx) in overview.today_duty"
              :key="idx"
              class="duty-item"
            >
              <div class="duty-shift-name">
                <span class="duty-dot" :style="{ background: shiftColors[idx % shiftColors.length] }" />
                {{ duty.shift_name }}
              </div>
              <div class="duty-detail">
                <span v-if="duty.leader" class="duty-leader">
                  带班：{{ duty.leader }}
                </span>
                <span class="duty-members">
                  {{ duty.members.join('、') || '暂无安排' }}
                </span>
              </div>
            </div>
          </div>
          <el-empty v-else description="今日暂无值班安排" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二行：快捷操作 + 待处理事项 -->
    <el-row :gutter="16" class="dashboard-row">
      <el-col :span="14">
        <el-card shadow="never" class="dashboard-card card-quick-actions">
          <template #header>
            <span class="card-title">快捷操作</span>
          </template>
          <div class="quick-actions-grid">
            <div
              v-for="action in quickActions"
              :key="action.label"
              class="quick-action-item"
              @click="router.push(action.path)"
            >
              <div class="quick-action-icon" :style="{ background: action.bgColor }">
                <el-icon :size="24" :color="action.iconColor">
                  <component :is="action.icon" />
                </el-icon>
              </div>
              <span class="quick-action-label">{{ action.label }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never" class="dashboard-card card-pending">
          <template #header>
            <span class="card-title">待处理事项</span>
          </template>
          <div class="pending-list">
            <div class="pending-item" @click="router.push('/swap')">
              <el-badge :value="overview.pending_swap_count" :hidden="overview.pending_swap_count === 0">
                <span class="pending-label">待审批调班</span>
              </el-badge>
              <span class="pending-count">{{ overview.pending_swap_count }} 条</span>
            </div>
            <div class="pending-item" @click="router.push('/message')">
              <el-badge :value="overview.unread_messages" :hidden="overview.unread_messages === 0">
                <span class="pending-label">未读消息</span>
              </el-badge>
              <span class="pending-count">{{ overview.unread_messages }} 条</span>
            </div>
            <div
              v-if="overview.constraint_warnings > 0"
              class="pending-item"
              @click="router.push('/schedule/calendar')"
            >
              <span class="pending-label" style="color: #DC3545">约束冲突</span>
              <span class="pending-count" style="color: #DC3545">
                {{ overview.constraint_warnings }} 条
              </span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第三行：最近公告 + 人员统计 -->
    <el-row :gutter="16" class="dashboard-row">
      <el-col :span="14">
        <el-card shadow="never" class="dashboard-card card-announcements">
          <template #header>
            <div class="card-header">
              <span class="card-title">最近公告</span>
              <el-button type="primary" text size="small" @click="router.push('/message')">
                查看全部
              </el-button>
            </div>
          </template>
          <div v-if="overview.recent_notices.length > 0" class="notice-list">
            <div
              v-for="notice in overview.recent_notices"
              :key="notice.id"
              class="notice-item"
            >
              <el-icon><Document /></el-icon>
              <span class="notice-title">{{ notice.title }}</span>
              <span class="notice-time">{{ notice.created_at }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无公告" :image-size="60" />
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never" class="dashboard-card card-staff-stats">
          <template #header>
            <span class="card-title">人员统计</span>
          </template>
          <div class="staff-stats-grid">
            <div class="staff-stat-item">
              <div class="stat-value" style="color: #0A63D8">{{ overview.staff_count }}</div>
              <div class="stat-label">人员总数</div>
            </div>
            <div class="staff-stat-item">
              <div class="stat-value" style="color: #28A745">{{ overview.org_count }}</div>
              <div class="stat-label">组织数量</div>
            </div>
            <div class="staff-stat-item">
              <div class="stat-value" style="color: #FFC107">{{ overview.active_rules_count }}</div>
              <div class="stat-label">活跃规则</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Calendar,
  List,
  Switch,
  Message,
  Bell,
  Document,
  Setting,
  DataAnalysis,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDashboardOverview } from '@/api/dashboard'
import type { DashboardOverview } from '@/api/dashboard'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)

const overview = ref<DashboardOverview>({
  org_count: 0,
  staff_count: 0,
  active_rules_count: 0,
  pending_swap_count: 0,
  today_duty: [],
  unread_messages: 0,
  recent_notices: [],
  constraint_warnings: 0,
  schedule_status: 'empty',
})

const todayStr = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
})

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    empty: '暂无排班',
    draft: '草稿',
    partial_published: '部分已发布',
    published: '已发布',
  }
  return map[overview.value.schedule_status] || '未知'
})

const statusTagType = computed(() => {
  const map: Record<string, string> = {
    empty: 'info',
    draft: 'warning',
    partial_published: '',
    published: 'success',
  }
  return (map[overview.value.schedule_status] || 'info') as any
})

const shiftColors = ['#FFD166', '#06D6A0', '#118AB2', '#F08A5D']

// 快捷操作（根据角色动态）
const quickActions = computed(() => {
  const actions = [
    { label: '自动排班', path: '/schedule/auto', icon: Calendar, bgColor: '#EBF5FF', iconColor: '#0A63D8' },
    { label: '排班日历', path: '/schedule', icon: List, bgColor: '#E8F8F0', iconColor: '#28A745' },
    { label: '调班申请', path: '/swap', icon: Switch, bgColor: '#FFF8E1', iconColor: '#FFC107' },
    { label: '消息中心', path: '/message', icon: Message, bgColor: '#F3E5F5', iconColor: '#9C27B0' },
  ]
  if (authStore.hasRole('admin')) {
    actions.push(
      { label: '系统设置', path: '/system', icon: Setting, bgColor: '#ECEFF1', iconColor: '#607D8B' },
      { label: '数据导出', path: '/schedule', icon: DataAnalysis, bgColor: '#FCE4EC', iconColor: '#E91E63' },
    )
  }
  return actions
})

const fetchOverview = async () => {
  loading.value = true
  try {
    const { data: res } = await getDashboardOverview()
    if (res.code === 200) {
      overview.value = { ...overview.value, ...res.data }
    }
  } catch {
    ElMessage.error('获取看板数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchOverview)
</script>

<style scoped>
.dashboard-page {
  padding: 0;
}

.dashboard-row {
  margin-bottom: 16px;
}

.dashboard-row:last-child {
  margin-bottom: 0;
}

.dashboard-card {
  border-radius: 6px;
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1F2D3D;
}

.card-date {
  font-size: 13px;
  color: #8492a6;
}

/* 排班概览 */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  text-align: center;
}

.overview-stat {
  padding: 12px 0;
}

.overview-stat.clickable {
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.2s;
}

.overview-stat.clickable:hover {
  background: #f5f7fa;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #8492a6;
}

/* 今日值班 */
.duty-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.duty-item {
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 3px solid #e6eaf0;
}

.duty-shift-name {
  font-size: 14px;
  font-weight: 600;
  color: #1F2D3D;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.duty-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.duty-detail {
  font-size: 13px;
  color: #556173;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.duty-leader {
  color: #F08A5D;
  font-weight: 500;
}

/* 快捷操作 */
.quick-actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 16px;
}

.quick-action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-action-item:hover {
  background: #f5f7fa;
  transform: translateY(-2px);
}

.quick-action-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.quick-action-label {
  font-size: 13px;
  color: #556173;
  font-weight: 500;
}

/* 待处理事项 */
.pending-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pending-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.pending-item:hover {
  background: #f0f2f5;
}

.pending-label {
  font-size: 14px;
  color: #1F2D3D;
  font-weight: 500;
}

.pending-count {
  font-size: 14px;
  color: #8492a6;
}

/* 最近公告 */
.notice-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notice-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
}

.notice-item:last-child {
  border-bottom: none;
}

.notice-item:hover .notice-title {
  color: #0A63D8;
}

.notice-title {
  flex: 1;
  font-size: 14px;
  color: #1F2D3D;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.2s;
}

.notice-time {
  font-size: 12px;
  color: #8492a6;
  flex-shrink: 0;
}

/* 人员统计 */
.staff-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  text-align: center;
  padding: 12px 0;
}

.staff-stat-item {
  padding: 12px 0;
}
</style>
