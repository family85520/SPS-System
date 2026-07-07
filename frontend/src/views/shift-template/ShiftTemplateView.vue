<template>
  <div class="shift-template-page">
    <!-- Header Stats Bar -->
    <div class="stat-grid">
      <!-- 总班次 -->
      <div class="neo-card stat-card stat-card-blue" :class="{ 'stat-card--active': filterType === 'all' }" @click="filterType = 'all'">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">总班次数量</span>
            <span class="stat-big-number">{{ templateList.length }}</span>
          </div>
          <div class="stat-deco stat-deco-total" />
        </div>
      </div>

      <!-- 白班 -->
      <div class="neo-card stat-card stat-card-green" :class="{ 'stat-card--active': filterType === 'day' }" @click="filterType = 'day'">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Sunrise /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">白班班次</span>
            <span class="stat-big-number">{{ dayShiftCount }}</span>
          </div>
          <div class="stat-deco stat-deco-day" />
        </div>
      </div>

      <!-- 夜班 -->
      <div class="neo-card stat-card stat-card-red" :class="{ 'stat-card--active': filterType === 'night' }" @click="filterType = 'night'">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Moon /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">夜班班次</span>
            <span class="stat-big-number">{{ nightShiftCount }}</span>
          </div>
          <div class="stat-deco stat-deco-night" />
        </div>
      </div>

      <!-- 特殊班次 -->
      <div class="neo-card stat-card stat-card-purple" :class="{ 'stat-card--active': filterType === 'special' }" @click="filterType = 'special'">
        <div class="stat-accent-bar" />
        <div class="stat-card-inner">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Star /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-label-text">特殊班次</span>
            <span class="stat-big-number">{{ specialShiftCount }}</span>
          </div>
          <div class="stat-deco stat-deco-special" />
        </div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="page-toolbar">
      <h2 class="page-title">
        <el-icon class="section-icon"><Document /></el-icon>
        班次模板列表
      </h2>
      <div class="toolbar-actions">
        <div class="search-box">
          <el-icon class="search-icon"><Search /></el-icon>
          <el-input
            v-model="keyword"
            placeholder="搜索班次名称..."
            clearable
          />
        </div>
        <el-button
          v-if="authStore.hasPermission('shift_template', 'create')"
          type="primary"
          class="btn-neo-primary toolbar-btn"
          @click="openCreateDialog"
        >
          <el-icon><Plus /></el-icon>
          新建班次
        </el-button>
      </div>
    </div>

    <!-- Card Grid -->
    <div class="card-grid" v-loading="loading">
      <div
        v-for="item in filteredList"
        :key="item.id"
        class="data-card"
        :class="{ 'data-card--disabled': item.status === 0 }"
        @click="openEditDialog(item)"
      >
        <!-- Card Header -->
        <div class="data-card-header">
          <div class="data-card-title">
            <div class="color-swatch" :style="{ background: item.color }"></div>
            <h3 class="data-card-name">{{ item.name }}</h3>
          </div>
          <span class="neo-badge" :class="item.status === 1 ? 'neo-badge--active' : 'neo-badge--inactive'">
            {{ item.status === 1 ? '启用' : '停用' }}
          </span>
        </div>

        <!-- Card Body -->
        <div class="data-card-body">
          <div class="data-detail">
            <el-icon class="detail-icon"><Clock /></el-icon>
            <span class="detail-text">{{ item.start_time }} - {{ item.end_time }}</span>
          </div>
          <div class="data-detail">
            <el-icon class="detail-icon"><UserFilled /></el-icon>
            <span class="detail-text">最少需要 {{ item.member_min }} 人在岗</span>
          </div>
          <div class="data-detail">
            <el-icon class="detail-icon"><Timer /></el-icon>
            <span class="detail-text">每日工时 {{ item.duration_hours }} 小时</span>
          </div>
        </div>

        <!-- Card Footer -->
        <div class="data-card-footer">
          <el-button
            class="neo-btn neo-btn--sm flex-1"
            @click.stop="openEditDialog(item)"
            v-if="authStore.hasPermission('shift_template', 'update')"
          >
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button
            class="neo-btn neo-btn--danger neo-btn--sm flex-1"
            @click.stop="handleDelete(item)"
            v-if="authStore.hasPermission('shift_template', 'delete')"
          >
            <el-icon><Delete /></el-icon>
            删除
          </el-button>
        </div>
      </div>

      <div v-if="!loading && filteredList.length === 0" class="empty-state">
        <el-icon :size="48" color="#C0C4CC"><Document /></el-icon>
        <p>暂无班次模板</p>
      </div>
    </div>

    <!-- Create/Edit Drawer -->
    <el-drawer
      v-model="drawerVisible"
      size="680px"
      direction="rtl"
      :close-on-click-modal="false"
      destroy-on-close
      class="shift-drawer"
    >
      <template #header="{ titleId, titleClass }">
        <div class="drawer-header-custom">
          <h3 :id="titleId" class="drawer-title-lg">
            <el-icon class="drawer-title-icon"><Document /></el-icon>
            {{ isCreate ? '新建班次' : '编辑班次' }}
          </h3>
          <el-button class="neo-btn neo-btn--sm" @click="drawerVisible = false">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </template>

      <div class="drawer-body">
        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-position="top"
          label-width="140px"
          class="edit-form"
          v-loading="saving"
        >
          <!-- Basic Info -->
          <div class="form-group">
            <label class="form-label">班次名称</label>
            <el-input
              v-model="formData.name"
              placeholder="请输入班次名称，例如：早班"
              maxlength="50"
              show-word-limit
              :disabled="!canEdit"
              class="neo-input"
            />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">开始时间</label>
              <el-time-select
                v-model="formData.start_time"
                start="00:00"
                step="00:30"
                end="23:30"
                :disabled="!canEdit"
                class="neo-input"
              />
            </div>
            <div class="form-group">
              <label class="form-label">结束时间</label>
              <el-time-select
                v-model="formData.end_time"
                start="00:00"
                step="00:30"
                end="23:30"
                :disabled="!canEdit"
                class="neo-input"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">最少在岗人数</label>
              <el-input-number
                v-model="formData.member_min"
                :min="1"
                :max="99"
                controls-position="right"
                :disabled="!canEdit"
                class="neo-input neo-input-number"
              />
            </div>
            <div class="form-group">
              <label class="form-label">最多在岗人数</label>
              <el-input-number
                v-model="formData.member_max"
                :min="formData.member_min"
                :max="99"
                controls-position="right"
                :disabled="!canEdit"
                class="neo-input neo-input-number"
              />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">班次时长</label>
            <el-input :model-value="computedDuration" disabled class="neo-input neo-input-disabled">
              <template #suffix>小时</template>
            </el-input>
            <div v-if="isCrossNight" class="cross-night-tip">
              <el-icon color="#FFD93D"><WarningFilled /></el-icon>
              跨夜班，时长自动计算
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">班次颜色标识</label>
            <div class="color-picker-grid">
              <label
                v-for="c in presetColors"
                :key="c"
                class="color-option"
                :class="{ 'color-option--active': formData.color === c }"
              >
                <input
                  type="radio"
                  name="shiftColor"
                  :value="c"
                  v-model="formData.color"
                  :disabled="!canEdit"
                />
                <span class="color-swatch-lg" :style="{ background: c }"></span>
                <span class="color-hex">{{ c }}</span>
              </label>
            </div>
          </div>

          <!-- Leader Group -->
          <div class="form-section">
            <div class="form-section-header">
              <span class="form-section-icon"><el-icon><Avatar /></el-icon></span>
              <span class="form-section-title">值班领导组</span>
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.leader_enabled, 'is-disabled': !canEdit }"
                @click="() => { if (canEdit) formData.leader_enabled = !formData.leader_enabled }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </div>
          </div>

          <template v-if="formData.leader_enabled">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">最少人数</label>
                <el-input-number
                  v-model="formData.leader_min"
                  :min="0"
                  :max="99"
                  controls-position="right"
                  :disabled="!canEdit"
                  class="neo-input neo-input-number"
                />
              </div>
              <div class="form-group">
                <label class="form-label">最多人数</label>
                <el-input-number
                  v-model="formData.leader_max"
                  :min="formData.leader_min"
                  :max="99"
                  controls-position="right"
                  :disabled="!canEdit"
                  class="neo-input neo-input-number"
                />
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">每次选出人数</label>
              <el-input-number
                v-model="formData.leader_count"
                :min="1"
                :max="formData.leader_max || 99"
                controls-position="right"
                :disabled="!canEdit"
                class="neo-input neo-input-number"
              />
            </div>
            <div class="form-group">
              <label class="form-label">独立轮换频次</label>
              <el-select v-model="formData.leader_rotation_frequency" :disabled="!canEdit" class="neo-input">
                <el-option label="按天轮换" value="day" />
                <el-option label="按周轮换" value="week" />
                <el-option label="按月轮换" value="month" />
              </el-select>
            </div>
            <div class="form-group">
              <label class="form-label">候选人员</label>
              <el-select
                v-model="formData.leader_pool"
                multiple
                filterable
                placeholder="选择领导候选人员"
                :disabled="!canEdit"
                class="neo-input"
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
            </div>
            <div class="form-group">
              <label class="form-label">标识回退</label>
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.leader_use_tag, 'is-disabled': !canEdit }"
                @click="() => { if (canEdit) formData.leader_use_tag = !formData.leader_use_tag }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </div>
            <div class="form-group" v-if="formData.leader_use_tag">
              <label class="form-label">标识名称</label>
              <el-input
                v-model="formData.leader_tag_name"
                placeholder="领导"
                :disabled="!canEdit"
                class="neo-input"
              />
            </div>
          </template>

          <!-- Member Group -->
          <div class="form-section">
            <div class="form-section-header">
              <span class="form-section-icon"><el-icon><User /></el-icon></span>
              <span class="form-section-title">值班人员组</span>
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.member_enabled, 'is-disabled': !canEdit }"
                @click="() => { if (canEdit) formData.member_enabled = !formData.member_enabled }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </div>
          </div>

          <template v-if="formData.member_enabled">
            <div class="form-group">
              <label class="form-label">轮换频次</label>
              <el-select v-model="formData.member_rotation_frequency" :disabled="!canEdit" class="neo-input">
                <el-option label="按天轮换" value="day" />
                <el-option label="按周轮换" value="week" />
                <el-option label="按月轮换" value="month" />
              </el-select>
            </div>
            <div class="form-group">
              <label class="form-label">跨模板共排</label>
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.allow_multi_template, 'is-disabled': !canEdit }"
                @click="() => { if (canEdit) formData.allow_multi_template = !formData.allow_multi_template }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </div>
          </template>

          <!-- Special Group -->
          <div class="form-section">
            <div class="form-section-header">
              <span class="form-section-icon"><el-icon><Star /></el-icon></span>
              <span class="form-section-title">特殊人员组</span>
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.special_enabled, 'is-disabled': !canEdit }"
                @click="() => { if (canEdit) formData.special_enabled = !formData.special_enabled }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </div>
          </div>

          <template v-if="formData.special_enabled">
            <div class="form-group">
              <label class="form-label">候选人员</label>
              <el-select
                v-model="formData.special_pool"
                multiple
                filterable
                placeholder="选择特殊人员候选池"
                :disabled="!canEdit"
                class="neo-input"
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
            </div>
            <div class="form-group">
              <label class="form-label">每次选出人数</label>
              <el-input-number
                v-model="formData.special_count"
                :min="1"
                :max="(formData.special_pool || []).length || 1"
                controls-position="right"
                :disabled="!canEdit"
                class="neo-input neo-input-number"
              />
            </div>
            <div class="form-group">
              <label class="form-label">轮换频次</label>
              <el-select v-model="formData.special_rotation_frequency" :disabled="!canEdit" class="neo-input">
                <el-option label="按天轮换" value="day" />
                <el-option label="按周轮换" value="week" />
                <el-option label="按月轮换" value="month" />
              </el-select>
            </div>
            <div class="form-group">
              <label class="form-label">从人员池排除</label>
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.special_exclude_from_member, 'is-disabled': !canEdit }"
                @click="() => { if (canEdit) formData.special_exclude_from_member = !formData.special_exclude_from_member }"
              >
                <span class="neo-switch-knob"></span>
              </span>
            </div>
          </template>

          <!-- Constraint Rules -->
          <div class="form-section">
            <div class="form-section-header">
              <span class="form-section-icon"><el-icon><List /></el-icon></span>
              <span class="form-section-title">约束规则</span>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">指定约束规则</label>
            <el-select
              v-model="formData.constraint_ids"
              multiple
              filterable
              placeholder="留空则使用全部已启用规则"
              :disabled="!canEdit"
              class="neo-input"
            >
              <el-option
                v-for="c in constraintList"
                :key="c.id"
                :label="c.rule_name"
                :value="c.id"
              />
            </el-select>
          </div>

          <!-- Apply Days -->
          <div class="form-section">
            <div class="form-section-header">
              <span class="form-section-icon"><el-icon><Calendar /></el-icon></span>
              <span class="form-section-title">适用日期</span>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">适用日期</label>
            <div class="day-selector">
              <button
                v-for="(label, idx) in dayLabels"
                :key="idx"
                type="button"
                class="day-btn-item"
                :class="{ 'day-btn-item--active': formData.apply_days.includes(idx + 1) }"
                :disabled="!canEdit"
                @click="toggleDay(idx + 1)"
              >
                {{ label }}
              </button>
            </div>
          </div>

          <!-- Status (edit only) -->
          <el-form-item label="启用状态" v-if="!isCreate">
            <span
              v-if="authStore.hasPermission('shift_template', 'update')"
              class="neo-switch-inline"
              :class="{ 'is-checked': currentStatus === 1, 'is-disabled': false }"
              @click="handleToggleStatus(currentStatus === 0)"
            >
              <span class="neo-switch-knob"></span>
            </span>
            <el-tag v-else :type="currentStatus === 1 ? 'success' : 'info'" size="small" effect="dark">
              {{ currentStatus === 1 ? '启用' : '停用' }}
            </el-tag>
          </el-form-item>
        </el-form>
      </div>

      <!-- Drawer Footer Actions -->
      <template #footer>
        <div class="drawer-footer-custom">
          <el-button class="neo-btn flex-1 btn-neo-ghost" @click="drawerVisible = false">
            取消
          </el-button>
          <el-button
            v-if="authStore.hasPermission('shift_template', isCreate ? 'create' : 'update')"
            class="neo-btn neo-btn--primary flex-1 btn-neo-primary"
            @click="handleSave"
          >
            <el-icon><Check /></el-icon>
            {{ isCreate ? '创建班次' : '保存班次' }}
          </el-button>
        </div>
      </template>
    </el-drawer>

    <!-- Delete Confirmation Dialog — 已由全局 ConfirmDialog 接管 -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus, Search, Clock, Sunrise, Moon, Star, Document,
  Edit, Delete, Close, Check, Avatar,
  User, UserFilled, Timer, List, Calendar,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import {
  getShiftTemplates, createShiftTemplate, updateShiftTemplate,
  deleteShiftTemplate, toggleShiftTemplateStatus,
  type ShiftTemplate, type ShiftTemplateForm,
} from '@/api/shift-template'
import api from '@/api/index'
import { useConfirm } from '@/composables/useConfirm'

