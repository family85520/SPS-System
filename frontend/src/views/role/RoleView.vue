<template>
  <div class="role-page">
    <!-- 页面标题栏 -->
    <div class="page-topbar">
      <div class="page-topbar-left">
        <h2 class="page-title">角色权限管理</h2>
        <p class="page-subtitle">管理系统角色、权限配置与人员标识</p>
      </div>
      <el-button class="btn-neo-primary btn-neo-sm" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        <span>新建角色</span>
      </el-button>
    </div>

    <div class="workspace">
      <!-- 左侧：角色列表 -->
      <div class="left-panel neo-card">
        <div class="panel-header">
          <h3 class="panel-title">
            <el-icon class="panel-icon"><User /></el-icon>
            角色列表
          </h3>
          <span class="role-count-badge">{{ roleList.length }} 个角色</span>
        </div>

        <div class="role-list" v-loading="loading" element-loading-text="加载中...">
          <div
            v-for="(role, index) in roleList"
            :key="role.id"
            class="role-item"
            :class="{ active: selectedId === role.id }"
            :style="{ animationDelay: `${index * 0.05}s` }"
            @click="handleSelect(role)"
          >
            <div class="role-item-top">
              <div class="role-item-avatar" :style="{ background: roleAvatarBg(role) }">
                <el-icon :size="18"><component :is="roleAvatarIcon(role)" /></el-icon>
              </div>
              <div class="role-item-info">
                <div class="role-item-name">{{ role.name }}</div>
                <div class="role-item-code">{{ role.code }}</div>
              </div>
            </div>
            <div class="role-item-meta">
              <el-tag v-if="role.is_system" size="small" type="info">内置</el-tag>
              <el-tag v-if="role.role_type === 'tag'" size="small" type="warning">标识</el-tag>
              <el-tag v-else-if="!role.is_system" size="small" type="success">角色</el-tag>
              <el-icon class="role-item-arrow"><ArrowRight /></el-icon>
            </div>
          </div>

          <div v-if="!loading && roleList.length === 0" class="role-empty">
            <el-icon :size="48" color="#C4B5FD"><UserFilled /></el-icon>
            <p>暂无角色</p>
            <span>点击「新建角色」开始创建</span>
          </div>
        </div>
      </div>

      <!-- 右侧：权限配置 -->
      <div class="right-panel" v-if="selectedId !== null && formData">
        <div class="right-panel neo-card right-panel--active">
          <!-- 编辑头部 -->
          <div class="edit-header">
            <div class="edit-header-left">
              <h3 class="edit-title">
                {{ isCreate ? (formData.role_type === 'tag' ? '新建标识' : '新建角色') : formData.name }}
                <el-tag v-if="!isCreate && formData.is_system" size="small" type="info">内置</el-tag>
                <el-tag v-if="!isCreate && formData.role_type === 'tag'" size="small" type="warning">标识</el-tag>
              </h3>
              <p class="edit-subtitle">{{ isCreate ? '配置角色基本信息与权限' : formData.code }}</p>
            </div>
            <el-button class="btn-neo-ghost btn-neo-sm" @click="selectedId = null">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>

          <div class="edit-form" v-loading="saving" element-loading-text="保存中...">
            <!-- 角色基本信息 -->
            <div class="form-section">
              <div class="form-section-header">
                <el-icon class="form-section-icon"><Setting /></el-icon>
                <span class="form-section-title">基本信息</span>
              </div>

              <el-form
                ref="formRef"
                :model="formData"
                :rules="rules"
                label-width="100px"
                label-position="right"
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
                <el-form-item v-if="isCreate || !formData.is_system" label="类型" :prop="isCreate ? 'role_type' : undefined">
                  <div class="radio-card-group">
                    <label class="radio-card" :class="{ 'radio-card--active': formData.role_type === 'role' }">
                      <input type="radio" name="role_type" value="role" v-model="formData.role_type" @change="handleTypeChange" />
                      <div class="radio-card__content">
                        <div class="radio-card__title">角色</div>
                        <div class="radio-card__desc">可配置功能权限，用于控制菜单与操作访问</div>
                      </div>
                    </label>
                    <label class="radio-card" :class="{ 'radio-card--active': formData.role_type === 'tag' }">
                      <input type="radio" name="role_type" value="tag" v-model="formData.role_type" @change="handleTypeChange" />
                      <div class="radio-card__content">
                        <div class="radio-card__title">标识</div>
                        <div class="radio-card__desc">仅标记人员身份（如"领导"、"新员工"），无需配置权限</div>
                      </div>
                    </label>
                  </div>
                </el-form-item>
                <el-form-item v-else label="类型">
                  <el-tag type="success">角色（内置）</el-tag>
                </el-form-item>
              </el-form>
            </div>

            <!-- 权限矩阵（标识类型隐藏） -->
            <template v-if="formData.role_type !== 'tag'">
            <div class="form-section">
              <div class="form-section-header">
                <el-icon class="form-section-icon"><Lock /></el-icon>
                <span class="form-section-title">权限配置</span>
                <span class="perm-count-badge">{{ permissionCount }} / {{ totalActions }} 项授权</span>
              </div>

              <div class="permission-table-wrapper">
                <el-table
                  :data="permissionModules"
                  border
                  size="default"
                  style="width: 100%"
                >
                  <el-table-column prop="label" label="功能模块" width="160" fixed>
                    <template #default="{ row }">
                      <div class="perm-module-cell">
                        <div class="perm-module-icon" :style="{ background: moduleColor(row.key) }">
                          <el-icon :size="18"><component :is="moduleIcon(row.key)" /></el-icon>
                        </div>
                        <span class="perm-module-label">{{ row.label }}</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column
                    v-for="action in actions"
                    :key="action.key"
                    :label="action.label"
                    :width="90"
                    align="center"
                  >
                    <template #default="{ row }">
                      <el-checkbox
                        v-model="permissionMap[row.key][action.key]"
                        :disabled="isActionDisabled(row, action)"
                        @change="handlePermissionChange"
                      >
                        <template #default>
                          <span :class="{ 'perm-action-dimmed': isActionDisabled(row, action) }">{{ action.label }}</span>
                        </template>
                      </el-checkbox>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
            </template>

            <div v-if="formData.role_type === 'tag'" class="tag-hint">
              <div class="alert-card alert-card--info">
                <el-icon :size="24"><InfoFilled /></el-icon>
                <div class="alert-card__content">
                  标识类型的角色仅用于在排班时识别人员身份（如"领导"、"新员工"），无需配置权限。创建后可在"人员管理"中为人员分配此标识。
                </div>
              </div>
            </div>

            <div class="form-actions">
              <el-button class="btn-neo-primary" @click="handleSave">
                <el-icon><Check /></el-icon>
                <span>保存</span>
              </el-button>
              <el-button v-if="!isCreate && !formData.is_system" class="btn-neo-danger" @click="handleDelete">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
              <el-button class="btn-neo-ghost" @click="handleCancel">
                <el-icon><Close /></el-icon>
                <span>取消</span>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <div class="empty-state-icon-wrap">
          <el-icon :size="64"><UserFilled /></el-icon>
        </div>
        <p class="empty-state-title">选择或创建一个角色</p>
        <p class="empty-state-desc">从左侧列表选择一个角色进行编辑，或点击「新建角色」开始创建</p>
        <el-button class="btn-neo-primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          <span>新建角色</span>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useConfirm } from '@/composables/useConfirm'
