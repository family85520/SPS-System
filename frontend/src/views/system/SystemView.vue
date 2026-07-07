<template>
  <div class="system-page">

    <!-- ====== 基本信息卡片 ====== -->
    <div class="neo-card">
      <h3 class="card-title">基本信息</h3>
      <el-form :model="formData" label-position="top" class="neo-form">

        <!-- 系统名称 -->
        <el-form-item label="系统名称">
          <el-input v-model="formData.system_name" placeholder="请输入系统名称" class="neo-input" />
        </el-form-item>

        <!-- 单位名称 -->
        <el-form-item label="单位名称">
          <el-input v-model="formData.org_name" placeholder="请输入单位名称" class="neo-input" />
        </el-form-item>

        <!-- 全局排班人数比例 -->
        <el-form-item label="全局排班人数比例">
          <el-input-number
            v-model="formData.daily_max_scheduled_ratio"
            :min="0.1"
            :max="1.0"
            :step="0.05"
            :precision="2"
            controls-position="right"
            class="neo-input"
          />
          <div class="form-tip">每日排班人数占在岗人员的默认比例上限（如0.70=70%），各组织可在组织管理中覆盖此值</div>
        </el-form-item>

      </el-form>
    </div>

    <!-- ====== 通知与权限卡片 ====== -->
    <div class="neo-card">
      <h3 class="card-title">通知与权限</h3>
      <el-form :model="formData" label-position="top" class="neo-form">

        <!-- 调班审批开关 -->
        <el-form-item label="调班审批开关">
          <div class="form-with-tip">
            <span
              class="neo-switch-inline"
              :class="{ 'is-checked': formData.swap_approval_enabled }"
              @click="formData.swap_approval_enabled = !formData.swap_approval_enabled"
            >
              <span class="neo-switch-knob"></span>
            </span>
            <div class="form-tip">开启后，调班申请需管理员审批；关闭后，双方确认即自动生效</div>
          </div>
        </el-form-item>

        <!-- 排班审核开关 -->
        <el-form-item label="排班审核开关">
          <div class="form-with-tip">
            <span
              class="neo-switch-inline"
              :class="{ 'is-checked': formData.schedule_approval_enabled }"
              @click="formData.schedule_approval_enabled = !formData.schedule_approval_enabled"
            >
              <span class="neo-switch-knob"></span>
            </span>
            <div class="form-tip">开启后，排班发布需管理员审核通过；关闭后，排班管理员可直接发布</div>
          </div>
        </el-form-item>

        <!-- 管理员接收全部通知 -->
        <el-form-item label="管理员接收全部通知">
          <div class="form-with-tip">
            <span
              class="neo-switch-inline"
              :class="{ 'is-checked': adminNotifRaw }"
              @click="adminNotifRaw = !adminNotifRaw"
            >
              <span class="neo-switch-knob"></span>
            </span>
            <div class="form-tip">开启后管理员将收到所有排班发布、撤回等通知，无论是否参与排班</div>
          </div>
        </el-form-item>

      </el-form>
    </div>

    <!-- ====== 自动排班卡片 ====== -->
    <div class="neo-card">
      <h3 class="card-title">每月自动排班</h3>
      <el-form :model="formData" label-position="top" class="neo-form">

        <!-- 启用自动排班 -->
        <el-form-item label="启用自动排班">
          <div class="form-with-tip">
            <span
              class="neo-switch-inline"
              :class="{ 'is-checked': autoScheduleEnabledRaw }"
              @click="autoScheduleEnabledRaw = !autoScheduleEnabledRaw"
            >
              <span class="neo-switch-knob"></span>
            </span>
            <div class="alert-card" style="margin-top:8px;padding:10px 12px;">
              <span class="alert-card__icon">⚠</span>
              <span class="alert-card__content" style="font-size:12px;">启用后，系统将在每月最后一天自动执行排班。请确保已配置班次模板和约束规则。</span>
            </div>
          </div>
        </el-form-item>

        <!-- 触发时间 -->
        <el-form-item label="触发时间" v-if="autoScheduleEnabledRaw">
          <el-time-select
            v-model="formData.auto_schedule_time"
            start="00:00"
            step="00:30"
            end="23:30"
            format="HH:mm"
            class="neo-input"
          />
          <div class="form-tip">每月最后一天此时间触发（默认 23:00）</div>
        </el-form-item>

        <!-- 排班组织 -->
        <el-form-item label="排班组织" v-if="autoScheduleEnabledRaw">
          <el-select v-model="formData.auto_schedule_org_ids" multiple placeholder="全部组织" class="neo-input" clearable>
            <el-option v-for="org in orgOptions" :key="org.id" :label="org.name" :value="org.id" />
          </el-select>
          <div class="form-tip">不选 = 所有启用组织</div>
        </el-form-item>

        <!-- 排班班次 -->
        <el-form-item label="排班班次" v-if="autoScheduleEnabledRaw">
          <el-select v-model="formData.auto_schedule_shift_ids" multiple placeholder="全部启用班次" class="neo-input" clearable>
            <el-option v-for="s in shiftOptions" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
          <div class="form-tip">不选 = 各组织全部启用班次模板</div>
        </el-form-item>

        <!-- 跳过已有排班 -->
        <el-form-item label="跳过已有排班" v-if="autoScheduleEnabledRaw">
          <div class="form-with-tip">
            <span
              class="neo-switch-inline"
              :class="{ 'is-checked': autoScheduleSkipExistingRaw }"
              @click="autoScheduleSkipExistingRaw = !autoScheduleSkipExistingRaw"
            >
              <span class="neo-switch-knob"></span>
            </span>
            <div class="form-tip">如果下月已有排班数据，跳过不覆盖</div>
          </div>
        </el-form-item>

        <!-- 排班状态 -->
        <el-form-item label="排班状态" v-if="autoScheduleEnabledRaw">
          <el-radio-group v-model="formData.auto_schedule_status" class="neo-radio-group">
            <el-radio value="draft">草稿（可手动调整）</el-radio>
            <el-radio value="published">直接发布</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 上次执行 -->
        <el-form-item label="上次执行" v-if="formData.auto_schedule_last_run && autoScheduleEnabledRaw">
          <span class="form-tip">{{ formData.auto_schedule_last_run }}</span>
        </el-form-item>

      </el-form>
    </div>

    <!-- ====== 操作按钮 ====== -->
    <div class="form-actions-bar">
      <el-button class="btn-neo-primary btn-neo-save" :loading="saving" @click="handleSave">
        <i class="fas fa-save"></i>
        保存设置
      </el-button>
    </div>

    <!-- 确认弹窗 -->
    <transition name="modal-fade">
      <div v-if="confirmModal.visible" class="modal-mask">
        <transition name="modal-slide">
          <div v-if="confirmModal.visible" class="modal-content">
            <div class="modal-header">
              <i class="fas fa-exclamation-triangle modal-icon"></i>
              <h3 class="modal-title">{{ confirmModal.title }}</h3>
            </div>
            <p class="modal-text">{{ confirmModal.text }}</p>
            <div class="modal-actions">
              <button class="btn-neo-ghost flex-1" @click="confirmModal.visible = false">取消</button>
              <button class="btn-neo-danger flex-1" @click="handleConfirmAction">{{ confirmModal.confirmText }}</button>
            </div>
          </div>
        </transition>
      </div>
    </transition>

    <!-- 成功弹窗 -->
    <transition name="modal-fade">
      <div v-if="successModal.visible" class="modal-mask">
        <transition name="modal-slide">
          <div v-if="successModal.visible" class="modal-content modal-success">
            <i class="fas fa-check-circle modal-success-icon"></i>
            <h3 class="modal-title">操作成功</h3>
            <p class="modal-text">{{ successModal.text }}</p>
            <button class="btn-neo-primary w-full" @click="successModal.visible = false">确定</button>
          </div>
        </transition>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSystemConfig, updateSystemConfig, type SystemConfig } from '@/api/system'
