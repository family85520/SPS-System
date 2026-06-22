<template>
  <div
    class="shift-block"
    :style="{
      background: shift.shift_color + '18',
      borderLeft: `3px solid ${shift.shift_color}`,
    }"
    :class="{
      'has-conflict': shift.conflicts.length > 0,
      'shift-dragging': isShiftDragging,
      'staff-drop-over': isStaffDropOver,
      'shift-drop-over': isShiftSwapOver,
    }"
    :draggable="(shift.status === 0 || shift.status === 2)"
    @click.stop="$emit('click', shift)"
    @dragstart="onShiftDragStart"
    @dragend="onShiftDragEnd"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- 领导标签 -->
    <div v-if="shift.leaders?.length" class="leader-list">
      <span v-for="(l, i) in shift.leaders" :key="i" class="leader-tag-item" :style="{ background: shift.shift_color }">{{ l.name }}</span>
    </div>
    <div v-else-if="shift.leader" class="leader-list">
      <span class="leader-tag-item" :style="{ background: shift.shift_color }">{{ shift.leader.name }}</span>
    </div>

    <!-- 班次名称 + 时间 -->
    <div class="shift-header">
      <span class="shift-name" :style="{ color: shift.shift_color }">{{ shift.shift_name }}</span>
      <span class="shift-time">{{ shift.start_time }}-{{ shift.end_time }}</span>
    </div>

    <!-- 值班人员（可拖拽调整顺序/移动班次） -->
    <div class="shift-members">
      <span
        v-for="(m, idx) in displayMembers"
        :key="m.staff_id"
        class="member-name"
        :class="{
          'member-draggable': shift.status === 0 || shift.status === 2,
          'member-drop-before': dropTargetIdx === idx,
        }"
        :draggable="shift.status === 0 || shift.status === 2"
        @dragstart.stop="onMemberDragStart($event, m.staff_id, idx)"
        @dragend="onMemberDragEnd"
        @dragover.prevent.stop="onMemberDragOver($event, idx)"
        @dragleave="onMemberDragLeave"
        @drop.prevent.stop="onMemberDrop($event, idx)"
        :title="'拖拽调整人员'"
      >
        {{ m.name }}
      </span>
      <span v-if="shift.members.length > 3" class="member-more">+{{ shift.members.length - 3 }}</span>
    </div>

    <!-- 状态标记 -->
    <div v-if="shift.status === 1" class="status-dot published" title="已发布"></div>
    <div v-if="shift.status === 2" class="status-dot recalled" title="已撤回"></div>
    <div v-if="shift.status === 3" class="status-dot pending" title="待审核"></div>

    <!-- 冲突标记 -->
    <el-icon v-if="shift.conflicts.length > 0" class="conflict-icon" color="#DC3545">
      <WarningFilled />
    </el-icon>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'
import type { CalendarShift, StaffInfo } from '@/api/schedule'

const props = defineProps<{
  shift: CalendarShift
}>()

const emit = defineEmits<{
  (e: 'click', shift: CalendarShift): void
  (e: 'staffDrag', staffId: number, fromScheduleId: number): void
  (e: 'staffDrop', staffId: number, fromScheduleId: number, toScheduleId: number): void
  (e: 'staffReorder', staffId: number, scheduleId: number, fromIdx: number, toIdx: number): void
  (e: 'shiftSwap', fromScheduleId: number, toScheduleId: number): void
}>()

const editable = () => props.shift.status === 0 || props.shift.status === 2

// ---- 成员显示顺序（拖拽重排） ----
const memberOrder = ref<number[] | null>(null)

const displayMembers = computed(() => {
  const members = props.shift.members.slice(0, 3)
  if (memberOrder.value && memberOrder.value.length === members.length) {
    return memberOrder.value.map(i => members[i])
  }
  return members
})

function reorderMembers(fromIdx: number, toIdx: number) {
  const members = displayMembers.value
  const item = members.splice(fromIdx, 1)[0]
  members.splice(toIdx, 0, item)
  memberOrder.value = members.map(m => props.shift.members.indexOf(m))
}

// ---- 班次互换拖拽 ----
const isShiftDragging = ref(false)

function onShiftDragStart(e: DragEvent) {
  isShiftDragging.value = true
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('application/shift-swap-id', String(props.shift.schedule_id))
  }
}

function onShiftDragEnd() {
  isShiftDragging.value = false
}

// ---- 人员拖拽 ----
const draggingMemberId = ref(0)
const draggingMemberIdx = ref(-1)
const dropTargetIdx = ref(-1)

function onMemberDragStart(e: DragEvent, staffId: number, idx: number) {
  draggingMemberId.value = staffId
  draggingMemberIdx.value = idx
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('application/staff-id', String(staffId))
    e.dataTransfer.setData('application/from-schedule-id', String(props.shift.schedule_id))
    e.dataTransfer.setData('application/from-idx', String(idx))
  }
  emit('staffDrag', staffId, props.shift.schedule_id)
}

function onMemberDragEnd() {
  draggingMemberId.value = 0
  draggingMemberIdx.value = -1
  dropTargetIdx.value = -1
}