import {
  Plus, Lock, UserFilled, Close, Check, Delete, ArrowRight,
  Setting, InfoFilled, User, Menu, Document, ChatDotRound,
  Calendar, Star, Connection,
} from '@element-plus/icons-vue'
import {
  getRoles,
  createRole,
  updateRole,
  deleteRole,
  getPermissionSchema,
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

const { confirm } = useConfirm()

// 权限模块和操作定义（从后端动态加载）
const permissionModules = ref<Array<{ key: string; label: string; actions: string[] }>>([])
const actions = ref<Array<{ key: string; label: string }>>([])
const supportedActionsMap = ref<Record<string, Set<string>>>({})

// 模块颜色映射
const moduleColors: Record<string, string> = {
  organization: '#3B82F6',
  staff: '#10B981',
  schedule: '#FFD93D',
  constraint: '#C4B5FD',
  swap: '#06B6D4',
  message: '#FF6B6B',
  role: '#8B5CF6',
  system: '#666666',
}

// 模块图标映射
const moduleIconMap: Record<string, any> = {
  organization: Menu,
  staff: User,
  schedule: Calendar,
  constraint: Document,
  swap: Connection,
  message: ChatDotRound,
  role: Lock,
  system: Setting,
}

function moduleColor(key: string): string {
  return moduleColors[key] || '#E5E7EB'
}

function moduleIcon(key: string) {
  return moduleIconMap[key] || Menu
}

// 统计已授权的 action 数量
const permissionCount = computed(() => {
  let count = 0
  permissionModules.value.forEach((m) => {
    actions.value.forEach((a) => {
      if (permissionMap[m.key]?.[a.key]) count++
    })
  })
  return count
})

const totalActions = computed(() => {
  let total = 0
  permissionModules.value.forEach((m) => {
    actions.value.forEach((a) => {
      if (isActionSupported(m.key, a.key)) total++
    })
  })
  return total
})

// 角色头像背景色
const roleAvatarColors = ['#3B82F6', '#10B981', '#FFD93D', '#C4B5FD', '#FF6B6B', '#06B6D4', '#8B5CF6']

function roleAvatarBg(role: Role): string {
  if (role.role_type === 'tag') return '#FFD93D'
  if (role.is_system) return '#E5E7EB'
  const hash = role.code.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0)
  return roleAvatarColors[hash % roleAvatarColors.length]
}

