<template>
  <el-drawer
    v-model="visible"
    :title="`${staffName} - 特殊排班规则`"
    size="560px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="drawer-body">
      <div class="drawer-toolbar">
        <el-button type="primary" size="small" @click="handleAdd">
          <el-icon><Plus /></el-icon>
          新增规则
        </el-button>
      </div>

      <div class="rule-list" v-loading="loading">
        <div v-for="rule in ruleList" :key="rule.id" class="rule-card">
          <div class="rule-card-header">
            <el-tag size="small">{{ ruleTypeLabel(rule.rule_type) }}</el-tag>
            <div class="rule-card-actions">
              <el-button link type="primary" size="small" @click="handleEdit(rule)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(rule)">删除</el-button>
            </div>
          </div>
          <div class="rule-card-body">
            <div class="rule-detail">{{ ruleParamsDesc(rule) }}</div>
            <div v-if="rule.effective_from || rule.effective_to" class="rule-validity">
              有效期：{{ rule.effective_from || '不限' }} ~ {{ rule.effective_to || '不限' }}
            </div>
            <div v-if="rule.reason" class="rule-reason">备注：{{ rule.reason }}</div>
          </div>
        </div>

        <el-empty v-if="!loading && ruleList.length === 0" description="暂无特殊排班规则" />
      </div>
    </div>

    <!-- 新增/编辑表单 -->
    <el-dialog
      v-model="formVisible"
      :title="isEdit ? '编辑规则' : '新增规则'"
      width="480px"
      append-to-body
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="right"
      >
        <el-form-item label="规则类型" prop="rule_type">
          <el-select v-model="formData.rule_type" placeholder="请选择规则类型" style="width: 100%" @change="handleTypeChange">
            <el-option
              v-for="t in ruleTypeOptions"
              :key="t.value"
              :label="t.label"
              :value="t.value"
            />
          </el-select>
        </el-form-item>

        <!-- exclude_shift: 不排某班次 -->
        <el-form-item v-if="formData.rule_type === 'exclude_shift'" label="排除班次">
          <el-select
            v-model="selectedShiftIds"
            multiple
            filterable
            placeholder="选择要排除的班次"
            style="width: 100%"
          >
            <el-option
              v-for="t in shiftTemplateList"
              :key="t.id"
              :label="`${t.name}（${t.start_time}-${t.end_time}）`"
              :value="t.id"
            />
          </el-select>
        </el-form-item>

        <!-- include_shift: 仅排某班次 -->
        <el-form-item v-if="formData.rule_type === 'include_shift'" label="仅排班次">
          <el-select
            v-model="selectedShiftIds"
            multiple
            filterable
            placeholder="选择仅排的班次"
            style="width: 100%"
          >
            <el-option
              v-for="t in shiftTemplateList"
              :key="t.id"
              :label="`${t.name}（${t.start_time}-${t.end_time}）`"
              :value="t.id"
            />
          </el-select>
        </el-form-item>

        <!-- exclude_post: 不排某岗位 -->
        <el-form-item v-if="formData.rule_type === 'exclude_post'" label="排除岗位ID">
          <el-input v-model="paramsInput" placeholder="输入岗位ID，逗号分隔，如 2" />
        </el-form-item>

        <!-- must_pair: 必须搭配某人 -->
        <el-form-item v-if="formData.rule_type === 'must_pair'" label="搭配人员">
          <el-select
            v-model="selectedStaffIds"
            multiple
            filterable
            placeholder="选择必须搭配的人员"
            style="width: 100%"
          >
            <el-option
              v-for="s in staffList"
              :key="s.id"
              :label="`${s.name}（${s.employee_no}）`"
              :value="s.id"
            />
          </el-select>
        </el-form-item>

        <!-- exclude_date: 特定日期不排班 -->
        <el-form-item v-if="formData.rule_type === 'exclude_date'" label="排除日期">
          <el-date-picker
            v-model="datePickerValue"
            type="dates"
            placeholder="选择不排班的日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>

        <!-- exclude_weekday: 特定星期不排某班 -->
        <template v-if="formData.rule_type === 'exclude_weekday'">
          <el-form-item label="排除星期">
            <el-checkbox-group v-model="weekdayValue">
              <el-checkbox v-for="(label, idx) in dayLabels" :key="idx" :value="idx + 1">{{ label }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="排除班次">
            <el-select
              v-model="selectedWeekdayShiftIds"
              multiple
              filterable
              placeholder="选择要排除的班次"
              style="width: 100%"
            >
              <el-option
                v-for="t in shiftTemplateList"
                :key="t.id"
                :label="`${t.name}（${t.start_time}-${t.end_time}）`"
                :value="t.id"
              />
            </el-select>
          </el-form-item>
        </template>

        <el-form-item label="有效期">
          <el-date-picker
            v-model="dateRangeValue"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="备注">
          <el-input v-model="formData.reason" type="textarea" :rows="3" placeholder="填写备注原因" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getSpecialRules,
  createSpecialRule,
  updateSpecialRule,
  deleteSpecialRule,
  type SpecialRule,
} from '@/api/special-rule'
import api from '@/api/index'

