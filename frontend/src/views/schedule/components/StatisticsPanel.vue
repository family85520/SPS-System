<template>
  <div class="statistics-panel" v-loading="loading">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <span class="filter-label">统计周期</span>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        style="width: 200px"
        size="small"
      />
      <span class="filter-label" style="margin-left: 8px;">组织</span>
      <el-select v-model="filterOrgId" placeholder="全部组织" clearable class="neo-input" style="width: 160px">
        <el-option v-for="org in orgList" :key="org.id" :label="org.name" :value="org.id" />
      </el-select>
      <el-button class="btn-neo-primary" @click="loadStatistics">查询</el-button>
      <el-button v-if="authStore.hasPermission('schedule', 'export')" class="btn-neo-primary" @click="handleExport">
        <el-icon><Download /></el-icon>
        导出
      </el-button>
    </div>

    <!-- 汇总卡片 -->
    <div class="summary-grid" v-if="statisticsData">
      <!-- 参与人数 -->
      <div class="summary-card neo-card stat-card stat-card-blue">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><User /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">参与人数</span>
            <span class="stat-big-number">{{ statisticsData.summary.total_staff }}</span>
          </div>
        </div>
      </div>

      <!-- 总班次数 -->
      <div class="summary-card neo-card stat-card stat-card-green">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Connection /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">总班次数</span>
            <span class="stat-big-number">{{ statisticsData.summary.total_shifts }}</span>
          </div>
        </div>
      </div>

      <!-- 人均班次 -->
      <div class="summary-card neo-card stat-card stat-card-cyan">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">人均班次</span>
            <span class="stat-big-number">{{ statisticsData.summary.avg_shifts_per_person }}</span>
          </div>
        </div>
      </div>

      <!-- 人均工时 -->
      <div class="summary-card neo-card stat-card stat-card-orange">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Timer /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">人均工时</span>
            <span class="stat-big-number">{{ statisticsData.summary.avg_hours_per_person }}<span class="stat-unit">h</span></span>
          </div>
        </div>
      </div>

      <!-- 夜班总次数 -->
      <div class="summary-card neo-card stat-card stat-card-red">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Moon /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">夜班总次数</span>
            <span class="stat-big-number">{{ statisticsData.summary.total_night_shifts }}</span>
          </div>
        </div>
      </div>

      <!-- 节假日班次 -->
      <div class="summary-card neo-card stat-card stat-card-purple">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Sunny /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">节假日班次</span>
            <span class="stat-big-number">{{ statisticsData.summary.total_holiday_shifts || 0 }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 统计表格 -->
    <div class="table-area">
      <el-table
        v-if="statisticsData && statisticsData.items.length > 0"
        :data="statisticsData.items"
        stripe
        :default-sort="{ prop: 'weight_score', order: 'descending' }"
        :row-class-name="tableRowClassName"
        style="width: 100%"
      >
        <el-table-column label="排名" width="60" align="center">
          <template #default="{ $index }">
            <div :class="['rank-badge', $index < 3 ? `rank-${$index + 1}` : 'rank-other']">
              {{ $index + 1 }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="staff_name" label="姓名" width="80">
          <template #default="{ row }">
            <span class="td-name">{{ row.staff_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="employee_no" label="工号" width="80">
          <template #default="{ row }">
            <span class="td-no">{{ row.employee_no || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="org_name" label="所属组织" min-width="100">
          <template #default="{ row }">
            <span class="td-org">{{ row.org_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_shifts" label="班次数" sortable width="100" align="right">
          <template #default="{ row }">
            <span class="td-number">{{ row.total_shifts }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_hours" label="总工时" sortable width="100" align="right">
          <template #default="{ row }">
            <span class="td-number">{{ row.total_hours }}h</span>
          </template>
        </el-table-column>
        <el-table-column prop="night_shifts" label="夜班" sortable width="80" align="center">
          <template #default="{ row }">
            <span class="td-badge badge-night">{{ row.night_shifts }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="weekend_shifts" label="周末班" sortable width="90" align="center">
          <template #default="{ row }">
            <span class="td-badge badge-weekend">{{ row.weekend_shifts }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="leader_shifts" label="值班领导" sortable width="100" align="center">
          <template #default="{ row }">
            <span class="td-badge badge-leader">{{ row.leader_shifts }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="holiday_shifts" label="节假日" sortable width="90" align="center">
          <template #default="{ row }">
            <span class="td-badge badge-holiday">{{ row.holiday_shifts || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="weight_score" label="权重分" sortable width="160" align="right">
          <template #default="{ row }">
            <div class="weight-cell">
              <div class="weight-bar-bg">
                <div
                  class="weight-bar-fill"
                  :style="getWeightBarStyle(row.weight_score)"
                />
              </div>
              <span class="weight-value">{{ row.weight_score }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="!loading && statisticsData && statisticsData.items.length === 0"
        description="该时间段内暂无排班数据"
        :image-size="80"
      />
    </div>

    <!-- 导出统计报表弹窗 -->
    <ExportStatisticsDialog
      v-model:visible="exportDialogVisible"
      :start-date="dateRange[0] || ''"
      :end-date="dateRange[1] || ''"
      :org-id="filterOrgId"
      :org-list="orgList"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Download,
  User,
  Connection,
  TrendCharts,
  Timer,
  Moon,
  Sunny,
} from '@element-plus/icons-vue'
import api from '@/api/index'
import { useAuthStore } from '@/stores/auth'
import { getScheduleStatistics } from '@/api/schedule'
import type { ScheduleStatisticsResponse } from '@/api/schedule'
import ExportStatisticsDialog from './ExportStatisticsDialog.vue'

// ==================== 筛选状态 ====================

const now = new Date()
const y = now.getFullYear()
const m = now.getMonth()
const lastDay = new Date(y, m + 1, 0).getDate()
const dateRange = ref<string[]>([
  `${y}-${String(m + 1).padStart(2, '0')}-01`,
  `${y}-${String(m + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`,
])
const filterOrgId = ref<number | undefined>(undefined)
const exportDialogVisible = ref(false)

// ==================== 数据 ====================

const authStore = useAuthStore()
const loading = ref(false)
const statisticsData = ref<ScheduleStatisticsResponse | null>(null)
const orgList = ref<any[]>([])

const maxWeight = computed(() => {
  if (!statisticsData.value?.items?.length) return 1
  return Math.max(...statisticsData.value.items.map(i => i.weight_score))
})

// ==================== 加载 ====================

async function loadOrgs() {
  try {
    const res: any = await api.get('/options/organizations')
    orgList.value = Array.isArray(res) ? res : (res.data || [])
  } catch (e) {
    orgList.value = []
  }
}

async function loadStatistics() {
  if (!dateRange.value || dateRange.value.length < 2) {
    ElMessage.warning('请选择统计周期')
    return
  }
  loading.value = true
  try {
    const params: any = {
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
    }
    if (filterOrgId.value) params.org_id = filterOrgId.value
    statisticsData.value = await getScheduleStatistics(params)
  } catch (e) {
    // interceptor handles error
  } finally {
    loading.value = false
  }
}

// ==================== 工具函数 ====================

function tableRowClassName({ rowIndex }: { rowIndex: number }) {
  if (rowIndex === 0) return 'rank-highlight-1'
  if (rowIndex === 1) return 'rank-highlight-2'
  if (rowIndex === 2) return 'rank-highlight-3'
  return ''
}

function getWeightBarStyle(score: number) {
  const ratio = maxWeight.value > 0 ? score / maxWeight.value : 0
  const color = ratio > 0.8 ? '#3B82F6' : ratio > 0.6 ? '#06B6D4' : ratio > 0.4 ? '#10B981' : '#FFD93D'
  return { width: (ratio * 100) + '%', background: color }
}

function handleExport() {
  exportDialogVisible.value = true
}

// ==================== 初始化 ====================

onMounted(async () => {
  await loadOrgs()
  await loadStatistics()
})
</script>

<style scoped>
.statistics-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--neo-color-bg-card);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-default);
  overflow: hidden;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: var(--neo-border-thick) solid var(--neo-color-border);
  background: var(--neo-color-bg-primary);
  flex-wrap: wrap;
  box-shadow: inset 0 -3px 0px 0px rgba(0,0,0,0.05);
}

.filter-label {
  font-size: 13px;
  color: var(--neo-color-text-primary);
  font-weight: 700;
}

/* 汇总卡片 */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  padding: 20px;
}

.summary-card {
  overflow: visible;
}

/* 新增配色变体 — 补全全局 stat-card 缺少的 cyan/orange */
.stat-card-cyan .stat-accent-bar    { background: #06B6D4; }
.stat-card-cyan .stat-icon-wrap     { background: #CFFAFE; color: #0E7490; }
.stat-card-orange .stat-accent-bar  { background: #F59E0B; }
.stat-card-orange .stat-icon-wrap   { background: #FEF3C7; color: #B45309; }

/* 表格区域 */
.table-area {
  flex: 1;
  overflow: auto;
  padding: 0 20px 20px;
}

.td-name {
  font-weight: 700;
  color: var(--neo-color-text-primary);
}

.td-no {
  color: var(--neo-color-text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.td-org {
  color: #556173;
  font-weight: 600;
}

.td-number {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.td-badge {
  display: inline-block;
  padding: 3px 10px;
  border: 2px solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  font-size: 12px;
  font-weight: 700;
  box-shadow: 1px 1px 0px 0px rgba(0,0,0,0.1);
  transition: all 0.15s ease;
}

.td-badge:hover {
  box-shadow: var(--neo-shadow-active);
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs));
}

.badge-night { background: #DBEAFE; color: #1D4ED8; }
.badge-weekend { background: #F5F3FF; color: #6D28D9; }
.badge-leader { background: #FFF7ED; color: #C2410C; }
.badge-holiday { background: #F5F3FF; color: #6D28D9; }

/* 排名徽章 */
.rank-badge {
  width: 26px;
  height: 26px;
  line-height: 26px;
  text-align: center;
  border-radius: var(--neo-radius-md);
  font-size: 12px;
  font-weight: 900;
  display: inline-block;
  border: 2px solid var(--neo-color-border);
  box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.15);
  transition: all 0.15s ease;
}

.rank-badge:hover {
  box-shadow: var(--neo-shadow-md);
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs));
}

.rank-1 { background: #FFD93D; color: var(--neo-color-text-primary); }
.rank-2 { background: #E5E7EB; color: var(--neo-color-text-primary); }
.rank-3 { background: #F97316; color: var(--neo-color-bg-card); }
.rank-other { background: var(--neo-color-bg-primary); color: #556173; }

/* 权重条 */
.weight-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}

.weight-bar-bg {
  width: 80px;
  height: 10px;
  background: var(--neo-color-bg-primary);
  border: 2px solid var(--neo-color-border);
  border-radius: var(--neo-radius-sm);
  overflow: hidden;
  box-shadow: inset 1px 1px 0px 0px rgba(0,0,0,0.1);
}

.weight-bar-fill {
  height: 100%;
  transition: width 0.4s ease;
  border-radius: 1px;
}

.weight-value {
  font-weight: 900;
  font-size: 13px;
  min-width: 36px;
  text-align: right;
  color: var(--neo-color-text-primary);
}

/* 排名高亮行 */
:deep(.rank-highlight-1) { background: #FFFBEB !important; }
:deep(.rank-highlight-2) { background: #F9FAFB !important; }
:deep(.rank-highlight-3) { background: #FFF7ED !important; }

/* ============================================
   移动端适配
   ============================================ */

@media (max-width: 768px) {
  .statistics-panel {
    border-width: 2px;
    box-shadow: var(--neo-shadow-md);
  }

  .filter-bar {
    padding: 12px;
    gap: 8px;
  }

  .filter-bar .neo-input {
    width: 100% !important;
    flex: 1 1 calc(50% - 8px);
  }

  .summary-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    padding: 12px;
  }

  .summary-card {
    padding: 12px 6px;
  }

  .stat-big-number {
    font-size: 22px !important;
  }

  .stat-unit {
    font-size: 11px;
  }

  .stat-label-text {
    font-size: 11px;
  }

  .table-area {
    padding: 0 8px 12px;
  }

  .rank-badge {
    width: 20px;
    height: 20px;
    line-height: 20px;
    font-size: 10px;
  }

  .weight-bar-bg {
    width: 50px;
  }

  .weight-value {
    font-size: 11px;
    min-width: 28px;
  }
}

@media (max-width: 480px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filter-bar .neo-input {
    flex: 1 1 100%;
  }
}
</style>
