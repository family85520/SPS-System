<template>
  <div class="schedule-page">
    <!-- 工具栏（日历视图专用） -->
    <div v-if="activeTab === 'calendar'" class="calendar-toolbar">
      <!-- 左侧：月份导航 -->
      <div class="toolbar-left">
        <el-button-group class="btn-neo-group">
          <el-button @click="navigateMonth(-1)" class="btn-neo-sm">
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <el-button @click="goToday" class="btn-neo-sm btn-neo-accent">今天</el-button>
          <el-button @click="navigateMonth(1)" class="btn-neo-sm">
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </el-button-group>
        <span class="current-month-label">{{ currentYear }}年{{ currentMonth + 1 }}月</span>
      </div>

      <!-- 中间：筛选卡片 -->
      <div class="toolbar-center">
        <div class="filter-card-group">
          <span class="filter-card-label">组织</span>
          <el-select
            v-model="filterOrgId"
            placeholder="全部组织"
            clearable
            class="toolbar-filter"
            @change="loadCalendar"
          >
            <el-option
              v-for="org in orgList"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
        </div>

        <div class="filter-card-group">
          <span class="filter-card-label">状态</span>
          <el-select
            v-model="filterStatus"
            placeholder="全部状态"
            clearable
            class="toolbar-filter"
            @change="loadCalendar"
          >
            <el-option label="草稿" :value="0" />
            <el-option label="已发布" :value="1" />
            <el-option label="已撤回" :value="2" />
            <el-option label="待审核" :value="3" />
          </el-select>
        </div>

        <div class="filter-card-group">
          <span class="filter-card-label">视图</span>
          <el-radio-group v-model="viewMode" @change="loadCalendar" class="toolbar-view-toggle">
            <el-radio-button value="month">月视图</el-radio-button>
            <el-radio-button value="week">周视图</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 右侧：操作按钮 -->
      <div class="toolbar-right">
        <!-- 主要操作（始终可见） -->
        <el-button v-if="authStore.hasPermission('schedule', 'create')" class="btn-neo-primary btn-neo-sm" @click="handleAutoSchedule">
          <el-icon><MagicStick /></el-icon>
          <span class="btn-text">自动排班</span>
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'create')" class="btn-neo-success btn-neo-sm" @click="handleAddSchedule('')">
          <el-icon><Plus /></el-icon>
          <span class="btn-text">添加排班</span>
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'read')" class="btn-neo-warning btn-neo-sm" @click="handleDownloadImportTemplate">
          <el-icon><Download /></el-icon>
          <span class="btn-text">下载模板</span>
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'create')" class="btn-neo-warning btn-neo-sm" @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>
          <span class="btn-text">导入</span>
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'create')" class="btn-neo-info btn-neo-sm" @click="handleValidate">
          <el-icon><CircleCheck /></el-icon>
          <span class="btn-text">校验</span>
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'publish')" class="btn-neo-primary btn-neo-sm" @click="handlePublish">
          <el-icon><Upload /></el-icon>
          <span class="btn-text">发布</span>
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'publish')" class="btn-neo-warning btn-neo-sm" @click="handleRecall">
          <el-icon><RefreshLeft /></el-icon>
          <span class="btn-text">撤回</span>
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'delete')" class="btn-neo-danger btn-neo-sm" @click="handleDeleteDrafts">
          <el-icon><Delete /></el-icon>
          <span class="btn-text">清除草稿</span>
        </el-button>

        <!-- 次要操作（折叠进更多菜单） -->
        <el-popover
          v-if="authStore.hasPermission('schedule', 'approve') || authStore.hasPermission('export', 'read')"
          placement="bottom-end"
          :width="180"
          trigger="click"
          popper-class="toolbar-more-popover"
        >
          <template #reference>
            <el-button class="btn-neo-ghost btn-neo-sm">
              <el-icon><More /></el-icon>
            </el-button>
          </template>
          <div class="more-menu">
            <el-button
              v-if="authStore.hasPermission('schedule', 'approve')"
              class="btn-neo-sm btn-more-item btn-neo-success"
              @click="handleApprove"
            >
              <el-icon><Select /></el-icon>
              <span class="btn-text">审核通过</span>
            </el-button>
            <el-button
              v-if="authStore.hasPermission('schedule', 'approve')"
              class="btn-neo-sm btn-more-item btn-neo-danger"
              @click="handleReject"
            >
              <el-icon><CloseBold /></el-icon>
              <span class="btn-text">审核拒绝</span>
            </el-button>
            <el-button
              v-if="authStore.hasPermission('export', 'read')"
              class="btn-neo-sm btn-more-item btn-neo-info"
              @click="handleExport"
            >
              <el-icon><Download /></el-icon>
              <span class="btn-text">导出</span>
            </el-button>
          </div>
        </el-popover>
      </div>
    </div>

    <!-- Tab 栏 -->
    <div class="tab-bar">
      <div
        :class="['tab-item', { active: activeTab === 'calendar' }]"
        @click="activeTab = 'calendar'"
      >
        日历视图
      </div>
      <div
        v-if="authStore.hasPermission('schedule', 'read')"
        :class="['tab-item', { active: activeTab === 'statistics' }]"
        @click="activeTab = 'statistics'"
      >
        统计报表
      </div>
    </div>

    <!-- 日历主体 -->
    <div v-if="activeTab === 'calendar'" class="calendar-body" v-loading="loading">
      <CalendarGrid
        :year="currentYear"
        :month="currentMonth"
        :view-mode="viewMode"
        :calendar-data="calendarData"
        @click-shift="handleClickShift"
        @add-schedule="handleAddSchedule"
        @staff-drop="handleStaffDrop"
        @shift-swap="handleShiftSwap"
      />

      <!-- 自动排班对话框 -->
      <el-dialog v-model="autoScheduleDialogVisible" title="自动排班" width="560px" class="neo-dialog">
        <div class="alert-card" style="margin-bottom: 20px;">
          <span class="alert-card__icon">⚠</span>
          <span class="alert-card__content">系统将根据预设的排班规则自动生成本月所有员工的排班计划，是否确认执行？</span>
        </div>
        <el-form label-width="110px" label-position="right">
          <el-form-item label="排班周期">
            <el-date-picker
              v-model="autoScheduleForm.start_date"
              type="date"
              placeholder="开始日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 45%"
            />
            <span class="form-tip" style="margin: 0 8px; color: #666;">至</span>
            <el-date-picker
              v-model="autoScheduleForm.end_date"
              type="date"
              placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 45%"
            />
          </el-form-item>
          <el-form-item label="排班范围" required>
            <el-select v-model="autoScheduleForm.org_id" placeholder="选择组织" class="neo-input" @change="handleAutoOrgChange">
              <el-option v-for="org in orgList" :key="org.id" :label="org.name" :value="org.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="班次模板" required>
            <el-checkbox-group v-model="autoScheduleForm.shift_template_ids">
              <el-checkbox
                v-for="t in shiftTemplateList"
                :key="t.id"
                :value="t.id"
              >
                {{ t.name }}（{{ t.start_time }}-{{ t.end_time }}）
              </el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="排班人员" required>
            <el-select
              v-model="autoScheduleForm.staff_ids"
              multiple
              filterable
              placeholder="选择参与排班的人员"
              class="neo-input"
            >
              <el-option
                v-for="s in allStaffList"
                :key="s.id"
                :label="s.name"
                :value="s.id"
              >
                <span style="float: left">{{ s.name }}</span>
                <span style="float: right; color: #909399; font-size: 12px">{{ s.employee_no }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button class="btn-neo-ghost" @click="autoScheduleDialogVisible = false">取消</el-button>
          <el-button :loading="autoScheduleLoading" class="btn-neo-primary" @click="handleAutoGenerate">
            一键生成
          </el-button>
        </template>
      </el-dialog>

      <!-- 校验报告 -->
      <el-dialog v-model="validationDialogVisible" title="约束校验报告" width="680px" class="neo-dialog">
        <template v-if="validationResult">
          <div style="display: flex; gap: 20px; margin-bottom: 20px;">
            <el-statistic title="通过" :value="validationResult.passed_count">
              <template #suffix><span style="color: #10B981">项</span></template>
            </el-statistic>
            <el-statistic title="警告" :value="validationResult.warning_count">
              <template #suffix><span style="color: #FFD93D">项</span></template>
            </el-statistic>
            <el-statistic title="失败" :value="validationResult.failed_count">
              <template #suffix><span style="color: #EF4444">项</span></template>
            </el-statistic>
          </div>

          <el-tabs class="neo-tabs">
            <el-tab-pane :label="`已通过（${validationResult.passed_count}）`">
              <div v-for="(item, idx) in validationResult.passed" :key="idx" class="font-weight-medium" style="padding: 6px 0; font-size: 13px;">
                <span style="color: #10B981;">✓</span> {{ item.rule_name }}
              </div>
            </el-tab-pane>
            <el-tab-pane :label="`警告（${validationResult.warning_count}）`">
              <div v-for="(item, idx) in validationResult.warnings" :key="idx" class="violation-item warning">
                <div class="violation-title">⚠ {{ item.rule_name }}</div>
                <div class="violation-msg">{{ item.message }}</div>
                <div class="violation-meta">日期：{{ item.date }} | 人员ID：{{ item.staff_id }}</div>
              </div>
            </el-tab-pane>
            <el-tab-pane :label="`失败（${validationResult.failed_count}）`">
              <div v-for="(item, idx) in validationResult.failed" :key="idx" class="violation-item error">
                <div class="violation-title">✕ {{ item.rule_name }}</div>
                <div class="violation-msg">{{ item.message }}</div>
                <div class="violation-meta">日期：{{ item.date }} | 人员ID：{{ item.staff_id }}</div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>
        <template #footer>
          <el-button class="btn-neo-ghost" @click="validationDialogVisible = false">关闭</el-button>
          <el-button
            v-if="authStore.hasPermission('schedule', 'publish')"
            type="primary"
            :disabled="!validationResult || validationResult.failed_count > 0"
            class="btn-neo-primary"
            @click="handlePublishFromValidation"
          >
            确认发布
          </el-button>
        </template>
      </el-dialog>

      <!-- 班次说明 -->
      <div class="shift-legend">
        <span class="legend-title">班次说明：</span>
        <div v-for="t in shiftTemplateList" :key="t.id" class="legend-item">
          <span class="legend-dot" :style="{ background: t.color }"></span>
          <span class="legend-text">{{ t.name }} ({{ t.start_time }}-{{ t.end_time }})</span>
        </div>
      </div>
    </div>

    <!-- 统计报表 -->
    <StatisticsPanel v-if="activeTab === 'statistics'" />

    <!-- 详情抽屉 -->
    <ShiftDetailDrawer
      v-model:visible="drawerVisible"
      :schedule="currentSchedule"
      :calendar-shift="currentCalendarShift"
      @refresh="handleRefresh"
    />

    <!-- 导出弹窗 -->
    <ExportDialog
      v-model:visible="exportDialogVisible"
      v-model:loading="exportLoading"
      :start-date="currentMonthRange.start"
      :end-date="currentMonthRange.end"
      :org-id="filterOrgId"
      :org-list="orgList"
    />

    <!-- 新建排班对话框 -->
    <el-dialog v-model="createDialogVisible" title="新建排班" width="460px" class="neo-dialog">
      <el-form label-width="90px" label-position="right">
        <el-form-item label="日期">
          <el-date-picker
            v-model="createForm.date"
            type="date"
            placeholder="选择排班日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="班次模板" required>
          <el-select v-model="createForm.shift_id" placeholder="选择班次模板" class="neo-input">
            <el-option
              v-for="t in shiftTemplateList"
              :key="t.id"
              :label="t.name"
              :value="t.id"
            >
              <span style="float: left">{{ t.name }}</span>
              <span style="float: right; color: #909399; font-size: 12px">
                {{ t.start_time }}-{{ t.end_time }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="组织" required>
          <el-select v-model="createForm.org_id" placeholder="选择组织" class="neo-input">
            <el-option
              v-for="org in orgList"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button class="btn-neo-ghost" @click="createDialogVisible = false">取消</el-button>
        <el-button :loading="creating" class="btn-neo-primary" @click="handleCreateSubmit">创建</el-button>
      </template>
    </el-dialog>

    <!-- 导入排班弹窗 — 拖拽上传 -->
    <el-dialog v-model="showImportDialog" title="导入排班" width="560px" class="neo-dialog" :close-on-click-modal="false">
      <div class="drag-upload-zone" @click="triggerImportFile">
        <i class="fas fa-cloud-upload-alt drag-upload-zone__icon"></i>
        <span class="drag-upload-zone__title">拖拽 .xlsx 文件到此处，或点击选择文件</span>
        <span class="drag-upload-zone__hint">支持 Excel 2007+ (.xlsx) 格式</span>
      </div>
      <input ref="importFileInput" type="file" accept=".xlsx" style="display:none" @change="handleImportFileChange" />
      <div v-if="importFileName" class="progress-bar__info" style="margin-top:12px;">
        <span class="progress-bar__filename">已选择：{{ importFileName }}</span>
        <span class="progress-bar__status" v-if="scheduleImporting">导入中...</span>
      </div>
      <template #footer>
        <el-button class="btn-neo-ghost" @click="showImportDialog = false">取消</el-button>
        <el-button :loading="scheduleImporting" class="btn-neo-primary" @click="doImportFile" :disabled="!importFileForImport">
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useConfirm } from '@/composables/useConfirm'
import {
  ArrowLeft,
  ArrowRight,
  Plus,
  Download,
  Upload,
  RefreshLeft,
  MagicStick,
  CircleCheck,
  Select,
  CloseBold,
  Delete,
  More,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/index'
import {
  getScheduleCalendar,
  getSchedule,
  createSchedule,
  publishSchedules,
  recallSchedules,
  recallSchedulesByMonth,
  approveSchedules,
  rejectSchedules,
  downloadScheduleImportTemplate,
  importScheduleTemplate,
  type CalendarDate,
  type CalendarShift,
  type Schedule,
} from '@/api/schedule'
import CalendarGrid from './components/CalendarGrid.vue'
import ShiftDetailDrawer from './components/ShiftDetailDrawer.vue'
import StatisticsPanel from './components/StatisticsPanel.vue'
import ExportDialog from './components/ExportDialog.vue'

// ==================== 日历状态 ====================

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const activeTab = ref<'calendar' | 'statistics'>('calendar')
const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth())
const viewMode = ref<'month' | 'week'>('month')
const { confirm } = useConfirm()
const calendarData = ref<CalendarDate[]>([])

// ==================== 筛选 ====================

const filterOrgId = ref<number | undefined>(undefined)
const filterStatus = ref<number | undefined>(undefined)

// ==================== 组织 + 班次模板 ====================

const orgList = ref<any[]>([])
const shiftTemplateList = ref<any[]>([])

async function loadOrgs() {
  try {
    const res: any = await api.get('/options/organizations')
    orgList.value = Array.isArray(res) ? res : (res.data || [])
  } catch (e) {
    orgList.value = []
  }
}

async function loadShiftTemplates() {
  try {
    const res: any = await api.get('/shift-templates/options')
    shiftTemplateList.value = Array.isArray(res) ? res : (res.data || [])
  } catch (e) {
    shiftTemplateList.value = []
  }
}

// ==================== 加载日历数据 ====================

function getDateRange(): { start: string; end: string } {
  const y = currentYear.value
  const m = currentMonth.value

  if (viewMode.value === 'week') {
    const firstDay = new Date(y, m, 1)
    const dow = firstDay.getDay()
    const diff = dow === 0 ? -6 : 1 - dow
    const monday = new Date(firstDay)
    monday.setDate(monday.getDate() + diff)

    const sunday = new Date(monday)
    sunday.setDate(sunday.getDate() + 6)

    return {
      start: formatDateStr(monday),
      end: formatDateStr(sunday),
    }
  }

  const firstDay = new Date(y, m, 1)
  const lastDay = new Date(y, m + 1, 0)

  const fDow = firstDay.getDay()
  const fDiff = fDow === 0 ? -6 : 1 - fDow
  const gridStart = new Date(firstDay)
  gridStart.setDate(gridStart.getDate() + fDiff)

  const lDow = lastDay.getDay()
  const lDiff = lDow === 0 ? 0 : 7 - lDow
  const gridEnd = new Date(lastDay)
  gridEnd.setDate(gridEnd.getDate() + lDiff)

  return {
    start: formatDateStr(gridStart),
    end: formatDateStr(gridEnd),
  }
}

async function loadCalendar() {
  loading.value = true
  try {
    const range = getDateRange()
    const params: any = {
      start_date: range.start,
      end_date: range.end,
    }
    if (filterOrgId.value) params.org_id = filterOrgId.value
    if (filterStatus.value !== undefined) params.status = filterStatus.value

    const res = await getScheduleCalendar(params)
    calendarData.value = res.dates || []
  } catch (e) {
    // interceptor handles error
  } finally {
    loading.value = false
  }
}

// ==================== 导航 ====================

function navigateMonth(delta: number) {
  const d = new Date(currentYear.value, currentMonth.value + delta, 1)
  currentYear.value = d.getFullYear()
  currentMonth.value = d.getMonth()
  loadCalendar()
}

function goToday() {
  const d = new Date()
  currentYear.value = d.getFullYear()
  currentMonth.value = d.getMonth()
  loadCalendar()
}

// ==================== 点击班次 → 打开抽屉 ====================

const drawerVisible = ref(false)
const currentSchedule = ref<Schedule | null>(null)
const currentCalendarShift = ref<CalendarShift | null>(null)

async function handleClickShift(shift: CalendarShift) {
  currentCalendarShift.value = shift
  try {
    const detail = await getSchedule(shift.schedule_id)
    currentSchedule.value = detail
    drawerVisible.value = true
  } catch (e) {
    // interceptor handles error
  }
}

async function handleShiftSwap(fromScheduleId: number, toScheduleId: number) {
  if (!fromScheduleId || fromScheduleId === toScheduleId) return
  try {
    await api.post(`/schedules/${fromScheduleId}/swap-staff/${toScheduleId}`)
    ElMessage.success('班次人员已互换')
    await handleRefresh()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.error('互换失败：' + (detail || (e?.message || '未知错误')))
  }
}

async function handleStaffDrop(staffId: number, fromScheduleId: number, toScheduleId: number) {
  if (!fromScheduleId || fromScheduleId === toScheduleId) return

  try {
    await api.post(`/schedules/${fromScheduleId}/remove-staff`, { staff_id: staffId })
    await api.post(`/schedules/${toScheduleId}/assign-staff`, { staff_id: staffId, role_type: 'member' })
    ElMessage.success('人员已调整')
    await handleRefresh()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.error('调整失败：' + (detail || (e?.message || '未知错误')))
  }
}

async function handleRefresh() {
  await loadCalendar()
  if (drawerVisible.value && currentSchedule.value) {
    try {
      const detail = await getSchedule(currentSchedule.value.id)
      currentSchedule.value = detail
    } catch (e) {
      drawerVisible.value = false
      currentSchedule.value = null
    }
  } else {
    currentSchedule.value = null
    currentCalendarShift.value = null
  }
}

// ==================== 新建排班 ====================

const createDialogVisible = ref(false)
const creating = ref(false)
const createForm = reactive({
  date: '',
  shift_id: null as number | null,
  org_id: null as number | null,
})

function handleAddSchedule(dateStr: string) {
  createForm.date = dateStr || ''
  createForm.shift_id = null
  createForm.org_id = filterOrgId.value || null
  createDialogVisible.value = true
}

async function handleCreateSubmit() {
  if (!createForm.date) {
    ElMessage.warning('请选择排班日期')
    return
  }
  if (!createForm.shift_id || !createForm.org_id) {
    ElMessage.warning('请选择班次模板和组织')
    return
  }
  creating.value = true
  try {
    await createSchedule({
      date: createForm.date,
      shift_id: createForm.shift_id,
      org_id: createForm.org_id,
      source: 'manual',
    })
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    await loadCalendar()
  } catch (e) {
    // interceptor handles error
  } finally {
    creating.value = false
  }
}

// ==================== 自动排班 ====================

const autoScheduleDialogVisible = ref(false)
const autoScheduleForm = reactive({
  start_date: '',
  end_date: '',
  org_id: null as number | null,
  shift_template_ids: [] as number[],
  staff_ids: [] as number[],
})
const autoScheduleLoading = ref(false)
const allStaffList = ref<any[]>([])

async function loadAllStaff() {
  try {
    const params: any = {}
    if (autoScheduleForm.org_id) params.org_id = autoScheduleForm.org_id
    const res: any = await api.get('/staffs/options', { params })
    let list = Array.isArray(res) ? res : (res.data || res.items || [])

    const excludeIds = new Set<number>()
    const selectedIds = autoScheduleForm.shift_template_ids
    for (const t of shiftTemplateList.value) {
      if (!selectedIds.includes(t.id)) continue
      if (t.special_enabled && t.special_pool) {
        for (const sid of t.special_pool) excludeIds.add(sid)
      }
      if (t.leader_enabled && t.leader_pool) {
        for (const sid of t.leader_pool) excludeIds.add(sid)
      }
    }

    if (excludeIds.size > 0) {
      list = list.filter((s: any) => !excludeIds.has(s.id))
    }

    allStaffList.value = list
    const validIds = allStaffList.value.map((s: any) => s.id)
    autoScheduleForm.staff_ids = autoScheduleForm.staff_ids.filter(id => validIds.includes(id))
  } catch (e) {
    allStaffList.value = []
  }
}

function handleAutoSchedule() {
  const y = currentYear.value
  const m = currentMonth.value
  autoScheduleForm.start_date = `${y}-${String(m + 1).padStart(2, '0')}-01`
  const lastDay = new Date(y, m + 1, 0).getDate()
  autoScheduleForm.end_date = `${y}-${String(m + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
  autoScheduleForm.org_id = filterOrgId.value || null
  autoScheduleForm.shift_template_ids = shiftTemplateList.value.map((t: any) => t.id)
  autoScheduleForm.staff_ids = []
  autoScheduleDialogVisible.value = true
  loadAllStaff()
}

function handleAutoOrgChange() {
  autoScheduleForm.staff_ids = []
  loadAllStaff()
}

async function handleAutoGenerate() {
  if (!autoScheduleForm.org_id) {
    ElMessage.warning('请选择排班范围（组织）')
    return
  }
  if (autoScheduleForm.shift_template_ids.length === 0) {
    ElMessage.warning('请至少选择一个班次模板')
    return
  }
  if (autoScheduleForm.staff_ids.length === 0) {
    ElMessage.warning('请选择排班人员')
    return
  }

  autoScheduleLoading.value = true
  try {
    const params: any = {
      start_date: autoScheduleForm.start_date,
      end_date: autoScheduleForm.end_date,
      org_id: autoScheduleForm.org_id,
      shift_template_ids: autoScheduleForm.shift_template_ids.join(','),
      staff_ids: autoScheduleForm.staff_ids.join(','),
    }
    const res: any = await api.post('/schedules/auto-generate', null, { params })

    autoScheduleDialogVisible.value = false
    ElMessage.success(`自动排班完成：共生成 ${res.report?.total_shifts || 0} 条排班`)

    if (res.conflicts && res.conflicts.length > 0) {
      ElMessage.warning(`排班发现 ${res.conflicts.length} 条冲突`)
    }

    await loadCalendar()
  } catch (e) {
    // interceptor handles error
  } finally {
    autoScheduleLoading.value = false
  }
}

// ==================== 当月日期范围（不含跨月） ====================

const currentMonthRange = computed(() => {
  const y = currentYear.value
  const m = currentMonth.value
  const start = new Date(y, m, 1)
  const end = new Date(y, m + 1, 0)
  return {
    start: formatDateStr(start),
    end: formatDateStr(end),
  }
})

// ==================== 导出排班 ====================

const exportDialogVisible = ref(false)
const exportLoading = ref(false)
const templateDownloading = ref(false)
const scheduleImporting = ref(false)

function handleExport() {
  exportDialogVisible.value = true
}

async function handleDownloadImportTemplate() {
  templateDownloading.value = true
  try {
    const params: any = {
      start_date: currentMonthRange.value.start,
      end_date: currentMonthRange.value.end,
    }
    if (filterOrgId.value) params.org_id = filterOrgId.value
    await downloadScheduleImportTemplate(params)
    ElMessage.success('模板已开始下载')
  } catch (e) {
    // interceptor handles error
  } finally {
    templateDownloading.value = false
  }
}

// ==================== 导入排班 ====================

const showImportDialog = ref(false)
const importFileInput = ref<HTMLInputElement | null>(null)
const importFileForImport = ref<File | null>(null)
const importFileName = ref('')

function triggerImportFile() {
  importFileInput.value?.click()
}

async function doImportFile() {
  if (!importFileForImport.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  try {
    await confirm({
      type: 'warning',
      title: '确认导入排班？',
      message: '导入会创建草稿排班；若同日期/组织/班次已有草稿或已撤回记录，会覆盖人员明细。已发布或待审核排班不会被覆盖。',
      confirmText: '确认导入',
      cancelText: '取消',
    })
    scheduleImporting.value = true
    try {
      const res: any = await importScheduleTemplate(importFileForImport.value!, filterOrgId.value)
      ElMessage.success(res.message || '排班导入完成')
      importFileForImport.value = null
      importFileName.value = ''
      showImportDialog.value = false
      await loadCalendar()
    } catch (e) {
      // interceptor handles error
    } finally {
      scheduleImporting.value = false
    }
  } catch (e) {
    // 用户取消
  }
}

function handleImportFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    ElMessage.warning('请上传 .xlsx 格式的排班模板')
    return
  }
  importFileForImport.value = file
  importFileName.value = file.name
}

// ==================== 约束校验 ====================

const validating = ref(false)
const validationResult = ref<any>(null)
const validationDialogVisible = ref(false)

async function handleValidate() {
  validating.value = true
  try {
    const range = getDateRange()
    const params: any = {
      start_date: range.start,
      end_date: range.end,
    }
    if (filterOrgId.value) params.org_id = filterOrgId.value

    const result: any = await api.post('/schedules/validate', null, { params })
    validationResult.value = result
    validationDialogVisible.value = true

    const { is_valid, passed_count, warning_count, failed_count } = result
    if (is_valid) {
      ElMessage.success(`校验通过：${passed_count} 项通过，${warning_count} 项警告`)
    } else {
      ElMessage.warning(`校验发现 ${failed_count} 项错误，${warning_count} 项警告，请处理后发布`)
    }
  } catch (e) {
    // interceptor handles error
  } finally {
    validating.value = false
  }
}

// ==================== 发布 / 撤回 ====================

async function handlePublish() {
  const ids = collectScheduleIdsByStatus([0, 2])
  if (ids.length === 0) {
    ElMessage.info('当前视图中没有草稿或已撤回状态的排班')
    return
  }

  try {
    await confirm({
      type: 'warning',
      title: '确认发布？',
      message: `确认发布当前视图中的 ${ids.length} 条排班？发布后排班将被锁定，变更需通过调班流程。`,
      confirmText: '确认发布',
      cancelText: '取消',
    })
    const res = await publishSchedules(ids)
    ElMessage.success(`成功发布 ${res.count ?? ids.length} 条排班`)
    await loadCalendar()
  } catch (e) {
    // 用户取消或接口错误
  }
}

async function handleRecall() {
  const orgId = filterOrgId.value
  if (!orgId) {
    ElMessage.warning('请先选择组织')
    return
  }

  const y = currentYear.value
  const m = currentMonth.value + 1
  const monthLabel = `${y}年${m}月`

  try {
    await confirm({
      type: 'warning',
      title: '确认撤回？',
      message: `确认撤回 ${monthLabel} 所有已发布/待审核的排班？撤回后排班将变为草稿。`,
      confirmText: '确认撤回',
      cancelText: '取消',
    })
    const res = await recallSchedulesByMonth(orgId, y, m)
    if (res.count === 0) {
      ElMessage.info(`${monthLabel} 没有可撤回的排班`)
    } else {
      ElMessage.success(`成功撤回 ${monthLabel} ${res.count} 条排班`)
    }
    await loadCalendar()
  } catch (e) {
    // 用户取消或接口错误
  }
}

async function handleApprove() {
  const pendingIds = collectScheduleIdsByStatus(3)
  if (pendingIds.length === 0) {
    ElMessage.info('当前视图中没有待审核的排班')
    return
  }

  try {
    await confirm({
      type: 'warning',
      title: '确认审核通过？',
      message: `确认通过当前视图中的 ${pendingIds.length} 条排班？通过后排班将被锁定。`,
      confirmText: '通过',
      cancelText: '取消',
    })
    const res = await approveSchedules(pendingIds)
    ElMessage.success(`审核通过 ${res.count ?? pendingIds.length} 条排班`)
    await loadCalendar()
  } catch (e) {
    // 用户取消或接口错误
  }
}

async function handleReject() {
  const pendingIds = collectScheduleIdsByStatus(3)
  if (pendingIds.length === 0) {
    ElMessage.info('当前视图中没有待审核的排班')
    return
  }

  try {
    await confirm({
      type: 'warning',
      title: '确认拒绝？',
      message: `确认拒绝当前视图中的 ${pendingIds.length} 条排班？拒绝后排班将打回草稿。`,
      confirmText: '拒绝',
      cancelText: '取消',
    })
    const res = await rejectSchedules(pendingIds)
    ElMessage.success(`已拒绝 ${res.count ?? pendingIds.length} 条排班`)
    await loadCalendar()
  } catch (e) {
    // 用户取消或接口错误
  }
}

async function handleDeleteDrafts() {
  try {
    await confirm({
      type: 'danger',
      title: '确认清除草稿？',
      message: '将删除当前视图中所有草稿和已撤回的排班，已发布和待审核的排班不受影响。此操作不可恢复。',
      confirmText: '确认删除',
      cancelText: '取消',
    })

    const range = getDateRange()
    const params: any = {
      start_date: range.start,
      end_date: range.end,
    }
    if (filterOrgId.value) params.org_id = filterOrgId.value

    const res: any = await api.post('/schedules/delete-drafts', null, { params })
    ElMessage.success(res.message || `已删除 ${res.count || 0} 条草稿排班`)
    await loadCalendar()
  } catch (e) {
    // 用户取消
  }
}

function collectScheduleIdsByStatus(statuses: number | number[]): number[] {
  const arr = Array.isArray(statuses) ? statuses : [statuses]
  const ids: number[] = []
  for (const day of calendarData.value) {
    for (const shift of day.shifts) {
      if (arr.includes(shift.status)) {
        ids.push(shift.schedule_id)
      }
    }
  }
  return [...new Set(ids)]
}

async function handlePublishFromValidation() {
  validationDialogVisible.value = false
  await handlePublish()
}

function formatDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

onMounted(async () => {
  await Promise.all([loadOrgs(), loadShiftTemplates()])
  await loadCalendar()

  if (route.query.auto === '1') {
    handleAutoSchedule()
    router.replace({ path: '/schedule' })
  }
})
</script>

<style scoped>
.schedule-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px - 40px);
  background: var(--neo-color-bg-primary);
  padding: 0;
  min-width: 900px;
  overflow-x: auto;
}

/* Tab 栏 */
.tab-bar {
  display: flex;
  gap: 0;
  margin: 20px 20px 0;
  background: var(--neo-color-bg-card);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md) var(--neo-radius-md) 0 0;
  box-shadow: var(--neo-shadow-default);
  overflow: hidden;
}

.tab-item {
  padding: 12px 28px;
  font-size: 14px;
  font-weight: 700;
  color: var(--neo-color-text-primary);
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.15s;
  user-select: none;
}

.tab-item:hover {
  background: var(--neo-color-bg-primary);
}

.tab-item.active {
  color: var(--neo-color-bg-card);
  background: var(--neo-color-accent-blue);
  border-bottom-color: var(--neo-color-border);
}

/* 工具栏 */
.calendar-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--neo-color-bg-card);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-default);
  margin: 0 20px 16px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.current-month-label {
  font-size: 18px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  white-space: nowrap;
}

.toolbar-center {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
  flex: 1 1 auto;
}

/* 筛选卡片组 — Neo 卡片样式，带标签 */
.filter-card-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
  background: var(--neo-color-bg-card);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-xs);
  padding: 8px 10px;
  transition: all 0.15s ease;
}

.filter-card-group:hover {
  box-shadow: var(--neo-shadow-hover);
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs));
}

.filter-card-label {
  font-size: 10px;
  font-weight: 900;
  color: var(--neo-color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  line-height: 1;
}

.toolbar-center .toolbar-filter {
  width: 150px !important;
  flex: 0 0 auto;
}

.toolbar-center .toolbar-view-toggle {
  flex: 0 0 auto;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

/* 按钮文字 — 大屏显示，小屏隐藏 */
.btn-text {
  display: inline;
  white-space: nowrap;
}

/* ============================================
   工具栏筛选控件样式（统一 Neo 风格）
   ============================================ */

/* 下拉选择 — 紧凑 Neo 风格 */
.toolbar-filter .el-select__wrapper {
  height: 36px !important;
  min-height: 36px !important;
  border: var(--neo-border-thick) solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-md) !important;
  box-shadow: var(--neo-shadow-xs) !important;
  background: var(--neo-color-bg-card) !important;
  padding: 0 10px !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  transition: all 0.1s ease !important;
}

.toolbar-filter .el-select__wrapper:hover {
  box-shadow: var(--neo-shadow-hover) !important;
}

.toolbar-filter .el-select__wrapper.is-focused {
  box-shadow: 4px 4px 0px 0px var(--neo-color-accent-yellow) !important;
  border-color: var(--neo-color-border) !important;
}

.toolbar-filter .el-input__inner {
  font-weight: 700 !important;
  font-size: 13px !important;
  color: var(--neo-color-text-primary) !important;
}

.toolbar-filter .el-input__inner::placeholder {
  color: var(--neo-color-text-muted) !important;
  font-weight: 600 !important;
}

/* 视图切换 — 统一 Neo 风格 */
.toolbar-view-toggle .el-radio-button__inner {
  height: 36px !important;
  min-height: 36px !important;
  line-height: 36px !important;
  border: var(--neo-border-thick) solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-md) !important;
  box-shadow: none !important;
  background: var(--neo-color-bg-card) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  padding: 0 16px !important;
  color: var(--neo-color-text-primary) !important;
  transition: all 0.1s ease !important;
}

.toolbar-view-toggle .el-radio-button__inner:hover {
  box-shadow: var(--neo-shadow-sm) !important;
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs));
}

/* 选中态 — 用 label 层级设颜色，避免 __inner 被全局样式覆盖 */
.toolbar-view-toggle .el-radio-button.is-active .el-radio-button__inner {
  background: var(--neo-color-accent-blue) !important;
  color: var(--neo-color-bg-card) !important;
  box-shadow: var(--neo-shadow-default) !important;
  border-color: var(--neo-color-border) !important;
  font-weight: 900 !important;
}

/* 相邻兄弟：选中第一个时，第二个左边不要重复阴影 */
.toolbar-view-toggle .el-radio-button:first-child.is-active .el-radio-button__inner {
  border-radius: 4px 0 0 4px !important;
}

.toolbar-view-toggle .el-radio-button:last-child.is-active .el-radio-button__inner {
  border-radius: 0 4px 4px 0 !important;
}

.toolbar-view-toggle .el-radio-button__original-radio {
  display: none !important;
}

/* 日历主体 */
.calendar-body {
  flex: 1;
  margin: 0 20px 20px;
  background: var(--neo-color-bg-card);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: 4px;
  box-shadow: var(--neo-shadow-hover);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 更多菜单 popover */
.toolbar-more-popover {
  border: var(--neo-border-thick) solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-md) !important;
  box-shadow: var(--neo-shadow-hover) !important;
  background: var(--neo-color-bg-card) !important;
  padding: 8px !important;
}

.more-menu {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.more-menu .btn-more-item {
  width: 100% !important;
  justify-content: flex-start;
}

.more-menu .btn-more-item .btn-text {
  display: inline;
}

/* 班次说明 */
.violation-item {
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.violation-item.warning {
  background: var(--neo-color-accent-yellow);
  border-left: var(--neo-border-ultra) solid var(--neo-color-border);
}

.violation-item.error {
  background: var(--neo-color-danger-bg);
  border-left: var(--neo-border-ultra) solid var(--neo-color-accent-red);
}

.violation-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--neo-color-text-primary);
  margin-bottom: 4px;
}

.violation-msg {
  font-size: 13px;
  color: var(--neo-color-text-secondary);
  margin-bottom: 2px;
}

.violation-meta {
  font-size: 12px;
  color: var(--neo-color-text-secondary);
}

.shift-legend {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border-top: var(--neo-border-thick) solid var(--neo-color-border);
  background: var(--neo-color-bg-primary);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.legend-title {
  font-size: 13px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border: var(--neo-border-thin) solid var(--neo-color-border);
  border-radius: 3px;
  background: var(--neo-color-bg-card);
  box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.08);
  transition: all 0.15s ease;
}

.legend-item:hover {
  box-shadow: var(--neo-shadow-md);
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs));
}

.legend-dot {
  width: 14px;
  height: 14px;
  border: var(--neo-border-thin) solid var(--neo-color-border);
  flex-shrink: 0;
}

.legend-text {
  font-size: 13px;
  font-weight: 700;
  color: var(--neo-color-text-primary);
  white-space: nowrap;
}

/* ========== 新增样式 ========== */

/* 筛选栏卡片 */
.filter-card {
  background: var(--neo-color-bg-card);
  border: var(--neo-border-ultra) solid var(--neo-color-border);
  border-radius: 4px;
  box-shadow: var(--neo-shadow-default);
  padding: 16px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.filter-card:hover {
  box-shadow: var(--neo-shadow-hover);
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs));
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-label-text {
  font-size: 12px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 班次图例卡片 */
.legend-card {
  background: var(--neo-color-bg-card);
  border: var(--neo-border-ultra) solid var(--neo-color-border);
  border-radius: 4px;
  box-shadow: var(--neo-shadow-default);
  padding: 14px 16px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.legend-card:hover {
  box-shadow: var(--neo-shadow-hover);
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs));
}

.legend-card-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.legend-card-title {
  font-size: 12px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-right: 8px;
}

.legend-color-box {
  width: 20px;
  height: 20px;
  border: var(--neo-border-thin) solid var(--neo-color-border);
  border-radius: 2px;
  flex-shrink: 0;
}

.legend-card-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-card-text {
  font-size: 13px;
  font-weight: 700;
  color: var(--neo-color-text-primary);
}

/* 统计卡片 */
.stat-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.stat-card {
  background: var(--neo-color-bg-card);
  border: var(--neo-border-ultra) solid var(--neo-color-border);
  border-radius: 4px;
  box-shadow: var(--neo-shadow-default);
  padding: 20px;
  transition: all 0.2s ease;
}

.stat-card:hover {
  box-shadow: 10px 10px 0px 0px #000000;
  transform: translate(var(--neo-translate-hover), var(--neo-translate-hover));
}

.stat-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.stat-card-icon {
  font-size: 20px;
  color: var(--neo-color-text-primary);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: var(--neo-border-thin) solid var(--neo-color-border);
  border-radius: 3px;
  background: var(--neo-color-bg-primary);
}

.stat-card-label {
  font-size: 12px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-card-value {
  font-size: 32px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  line-height: 1;
}

/* 自动排班对话框样式增强 */
.neo-dialog :deep(.el-dialog__header) {
  border-bottom: var(--neo-border-thick) solid var(--neo-color-border);
  background: var(--neo-color-bg-primary);
  padding: 16px 20px;
}

.neo-dialog :deep(.el-dialog__title) {
  font-weight: 900 !important;
  color: var(--neo-color-text-primary);
  font-size: 18px;
}

.neo-dialog :deep(.el-dialog__body) {
  padding: 20px;
}

/* 校验报告标签页样式 */
.neo-tabs :deep(.el-tabs__header) {
  border-bottom: var(--neo-border-thick) solid var(--neo-color-border);
  background: var(--neo-color-bg-primary);
}

.neo-tabs :deep(.el-tabs__item) {
  font-weight: 700 !important;
  color: var(--neo-color-text-primary) !important;
  border: 2px solid transparent !important;
  border-bottom: none !important;
  transition: all 0.15s ease !important;
}

.neo-tabs :deep(.el-tabs__item.is-active) {
  background: var(--neo-color-bg-card) !important;
  border: var(--neo-border-thin) solid var(--neo-color-border) !important;
  border-bottom: 2px solid var(--neo-color-bg-card) !important;
  color: var(--neo-color-accent-blue) !important;
  font-weight: 900 !important;
}

.neo-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.neo-tabs :deep(.el-tabs__content) {
  padding: 16px 0;
}

/* 校验结果项 */
.validation-item {
  padding: 10px 12px;
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  margin-bottom: 8px;
  transition: all 0.15s ease;
}

.validation-item:hover {
  box-shadow: var(--neo-shadow-hover);
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs));
}

.validation-item.passed {
  background: var(--neo-color-success-bg);
  border-color: var(--neo-color-border);
}

.validation-item.warning {
  background: var(--neo-color-accent-yellow);
  border-color: var(--neo-color-border);
}

.validation-item.error {
  background: var(--neo-color-danger-bg);
  border-color: var(--neo-color-accent-red);
}

.validation-item-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--neo-color-text-primary);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.validation-item-msg {
  font-size: 13px;
  color: var(--neo-color-text-secondary);
  margin-bottom: 2px;
  font-weight: 600;
}

.validation-item-meta {
  font-size: 12px;
  color: var(--neo-color-text-secondary);
  font-weight: 600;
}

/* 筛选按钮 */
.filter-btn {
  width: 100%;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--neo-color-accent-yellow);
  color: var(--neo-color-text-primary);
  border: var(--neo-border-ultra) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-hover);
  font-weight: 900;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.1s ease;
}

.filter-btn:hover {
  box-shadow: var(--neo-shadow-default);
  transform: translate(var(--neo-translate-hover), var(--neo-translate-hover));
}

.filter-btn:active {
  box-shadow: var(--neo-shadow-active);
  transform: translate(var(--neo-translate-active), var(--neo-translate-active));
}

/* ============================================
   移动端适配
   ============================================ */

/* 页面整体 */
@media (max-width: 1024px) {
  /* 平板：按钮文字隐藏，只显示图标 */
  .btn-text {
    display: none;
  }

  .toolbar-right .el-button {
    padding: 6px 8px;
  }
}

@media (max-width: 768px) {
  .schedule-page {
    min-width: unset;
    overflow-x: visible;
    height: auto;
  }

  /* Tab 栏 */
  .tab-bar {
    margin: 12px 12px 0;
  }

  .tab-item {
    padding: 10px 16px;
    font-size: 13px;
  }

  /* 工具栏 */
  .calendar-toolbar {
    margin: 0 12px 12px;
    padding: 10px 12px;
    gap: 8px;
  }

  .toolbar-left {
    gap: 6px;
  }

  .current-month-label {
    font-size: 14px;
  }

  /* 筛选区 — 全宽换行 */
  .toolbar-center {
    width: 100%;
    gap: 8px;
  }

  .filter-card-group {
    flex: 1 1 calc(50% - 8px);
    min-width: 120px;
    padding: 6px 8px;
  }

  .filter-card-group:last-child {
    flex: 1 1 100%;
  }

  .toolbar-center .toolbar-filter {
    width: 100% !important;
  }

  .toolbar-center .toolbar-view-toggle {
    width: 100%;
    display: flex;
    justify-content: center;
  }

  .toolbar-center .toolbar-view-toggle .el-radio-button__inner {
    flex: 1;
    text-align: center;
  }

  /* 按钮区 — 全宽换行 */
  .toolbar-right {
    width: 100%;
    justify-content: stretch;
    gap: 4px;
  }

  .toolbar-right .el-button {
    flex: 1 1 calc(33.33% - 4px);
    min-width: 0;
    padding: 6px 4px;
    font-size: 11px;
    height: 34px;
    justify-content: center;
  }

  /* 日历主体 */
  .calendar-body {
    margin: 0 12px 12px;
    overflow: visible;
  }

  /* 班次图例 */
  .shift-legend {
    padding: 10px 12px;
    gap: 8px;
  }

  .legend-item {
    padding: 3px 6px;
    font-size: 12px;
  }

  .legend-text {
    font-size: 12px;
  }

  /* 对话框 */
  .neo-dialog :deep(.el-dialog) {
    width: 95% !important;
    margin: 20px auto;
  }

  .neo-dialog :deep(.el-dialog__body) {
    padding: 12px;
  }
}

/* 小屏手机 */
@media (max-width: 480px) {
  .calendar-toolbar {
    padding: 8px 10px;
    margin: 0 8px 8px;
  }

  .current-month-label {
    font-size: 13px;
  }

  .toolbar-right .el-button {
    flex: 1 1 calc(50% - 4px);
    font-size: 11px;
    height: 32px;
  }

  .tab-item {
    padding: 8px 12px;
    font-size: 12px;
  }

  .calendar-body {
    margin: 0 8px 8px;
  }
}
</style>
