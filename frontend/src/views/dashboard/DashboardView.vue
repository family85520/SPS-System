<template>
  <div class="dashboard-page" v-loading="loading">
    <!-- ============================================================
         顶部：核心指标卡片（仅保留真实数据）
         ============================================================ -->
    <div class="stat-grid">
      <!-- 总员工数 -->
      <div class="neo-card stat-card stat-card-blue">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><User /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">总员工数</span>
            <span class="stat-big-number">{{ overview.staff_count }}</span>
          </div>
          <div class="stat-deco stat-deco-users" />
        </div>
      </div>

      <!-- 组织数量 -->
      <div class="neo-card stat-card stat-card-green">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><OfficeBuilding /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">组织数量</span>
            <span class="stat-big-number">{{ overview.org_count }}</span>
          </div>
          <div class="stat-deco stat-deco-org" />
        </div>
      </div>

      <!-- 待审批事项 -->
      <div class="neo-card stat-card stat-card-red">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Switch /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">待审批事项</span>
            <span class="stat-big-number">{{ overview.pending_swap_count }}</span>
          </div>
          <span class="stat-urgent-tag" v-if="overview.pending_swap_count > 0">紧急</span>
          <div class="stat-deco stat-deco-alert" />
        </div>
      </div>

      <!-- 未读消息 -->
      <div class="neo-card stat-card stat-card-purple">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Message /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">未读消息</span>
            <span class="stat-big-number">{{ overview.unread_messages }}</span>
          </div>
          <div class="stat-deco stat-deco-msg" />
        </div>
      </div>
    </div>

    <!-- ============================================================
         主内容区：第一行 3 列等宽 + 第二行左宽（快捷操作 + 工作量）+ 右窄（通知 + 模板）
         ============================================================ -->
    <div class="dashboard-main">
      <!-- 第一行：今日值班 | 本月排班状态 | 待处理事项（等宽三列） -->
      <div class="tri-row">
        <!-- 列 1：今日值班 -->
        <div class="neo-card tri-card duty-card">
          <div class="card-header">
            <h3 class="card-title font-weight-extrabold">今日值班</h3>
            <span class="card-date">{{ todayStr }}</span>
          </div>
          <div class="tri-body">
            <div v-if="overview.today_duty.length > 0" class="duty-list">
              <div v-for="(duty, idx) in overview.today_duty" :key="idx" class="neo-list-item">
                <div class="duty-shift-name">
                  <span class="list-item-dot" :style="{ background: shiftColors[idx % shiftColors.length] }" />
                  {{ duty.shift_name }}
                </div>
                <div class="duty-detail">
                  <span v-if="duty.leader" class="duty-leader font-weight-medium">
                    带班：{{ duty.leader }}
                  </span>
                  <span class="duty-members">
                    {{ duty.members.join('、') || '暂无安排' }}
                  </span>
                </div>
              </div>
            </div>
            <el-empty v-else description="今日暂无安排" :image-size="40" />
          </div>
        </div>

        <!-- 列 2：本月排班状态 -->
        <div class="neo-card tri-card schedule-card">
          <div class="card-header">
            <h3 class="card-title font-weight-extrabold">本月排班状态</h3>
            <span class="card-date">{{ currentMonthLabel }}</span>
          </div>
          <div class="tri-body">
            <div class="status-grid">
              <div class="status-item status-item--clickable" @click="router.push('/schedule')">
                <span class="status-label">已发布</span>
                <span class="status-value status-success">{{ scheduleStatus.published }}</span>
              </div>
              <div class="status-item status-item--clickable" @click="router.push('/schedule')">
                <span class="status-label">草稿</span>
                <span class="status-value status-warning">{{ scheduleStatus.draft }}</span>
              </div>
              <div class="status-item status-item--clickable" @click="router.push('/schedule')">
                <span class="status-label">已撤回</span>
                <span class="status-value status-info">{{ scheduleStatus.recalled }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 列 3：待处理事项 -->
        <div class="neo-card tri-card pending-card">
          <div class="card-header">
            <h3 class="card-title font-weight-extrabold">待处理事项</h3>
          </div>
          <div class="tri-body">
            <div class="pending-list">
              <div v-if="authStore.hasPermission('swap', 'read') || authStore.hasPermission('swap', 'approve')"
                   class="neo-list-item neo-list-item--clickable" @click="handleSwapNavigate">
                <span class="pending-label">待审批调班</span>
                <span class="neo-badge neo-badge--red" v-if="overview.pending_swap_count > 0">{{ overview.pending_swap_count }}</span>
                <span class="pending-count font-weight-medium">{{ overview.pending_swap_count }} 条</span>
              </div>
              <div v-if="authStore.hasPermission('message', 'read')" class="neo-list-item neo-list-item--clickable"
                   @click="router.push('/message')">
                <span class="pending-label">未读消息</span>
                <span class="neo-badge neo-badge--red" v-if="overview.unread_messages > 0">{{ overview.unread_messages }}</span>
                <span class="pending-count font-weight-medium">{{ overview.unread_messages }} 条</span>
              </div>
              <el-empty
                v-if="!authStore.hasPermission('swap', 'read') && !authStore.hasPermission('swap', 'approve')
                     && !authStore.hasPermission('message', 'read')"
                description="暂无待办" :image-size="40"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 第二行：左宽（快捷操作 + 工作量）+ 右窄（最近通知 + 班次模板） -->
      <div class="bottom-row">
        <!-- 左侧 -->
        <div class="main-left">
          <!-- 快捷操作 -->
          <div class="neo-card quick-card">
            <div class="card-header">
              <h3 class="card-title font-weight-extrabold">快捷操作</h3>
            </div>
            <div class="action-grid">
              <div v-for="action in quickActions" :key="action.label" class="action-item"
                   @click="router.push(action.path)">
                <div class="qa-icon" :style="{ background: action.bgColor }">
                  <el-icon :size="22"><component :is="action.icon" /></el-icon>
                </div>
                <span class="qa-label">{{ action.label }}</span>
              </div>
            </div>
          </div>

          <!-- 值班工作量统计 -->
          <div class="neo-card workload-card" v-if="authStore.hasPermission('schedule', 'read')" v-loading="workloadLoading">
            <div class="card-header">
              <h3 class="card-title font-weight-extrabold">值班工作量统计</h3>
              <span class="card-date">{{ currentMonthLabel }}</span>
            </div>
            <div v-if="workloadItems.length > 0" class="workload-body">
              <div class="mini-stat-grid">
                <div class="neo-card mini-stat-card">
                  <div class="mini-stat-value" style="color: #3B82F6">{{ workloadSummary.total_staff }}</div>
                  <div class="mini-stat-label">参与人数</div>
                </div>
                <div class="neo-card mini-stat-card">
                  <div class="mini-stat-value" style="color: #10B981">{{ workloadSummary.total_shifts }}</div>
                  <div class="mini-stat-label">总班次数</div>
                </div>
                <div class="neo-card mini-stat-card">
                  <div class="mini-stat-value" style="color: #EF4444">{{ workloadSummary.avg_shifts_per_person }}</div>
                  <div class="mini-stat-label">人均班次</div>
                </div>
                <div class="neo-card mini-stat-card">
                  <div class="mini-stat-value" style="color: #FF6B6B">
                    {{ workloadSummary.avg_hours_per_person }}<span class="unit-h">h</span>
                  </div>
                  <div class="mini-stat-label">人均工时</div>
                </div>
              </div>
              <div class="workload-ranking">
                <div class="workload-ranking-title font-weight-extrabold">工作量排名 Top 5</div>
                <div class="ranking-list">
                  <div v-for="(item, idx) in workloadItems" :key="item.staff_id" class="ranking-item">
                    <div class="ranking-row">
                      <div :class="['ranking-badge', idx < 3 ? `ranking-${idx + 1}` : 'ranking-other']">{{ idx + 1 }}</div>
                      <div class="ranking-info">
                        <div class="ranking-name font-weight-bold">{{ item.staff_name }}</div>
                        <div class="ranking-detail">
                          {{ item.total_shifts }}班 · {{ item.total_hours }}h · 夜班{{ item.night_shifts }}
                        </div>
                      </div>
                      <div class="neo-progress-wrapper">
                        <div class="neo-progress-bg">
                          <div class="neo-progress-fill"
                               :style="{ width: getBarWidth(item.weight_score), background: getBarColor(idx) }" />
                        </div>
                      </div>
                      <div class="ranking-score" :style="{ color: getScoreColor(idx) }">{{ item.weight_score }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <el-empty v-else description="当月暂无已发布排班数据，请先发布排班后再查看" :image-size="60" />
          </div>
        </div>

        <!-- 右侧窄栏：最近通知 + 班次模板 -->
        <div class="main-right">
          <!-- 最近通知（最多 5 条） -->
          <div class="neo-card notification-card">
            <div class="card-header">
              <h3 class="card-title font-weight-extrabold">最近通知</h3>
              <el-icon :size="18"><Bell /></el-icon>
            </div>
            <div class="notification-list">
              <div v-for="note in noticeCards" :key="note.id" class="notice-card notice-card--clickable"
                   :style="{ background: note.bgColor }" @click="handleNoticeClick(note.id)">
                <div class="notice-top">
                  <span class="notice-title-text">{{ note.title }}</span>
                  <span class="notice-time">{{ note.time }}</span>
                </div>
                <p class="notice-desc">{{ note.desc }}</p>
              </div>
              <el-empty v-if="noticeCards.length === 0" description="暂无通知" :image-size="48" />
            </div>
          </div>

          <!-- 班次模板统计 -->
          <div class="neo-card template-stat-card">
            <div class="card-header">
              <h3 class="card-title font-weight-extrabold">班次模板</h3>
            </div>
            <div class="template-stats">
              <div class="template-stat-item">
                <div class="stat-value" style="color: #3B82F6">{{ shiftTemplateCount }}</div>
                <div class="stat-label">已启用</div>
              </div>
              <div class="template-stat-item">
                <div class="stat-value" style="color: #666">{{ shiftTemplateDisabled }}</div>
                <div class="stat-label">已停用</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  User, OfficeBuilding, Switch, Message, Bell,
  MagicStick, List, Calendar, Clock, Setting, Key,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDashboardOverview } from '@/api/dashboard'
import type { DashboardOverview } from '@/api/dashboard'
import { getScheduleStatistics, getSchedules } from '@/api/schedule'
import type { ScheduleStatisticsResponse } from '@/api/schedule'
import { getShiftTemplates } from '@/api/shift-template'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const overview = ref<DashboardOverview>({
  org_count: 0, staff_count: 0, active_rules_count: 0,
  pending_swap_count: 0, today_duty: [], unread_messages: 0,
  recent_notices: [], constraint_warnings: 0, schedule_status: 'empty',
})

const todayStr = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
})

