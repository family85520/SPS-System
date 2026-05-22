<template>
  <div class="schedule-page">
    <!-- 工具栏 -->
    <div class="calendar-toolbar">
      <!-- 左侧：导航 -->
      <div class="toolbar-left">
        <el-button-group>
          <el-button @click="navigateMonth(-1)">
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <el-button @click="goToday">今天</el-button>
          <el-button @click="navigateMonth(1)">
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </el-button-group>
        <span class="current-month-label">{{ currentYear }}年{{ currentMonth + 1 }}月</span>
      </div>

      <!-- 中间：筛选 -->
      <div class="toolbar-center">
        <el-select
          v-model="filterOrgId"
          placeholder="全部组织"
          clearable
          style="width: 160px"
          @change="loadCalendar"
        >
          <el-option
            v-for="org in orgList"
            :key="org.id"
            :label="org.name"
            :value="org.id"
          />
        </el-select>

        <el-select
          v-model="filterStatus"
          placeholder="全部状态"
          clearable
          style="width: 120px"
          @change="loadCalendar"
        >
          <el-option label="草稿" :value="0" />
          <el-option label="已发布" :value="1" />
          <el-option label="已撤回" :value="2" />
          <el-option label="待审核" :value="3" />
        </el-select>

        <el-radio-group v-model="viewMode" @change="loadCalendar">
          <el-radio-button value="month">月视图</el-radio-button>
          <el-radio-button value="week">周视图</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 右侧：操作 -->
      <div class="toolbar-right">
        <el-button v-if="authStore.hasPermission('schedule', 'create')" @click="handleAutoSchedule">
          <el-icon><MagicStick /></el-icon>
          自动排班
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'create')" @click="handleAddSchedule('')">
          <el-icon><Plus /></el-icon>
          添加排班
        </el-button>
        <el-button :loading="validating" @click="handleValidate">
          <el-icon><CircleCheck /></el-icon>
          校验
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'publish')" type="primary" @click="handlePublish">
          <el-icon><Upload /></el-icon>
          发布
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'publish')" @click="handleRecall">
          <el-icon><RefreshLeft /></el-icon>
          撤回
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'delete')" type="danger" @click="handleDeleteDrafts">
          <el-icon><Delete /></el-icon>
          清除草稿
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'approve')" type="success" @click="handleApprove">
          <el-icon><Select /></el-icon>
          审核通过
        </el-button>
        <el-button v-if="authStore.hasPermission('schedule', 'approve')" type="danger" @click="handleReject">
          <el-icon><CloseBold /></el-icon>
          审核拒绝
        </el-button>
        <el-button v-if="authStore.hasPermission('export', 'read')" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出排班
        </el-button>
      </div>
    </div>

    <!-- 日历主体 -->
    <div class="calendar-body" v-loading="loading">
      <CalendarGrid
        :year="currentYear"
        :month="currentMonth"
        :view-mode="viewMode"
        :calendar-data="calendarData"
        @click-shift="handleClickShift"
        @add-schedule="handleAddSchedule"
      />

      <!-- 自动排班对话框 -->
      <el-dialog v-model="autoScheduleDialogVisible" title="自动排班" width="520px">
        <el-form label-width="100px">
          <el-form-item label="排班周期">
            <el-date-picker
              v-model="autoScheduleForm.start_date"
              type="date"
              placeholder="开始日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 45%"
            />
            <span style="margin: 0 8px; color: #909399">至</span>
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
            <el-select v-model="autoScheduleForm.org_id" placeholder="选择组织" style="width: 100%" @change="handleAutoOrgChange">
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
          <el-form-item label="领导排班">
            <el-checkbox v-model="autoScheduleForm.include_leader">
              需要领导参与排班
            </el-checkbox>
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              候选范围：班次模板中指定的领导候选人员 > 标记为"带班领导"标签的人员 > 全部人员
            </div>
          </el-form-item>
          <el-form-item label="排班人员" required>
            <el-select
              v-model="autoScheduleForm.staff_ids"
              multiple
              filterable
              placeholder="选择参与排班的人员"
              style="width: 100%"
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
          <el-button @click="autoScheduleDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="autoScheduleLoading" @click="handleAutoGenerate">
            一键生成
          </el-button>
        </template>
      </el-dialog>

      <!-- 校验报告 -->
      <el-dialog v-model="validationDialogVisible" title="约束校验报告" width="640px">
        <template v-if="validationResult">
          <div style="display: flex; gap: 24px; margin-bottom: 20px;">
            <el-statistic title="通过" :value="validationResult.passed_count">
              <template #suffix><span style="color: #28A745">项</span></template>
            </el-statistic>
            <el-statistic title="警告" :value="validationResult.warning_count">
              <template #suffix><span style="color: #FFC107">项</span></template>
            </el-statistic>
            <el-statistic title="失败" :value="validationResult.failed_count">
              <template #suffix><span style="color: #DC3545">项</span></template>
            </el-statistic>
          </div>

          <el-tabs>
            <el-tab-pane :label="`已通过（${validationResult.passed_count}）`">
              <div v-for="(item, idx) in validationResult.passed" :key="idx" style="padding: 6px 0; font-size: 13px;">
                <span style="color: #28A745;">✓</span> {{ item.rule_name }}
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
          <el-button @click="validationDialogVisible = false">关闭</el-button>
          <el-button v-if="authStore.hasPermission('schedule', 'publish')" type="primary" :disabled="validationResult && !validationResult.is_valid" @click="handlePublish; validationDialogVisible = false">
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

    <!-- 详情抽屉 -->
    <ShiftDetailDrawer
      v-model:visible="drawerVisible"
      :schedule="currentSchedule"
      :calendar-shift="currentCalendarShift"
      @refresh="handleRefresh"
    />

    <!-- 新建排班对话框 -->
    <el-dialog v-model="createDialogVisible" title="新建排班" width="420px">
      <el-form label-width="80px">
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
          <el-select v-model="createForm.shift_id" placeholder="选择班次模板" style="width: 100%">
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
          <el-select v-model="createForm.org_id" placeholder="选择组织" style="width: 100%">
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
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateSubmit">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/index'
import {
  getScheduleCalendar,
  getSchedule,
  createSchedule,
  publishSchedules,
  recallSchedules,
  approveSchedules,
  rejectSchedules,
  type CalendarDate,
  type CalendarShift,
  type Schedule,
} from '@/api/schedule'
import CalendarGrid from './components/CalendarGrid.vue'
import ShiftDetailDrawer from './components/ShiftDetailDrawer.vue'

