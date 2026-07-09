<template>
  <div class="constraint-page">
    <!-- 左侧：规则列表 -->
    <div class="left-panel">
      <div class="panel-header">
        <div class="panel-header-title">
          <span class="panel-icon"><el-icon><Lock /></el-icon></span>
          <h3>约束规则</h3>
        </div>
        <!-- 新建规则：需要 constraint create 权限 -->
        <el-button
          v-if="authStore.hasPermission('constraint', 'create')"
          class="btn-neo-primary btn-neo-sm" size="small"
          @click="handleCreate"
        >
          <el-icon><Plus /></el-icon>
          新建规则
        </el-button>
      </div>

      <div class="rule-list" v-loading="loading">
        <div
          v-for="(item, index) in ruleList"
          :key="item.id"
          class="rule-item"
          :class="{ active: selectedId === item.id, disabled: !item.enabled, preset: isPreset(item.rule_type) }"
          :style="{ '--delay': index * 0.04 }"
          @click="handleSelect(item)"
        >
          <div class="rule-item-icon" :class="getRuleIconClass(item.rule_type)">
            <el-icon><component :is="getRuleIcon(item.rule_type)" /></el-icon>
          </div>
          <div class="rule-item-body">
            <div class="rule-item-header">
              <span class="rule-name">{{ item.rule_name }}</span>
              <el-tag
                v-if="item.is_preset"
                size="small"
                class="preset-badge"
              >预置</el-tag>
            </div>
            <div class="rule-item-meta">
              <span class="priority-tag">{{ item.priority }}</span>
              <span class="rule-type-label">{{ getRuleTypeLabel(item.rule_type) }}</span>
            </div>
          </div>
          <!-- 启停切换：需要 constraint update 权限 -->
          <span
            v-if="authStore.hasPermission('constraint', 'update')"
            class="neo-switch-inline neo-switch-inline--sm"
            :class="{ 'is-checked': item.enabled, 'is-disabled': false }"
            @click.stop="handleToggle(item)"
          >
            <span class="neo-switch-knob neo-switch-knob--sm"></span>
          </span>
        </div>

        <div v-if="!loading && ruleList.length === 0" class="rule-empty">
          <el-icon :size="48" color="#C0C4CC"><Lock /></el-icon>
          <p>暂无约束规则</p>
        </div>
      </div>
    </div>

    <!-- 右侧：规则详情编辑 -->
    <div class="right-panel">
      <template v-if="selectedId !== null && formData">
        <div class="panel-header">
          <div class="panel-header-title">
            <span class="panel-icon panel-icon--blue"><el-icon><Setting /></el-icon></span>
            <h3>{{ isCreate ? '新建自定义规则' : (isPreset(formData.rule_type) ? '编辑预置规则' : '编辑自定义规则') }}</h3>
          </div>
        </div>

        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-width="140px"
          label-position="right"
          class="edit-form"
          v-loading="saving"
        >
          <el-form-item label="规则名称" prop="rule_name">
            <el-input
              v-model="formData.rule_name"
              placeholder="请输入规则名称"
              maxlength="100"
              show-word-limit
              :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')"
            />
          </el-form-item>

          <el-form-item v-if="isCreate" label="规则类型" prop="rule_type">
            <el-select v-model="formData.rule_type" placeholder="请选择规则类型" class="neo-input" @change="handleTypeChange">
              <el-option
                v-for="t in customRuleTypes"
                :key="t.value"
                :label="t.label"
                :value="t.value"
              />
            </el-select>
            <div class="type-hint">相同规则类型可针对不同组织创建多条</div>
          </el-form-item>

          <el-form-item v-else label="规则类型">
            <el-input :model-value="formData.rule_type" disabled />
          </el-form-item>

          <el-form-item label="启用状态">
            <span
              class="neo-switch-inline"
              :class="{ 'is-checked': formData.enabled, 'is-disabled': !authStore.hasPermission('constraint', 'update') }"
              @click="() => { if (authStore.hasPermission('constraint', 'update')) formData.enabled = !formData.enabled }"
            >
              <span class="neo-switch-knob"></span>
            </span>
          </el-form-item>

          <el-form-item label="优先级" prop="priority">
            <el-input-number
              v-model="formData.priority"
              :min="1"
              :max="999"
              controls-position="right"
              :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')"
            />
            <span class="priority-tip">数字越小越优先</span>
          </el-form-item>

          <el-form-item label="适用范围" prop="scope_type">
            <el-radio-group
              v-model="formData.scope_type"
              :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')"
            >
              <el-radio value="all">全部组织</el-radio>
              <el-radio value="org">指定组织</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="formData.scope_type === 'org'" label="指定组织">
            <el-select
              v-model="formData.scope_ids"
              multiple
              filterable
              placeholder="选择适用的组织"
              class="neo-input"
              :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')"
            >
              <el-option
                v-for="org in orgList"
                :key="org.id"
                :label="org.name"
                :value="org.id"
              />
            </el-select>
          </el-form-item>

          <div class="form-section-header">
            <el-icon class="form-section-icon"><DataLine /></el-icon>
            <span class="form-section-title">规则参数</span>
          </div>

          <!-- 连续工作上限 -->
          <template v-if="formData.rule_type === 'MAX_CONTINUOUS_DAYS'">
            <el-form-item label="最多连续上班天数">
              <el-input-number v-model="formData.params.max_days" :min="1" :max="30" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 连续工作后最少休息 -->
          <template v-if="formData.rule_type === 'MIN_REST_AFTER_CONTINUOUS'">
            <el-form-item label="最少休息天数">
              <el-input-number v-model="formData.params.rest_days" :min="1" :max="14" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 班次最少间隔 -->
          <template v-if="formData.rule_type === 'MIN_SHIFT_INTERVAL'">
            <el-form-item label="最少间隔小时数">
              <el-input-number v-model="formData.params.hours" :min="1" :max="48" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">小时</span>
            </el-form-item>
          </template>

          <!-- 夜班后最少休息 -->
          <template v-if="formData.rule_type === 'MIN_REST_AFTER_NIGHT'">
            <el-form-item label="最少休息小时数">
              <el-input-number v-model="formData.params.hours" :min="1" :max="72" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">小时</span>
            </el-form-item>
          </template>

          <!-- 每天最多上班数 -->
          <template v-if="formData.rule_type === 'MAX_SHIFTS_PER_DAY'">
            <el-form-item label="每天最多排几个班">
              <el-input-number v-model="formData.params.count" :min="1" :max="5" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">个</span>
            </el-form-item>
          </template>

          <!-- 每周最多工作时长 -->
          <template v-if="formData.rule_type === 'MAX_WEEKLY_HOURS'">
            <el-form-item label="每周累计小时上限">
              <el-input-number v-model="formData.params.hours" :min="1" :max="168" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">小时</span>
            </el-form-item>
          </template>

          <!-- 节假日模式 -->
          <template v-if="formData.rule_type === 'HOLIDAY_MODE'">
            <el-form-item label="节假日排班模式">
              <el-radio-group v-model="formData.params.mode" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')">
                <el-radio value="normal">正常轮转</el-radio>
                <el-radio value="special">特殊安排</el-radio>
              </el-radio-group>
            </el-form-item>
          </template>

          <!-- 周末差异化 -->
          <template v-if="formData.rule_type === 'WEEKEND_DIFF'">
            <el-form-item label="启用周末差异化">
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.params.enabled, 'is-disabled': !authStore.hasPermission('constraint', isCreate ? 'create' : 'update') }"
                @click="() => { if (authStore.hasPermission('constraint', isCreate ? 'create' : 'update')) formData.params.enabled = !formData.params.enabled }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </el-form-item>
          </template>

          <!-- 连续夜班上限 -->
          <template v-if="formData.rule_type === 'MAX_CONSECUTIVE_NIGHTS'">
            <el-form-item label="最多连续夜班天数">
              <el-input-number v-model="formData.params.max_days" :min="1" :max="14" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 夜班之间最少间隔 -->
          <template v-if="formData.rule_type === 'MIN_INTERVAL_BETWEEN_NIGHTS'">
            <el-form-item label="夜班之间最少间隔">
              <el-input-number v-model="formData.params.days" :min="1" :max="14" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 每月最多夜班次数 -->
          <template v-if="formData.rule_type === 'MAX_NIGHTS_PER_MONTH'">
            <el-form-item label="每月最多夜班次数">
              <el-input-number v-model="formData.params.count" :min="1" :max="31" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">次</span>
            </el-form-item>
          </template>

          <!-- 工作量均衡分配 -->
          <template v-if="formData.rule_type === 'EQUAL_DISTRIBUTION'">
            <el-form-item label="启用工作量均衡">
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.params.enabled, 'is-disabled': !authStore.hasPermission('constraint', isCreate ? 'create' : 'update') }"
                @click="() => { if (authStore.hasPermission('constraint', isCreate ? 'create' : 'update')) formData.params.enabled = !formData.params.enabled }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </el-form-item>
            <el-form-item v-if="formData.params.enabled" label="允许偏差天数">
              <el-input-number v-model="formData.params.tolerance_days" :min="0" :max="10" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 值班领导轮换均衡 -->
          <template v-if="formData.rule_type === 'LEADER_ROTATION'">
            <el-form-item label="启用领导轮换均衡">
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.params.enabled, 'is-disabled': !authStore.hasPermission('constraint', isCreate ? 'create' : 'update') }"
                @click="() => { if (authStore.hasPermission('constraint', isCreate ? 'create' : 'update')) formData.params.enabled = !formData.params.enabled }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </el-form-item>
          </template>

          <!-- 周末轮转均衡 -->
          <template v-if="formData.rule_type === 'WEEKEND_ROTATION'">
            <el-form-item label="启用周末轮转均衡">
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.params.enabled, 'is-disabled': !authStore.hasPermission('constraint', isCreate ? 'create' : 'update') }"
                @click="() => { if (authStore.hasPermission('constraint', isCreate ? 'create' : 'update')) formData.params.enabled = !formData.params.enabled }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </el-form-item>
            <el-form-item v-if="formData.params.enabled" label="每人每月最少周末班次">
              <el-input-number v-model="formData.params.min_times_per_month" :min="1" :max="10" controls-position="right" :disabled="!authStore.hasPermission('constraint', isCreate ? 'create' : 'update')" />
              <span class="param-unit">次</span>
            </el-form-item>
          </template>

          <!-- 新员工搭配老员工 -->
          <template v-if="formData.rule_type === 'NEW_STAFF_PAIRING'">
            <el-form-item label="启用新员工搭配">
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.params.enabled, 'is-disabled': !authStore.hasPermission('constraint', isCreate ? 'create' : 'update') }"
                @click="() => { if (authStore.hasPermission('constraint', isCreate ? 'create' : 'update')) formData.params.enabled = !formData.params.enabled }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </el-form-item>
          </template>

          <el-form-item>
            <div class="form-actions">
              <!-- 保存：新建时需要 create，编辑时需要 update -->
              <el-button
                v-if="authStore.hasPermission('constraint', isCreate ? 'create' : 'update')"
                type="primary"
                @click="handleSave"
              >
                保存
              </el-button>
              <!-- 删除：需要 constraint delete 权限 -->
              <el-button
                v-if="!isCreate && canDelete && authStore.hasPermission('constraint', 'delete')"
                class="btn-neo-danger"
                @click="handleDelete"
              >
                删除
              </el-button>
              <el-button class="btn-neo-ghost" @click="handleCancel">取消</el-button>
            </div>
          </el-form-item>
        </el-form>
      </template>

      <div v-else class="empty-state">
        <div class="empty-state-icon-wrap">
          <el-icon :size="56" color="#C0C4CC"><Setting /></el-icon>
        </div>
        <p>请从左侧选择规则<br>或点击"新建规则"</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useConfirm } from '@/composables/useConfirm'
