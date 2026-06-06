<template>
  <div class="system-page">
    <div class="page-header">
      <h3>系统配置</h3>
    </div>

    <div class="page-content" v-loading="loading">
      <el-form
        :model="formData"
        label-width="120px"
        label-position="right"
        style="max-width: 600px"
      >
        <el-form-item label="系统名称">
          <el-input v-model="formData.system_name" placeholder="请输入系统名称" />
        </el-form-item>

        <el-form-item label="单位名称">
          <el-input v-model="formData.org_name" placeholder="请输入单位名称" />
        </el-form-item>

        <el-form-item label="调班审批开关">
          <el-switch
            v-model="formData.swap_approval_enabled"
            active-text="开启"
            inactive-text="关闭"
          />
          <div class="form-tip">
            开启后，调班申请需管理员审批；关闭后，双方确认即自动生效
          </div>
        </el-form-item>

        <el-form-item label="排班审核开关">
          <el-switch
            v-model="formData.schedule_approval_enabled"
            active-text="开启"
            inactive-text="关闭"
          />
          <div class="form-tip">
            开启后，排班发布需管理员审核通过；关闭后，排班管理员可直接发布
          </div>
        </el-form-item>

        <el-form-item label="管理员接收全部通知">
          <el-switch
            v-model="formData.admin_receive_all_notifications"
            active-text="开启"
            inactive-text="关闭"
            active-value="true"
            inactive-value="false"
          />
          <div class="form-tip">开启后管理员将收到所有排班发布、撤回等通知，无论是否参与排班</div>
        </el-form-item>

        <el-form-item label="全局排班人数比例">
          <el-input-number
            v-model="formData.daily_max_scheduled_ratio"
            :min="0.1"
            :max="1.0"
            :step="0.05"
            :precision="2"
            controls-position="right"
            style="width: 200px"
          />
          <div class="form-tip">每日排班人数占在岗人员的默认比例上限（如0.70=70%），各组织可在组织管理中覆盖此值</div>
        </el-form-item>

        <el-divider content-position="left">每月自动排班</el-divider>

        <el-form-item label="启用自动排班">
          <el-switch v-model="formData.auto_schedule_enabled" active-text="开启" inactive-text="关闭"
            active-value="true" inactive-value="false" />
          <div class="form-tip">开启后，每月最后一天按指定时间自动生成下月排班</div>
        </el-form-item>

        <el-form-item label="触发时间">
          <el-time-select
            v-model="formData.auto_schedule_time"
            placeholder="选择时间"
            start="00:00"
            step="00:30"
            end="23:30"
            format="HH:mm"
            style="width: 150px"
          />
          <div class="form-tip">每月最后一天此时间触发（默认 23:00）</div>
        </el-form-item>

        <el-form-item label="排班组织">
          <el-select v-model="formData.auto_schedule_org_ids" multiple placeholder="全部组织"
            style="width: 100%" clearable>
            <el-option v-for="org in orgOptions" :key="org.id" :label="org.name" :value="org.id" />
          </el-select>
          <div class="form-tip">不选 = 所有启用组织</div>
        </el-form-item>

        <el-form-item label="排班班次">
          <el-select v-model="formData.auto_schedule_shift_ids" multiple placeholder="全部启用班次"
            style="width: 100%" clearable>
            <el-option v-for="s in shiftOptions" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
          <div class="form-tip">不选 = 各组织全部启用班次模板</div>
        </el-form-item>

        <el-form-item label="跳过已有排班">
          <el-switch v-model="formData.auto_schedule_skip_existing" active-text="是" inactive-text="否"
            active-value="true" inactive-value="false" />
          <div class="form-tip">如果下月已有排班数据，跳过不覆盖</div>
        </el-form-item>

        <el-form-item label="排班状态">
          <el-radio-group v-model="formData.auto_schedule_status">
            <el-radio value="draft">草稿（可手动调整）</el-radio>
            <el-radio value="published">直接发布</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="formData.auto_schedule_last_run" label="上次执行">
          <span style="color:#909399;">{{ formData.auto_schedule_last_run }}</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSystemConfig, updateSystemConfig, type SystemConfig } from '@/api/system'
import { getOrgList } from '@/api/organization'
import { getShiftTemplates } from '@/api/shift-template'
import { useSystemStore } from '@/stores/system'

const loading = ref(false)
const saving = ref(false)

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
  } catch (e) {
    // interceptor handles error
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const res = await updateSystemConfig(formData.value)
    formData.value = res
    // 更新全局 store
    const systemStore = useSystemStore()
    systemStore.systemName = res.system_name
    systemStore.orgName = res.org_name
    systemStore.swapApprovalEnabled = res.swap_approval_enabled
    localStorage.setItem('scheduleApproval', String(res.schedule_approval_enabled))
    localStorage.setItem('systemName', res.system_name)
    localStorage.setItem('orgName', res.org_name)
    localStorage.setItem('swapApproval', String(res.swap_approval_enabled))
    ElMessage.success('保存成功')
  } catch (e) {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

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
.system-page {
  background: #FFFFFF;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(31, 45, 61, 0.06);
  overflow: hidden;
}

.page-header {
  padding: 16px 24px;
  border-bottom: 1px solid #E6EAF0;
}

.page-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1F2D3D;
}

.page-content {
  padding: 24px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.5;
}

.config-tip {
  font-size: 12px;
  color: #8492a6;
  margin-left: 8px;
}
</style>
