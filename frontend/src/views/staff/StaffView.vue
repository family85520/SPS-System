<template>
  <div class="staff-page">
    <div class="page-header">
      <h3>人员管理</h3>
    </div>

    <div class="page-content">
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="keyword"
            placeholder="搜索人员姓名或工号"
            clearable
            prefix-icon="Search"
            style="width: 280px"
            @input="handleSearch"
            @clear="handleSearch"
          />
          <el-button
            v-if="authStore.hasPermission('staff', 'update')"
            type="warning"
            :disabled="selectedStaffIds.length === 0"
            @click="handleBatchResetPwd"
          >
            批量重置密码
          </el-button>
        </div>
        <el-button
          v-if="authStore.hasPermission('staff', 'create')"
          type="primary"
          @click="handleCreate"
        >
          <el-icon><Plus /></el-icon>
          新增人员
        </el-button>
      </div>

      <!-- 人员表格 -->
      <el-table
        :data="filteredStaffList"
        stripe
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        :row-class-name="tableRowClassName"
      >
        <el-table-column type="selection" width="50" :selectable="isRowSelectable" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="phone" label="联系方式" width="130" />
        <el-table-column label="所属组织" width="160">
          <template #default="{ row }">
            {{ orgNameMap[row.org_id] || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="角色+身份标识" min-width="220">
          <template #default="{ row }">
            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
              <!-- 角色（绿色） -->
              <el-tag
                v-for="role in (row.account_roles || [])"
                :key="'role-' + role"
                size="small"
                type="success"
              >
                {{ role }}
              </el-tag>
              <!-- 标识（橙色） -->
              <el-tag
                v-for="tag in (row.tag_roles || [])"
                :key="'tag-' + tag.id"
                size="small"
                type="warning"
              >
                {{ tag.name }}
              </el-tag>
              <!-- 无任何角色/标识时显示 - -->
              <span
                v-if="(!row.account_roles || row.account_roles.length === 0) && (!row.tag_roles || row.tag_roles.length === 0)"
                style="color: #909399"
              >-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="登录账号" width="160">
          <template #default="{ row }">
            <template v-if="row.has_account">
              <div>{{ row.account_username }}</div>
              <el-tag :type="row.account_status === 1 ? 'success' : 'danger'" size="small" style="margin-top: 2px">
                {{ row.account_status === 1 ? '正常' : '禁用' }}
              </el-tag>
            </template>
            <el-tag v-else size="small" type="info">未创建</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="特殊规则" min-width="180">
          <template #default="{ row }">
            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
              <el-tag
                v-for="rule in (staffRulesMap[row.id] || [])"
                :key="rule.id"
                size="small"
                type="info"
              >
                {{ ruleDesc(rule) }}
              </el-tag>
              <span v-if="!staffRulesMap[row.id] || staffRulesMap[row.id].length === 0" style="color: #909399">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <!-- ========== 修改点1：系统账号重置密码仅限admin角色 ========== -->
            <template v-if="row.is_system_account">
              <el-button
                v-if="authStore.hasRole('admin')"
                link type="warning" size="small"
                @click="handleResetSingle(row)"
              >
                重置密码
              </el-button>
            </template>
            <!-- 普通人员：正常操作 -->
            <template v-else>
              <el-button
                v-if="authStore.hasPermission('staff', 'update')"
                link type="primary" size="small"
                @click="handleEdit(row)"
              >
                编辑
              </el-button>
              <el-button
                v-if="authStore.hasPermission('staff', 'update')"
                link type="primary" size="small"
                @click="handleAccount(row)"
              >
                账号
              </el-button>
              <el-button
                v-if="authStore.hasPermission('staff', 'update')"
                link type="primary" size="small"
                @click="handleSpecialRule(row)"
              >
                特殊规则
              </el-button>
              <el-button
                v-if="authStore.hasPermission('staff', 'update')"
                link
                :type="row.status === 1 ? 'warning' : 'success'"
                size="small"
                @click="handleToggleStatus(row)"
              >
                {{ row.status === 1 ? '停用' : '启用' }}
              </el-button>
              <el-button
                v-if="authStore.hasPermission('staff', 'delete')"
                link type="danger" size="small"
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </template>
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
      :title="isCreate ? '新增人员' : '编辑人员'"
      size="480px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="90px"
        label-position="right"
        style="padding: 16px"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item v-if="!isCreate" label="工号" prop="employee_no">
          <el-input v-model="formData.employee_no" disabled />
        </el-form-item>
        <el-form-item v-if="isCreate" label="工号">
          <el-input v-model="formData.employee_no" disabled :placeholder="employeeNoLoading ? '生成中...' : '选择组织后自动生成'" />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="formData.phone" placeholder="请输入联系方式" />
        </el-form-item>
        <el-form-item label="所属组织" prop="org_id">
          <el-select v-model="formData.org_id" placeholder="请选择组织" style="width: 100%" @change="onOrgChange">
            <el-option
              v-for="org in orgList"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="formData.status" style="width: 100%">
            <el-option label="在岗" :value="1" />
            <el-option label="请假" :value="2" />
            <el-option label="外派" :value="3" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色标签">
          <el-select
            v-model="formData.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入或选择标签"
            style="width: 100%"
          >
            <el-option
              v-for="role in roleList"
              :key="role.id"
              :label="role.name"
              :value="role.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="身份标识">
          <el-select
            v-model="formData.tag_role_ids"
            multiple
            filterable
            placeholder="选择身份标识"
            style="width: 100%"
          >
            <el-option
              v-for="tag in tagOptions"
              :key="tag.id"
              :label="tag.name"
              :value="tag.id"
            />
          </el-select>
          <div style="font-size: 12px; color: #909399; margin-top: 4px">
            标识在"角色管理"中创建，类型选择"标识"
          </div>
        </el-form-item>

        <template v-if="isCreate">
          <el-divider content-position="left">登录账号</el-divider>
          <el-form-item label="创建账号">
            <el-switch v-model="formData.create_account" @change="onAccountToggle" />
            <span style="font-size: 12px; color: #909399; margin-left: 8px">
              {{ formData.create_account ? '用户名=工号，初始密码=123456，角色根据标签自动匹配' : '不创建登录系统账号' }}
            </span>
          </el-form-item>
          <el-form-item v-if="formData.create_account" label="首次改密">
            <el-switch v-model="formData.must_change_password" />
            <span style="font-size: 12px; color: #909399; margin-left: 8px">
              {{ formData.must_change_password ? '首次登录需修改密码' : '首次登录不提示修改密码' }}
            </span>
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-drawer>

    <!-- 账号管理抽屉 -->
    <AccountDrawer
      v-model:visible="accountVisible"
      :staff="accountStaff"
      @refresh="refreshAccountData"
    />

    <!-- 特殊规则抽屉 -->
    <SpecialRuleDrawer
      v-model:visible="specialRuleVisible"
      :staff-id="specialRuleStaffId"
      :staff-name="specialRuleStaffName"
      @saved="loadAllRules"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import SpecialRuleDrawer from './components/SpecialRuleDrawer.vue'
import AccountDrawer from './components/AccountDrawer.vue'
import api from '@/api/index'
import { getSpecialRules, type SpecialRule } from '@/api/special-rule'
import request from '@/utils/request'

const authStore = useAuthStore()

// ========== 新增：辅助判断是否为admin角色 ==========
const isAdmin = computed(() => authStore.hasRole('admin'))

// 状态
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const staffList = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const orgList = ref<any[]>([])
const orgNameMap = ref<Record<number, string>>({})
const roleList = ref<any[]>([])
const tagOptions = ref<any[]>([])
const staffRulesMap = ref<Record<number, SpecialRule[]>>({})
const drawerVisible = ref(false)
const isCreate = ref(false)
const employeeNoLoading = ref(false)
const formRef = ref<FormInstance>()

// 特殊规则抽屉
const specialRuleVisible = ref(false)
const specialRuleStaffId = ref<number | null>(null)
const specialRuleStaffName = ref('')

// 账号管理抽屉
const accountVisible = ref(false)
const accountStaff = ref<any>(null)

// 批量选择
const selectedStaffIds = ref<number[]>([])

const defaultForm = {
  id: 0,
  name: '',
  employee_no: '',
  phone: '',
  org_id: null as number | null,
  status: 1,
  tags: [] as string[],
  tag_role_ids: [] as number[],
  create_account: true,
  must_change_password: true,
}

const formData = ref({ ...defaultForm })

const rules: FormRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  org_id: [{ required: true, message: '请选择组织', trigger: 'change' }],
}

// 搜索过滤
const filteredStaffList = computed(() => {
  return Array.isArray(staffList.value) ? staffList.value : []
})

// 状态标签
function statusLabel(status: number): string {
  const map: Record<number, string> = { 1: '在岗', 2: '请假', 3: '外派', 0: '停用' }
  return map[status] || '未知'
}

function statusType(status: number): string {
  const map: Record<number, string> = { 1: 'success', 2: 'warning', 3: 'info', 0: 'danger' }
  return map[status] || 'info'
}

// 特殊规则描述
const ruleTypeMap: Record<string, string> = {
  exclude_shift: '排除班次',
  include_shift: '仅排班次',
  exclude_post: '排除岗位',
  must_pair: '搭配人员',
  exclude_date: '排除日期',
  exclude_weekday: '排除星期',
}

function ruleDesc(rule: SpecialRule): string {
  return ruleTypeMap[rule.rule_type] || rule.rule_type
}

// 加载数据
const systemAccounts = ref<any[]>([])

async function loadStaff() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    const res: any = await api.get('/staffs', { params })
    const list = Array.isArray(res) ? res : (res.items || [])
    staffList.value = list
    total.value = res.total || list.length
    await loadAllRules()
    if (isAdmin.value) {
      await loadSystemAccounts()
    }
  } catch (e) {
    staffList.value = []
  } finally {
    loading.value = false
  }
}