import { Plus, Setting, Lock, DataLine, Clock, Sunny, Moon, Star, Connection, ScaleToOriginal, RefreshRight, Calendar, UserFilled, TrendCharts } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import {
  getConstraints,
  createConstraint,
  updateConstraint,
  deleteConstraint,
  toggleConstraint,
  type Constraint,
  type ConstraintUpdate,
  type ConstraintCreate,
} from '@/api/constraint'
import api from '@/api/index'

const authStore = useAuthStore()
const { confirm } = useConfirm()

const orgList = ref<any[]>([])

async function loadOrgs() {
  try {
    const res: any = await api.get('/options/organizations')
    orgList.value = Array.isArray(res) ? res : (res.data || [])
  } catch {
    orgList.value = []
  }
}

// 预置规则类型
const presetRuleTypes = new Set([
  'MAX_CONTINUOUS_DAYS',
  'MIN_REST_AFTER_CONTINUOUS',
  'MIN_SHIFT_INTERVAL',
  'MIN_REST_AFTER_NIGHT',
  'MAX_SHIFTS_PER_DAY',
  'MAX_WEEKLY_HOURS',
  'HOLIDAY_MODE',
  'WEEKEND_DIFF',
  'MAX_CONSECUTIVE_NIGHTS',
  'MIN_INTERVAL_BETWEEN_NIGHTS',
  'MAX_NIGHTS_PER_MONTH',
  'EQUAL_DISTRIBUTION',
  'LEADER_ROTATION',
  'WEEKEND_ROTATION',
  'NEW_STAFF_PAIRING',
])

