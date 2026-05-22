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
      <el-select v-model="filterOrgId" placeholder="全部组织" clearable style="width: 160px">
        <el-option v-for="org in orgList" :key="org.id" :label="org.name" :value="org.id" />
      </el-select>
      <el-button type="primary" @click="loadStatistics">查询</el-button>
      <el-button v-if="authStore.hasPermission('export', 'read')" @click="handleExport">
        <el-icon><Download /></el-icon>
        导出
      </el-button>
    </div>

    <!-- 汇总卡片 -->
    <div class="summary-grid" v-if="statisticsData">
      <div class="summary-card">
        <div class="summary-value" style="color: #0A63D8;">
          {{ statisticsData.summary.total_staff }}<span class="summary-unit">人</span>
        </div>
        <div class="summary-label">参与人数</div>
      </div>
      <div class="summary-card">
        <div class="summary-value" style="color: #28A745;">
          {{ statisticsData.summary.total_shifts }}<span class="summary-unit">班</span>
        </div>
        <div class="summary-label">总班次数</div>
      </div>
      <div class="summary-card">
        <div class="summary-value" style="color: #17A2B8;">
          {{ statisticsData.summary.avg_shifts_per_person }}<span class="summary-unit">班</span>
        </div>
        <div class="summary-label">人均班次</div>
      </div>
      <div class="summary-card">
        <div class="summary-value" style="color: #FFC107;">
          {{ statisticsData.summary.avg_hours_per_person }}<span class="summary-unit">h</span>
        </div>
        <div class="summary-label">人均工时</div>
      </div>
      <div class="summary-card">
        <div class="summary-value" style="color: #DC3545;">
          {{ statisticsData.summary.total_night_shifts }}<span class="summary-unit">班</span>
        </div>
        <div class="summary-label">夜班总次数</div>
      </div>
      <div class="summary-card">
        <div class="summary-value" style="color: #9C27B0;">
          {{ statisticsData.summary.total_holiday_shifts || 0 }}<span class="summary-unit">班</span>
        </div>
        <div class="summary-label">节假日班次</div>
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
import { Download } from '@element-plus/icons-vue'
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
  const color = ratio > 0.8 ? '#0A63D8' : ratio > 0.6 ? '#17A2B8' : ratio > 0.4 ? '#28A745' : '#FFC107'
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
  background: #FFFFFF;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(31, 45, 61, 0.06);
  overflow: hidden;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #E6EAF0;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 13px;
  color: #556173;
  font-weight: 500;
}

/* 汇总卡片 */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  padding: 20px;
}

.summary-card {
  text-align: center;
  padding: 16px 8px;
  background: #F5F7FA;
  border-radius: 6px;
  position: relative;
  overflow: hidden;
}

.summary-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.summary-card:nth-child(1)::before { background: #0A63D8; }
.summary-card:nth-child(2)::before { background: #28A745; }
.summary-card:nth-child(3)::before { background: #17A2B8; }
.summary-card:nth-child(4)::before { background: #FFC107; }
.summary-card:nth-child(5)::before { background: #DC3545; }
.summary-card:nth-child(6)::before { background: #9C27B0; }

.summary-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}

.summary-unit {
  font-size: 13px;
  font-weight: 400;
  color: #909399;
  margin-left: 2px;
}

.summary-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

/* 表格区域 */
.table-area {
  flex: 1;
  overflow: auto;
  padding: 0 20px 20px;
}

.td-name {
  font-weight: 600;
  color: #1F2D3D;
}

.td-no {
  color: #909399;
  font-size: 12px;
}

.td-org {
  color: #556173;
}

.td-number {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.td-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 500;
}

.badge-night { background: #E3F2FD; color: #1565C0; }
.badge-weekend { background: #F3E5F5; color: #7B1FA2; }
.badge-leader { background: #FFF3E0; color: #E65100; }
.badge-holiday { background: #F3E5F5; color: #7B1FA2; }

/* 排名徽章 */
.rank-badge {
  width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  display: inline-block;
}

.rank-1 { background: #FFC107; color: #fff; }
.rank-2 { background: #C0C4CC; color: #fff; }
.rank-3 { background: #CD7F32; color: #fff; }
.rank-other { background: #E6EAF0; color: #556173; }

/* 权重条 */
.weight-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}

.weight-bar-bg {
  width: 80px;
  height: 6px;
  background: #EBEEF5;
  border-radius: 3px;
  overflow: hidden;
}

.weight-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.weight-value {
  font-weight: 700;
  font-size: 13px;
  min-width: 36px;
  text-align: right;
  color: #1F2D3D;
}

/* 排名高亮行 */
:deep(.rank-highlight-1) { background: #FFFDE7 !important; }
:deep(.rank-highlight-2) { background: #F5F5F5 !important; }
:deep(.rank-highlight-3) { background: #FFF8E1 !important; }
</style>