const props = defineProps<{
  staffId: number | null
  staffName: string
}>()

const visible = defineModel<boolean>('visible', { default: false })

const emit = defineEmits<{
  (e: 'saved'): void
}>()

const dayLabels = ['一', '二', '三', '四', '五', '六', '日']

const ruleTypeOptions = [
  { value: 'exclude_shift', label: '不排某班次' },
  { value: 'include_shift', label: '仅排某班次' },
  { value: 'exclude_post', label: '不排某岗位' },
  { value: 'must_pair', label: '必须搭配某人' },
  { value: 'exclude_date', label: '特定日期不排班' },
  { value: 'exclude_weekday', label: '特定星期不排某班' },
]

const ruleTypeMap: Record<string, string> = {
  exclude_shift: '不排某班次',
  include_shift: '仅排某班次',
  exclude_post: '不排某岗位',
  must_pair: '必须搭配某人',
  exclude_date: '特定日期不排班',
  exclude_weekday: '特定星期不排某班',
}

const loading = ref(false)
const saving = ref(false)
const ruleList = ref<SpecialRule[]>([])
const formVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

// 关联数据
const shiftTemplateList = ref<any[]>([])
const staffList = ref<any[]>([])

// 表单值
const selectedShiftIds = ref<number[]>([])
const selectedWeekdayShiftIds = ref<number[]>([])
const selectedStaffIds = ref<number[]>([])
const paramsInput = ref('')  // 仅 exclude_post 使用
const datePickerValue = ref<string[]>([])
const weekdayValue = ref<number[]>([])
const dateRangeValue = ref<[string, string] | null>(null)

const formData = ref({
  rule_type: 'exclude_shift',
  reason: '',
})

const formRules: FormRules = {
  rule_type: [{ required: true, message: '请选择规则类型', trigger: 'change' }],
}

// ==================== 名称映射 ====================

const shiftNameMap = computed(() => {
  const map: Record<number, string> = {}
  shiftTemplateList.value.forEach((t) => {
    map[t.id] = `${t.name}（${t.start_time}-${t.end_time}）`
  })
  return map
})

const staffNameMap = computed(() => {
  const map: Record<number, string> = {}
  staffList.value.forEach((s) => {
    map[s.id] = `${s.name}（${s.employee_no}）`
  })
  return map
})

function ruleTypeLabel(type: string): string {
  return ruleTypeMap[type] || type
}

