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
        <el-button type="primary" @click="handleCreate" style="margin-top: 8px; width: 100%">
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
            <el-input v-model="formData.name" placeholder="请输入班次名称" maxlength="50" show-word-limit />
          </el-form-item>

          <el-form-item label="起始时间" prop="start_time">
            <el-time-select
              v-model="formData.start_time"
              start="00:00"
              step="00:30"
              end="23:30"
              placeholder="选择起始时间"
              style="width: 100%"
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
              <el-color-picker v-model="formData.color" :predefine="presetColors" />
              <span class="color-preview" :style="{ background: formData.color }">
                {{ formData.color }}
              </span>
            </div>
          </el-form-item>

          <el-divider content-position="left">值班领导</el-divider>

          <el-form-item label="最少人数" prop="leader_min">
            <el-input-number v-model="formData.leader_min" :min="0" :max="99" controls-position="right" />
          </el-form-item>

          <el-form-item label="最多人数" prop="leader_max">
            <el-input-number v-model="formData.leader_max" :min="formData.leader_min" :max="99" controls-position="right" />
          </el-form-item>

          <el-form-item label="候选人员">
            <el-select
              v-model="formData.leader_pool"
              multiple
              filterable
              placeholder="选择领导候选人员（留空则从全部人员中选）"
              style="width: 100%"
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
            <div class="cross-night-tip">不指定则自动排班时从带班领导标签或全部人员中选取</div>
          </el-form-item>

          <el-divider content-position="left">排班模式</el-divider>

          <el-form-item label="排班模式">
            <el-select v-model="formData.schedule_mode" style="width: 100%">
              <el-option label="逐人轮询（默认）" value="individual" />
              <el-option label="值班组轮换" value="team_rotation" />
              <el-option label="轮换组排班" value="rotation_group" />
            </el-select>
            <div class="cross-night-tip">
              <template v-if="formData.schedule_mode === 'individual'">每个人员独立排班，按排班次数均衡分配</template>
              <template v-if="formData.schedule_mode === 'team_rotation'">按值班组轮换，今天A组明天B组，适合白班夜班联动</template>
              <template v-if="formData.schedule_mode === 'rotation_group'">使用轮换组配置，适合行政班等固定人员按月轮换</template>
            </div>
          </el-form-item>

          <!-- 值班组配置（team_rotation 模式） -->
          <template v-if="formData.schedule_mode === 'team_rotation'">
            <el-divider content-position="left">值班组配置</el-divider>

            <el-form-item label="值班组">
              <div style="width: 100%;">
                <div v-for="(team, idx) in dutyTeams" :key="team.id || idx" class="rotation-group-item">
                  <div class="rotation-group-header">
                    <el-input v-model="team.name" placeholder="组名称（如：白班A组）" style="width: 200px" />
                    <el-input-number v-model="team.priority" :min="1" :max="100" controls-position="right" style="width: 90px" />
                    <el-switch v-model="team.enabled" />
                    <el-button type="danger" text @click="dutyTeams.splice(idx, 1)">删除</el-button>
                  </div>
                  <div class="rotation-group-body">
                    <el-select
                      v-model="team.staff_ids"
                      multiple
                      filterable
                      placeholder="选择组内人员（建议新老搭配）"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="s in staffList"
                        :key="s.id"
                        :label="s.name"
                        :value="s.id"
                      >
                        <span style="float: left">{{ s.name }}</span>
                        <span style="float: right; color: #909399; font-size: 12px">
                          {{ (s.tags || []).join(',') || '无标签' }}
                        </span>
                      </el-option>
                    </el-select>
                  </div>
                </div>
                <el-button @click="addDutyTeam" style="margin-top: 8px;">+ 添加值班组</el-button>
                <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                  值班组按日期轮流值班，同组人员在同一天排班。建议每组2人，新老员工搭配。
                </div>
              </div>
            </el-form-item>
          </template>

          <el-divider content-position="left">整体轮换频次</el-divider>

          <el-form-item label="轮换频次">
            <el-select v-model="formData.rotation_frequency" style="width: 100%">
              <el-option label="按天轮换" value="day" />
              <el-option label="按周轮换" value="week" />
              <el-option label="按月轮换" value="month" />
            </el-select>
            <div class="cross-night-tip">控制该班次整体的轮换周期，不影响轮换组内各自的频次</div>
          </el-form-item>

          <el-divider content-position="left">值班人员</el-divider>

          <el-form-item label="最少人数" prop="member_min">
            <el-input-number v-model="formData.member_min" :min="1" :max="99" controls-position="right" />
          </el-form-item>

          <el-form-item label="最多人数" prop="member_max">
            <el-input-number v-model="formData.member_max" :min="formData.member_min" :max="99" controls-position="right" />
          </el-form-item>

          <el-divider content-position="left">轮换组（可选）</el-divider>

          <el-form-item label="轮换组">
            <div style="width: 100%;">
              <div v-for="(group, idx) in rotationGroups" :key="group.id || idx" class="rotation-group-item">
                <div class="rotation-group-header">
                  <el-input v-model="group.name" placeholder="组名称" style="width: 150px" />
                  <el-select v-model="group.rotation_unit" style="width: 110px">
                    <el-option label="按天" value="day" />
                    <el-option label="按周" value="week" />
                    <el-option label="按月" value="month" />
                  </el-select>
                  <el-input-number v-model="group.slot_count" :min="1" :max="10" controls-position="right" style="width: 90px" />
                  <el-input-number v-model="group.priority" :min="1" :max="100" controls-position="right" style="width: 90px" />
                  <el-switch v-model="group.enabled" />
                  <el-button type="danger" text @click="rotationGroups.splice(idx, 1)">删除</el-button>
                </div>
                <div class="rotation-group-body">
                  <el-select
                    v-model="group.staff_ids"
                    multiple
                    filterable
                    placeholder="选择轮换人员（按顺序轮换）"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="s in staffList"
                      :key="s.id"
                      :label="s.name"
                      :value="s.id"
                    />
                  </el-select>
                </div>
              </div>
              <el-button @click="addRotationGroup" style="margin-top: 8px;">+ 添加轮换组</el-button>
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                轮换组内的人员按顺序在指定周期内循环值班，剩余名额从全员中公平轮值
              </div>
            </div>
          </el-form-item>

          <el-divider content-position="left">适用日期</el-divider>

          <el-form-item label="适用日期" prop="apply_days">
            <el-checkbox-group v-model="formData.apply_days">
              <el-checkbox-button v-for="(label, idx) in dayLabels" :key="idx" :value="idx + 1">
                {{ label }}
              </el-checkbox-button>
            </el-checkbox-group>
          </el-form-item>

          <el-form-item v-if="!isCreate" label="启用状态">
            <el-switch
              :model-value="currentStatus === 1"
              active-text="启用"
              inactive-text="停用"
              @change="handleToggleStatus"
            />
          </el-form-item>

          <el-form-item>
            <div class="form-actions">
              <el-button type="primary" @click="handleSave">保存</el-button>
              <el-button v-if="!isCreate" @click="handleCopy">复制</el-button>
              <el-button v-if="!isCreate" type="danger" @click="handleDelete">删除</el-button>
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

  // 删除服务器有但前端没有的
  for (const sid of serverIds) {
    if (!frontendIds.includes(sid)) {
      await api.delete(`/shift-templates/${templateId}/duty-teams/${sid}`)
    }
  }

  // 创建或更新
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

