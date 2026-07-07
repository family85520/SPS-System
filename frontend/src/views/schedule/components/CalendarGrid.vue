<template>
  <div class="calendar-grid">
    <!-- 月视图 -->
    <template v-if="viewMode === 'month'">
      <!-- 星期头部 + 日期网格 — 同一容器确保列宽一致 -->
      <div class="calendar-table">
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
                  @staffDrop="(staffId: number, fromSid: number, toSid: number) => emit('staffDrop', staffId, fromSid, toSid)"
                  @shiftSwap="(fromSid: number, toSid: number) => emit('shiftSwap', fromSid, toSid)"
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
              @staffDrop="(staffId: number, fromSid: number, toSid: number) => emit('staffDrop', staffId, fromSid, toSid)"
              @shiftSwap="(fromSid: number, toSid: number) => emit('shiftSwap', fromSid, toSid)"
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

const emit = defineEmits<{
  (e: 'clickShift', shift: CalendarShift): void
  (e: 'addSchedule', dateStr: string): void
  (e: 'staffDrop', staffId: number, fromScheduleId: number, toScheduleId: number): void
  (e: 'shiftSwap', fromScheduleId: number, toScheduleId: number): void
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

  let startWeekday = firstDay.getDay() - 1
  if (startWeekday < 0) startWeekday = 6

  const today = new Date()
  const todayStr = formatDate(today)

  const grid: DayCell[][] = []
  let currentRow: DayCell[] = []

  const prevMonthLastDay = new Date(year, month, 0).getDate()
  for (let i = startWeekday - 1; i >= 0; i--) {
    const d = new Date(year, month - 1, prevMonthLastDay - i)
    currentRow.push(makeCell(d, false, todayStr))
  }

  for (let day = 1; day <= daysInMonth; day++) {
    if (currentRow.length === 7) {
      grid.push(currentRow)
      currentRow = []
    }
    const d = new Date(year, month, day)
    currentRow.push(makeCell(d, true, todayStr))
  }

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

/* 星期头部 + 日期网格 — 用同一个 grid 容器确保列宽一致 */
.calendar-table {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  min-width: 768px;
}

/* 星期头部 */
.weekday-header {
  display: contents;
}

.weekday-cell {
  padding: 10px 0;
  text-align: center;
  font-size: 14px;
  font-weight: 900;
  color: #FFFFFF;
  background: #000000;
  border-right: 3px solid #333333;
  border-bottom: 3px solid #000000;
  text-transform: uppercase;
  letter-spacing: 1px;
  position: sticky;
  top: 0;
  z-index: 10;
}
.weekday-cell:last-child {
  border-right: none;
}

/* 日期网格 */
.month-grid {
  display: contents;
}

.month-row {
  display: contents;
}

.day-cell {
  border-right: 3px solid #000000;
  border-bottom: 3px solid #000000;
  padding: 6px;
  min-height: 120px;
  overflow: visible;
  transition: all 0.1s ease;
  background: #FFFFFF;
  cursor: pointer;
  position: relative;
}

.day-cell:last-child {
  border-right: none;
}

.day-cell:hover {
  background: #FFD93D;
}

.day-cell.other-month {
  background: #F5F5F0;
}

.day-cell.other-month .day-number {
  color: #BBBBBB;
}

/* 原型：.calendar-cell.today → border-neo-accent border-4 */
.day-cell.is-today {
  border: 4px solid #FF6B6B;
  background: #FFFFFF;
}

.day-cell.is-weekend {
  background: #FFFBF0;
}

/* 日期头部 — 原型：font-bold text-lg */
.day-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  padding: 0 2px;
}

/* 日期数字 — 原型：font-bold text-lg */
.day-number {
  font-size: 18px;
  font-weight: 900;
  color: #000000;
  width: 28px;
  height: 28px;
  line-height: 28px;
  text-align: center;
  border-radius: 2px;
}

/* 原型：.calendar-cell.today 用红色边框标记，不需要额外背景 */
.day-number.today {
  background: #FF6B6B;
  color: #FFFFFF;
  border: 2px solid #000000;
  box-shadow: 2px 2px 0px 0px #000000;
}

/* 添加按钮 — 原型风格 */
.add-btn {
  opacity: 0;
  transition: opacity 0.1s ease;
  width: 22px;
  height: 22px;
  background: #FFD93D !important;
  border-color: #000000 !important;
  border-radius: 2px !important;
  box-shadow: 2px 2px 0px 0px #000000 !important;
}
.add-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0px 0px #000000 !important;
}

.day-cell:hover .add-btn {
  opacity: 1;
}

/* 班次列表 */
.shift-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

/* 更多指示器 — 原型风格 */
.more-indicator {
  font-size: 11px;
  font-weight: 700;
  color: #000000;
  text-align: center;
  padding: 2px 4px;
  cursor: pointer;
  border-radius: 2px;
  border: 2px solid #000000;
  background: #FFD93D;
  box-shadow: 1px 1px 0px 0px #000000;
  transition: all 0.1s ease;
}