const customRuleTypes = [
  { value: 'MAX_CONTINUOUS_DAYS', label: '连续工作上限' },
  { value: 'MIN_REST_AFTER_CONTINUOUS', label: '连续工作后最少休息' },
  { value: 'MIN_SHIFT_INTERVAL', label: '班次最少间隔' },
  { value: 'MAX_SHIFTS_PER_DAY', label: '每天最多上班数' },
  { value: 'MAX_WEEKLY_HOURS', label: '每周最多工作时长' },
  { value: 'MIN_REST_AFTER_NIGHT', label: '夜班后最少休息' },
  { value: 'MAX_CONSECUTIVE_NIGHTS', label: '连续夜班上限' },
  { value: 'MIN_INTERVAL_BETWEEN_NIGHTS', label: '夜班之间最少间隔天数' },
  { value: 'MAX_NIGHTS_PER_MONTH', label: '每月最多夜班次数' },
  { value: 'EQUAL_DISTRIBUTION', label: '工作量均衡分配' },
  { value: 'LEADER_ROTATION', label: '值班领导轮换均衡' },
  { value: 'WEEKEND_ROTATION', label: '周末轮转均衡' },
  { value: 'HOLIDAY_MODE', label: '节假日排班模式' },
  { value: 'WEEKEND_DIFF', label: '周末差异化' },
  { value: 'NEW_STAFF_PAIRING', label: '新员工必须搭配老员工' },
]

