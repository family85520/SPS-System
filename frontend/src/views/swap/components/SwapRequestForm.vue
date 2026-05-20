<template>
  <el-dialog
    :model-value="visible"
    title="发起调班申请"
    width="600px"
    @close="$emit('update:visible', false)"
  >
    <el-form :model="form" label-width="100px" ref="formRef" :rules="rules">
      <el-form-item label="调班类型" prop="swap_type">
        <el-radio-group v-model="form.swap_type" @change="onTypeChange">
          <el-radio value="specified">指定换班</el-radio>
          <el-radio value="open">开放换班</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="我的班次" prop="requester_schedule_id">
        <el-select v-model="form.requester_schedule_id" placeholder="选择要换的班次" style="width: 100%">
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
          <el-select v-model="form.target_schedule_id" placeholder="选择对方班次" style="width: 100%">
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
    </el-form>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">提交申请</el-button>
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
    const { data: res } = await getMySchedules({ staff_id: authStore.staffId })
    mySchedules.value = res.items || []
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
    const { data: res } = await request.get('/api/staffs', { params: { keyword, page: 1, page_size: 50 } })
    targetUsers.value = (res.items || []).map((s: any) => ({ id: s.id, name: s.name }))
  } catch {
    targetUsers.value = []
  } finally {
    targetLoading.value = false
  }
}

const onTargetChange = async (targetStaffId: number) => {
  form.value.target_schedule_id = null
  try {
    const { data: res } = await request.get('/api/schedules', {
      params: { staff_id: targetStaffId, page: 1, page_size: 50 },
    })
    targetSchedules.value = res.items || []
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
