<template>
  <el-drawer
    :model-value="visible"
    :title="drawerTitle"
    direction="rtl"
    size="420px"
    @close="handleClose"
  >
    <template v-if="schedule">
      <!-- 班次信息 -->
      <div class="info-section">
        <div class="info-row">
          <span class="info-label">日期</span>
          <span class="info-value">{{ schedule.date }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">班次</span>
          <span class="info-value">
            <span class="color-dot" :style="{ background: schedule.shift_color || '#999' }"></span>
            {{ schedule.shift_name || '未知' }}
            <span class="time-text">{{ schedule.shift_start_time }}-{{ schedule.shift_end_time }}</span>
          </span>
        </div>
        <div class="info-row">
          <span class="info-label">组织</span>
          <span class="info-value">{{ schedule.org_name || '-' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">状态</span>
          <el-tag :type="statusTagType" size="small">{{ statusText }}</el-tag>
        </div>
      </div>

      <el-divider />

      <!-- 值班领导 -->
      <div class="section">
        <div class="section-title">值班领导</div>
        <StaffSelector
          v-if="isDraft && authStore.hasPermission('schedule', 'update')"
          :model-value="schedule.leader_staff_id"
          :org-id="schedule.org_id"
          placeholder="选择值班领导"
          @update:model-value="handleLeaderChange"
        />
        <div v-else class="current-leader">
          <template v-if="schedule.leaders?.length">
            <span v-for="(l, i) in schedule.leaders" :key="i" class="leader-name-item">{{ l.name }}</span>
          </template>
          <template v-else>{{ schedule.leader_name || '未指定' }}</template>
        </div>
      </div>

      <el-divider />

      <!-- 值班人员 -->
      <div class="section">
        <div class="section-title">
          值班人员（{{ memberDetails.length }}人）
        </div>

        <!-- 已分配人员列表 -->
        <div class="member-list">
          <div v-for="d in memberDetails" :key="d.id" class="member-item">
            <div class="member-info">
              <span class="member-name">{{ d.staff_name }}</span>
              <el-tag v-if="d.is_substitute" size="small" type="warning">替班</el-tag>
              <el-tag v-if="d.role_type === 'leader'" size="small" type="success">领导</el-tag>
            </div>
            <el-button
              v-if="isDraft && authStore.hasPermission('schedule', 'delete')"
              type="danger"
              link
              size="small"
              @click="handleRemoveMember(d)"
            >
              移除
            </el-button>
          </div>
          <el-empty v-if="memberDetails.length === 0" description="暂无值班人员" :image-size="48" />
        </div>

        <!-- 添加人员：需要 schedule update 权限 -->
        <div v-if="isDraft && authStore.hasPermission('schedule', 'update')" class="add-member-area">
          <StaffSelector
            v-model="newStaffId"
            :org-id="schedule.org_id"
            :exclude-ids="existingStaffIds"
            placeholder="搜索并添加人员"
          />
          <div class="add-member-options">
            <el-checkbox v-model="isSubstitute" label="替班" size="small" />
            <el-radio-group v-model="newRoleType" size="small">
              <el-radio-button value="member">成员</el-radio-button>
              <el-radio-button value="leader">领导</el-radio-button>
            </el-radio-group>
            <el-button type="primary" size="small" :disabled="!newStaffId" @click="handleAddMember">
              添加
            </el-button>
          </div>
        </div>
      </div>

      <!-- 冲突提示 -->
      <template v-if="conflicts.length > 0">
        <el-divider />
        <div class="section">
          <div class="section-title" style="color: #DC3545">
            <el-icon><WarningFilled /></el-icon>
            冲突提示
          </div>
          <div class="conflict-list">
            <div v-for="(msg, idx) in conflicts" :key="idx" class="conflict-item">
              {{ msg }}
            </div>
          </div>
        </div>
      </template>

      <!-- 操作按钮 -->
      <div class="drawer-footer">
        <!-- 删除：需要 schedule delete 权限 -->
        <el-button
          v-if="isDraft && authStore.hasPermission('schedule', 'delete')"
          type="danger"
          @click="handleDelete"
        >
          删除
        </el-button>
        <div style="flex: 1" />
        <el-button @click="handleClose">关闭</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { Schedule, ScheduleDetail, CalendarShift } from '@/api/schedule'
import {
  getSchedule,
  deleteSchedule,
  assignStaff,
  removeStaff,
} from '@/api/schedule'
import StaffSelector from './StaffSelector.vue'

const props = defineProps<{
  visible: boolean
  schedule: Schedule | null
  calendarShift: CalendarShift | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'refresh'): void
}>()

// ==================== 权限 ====================

const authStore = useAuthStore()

// ==================== 状态 ====================

const newStaffId = ref<number | null>(null)
const isSubstitute = ref(false)
const newRoleType = ref<string>('member')

// ==================== 计算属性 ====================

const drawerTitle = computed(() => {
  if (!props.schedule) return '排班详情'
  return `${props.schedule.date} ${props.schedule.shift_name || ''}`
})

const isDraft = computed(() => props.schedule?.status === 0 || props.schedule?.status === 2)

const statusText = computed(() => {
  const map: Record<number, string> = { 0: '草稿', 1: '已发布', 2: '已撤回', 3: '待审核' }
  return map[props.schedule?.status ?? 0] || '未知'
})

const statusTagType = computed(() => {
  const map: Record<number, string> = { 0: 'info', 1: 'success', 2: 'warning', 3: 'danger' }
  return map[props.schedule?.status ?? 0] || 'info'
})

const memberDetails = computed(() => {
  return props.schedule?.details || []
})

const existingStaffIds = computed(() => {
  return memberDetails.value.map((d) => d.staff_id)
})

const conflicts = computed(() => {
  return props.calendarShift?.conflicts || []
})

// ==================== 操作 ====================

async function handleLeaderChange(staffId: number | number[] | null) {
  if (!props.schedule || staffId === null || staffId === undefined || typeof staffId === 'object') return
  try {
    const oldLeader = memberDetails.value.find((d) => d.role_type === 'leader')
    if (oldLeader) {
      await removeStaff(props.schedule.id, oldLeader.staff_id)
    }
    await assignStaff(props.schedule.id, {
      staff_id: staffId as number,
      role_type: 'leader',
    })
    ElMessage.success('领导设置成功')
    emit('refresh')
  } catch (e) {
    // interceptor handles error
  }
}

async function handleAddMember() {
  if (!newStaffId.value || !props.schedule || newStaffId.value === 0) return
  try {
    await assignStaff(props.schedule.id, {
      staff_id: newStaffId.value,
      role_type: newRoleType.value,
      is_substitute: isSubstitute.value,
    })
    ElMessage.success('添加成功')
    newStaffId.value = null
    isSubstitute.value = false
    newRoleType.value = 'member'
    emit('refresh')
  } catch (e) {
    // interceptor handles error
  }
}

async function handleRemoveMember(detail: ScheduleDetail) {
  if (!props.schedule) return
  try {
    await ElMessageBox({
      title: '确认移除？',
      message: `确认移除「${detail.staff_name}」的值班安排？`,
      showCancelButton: true,
      confirmButtonText: '移除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await removeStaff(props.schedule.id, detail.staff_id)
    ElMessage.success('移除成功')
    emit('refresh')
  } catch (e) {
    // 用户取消或接口错误
  }
}

async function handleDelete() {
  if (!props.schedule) return
  try {
    await ElMessageBox({
      title: '确认删除？',
      message: `确认删除 ${props.schedule.date} ${props.schedule.shift_name} 的排班记录？删除后无法恢复。`,
      showCancelButton: true,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteSchedule(props.schedule.id)
    ElMessage.success('删除成功')
    handleClose()
    emit('refresh')
  } catch (e) {
    // 用户取消或接口错误
  }
}

function handleClose() {
  emit('update:visible', false)
}
</script>

<style scoped>
.info-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  font-size: 14px;
}

.info-label {
  width: 60px;
  color: #909399;
  flex-shrink: 0;
}

.info-value {
  color: #1F2D3D;
  display: flex;
  align-items: center;
  gap: 6px;
}

.color-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}

.time-text {
  font-size: 12px;
  color: #909399;
}

.section {
  margin-bottom: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1F2D3D;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.current-leader {
  font-size: 14px;
  color: #556173;
  padding: 4px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.leader-name-item {
  font-size: 14px;
  color: #556173;
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.member-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: #F5F7FA;
  border-radius: 4px;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.member-name {
  font-size: 14px;
  color: #1F2D3D;
}

.add-member-area {
  border: 1px dashed #E6EAF0;
  border-radius: 6px;
  padding: 12px;
}

.add-member-options {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.conflict-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.conflict-item {
  font-size: 13px;
  color: #DC3545;
  padding: 8px 10px;
  background: #FFF5F5;
  border-radius: 4px;
  border-left: 3px solid #DC3545;
}

.drawer-footer {
  display: flex;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #E6EAF0;
  margin-top: 16px;
}
</style>