function ruleParamsDesc(rule: SpecialRule): string {
  const params = rule.params || {}
  switch (rule.rule_type) {
    case 'exclude_shift': {
      const ids: number[] = params.exclude_shift_ids || []
      const names = ids.map((id) => shiftNameMap.value[id] || `ID:${id}`)
      return `排除班次：${names.join('、')}`
    }
    case 'include_shift': {
      const ids: number[] = params.include_shift_ids || []
      const names = ids.map((id) => shiftNameMap.value[id] || `ID:${id}`)
      return `仅排班次：${names.join('、')}`
    }
    case 'exclude_post':
      return `排除岗位ID：${(params.exclude_post_ids || []).join(', ')}`
    case 'must_pair': {
      const ids: number[] = params.must_pair_staff_ids || []
      const names = ids.map((id) => staffNameMap.value[id] || `ID:${id}`)
      return `必须搭配：${names.join('、')}`
    }
    case 'exclude_date':
      return `排除日期：${(params.exclude_dates || []).join('、')}`
    case 'exclude_weekday': {
      const weekdays = (params.exclude_weekdays || []).map((d: number) => `周${dayLabels[d - 1]}`).join('、')
      const shiftIds: number[] = params.exclude_shift_ids || []
      const shiftNames = shiftIds.map((id) => shiftNameMap.value[id] || `ID:${id}`)
      return `排除：每${weekdays}的班次「${shiftNames.join('、')}」`
    }
    default:
      return JSON.stringify(params)
  }
}

function handleTypeChange() {
  selectedShiftIds.value = []
  selectedWeekdayShiftIds.value = []
  selectedStaffIds.value = []
  paramsInput.value = ''
  datePickerValue.value = []
  weekdayValue.value = []
}

// ==================== 加载关联数据 ====================

async function loadShiftTemplates() {
  try {
    const res = await api.get('/shift-templates')
    shiftTemplateList.value = Array.isArray(res) ? res : []
  } catch (e) {
    shiftTemplateList.value = []
  }
}

async function loadStaffList() {
  try {
    const res: any = await api.get('/staffs')
    staffList.value = Array.isArray(res) ? res : (res.items || [])
  } catch (e) {
    staffList.value = []
  }
}

// ==================== 加载规则列表 ====================

async function loadList() {
  if (!props.staffId) return
  loading.value = true
  try {
    ruleList.value = await getSpecialRules({ staff_id: props.staffId })
  } catch (e) {
    // interceptor handles error
  } finally {
    loading.value = false
  }
}

// ==================== 新增 ====================

function handleAdd() {
  isEdit.value = false
  editingId.value = null
  formData.value = { rule_type: 'exclude_shift', reason: '' }
  selectedShiftIds.value = []
  selectedWeekdayShiftIds.value = []
  selectedStaffIds.value = []
  paramsInput.value = ''
  datePickerValue.value = []
  weekdayValue.value = []
  dateRangeValue.value = null
  formVisible.value = true
}

// ==================== 编辑 ====================

function handleEdit(rule: SpecialRule) {
  isEdit.value = true
  editingId.value = rule.id
  formData.value = {
    rule_type: rule.rule_type,
    reason: rule.reason || '',
  }

  const params = rule.params || {}
  selectedShiftIds.value = []
  selectedWeekdayShiftIds.value = []
  selectedStaffIds.value = []
  paramsInput.value = ''
  datePickerValue.value = []
  weekdayValue.value = []
  dateRangeValue.value = rule.effective_from && rule.effective_to
    ? [rule.effective_from, rule.effective_to]
    : null

  switch (rule.rule_type) {
    case 'exclude_shift':
      selectedShiftIds.value = params.exclude_shift_ids || []
      break
    case 'include_shift':
      selectedShiftIds.value = params.include_shift_ids || []
      break
    case 'exclude_post':
      paramsInput.value = (params.exclude_post_ids || []).join(',')
      break
    case 'must_pair':
      selectedStaffIds.value = params.must_pair_staff_ids || []
      break
    case 'exclude_date':
      datePickerValue.value = params.exclude_dates || []
      break
    case 'exclude_weekday':
      weekdayValue.value = params.exclude_weekdays || []
      selectedWeekdayShiftIds.value = params.exclude_shift_ids || []
      break
  }

  formVisible.value = true
}

// ==================== 构建 params ====================

function buildParams(): Record<string, any> {
  switch (formData.value.rule_type) {
    case 'exclude_shift':
      return { exclude_shift_ids: selectedShiftIds.value }
    case 'include_shift':
      return { include_shift_ids: selectedShiftIds.value }
    case 'exclude_post':
      return { exclude_post_ids: paramsInput.value.split(',').map(Number).filter(Boolean) }
    case 'must_pair':
      return { must_pair_staff_ids: selectedStaffIds.value }
    case 'exclude_date':
      return { exclude_dates: datePickerValue.value }
    case 'exclude_weekday':
      return {
        exclude_weekdays: weekdayValue.value,
        exclude_shift_ids: selectedWeekdayShiftIds.value,
      }
    default:
      return {}
  }
}