const authStore = useAuthStore()
const { confirmDanger, confirmWarning } = useConfirm()

const canEdit = computed(() => {
  if (isCreate.value) return authStore.hasPermission('shift_template', 'create')
  return authStore.hasPermission('shift_template', 'update')
})

const dayLabels = ['一', '二', '三', '四', '五', '六', '日']

function toggleDay(day: number) {
  const days = formData.value.apply_days
  const idx = days.indexOf(day)
  if (idx > -1) {
    days.splice(idx, 1)
  } else {
    days.push(day)
  }
}

const presetColors = [
  '#FFD93D', '#FF6B6B', '#3B82F6', '#10B981', '#C4B5FD', '#F59E0B',
]

const loading = ref(false)
const templateList = ref<ShiftTemplate[]>([])
const keyword = ref('')
const filterType = ref<'all' | 'day' | 'night' | 'special'>('all')
const drawerVisible = ref(false)
const isCreate = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const currentStatus = ref(1)
const staffList = ref<any[]>([])
const constraintList = ref<any[]>([])

const defaultForm: ShiftTemplateForm = {
  name: '', org_id: null, start_time: '08:00', end_time: '16:00',
  color: '#FFD93D', leader_min: 0, leader_max: 1, leader_pool: null,
  member_min: 1, member_max: 2, apply_days: [1, 2, 3, 4, 5],
  allow_multi_template: false, leader_enabled: false,
  leader_rotation_frequency: 'week', leader_count: 1,
  leader_use_tag: true, leader_tag_name: null as string | null,
  member_enabled: true, member_rotation_frequency: 'day',
  special_enabled: false, special_rotation_frequency: 'month',
  special_count: 1, special_pool: null, special_exclude_from_member: true,
  constraint_ids: null,
}

