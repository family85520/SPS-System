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
      <span style="float: left">{{ staff.name }}</span>
      <span style="float: right; color: #909399; font-size: 12px">{{ staff.employee_no }}</span>
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
    const params: any = { status: 1 }
    if (props.orgId) params.org_id = props.orgId
    const res: any = await api.get('/staffs', { params })
    staffList.value = Array.isArray(res) ? res : (res.items || [])
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
