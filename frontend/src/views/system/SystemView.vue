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
import { useSystemStore } from '@/stores/system'

const loading = ref(false)
const saving = ref(false)

const formData = ref<SystemConfig>({
  system_name: '排班管理系统',
  org_name: '',
  swap_approval_enabled: true,
  schedule_approval_enabled: false,
  admin_receive_all_notifications: 'true',
})

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

onMounted(() => {
  loadConfig()
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