function roleAvatarIcon(role: Role) {
  if (role.role_type === 'tag') return Star
  if (role.is_system) return Lock
  return User
}

async function loadPermissionSchema() {
  try {
    const schema = await getPermissionSchema()
    permissionModules.value = schema.modules || []
    actions.value = schema.actions || []
    const map: Record<string, Set<string>> = {}
    schema.modules.forEach((m: any) => {
      map[m.key] = new Set(m.actions)
    })
    supportedActionsMap.value = map
  } catch {
    permissionModules.value = []
    actions.value = []
    supportedActionsMap.value = {}
  }
  Object.assign(permissionMap, createEmptyPermissionMap())
}

function createEmptyPermissionMap(): Record<string, Record<string, boolean>> {
  const map: Record<string, Record<string, boolean>> = {}
  permissionModules.value.forEach((m) => {
    map[m.key] = {}
    actions.value.forEach((a) => {
      map[m.key][a.key] = false
    })
  })
  return map
}

const permissionMap = reactive<Record<string, Record<string, boolean>>>(createEmptyPermissionMap())

const defaultForm = {
  name: '',
  code: '',
  role_type: 'role' as string,
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

function loadPermissionsToMap(permissions: Record<string, any> | null) {
  permissionModules.value.forEach((m) => {
    actions.value.forEach((a) => {
      permissionMap[m.key][a.key] = false
    })
  })

  if (!permissions) return

  if (permissions.all === true) {
    permissionModules.value.forEach((m) => {
      actions.value.forEach((a) => {
        if (isActionSupported(m.key, a.key)) {
          permissionMap[m.key][a.key] = true
        }
      })
    })
    return
  }

  for (const [moduleKey, moduleActions] of Object.entries(permissions)) {
    if (Array.isArray(moduleActions) && permissionMap[moduleKey]) {
      moduleActions.forEach((action: string) => {
        if (permissionMap[moduleKey][action] !== undefined && isActionSupported(moduleKey, action)) {
          permissionMap[moduleKey][action] = true
        }
      })
    }
  }
}

function saveMapToPermissions(): Record<string, string[]> {
  const permissions: Record<string, string[]> = {}
  permissionModules.value.forEach((m) => {
    const enabledActions: string[] = []
    actions.value.forEach((a) => {
      if (permissionMap[m.key][a.key] && isActionSupported(m.key, a.key)) {
        enabledActions.push(a.key)
      }
    })
    if (enabledActions.length > 0) {
      permissions[m.key] = enabledActions
    }
  })
  return permissions
}

function isActionSupported(moduleKey: string, actionKey: string): boolean {
  const supported = supportedActionsMap.value[moduleKey]
  return supported ? supported.has(actionKey) : false
}

function isActionDisabled(moduleItem: any, actionItem: any): boolean {
  return !isActionSupported(moduleItem.key, actionItem.key)
}

function handlePermissionChange() {}

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

function handleSelect(role: Role) {
  isCreate.value = false
  selectedId.value = role.id
  formData.value = {
    name: role.name,
    code: role.code,
    role_type: role.role_type || 'role',
    permissions: role.permissions || {},
    is_system: role.is_system,
  }
  if (role.role_type !== 'tag') {
    loadPermissionsToMap(role.permissions)
  }
}

function handleCreate() {
  isCreate.value = true
  selectedId.value = -1
  formData.value = { ...defaultForm }
  loadPermissionsToMap(null)
}

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
        role_type: formData.value.role_type,
        permissions: formData.value.role_type === 'tag' ? undefined : permissions,
      }
      await createRole(payload)
      ElMessage.success('创建成功')
      await loadList()
      isCreate.value = false
    } else {
      const payload: RoleUpdate = {
        name: formData.value.name,
        role_type: formData.value.role_type,
        permissions: formData.value.role_type === 'tag' ? undefined : permissions,
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

async function handleDelete() {
  if (!selectedId.value) return
  try {
    await confirm({
      type: 'danger',
      title: '确认删除？',
      message: '删除后数据无法恢复，请慎重操作。',
      confirmText: '删除',
      cancelText: '取消',
    })
    await deleteRole(selectedId.value)
    ElMessage.success('删除成功')
    selectedId.value = null
    await loadList()
  } catch (e) {
    // cancel or error
  }
}

function handleCancel() {
  selectedId.value = null
}

function handleTypeChange() {
  if (formData.value.role_type === 'tag') {
    Object.assign(permissionMap, createEmptyPermissionMap())
  }
}

onMounted(async () => {
  await loadPermissionSchema()
  await loadList()
})
</script>

<style scoped>
.role-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px - 40px);
  gap: 16px;
  padding: 16px;
  background: #FFFDF5;
  overflow: hidden;
}

