<template>
  <div class="constraint-page">
    <!-- 左侧：规则列表 -->
    <div class="left-panel">
      <div class="panel-header">
        <h3>约束规则</h3>
        <el-button type="primary" size="small" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建规则
        </el-button>
      </div>

      <div class="rule-list" v-loading="loading">
        <div
          v-for="item in ruleList"
          :key="item.id"
          class="rule-item"
          :class="{ active: selectedId === item.id, disabled: !item.enabled, preset: isPreset(item.rule_type) }"
          @click="handleSelect(item)"
        >
          <div class="rule-item-header">
            <span class="priority-badge">{{ item.priority }}</span>
            <span class="rule-name">{{ item.rule_name }}</span>
            <el-tag v-if="item.is_preset" size="small" type="info">预置</el-tag>
            <el-switch
              :model-value="item.enabled"
              size="small"
              inline-prompt
              active-text=""
              inactive-text=""
              @click.stop
              @change="handleToggle(item)"
            />
          </div>
        </div>

        <el-empty v-if="!loading && ruleList.length === 0" description="暂无约束规则" />
      </div>
    </div>

    <!-- 右侧：规则详情编辑 -->
    <div class="right-panel">
      <template v-if="selectedId !== null && formData">
        <div class="panel-header">
          <h3>{{ isCreate ? '新建自定义规则' : (isPreset(formData.rule_type) ? '编辑预置规则' : '编辑自定义规则') }}</h3>
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
            />
          </el-form-item>

          <el-form-item v-if="isCreate" label="规则类型" prop="rule_type">
            <el-select v-model="formData.rule_type" placeholder="请选择规则类型" style="width: 100%" @change="handleTypeChange">
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
            <el-switch v-model="formData.enabled" active-text="启用" inactive-text="停用" />
          </el-form-item>

          <el-form-item label="优先级" prop="priority">
            <el-input-number v-model="formData.priority" :min="1" :max="999" controls-position="right" />
            <span class="priority-tip">数字越小越优先</span>
          </el-form-item>

          <el-form-item label="适用范围" prop="scope_type">
            <el-radio-group v-model="formData.scope_type">
              <el-radio value="all">全部组织</el-radio>
              <el-radio value="org">指定组织</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="formData.scope_type === 'org'" label="指定组织">
            <el-input v-model="formData.scope_ids" placeholder="输入组织ID，逗号分隔" />
          </el-form-item>

          <el-divider content-position="left">规则参数</el-divider>

          <!-- 连续工作上限 -->
          <template v-if="formData.rule_type === 'MAX_CONTINUOUS_DAYS'">
            <el-form-item label="最多连续上班天数">
              <el-input-number v-model="formData.params.max_days" :min="1" :max="30" controls-position="right" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 连续工作后最少休息 -->
          <template v-if="formData.rule_type === 'MIN_REST_AFTER_CONTINUOUS'">
            <el-form-item label="最少休息天数">
              <el-input-number v-model="formData.params.rest_days" :min="1" :max="14" controls-position="right" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 班次最少间隔 -->
          <template v-if="formData.rule_type === 'MIN_SHIFT_INTERVAL'">
            <el-form-item label="最少间隔小时数">
              <el-input-number v-model="formData.params.hours" :min="1" :max="48" controls-position="right" />
              <span class="param-unit">小时</span>
            </el-form-item>
          </template>

          <!-- 夜班后最少休息 -->
          <template v-if="formData.rule_type === 'MIN_REST_AFTER_NIGHT'">
            <el-form-item label="最少休息小时数">
              <el-input-number v-model="formData.params.hours" :min="1" :max="72" controls-position="right" />
              <span class="param-unit">小时</span>
            </el-form-item>
          </template>

          <!-- 每天最多上班数 -->
          <template v-if="formData.rule_type === 'MAX_SHIFTS_PER_DAY'">
            <el-form-item label="每天最多排几个班">
              <el-input-number v-model="formData.params.count" :min="1" :max="5" controls-position="right" />
              <span class="param-unit">个</span>
            </el-form-item>
          </template>

          <!-- 每周最多工作时长 -->
          <template v-if="formData.rule_type === 'MAX_WEEKLY_HOURS'">
            <el-form-item label="每周累计小时上限">
              <el-input-number v-model="formData.params.hours" :min="1" :max="168" controls-position="right" />
              <span class="param-unit">小时</span>
            </el-form-item>
          </template>

          <!-- 节假日模式 -->
          <template v-if="formData.rule_type === 'HOLIDAY_MODE'">
            <el-form-item label="节假日排班模式">
              <el-radio-group v-model="formData.params.mode">
                <el-radio value="normal">正常轮转</el-radio>
                <el-radio value="special">特殊安排</el-radio>
              </el-radio-group>
            </el-form-item>
          </template>

          <!-- 周末差异化 -->
          <template v-if="formData.rule_type === 'WEEKEND_DIFF'">
            <el-form-item label="启用周末差异化">
              <el-switch v-model="formData.params.enabled" active-text="启用" inactive-text="禁用" />
            </el-form-item>
          </template>

          <!-- 连续夜班上限 -->
          <template v-if="formData.rule_type === 'MAX_CONSECUTIVE_NIGHTS'">
            <el-form-item label="最多连续夜班天数">
              <el-input-number v-model="formData.params.max_days" :min="1" :max="14" controls-position="right" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 夜班之间最少间隔 -->
          <template v-if="formData.rule_type === 'MIN_INTERVAL_BETWEEN_NIGHTS'">
            <el-form-item label="夜班之间最少间隔">
              <el-input-number v-model="formData.params.days" :min="1" :max="14" controls-position="right" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 每月最多夜班次数 -->
          <template v-if="formData.rule_type === 'MAX_NIGHTS_PER_MONTH'">
            <el-form-item label="每月最多夜班次数">
              <el-input-number v-model="formData.params.count" :min="1" :max="31" controls-position="right" />
              <span class="param-unit">次</span>
            </el-form-item>
          </template>

          <!-- 工作量均衡分配 -->
          <template v-if="formData.rule_type === 'EQUAL_DISTRIBUTION'">
            <el-form-item label="启用工作量均衡">
              <el-switch v-model="formData.params.enabled" active-text="启用" inactive-text="禁用" />
            </el-form-item>
            <el-form-item v-if="formData.params.enabled" label="允许偏差天数">
              <el-input-number v-model="formData.params.tolerance_days" :min="0" :max="10" controls-position="right" />
              <span class="param-unit">天</span>
            </el-form-item>
          </template>

          <!-- 值班领导轮换均衡 -->
          <template v-if="formData.rule_type === 'LEADER_ROTATION'">
            <el-form-item label="启用领导轮换均衡">
              <el-switch v-model="formData.params.enabled" active-text="启用" inactive-text="禁用" />
            </el-form-item>
          </template>

          <!-- 周末轮转均衡 -->
          <template v-if="formData.rule_type === 'WEEKEND_ROTATION'">
            <el-form-item label="启用周末轮转均衡">
              <el-switch v-model="formData.params.enabled" active-text="启用" inactive-text="禁用" />
            </el-form-item>
            <el-form-item v-if="formData.params.enabled" label="每人每月最少周末班次">
              <el-input-number v-model="formData.params.min_times_per_month" :min="1" :max="10" controls-position="right" />
              <span class="param-unit">次</span>
            </el-form-item>
          </template>

          <!-- 新员工搭配老员工 -->
          <template v-if="formData.rule_type === 'NEW_STAFF_PAIRING'">
            <el-form-item label="启用新员工搭配">
              <el-switch v-model="formData.params.enabled" active-text="启用" inactive-text="禁用" />
            </el-form-item>
          </template>

          <el-form-item>
            <div class="form-actions">
              <el-button type="primary" @click="handleSave">保存</el-button>
              <el-button v-if="!isCreate && canDelete" type="danger" @click="handleDelete">删除</el-button>
              <el-button @click="handleCancel">取消</el-button>
            </div>
          </el-form-item>
        </el-form>
      </template>

      <div v-else class="empty-state">
        <el-icon :size="48" color="#C0C4CC"><Setting /></el-icon>
        <p>请从左侧选择规则或点击"新建规则"</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Setting } from '@element-plus/icons-vue'
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
  // 基础工时约束
  { value: 'MAX_CONTINUOUS_DAYS', label: '连续工作上限' },
  { value: 'MIN_REST_AFTER_CONTINUOUS', label: '连续工作后最少休息' },
  { value: 'MIN_SHIFT_INTERVAL', label: '班次最少间隔' },
  { value: 'MAX_SHIFTS_PER_DAY', label: '每天最多上班数' },
  { value: 'MAX_WEEKLY_HOURS', label: '每周最多工作时长' },
  // 夜班约束
  { value: 'MIN_REST_AFTER_NIGHT', label: '夜班后最少休息' },
  { value: 'MAX_CONSECUTIVE_NIGHTS', label: '连续夜班上限' },
  { value: 'MIN_INTERVAL_BETWEEN_NIGHTS', label: '夜班之间最少间隔天数' },
  { value: 'MAX_NIGHTS_PER_MONTH', label: '每月最多夜班次数' },
  // 均衡轮转
  { value: 'EQUAL_DISTRIBUTION', label: '工作量均衡分配' },
  { value: 'LEADER_ROTATION', label: '值班领导轮换均衡' },
  { value: 'WEEKEND_ROTATION', label: '周末轮转均衡' },
  // 节假日与周末
  { value: 'HOLIDAY_MODE', label: '节假日排班模式' },
  { value: 'WEEKEND_DIFF', label: '周末差异化' },
  // 特殊约束
  { value: 'NEW_STAFF_PAIRING', label: '新员工必须搭配老员工' },
]