// ==================== 日历状态 ====================

const authStore = useAuthStore()
const loading = ref(false)
const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth())
const viewMode = ref<'month' | 'week'>('month')
const calendarData = ref<CalendarDate[]>([])

// ==================== 筛选 ====================

const filterOrgId = ref<number | undefined>(undefined)
const filterStatus = ref<number | undefined>(undefined)

// ==================== 组织 + 班次模板 ====================

const orgList = ref<any[]>([])
const shiftTemplateList = ref<any[]>([])

async function loadOrgs() {
  try {
    const res = await api.get('/organizations')
    orgList.value = Array.isArray(res) ? res : []
  } catch (e) {
    // interceptor handles error
  }
}

async function loadShiftTemplates() {
  try {
    const res = await api.get('/shift-templates')
    shiftTemplateList.value = Array.isArray(res) ? res : []
  } catch (e) {
    // interceptor handles error
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
  include_leader: true,
})
const autoScheduleLoading = ref(false)
const allStaffList = ref<any[]>([])

async function loadAllStaff() {
  try {
    const params: any = {}
    if (autoScheduleForm.org_id) params.org_id = autoScheduleForm.org_id
    const res: any = await api.get('/staffs', { params })
    allStaffList.value = Array.isArray(res) ? res : (res.items || [])
    // 清除不在当前列表中的已选人员
    const validIds = allStaffList.value.map((s: any) => s.id)
    autoScheduleForm.staff_ids = autoScheduleForm.staff_ids.filter(id => validIds.includes(id))
  } catch (e) {
    allStaffList.value = []
  }
}

function handleAutoSchedule() {
  // 默认当月
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
      include_leader: autoScheduleForm.include_leader,
    }
    const res: any = await api.post('/schedules/auto-generate', null, { params })

    autoScheduleDialogVisible.value = false
    ElMessage.success(`自动排班完成：共生成 ${res.report?.total_shifts || 0} 条排班`)

    if (res.conflicts && res.conflicts.length > 0) {
      ElMessageBox({
        title: '排班冲突提示',
        message: res.conflicts.slice(0, 10).join('\n') + (res.conflicts.length > 10 ? `\n...共${res.conflicts.length}条` : ''),
        type: 'warning',
      })
    }

    await loadCalendar()
  } catch (e) {
    // interceptor handles error
  } finally {
    autoScheduleLoading.value = false
  }
}

// ==================== 导出排班 ====================

