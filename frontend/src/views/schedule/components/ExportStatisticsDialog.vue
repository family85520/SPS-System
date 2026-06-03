<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    title="导出统计报表"
    width="400px"
    :close-on-click-modal="!exporting"
  >
    <el-form label-width="80px">
      <el-form-item label="日期范围">
        <el-date-picker
          v-model="form.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="选择组织">
        <el-select v-model="form.orgId" placeholder="全部组织" clearable style="width: 100%">
          <el-option
            v-for="org in orgList"
            :key="org.id"
            :label="org.name"
            :value="org.id"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button :disabled="exporting" @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="exporting" @click="handleExport">
        <el-icon><Download /></el-icon>
        导出
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { downloadStatisticsExcel } from '@/api/export'

interface OrgOption {
  id: number
  name: string
}

interface Props {
  visible: boolean
  startDate?: string
  endDate?: string
  orgId?: number
  orgList: OrgOption[]
}

const props = withDefaults(defineProps<Props>(), {
  startDate: '',
  endDate: '',
  orgId: undefined,
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const exporting = defineModel<boolean>('loading', { default: false })

const form = reactive({
  dateRange: [] as string[],
  orgId: undefined as number | undefined,
})

watch(
  () => props.visible,
  (val) => {
    if (val) {
      form.dateRange = props.startDate && props.endDate
        ? [props.startDate, props.endDate]
        : []
      form.orgId = props.orgId
    }
  },
  { immediate: true },
)

async function handleExport() {
  if (!form.dateRange || form.dateRange.length < 2) {
    ElMessage.warning('请选择日期范围')
    return
  }

  const [start_date, end_date] = form.dateRange
  const params = {
    start_date,
    end_date,
    org_id: form.orgId || undefined,
  }

  exporting.value = true
  try {
    await downloadStatisticsExcel(params)
    ElMessage.success('导出成功')
    emit('update:visible', false)
  } catch {
    // 拦截器已统一处理错误提示
  } finally {
    exporting.value = false
  }
}
</script>
