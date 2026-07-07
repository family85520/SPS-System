<template>
  <el-select
    :model-value="modelValue"
    :multiple="multiple"
    filterable
    remote
    :remote-method="handleSearch"
    :loading="loading"
    placeholder="搜索并选择人员"
    clearable
    style="width: 100%"
    @change="handleChange"
  >
    <el-option
      v-for="staff in filteredList"
      :key="staff.id"
      :label="staff.name"
      :value="staff.id"
    >
      <span class="font-weight-medium" style="float: left;">{{ staff.name }}</span>
      <span class="font-weight-medium" style="float: right; color: #666; font-size: 12px;">{{ staff.employee_no }}</span>
    </el-option>
  </el-select>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/api/index'

interface StaffItem {
  id: number
  name: string
  employee_no: string
  org_id: number
  status: number
}

const props = withDefaults(defineProps<{
  modelValue: number | number[] | null
  orgId?: number | null
  multiple?: boolean
  excludeIds?: number[]
}>(), {
  modelValue: null,
  orgId: null,
  multiple: false,
  excludeIds: () => [],
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: number | number[] | null): void
}>()

const loading = ref(false)
const staffList = ref<StaffItem[]>([])
const searchKeyword = ref('')

const filteredList = computed(() => {
  let list = staffList.value
  if (props.excludeIds.length > 0) {
    list = list.filter((s) => !props.excludeIds.includes(s.id))
  }
  return list
})

async function loadStaff() {
  loading.value = true
  try {
    const params: any = {}
    if (props.orgId) params.org_id = props.orgId
    const res: any = await api.get('/staffs/options', { params })
    const list = Array.isArray(res) ? res : (res.data || [])
    staffList.value = list
  } catch (e) {
    staffList.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch(keyword: string) {
  searchKeyword.value = keyword
}

function handleChange(val: number | number[] | null) {
  emit('update:modelValue', val)
}

watch(() => props.orgId, () => {
  loadStaff()
})

onMounted(() => {
  loadStaff()
})
</script>

<style scoped>
/* 人员选择器下拉选项样式 */
:deep(.el-select) {
  width: 100%;
}

:deep(.el-select .el-select__wrapper) {
  border: 3px solid #000000 !important;
  border-radius: 4px !important;
  box-shadow: 3px 3px 0px 0px #000000 !important;
  background: #FFFFFF !important;
  height: 40px !important;
  min-height: 40px !important;
  transition: all 0.1s ease !important;
}

:deep(.el-select .el-select__wrapper:hover) {
  box-shadow: 4px 4px 0px 0px #000000 !important;
}

:deep(.el-select .el-select__wrapper.is-focused) {
  box-shadow: 4px 4px 0px 0px #FFD93D !important;
  border-color: #000000 !important;
}

:deep(.el-option__label) {
  font-weight: 600 !important;
  font-size: 13px !important;
}

:deep(.el-option__content) {
  font-weight: 600 !important;
}
</style>