function handleExport() {
  ElMessage.info('导出排班功能将在后续版本中实现')
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
  const draftIds = collectScheduleIdsByStatus(0)
  if (draftIds.length === 0) {
    ElMessage.info('当前视图中没有草稿状态的排班')
    return
  }

  try {
    await ElMessageBox({
      title: '确认发布？',
      message: `确认发布当前视图中的 ${draftIds.length} 条排班？发布后排班将被锁定，变更需通过调班流程。`,
      showCancelButton: true,
      confirmButtonText: '确认发布',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await publishSchedules(draftIds)
    ElMessage.success(`成功发布 ${res.count ?? draftIds.length} 条排班`)
    await loadCalendar()
  } catch (e) {
    // 用户取消或接口错误
  }
}

async function handleRecall() {
  const publishedIds = collectScheduleIdsByStatus(1)
  if (publishedIds.length === 0) {
    ElMessage.info('当前视图中没有已发布的排班')
    return
  }

  try {
    await ElMessageBox({
      title: '确认撤回？',
      message: `确认撤回当前视图中的 ${publishedIds.length} 条排班？撤回后排班将变为草稿，相关人员将收到通知。`,
      showCancelButton: true,
      confirmButtonText: '确认撤回',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await recallSchedules(publishedIds)
    ElMessage.success(`成功撤回 ${res.count ?? publishedIds.length} 条排班`)
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
    await ElMessageBox({
      title: '确认审核通过？',
      message: `确认通过当前视图中的 ${pendingIds.length} 条排班？通过后排班将被锁定。`,
      showCancelButton: true,
      confirmButtonText: '通过',
      cancelButtonText: '取消',
      type: 'warning',
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
    await ElMessageBox({
      title: '确认拒绝？',
      message: `确认拒绝当前视图中的 ${pendingIds.length} 条排班？拒绝后排班将打回草稿。`,
      showCancelButton: true,
      confirmButtonText: '拒绝',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await rejectSchedules(pendingIds)
    ElMessage.success(`已拒绝 ${res.count ?? pendingIds.length} 条排班`)
    await loadCalendar()
  } catch (e) {
    // 用户取消或接口错误
  }
}

// 判断当前视图中是否有可编辑的排班（草稿或已撤回）
function hasEditableSchedules(): boolean {
  for (const day of calendarData.value) {
    for (const shift of day.shifts) {
      if (shift.status === 0 || shift.status === 2) return true
    }
  }
  return false
}

async function handleDeleteDrafts() {
  try {
    await ElMessageBox({
      title: '确认清除草稿？',
      message: '将删除当前视图中所有草稿和已撤回的排班，已发布和待审核的排班不受影响。此操作不可恢复。',
      showCancelButton: true,
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
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

function collectScheduleIdsByStatus(status: number): number[] {
  const ids: number[] = []
  for (const day of calendarData.value) {
    for (const shift of day.shifts) {
      if (shift.status === status) {
        ids.push(shift.schedule_id)
      }
    }
  }
  return [...new Set(ids)]
}

// ==================== 工具函数 ====================

function formatDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

// ==================== 初始化 ====================

onMounted(async () => {
  await Promise.all([loadOrgs(), loadShiftTemplates()])
  await loadCalendar()
})
</script>

<style scoped>
.schedule-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px - 40px);
  background: #F5F7FA;
  padding: 16px;
  min-width: 900px;
  overflow-x: auto;
}

/* 工具栏 */
.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  background: #FFFFFF;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(31, 45, 61, 0.06);
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.current-month-label {
  font-size: 18px;
  font-weight: 600;
  color: #1F2D3D;
}

.toolbar-center {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 日历主体 */
.calendar-body {
  flex: 1;
  background: #FFFFFF;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(31, 45, 61, 0.06);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 班次说明 */
.violation-item {
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.violation-item.warning {
  background: #FFF8E1;
  border-left: 3px solid #FFC107;
}

.violation-item.error {
  background: #FFF5F5;
  border-left: 3px solid #DC3545;
}

.violation-title {
  font-size: 14px;
  font-weight: 600;
  color: #1F2D3D;
  margin-bottom: 4px;
}

.violation-msg {
  font-size: 13px;
  color: #556173;
  margin-bottom: 2px;
}

.violation-meta {
  font-size: 12px;
  color: #909399;
}
.shift-legend {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border-top: 1px solid #E6EAF0;
  background: #FAFBFC;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.legend-title {
  font-size: 13px;
  font-weight: 600;
  color: #556173;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}

.legend-text {
  font-size: 13px;
  color: #1F2D3D;
}
</style>
