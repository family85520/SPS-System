<template>
  <div class="calendar-grid">
    <!-- 月视图 -->
    <template v-if="viewMode === 'month'">
      <!-- 星期头部 -->
      <div class="weekday-header">
        <div v-for="day in weekdayLabels" :key="day" class="weekday-cell">{{ day }}</div>
      </div>

      <!-- 日期网格 -->
      <div class="month-grid">
        <div
          v-for="(row, ri) in monthGrid"
          :key="ri"
          class="month-row"
        >
          <div
            v-for="(cell, ci) in row"
            :key="ci"
            class="day-cell"
            :class="{
              'other-month': !cell.isCurrentMonth,
              'is-today': cell.isToday,
              'is-weekend': cell.isWeekend,
            }"
          >
            <div class="day-header">
              <span class="day-number" :class="{ today: cell.isToday }">{{ cell.day }}</span>
              <el-button
                v-if="cell.isCurrentMonth"
                class="add-btn"
                size="small"
                circle
                @click.stop="$emit('addSchedule', cell.dateStr)"
              >
                <el-icon><Plus /></el-icon>
              </el-button>
            </div>

            <div class="shift-list">
              <ShiftCell
                v-for="shift in getShiftsForDate(cell.dateStr)"
                :key="shift.schedule_id"
                :shift="shift"
                @click="$emit('clickShift', $event)"
              />
              <div
                v-if="getShiftsForDate(cell.dateStr).length > maxVisible"
                class="more-indicator"
                @click.stop="$emit('clickShift', getShiftsForDate(cell.dateStr)[0])"
              >
                +{{ getShiftsForDate(cell.dateStr).length - maxVisible }} 更多
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 周视图 -->
    <template v-if="viewMode === 'week'">
      <div class="week-grid">
        <div
          v-for="cell in weekCells"
          :key="cell.dateStr"
          class="week-day-col"
          :class="{ 'is-today': cell.isToday, 'is-weekend': cell.isWeekend }"
        >
          <div class="week-day-header">
            <span class="weekday-name">{{ weekdayLabels[cell.weekday] }}</span>
            <span class="day-number" :class="{ today: cell.isToday }">{{ cell.day }}</span>
            <el-button
              class="add-btn"
              size="small"
              circle
              @click.stop="$emit('addSchedule', cell.dateStr)"
            >
              <el-icon><Plus /></el-icon>
            </el-button>
          </div>

          <div class="shift-list">
            <ShiftCell
              v-for="shift in getShiftsForDate(cell.dateStr)"
              :key="shift.schedule_id"
              :shift="shift"
              @click="$emit('clickShift', $event)"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import type { CalendarDate, CalendarShift } from '@/api/schedule'
import ShiftCell from './ShiftCell.vue'

const props = defineProps<{
  year: number
  month: number  // 0-based (0=Jan, 11=Dec)
  viewMode: 'month' | 'week'
  calendarData: CalendarDate[]
  currentWeekStart?: Date  // 周视图的起始日期
  maxVisible?: number
}>()

defineEmits<{
  (e: 'clickShift', shift: CalendarShift): void
  (e: 'addSchedule', dateStr: string): void
}>()

const weekdayLabels = ['一', '二', '三', '四', '五', '六', '日']
const maxVisible = computed(() => props.maxVisible ?? 3)

// ==================== 数据索引 ====================

const dateShiftMap = computed(() => {
  const map: Record<string, CalendarShift[]> = {}
  for (const d of props.calendarData) {
    map[d.date] = d.shifts
  }
  return map
})

function getShiftsForDate(dateStr: string): CalendarShift[] {
  return dateShiftMap.value[dateStr] || []
}

// ==================== 月视图网格 ====================

interface DayCell {
  date: Date
  dateStr: string
  day: number
  weekday: number
  isCurrentMonth: boolean
  isToday: boolean
  isWeekend: boolean
}

const monthGrid = computed((): DayCell[][] => {
  const year = props.year
  const month = props.month

  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const daysInMonth = lastDay.getDate()

  // 周一=0, 周日=6
  let startWeekday = firstDay.getDay() - 1
  if (startWeekday < 0) startWeekday = 6

  const today = new Date()
  const todayStr = formatDate(today)

  const grid: DayCell[][] = []
  let currentRow: DayCell[] = []

  // 填充上月尾部
  const prevMonthLastDay = new Date(year, month, 0).getDate()
  for (let i = startWeekday - 1; i >= 0; i--) {
    const d = new Date(year, month - 1, prevMonthLastDay - i)
    currentRow.push(makeCell(d, false, todayStr))
  }

  // 本月
  for (let day = 1; day <= daysInMonth; day++) {
    if (currentRow.length === 7) {
      grid.push(currentRow)
      currentRow = []
    }
    const d = new Date(year, month, day)
    currentRow.push(makeCell(d, true, todayStr))
  }

  // 填充下月头部
  let nextDay = 1
  while (currentRow.length < 7) {
    const d = new Date(year, month + 1, nextDay)
    currentRow.push(makeCell(d, false, todayStr))
    nextDay++
  }
  if (currentRow.length > 0) {
    grid.push(currentRow)
  }

  return grid
})