.more-indicator:hover {
  box-shadow: 2px 2px 0px 0px #000000;
  transform: translate(-1px, -1px);
}

/* ========== 周视图 ========== */
.week-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  min-height: 450px;
}

.week-day-col {
  border-right: 3px solid #000000;
  padding: 8px;
  min-width: 130px;
  background: #FFFFFF;
  transition: all 0.1s ease;
  cursor: pointer;
}

.week-day-col:last-child {
  border-right: none;
}

.week-day-col:hover {
  background: #FFD93D;
}

.week-day-col.is-today {
  border: 3px solid #FF6B6B;
}

.week-day-col.is-weekend {
  background: #FFFBF0;
}

.week-day-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-bottom: 8px;
  border-bottom: 3px solid #000000;
  margin-bottom: 8px;
}

.weekday-name {
  font-size: 12px;
  font-weight: 900;
  color: #000000;
  text-transform: uppercase;
}

.week-day-header .day-number {
  font-size: 22px;
  font-weight: 900;
}

.week-day-header .add-btn {
  opacity: 0;
  transition: opacity 0.1s ease;
}

.week-day-col:hover .add-btn {
  opacity: 1;
}

.week-day-col .shift-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 最小宽度 — 保证 7 列不挤碎 */
.calendar-table {
  min-width: 768px;
}

/* ============================================
   移动端适配 — 卡片式布局
   ============================================ */

@media (max-width: 768px) {
  /* 取消最小宽度，允许网格缩到屏幕宽 */
  .calendar-table {
    min-width: unset;
  }

  /* 星期头部 — 改为单列卡片 */
  .weekday-header {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 8px 6px;
    background: #000000;
    border-bottom: 3px solid #000000;
    position: static;
    z-index: auto;
  }

  .weekday-cell {
    font-size: 11px;
    padding: 6px 0;
    border-right: none;
    border-bottom: 3px solid #000000;
    flex: 1 1 calc(14.28% - 4px);
    min-width: 0;
  }

  /* 日期网格 — 单列卡片 */
  .month-grid {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .month-row {
    display: contents;
  }

  .day-cell {
    border-right: 3px solid #000000;
    border-left: 3px solid #000000;
    border-bottom: 3px solid #000000;
    border-radius: 0;
    padding: 8px 10px;
    min-height: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .day-cell:last-child {
    border-right: 3px solid #000000;
  }

  .day-cell.is-today {
    border: 3px solid #FF6B6B;
    background: #FFFDF5;
  }

  /* 日期头部 — 水平排列 */
  .day-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0;
    padding: 0;
  }

  /* 日期数字 */
  .day-number {
    font-size: 16px;
    width: auto;
    height: auto;
    line-height: 1;
    display: inline;
  }

  .day-number.today {
    background: #FF6B6B;
    color: #FFFFFF;
    border: 2px solid #000000;
    box-shadow: 2px 2px 0px 0px #000000;
    padding: 2px 6px;
    border-radius: 2px;
    display: inline;
    width: auto;
    height: auto;
    line-height: 1;
  }

  /* 添加按钮 */
  .add-btn {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
  }

  /* 班次列表 */
  .shift-list {
    gap: 3px;
  }

  /* 更多指示器 */
  .more-indicator {
    font-size: 10px;
    padding: 2px 4px;
  }

  /* 周视图 — 单列卡片 */
  .week-grid {
    display: flex;
    flex-direction: column;
    gap: 0;
    min-height: unset;
  }

  .week-day-col {
    border-right: 3px solid #000000;
    border-left: 3px solid #000000;
    border-bottom: 3px solid #000000;
    border-radius: 0;
    padding: 8px 10px;
    min-width: unset;
    min-height: auto;
  }

  .week-day-col:last-child {
    border-right: 3px solid #000000;
  }

  .week-day-col.is-today {
    border: 3px solid #FF6B6B;
    background: #FFFDF5;
  }

  .week-day-header {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 6px;
    padding-bottom: 6px;
    border-bottom: 3px solid #000000;
    margin-bottom: 6px;
  }

  .weekday-name {
    font-size: 12px;
    font-weight: 900;
    color: #000000;
  }

  .week-day-header .day-number {
    font-size: 18px;
    font-weight: 900;
    width: auto;
    height: auto;
    line-height: 1;
  }

  .week-day-header .add-btn {
    margin-left: auto;
  }
}

/* 极小屏幕进一步缩小 */
@media (max-width: 480px) {
  .weekday-cell {
    font-size: 10px;
    padding: 4px 0;
  }

  .day-cell {
    padding: 6px 8px;
  }

  .day-number {
    font-size: 14px;
  }

  .day-number.today {
    font-size: 14px;
    padding: 1px 4px;
  }

  .week-day-col {
    padding: 6px 8px;
  }

  .week-day-header .day-number {
    font-size: 16px;
  }
}
</style>
