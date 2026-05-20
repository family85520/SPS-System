<template>
  <div class="user-page">
    <div class="page-header">
      <h3>用户账号管理</h3>
    </div>

    <div class="page-content">
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="keyword"
            placeholder="搜索用户名"
            clearable
            prefix-icon="Search"
            style="width: 220px"
            @input="handleSearch"
            @clear="handleSearch"
          />
          <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
          <el-select v-model="roleFilter" placeholder="角色筛选" clearable style="width: 160px" @change="handleSearch">
            <el-option
              v-for="role in allRoles"
              :key="role.id"
              :label="role.name"
              :value="role.id"
            />
          </el-select>
        </div>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新增用户
        </el-button>
      </div>

      <!-- 用户表格 -->
      <el-table :data="userList" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column label="关联人员" width="120">
          <template #default="{ row }">
            <span v-if="row.staff_name">{{ row.staff_name }}</span>
            <span v-else style="color: #909399">未关联</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag
              v-for="roleName in row.roles"
              :key="roleName"
              size="small"
              type="warning"
              style="margin-right: 4px; margin-bottom: 2px;"
            >
              {{ roleName }}
            </el-tag>
            <span v-if="!row.roles || row.roles.length === 0" style="color: #909399">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近登录" width="170">
          <template #default="{ row }">
            {{ row.last_login_at ? row.last_login_at.slice(0, 16) : '从未登录' }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            {{ row.created_at ? row.created_at.slice(0, 16) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="handleResetPwd(row)">重置密码</el-button>
            <el-button
              link
              :type="row.status === 1 ? 'warning' : 'success'"
              size="small"
              @click="handleToggleStatus(row)"
            >
              {{ row.status === 1 ? '禁用' : '启用' }}
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="row.username === 'admin'"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- 新增/编辑抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="isCreate ? '新增用户' : '编辑用户'"
      size="480px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="right"
        style="padding: 16px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名"
            :disabled="!isCreate"
          />
        </el-form-item>
        <el-form-item v-if="isCreate" label="密码" prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            show-password
            placeholder="请输入密码（至少6位）"
          />
        </el-form-item>

        <!-- 人员关联方式 -->
        <template v-if="isCreate">
          <el-divider content-position="left">人员信息</el-divider>
          <el-form-item label="创建方式">
            <el-radio-group v-model="formData.createStaff">
              <el-radio :value="false">关联已有人员</el-radio>
              <el-radio :value="true">同步创建新人员</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 关联已有人员 -->
          <el-form-item v-if="!formData.createStaff" label="选择人员">
            <el-select
              v-model="formData.staff_id"
              placeholder="选择关联人员（可选）"
              clearable
              filterable
              remote
              :remote-method="searchStaff"
              :loading="staffLoading"
              style="width: 100%"
            >
              <el-option
                v-for="s in staffOptions"
                :key="s.id"
                :label="`${s.name}（${s.employee_no}）`"
                :value="s.id"
              />
            </el-select>
          </el-form-item>

          <!-- 同步创建人员 -->
          <template v-if="formData.createStaff">
            <el-form-item label="姓名" prop="staff_name">
              <el-input v-model="formData.staff_name" placeholder="请输入人员姓名" />
            </el-form-item>
            <el-form-item label="工号" prop="employee_no">
              <el-input v-model="formData.employee_no" placeholder="请输入工号" />
            </el-form-item>
            <el-form-item label="联系电话">
              <el-input v-model="formData.phone" placeholder="请输入联系电话" />
            </el-form-item>
            <el-form-item label="所属组织" prop="org_id">
              <el-select v-model="formData.org_id" placeholder="请选择组织" style="width: 100%">
                <el-option
                  v-for="org in orgOptions"
                  :key="org.id"
                  :label="org.name"
                  :value="org.id"
                />
              </el-select>
            </el-form-item>
          </template>
        </template>

        <!-- 编辑模式：关联人员 -->
        <el-form-item v-if="!isCreate" label="关联人员">
          <el-select
            v-model="formData.staff_id"
            placeholder="选择关联人员（可选）"
            clearable
            filterable
            remote
            :remote-method="searchStaff"
            :loading="staffLoading"
            style="width: 100%"
          >
            <el-option
              v-for="s in staffOptions"
              :key="s.id"
              :label="`${s.name}（${s.employee_no}）`"
              :value="s.id"
            />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">账号设置</el-divider>
        <el-form-item label="状态">
          <el-select v-model="formData.status" style="width: 100%">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item label="分配角色">
          <el-select
            v-model="formData.role_ids"
            multiple
            placeholder="选择角色"
            style="width: 100%"
          >
            <el-option
              v-for="role in allRoles"
              :key="role.id"
              :label="role.name"
              :value="role.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isCreate" label="首次改密">
          <el-switch v-model="formData.mustChangePassword" />
          <span style="font-size: 12px; color: #909399; margin-left: 8px">开启后首次登录需修改密码</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-drawer>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="pwdDialogVisible" title="重置密码" width="400px">
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input :model-value="pwdForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input
            v-model="pwdForm.new_password"
            type="password"
            show-password
            placeholder="请输入新密码（至少6位）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdSaving" @click="doResetPwd">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getRoles, type Role } from '@/api/role'
import {
  getUserList, createUser, updateUser, resetPassword, deleteUser, getStaffOptions,
} from '@/api/user'
import type { UserItem } from '@/api/user'
import api from '@/api/index'

// 状态
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const statusFilter = ref<number | undefined>(undefined)
const roleFilter = ref<number | undefined>(undefined)
const userList = ref<UserItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

// 角色
const allRoles = ref<Role[]>([])

// 人员搜索
const staffOptions = ref<any[]>([])
const staffLoading = ref(false)

// 组织列表
const orgOptions = ref<any[]>([])

async function loadOrgs() {
  try {
    const res = await api.get('/organizations')
    orgOptions.value = Array.isArray(res) ? res : []
  } catch {
    orgOptions.value = []
  }
}

// 抽屉
const drawerVisible = ref(false)
const isCreate = ref(false)
const formRef = ref<FormInstance>()
const defaultForm = {
  id: 0,
  username: '',
  password: '',
  staff_id: null as number | null,
  status: 1,
  role_ids: [] as number[],
  mustChangePassword: true,
  // 同步创建人员
  createStaff: false,
  staff_name: '',
  employee_no: '',
  phone: '',
  org_id: null as number | null,
}
const formData = ref({ ...defaultForm })

const formRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度 3-50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  staff_name: [
    { required: true, message: '请输入人员姓名', trigger: 'blur' },
  ],
  employee_no: [
    { required: true, message: '请输入工号', trigger: 'blur' },
  ],
  org_id: [
    { required: true, message: '请选择所属组织', trigger: 'change' },
  ],
}

// 重置密码弹窗
const pwdDialogVisible = ref(false)
const pwdSaving = ref(false)
const pwdForm = ref({ user_id: 0, username: '', new_password: '' })

// 加载数据
async function loadUsers() {
  loading.value = true
  try {
    const { data: res } = await getUserList({
      keyword: keyword.value || undefined,
      status: statusFilter.value,
      role_id: roleFilter.value,
      page: page.value,
      page_size: pageSize.value,
    })
    userList.value = res.items || []
    total.value = res.total || 0
  } catch {
    userList.value = []
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  try {
    const res = await getRoles()
    allRoles.value = Array.isArray(res) ? res : []
  } catch {
    allRoles.value = []
  }
}

async function searchStaff(keyword: string) {
  if (!keyword) {
    staffOptions.value = []
    return
  }
  staffLoading.value = true
  try {
    const { data: res } = await api.get('/staffs', { params: { keyword, page: 1, page_size: 50 } })
    const list = res.items || []
    staffOptions.value = list.map((s: any) => ({
      id: s.id,
      name: s.name,
      employee_no: s.employee_no,
    }))
  } catch {
    staffOptions.value = []
  } finally {
    staffLoading.value = false
  }
}

// 搜索
let searchTimer: ReturnType<typeof setTimeout> | null = null
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadUsers()
  }, 300)
}