// ==================== 保存 ====================

// ==================== 校验逻辑 ====================

function validateRule(): string | null {
  const ruleType = formData.value.rule_type
  const newParams = buildParams()
  const existingRules = ruleList.value

  // 1. 校验必填参数
  if (ruleType === 'exclude_shift' || ruleType === 'include_shift') {
    if (selectedShiftIds.value.length === 0) {
      return '请至少选择一个班次'
    }
  }
  if (ruleType === 'must_pair') {
    if (selectedStaffIds.value.length === 0) {
      return '请至少选择一个搭配人员'
    }
    // 不能搭配自己
    if (selectedStaffIds.value.includes(props.staffId!)) {
      return '不能将自己设为搭配人员'
    }
  }
  if (ruleType === 'exclude_post') {
    if (!paramsInput.value.trim()) {
      return '请填写岗位ID'
    }
  }
  if (ruleType === 'exclude_date') {
    if (datePickerValue.value.length === 0) {
      return '请至少选择一个排除日期'
    }
  }
  if (ruleType === 'exclude_weekday') {
    if (weekdayValue.value.length === 0) {
      return '请至少选择一个排除星期'
    }
    if (selectedWeekdayShiftIds.value.length === 0) {
      return '请至少选择一个排除班次'
    }
  }

  // 2. 与已有规则的冲突校验
  for (const existing of existingRules) {
    // 跳过当前正在编辑的规则
    if (isEdit.value && editingId.value === existing.id) continue

    const eParams = existing.params || {}

    // 2.1 完全重复：同类型 + 同参数
    if (existing.rule_type === ruleType) {
      let isDuplicate = false
      switch (ruleType) {
        case 'exclude_shift':
        case 'include_shift': {
          const key = ruleType === 'exclude_shift' ? 'exclude_shift_ids' : 'include_shift_ids'
          const newIds = (newParams[key] || []).sort().join(',')
          const oldIds = (eParams[key] || []).sort().join(',')
          isDuplicate = newIds === oldIds
          break
        }
        case 'must_pair': {
          const newIds = (newParams.must_pair_staff_ids || []).sort().join(',')
          const oldIds = (eParams.must_pair_staff_ids || []).sort().join(',')
          isDuplicate = newIds === oldIds
          break
        }
        case 'exclude_date': {
          const newDates = (newParams.exclude_dates || []).sort().join(',')
          const oldDates = (eParams.exclude_dates || []).sort().join(',')
          isDuplicate = newDates === oldDates
          break
        }
        case 'exclude_weekday': {
          const newDays = (newParams.exclude_weekdays || []).sort().join(',')
          const oldDays = (eParams.exclude_weekdays || []).sort().join(',')
          const newShifts = (newParams.exclude_shift_ids || []).sort().join(',')
          const oldShifts = (eParams.exclude_shift_ids || []).sort().join(',')
          isDuplicate = newDays === oldDays && newShifts === oldShifts
          break
        }
        case 'exclude_post': {
          const newIds = (newParams.exclude_post_ids || []).sort().join(',')
          const oldIds = (eParams.exclude_post_ids || []).sort().join(',')
          isDuplicate = newIds === oldIds
          break
        }
      }
      if (isDuplicate) {
        return `已存在相同的「${ruleTypeMap[ruleType]}」规则，请勿重复添加`
      }
    }

    // 2.2 exclude_shift 与 include_shift 互斥冲突
    if (ruleType === 'exclude_shift' && existing.rule_type === 'include_shift') {
      const excluded = newParams.exclude_shift_ids || []
      const included = eParams.include_shift_ids || []
      const overlap = excluded.filter((id: number) => included.includes(id))
      if (overlap.length > 0) {
        const names = overlap.map((id: number) => shiftNameMap.value[id] || `ID:${id}`)
        return `排除的班次「${names.join('、')}」与已有的「仅排某班次」规则冲突：这些班次是唯一允许排班的，不能排除`
      }
    }

    if (ruleType === 'include_shift' && existing.rule_type === 'exclude_shift') {
      const included = newParams.include_shift_ids || []
      const excluded = eParams.exclude_shift_ids || []
      const overlap = included.filter((id: number) => excluded.includes(id))
      if (overlap.length > 0) {
        const names = overlap.map((id: number) => shiftNameMap.value[id] || `ID:${id}`)
        return `仅排的班次「${names.join('、')}」与已有的「排除某班次」规则冲突：这些班次已被排除，不能作为仅排班次`
      }
    }

    // 2.3 include_shift 排除了所有可用班次
    if (ruleType === 'exclude_shift' && existing.rule_type === 'include_shift') {
      const excluded = newParams.exclude_shift_ids || []
      const included = eParams.include_shift_ids || []
      const remaining = included.filter((id: number) => !excluded.includes(id))
      if (remaining.length === 0) {
        return `排除这些班次后，「仅排某班次」规则中已无可用班次，会导致该人员无法排班`
      }
    }

    if (ruleType === 'include_shift' && existing.rule_type === 'exclude_shift') {
      const included = newParams.include_shift_ids || []
      const excluded = eParams.exclude_shift_ids || []
      const remaining = included.filter((id: number) => !excluded.includes(id))
      if (remaining.length === 0) {
        return `选择的班次全部被「排除某班次」规则排除，会导致该人员无法排班`
      }
    }

    // 2.4 exclude_weekday 与 exclude_shift 重叠提示
    if (ruleType === 'exclude_weekday' && existing.rule_type === 'exclude_shift') {
      const weekdayShifts = newParams.exclude_shift_ids || []
      const fullExcluded = eParams.exclude_shift_ids || []
      const overlap = weekdayShifts.filter((id: number) => fullExcluded.includes(id))
      if (overlap.length > 0) {
        const names = overlap.map((id: number) => shiftNameMap.value[id] || `ID:${id}`)
        return `班次「${names.join('、')}」已被「排除某班次」规则完全排除，无需再设置星期排除`
      }
    }
  }

  return null  // 校验通过
}

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  // 业务规则校验
  const errorMsg = validateRule()
  if (errorMsg) {
    ElMessage.warning(errorMsg)
    return
  }

  saving.value = true
  try {
    const payload = {
      staff_id: props.staffId!,
      rule_type: formData.value.rule_type,
      params: buildParams(),
      effective_from: dateRangeValue.value ? dateRangeValue.value[0] : null,
      effective_to: dateRangeValue.value ? dateRangeValue.value[1] : null,
      reason: formData.value.reason || null,
    }

    if (isEdit.value && editingId.value) {
      await updateSpecialRule(editingId.value, payload)
      ElMessage.success('修改成功')
    } else {
      await createSpecialRule(payload)
      ElMessage.success('创建成功')
    }

    formVisible.value = false
    await loadList()
    emit('saved')
  } catch (e) {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

// ==================== 删除 ====================

async function handleDelete(rule: SpecialRule) {
  try {
    await ElMessageBox({
      title: '确认删除？',
      message: '删除后数据无法恢复，请慎重操作。',
      showCancelButton: true,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteSpecialRule(rule.id)
    ElMessage.success('删除成功')
    await loadList()
    emit('saved')
  } catch (e) {
    // user cancel or error
  }
}

function handleClose() {
  visible.value = false
}

// ==================== 打开时加载数据 ====================

watch(visible, (val) => {
  if (val && props.staffId) {
    loadList()
    loadShiftTemplates()
    loadStaffList()
  }
})
</script>

<style scoped>
.drawer-body {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.drawer-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.rule-list {
  flex: 1;
  overflow-y: auto;
}

.rule-card {
  border: 1px solid #E6EAF0;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
}

.rule-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.rule-card-actions {
  display: flex;
  gap: 4px;
}

.rule-detail {
  font-size: 13px;
  color: #1F2D3D;
  margin-bottom: 4px;
}

.rule-validity {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.rule-reason {
  font-size: 12px;
  color: #909399;
}
</style>