import { getOrgList } from '@/api/organization'
import { getShiftTemplates } from '@/api/shift-template'
import { useSystemStore } from '@/stores/system'

// ---------- 数据加载 ----------
const loading = ref(false)
const saving = ref(false)
const originalFormData = ref<SystemConfig | null>(null)

const orgOptions = ref<{ id: number; name: string }[]>([])
const shiftOptions = ref<{ id: number; name: string }[]>([])

const formData = ref<SystemConfig>({
  system_name: '排班管理系统',
  org_name: '',
  swap_approval_enabled: true,
  schedule_approval_enabled: false,
  admin_receive_all_notifications: 'true',
  daily_max_scheduled_ratio: 0.7,
  auto_schedule_enabled: 'false',
  auto_schedule_status: 'draft',
  auto_schedule_last_run: '',
  auto_schedule_time: '23:00',
  auto_schedule_org_ids: [] as number[],
  auto_schedule_shift_ids: [] as number[],
  auto_schedule_skip_existing: 'false',
} as any)

async function loadConfig() {
  loading.value = true
  try {
    const res = await getSystemConfig()
    formData.value = res
    originalFormData.value = JSON.parse(JSON.stringify(res))
  } catch (e) {
    // interceptor handles error
  } finally {
    loading.value = false
  }
}