function handlePageChange(newPage: number) {
  page.value = newPage
  loadUsers()
}

function handleSizeChange(newSize: number) {
  pageSize.value = newSize
  page.value = 1
  loadUsers()
}

// 新增
function handleCreate() {
  isCreate.value = true
  formData.value = { ...defaultForm }
  staffOptions.value = []
  drawerVisible.value = true
}

// 编辑
function handleEdit(row: UserItem) {
  isCreate.value = false
  formData.value = {
    id: row.id,
    username: row.username,
    password: '',
    staff_id: row.staff_id,
    status: row.status,
    role_ids: [...row.role_ids],
    mustChangePassword: false,
    createStaff: false,
    staff_name: '',
    employee_no: '',
    phone: '',
    org_id: null,
  }
  if (row.staff_name && row.staff_id) {
    staffOptions.value = [{ id: row.staff_id, name: row.staff_name, employee_no: '' }]
  } else {
    staffOptions.value = []
  }
  drawerVisible.value = true
}

// 保存
async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isCreate.value) {
      const params: any = {
        username: formData.value.username,
        password: formData.value.password,
        status: formData.value.status,
        role_ids: formData.value.role_ids,
        must_change_password: formData.value.mustChangePassword,
        create_staff: formData.value.createStaff,
      }

      if (formData.value.createStaff) {
        params.staff_name = formData.value.staff_name
        params.employee_no = formData.value.employee_no
        params.phone = formData.value.phone || undefined
        params.org_id = formData.value.org_id
      } else {
        params.staff_id = formData.value.staff_id || undefined
      }

      await createUser(params)
      ElMessage.success('创建成功')
    } else {
      await updateUser(formData.value.id, {
        staff_id: formData.value.staff_id || null,
        status: formData.value.status,
        role_ids: formData.value.role_ids,
      })
      ElMessage.success('保存成功')
    }
    drawerVisible.value = false
    await loadUsers()
  } catch {
    // interceptor handles
  } finally {
    saving.value = false
  }
}