/* ========== 顶部栏 ========== */
.page-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 900;
  color: #000000;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.page-subtitle {
  font-size: 13px;
  font-weight: 600;
  color: #666666;
  margin: 4px 0 0 0;
}

/* ========== 工作区 ========== */
.workspace {
  flex: 1;
  display: flex;
  gap: 16px;
  overflow: hidden;
  min-height: 0;
}

/* ========== 左面板 ========== */
.left-panel {
  width: 320px;
  min-width: 280px;
  max-width: 320px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 4px solid #000000;
  background: #FFFDF5;
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 900;
  color: #000000;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.panel-icon {
  font-size: 16px;
}

.role-count-badge {
  font-size: 11px;
  font-weight: 900;
  color: #000000;
  background: #FFD93D;
  border: 2px solid #000000;
  padding: 2px 8px;
  border-radius: 2px;
  box-shadow: 2px 2px 0px 0px #000000;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.role-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ========== 角色列表项 ========== */
.role-item {
  padding: 12px;
  background: #FFFFFF;
  border: 3px solid #000000;
  border-radius: 4px;
  box-shadow: 3px 3px 0px 0px #000000;
  cursor: pointer;
  transition: all 0.15s ease;
  animation: slide-in-left 0.3s ease both;
}

.role-item:hover {
  box-shadow: 5px 5px 0px 0px #000000;
  transform: translate(-2px, -2px);
  background: #FFFDF5;
}

.role-item.active {
  background: #DBEAFE;
  border-color: #3B82F6;
  box-shadow: 4px 4px 0px 0px #3B82F6;
  transform: translate(2px, 2px);
}

.role-item-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.role-item-avatar {
  width: 36px;
  height: 36px;
  border: 3px solid #000000;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2px 2px 0px 0px #000000;
  flex-shrink: 0;
  color: #FFFFFF;
  transition: transform 0.2s ease;
}

.role-item:hover .role-item-avatar {
  transform: rotate(5deg) scale(1.05);
}

.role-item-info {
  flex: 1;
  min-width: 0;
}

.role-item-name {
  font-size: 14px;
  font-weight: 700;
  color: #000000;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.role-item-code {
  font-size: 12px;
  font-weight: 600;
  color: #666666;
  font-family: monospace;
}

.role-item-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: flex-end;
}

.role-item-arrow {
  color: #999999;
  font-size: 14px;
  transition: transform 0.2s ease, color 0.2s ease;
}

.role-item:hover .role-item-arrow {
  color: #3B82F6;
  transform: translateX(3px);
}

.role-item.active .role-item-arrow {
  color: #3B82F6;
}

/* 空状态 */
.role-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #999999;
  padding: 40px 20px;
}

.role-empty p {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.role-empty span {
  font-size: 12px;
  color: #C0C4CC;
}

/* ========== 右面板 ========== */
.right-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel--active {
  border-color: #3B82F6 !important;
}

/* ========== 编辑头部 ========== */
.edit-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 4px solid #000000;
  background: #FFFDF5;
  flex-shrink: 0;
}

.edit-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 900;
  color: #000000;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.edit-subtitle {
  font-size: 12px;
  font-weight: 600;
  color: #666666;
  margin: 4px 0 0 0;
  font-family: monospace;
}

