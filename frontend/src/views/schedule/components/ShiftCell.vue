<template>
  <div
    class="shift-block"
    :class="{
      'has-conflict': shift.conflicts.length > 0,
      'shift-dragging': isShiftDragging,
      'staff-drop-over': isStaffDropOver,
      'shift-drop-over': isShiftSwapOver,
    }"
    :draggable="editable()"
    @click.stop="$emit('click', shift)"
    @dragstart="onShiftDragStart"
    @dragend="onShiftDragEnd"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- 班次名称 + 时间 — 第一行 -->
    <div class="shift-main-row">
      <span
        class="shift-tag shift-tag-main"
        :style="{ background: shift.shift_color, color: getContrastColor(shift.shift_color) }"
      >
        {{ shift.shift_name }}
        <span class="shift-time">{{ shift.start_time }}-{{ shift.end_time }}</span>
      </span>
    </div>

    <!-- 领导 + 组员 — 第二行混合排列，flex-wrap 自适应换行 -->
    <div class="shift-person-row">
      <!-- 领导 -->
      <template v-if="shift.leaders?.length">
        <span
          v-for="l in leaderNames"
          :key="'l-' + l"
          class="shift-tag shift-tag-leader"
          :style="{ background: shift.shift_color, color: getContrastColor(shift.shift_color) }"
        >
          {{ l }}
        </span>
      </template>
      <template v-else-if="shift.leader">
        <span
          class="shift-tag shift-tag-leader"
          :style="{ background: shift.shift_color, color: getContrastColor(shift.shift_color) }"
        >
          {{ shift.leader.name }}
        </span>
      </template>

      <!-- 组员 -->
      <template v-for="(m, idx) in displayMembers" :key="m.staff_id">
        <span
          class="shift-tag shift-tag-member"
          :class="{ 'member-draggable': editable() }"
          :draggable="editable()"
          @dragstart.stop="onMemberDragStart($event, m.staff_id, idx)"
          @dragend="onMemberDragEnd"
          @dragover.prevent.stop="onMemberDragOver($event, idx)"
          @dragleave="onMemberDragLeave"
          @drop.prevent.stop="onMemberDrop($event, idx)"
          :title="'拖拽调整人员'"
          :style="{ borderColor: shift.shift_color }"
        >
          {{ m.name }}
        </span>
      </template>
      <span v-if="shift.members.length > 3" class="member-more">+{{ shift.members.length - 3 }}</span>
    </div>

    <!-- 状态标记 -->
    <div v-if="shift.status === 1" class="status-dot published" title="已发布"></div>
    <div v-if="shift.status === 2" class="status-dot recalled" title="已撤回"></div>
    <div v-if="shift.status === 3" class="status-dot pending" title="待审核"></div>

    <!-- 冲突标记 -->
    <el-icon v-if="shift.conflicts.length > 0" class="conflict-icon" color="#EF4444">
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

// ---- 领导名单（合并 leaders 数组和 leader 对象） ----
const leaderNames = computed(() => {
  if (props.shift.leaders?.length) {
    return props.shift.leaders.map(l => l.name)
  }
  if (props.shift.leader) {
    return [props.shift.leader.name]
  }
  return []
})

// ---- 对比色：深色背景用白字，浅色背景用黑字 ----
function getContrastColor(hex: string): string {
  if (!hex) return '#000000'
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.55 ? '#000000' : '#FFFFFF'
}

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
    if (fromIdx !== toIdx) {
      reorderMembers(fromIdx, toIdx)
      emit('staffReorder', staffId, props.shift.schedule_id, fromIdx, toIdx)
    }
  } else {
    emit('staffDrop', staffId, fromSid, props.shift.schedule_id)
  }
}

// ---- 统一接收拖放 ----
const isStaffDropOver = ref(false)
const isShiftSwapOver = ref(false)