// 重置密码
function handleResetPwd(row: UserItem) {
  pwdForm.value = { user_id: row.id, username: row.username, new_password: '' }
  pwdDialogVisible.value = true
}

async function doResetPwd() {
  if (!pwdForm.value.new_password || pwdForm.value.new_password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  pwdSaving.value = true
  try {
    await resetPassword(pwdForm.value.user_id, pwdForm.value.new_password)
    ElMessage.success('密码重置成功')
    pwdDialogVisible.value = false
  } catch {
    // interceptor handles
  } finally {
    pwdSaving.value = false
  }
}

// 切换状态
async function handleToggleStatus(row: UserItem) {
  const newStatus = row.status === 1 ? 0 : 1
  try {
    await ElMessageBox({
      title: '提示',
      message: newStatus === 0 ? `确认禁用用户 "${row.username}"？禁用后该用户将无法登录。` : `确认启用用户 "${row.username}"？`,
      showCancelButton: true,
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await updateUser(row.id, { status: newStatus })
    ElMessage.success(newStatus === 1 ? '已启用' : '已禁用')
    await loadUsers()
  } catch {}
}

// 删除
async function handleDelete(row: UserItem) {
  if (row.username === 'admin') {
    ElMessage.warning('admin 账号不可删除')
    return
  }
  try {
    await ElMessageBox({
      title: '确认删除？',
      message: `删除用户 "${row.username}" 后将无法恢复，请慎重操作。`,
      showCancelButton: true,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    await loadUsers()
  } catch {}
}

onMounted(() => {
  loadUsers()
  loadRoles()
  loadOrgs()
})
</script>

<style scoped>
.user-page {
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
  padding: 16px 24px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}
</style>
