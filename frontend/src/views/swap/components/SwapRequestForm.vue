<template>
  <el-dialog
    :model-value="visible"
    title="发起调班申请"
    width="600px"
    class="swap-dialog"
    @close="$emit('update:visible', false)"
  >
    <el-form :model="form" label-width="100px" ref="formRef" :rules="rules">
      <el-form-item label="调班类型" prop="swap_type">
        <el-radio-group v-model="form.swap_type" @change="onTypeChange" class="neo-radio-group">
          <el-radio value="specified">指定换班</el-radio>
          <el-radio value="open">开放换班</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="我的班次" prop="requester_schedule_id">
        <el-select v-model="form.requester_schedule_id" placeholder="选择要换的班次" class="neo-input">
          <el-option
            v-for="s in mySchedules"
            :key="s.id"
            :label="`${s.date} | ${s.shift_name || '班次' + s.shift_id}`"
            :value="s.id"
          />
        </el-select>
      </el-form-item>

      <template v-if="form.swap_type === 'specified'">
        <el-form-item label="换班对象" prop="target_id">
          <el-select
            v-model="form.target_id"
            placeholder="选择换班对象"
            filterable
            remote
            :remote-method="searchTarget"
            :loading="targetLoading"
            style="width: 100%"
            @change="onTargetChange"
            class="neo-input"
          >
            <el-option
              v-for="u in targetUsers"
              :key="u.id"
              :label="u.name"
              :value="u.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="对方班次" prop="target_schedule_id" v-if="form.target_id">
          <el-select v-model="form.target_schedule_id" placeholder="选择对方班次" class="neo-input">
            <el-option
              v-for="s in targetSchedules"
              :key="s.id"
              :label="`${s.date} | ${s.shift_name || '班次' + s.shift_id}`"
              :value="s.id"
            />
          </el-select>
        </el-form-item>
      </template>

      <el-form-item label="申请原因" prop="reason">
        <el-input
          v-model="form.reason"
          type="textarea"
          :rows="3"
          placeholder="请输入申请原因（选填）"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <div class="alert-card" style="margin-top:8px;">
        <span class="alert-card__icon">ℹ</span>
        <span class="alert-card__content">提交申请后，对方需确认同意方可完成换班。开放换班模式下，其他符合条件的同事也可认领。</span>
      </div>
    </el-form>

    <template #footer>
      <el-button class="btn-neo-ghost btn-neo-sm" @click="$emit('update:visible', false)">取消</el-button>
      <el-button class="btn-neo-primary btn-neo-sm" :loading="submitting" @click="handleSubmit">提交申请</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createSwap, getMySchedules } from '@/api/swap'
import { useAuthStore } from '@/stores/auth'
import request from '@/utils/request'
import type { FormInstance, FormRules } from 'element-plus'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}>()

const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = ref({
  swap_type: 'specified',
  requester_schedule_id: null as number | null,
  target_id: null as number | null,
  target_schedule_id: null as number | null,
  reason: '',
})

const rules: FormRules = {
  swap_type: [{ required: true, message: '请选择调班类型' }],
  requester_schedule_id: [{ required: true, message: '请选择您的班次' }],
  target_id: [{ required: true, message: '请选择换班对象' }],
  target_schedule_id: [{ required: true, message: '请选择对方班次' }],
}

const mySchedules = ref<any[]>([])
const targetUsers = ref<any[]>([])
const targetSchedules = ref<any[]>([])
const targetLoading = ref(false)

const loadMySchedules = async () => {
  try {
    if (!authStore.staffId) {
      mySchedules.value = []
      return
    }
    const { data: res } = await getMySchedules({ staff_id: authStore.staffId, status: 1 })
    mySchedules.value = res.data || res.items || []
  } catch {
    mySchedules.value = []
  }
}

const searchTarget = async (keyword: string) => {
  if (!keyword) {
    targetUsers.value = []
    return
  }
  targetLoading.value = true
  try {
    const { data: res } = await request.get('/api/staffs/options', { params: { keyword } })
    const items = res.data || res.items || res || []
    targetUsers.value = (Array.isArray(items) ? items : []).map((s: any) => ({ id: s.id, name: s.name }))
  } catch {
    targetUsers.value = []
  } finally {
    targetLoading.value = false
  }
}