const formData = ref<ShiftTemplateForm>({ ...defaultForm })

const filteredList = computed(() => {
  let list = templateList.value

  // Filter by keyword
  if (keyword.value) {
    list = list.filter((t) => t.name.includes(keyword.value))
  }

  // Filter by type
  if (filterType.value !== 'all') {
    list = list.filter((t) => {
      if (filterType.value === 'day') return t.status === 1 && isDayShift(t) && !(t as any).special_enabled
      if (filterType.value === 'night') return t.status === 1 && isNightShift(t) && !(t as any).special_enabled
      if (filterType.value === 'special') return t.status === 1 && (t as any).special_enabled
      return true
    })
  }

  return list
})

// Stats helpers
function parseTime(t: string): { h: number; m: number } {
  const [h, m] = t.split(':').map(Number)
  return { h, m }
}

function isDayShift(t: ShiftTemplate): boolean {
  // 白班：标准白天工作时间，结束时间在 18:00 之前
  const { h: eh } = parseTime(t.end_time)
  return eh < 18
}

function isNightShift(t: ShiftTemplate): boolean {
  const { h: sh } = parseTime(t.start_time)
  const { h: eh } = parseTime(t.end_time)
  // 夜班：20:00后开始 或 08:00前结束
  return sh >= 20 || eh <= 8
}