function onMemberDragOver(_e: DragEvent, idx: number) {
  dropTargetIdx.value = idx
}

function onMemberDragLeave() {
  dropTargetIdx.value = -1
}

function onMemberDrop(e: DragEvent, toIdx: number) {
  dropTargetIdx.value = -1
  const staffId = parseInt(e.dataTransfer?.getData('application/staff-id') || '0')
  const fromSid = parseInt(e.dataTransfer?.getData('application/from-schedule-id') || '0')
  const fromIdx = parseInt(e.dataTransfer?.getData('application/from-idx') || '0')
  if (!staffId || !fromSid) return

  if (fromSid === props.shift.schedule_id) {
    // 同班次内：调整显示顺序
    if (fromIdx !== toIdx) {
      reorderMembers(fromIdx, toIdx)
      emit('staffReorder', staffId, props.shift.schedule_id, fromIdx, toIdx)
    }
  } else {
    // 跨班次：移动到目标班次
    emit('staffDrop', staffId, fromSid, props.shift.schedule_id)
  }
}

// ---- 统一接收拖放（区分班次互换 vs 人员移动） ----
const isStaffDropOver = ref(false)
const isShiftSwapOver = ref(false)

function onDragOver(e: DragEvent) {
  if (!e.dataTransfer) return
  const types = e.dataTransfer.types
  if (types.includes('application/shift-swap-id')) {
    // 班次互换：排除自身
    const fromId = parseInt(e.dataTransfer.getData('application/shift-swap-id') || '0')
    if (fromId === props.shift.schedule_id) return
    if (!editable()) return
    isShiftSwapOver.value = true
    e.dataTransfer.dropEffect = 'move'
  } else if (types.includes('application/staff-id')) {
    // 人员移动：排除自身班次
    const fromSid = parseInt(e.dataTransfer.getData('application/from-schedule-id') || '0')
    if (fromSid === props.shift.schedule_id) return
    if (!editable()) return
    isStaffDropOver.value = true
    e.dataTransfer.dropEffect = 'move'
  }
}

function onDragLeave() {
  isStaffDropOver.value = false
  isShiftSwapOver.value = false
}

function onDrop(e: DragEvent) {
  isStaffDropOver.value = false
  isShiftSwapOver.value = false
  if (!e.dataTransfer) return
  if (e.dataTransfer.types.includes('application/shift-swap-id')) {
    const fromId = parseInt(e.dataTransfer.getData('application/shift-swap-id') || '0')
    if (fromId && fromId !== props.shift.schedule_id) {
      emit('shiftSwap', fromId, props.shift.schedule_id)
    }
  } else if (e.dataTransfer.types.includes('application/staff-id')) {
    const staffId = parseInt(e.dataTransfer.getData('application/staff-id') || '0')
    const fromSid = parseInt(e.dataTransfer.getData('application/from-schedule-id') || '0')
    if (staffId && fromSid) {
      emit('staffDrop', staffId, fromSid, props.shift.schedule_id)
    }
  }
}
</script>

<style scoped>
.shift-block {
  border-radius: 3px;
  padding: 4px 6px;
  margin-bottom: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}

.shift-block:hover {
  filter: brightness(0.95);
  transform: scale(1.01);
}

.shift-block.shift-dragging {
  opacity: 0.4;
}

.shift-block.staff-drop-over {
  outline: 2px dashed #0A63D8;
  outline-offset: -1px;
  background: #ECF5FF !important;
}

.shift-block.shift-drop-over {
  outline: 2px dashed #28A745;
  outline-offset: -1px;
  background: #F0FDF4 !important;
}

.shift-block[draggable="true"] {
  cursor: grab;
}

.shift-block[draggable="true"]:active {
  cursor: grabbing;
}

.shift-block.has-conflict {
  border: 1px solid #DC3545;
}

.leader-list {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}
.leader-tag-item {
  color: #FFFFFF;
  padding: 0 5px;
  border-radius: 2px;
  font-size: 10px;
  line-height: 16px;
}

.shift-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  margin-bottom: 2px;
}

.shift-name {
  font-weight: 600;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shift-time {
  font-size: 10px;
  color: #909399;
  flex-shrink: 0;
}

.shift-members {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.member-name {
  font-size: 11px;
  color: #556173;
  background: rgba(255, 255, 255, 0.6);
  padding: 0 4px;
  border-radius: 2px;
  line-height: 16px;
}

.member-name.member-draggable {
  cursor: grab;
}

.member-name.member-draggable:active {
  cursor: grabbing;
}

.member-name.member-draggable:hover {
  background: rgba(10, 99, 216, 0.15);
  color: #0A63D8;
}

.member-name.member-drop-before {
  border-left: 2px solid #0A63D8;
  padding-left: 2px;
}

.member-more {
  font-size: 10px;
  color: #909399;
  line-height: 16px;
}

.status-dot {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.published {
  background: #28A745;
}

.status-dot.recalled {
  background: #909399;
}

.status-dot.pending {
  background: #E6A23C;
}

.conflict-icon {
  position: absolute;
  bottom: 3px;
  right: 3px;
  font-size: 14px;
}
</style>
