<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    title="导出统计报表"
    width="400px"
    class="neo-dialog"
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
        <el-select v-model="form.orgId" placeholder="全部组织" clearable class="neo-input" style="width: 100%">
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
      <el-button class="btn-neo-ghost" :disabled="exporting" @click="emit('update:visible', false)">取消</el-button>
      <el-button :loading="exporting" class="btn-neo-primary" @click="handleExport">
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

<style scoped>
/* Neo 表单控件样式 */
:deep(.el-dialog) {
  border: 4px solid #000000 !important;
  border-radius: 4px !important;
  box-shadow: 8px 8px 0px 0px #000000 !important;
}

:deep(.el-dialog__header) {
  border-bottom: 3px solid #000000 !important;
  background: #FFFDF5 !important;
  padding: 16px 20px !important;
}

:deep(.el-dialog__title) {
  font-weight: 900 !important;
  color: #000000 !important;
  font-size: 18px !important;
}

:deep(.el-form-item__label) {
  font-weight: 700 !important;
  color: #000000 !important;
  font-size: 14px !important;
}

:deep(.el-date-editor.el-input__wrapper) {
  border: 3px solid #000000 !important;
  border-radius: 4px !important;
  box-shadow: 3px 3px 0px 0px #000000 !important;
  background: #FFFFFF !important;
}

:deep(.el-select .el-select__wrapper) {
  border: 3px solid #000000 !important;
  border-radius: 4px !important;
  box-shadow: 3px 3px 0px 0px #000000 !important;
  background: #FFFFFF !important;
}
</style>