const dayShiftCount = computed(() =>
  templateList.value.filter((t) => t.status === 1 && isDayShift(t) && !(t as any).special_enabled).length
)
const nightShiftCount = computed(() =>
  templateList.value.filter((t) => t.status === 1 && isNightShift(t) && !(t as any).special_enabled).length
)
const specialShiftCount = computed(() =>
  templateList.value.filter((t) => t.status === 1 && (t as any).special_enabled).length
)

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
  member_min: [{ required: true, message: '请设置最少人数', trigger: 'change' }],
  member_max: [{ required: true, message: '请设置最多人数', trigger: 'change' }],
  leader_min: [{ required: true, message: '请设置最少人数', trigger: 'change' }],
  leader_max: [{ required: true, message: '请设置最多人数', trigger: 'change' }],
  apply_days: [
    { type: 'array', required: true, min: 1, message: '请至少选择一天', trigger: 'change' },
  ],
}

async function loadConstraintList() {
  try {
    const res: any = await api.get('/constraints')
    const list = Array.isArray(res) ? res : (res.items || res.data || [])
    constraintList.value = list.filter((c: any) => c.enabled)
  } catch {
    constraintList.value = []
  }
}

async function loadStaffList() {
  try {
    const res: any = await api.get('/staffs/options')
    const list = Array.isArray(res) ? res : (res.data || [])
    staffList.value = list
  } catch {
    staffList.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    templateList.value = await getShiftTemplates()
  } catch { /* handled */ }
  finally {
    loading.value = false
  }
}

