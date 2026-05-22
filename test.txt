<template>
  <div class="role-page">
    <!-- 左侧：角色列表 -->
    <div class="left-panel">
      <div class="panel-header">
        <h3>角色列表</h3>
        <el-button type="primary" size="small" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建角色
        </el-button>
      </div>

      <div class="role-list" v-loading="loading">
        <div
          v-for="role in roleList"
          :key="role.id"
          class="role-item"
          :class="{ active: selectedId === role.id }"
          @click="handleSelect(role)"
        >
          <div class="role-item-header">
            <span class="role-name">{{ role.name }}</span>
            <el-icon v-if="role.is_system" color="#909399" :size="14"><Lock /></el-icon>
            <el-tag v-if="role.is_system" size="small" type="info">内置</el-tag>
          </div>
          <div class="role-item-code">{{ role.code }}</div>
        </div>

        <el-empty v-if="!loading && roleList.length === 0" description="暂无角色" />
      </div>
    </div>

    <!-- 右侧：权限配置 -->
    <div class="right-panel">
      <template v-if="selectedId !== null && formData">
        <div class="panel-header">
          <h3>
            {{ isCreate ? '新建角色' : formData.name }}
            <el-tag v-if="!isCreate && formData.is_system" size="small" type="info" style="margin-left: 8px">内置</el-tag>
          </h3>
        </div>

        <div class="edit-form" v-loading="saving">
          <!-- 角色基本信息 -->
          <el-form
            ref="formRef"
            :model="formData"
            :rules="rules"
            label-width="90px"
            label-position="right"
            style="margin-bottom: 24px"
          >
            <el-form-item label="角色名称" prop="name">
              <el-input
                v-model="formData.name"
                placeholder="请输入角色名称"
              />
            </el-form-item>
            <el-form-item v-if="isCreate" label="角色编码" prop="code">
              <el-input v-model="formData.code" placeholder="如 custom_role" />
            </el-form-item>
            <el-form-item v-else label="角色编码">
              <el-input :model-value="formData.code" disabled />
            </el-form-item>
          </el-form>

          <!-- 权限矩阵 -->
          <div class="permission-section">
            <h4>权限配置</h4>
            <el-table :data="permissionModules" border size="small" style="width: 100%">
              <el-table-column prop="label" label="功能模块" width="140" />
              <el-table-column v-for="action in actions" :key="action.key" :label="action.label" width="80" align="center">
                <template #default="{ row }">
                  <el-checkbox
                    v-model="permissionMap[row.key][action.key]"
                    @change="handlePermissionChange"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="form-actions">
            <el-button type="primary" @click="handleSave">保存</el-button>
            <el-button v-if="!isCreate && !formData.is_system" type="danger" @click="handleDelete">删除</el-button>
            <el-button @click="handleCancel">取消</el-button>
          </div>
        </div>
      </template>

      <div v-else class="empty-state">
        <el-icon :size="48" color="#C0C4CC"><UserFilled /></el-icon>
        <p>请从左侧选择角色或点击"新建角色"</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Lock, UserFilled } from '@element-plus/icons-vue'
import {
  getRoles,
  createRole,
  updateRole,
  deleteRole,
  type Role,
  type RoleCreate,
  type RoleUpdate,
} from '@/api/role'

// 状态
const loading = ref(false)
const saving = ref(false)
const roleList = ref<Role[]>([])
const selectedId = ref<number | null>(null)
const isCreate = ref(false)
const formRef = ref<FormInstance>()

// 权限模块定义
const permissionModules = [
  { key: 'organization', label: '组织管理' },
  { key: 'staff', label: '人员管理' },
  { key: 'shift_template', label: '班次模板' },
  { key: 'constraint', label: '约束规则' },
  { key: 'schedule', label: '排班管理' },
  { key: 'swap', label: '调班管理' },
  { key: 'message', label: '消息中心' },
  { key: 'export', label: '数据导出' },
]

const actions = [
  { key: 'read', label: '查看' },
  { key: 'create', label: '创建' },
  { key: 'update', label: '编辑' },
  { key: 'delete', label: '删除' },
  { key: 'publish', label: '发布' },
  { key: 'approve', label: '审批' },
]

// 权限矩阵响应式对象
function createEmptyPermissionMap(): Record<string, Record<string, boolean>> {
  const map: Record<string, Record<string, boolean>> = {}
  permissionModules.forEach((m) => {
    map[m.key] = {}
    actions.forEach((a) => {
      map[m.key][a.key] = false
    })
  })
  return map
}

const permissionMap = reactive<Record<string, Record<string, boolean>>>(createEmptyPermissionMap())

const defaultForm = {
  name: '',
  code: '',
  permissions: {} as Record<string, any>,
  is_system: false,
}

