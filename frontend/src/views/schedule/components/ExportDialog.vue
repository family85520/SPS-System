<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    title="导出排班表"
    width="520px"
    :close-on-click-modal="!exporting"
  >
    <el-form label-width="80px">
      <el-form-item label="导出格式">
        <el-radio-group v-model="form.format">
          <el-radio value="excel">Excel</el-radio>
          <el-radio value="pdf">PDF</el-radio>
        </el-radio-group>
      </el-form-item>

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

      <el-form-item label="导出维度">
        <el-radio-group v-model="form.dimension">
          <el-radio value="org">按组织</el-radio>
          <el-radio value="person">按人员</el-radio>
        </el-radio-group>
        <div style="font-size: 12px; color: #909399; margin-top: 4px;">
          按组织：每日每班次一行　|　按人员：每人一行，日期为列
        </div>
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

    <template v-if="form.format === 'excel' && form.dimension === 'org'">
    <el-divider content-position="left">
      <span style="display:flex;align-items:center;gap:4px;">
        自定义模板（仅「按组织 + Excel」可用）
        <el-tooltip placement="top" content="自定义模板仅对「按组织维度导出 Excel」生效，PDF / 按人员 / 统计报表不适用。">
          <span style="color:#909399;cursor:help;">ⓘ</span>
        </el-tooltip>
      </span>
    </el-divider>
    <div style="font-size:12px;color:#909399;margin-bottom:6px;">
      上传自定义 .xlsx 模板，使用下方变量定制排班表样式。
    </div>

    <!-- 变量列表 -->
    <details style="margin-bottom:8px;">
      <summary style="cursor:pointer;font-size:13px;color:#409eff;">查看可用变量 / 操作指南（点击展开）</summary>
      <div v-if="variables.length" style="margin-top:6px;max-height:280px;overflow-y:auto;background:#f8f9fb;padding:10px;border-radius:4px;font-size:11px;line-height:1.9;">
        <div style="margin-bottom:10px;color:#606266;">
          <b>📋 使用步骤：</b><br/>
          1. 下载默认模板或手写 .xlsx，在单元格填入下方变量<br/>
          2. 上传模板，设为默认<br/>
          3. 导出排班表时自动套用<br/>
          <span style="color:#909399;">💡 变量有<u>索引</u>和<u>名称</u>两种写法，效果完全相同，任选一种。</span>
        </div>
        <div v-for="g in varGroups" :key="g.name" style="margin-bottom:4px;">
          <b style="color:#303133;">{{ g.name }}</b>
          <div style="padding-left:12px;">
            <span v-for="v in g.items" :key="v.name"
                  style="display:inline-block;margin:1px 4px;padding:1px 6px;background:#e8ecf1;border-radius:3px;color:#555;"
                  :title="v.desc + (v.example ? ' → ' + v.example : '')">
              {{ v.name }}
            </span>
          </div>
        </div>
      </div>
      <div v-else style="font-size:11px;color:#999;margin-top:4px;">加载变量列表中...</div>
    </details>

    <div v-for="tpl in templates" :key="tpl.id" style="display:flex;align-items:center;gap:8px;margin-bottom:6px;padding:6px 8px;background:#f5f7fa;border-radius:4px">
      <span style="flex:1;font-size:13px;">{{ tpl.name }}<el-tag v-if="tpl.is_default" size="small" type="success" style="margin-left:6px;">默认</el-tag></span>
      <el-button v-if="!tpl.is_default" size="small" @click="setDefault(tpl.id)">设为默认</el-button>
      <el-button size="small" type="danger" @click="removeTemplate(tpl.id)">删除</el-button>
    </div>

    <div style="margin-top:8px;display:flex;gap:8px;">
      <input ref="fileInput" type="file" accept=".xlsx" style="display:none" @change="onFileChange" />
      <el-button size="small" @click="downloadDefaultTemplate">
        <el-icon><Download /></el-icon> 下载默认模板
      </el-button>
      <el-button size="small" @click="($refs.fileInput as HTMLInputElement).click()">
        <el-icon><Upload /></el-icon> 上传模板
      </el-button>
      <span v-if="uploadName" style="font-size:12px;margin-left:8px;color:#409eff;">{{ uploadName }}</span>
    </div>
    </template>

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
import { reactive, watch, ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import {
  downloadScheduleExcel,
  downloadSchedulePdf,
  listTemplates,
  uploadTemplate,
  deleteTemplate,
  setDefaultTemplate,
  type ExportTemplateItem,
} from '@/api/export'
import api from '@/api/index'

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
  format: 'excel' as 'excel' | 'pdf',
  dateRange: [] as string[],
  dimension: 'org' as 'org' | 'person',
  orgId: undefined as number | undefined,
})