function openEditDialog(item: ShiftTemplate) {
  isCreate.value = false
  currentStatus.value = item.status
  formData.value = {
    name: item.name, org_id: item.org_id,
    start_time: item.start_time, end_time: item.end_time,
    color: item.color, leader_min: item.leader_min, leader_max: item.leader_max,
    leader_pool: item.leader_pool, member_min: item.member_min, member_max: item.member_max,
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
  drawerVisible.value = true
}

function openCreateDialog() {
  isCreate.value = true
  currentStatus.value = 1
  formData.value = { ...defaultForm, apply_days: [...defaultForm.apply_days] }
  drawerVisible.value = true
}

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isCreate.value) {
      const created = await createShiftTemplate(formData.value)
      ElMessage.success('创建成功')
      await loadList()
      openEditDialog(created)
    } else {
      const existing = templateList.value.find(t => t.name === formData.value.name && t.id !== undefined)
      if (!existing) {
        const created = await createShiftTemplate(formData.value)
        ElMessage.success('创建成功')
        await loadList()
        openEditDialog(created)
      } else {
        const updated = await updateShiftTemplate(existing.id, formData.value)
        ElMessage.success('保存成功')
        await loadList()
        openEditDialog(updated)
      }
    }
  } catch (e) {
    // error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleDelete(item: ShiftTemplate) {
  const confirmed = await confirmDanger(
    `您确定要删除「${item.name}」吗？删除后相关排班数据也会受到影响，此操作不可恢复。`,
    '确认删除',
  ).catch(() => false)
  if (!confirmed) return
  try {
    await deleteShiftTemplate(item.id)
    ElMessage.success('删除成功')
    await loadList()
  } catch (e) {
    // error handled by interceptor
  }
}