/* ========== 编辑表单 ========== */
.edit-form {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 表单区块 */
.form-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-top: 4px solid #000000;
}

.form-section-icon {
  font-size: 18px;
  color: #3B82F6;
}

.form-section-title {
  font-size: 14px;
  font-weight: 900;
  color: #000000;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex: 1;
}

/* 权限计数徽章 */
.perm-count-badge {
  font-size: 11px;
  font-weight: 900;
  color: #000000;
  background: #FFD93D;
  border: 2px solid #000000;
  padding: 2px 8px;
  border-radius: 2px;
  box-shadow: 2px 2px 0px 0px #000000;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

/* ========== 权限表格 ========== */
.permission-table-wrapper {
  border: 3px solid #000000;
  border-radius: 4px;
  box-shadow: 4px 4px 0px 0px #000000;
  background: #FFFFFF;
  overflow: auto;
}

:deep(.permission-table-wrapper .el-table) {
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  background: #FFFFFF !important;
}

:deep(.permission-table-wrapper .el-table__header-wrapper th) {
  background: #FFFDF5 !important;
  border-bottom: 3px solid #000000 !important;
  border-top: none !important;
  font-weight: 900 !important;
  color: #000000 !important;
  font-size: 12px !important;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

:deep(.permission-table-wrapper .el-table__body-wrapper td) {
  border-bottom: 2px solid #E6EAF0 !important;
  font-weight: 500 !important;
  color: #000000 !important;
  padding: 8px 0 !important;
}

:deep(.permission-table-wrapper .el-table__body-wrapper tr:hover > td) {
  background: #FFFDF5 !important;
}

:deep(.permission-table-wrapper .el-table__cell) {
  border-color: #E6EAF0 !important;
}

.perm-module-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 12px;
}

.perm-module-icon {
  width: 32px;
  height: 32px;
  border: 2px solid #000000;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2px 2px 0px 0px #000000;
  color: #FFFFFF;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.perm-module-cell:hover .perm-module-icon {
  transform: rotate(5deg) scale(1.05);
}

.perm-module-label {
  font-size: 13px;
  font-weight: 700;
  color: #000000;
}

.perm-action-dimmed {
  color: #C0C4CC !important;
  font-weight: 500 !important;
}

/* ========== 表单操作 ========== */
.form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 16px;
  border-top: 3px solid #000000;
  flex-wrap: wrap;
}

/* ========== Tag 提示 ========== */
.tag-hint {
  margin-bottom: 8px;
}

/* ========== 空状态 ========== */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #999999;
  animation: pop-in 0.3s ease;
}

.empty-state-icon-wrap {
  width: 80px;
  height: 80px;
  border: 4px solid #000000;
  border-radius: 4px;
  background: #C4B5FD;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 6px 6px 0px 0px #000000;
  color: #FFFFFF;
  transition: transform 0.3s ease;
}

.empty-state:hover .empty-state-icon-wrap {
  transform: rotate(-5deg) scale(1.05);
}

.empty-state-title {
  font-size: 18px;
  font-weight: 900;
  color: #000000;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.empty-state-desc {
  font-size: 13px;
  font-weight: 600;
  color: #666666;
  margin: 0;
  text-align: center;
  max-width: 320px;
  line-height: 1.5;
}

/* ========== 动画 ========== */
@keyframes slide-in-left {
  from { transform: translateX(-12px); opacity: 0; }
  to   { transform: translateX(0); opacity: 1; }
}

@keyframes pop-in {
  0%   { transform: scale(0.85); opacity: 0; }
  60%  { transform: scale(1.05); }
  100% { transform: scale(1); opacity: 1; }
}

/* ========== 响应式 ========== */
@media (max-width: 1024px) {
  .left-panel {
    width: 260px;
    min-width: 240px;
    max-width: 260px;
  }

  .edit-form {
    padding: 12px 16px 20px;
  }
}

@media (max-width: 768px) {
  .role-page {
    padding: 12px;
    gap: 12px;
  }

  .workspace {
    flex-direction: column;
  }

  .left-panel {
    width: 100% !important;
    min-width: unset;
    max-width: unset;
    max-height: 240px;
  }

  .right-panel {
    min-height: 0;
  }

  .page-title {
    font-size: 18px;
  }

  .edit-form {
    padding: 12px;
  }

  .form-actions {
    flex-wrap: wrap;
  }

  .edit-header {
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }
}
</style>