// ==================== 轮换组 ====================

interface RotationGroupForm {
  id?: number
  shift_template_id?: number
  name: string
  staff_ids: number[]
  rotation_unit: string
  slot_count: number
  priority: number
  enabled: boolean
}

const rotationGroups = ref<RotationGroupForm[]>([])

function addRotationGroup() {
  rotationGroups.value.push({
    name: '',
    staff_ids: [],
    rotation_unit: 'month',
    slot_count: 1,
    priority: (rotationGroups.value.length + 1) * 10,
    enabled: true,
  })
}

async function loadRotationGroups(templateId: number) {
  try {
    const res = await api.get(`/shift-templates/${templateId}/rotation-groups`)
    rotationGroups.value = Array.isArray(res) ? res : []
  } catch {
    rotationGroups.value = []
  }
}

async function saveRotationGroups(templateId: number) {
  // 获取服务器已有轮换组
  const serverRes = await api.get(`/shift-templates/${templateId}/rotation-groups`)
  const serverIds = (Array.isArray(serverRes) ? serverRes : []).map((g: any) => g.id)
  const frontendIds = rotationGroups.value.filter(g => g.id).map(g => g.id)

  // 删除服务器有但前端没有的
  for (const sid of serverIds) {
    if (!frontendIds.includes(sid)) {
      await api.delete(`/shift-templates/${templateId}/rotation-groups/${sid}`)
    }
  }

  // 创建或更新
  for (const group of rotationGroups.value) {
    const payload = {
      name: group.name,
      staff_ids: group.staff_ids,
      rotation_unit: group.rotation_unit,
      slot_count: group.slot_count,
      priority: group.priority,
      enabled: group.enabled,
    }
    if (group.id) {
      await api.put(`/shift-templates/${templateId}/rotation-groups/${group.id}`, payload)
    } else {
      await api.post(`/shift-templates/${templateId}/rotation-groups`, payload)
    }
  }
}

const staffList = ref<any[]>([])

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
  rotation_frequency: 'day',
  schedule_mode: 'individual',
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
    const res: any = await api.get('/staffs')
    staffList.value = Array.isArray(res) ? res : (res.items || [])
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
    rotation_frequency: item.rotation_frequency || 'day',
    schedule_mode: item.schedule_mode || 'individual',
  }
  loadRotationGroups(item.id)
  loadDutyTeams(item.id)
}

function handleCreate() {
  isCreate.value = true
  selectedId.value = -1
  currentStatus.value = 1
  formData.value = { ...defaultForm, apply_days: [...defaultForm.apply_days] }
  rotationGroups.value = []
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
        if (rotationGroups.value.length > 0) await saveRotationGroups(created.id)
        if (dutyTeams.value.length > 0) await saveDutyTeams(created.id)
      }
      ElMessage.success('创建成功')
      await loadList()
      handleSelect(created)
      isCreate.value = false
    } else {
      const updated = await updateShiftTemplate(selectedId.value!, formData.value)
      await saveRotationGroups(selectedId.value!)
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

/* 左侧列表 */
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

/* 右侧表单 */
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
