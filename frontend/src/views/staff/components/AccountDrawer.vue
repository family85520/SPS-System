<template>
  <el-drawer
    :model-value="visible"
    title="账号管理"
    size="420px"
    @close="$emit('update:visible', false)"
  >
    <template v-if="staff">
      <el-descriptions :column="1" border size="small" style="margin-bottom: 20px">
        <el-descriptions-item label="姓名">{{ staff.name }}</el-descriptions-item>
        <el-descriptions-item label="工号">{{ staff.employee_no }}</el-descriptions-item>
        <el-descriptions-item label="登录账号">{{ staff.account_username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="账号状态">
          <el-tag v-if="staff.has_account" :type="staff.account_status === 1 ? 'success' : 'danger'" size="small">
            {{ staff.account_status === 1 ? '启用' : '禁用' }}
          </el-tag>
          <el-tag v-else type="info" size="small">未创建</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 已有账号 -->
      <template v-if="staff.has_account">
        <el-divider content-position="left">账号操作</el-divider>
        <el-form label-width="80px">
          <el-form-item label="账号状态">
            <el-switch
              :model-value="staff.account_status === 1"
              active-text="启用"
              inactive-text="禁用"
              @change="handleToggleStatus"
            />
          </el-form-item>
          <el-form-item label="重置密码">
            <div style="display: flex; gap: 8px; width: 100%">
              <el-input v-model="newPassword" type="password" show-password placeholder="输入新密码（至少6位）" />
              <el-button type="warning" :loading="resetting" @click="handleResetPwd" :disabled="!newPassword || newPassword.length < 6">
                重置
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="角色标签">
            <div style="width: 100%">
              <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px;">
                <el-tag
                  v-for="tag in (staff.tags || [])"
                  :key="tag"
                  type="warning"
                  closable
                  @close="removeTag(tag)"
                >
                  {{ tag }}
                </el-tag>
                <span v-if="!staff.tags || staff.tags.length === 0" style="color: #909399; font-size: 13px">暂无标签</span>
              </div>
              <el-select
                v-model="newTag"
                filterable
                allow-create
                default-first-option
                placeholder="输入或选择标签后回车"
                size="small"
                style="width: 100%"
                @change="addTag"
              >
                <el-option
                  v-for="role in allRoles"
                  :key="role.id"
                  :label="role.name"
                  :value="role.name"
                />
              </el-select>
              <div style="font-size: 12px; color: #909399; margin-top: 4px">
                系统角色根据标签自动匹配
              </div>
            </div>
          </el-form-item>
          <el-form-item label="系统角色">
            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
              <el-tag
                v-for="roleName in (staff.account_roles || [])"
                :key="roleName"
                size="small"
                type="success"
              >
                {{ roleName }}
              </el-tag>
              <span v-if="!staff.account_roles || staff.account_roles.length === 0" style="color: #909399; font-size: 12px">无</span>
            </div>
          </el-form-item>
        </el-form>
      </template>

      <!-- 无账号：创建 -->
      <template v-else>
        <el-divider content-position="left">创建登录账号</el-divider>
        <p style="font-size: 12px; color: #909399; margin-bottom: 16px;">
          登录账号默认使用工号，创建后不可修改
        </p>
        <el-form label-width="80px">
          <el-form-item label="账号">
            <el-input :model-value="staff.employee_no" disabled />
          </el-form-item>
          <el-form-item label="初始密码" required>
            <el-input v-model="createPassword" type="password" show-password placeholder="请输入初始密码（至少6位）" />
          </el-form-item>
          <el-form-item label="首次改密">
            <el-switch v-model="createMustChangePwd" />
            <span style="font-size: 12px; color: #909399; margin-left: 8px">
              {{ createMustChangePwd ? '首次登录需修改密码' : '不提示修改密码' }}
            </span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="creating" @click="handleCreateAccount" style="width: 100%">
              创建账号
            </el-button>
          </el-form-item>
        </el-form>
      </template>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'
import type { Role } from '@/api/role'
import api from '@/api/index'

interface StaffItem {
  id: number
  name: string
  employee_no: string
  has_account: boolean
  account_username: string | null
  account_status: number | null
  account_roles: string[] | null
  tags: string[] | null
}

const props = defineProps<{
  visible: boolean
  staff: StaffItem | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'refresh'): void
}>()

const allRoles = ref<Role[]>([])
const newPassword = ref('')
const resetting = ref(false)
const newTag = ref('')

const createPassword = ref('')
const createMustChangePwd = ref(true)
const creating = ref(false)

async function loadRoles() {
  try {
    const res: any = await api.get('/roles/options')
    const list = Array.isArray(res) ? res : (res.data || [])
    allRoles.value = list
  } catch {
    allRoles.value = []
  }
}

async function handleToggleStatus(val: boolean) {
  if (!props.staff) return
  try {
    await request.put(`/api/staffs/${props.staff.id}/account`, {
      account_status: val ? 1 : 0,
    })
    ElMessage.success(val ? '已启用' : '已禁用')
    emit('refresh')
  } catch {}
}

async function handleResetPwd() {
  if (!props.staff || !newPassword.value) return
  resetting.value = true
  try {
    await request.put(`/api/staffs/${props.staff.id}/account`, {
      reset_password: newPassword.value,
    })
    ElMessage.success('密码已重置，下次登录需修改')
    newPassword.value = ''
    emit('refresh')
  } catch {} finally {
    resetting.value = false
  }
}

async function addTag(val: string) {
  if (!props.staff || !val) return
  const currentTags = [...(props.staff.tags || [])]
  if (currentTags.includes(val)) {
    newTag.value = ''
    return
  }
  currentTags.push(val)
  await updateStaffTags(currentTags)
  newTag.value = ''
}

async function removeTag(tag: string) {
  if (!props.staff) return
  const currentTags = (props.staff.tags || []).filter((t: string) => t !== tag)
  await updateStaffTags(currentTags)
}

async function updateStaffTags(tags: string[]) {
  if (!props.staff) return
  try {
    // 更新人员标签
    await request.put(`/api/staffs/${props.staff.id}`, { tags })
    // 同步标签到系统角色
    await request.put(`/api/staffs/${props.staff.id}/sync-roles`)
    ElMessage.success('标签和角色已同步')
    emit('refresh')
  } catch {}
}

async function handleCreateAccount() {
  if (!props.staff) return
  if (!createPassword.value || createPassword.value.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  creating.value = true
  try {
    let url = `/api/staffs/${props.staff.id}/account?password=${encodeURIComponent(createPassword.value)}`
    url += `&must_change_password=${createMustChangePwd.value}`
    await request.post(url)
    ElMessage.success('账号创建成功')
    createPassword.value = ''
    emit('refresh')
    emit('update:visible', false)
  } catch {} finally {
    creating.value = false
  }
}

watch(() => props.visible, async (val) => {
  if (val) {
    await loadRoles()
    newPassword.value = ''
    newTag.value = ''
    createPassword.value = ''
    createMustChangePwd.value = true
  }
})
</script>
