<template>
  <el-drawer
    :model-value="visible"
    :title="drawerTitle"
    direction="rtl"
    size="460px"
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
          <el-tag :type="statusTagType" size="small" effect="dark">{{ statusText }}</el-tag>
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

        <div class="member-list">
          <div v-for="d in memberDetails" :key="d.id" class="member-item">
            <div class="member-info">
              <span class="member-name">{{ d.staff_name }}</span>
              <el-tag v-if="d.is_substitute" size="small" type="warning" effect="dark">替班</el-tag>
              <el-tag v-if="d.role_type === 'leader'" size="small" type="success" effect="dark">领导</el-tag>
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

        <div v-if="isDraft && authStore.hasPermission('schedule', 'update')" class="add-member-area">
          <StaffSelector
            v-model="newStaffId"
            :org-id="schedule.org_id"
            :exclude-ids="existingStaffIds"
            placeholder="搜索并添加人员"
          />
          <div class="add-member-options">
            <el-checkbox v-model="isSubstitute" label="替班" size="small" />
            <el-radio-group v-model="newRoleType" size="small" class="neo-radio-group">
              <el-radio-button value="member">成员</el-radio-button>
              <el-radio-button value="leader">领导</el-radio-button>
            </el-radio-group>
            <el-button size="small" :disabled="!newStaffId" class="btn-neo-primary" @click="handleAddMember">
              添加
            </el-button>
          </div>
        </div>
      </div>

      <!-- 冲突提示 -->
      <template v-if="conflicts.length > 0">
        <el-divider />
        <div class="section">
          <div class="section-title" style="color: #EF4444">
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
        <el-button
          v-if="isDraft && authStore.hasPermission('schedule', 'delete')"
          type="danger"
          class="btn-neo-danger"
          @click="handleDelete"
        >
          删除
        </el-button>
        <div style="flex: 1" />
        <el-button class="btn-neo-ghost" @click="handleClose">关闭</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useConfirm } from '@/composables/useConfirm'
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

const authStore = useAuthStore()
const { confirm } = useConfirm()

const newStaffId = ref<number | null>(null)
const isSubstitute = ref(false)
const newRoleType = ref<string>('member')

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
    await confirm({
      type: 'danger',
      title: '确认移除？',
      message: `确认移除「${detail.staff_name}」的值班安排？`,
      confirmText: '移除',
      cancelText: '取消',
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
    await confirm({
      type: 'danger',
      title: '确认删除？',
      message: `确认删除 ${props.schedule.date} ${props.schedule.shift_name} 的排班记录？删除后无法恢复。`,
      confirmText: '删除',
      cancelText: '取消',
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
  color: #666;
  flex-shrink: 0;
  font-weight: 700;
}

.info-value {
  color: #000000;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  border: 2px solid #000000;
  flex-shrink: 0;
}

.time-text {
  font-size: 12px;
  color: #666;
  font-weight: 600;
}

.section {
  margin-bottom: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 900;
  color: #000000;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.current-leader {
  font-size: 14px;
  color: #333;
  padding: 4px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  font-weight: 600;
}
.leader-name-item {
  font-size: 14px;
  color: #333;
  font-weight: 600;
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
  padding: 10px 12px;
  background: #FFFDF5;
  border: 3px solid #000000;
  box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.06);
  transition: all 0.15s ease;
}

.member-item:hover {
  box-shadow: 4px 4px 0px 0px #000000;
  transform: translate(-1px, -1px);
}

.member-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.member-name {
  font-size: 14px;
  color: #000000;
  font-weight: 700;
}

.add-member-area {
  border: 3px dashed #000000;
  border-radius: 4px;
  padding: 14px;
  background: #FFFDF5;
  box-shadow: inset 2px 2px 0px 0px rgba(0,0,0,0.05);
}

.add-member-options {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.conflict-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.conflict-item {
  font-size: 13px;
  color: #EF4444;
  padding: 10px 12px;
  background: #FEE2E2;
  border: 3px solid #000000;
  border-left: 4px solid #EF4444;
  border-radius: 3px;
  font-weight: 600;
  box-shadow: 2px 2px 0px 0px rgba(239,68,68,0.15);
  transition: all 0.15s ease;
}

.conflict-item:hover {
  box-shadow: 3px 3px 0px 0px rgba(239,68,68,0.25);
  transform: translate(-1px, -1px);
}

.drawer-footer {
  display: flex;
  align-items: center;
  padding-top: 16px;
  border-top: 3px solid #000000;
  margin-top: 16px;
}
</style>