// ==================== 通知卡片（最多 5 条） ====================
interface NoticeCard {
  id: number
  title: string
  time: string
  desc: string
  bgColor: string
}

const noticeCards = computed<NoticeCard[]>(() => {
  const notices = overview.value.recent_notices
  const colors = ['#FFD93D', '#C4B5FD', '#86EFAC', '#FCA5A5', '#93C5FD']
  return notices.slice(0, 5).map((n, i) => ({
    id: n.id,
    title: n.title,
    time: n.created_at || '刚刚',
    desc: '点击查看公告详情...',
    bgColor: colors[i % colors.length],
  }))
})

function handleNoticeClick(noticeId: number) {
  router.push({ path: '/message', query: { noticeId, tab: 'announcement' } })
}

function handleSwapNavigate() {
  // 根据用户角色决定跳转到哪个 tab
  if (authStore.hasRole('admin') || authStore.hasRole('scheduler') || authStore.hasRole('leader')) {
    // 管理员/调度员/组长 → 全部记录
    router.push('/swap?tab=all')
  } else if (authStore.hasPermission('swap', 'approve')) {
    // 有审批权限 → 待我处理（审批者/接收方）
    router.push('/swap?tab=pending')
  } else {
    // 普通员工 → 我的申请（发起人）
    router.push('/swap?tab=mine')
  }
}