async function loadSystemAccounts() {
  if (!isAdmin.value) return
  try {
    const res: any = await api.get('/staffs/system-accounts')
    systemAccounts.value = res.items || []
    const allItems = [...systemAccounts.value, ...staffList.value]
    staffList.value = allItems
  } catch {
    // 不影响主列表
  }
}

async function loadOrgs() {
  try {
    const res: any = await api.get('/options/organizations')
    const list = Array.isArray(res) ? res : (res.data || [])
    orgList.value = list
    orgList.value.forEach((org: any) => {
      orgNameMap.value[org.id] = org.name
    })
  } catch (e) {
    orgList.value = []
  }
}

async function loadRoles() {
  try {
    const res: any = await api.get('/roles/options')
    const list = Array.isArray(res) ? res : (res.data || [])
    // 只取角色类型，排除标识类型
    roleList.value = list.filter((r: any) => r.role_type === 'role')
  } catch (e) {
    roleList.value = []
  }
}

async function loadTagOptions() {
  try {
    const res: any = await api.get('/roles/options', { params: { type: 'tag' } })
    tagOptions.value = Array.isArray(res) ? res : (res.data || [])
  } catch {
    tagOptions.value = []
  }
}

async function loadAllRules() {
  try {
    const allRules: SpecialRule[] = await getSpecialRules({})
    const map: Record<number, SpecialRule[]> = {}
    for (const rule of allRules) {
      if (!map[rule.staff_id]) map[rule.staff_id] = []
      map[rule.staff_id].push(rule)
    }
    staffRulesMap.value = map
  } catch (e) {
    staffRulesMap.value = {}
  }
}