// ==================== 周视图 ====================

const weekCells = computed((): DayCell[] => {
  const today = new Date()
  const todayStr = formatDate(today)

  // 获取当前周的周一
  let baseDate: Date
  if (props.currentWeekStart) {
    baseDate = props.currentWeekStart
  } else {
    baseDate = new Date(props.year, props.month, 1)
    const dow = baseDate.getDay()
    const diff = dow === 0 ? -6 : 1 - dow
    baseDate.setDate(baseDate.getDate() + diff)
  }

  const cells: DayCell[] = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(baseDate)
    d.setDate(d.getDate() + i)
    const weekday = d.getDay()
    cells.push({
      date: d,
      dateStr: formatDate(d),
      day: d.getDate(),
      weekday: weekday === 0 ? 6 : weekday - 1,
      isCurrentMonth: d.getMonth() === props.month,
      isToday: formatDate(d) === todayStr,
      isWeekend: weekday === 0 || weekday === 6,
    })
  }
  return cells
})

// ==================== 工具函数 ====================

function makeCell(date: Date, isCurrentMonth: boolean, todayStr: string): DayCell {
  const weekday = date.getDay()
  return {
    date,
    dateStr: formatDate(date),
    day: date.getDate(),
    weekday: weekday === 0 ? 6 : weekday - 1,
    isCurrentMonth,
    isToday: formatDate(date) === todayStr,
    isWeekend: weekday === 0 || weekday === 6,
  }
}

function formatDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}
</script>

<style scoped>
.calendar-grid {
  flex: 1;
  overflow: auto;
}

/* 星期头部 */
.weekday-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  background: #FAFBFC;
  border-bottom: 1px solid #E6EAF0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.weekday-cell {
  padding: 10px 0;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: #556173;
}

/* 月视图 */
.month-grid {
  display: flex;
  flex-direction: column;
}

.month-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  min-height: 120px;
  border-bottom: 1px solid #E6EAF0;
}

.day-cell {
  border-right: 1px solid #E6EAF0;
  padding: 4px;
  min-height: 120px;
  overflow: hidden;
  transition: background 0.15s ease;
}

.day-cell:last-child {
  border-right: none;
}

.day-cell:hover {
  background: #FAFBFC;
}

.day-cell.other-month {
  background: #F9FAFB;
}

.day-cell.other-month .day-number {
  color: #C0C4CC;
}

.day-cell.is-today {
  background: #F0F5FF;
}

.day-cell.is-weekend {
  background: #FAFAFA;
}

.day-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  padding: 0 2px;
}

.day-number {
  font-size: 13px;
  font-weight: 500;
  color: #1F2D3D;
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  border-radius: 50%;
}

.day-number.today {
  background: #0A63D8;
  color: #FFFFFF;
}

.add-btn {
  opacity: 0;
  transition: opacity 0.15s ease;
  width: 20px;
  height: 20px;
}

.day-cell:hover .add-btn {
  opacity: 1;
}

.shift-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.more-indicator {
  font-size: 11px;
  color: #0A63D8;
  text-align: center;
  padding: 2px 0;
  cursor: pointer;
  border-radius: 3px;
}

.more-indicator:hover {
  background: #ECF5FF;
}

/* 周视图 */
.week-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  min-height: 500px;
}

.week-day-col {
  border-right: 1px solid #E6EAF0;
  padding: 8px;
  min-width: 140px;
}

.week-day-col:last-child {
  border-right: none;
}

.week-day-col.is-today {
  background: #F0F5FF;
}

.week-day-col.is-weekend {
  background: #FAFAFA;
}

.week-day-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-bottom: 8px;
  border-bottom: 1px solid #E6EAF0;
  margin-bottom: 8px;
}

.weekday-name {
  font-size: 12px;
  color: #909399;
}

.week-day-header .day-number {
  font-size: 18px;
  font-weight: 600;
}

.week-day-header .add-btn {
  opacity: 0;
  transition: opacity 0.15s ease;
}

.week-day-col:hover .add-btn {
  opacity: 1;
}

.week-day-col .shift-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