function isPreset(ruleType: string): boolean {
  return presetRuleTypes.has(ruleType)
}

// 规则类型显示标签
const ruleTypeLabels: Record<string, string> = {
  MAX_CONTINUOUS_DAYS: '连续工作上限',
  MIN_REST_AFTER_CONTINUOUS: '连续后休息',
  MIN_SHIFT_INTERVAL: '班次间隔',
  MIN_REST_AFTER_NIGHT: '夜班后休息',
  MAX_SHIFTS_PER_DAY: '每日班次上限',
  MAX_WEEKLY_HOURS: '每周工时',
  HOLIDAY_MODE: '节假日模式',
  WEEKEND_DIFF: '周末差异化',
  MAX_CONSECUTIVE_NIGHTS: '连续夜班上限',
  MIN_INTERVAL_BETWEEN_NIGHTS: '夜班间隔',
  MAX_NIGHTS_PER_MONTH: '每月夜班次数',
  EQUAL_DISTRIBUTION: '工作量均衡',
  LEADER_ROTATION: '领导轮换',
  WEEKEND_ROTATION: '周末轮转',
  NEW_STAFF_PAIRING: '新老搭配',
}

function getRuleTypeLabel(ruleType: string): string {
  return ruleTypeLabels[ruleType] || ruleType
}