// 搜索（防抖）
let searchTimer: ReturnType<typeof setTimeout> | null = null
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadStaff()
  }, 300)
}

// 分页切换
function handlePageChange(newPage: number) {
  page.value = newPage
  loadStaff()
}

function handleSizeChange(newSize: number) {
  pageSize.value = newSize
  page.value = 1
  loadStaff()
}

function handleCreate() {
  isCreate.value = true
  formData.value = { ...defaultForm, employee_no: '', tag_role_ids: [] }
  drawerVisible.value = true
}

async function onOrgChange(orgId: number | null) {
  if (!isCreate.value || !orgId) {
    if (isCreate.value) formData.value.employee_no = ''
    return
  }
  employeeNoLoading.value = true
  try {
    const res: any = await api.get('/staffs/next-employee-no', { params: { org_id: orgId } })
    formData.value.employee_no = res.employee_no || ''
  } catch {
    formData.value.employee_no = ''
  } finally {
    employeeNoLoading.value = false
  }
}

// 表格选择
function handleSelectionChange(rows: any[]) {
  selectedStaffIds.value = rows.filter(r => !r.is_system_account).map(r => r.id)
}

function isRowSelectable(row: any) {
  return !row.is_system_account
}

function tableRowClassName({ row }: { row: any }) {
  return row.is_system_account ? 'system-account-row' : ''
}