const formData = ref({ ...defaultForm })

const rules: FormRules = {
  name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' },
    { max: 50, message: '角色名称不能超过50个字符', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入角色编码', trigger: 'blur' },
    { max: 30, message: '角色编码不能超过30个字符', trigger: 'blur' },
  ],
}

// 将 permissions 对象转为权限矩阵
function loadPermissionsToMap(permissions: Record<string, any> | null) {
  // 先清空
  permissionModules.forEach((m) => {
    actions.forEach((a) => {
      permissionMap[m.key][a.key] = false
    })
  })

  if (!permissions) return

  // all=true 表示全部权限
  if (permissions.all === true) {
    permissionModules.forEach((m) => {
      actions.forEach((a) => {
        permissionMap[m.key][a.key] = true
      })
    })
    return
  }

  // 按模块加载
  for (const [moduleKey, moduleActions] of Object.entries(permissions)) {
    if (Array.isArray(moduleActions) && permissionMap[moduleKey]) {
      moduleActions.forEach((action: string) => {
        if (permissionMap[moduleKey][action] !== undefined) {
          permissionMap[moduleKey][action] = true
        }
      })
    }
  }
}

// 将权限矩阵转为 permissions 对象
function saveMapToPermissions(): Record<string, string[]> {
  const permissions: Record<string, string[]> = {}
  permissionModules.forEach((m) => {
    const enabledActions: string[] = []
    actions.forEach((a) => {
      if (permissionMap[m.key][a.key]) {
        enabledActions.push(a.key)
      }
    })
    if (enabledActions.length > 0) {
      permissions[m.key] = enabledActions
    }
  })
  return permissions
}

function handlePermissionChange() {
  // 权限变化时触发
}

// 加载列表
async function loadList() {
  loading.value = true
  try {
    roleList.value = await getRoles()
  } catch (e) {
    // interceptor handles error
  } finally {
    loading.value = false
  }
}

// 选择角色
function handleSelect(role: Role) {
  isCreate.value = false
  selectedId.value = role.id
  formData.value = {
    name: role.name,
    code: role.code,
    permissions: role.permissions || {},
    is_system: role.is_system,
  }
  loadPermissionsToMap(role.permissions)
}

// 新建
function handleCreate() {
  isCreate.value = true
  selectedId.value = -1
  formData.value = { ...defaultForm }
  loadPermissionsToMap(null)
}

// 保存
async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const permissions = saveMapToPermissions()
  saving.value = true

  try {
    if (isCreate.value) {
      const payload: RoleCreate = {
        name: formData.value.name,
        code: formData.value.code,
        permissions,
      }
      await createRole(payload)
      ElMessage.success('创建成功')
      await loadList()
      isCreate.value = false
    } else {
      const payload: RoleUpdate = {
        name: formData.value.name,
        permissions,
      }
      await updateRole(selectedId.value!, payload)
      ElMessage.success('保存成功')
      await loadList()
    }
  } catch (e) {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

// 删除
async function handleDelete() {
  if (!selectedId.value) return
  try {
    await ElMessageBox({
      title: '确认删除？',
      message: '删除后数据无法恢复，请慎重操作。',
      showCancelButton: true,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteRole(selectedId.value)
    ElMessage.success('删除成功')
    selectedId.value = null
    await loadList()
  } catch (e) {
    // cancel or error
  }
}

// 取消
function handleCancel() {
  selectedId.value = null
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.role-page {
  display: flex;
  height: calc(100vh - 56px - 40px);
  gap: 16px;
  padding: 16px;
  background: #F5F7FA;
  overflow-x: auto;
  min-width: 700px;
}

/* 左侧列表 */
.left-panel {
  width: 280px;
  min-width: 240px;
  background: #FFFFFF;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(31, 45, 61, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #E6EAF0;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1F2D3D;
}

.role-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.role-item {
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
  border: 2px solid transparent;
}

.role-item:hover {
  background: #F5F7FA;
}

.role-item.active {
  background: #ECF5FF;
  border-color: #0A63D8;
}

.role-item-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.role-name {
  font-size: 14px;
  font-weight: 600;
  color: #1F2D3D;
}

.role-item-code {
  font-size: 12px;
  color: #909399;
  padding-left: 2px;
}

/* 右侧编辑 */
.right-panel {
  flex: 1;
  min-width: 400px;
  background: #FFFFFF;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(31, 45, 61, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.edit-form {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px 24px;
}

.permission-section {
  margin-bottom: 24px;
}

.permission-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1F2D3D;
}

.form-actions {
  display: flex;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid #E6EAF0;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #C0C4CC;
}

.empty-state p {
  margin-top: 16px;
  font-size: 14px;
}
</style>