// 规则图标映射
const ruleIconMap: Record<string, any> = {
  MAX_CONTINUOUS_DAYS: Clock,
  MIN_REST_AFTER_CONTINUOUS: Clock,
  MIN_SHIFT_INTERVAL: Clock,
  MIN_REST_AFTER_NIGHT: Moon,
  MAX_SHIFTS_PER_DAY: Calendar,
  MAX_WEEKLY_HOURS: TrendCharts,
  HOLIDAY_MODE: Star,
  WEEKEND_DIFF: Calendar,
  MAX_CONSECUTIVE_NIGHTS: Moon,
  MIN_INTERVAL_BETWEEN_NIGHTS: Clock,
  MAX_NIGHTS_PER_MONTH: Moon,
  EQUAL_DISTRIBUTION: ScaleToOriginal,
  LEADER_ROTATION: RefreshRight,
  WEEKEND_ROTATION: Connection,
  NEW_STAFF_PAIRING: UserFilled,
}

function getRuleIcon(ruleType: string): any {
  return ruleIconMap[ruleType] || Clock
}

// 规则图标背景色类
const ruleIconColorMap: Record<string, string> = {
  MAX_CONTINUOUS_DAYS: 'yellow',
  MIN_REST_AFTER_CONTINUOUS: 'yellow',
  MIN_SHIFT_INTERVAL: 'blue',
  MIN_REST_AFTER_NIGHT: 'purple',
  MAX_SHIFTS_PER_DAY: 'red',
  MAX_WEEKLY_HOURS: 'green',
  HOLIDAY_MODE: 'accent',
  WEEKEND_DIFF: 'cyan',
  MAX_CONSECUTIVE_NIGHTS: 'purple',
  MIN_INTERVAL_BETWEEN_NIGHTS: 'blue',
  MAX_NIGHTS_PER_MONTH: 'purple',
  EQUAL_DISTRIBUTION: 'green',
  LEADER_ROTATION: 'blue',
  WEEKEND_ROTATION: 'cyan',
  NEW_STAFF_PAIRING: 'yellow',
}

function getRuleIconClass(ruleType: string): string {
  return ruleIconColorMap[ruleType] || 'yellow'
}

const canDelete = computed(() => {
  if (formData.value.is_preset) {
    return false
  }
  return true
})

// 状态
const loading = ref(false)
const saving = ref(false)
const ruleList = ref<Constraint[]>([])
const selectedId = ref<number | null>(null)
const isCreate = ref(false)
const formRef = ref<FormInstance>()

const defaultParams: Record<string, Record<string, any>> = {
  MAX_CONTINUOUS_DAYS: { max_days: 5 },
  MIN_REST_AFTER_CONTINUOUS: { rest_days: 1 },
  MIN_SHIFT_INTERVAL: { hours: 8 },
  MAX_SHIFTS_PER_DAY: { count: 1 },
  MAX_WEEKLY_HOURS: { hours: 48 },
  MIN_REST_AFTER_NIGHT: { hours: 12 },
  MAX_CONSECUTIVE_NIGHTS: { max_days: 3 },
  MIN_INTERVAL_BETWEEN_NIGHTS: { days: 2 },
  MAX_NIGHTS_PER_MONTH: { count: 8 },
  EQUAL_DISTRIBUTION: { enabled: true, tolerance_days: 2 },
  LEADER_ROTATION: { enabled: true },
  WEEKEND_ROTATION: { enabled: true, min_times_per_month: 2 },
  HOLIDAY_MODE: { mode: 'normal' },
  WEEKEND_DIFF: { enabled: false },
  NEW_STAFF_PAIRING: { enabled: true },
}