// ==================== 快捷操作 ====================
const quickActions = computed(() => {
  const items: Array<{ label: string; path: string; icon: any; bgColor: string }> = []
  if (authStore.hasPermission('staff', 'read'))
    items.push({ label: '人员管理', path: '/staffs', icon: User, bgColor: '#DBEAFE' })
  if (authStore.hasPermission('organization', 'read'))
    items.push({ label: '组织架构', path: '/organizations', icon: OfficeBuilding, bgColor: '#D1FAE5' })
  if (authStore.hasPermission('shift_template', 'read'))
    items.push({ label: '班次模板', path: '/shift-templates', icon: Clock, bgColor: '#FEF3C7' })
  if (authStore.hasPermission('constraint', 'read'))
    items.push({ label: '排班规则', path: '/constraints', icon: Setting, bgColor: '#EDE9FE' })
  if (authStore.hasPermission('schedule', 'create'))
    items.push({ label: '自动排班', path: '/schedule?auto=1', icon: MagicStick, bgColor: '#FFD93D' })
  if (authStore.hasPermission('schedule', 'read'))
    items.push({ label: '排班日历', path: '/schedule', icon: Calendar, bgColor: '#D1FAE5' })
  if (authStore.hasPermission('swap', 'read'))
    items.push({ label: '调班管理', path: '/swap?tab=' + (authStore.hasRole('admin') || authStore.hasRole('scheduler') || authStore.hasRole('leader') ? 'all' : (authStore.hasPermission('swap', 'approve') ? 'pending' : 'mine')), icon: Switch, bgColor: '#FCA5A5' })
  if (authStore.hasPermission('message', 'read'))
    items.push({ label: '消息中心', path: '/message', icon: Message, bgColor: '#BFDBFE' })
  if (authStore.hasRole('admin'))
    items.push({ label: '角色权限', path: '/roles', icon: Key, bgColor: '#E5E7EB' })
  if (authStore.hasRole('admin'))
    items.push({ label: '系统设置', path: '/system', icon: List, bgColor: '#FCE7F3' })
  return items
})