// 同步外部默认值
watch(
  () => props.visible,
  (val) => {
    if (val) {
      form.dateRange = props.startDate && props.endDate
        ? [props.startDate, props.endDate]
        : []
      form.orgId = props.orgId
      form.format = 'excel'
      form.dimension = 'org'
    }
  },
  { immediate: true },
)

// ===== 模板管理 =====
const templates = ref<ExportTemplateItem[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const uploadName = ref('')
let uploadFile: File | null = null

interface VarItem { name: string; desc: string; category: string; example: string }
const variables = ref<VarItem[]>([])

const varGroups = computed(() => {
  const groups: Record<string, VarItem[]> = {}
  for (const v of variables.value) {
    if (!groups[v.category]) groups[v.category] = []
    groups[v.category].push(v)
  }
  return Object.entries(groups).map(([name, items]) => ({ name, items }))
})

async function loadTemplates() {
  try {
    templates.value = await listTemplates()
    const res = await api.get('/export/templates/variables')
    variables.value = (res as any).variables ?? []
  } catch { templates.value = [] }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    uploadFile = input.files[0]
    uploadName.value = uploadFile.name
    // Auto-upload when file selected
    doUpload()
  }
}

async function doUpload() {
  if (!uploadFile) return
  try {
    const name = uploadFile.name.replace('.xlsx', '')
    await uploadTemplate(uploadFile, name, templates.value.length === 0, '')
    ElMessage.success('模板上传成功')
    uploadName.value = ''
    uploadFile = null
    await loadTemplates()
  } catch { /* handled by interceptor */ }
}

async function setDefault(id: number) {
  try {
    await setDefaultTemplate(id)
    ElMessage.success('已设为默认模板')
    await loadTemplates()
  } catch { /* handled */ }
}

async function removeTemplate(id: number) {
  try {
    await ElMessageBox.confirm('确认删除该模板？', '删除模板', { type: 'warning' })
    await deleteTemplate(id)
    ElMessage.success('删除成功')
    await loadTemplates()
  } catch { /* cancelled or error */ }
}

async function downloadDefaultTemplate() {
  try {
    const res = await api.get('/export/templates/default/download', { responseType: 'blob', timeout: 15000 })
    const url = window.URL.createObjectURL(res as any)
    const a = document.createElement('a'); a.href = url; a.download = '排班表模板.xlsx'
    a.click(); window.URL.revokeObjectURL(url)
  } catch { ElMessage.error('下载失败') }
}

onMounted(loadTemplates)

async function handleExport() {
  if (!form.dateRange || form.dateRange.length < 2) {
    ElMessage.warning('请选择日期范围')
    return
  }

  const [start_date, end_date] = form.dateRange
  const baseParams = {
    start_date,
    end_date,
    org_id: form.orgId || undefined,
  }

  exporting.value = true
  try {
    if (form.format === 'excel') {
      await downloadScheduleExcel({
        ...baseParams,
        dimension: form.dimension,
      })
    } else {
      await downloadSchedulePdf({
        ...baseParams,
        dimension: form.dimension,
      })
    }
    ElMessage.success('导出成功')
    emit('update:visible', false)
  } catch {
    // 拦截器已统一处理错误提示
  } finally {
    exporting.value = false
  }
}
</script>