const formData = ref<{
  id?: number
  rule_type: string
  rule_name: string
  params: Record<string, any>
  priority: number
  scope_type: string
  scope_ids: number[]
  enabled: boolean
  is_preset: boolean
}>({
  rule_type: '',
  rule_name: '',
  params: {},
  priority: 1,
  scope_type: 'all',
  scope_ids: [],
  enabled: true,
  is_preset: false,
})

const rules: FormRules = {
  rule_name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' },
    { max: 100, message: '规则名称不能超过100个字符', trigger: 'blur' },
  ],
  rule_type: [
    { required: true, message: '请选择规则类型', trigger: 'change' },
  ],
  priority: [
    { required: true, message: '请设置优先级', trigger: 'change' },
  ],
}

async function loadList() {
  loading.value = true
  try {
    ruleList.value = await getConstraints()
  } catch (e) {
    // interceptor handles error
  } finally {
    loading.value = false
  }
}

function handleSelect(item: Constraint) {
  isCreate.value = false
  selectedId.value = item.id
  // scope_ids 统一为数组格式
  let scopeIds = item.scope_ids
  if (typeof scopeIds === 'string') {
    try { scopeIds = JSON.parse(scopeIds) } catch { scopeIds = [] }
  }
  if (!Array.isArray(scopeIds)) scopeIds = scopeIds ? [scopeIds] : []

  formData.value = {
    id: item.id,
    rule_type: item.rule_type,
    rule_name: item.rule_name,
    params: { ...item.params },
    priority: item.priority,
    scope_type: item.scope_type,
    scope_ids: scopeIds,
    enabled: item.enabled,
    is_preset: item.is_preset,
  }
}

function handleCreate() {
  isCreate.value = true
  selectedId.value = -1
  formData.value = {
    rule_type: 'MAX_CONTINUOUS_DAYS',
    rule_name: '连续工作上限',
    params: { max_days: 5 },
    priority: 0,
    scope_type: 'all',
    scope_ids: [],
    enabled: true,
    is_preset: false,
  }
}

function handleTypeChange(value: string) {
  formData.value.params = { ...defaultParams[value] }
}

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isCreate.value) {
      const payload: ConstraintCreate = {
        rule_type: formData.value.rule_type,
        rule_name: formData.value.rule_name,
        params: formData.value.params,
        priority: formData.value.priority,
        scope_type: formData.value.scope_type,
        scope_ids: formData.value.scope_type === 'org' ? formData.value.scope_ids : null,
        enabled: formData.value.enabled,
      }
      await createConstraint(payload)
      ElMessage.success('创建成功')
      await loadList()
      isCreate.value = false
    } else {
      const payload: ConstraintUpdate = {
        rule_name: formData.value.rule_name,
        params: formData.value.params,
        priority: formData.value.priority,
        scope_type: formData.value.scope_type,
        scope_ids: formData.value.scope_type === 'org' ? formData.value.scope_ids : null,
        enabled: formData.value.enabled,
      }
      await updateConstraint(formData.value.id!, payload)
      ElMessage.success('保存成功')
      await loadList()
    }
  } catch (e) {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!formData.value.id) return
  try {
    await confirm({
      type: 'danger',
      title: '确认删除？',
      message: '删除后数据无法恢复，请慎重操作。',
      confirmText: '删除',
      cancelText: '取消',
    })
    await deleteConstraint(formData.value.id)
    ElMessage.success('删除成功')
    selectedId.value = null
    await loadList()
  } catch (e) {
    // 用户取消或接口错误
  }
}