async function handleToggleStatus(val: boolean) {
  const current = templateList.value.find(
    (t) => t.name === formData.value.name && (!isCreate.value)
  )
  if (!current) return
  const tip = val ? '确认启用该班次模板？' : '停用后该班次不参与自动排班，确认停用？'
  try {
    await confirmWarning(tip, '确认操作？')
    const updated = await toggleShiftTemplateStatus(current.id)
    currentStatus.value = updated.status
    ElMessage.success(updated.status === 1 ? '已启用' : '已停用')
    await loadList()
  } catch (e) {
    // cancelled or error
  }
}

onMounted(() => {
  loadList()
  loadStaffList()
  loadConstraintList()
})
</script>

<style scoped>
/* ================================================================
   页面特定布局（共享样式已迁移至 global.scss）
   ================================================================ */

/* --- 页面容器 --- */
.shift-template-page {
  padding: 24px;
  background: #FFFDF5;
  min-height: calc(100vh - 96px);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* --- 页面内局部覆盖 --- */
.search-box {
  position: relative;
  width: 280px;
  flex-shrink: 0;
}
.search-box .search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
  font-size: 18px;
  z-index: 1;
  pointer-events: none;
}
.search-box :deep(.el-input__wrapper) {
  padding-left: 42px !important;
  height: 44px !important;
  min-height: 44px !important;
  border: 3px solid #000000 !important;
  border-radius: 4px !important;
  box-shadow: 3px 3px 0px 0px #000000 !important;
  background: #FFFFFF !important;
}
.search-box :deep(.el-input__inner) {
  font-weight: 600 !important;
}

/* --- 抽屉样式覆盖 --- */
.shift-drawer :deep(.el-drawer) {
  border: 3px solid #000000 !important;
  border-radius: 0 !important;
  box-shadow: 8px 0px 0px 0px #000000 !important;
}
.shift-drawer :deep(.el-drawer__header) {
  border-bottom: 3px solid #000000 !important;
  background: #FFFDF5 !important;
  padding: 16px 24px !important;
  margin-bottom: 0 !important;
}
.shift-drawer :deep(.el-drawer__body) {
  background: #FFFFFF !important;
}

/* --- 抽屉 body 右边距 --- */
.drawer-body {
  padding-right: 8px;
}

/* --- 表单底部 --- */
.edit-form {
  padding-bottom: 24px;
}

/* --- 跨夜提示 --- */
.cross-night-tip {
  font-size: 14px;
  color: #333;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
}

/* --- 详情文字 --- */
.detail-text {
  font-size: 14px;
  font-weight: 600;
  color: #000000;
}

/* --- 日期选择器布局 --- */
.day-selector {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* --- 空状态跨列覆盖 --- */
.empty-state {
  grid-column: 1 / -1;
  padding: 60px 20px;
}
.empty-state p {
  margin-top: 12px;
  font-size: 15px;
}

/* --- 小按钮覆盖 --- */
.neo-btn--sm {
  padding: 6px 12px !important;
  font-size: 13px !important;
}

/* --- 页面特有动画延迟 --- */
.stat-card:nth-child(1) { animation: pop-in 0.35s ease both; animation-delay: 0.05s; }
.stat-card:nth-child(2) { animation: pop-in 0.35s ease both; animation-delay: 0.1s; }
.stat-card:nth-child(3) { animation: pop-in 0.35s ease both; animation-delay: 0.15s; }
.stat-card:nth-child(4) { animation: pop-in 0.35s ease both; animation-delay: 0.2s; }

/* --- 响应式 --- */
@media (max-width: 768px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); gap: 12px; }
  .stat-icon-wrap { width: 42px; height: 42px; }
  .stat-icon-wrap .el-icon { font-size: 18px !important; }
  .stat-big-number { font-size: 28px; }
  .stat-label-text { font-size: 11px; }
  .stat-card-inner { padding: 14px; gap: 10px; }
  .stat-deco { display: none; }
  .card-grid { grid-template-columns: 1fr; }
  .page-toolbar { flex-direction: column; align-items: stretch; gap: 12px; }
  .toolbar-actions { flex-direction: column; width: 100%; }
  .search-box { width: 100%; }
  .color-picker-grid { grid-template-columns: repeat(3, 1fr); }
  .form-row { grid-template-columns: 1fr; }
}

@media (max-width: 1200px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