function onDragOver(e: DragEvent) {
  if (!e.dataTransfer) return
  const types = e.dataTransfer.types
  if (types.includes('application/shift-swap-id')) {
    const fromId = parseInt(e.dataTransfer.getData('application/shift-swap-id') || '0')
    if (fromId === props.shift.schedule_id) return
    if (!editable()) return
    isShiftSwapOver.value = true
    e.dataTransfer.dropEffect = 'move'
  } else if (types.includes('application/staff-id')) {
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
  padding: 4px 5px;
  margin-bottom: 3px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.1s ease;
  position: relative;
  border: 2px solid #000000;
  border-radius: 2px;
  background: #FFFFFF;
  box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.shift-block:hover {
  box-shadow: 4px 4px 0px 0px #000000;
  transform: translate(-1px, -1px);
}

.shift-block.shift-dragging {
  opacity: 0.4;
}

.shift-block.staff-drop-over {
  border: 2px dashed #3B82F6;
  background: #DBEAFE !important;
  box-shadow: 3px 3px 0px 0px #3B82F6;
}

.shift-block.shift-drop-over {
  border: 2px dashed #10B981;
  background: #D1FAE5 !important;
  box-shadow: 3px 3px 0px 0px #10B981;
}

.shift-block[draggable="true"] {
  cursor: grab;
}

.shift-block[draggable="true"]:active {
  cursor: grabbing;
}

.shift-block.has-conflict {
  border: 2px solid #EF4444;
  box-shadow: 2px 2px 0px 0px #EF4444;
}

/* ---- 班次名行 ---- */
.shift-main-row {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 2px;
  overflow: hidden;
  min-width: 0;
}

/* ---- 人员行（领导+组员混排，flex-wrap 自适应换行） ---- */
.shift-person-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  min-width: 0;
}

/* ---- 原型风格紧凑标签 ---- */
.shift-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 5px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.4;
  border: 2px solid #000000;
  border-radius: 2px;
  white-space: nowrap;
  transition: all 0.1s ease;
  flex-shrink: 0;
}

.shift-tag:hover {
  box-shadow: 1px 1px 0px 0px #000000;
  transform: translate(-1px, -1px);
}

.shift-tag-leader {
  color: #FFFFFF;
  text-shadow: 0 1px 0 rgba(255,255,255,0.3);
}

.shift-tag-member {
  background: #FFFFFF;
  color: #333333;
  font-weight: 600;
}

.shift-tag-main {
  color: #FFFFFF;
  text-shadow: 0 1px 0 rgba(255,255,255,0.3);
}

.shift-tag .shift-time {
  font-size: 9px;
  color: rgba(255,255,255,0.8);
  margin-left: 3px;
  font-weight: 600;
}

.shift-tag-member .shift-time {
  color: #666666;
}

/* ---- 成员拖拽 ---- */
.member-draggable {
  cursor: grab;
}

.member-draggable:active {
  cursor: grabbing;
}

.member-draggable:hover {
  background: rgba(59, 130, 246, 0.1) !important;
  border-color: #3B82F6 !important;
  box-shadow: 1px 1px 0px 0px rgba(59, 130, 246, 0.3);
  transform: translate(-1px, -1px);
}

/* ---- "+N 更多" ---- */
.member-more {
  font-size: 10px;
  color: #999999;
  line-height: 16px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ---- 状态标记 ---- */
.status-dot {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 7px;
  height: 7px;
  border-radius: 2px;
  border: 1px solid rgba(0,0,0,0.3);
  transition: transform 0.2s ease;
}

.status-dot:hover {
  transform: scale(1.3);
}

.status-dot.published {
  background: #10B981;
}

.status-dot.recalled {
  background: #6B7280;
}

.status-dot.pending {
  background: #FFD93D;
}

.conflict-icon {
  position: absolute;
  bottom: 1px;
  right: 1px;
  font-size: 11px;
}

/* ============================================
   移动端适配
   ============================================ */

@media (max-width: 768px) {
  .shift-block {
    padding: 3px 4px;
    margin-bottom: 2px;
    font-size: 10px;
  }

  .shift-tag {
    font-size: 9px;
    padding: 1px 3px;
  }

  .shift-tag .shift-time {
    font-size: 8px;
  }

  .shift-leader-row,
  .shift-main-row,
  .shift-member-row {
    gap: 2px;
  }

  .status-dot {
    width: 6px;
    height: 6px;
  }

  .conflict-icon {
    font-size: 10px;
  }
}

@media (max-width: 480px) {
  .shift-block {
    padding: 2px 3px;
    margin-bottom: 2px;
    font-size: 9px;
  }

  .shift-tag {
    font-size: 8px;
    padding: 0px 3px;
  }

  .shift-tag .shift-time {
    font-size: 7px;
  }

  .member-more {
    font-size: 9px;
  }
}
</style>