async function handleToggle(item: Constraint) {
  try {
    await toggleConstraint(item.id)
    ElMessage.success(item.enabled ? '已禁用' : '已启用')
    await loadList()
    if (selectedId.value === item.id) {
      const updated = ruleList.value.find(r => r.id === item.id)
      if (updated) handleSelect(updated)
    }
  } catch (e) {
    // interceptor handles error
  }
}

function handleCancel() {
  selectedId.value = null
}

onMounted(() => {
  loadList()
  loadOrgs()
})
</script>

<style scoped>
/* ============================================================
   Constraint View — Neo-brutalism redesign
   Inspired by GemDesign ShiftRuleConfigPage prototype
   ============================================================ */

/* ---- Page Container ---- */
.constraint-page {
  display: flex;
  height: calc(100vh - 56px - 40px);
  gap: 20px;
  padding: 20px;
  background: var(--neo-color-bg-primary);
  overflow: hidden;
  min-width: 900px;
  animation: slide-in-left 0.3s ease both;
}

/* ---- Left / Right Panels — neo-card style ---- */
.left-panel,
.right-panel {
  background: var(--neo-color-bg-card);
  border: var(--neo-border-ultra) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.2s ease;
}

.left-panel {
  width: 400px;
  min-width: 340px;
  max-width: 480px;
}

.right-panel {
  flex: 1;
}

/* ---- Panel Header ---- */
.panel-header {
  padding: 16px 20px;
  border-bottom: var(--neo-border-ultra) solid var(--neo-color-border);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--neo-color-bg-primary);
}

.panel-header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-icon {
  width: 36px;
  height: 36px;
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  box-shadow: var(--neo-shadow-md);
  flex-shrink: 0;
  transition: transform 0.15s ease;
}

.panel-icon--blue {
  background: var(--neo-color-info-bg);
  color: var(--neo-color-accent-blue-hover);
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ---- Rule List ---- */
.rule-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ---- Rule Item — prototype card style ---- */
.rule-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: var(--neo-border-ultra) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  background: var(--neo-color-bg-card);
  box-shadow: var(--neo-shadow-default);
  cursor: pointer;
  transition: all 0.15s ease;
  animation: slide-in-left 0.3s ease both;
  animation-delay: calc(var(--delay, 0) * 1s);
  position: relative;
}

.rule-item:hover {
  box-shadow: var(--neo-shadow-hover);
  transform: translate(var(--neo-translate-hover), var(--neo-translate-hover));
  background: var(--neo-color-bg-primary);
}

.rule-item.active {
  background: var(--neo-color-bg-primary);
  border-color: var(--neo-color-accent-blue);
  box-shadow: 5px 5px 0px 0px #3B82F6;
}

.rule-item.active:hover {
  box-shadow: 8px 8px 0px 0px #3B82F6;
  transform: translate(var(--neo-translate-lg), var(--neo-translate-lg));
}

.rule-item.disabled {
  opacity: 0.5;
}

.rule-item.disabled:hover {
  transform: none;
  box-shadow: var(--neo-shadow-default);
}

/* ---- Rule Item Icon ---- */
.rule-item-icon {
  width: 44px;
  height: 44px;
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  box-shadow: var(--neo-shadow-active);
  transition: transform 0.2s ease;
}

.rule-item:hover .rule-item-icon {
  transform: rotate(3deg);
}