// ========== 修改点2：单个重置密码增加admin角色二次校验 ==========
async function handleResetSingle(row: any) {
  // 系统账号重置密码必须是admin角色
  if (row.is_system_account && !isAdmin.value) {
    ElMessage.error('系统账号密码仅允许管理员重置')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认将 "${row.name}" 的密码重置为默认密码（123456）？重置后首次登录需修改密码。`,
      '重置密码',
      { confirmButtonText: '确认重置', cancelButtonText: '取消', type: 'warning' }
    )
    let res: any
    if (row.is_system_account) {
      res = await request.post(`/api/staffs/reset-password-by-user/${row.user_id}`)
    } else {
      res = await request.post(`/api/staffs/${row.id}/reset-password`)
    }
    ElMessage.success(res.message || '密码已重置')
    await loadStaff()
    await loadSystemAccounts()
  } catch {}
}

// ========== 修改点3：批量重置密码排除系统账号（双重保险） ==========
async function handleBatchResetPwd() {
  if (selectedStaffIds.value.length === 0) {
    ElMessage.warning('请先选择要重置的人员')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认将选中的 ${selectedStaffIds.value.length} 位人员密码重置为默认密码（123456）？`,
      '批量重置密码',
      { confirmButtonText: '确认重置', cancelButtonText: '取消', type: 'warning' }
    )
    const { data: res } = await request.post('/api/staffs/reset-passwords', { staff_ids: selectedStaffIds.value })
    ElMessage.success(res.message || '批量重置完成')
    selectedStaffIds.value = []
    await loadStaff()
    await loadSystemAccounts()
  } catch {}
}

function handleAccount(row: any) {
  accountStaff.value = { ...row }
  accountVisible.value = true
}

function onAccountToggle(val: boolean) {
  if (!val) {
    formData.value.must_change_password = false
  } else {
    formData.value.must_change_password = true
  }
}

async function refreshAccountData() {
  await loadStaff()
  if (accountStaff.value) {
    const fresh = staffList.value.find((s: any) => s.id === accountStaff.value.id)
    if (fresh) {
      accountStaff.value = { ...fresh }
    }
  }
}

// 编辑
function handleEdit(row: any) {
  isCreate.value = false
  formData.value = {
    id: row.id,
    name: row.name,
    employee_no: row.employee_no,
    phone: row.phone || '',
    org_id: row.org_id,
    status: row.status,
    tags: row.tags || [],
    tag_role_ids: (row.tag_roles || []).map((t: any) => t.id),
    create_account: true,
    must_change_password: true,
  }
  drawerVisible.value = true
}

// 特殊规则
function handleSpecialRule(row: any) {
  specialRuleStaffId.value = row.id
  specialRuleStaffName.value = row.name
  specialRuleVisible.value = true
}

// 保存
async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isCreate.value) {
      await api.post('/staffs', {
        name: formData.value.name,
        employee_no: formData.value.employee_no,
        phone: formData.value.phone,
        org_id: formData.value.org_id,
        tags: formData.value.tags,
        tag_role_ids: formData.value.tag_role_ids,
        create_account: formData.value.create_account,
        must_change_password: formData.value.create_account ? formData.value.must_change_password : false,
      })
      ElMessage.success(formData.value.create_account ? '人员和登录账号创建成功' : '人员创建成功（未创建账号）')
    } else {
      await api.put(`/staffs/${formData.value.id || 0}`, {
        name: formData.value.name,
        employee_no: formData.value.employee_no,
        phone: formData.value.phone,
        org_id: formData.value.org_id,
        status: formData.value.status,
        tags: formData.value.tags,
        tag_role_ids: formData.value.tag_role_ids,
      })
      ElMessage.success('保存成功')
    }
    drawerVisible.value = false
    await loadStaff()
    await loadAllRules()
  } catch (e) {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

// 切换状态
async function handleToggleStatus(row: any) {
  const newStatus = row.status === 1 ? 0 : 1
  try {
    await ElMessageBox({
      title: '提示',
      message: newStatus === 1 ? '确认启用该人员？' : '停用后该人员不参与自动排班，确认停用？',
      showCancelButton: true,
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await api.put(`/staffs/${row.id}`, { status: newStatus })
    ElMessage.success(newStatus === 1 ? '已启用' : '已停用')
    await loadStaff()
  } catch (e) {
    // cancel
  }
}

// 删除
async function handleDelete(row: any) {
  try {
    await ElMessageBox({
      title: '确认删除？',
      message: '删除后数据无法恢复，请慎重操作。',
      showCancelButton: true,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await api.delete(`/staffs/${row.id}`)
    ElMessage.success('删除成功')
    await loadStaff()
  } catch (e) {
    // cancel
  }
}

onMounted(() => {
  loadStaff()
  loadOrgs()
  loadRoles()
  loadTagOptions()
})
</script>

<style scoped>
.staff-page {
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

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

:deep(.system-account-row) {
  background-color: #fafafa !important;
}

:deep(.system-account-row:hover > td) {
  background-color: #f0f0f0 !important;
}
</style>
