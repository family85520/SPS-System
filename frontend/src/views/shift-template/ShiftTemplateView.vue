<template>
  <div class="shift-template-page">
    <!-- 左侧面板：模板列表 -->
    <div class="left-panel">
      <div class="panel-header">
        <el-input
          v-model="keyword"
          placeholder="搜索班次模板"
          clearable
          prefix-icon="Search"
        />
        <!-- 新建模板：需要 shift_template create 权限 -->
        <el-button
          v-if="authStore.hasPermission('shift_template', 'create')"
          type="primary"
          @click="handleCreate"
          style="margin-top: 8px; width: 100%"
        >
          <el-icon><Plus /></el-icon>
          新建模板
        </el-button>
      </div>

      <div class="template-list" v-loading="loading">
        <div
          v-for="item in filteredList"
          :key="item.id"
          class="template-item"
          :class="{ active: selectedId === item.id, disabled: item.status === 0 }"
          @click="handleSelect(item)"
        >
          <div class="template-item-header">
            <span class="color-dot" :style="{ background: item.color }"></span>
            <span class="template-name">{{ item.name }}</span>
            <el-tag size="small" :type="item.status === 1 ? 'success' : 'info'">
              {{ item.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </div>
          <div class="template-item-time">
            {{ item.start_time }} - {{ item.end_time }}
            <span class="duration">{{ item.duration_hours }}h</span>
          </div>
          <div class="template-item-days">
            <span
              v-for="d in 7"
              :key="d"
              class="day-tag"
              :class="{ active: item.apply_days.includes(d) }"
            >
              {{ dayLabels[d - 1] }}
            </span>
          </div>
        </div>

        <el-empty v-if="!loading && filteredList.length === 0" description="暂无班次模板" />
      </div>
    </div>

    <!-- 右侧面板：编辑表单 -->
    <div class="right-panel">
      <template v-if="selectedId !== null && formData">
        <div class="panel-header">
          <h3>{{ isCreate ? '新建班次模板' : '编辑班次模板' }}</h3>
        </div>

        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-width="120px"
          label-position="right"
          class="edit-form"
          v-loading="saving"
        >
          <el-form-item label="班次名称" prop="name">
            <el-input
              v-model="formData.name"
              placeholder="请输入班次名称"
              maxlength="50"
              show-word-limit
              :disabled="!canEdit"
            />
          </el-form-item>

          <el-form-item label="起始时间" prop="start_time">
            <el-time-select
              v-model="formData.start_time"
              start="00:00"
              step="00:30"
              end="23:30"
              placeholder="选择起始时间"
              style="width: 100%"
              :disabled="!canEdit"
            />
          </el-form-item>

          <el-form-item label="结束时间" prop="end_time">
            <el-time-select
              v-model="formData.end_time"
              start="00:00"
              step="00:30"
              end="23:30"
              placeholder="选择结束时间"
              style="width: 100%"
              :disabled="!canEdit"
            />
          </el-form-item>

          <el-form-item label="班次时长">
            <el-input :model-value="computedDuration" disabled>
              <template #suffix>小时</template>
            </el-input>
            <div v-if="isCrossNight" class="cross-night-tip">
              <el-icon color="#FFC107"><WarningFilled /></el-icon>
              跨夜班，时长自动计算
            </div>
          </el-form-item>

          <el-form-item label="颜色标识" prop="color">
            <div class="color-picker-wrapper">
              <el-color-picker v-model="formData.color" :predefine="presetColors" :disabled="!canEdit" />
              <span class="color-preview" :style="{ background: formData.color }">
                {{ formData.color }}
              </span>
            </div>
          </el-form-item>

          <el-divider content-position="left">值班领导组</el-divider>

          <el-form-item label="启用领导组">
            <el-switch v-model="formData.leader_enabled" :disabled="!canEdit" />
            <div class="cross-night-tip">关闭后自动排班不分配值班领导；打开后优先级：候选池 > "带班领导"身份标识 > 空缺</div>
          </el-form-item>

          <template v-if="formData.leader_enabled">
            <el-form-item label="最少人数" prop="leader_min">
              <el-input-number v-model="formData.leader_min" :min="0" :max="99" controls-position="right" :disabled="!canEdit" />
            </el-form-item>

            <el-form-item label="最多人数" prop="leader_max">
              <el-input-number v-model="formData.leader_max" :min="formData.leader_min" :max="99" controls-position="right" :disabled="!canEdit" />
            </el-form-item>

            <el-form-item label="每次选出人数">
              <el-input-number v-model="formData.leader_count" :min="1" :max="formData.leader_max || 99" controls-position="right" :disabled="!canEdit" />
              <div class="cross-night-tip">独立于最少/最多人数，控制每次轮换实际选出的领导数</div>
            </el-form-item>

            <el-form-item label="独立轮换频次">
              <el-select v-model="formData.leader_rotation_frequency" style="width: 100%" :disabled="!canEdit">
                <el-option label="按天轮换" value="day" />
                <el-option label="按周轮换" value="week" />
                <el-option label="按月轮换" value="month" />
              </el-select>
              <div class="cross-night-tip">领导组轮换周期，默认按周轮换</div>
            </el-form-item>
            <el-form-item label="候选人员">
              <el-select
                v-model="formData.leader_pool"
                multiple
                filterable
                placeholder="选择领导候选人员（最高优先级）"
                style="width: 100%"
                :disabled="!canEdit"
              >
                <el-option
                  v-for="s in staffList"
                  :key="s.id"
                  :label="s.name"
                  :value="s.id"
                >
                  <span style="float: left">{{ s.name }}</span>
                  <span style="float: right; color: #909399; font-size: 12px">{{ s.employee_no }}</span>
                </el-option>
              </el-select>
              <div class="cross-night-tip">优先级1：候选池 → 优先级2：标识"领导/带班" → 优先级3：空着不选</div>
            </el-form-item>

            <el-form-item label="标识回退">
              <el-switch v-model="formData.leader_use_tag" :disabled="!canEdit" />
              <div class="cross-night-tip">候选池为空时，是否回退到指定身份标识的人员</div>
            </el-form-item>

            <el-form-item label="标识名称" v-if="formData.leader_use_tag">
              <el-input v-model="formData.leader_tag_name" placeholder="领导" style="width: 200px" :disabled="!canEdit" />
              <div class="cross-night-tip">候选池为空时，用此标识名匹配人员（默认"领导"，可自定义）</div>
            </el-form-item>
          </template>

          <el-divider content-position="left">值班人员组</el-divider>

          <el-form-item label="启用人员组">
            <el-switch v-model="formData.member_enabled" :disabled="!canEdit" />
            <div class="cross-night-tip">关闭后自动排班不会分配值班人员（仅特殊人员+领导）</div>
          </el-form-item>

          <template v-if="formData.member_enabled">
            <el-form-item label="最少人数" prop="member_min">
              <el-input-number v-model="formData.member_min" :min="1" :max="99" controls-position="right" :disabled="!canEdit" />
            </el-form-item>

            <el-form-item label="最多人数" prop="member_max">
              <el-input-number v-model="formData.member_max" :min="formData.member_min" :max="99" controls-position="right" :disabled="!canEdit" />
            </el-form-item>

            <el-form-item label="轮换频次">
              <el-select v-model="formData.member_rotation_frequency" style="width: 100%" :disabled="!canEdit">
                <el-option label="按天轮换" value="day" />
                <el-option label="按周轮换" value="week" />
                <el-option label="按月轮换" value="month" />
              </el-select>
              <div class="cross-night-tip">值班人员组的轮换周期，默认按天轮换</div>
            </el-form-item>

            <el-form-item label="跨模板共排">
              <el-switch v-model="formData.allow_multi_template" :disabled="!canEdit" />
              <div class="cross-night-tip">开启后本模板人员当天可同时参与其他模板的班次</div>
            </el-form-item>
          </template>

          <el-divider content-position="left">特殊人员组（可选）</el-divider>

          <el-form-item label="启用特殊人员">
            <el-switch v-model="formData.special_enabled" :disabled="!canEdit" />
            <div class="cross-night-tip">开启后从候选池中按轮换频次选人，优先级最高</div>
          </el-form-item>

          <template v-if="formData.special_enabled">
            <el-form-item label="候选人员" prop="special_pool">
              <el-select
                v-model="formData.special_pool"
                multiple
                filterable
                placeholder="选择特殊人员候选池"
                style="width: 100%"
                :disabled="!canEdit"
              >
                <el-option
                  v-for="s in staffList"
                  :key="s.id"
                  :label="s.name"
                  :value="s.id"
                >
                  <span style="float: left">{{ s.name }}</span>
                  <span style="float: right; color: #909399; font-size: 12px">{{ s.employee_no }}</span>
                </el-option>
              </el-select>
              <div class="cross-night-tip">例如：行政值班中固定轮换的2名特殊人员</div>
            </el-form-item>

            <el-form-item label="每次选出人数">
              <el-input-number v-model="formData.special_count" :min="1" :max="(formData.special_pool || []).length || 1" controls-position="right" :disabled="!canEdit" />
            </el-form-item>

            <el-form-item label="轮换频次">
              <el-select v-model="formData.special_rotation_frequency" style="width: 100%" :disabled="!canEdit">
                <el-option label="按天轮换" value="day" />
                <el-option label="按周轮换" value="week" />
                <el-option label="按月轮换" value="month" />
              </el-select>
              <div class="cross-night-tip">例如按月轮换：5月A、6月B、7月A、8月B...</div>
            </el-form-item>

            <el-form-item label="从人员池排除">
              <el-switch v-model="formData.special_exclude_from_member" :disabled="!canEdit" />
              <div class="cross-night-tip">开启后特殊人员不会被选入值班人员组（推荐开启）</div>
            </el-form-item>
          </template>

          <el-divider content-position="left">约束规则（可选）</el-divider>

          <el-form-item label="指定约束规则">
            <el-select
              v-model="formData.constraint_ids"
              multiple
              filterable
              placeholder="留空则使用全部已启用规则"
              style="width: 100%"
              :disabled="!canEdit"
            >
              <el-option
                v-for="c in constraintList"
                :key="c.id"
                :label="c.rule_name"
                :value="c.id"
              />
            </el-select>
            <div class="cross-night-tip">指定后自动排班仅使用选中的约束规则，留空则使用所有已启用规则</div>
          </el-form-item>

          <el-divider content-position="left">适用日期</el-divider>

          <el-form-item label="适用日期" prop="apply_days">
            <el-checkbox-group v-model="formData.apply_days" :disabled="!canEdit">
              <el-checkbox-button v-for="(label, idx) in dayLabels" :key="idx" :value="idx + 1">
                {{ label }}
              </el-checkbox-button>
            </el-checkbox-group>
          </el-form-item>

          <!-- 启用状态：需要 shift_template update 权限 -->
          <el-form-item v-if="!isCreate" label="启用状态">
            <el-switch
              v-if="authStore.hasPermission('shift_template', 'update')"
              :model-value="currentStatus === 1"
              active-text="启用"
              inactive-text="停用"
              @change="handleToggleStatus"
            />
            <el-tag v-else :type="currentStatus === 1 ? 'success' : 'info'" size="small">
              {{ currentStatus === 1 ? '启用' : '停用' }}
            </el-tag>
          </el-form-item>

          <el-form-item>
            <div class="form-actions">
              <!-- 保存：新建需要 create，编辑需要 update -->
              <el-button
                v-if="authStore.hasPermission('shift_template', isCreate ? 'create' : 'update')"
                type="primary"
                @click="handleSave"
              >
                保存
              </el-button>
              <!-- 复制：需要 shift_template create 权限 -->
              <el-button
                v-if="!isCreate && authStore.hasPermission('shift_template', 'create')"
                @click="handleCopy"
              >
                复制
              </el-button>
              <!-- 删除：需要 shift_template delete 权限 -->
              <el-button
                v-if="!isCreate && authStore.hasPermission('shift_template', 'delete')"
                type="danger"
                @click="handleDelete"
              >
                删除
              </el-button>
              <el-button @click="handleCancel">取消</el-button>
            </div>
          </el-form-item>
        </el-form>
      </template>

      <div v-else class="empty-state">
        <el-icon :size="48" color="#C0C4CC"><Document /></el-icon>
        <p>请从左侧选择模板或点击"新建模板"</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, WarningFilled, Document } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/index'
import {
  getShiftTemplates,
  createShiftTemplate,
  updateShiftTemplate,
  deleteShiftTemplate,
  copyShiftTemplate,
  toggleShiftTemplateStatus,
  type ShiftTemplate,
  type ShiftTemplateForm,
} from '@/api/shift-template'

const authStore = useAuthStore()

// 编辑权限计算属性：新建时需要 create，编辑时需要 update
const canEdit = computed(() => {
  if (isCreate.value) return authStore.hasPermission('shift_template', 'create')
  return authStore.hasPermission('shift_template', 'update')
})

// ==================== 值班组 ====================

interface DutyTeamForm {
  id?: number
  shift_template_id?: number
  name: string
  staff_ids: number[]
  priority: number
  enabled: boolean
}

const dutyTeams = ref<DutyTeamForm[]>([])

function addDutyTeam() {
  dutyTeams.value.push({
    name: '',
    staff_ids: [],
    priority: (dutyTeams.value.length + 1) * 10,
    enabled: true,
  })
}

async function loadDutyTeams(templateId: number) {
  try {
    const res = await api.get(`/shift-templates/${templateId}/duty-teams`)
    dutyTeams.value = Array.isArray(res) ? res : []
  } catch {
    dutyTeams.value = []
  }
}

async function saveDutyTeams(templateId: number) {
  const serverRes = await api.get(`/shift-templates/${templateId}/duty-teams`)
  const serverIds = (Array.isArray(serverRes) ? serverRes : []).map((t: any) => t.id)
  const frontendIds = dutyTeams.value.filter(t => t.id).map(t => t.id)

  for (const sid of serverIds) {
    if (!frontendIds.includes(sid)) {
      await api.delete(`/shift-templates/${templateId}/duty-teams/${sid}`)
    }
  }

  for (const team of dutyTeams.value) {
    const payload = {
      name: team.name,
      staff_ids: team.staff_ids,
      priority: team.priority,
      enabled: team.enabled,
    }
    if (team.id) {
      await api.put(`/shift-templates/${templateId}/duty-teams/${team.id}`, payload)
    } else {
      await api.post(`/shift-templates/${templateId}/duty-teams`, payload)
    }
  }
}

const staffList = ref<any[]>([])
const constraintList = ref<any[]>([])

async function loadConstraintList() {
  try {
    const res: any = await api.get('/constraints')
    const list = Array.isArray(res) ? res : (res.items || res.data || [])
    constraintList.value = list.filter((c: any) => c.enabled)
  } catch {
    constraintList.value = []
  }
}

const dayLabels = ['一', '二', '三', '四', '五', '六', '日']

const presetColors = [
  '#FFD166', '#06D6A0', '#118AB2', '#F08A5D',
  '#EF476F', '#7B68EE', '#20B2AA', '#FF6347',
]

const loading = ref(false)
const templateList = ref<ShiftTemplate[]>([])
const keyword = ref('')
const selectedId = ref<number | null>(null)
const isCreate = ref(false)

const saving = ref(false)
const formRef = ref<FormInstance>()
const currentStatus = ref(1)

const defaultForm: ShiftTemplateForm = {
  name: '',
  org_id: null,
  start_time: '08:00',
  end_time: '16:00',
  color: '#FFD166',
  leader_min: 0,
  leader_max: 1,
  leader_pool: null,
  member_min: 1,
  member_max: 2,
  apply_days: [1, 2, 3, 4, 5],
  allow_multi_template: false,
  leader_enabled: false,
  leader_rotation_frequency: 'week',
  leader_count: 1,
  leader_use_tag: true,
  leader_tag_name: null as string | null,
  member_enabled: true,
  member_rotation_frequency: 'day',
  special_enabled: false,
  special_rotation_frequency: 'month',
  special_count: 1,
  special_pool: null,
  special_exclude_from_member: true,
  constraint_ids: null,
}

const formData = ref<ShiftTemplateForm>({ ...defaultForm })

const filteredList = computed(() => {
  if (!keyword.value) return templateList.value
  return templateList.value.filter((t) => t.name.includes(keyword.value))
})

const computedDuration = computed(() => {
  if (!formData.value.start_time || !formData.value.end_time) return '-'
  const [sh, sm] = formData.value.start_time.split(':').map(Number)
  const [eh, em] = formData.value.end_time.split(':').map(Number)
  let startMin = sh * 60 + sm
  let endMin = eh * 60 + em
  if (endMin <= startMin) endMin += 24 * 60
  return ((endMin - startMin) / 60).toFixed(1)
})

const isCrossNight = computed(() => {
  if (!formData.value.start_time || !formData.value.end_time) return false
  const [sh, sm] = formData.value.start_time.split(':').map(Number)
  const [eh, em] = formData.value.end_time.split(':').map(Number)
  return eh * 60 + em <= sh * 60 + sm
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入班次名称', trigger: 'blur' },
    { max: 50, message: '班次名称不能超过50个字符', trigger: 'blur' },
  ],
  start_time: [{ required: true, message: '请选择起始时间', trigger: 'change' }],
  end_time: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
  color: [{ required: true, message: '请选择颜色', trigger: 'change' }],
  leader_min: [{ required: true, message: '请设置最少人数', trigger: 'change' }],
  leader_max: [{ required: true, message: '请设置最多人数', trigger: 'change' }],
  member_min: [{ required: true, message: '请设置最少人数', trigger: 'change' }],
  member_max: [{ required: true, message: '请设置最多人数', trigger: 'change' }],
  apply_days: [
    { type: 'array', required: true, min: 1, message: '请至少选择一天', trigger: 'change' },
  ],
}

async function loadStaffList() {
  try {
    const res: any = await api.get('/staffs/options')
    const list = Array.isArray(res) ? res : (res.data || [])
    staffList.value = list
  } catch (e) {
    staffList.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    templateList.value = await getShiftTemplates()
  } catch (e) {
    // interceptor handles error
  } finally {
    loading.value = false
  }
}

function handleSelect(item: ShiftTemplate) {
  isCreate.value = false
  selectedId.value = item.id
  currentStatus.value = item.status
  formData.value = {
    name: item.name,
    org_id: item.org_id,
    start_time: item.start_time,
    end_time: item.end_time,
    color: item.color,
    leader_min: item.leader_min,
    leader_max: item.leader_max,
    leader_pool: item.leader_pool,
    member_min: item.member_min,
    member_max: item.member_max,
    apply_days: [...item.apply_days],
    allow_multi_template: (item as any).allow_multi_template ?? false,
    leader_enabled: (item as any).leader_enabled ?? false,
    leader_rotation_frequency: (item as any).leader_rotation_frequency ?? 'week',
    leader_count: (item as any).leader_count ?? 1,
    leader_use_tag: (item as any).leader_use_tag ?? true,
    leader_tag_name: (item as any).leader_tag_name ?? null,
    member_enabled: (item as any).member_enabled ?? true,
    member_rotation_frequency: (item as any).member_rotation_frequency ?? 'day',
    special_enabled: (item as any).special_enabled ?? false,
    special_rotation_frequency: (item as any).special_rotation_frequency ?? 'month',
    special_count: (item as any).special_count ?? 1,
    special_pool: (item as any).special_pool ?? null,
    special_exclude_from_member: (item as any).special_exclude_from_member ?? true,
    constraint_ids: (item as any).constraint_ids ?? null,
  }
  loadDutyTeams(item.id)
}

function handleCreate() {
  isCreate.value = true
  selectedId.value = -1
  currentStatus.value = 1
  formData.value = { ...defaultForm, apply_days: [...defaultForm.apply_days] }
  dutyTeams.value = []
}

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isCreate.value) {
      const created = await createShiftTemplate(formData.value)
      if (created && created.id) {
        if (dutyTeams.value.length > 0) await saveDutyTeams(created.id)
      }
      ElMessage.success('创建成功')
      await loadList()
      handleSelect(created)
      isCreate.value = false
    } else {
      const updated = await updateShiftTemplate(selectedId.value!, formData.value)
      await saveDutyTeams(selectedId.value!)
      ElMessage.success('保存成功')
      await loadList()
      handleSelect(updated)
    }
  } catch (e) {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

async function handleCopy() {
  if (!selectedId.value) return
  saving.value = true
  try {
    const copied = await copyShiftTemplate(selectedId.value)
    ElMessage.success('复制成功')
    await loadList()
    handleSelect(copied)
  } catch (e) {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!selectedId.value) return
  try {
    await ElMessageBox({
      title: '确认删除？',
      message: '删除后数据无法恢复，请慎重操作。',
      showCancelButton: true,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteShiftTemplate(selectedId.value)
    ElMessage.success('删除成功')
    selectedId.value = null
    await loadList()
  } catch (e) {
    // 用户取消或接口错误
  }
}

async function handleToggleStatus(val: boolean) {
  if (!selectedId.value) return
  const tip = val ? '确认启用该班次模板？' : '停用后该班次不参与自动排班，确认停用？'
  try {
    await ElMessageBox({
      title: '确认操作？',
      message: tip,
      showCancelButton: true,
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const updated = await toggleShiftTemplateStatus(selectedId.value)
    currentStatus.value = updated.status
    ElMessage.success(updated.status === 1 ? '已启用' : '已停用')
    await loadList()
    handleSelect(updated)
  } catch (e) {
    // 用户取消或接口错误
  }
}

function handleCancel() {
  selectedId.value = null
}

onMounted(() => {
  loadList()
  loadStaffList()
  loadConstraintList()
})
</script>

<style scoped>
.shift-template-page {
  display: flex;
  height: calc(100vh - 56px - 40px);
  gap: 16px;
  padding: 16px;
  background: #F5F7FA;
  overflow-x: auto;
  min-width: 700px;
}

.left-panel {
  width: 320px;
  min-width: 280px;
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
}

.template-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.template-item {
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
  border: 2px solid transparent;
}

.template-item:hover {
  background: #F5F7FA;
}

.template-item.active {
  background: #ECF5FF;
  border-color: #0A63D8;
}

.template-item.disabled {
  opacity: 0.55;
}

.template-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}

.template-name {
  font-size: 14px;
  font-weight: 600;
  color: #1F2D3D;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-item-time {
  font-size: 12px;
  color: #556173;
  margin-bottom: 6px;
  padding-left: 20px;
}

.template-item-time .duration {
  margin-left: 8px;
  background: #F0F2F5;
  padding: 0 6px;
  border-radius: 3px;
  font-size: 11px;
}

.template-item-days {
  display: flex;
  gap: 4px;
  padding-left: 20px;
}

.day-tag {
  width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  border-radius: 3px;
  font-size: 11px;
  color: #C0C4CC;
  background: #F5F7FA;
}

.day-tag.active {
  background: #0A63D8;
  color: #FFFFFF;
}

.right-panel {
  flex: 1;
  min-width: 400px;
  background: #FFFFFF;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(31, 45, 61, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel .panel-header {
  padding: 16px 24px;
}

.right-panel .panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1F2D3D;
}

.edit-form {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px 24px;
}

.color-picker-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.color-preview {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  color: #FFFFFF;
}

.cross-night-tip {
  font-size: 12px;
  color: #E6A23C;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
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

.rotation-group-item {
  border: 1px solid #EBEEF5;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
  background: #FAFBFC;
}

.rotation-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.rotation-group-body {
  margin-top: 4px;
}
</style>