.rule-item-icon--yellow { background: var(--neo-color-accent-yellow); color: var(--neo-color-text-primary); }
.rule-item-icon--red { background: #FF6B6B; color: var(--neo-color-bg-card); }
.rule-item-icon--blue { background: var(--neo-color-info-bg); color: var(--neo-color-accent-blue-hover); }
.rule-item-icon--green { background: #D1FAE5; color: #047857; }
.rule-item-icon--purple { background: #EDE9FE; color: #6D28D9; }
.rule-item-icon--cyan { background: #CFFAFE; color: #0E7490; }
.rule-item-icon--accent { background: #FF6B6B; color: var(--neo-color-bg-card); }
.rule-item-icon--black { background: var(--neo-color-text-primary); color: var(--neo-color-bg-card); }

/* ---- Rule Item Body ---- */
.rule-item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rule-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rule-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--neo-color-text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---- Preset badge — neo-badge style ---- */
.preset-badge {
  background: var(--neo-color-accent-yellow) !important;
  color: var(--neo-color-text-primary) !important;
  border: var(--neo-border-thin) solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-sm) !important;
  font-weight: 700 !important;
  box-shadow: var(--neo-shadow-active) !important;
  font-size: 11px !important;
  padding: 0 6px !important;
  height: 20px !important;
  line-height: 16px !important;
}

/* ---- Rule Meta Row ---- */
.rule-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.priority-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 20px;
  padding: 0 6px;
  border: var(--neo-border-thin) solid var(--neo-color-border);
  border-radius: var(--neo-radius-sm);
  font-size: 12px;
  font-weight: 900;
  box-shadow: var(--neo-shadow-active);
  color: var(--neo-color-bg-card);
  background: var(--neo-color-accent-blue);
  flex-shrink: 0;
}

.rule-type-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--neo-color-text-secondary);
}

/* ---- Rule Empty State ---- */
.rule-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #C0C4CC;
  padding: 40px 20px;
}

.rule-empty p {
  font-size: 14px;
  font-weight: 600;
  text-align: center;
}

/* ---- Right Panel — Edit Form ---- */
.edit-form {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px 32px;
}

/* ---- Form Section Header (replaces el-divider) ---- */
.form-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 0;
  margin-top: 8px;
  margin-bottom: 4px;
  border-top: var(--neo-border-ultra) solid var(--neo-color-border);
}

.form-section-icon {
  font-size: 20px;
  color: var(--neo-color-accent-blue);
  flex-shrink: 0;
}

.form-section-title {
  font-size: 16px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ---- Priority Tip ---- */
.priority-tip {
  font-size: 12px;
  color: var(--neo-color-text-secondary);
  margin-left: 12px;
  font-weight: 600;
}

/* ---- Param Unit ---- */
.param-unit {
  font-size: 14px;
  color: var(--neo-color-text-primary);
  margin-left: 8px;
  font-weight: 700;
}

/* ---- Form Actions ---- */
.form-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
}

/* ---- Empty State (right panel) ---- */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px 20px;
}

.empty-state-icon-wrap {
  width: 80px;
  height: 80px;
  border: var(--neo-border-ultra) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  background: var(--neo-color-disabled);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--neo-shadow-default);
  transition: transform 0.2s ease;
}

.empty-state:hover .empty-state-icon-wrap {
  transform: rotate(10deg) scale(1.05);
}

.empty-state p {
  margin-top: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--neo-color-text-muted);
  text-align: center;
  line-height: 1.6;
}

/* ---- Type Hint ---- */
.type-hint {
  font-size: 12px;
  color: var(--neo-color-text-secondary);
  margin-top: 4px;
  line-height: 1.5;
  font-weight: 600;
}

/* ---- Neo Switch Inline (small) ---- */
.neo-switch-inline--sm {
  width: 32px !important;
  height: 18px !important;
  border-width: 2px !important;
  box-shadow: var(--neo-shadow-active) !important;
  flex-shrink: 0;
}

.neo-switch-inline--sm .neo-switch-knob--sm {
  width: 10px !important;
  height: 10px !important;
  border-width: 1px !important;
  box-shadow: var(--neo-shadow-xs) !important;
}

/* ---- Responsive ---- */
@media (max-width: 1200px) {
  .left-panel {
    width: 320px;
    min-width: 280px;
  }
}

@media (max-width: 900px) {
  .constraint-page {
    flex-direction: column;
    height: auto;
    min-height: calc(100vh - 56px - 40px);
  }

  .left-panel {
    width: 100%;
    max-width: none;
    height: 300px;
  }

  .right-panel {
    min-height: 500px;
  }
}
</style>