function isPreset(ruleType: string): boolean {
  return presetRuleTypes.has(ruleType)
}

const canDelete = computed(() => {
  // 全局预置规则不可删除
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
  scope_ids: any
  enabled: boolean
  is_preset: boolean
}>({
  rule_type: '',
  rule_name: '',
  params: {},
  priority: 1,
  scope_type: 'all',
  scope_ids: null,
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

// 加载列表
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

// 选择规则
function handleSelect(item: Constraint) {
  isCreate.value = false
  selectedId.value = item.id
  formData.value = {
    id: item.id,
    rule_type: item.rule_type,
    rule_name: item.rule_name,
    params: { ...item.params },
    priority: item.priority,
    scope_type: item.scope_type,
    scope_ids: item.scope_ids,
    enabled: item.enabled,
    is_preset: item.is_preset,
  }
}

// 新建规则
function handleCreate() {
  isCreate.value = true
  selectedId.value = -1
  formData.value = {
    rule_type: 'MAX_CONTINUOUS_DAYS',
    rule_name: '连续工作上限',
    params: { max_days: 5 },
    priority: 0,
    scope_type: 'all',
    scope_ids: null,
    enabled: true,
    is_preset: false,
  }
}

function handleTypeChange(value: string) {
  formData.value.params = { ...defaultParams[value] }
}

// 保存
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
        scope_ids: formData.value.scope_type === 'org' ? String(formData.value.scope_ids).split(',').map(Number) : null,
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
        scope_ids: formData.value.scope_type === 'org' ? String(formData.value.scope_ids).split(',').map(Number) : null,
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

// 删除
async function handleDelete() {
  if (!formData.value.id) return
  try {
    await ElMessageBox({
      title: '确认删除？',
      message: '删除后数据无法恢复，请慎重操作。',
      showCancelButton: true,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteConstraint(formData.value.id)
    ElMessage.success('删除成功')
    selectedId.value = null
    await loadList()
  } catch (e) {
    // 用户取消或接口错误
  }
}

// 切换启用状态
async function handleToggle(item: Constraint) {
  try {
    await toggleConstraint(item.id)
    ElMessage.success(item.enabled ? '已禁用' : '已启用')
    await loadList()
    // 如果当前正在编辑该规则，刷新表单数据
    if (selectedId.value === item.id) {
      const updated = ruleList.value.find(r => r.id === item.id)
      if (updated) handleSelect(updated)
    }
  } catch (e) {
    // interceptor handles error
  }
}

// 取消
function handleCancel() {
  selectedId.value = null
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.constraint-page {
  display: flex;
  height: calc(100vh - 56px - 40px);
  gap: 16px;
  padding: 16px;
  background: #F5F7FA;
  overflow-x: auto;
  min-width: 700px;
}

/* 左侧列表 */
.left-panel {
  width: 340px;
  min-width: 300px;
  background: #FFFFFF;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(31, 45, 61, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #E6EAF0;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1F2D3D;
}

.rule-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.rule-item {
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
  border: 2px solid transparent;
}

.rule-item:hover {
  background: #F5F7FA;
}

.rule-item.active {
  background: #ECF5FF;
  border-color: #0A63D8;
}

.rule-item.disabled {
  opacity: 0.55;
}

.rule-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.priority-badge {
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  border-radius: 50%;
  background: #E6EAF0;
  color: #556173;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.rule-name {
  font-size: 14px;
  font-weight: 600;
  color: #1F2D3D;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 右侧编辑 */
.right-panel {
  flex: 1;
  background: #FFFFFF;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(31, 45, 61, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.edit-form {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px 24px;
}

.priority-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 12px;
}

.param-unit {
  font-size: 14px;
  color: #556173;
  margin-left: 8px;
}

.form-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #C0C4CC;
}

.empty-state p {
  margin-top: 16px;
  font-size: 14px;
}

.type-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