const onTargetChange = async (targetStaffId: number) => {
  form.value.target_schedule_id = null
  try {
    const { data: res } = await request.get('/api/schedules/by-staff', {
      params: { staff_id: targetStaffId, status: 1 },
    })
    targetSchedules.value = res.data || []
  } catch {
    targetSchedules.value = []
  }
}

const onTypeChange = () => {
  form.value.target_id = null
  form.value.target_schedule_id = null
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()

  if (form.value.swap_type === 'specified' && (!form.value.target_id || !form.value.target_schedule_id)) {
    ElMessage.warning('请完善指定换班信息')
    return
  }

  submitting.value = true
  try {
    await createSwap({
      swap_type: form.value.swap_type,
      requester_schedule_id: form.value.requester_schedule_id!,
      target_id: form.value.target_id || undefined,
      target_schedule_id: form.value.target_schedule_id || undefined,
      reason: form.value.reason || undefined,
    })
    ElMessage.success('申请提交成功')
    emit('update:visible', false)
    emit('success')
  } catch {
    // interceptor handles
  } finally {
    submitting.value = false
  }
}

watch(() => props.visible, (val) => {
  if (val) {
    loadMySchedules()
    form.value = { swap_type: 'specified', requester_schedule_id: null, target_id: null, target_schedule_id: null, reason: '' }
  }
})
</script>

<style scoped>
/* 弹窗 — 覆盖全局 .el-dialog */
.swap-dialog :deep(.el-dialog) {
  border: 4px solid #000000 !important;
  border-radius: 4px !important;
  box-shadow: 10px 10px 0px 0px #000000 !important;
  background: #FFFDF5 !important;
}

.swap-dialog :deep(.el-dialog__header) {
  border-bottom: 3px solid #000000 !important;
  background: #FFFDF5 !important;
  padding: 16px 20px !important;
  margin: 0 !important;
}

.swap-dialog :deep(.el-dialog__title) {
  font-weight: 900 !important;
  color: #000000 !important;
  font-size: 16px !important;
  letter-spacing: 0.3px !important;
}

.swap-dialog :deep(.el-dialog__body) {
  padding: 20px !important;
  background: #FFFDF5 !important;
}

.swap-dialog :deep(.el-dialog__footer) {
  border-top: 3px solid #000000 !important;
  padding: 14px 20px !important;
  background: #FFFDF5 !important;
}

/* 表单标签 */
:deep(.el-form-item__label) {
  font-weight: 800 !important;
  color: #000000 !important;
  font-size: 13px !important;
  letter-spacing: 0.2px !important;
}

/* 单选按钮 Neo 风格 */
.neo-radio-group {
  display: flex !important;
  gap: 10px !important;
}

.neo-radio-group :deep(.el-radio) {
  margin-right: 0 !important;
}

.neo-radio-group :deep(.el-radio__label) {
  font-weight: 700 !important;
  font-size: 13px !important;
}

.neo-radio-group :deep(.el-radio__input) {
  border: 3px solid #000000 !important;
  box-shadow: 2px 2px 0px 0px #000000 !important;
  border-radius: 4px !important;
  transition: all 0.1s ease !important;
}

.neo-radio-group :deep(.el-radio__input.is-checked .el-radio__inner) {
  background: #3B82F6 !important;
  border-color: #000000 !important;
  box-shadow: 2px 2px 0px 0px #000000 !important;
}

.neo-radio-group :deep(.el-radio__input.is-checked + .el-radio__label) {
  font-weight: 900 !important;
  color: #000000 !important;
}

/* 字数统计 */
:deep(.el-textarea .el-input__count) {
  background: transparent !important;
  font-weight: 600 !important;
  font-size: 12px !important;
  color: #999999 !important;
}

/* ============================================
   移动端适配
   ============================================ */

@media (max-width: 768px) {
  .swap-dialog :deep(.el-dialog) {
    width: 95% !important;
    box-shadow: 6px 6px 0px 0px #000000 !important;
  }

  .btn-neo-primary,
  .btn-neo-ghost {
    width: 100% !important;
    justify-content: center !important;
  }
}
</style>