// ==================== 值班工作量统计 ====================
const workloadData = ref<ScheduleStatisticsResponse | null>(null)
const workloadLoading = ref(false)

const currentMonthLabel = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月`
})

const workloadSummary = computed(() =>
  workloadData.value?.summary || {
    total_staff: 0, total_shifts: 0,
    avg_shifts_per_person: 0, avg_hours_per_person: 0,
    total_night_shifts: 0,
  }
)

const workloadItems = computed(() => workloadData.value?.items || [])
const maxWorkloadWeight = computed(() => {
  if (!workloadItems.value.length) return 1
  return Math.max(...workloadItems.value.map(i => i.weight_score))
})

function getBarColor(index: number) {
  return ['#3B82F6', '#10B981', '#EF4444', '#FF6B6B', '#FFD93D'][index % 5]
}
function getScoreColor(index: number) { return getBarColor(index) }
function getBarWidth(score: number) {
  return maxWorkloadWeight.value > 0 ? (score / maxWorkloadWeight.value * 100) + '%' : '0%'
}

const fetchWorkload = async () => {
  if (!authStore.hasPermission('schedule', 'read')) return
  workloadLoading.value = true
  try {
    const d = new Date()
    const yy = d.getFullYear(), mm = d.getMonth()
    const startDate = `${yy}-${String(mm + 1).padStart(2, '0')}-01`
    const ld = new Date(yy, mm + 1, 0).getDate()
    const endDate = `${yy}-${String(mm + 1).padStart(2, '0')}-${String(ld).padStart(2, '0')}`
    workloadData.value = await getScheduleStatistics({ start_date: startDate, end_date: endDate, top: 5 })
  } catch { /* silently fail */ }
  finally { workloadLoading.value = false }
}

const shiftColors = ['#FFD166', '#06D6A0', '#118AB2', '#F08A5D']

// ==================== 本月排班状态明细 ====================
const scheduleStatus = ref({ published: 0, draft: 0, recalled: 0, total: 0 })

const fetchScheduleStatus = async () => {
  if (!authStore.hasPermission('schedule', 'read')) return
  try {
    const d = new Date()
    const yy = d.getFullYear(), mm = d.getMonth()
    const startDate = `${yy}-${String(mm + 1).padStart(2, '0')}-01`
    const ld = new Date(yy, mm + 1, 0).getDate()
    const endDate = `${yy}-${String(mm + 1).padStart(2, '0')}-${String(ld).padStart(2, '0')}`
    const res: any = await getSchedules({ start_date: startDate, end_date: endDate, page: 1, page_size: 200 })
    const items = res?.items || []
    scheduleStatus.value = {
      published: items.filter((s: any) => s.status === 1).length,
      draft: items.filter((s: any) => s.status === 0).length,
      recalled: items.filter((s: any) => s.status === 2).length,
      total: items.length,
    }
  } catch { /* silently fail */ }
}

// ==================== 班次模板统计 ====================
const shiftTemplateCount = ref(0)
const shiftTemplateDisabled = ref(0)

const fetchShiftTemplates = async () => {
  if (!authStore.hasPermission('shift_template', 'read')) return
  try {
    const res: any = await getShiftTemplates({ status: 1 })
    const items = Array.isArray(res) ? res : (res?.items || [])
    shiftTemplateCount.value = items.filter((t: any) => t.status === 1).length
  } catch { /* silently fail */ }
  try {
    const res: any = await getShiftTemplates({ status: 0 })
    const items = Array.isArray(res) ? res : (res?.items || [])
    shiftTemplateDisabled.value = items.filter((t: any) => t.status === 0).length
  } catch { /* silently fail */ }
}

// ==================== 数据加载 ====================
const fetchOverview = async () => {
  loading.value = true
  try {
    const { data: res } = await getDashboardOverview()
    if (res.code === 200) overview.value = { ...overview.value, ...res.data }
  } catch { ElMessage.error('获取看板数据失败') }
  finally { loading.value = false }
}

onMounted(async () => {
  await fetchOverview()
  await fetchWorkload()
  await fetchScheduleStatus()
  await fetchShiftTemplates()
})
</script>

<style scoped>
/* ================================================================
   页面特定布局（共享样式已迁移至 global.scss）
   ================================================================ */

/* --- 页面容器 --- */
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
@media (max-width: 768px) {
  .dashboard-page {
    gap: 16px;
    padding: 0 8px;
  }
}

/* --- 主内容区 --- */
.dashboard-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* --- 第一行：三列等宽 --- */
.tri-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 1200px) {
  .tri-row { grid-template-columns: 1fr; }
}
.tri-card { padding: 0; }
.tri-body { padding: 16px; min-height: 100px; }
@media (max-width: 768px) {
  .tri-body { padding: 12px; min-height: 80px; }
}

/* --- 第二行：左宽 + 右窄 --- */
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
}
@media (max-width: 1200px) {
  .bottom-row { grid-template-columns: 1fr; }
}
.main-left, .main-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* --- 统计卡片装饰图案（页面特有） --- */
.stat-deco {
  position: absolute;
  bottom: 10px;
  right: 14px;
  opacity: 0.12;
  font-size: 40px;
  font-weight: 900;
  line-height: 1;
  color: var(--neo-color-text-primary);
  pointer-events: none;
  transition: transform 0.3s ease, opacity 0.3s ease;
  user-select: none;
}
.stat-card:hover .stat-deco {
  transform: scale(1.15) rotate(5deg);
  opacity: 0.18;
}
.stat-deco-users::after { content: '👥'; font-size: 28px; }
.stat-deco-org::after   { content: '🏢'; font-size: 28px; }
.stat-deco-alert::after { content: '⚠️'; font-size: 28px; }
.stat-deco-msg::after   { content: '💬'; font-size: 28px; }
@media (max-width: 768px) {
  .stat-deco { display: none; }
}

/* --- 今日值班模块 --- */
.duty-list { display: flex; flex-direction: column; gap: 10px; }
.duty-shift-name {
  font-size: 14px;
  color: var(--neo-color-text-primary);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
}
.duty-detail {
  font-size: 13px;
  color: #555;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.duty-leader { color: var(--neo-color-accent-red); font-weight: 600; }
@media (max-width: 768px) {
  .duty-shift-name { font-size: 12px; }
  .duty-detail { font-size: 11px; }
}

/* --- 待处理事项 --- */
.pending-list { display: flex; flex-direction: column; gap: 10px; }
.pending-label { font-size: 14px; color: var(--neo-color-text-primary); font-weight: 700; }
.pending-count { font-size: 14px; color: var(--neo-color-text-secondary); font-weight: 700; }
@media (max-width: 768px) {
  .pending-label { font-size: 13px; }
  .pending-count { font-size: 13px; }
}

/* --- 通知列表 --- */
.notification-list { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
@media (max-width: 768px) {
  .notification-list { padding: 12px; gap: 8px; }
}

/* --- 快捷操作卡片 --- */
.quick-card { padding: 0; }
@media (max-width: 768px) {
  .action-grid { grid-template-columns: repeat(auto-fill, minmax(72px, 1fr)); padding: 14px; gap: 8px; }
  .qa-icon { width: 40px; height: 40px; }
  .qa-label { font-size: 11px; }
  .action-item { padding: 12px 6px; }
}

/* --- 班次模板统计 --- */
.template-stat-card { padding: 0; }
.template-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 20px;
}
.template-stat-item {
  text-align: center;
  padding: 14px 8px;
  background: var(--neo-color-bg-primary);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-active);
  transition: all 0.15s;
}
.template-stat-item:hover {
  box-shadow: var(--neo-shadow-default);
  transform: translate(var(--neo-translate-hover), var(--neo-translate-hover));
}
.template-stat-item .stat-value {
  font-size: 28px;
  font-weight: 900;
  line-height: 1;
  margin-bottom: 4px;
  transition: transform 0.2s ease;
  display: block;
  transform-origin: center;
}
.template-stat-item:hover .stat-value {
  transform: scale(1.12) rotate(-1deg);
}
.template-stat-item .stat-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--neo-color-text-secondary);
  text-transform: uppercase;
}
@media (max-width: 768px) {
  .template-stats { padding: 14px; gap: 8px; }
  .template-stat-item { padding: 10px 6px; }
  .template-stat-item .stat-value { font-size: 22px; }
  .template-stat-item .stat-label { font-size: 10px; }
}

/* --- 值班工作量统计 --- */
.workload-card { padding: 0; }
.workload-body {
  display: flex;
  gap: 28px;
  padding: 20px;
}
@media (max-width: 768px) {
  .workload-body {
    flex-direction: column;
    gap: 20px;
    padding: 16px;
  }
}
.unit-h { font-size: 13px; color: var(--neo-color-text-secondary); }
.workload-ranking { flex: 1; min-width: 0; }
.workload-ranking-title { font-size: 13px; color: var(--neo-color-text-primary); margin-bottom: 10px; }

/* --- 动画延迟（页面特有） --- */
.stat-card:nth-child(1) { animation: pop-in 0.35s ease both; animation-delay: 0.05s; }
.stat-card:nth-child(2) { animation: pop-in 0.35s ease both; animation-delay: 0.1s; }
.stat-card:nth-child(3) { animation: pop-in 0.35s ease both; animation-delay: 0.15s; }
.stat-card:nth-child(4) { animation: pop-in 0.35s ease both; animation-delay: 0.2s; }
.duty-list .neo-list-item:nth-child(1) { animation-delay: 0.1s; }
.duty-list .neo-list-item:nth-child(2) { animation-delay: 0.15s; }
.duty-list .neo-list-item:nth-child(3) { animation-delay: 0.2s; }
.duty-list .neo-list-item:nth-child(4) { animation-delay: 0.25s; }
.duty-list .neo-list-item:nth-child(5) { animation-delay: 0.3s; }
.pending-list .neo-list-item:nth-child(1) { animation-delay: 0.1s; }
.pending-list .neo-list-item:nth-child(2) { animation-delay: 0.15s; }
.ranking-list .ranking-item:nth-child(1) { animation-delay: 0.1s; }
.ranking-list .ranking-item:nth-child(2) { animation-delay: 0.15s; }
.ranking-list .ranking-item:nth-child(3) { animation-delay: 0.2s; }
.ranking-list .ranking-item:nth-child(4) { animation-delay: 0.25s; }
.ranking-list .ranking-item:nth-child(5) { animation-delay: 0.3s; }
.mini-stat-card:nth-child(1) { animation-delay: 0.05s; }
.mini-stat-card:nth-child(2) { animation-delay: 0.1s; }
.mini-stat-card:nth-child(3) { animation-delay: 0.15s; }
.mini-stat-card:nth-child(4) { animation-delay: 0.2s; }
</style>