// ---------- 保存 ----------
async function handleSave() {
  saving.value = true
  try {
    const res = await updateSystemConfig(formData.value)
    formData.value = res
    originalFormData.value = JSON.parse(JSON.stringify(res))

    // 更新全局 store
    const systemStore = useSystemStore()
    systemStore.systemName = res.system_name
    systemStore.orgName = res.org_name
    systemStore.swapApprovalEnabled = res.swap_approval_enabled
    localStorage.setItem('scheduleApproval', String(res.schedule_approval_enabled))
    localStorage.setItem('systemName', res.system_name)
    localStorage.setItem('orgName', res.org_name)
    localStorage.setItem('swapApproval', String(res.swap_approval_enabled))

    showSuccess('设置已成功保存！')
  } catch (e) {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

// ---------- 弹窗管理 ----------
const confirmModal = ref({ visible: false, title: '', text: '', confirmText: '确认', callback: null as (() => void) | null })
const successModal = ref({ visible: false, text: '' })

function showConfirm(title: string, text: string, confirmText: string = '确认', callback: () => void = () => {}) {
  confirmModal.value = { visible: true, title, text, confirmText, callback }
}

function handleConfirmAction() {
  confirmModal.value.visible = false
  if (confirmModal.value.callback) confirmModal.value.callback()
}

function showSuccess(text: string) {
  successModal.value = { visible: true, text }
}

// ---------- 布尔转换 helpers ----------
// 后端以字符串 'true'/'false' 存储，neo-toggle 期望布尔值
const adminNotifRaw = computed({
  get: () => formData.value.admin_receive_all_notifications === 'true',
  set: (v: boolean) => { formData.value.admin_receive_all_notifications = v ? 'true' : 'false' },
})

const autoScheduleEnabledRaw = computed({
  get: () => formData.value.auto_schedule_enabled === 'true',
  set: (v: boolean) => { formData.value.auto_schedule_enabled = v ? 'true' : 'false' },
})

const autoScheduleSkipExistingRaw = computed({
  get: () => formData.value.auto_schedule_skip_existing === 'true',
  set: (v: boolean) => { formData.value.auto_schedule_skip_existing = v ? 'true' : 'false' },
})

// ---------- 下拉选项加载 ----------
async function loadOrgs() {
  try {
    const res: any = await getOrgList()
    const list = Array.isArray(res) ? res : (res?.data || res?.items || [])
    orgOptions.value = list.map((org: any) => ({ id: org.id, name: org.name }))
  } catch { /* ignore */ }
}

async function loadShifts() {
  try {
    const res: any = await getShiftTemplates()
    const list = Array.isArray(res) ? res : (res?.data || res?.items || [])
    shiftOptions.value = list.map((s: any) => ({ id: s.id, name: s.name }))
  } catch { /* ignore */ }
}

onMounted(() => {
  loadConfig()
  loadOrgs()
  loadShifts()
})
</script>

<style scoped>
/* ============================================================
   Neo-brutalism Design System
   基于 GemDesign 原型风格 + 项目现有全局样式体系
   布局：全宽（与项目其他页面一致）
   ============================================================ */

/* --- 页面容器 --- */
.system-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* --- Neo 卡片（复用项目全局样式） --- */
.neo-card {
  background: #FFFFFF;
  border: 3px solid #000000;
  border-radius: 4px;
  box-shadow: 6px 6px 0px 0px #000000;
  padding: 28px;
  transition: all 0.2s ease;
}

.neo-card:hover {
  box-shadow: 8px 8px 0px 0px #000000;
  transform: translateY(-1px);
}

.card-title {
  margin: 0 0 24px 0;
  font-size: 18px;
  font-weight: 900;
  color: #000000;
  padding-bottom: 12px;
  border-bottom: 2px solid #000000;
}

/* --- Neo 表单 --- */
.neo-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.neo-form :deep(.el-form-item__label) {
  font-size: 15px;
  font-weight: 700;
  color: #000000;
  padding-bottom: 0;
  line-height: 1.5;
}

.neo-form :deep(.el-form-item--large) {
  margin-bottom: 0;
}

/* --- 提示文字 --- */
.form-tip {
  font-size: 12px;
  color: #666666;
  margin-top: 4px;
  line-height: 1.5;
  font-weight: 600;
}

/* --- 带 tip 的行 --- */
.form-with-tip {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* --- Neo Radio Group --- */
.neo-radio-group {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.neo-radio-group :deep(.el-radio) {
  margin: 0;
}

.neo-radio-group :deep(.el-radio__label) {
  font-weight: 700;
  font-size: 14px;
  color: #000000;
}

.neo-radio-group :deep(.el-radio__input) {
  border: 2px solid #000000;
}

.neo-radio-group :deep(.el-radio.is-checked .el-radio__label) {
  font-weight: 700;
  color: #000000;
}

/* --- 底部操作按钮栏 --- */
.form-actions-bar {
  display: flex;
  justify-content: flex-start;
  padding: 4px 0;
}

.btn-neo-save {
  height: 52px !important;
  padding: 0 48px !important;
  font-size: 16px !important;
  letter-spacing: 0.08em !important;
}

/* --- 弹窗遮罩 --- */
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background: #FFFFFF;
  border: 3px solid #000000;
  border-radius: 4px;
  box-shadow: 8px 8px 0px 0px #000000;
  max-width: 480px;
  width: 90%;
  padding: 28px;
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.modal-icon {
  font-size: 28px;
  color: #FF6B6B;
}

.modal-title {
  margin: 0;
  font-size: 20px;
  font-weight: 900;
  color: #000000;
}

.modal-text {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  line-height: 1.6;
  margin: 0 0 20px 0;
}

.modal-actions {
  display: flex;
  gap: 12px;
}

/* 成功弹窗 */
.modal-success {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.modal-success-icon {
  font-size: 48px;
  color: #3B82F6;
  margin: 0;
}

/* --- 弹窗动画 --- */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-slide-enter-active {
  transition: transform 0.2s ease;
}

.modal-slide-enter-from,
.modal-slide-leave-to {
  transform: translateY(20px) scale(0.95);
  opacity: 0;
}

/* --- 响应式 --- */
@media (max-width: 768px) {
  .neo-card {
    padding: 16px;
  }

  .card-title {
    font-size: 16px;
  }

  .form-with-tip {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .modal-content {
    width: 95%;
    padding: 20px;
  }
}
</style>
