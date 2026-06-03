<template>
  <div
    class="shift-block"
    :style="{
      background: shift.shift_color + '18',
      borderLeft: `3px solid ${shift.shift_color}`,
    }"
    :class="{ 'has-conflict': shift.conflicts.length > 0 }"
    @click.stop="$emit('click', shift)"
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

    <!-- 值班人员 -->
    <div class="shift-members">
      <span v-for="m in shift.members.slice(0, 3)" :key="m.staff_id" class="member-name">
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
import { WarningFilled } from '@element-plus/icons-vue'
import type { CalendarShift } from '@/api/schedule'

defineProps<{
  shift: CalendarShift
}>()

defineEmits<{
  (e: 'click', shift: CalendarShift): void
}>()
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
