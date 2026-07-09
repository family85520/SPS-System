<template>
  <div class="staff-page">
    <!-- ====== 页面头部 ====== -->
    <div class="page-header">
      <div class="header-main">
        <div class="header-icon">
          <el-icon :size="24"><UserFilled /></el-icon>
        </div>
        <div class="header-text">
          <h2 class="header-title">人员管理</h2>
          <p class="header-desc">管理所有员工信息，配置排班权限与岗位属性，确保排班系统数据准确完整。</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button class="btn-neo-ghost" @click="loadStaff">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button
          v-if="authStore.hasPermission('staff', 'create')"
          class="btn-neo-primary"
          @click="handleCreate"
        >
          <el-icon><Plus /></el-icon>
          新增人员
        </el-button>
      </div>
    </div>

    <div class="page-content">
      <!-- ====== 搜索筛选卡片 ====== -->
      <div class="neo-card search-card">
        <div class="search-row">
          <div class="search-input-wrap">
            <el-icon class="search-icon"><Search /></el-icon>
            <el-input
              v-model="keyword"
              placeholder="搜索员工姓名、工号或部门..."
              clearable
              @input="debounceSearch"
              @clear="loadStaff"
            />
          </div>
          <el-select v-model="deptFilter" placeholder="全部部门" clearable @change="loadStaff" class="neo-select">
            <el-option
              v-for="org in orgList"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
          <el-select v-model="statusFilter" placeholder="全部状态" clearable @change="loadStaff" class="neo-select">
            <el-option label="在岗" :value="1" />
            <el-option label="请假" :value="2" />
            <el-option label="外派" :value="3" />
            <el-option label="停用" :value="0" />
          </el-select>
        </div>
      </div>

      <!-- ====== 统计卡片 ====== -->
      <div class="stats-grid">
        <div class="neo-card stat-card">
          <div class="stat-header">
            <el-icon :size="24" class="stat-icon stat-icon-accent"><UserFilled /></el-icon>
            <span class="stat-label">总员工数</span>
          </div>
          <span class="stat-value">{{ total }}</span>
        </div>
        <div class="neo-card stat-card">
          <div class="stat-header">
            <el-icon :size="24" class="stat-icon stat-icon-success"><Check /></el-icon>
            <span class="stat-label">在岗</span>
          </div>
          <span class="stat-value">{{ statsActive }}</span>
        </div>
        <div class="neo-card stat-card">
          <div class="stat-header">
            <el-icon :size="24" class="stat-icon stat-icon-warning"><Coffee /></el-icon>
            <span class="stat-label">请假</span>
          </div>
          <span class="stat-value">{{ statsLeave }}</span>
        </div>
        <div class="neo-card stat-card">
          <div class="stat-header">
            <el-icon :size="24" class="stat-icon stat-icon-danger"><Close /></el-icon>
            <span class="stat-label">停用</span>
          </div>
          <span class="stat-value">{{ statsResigned }}</span>
        </div>
      </div>

      <!-- ====== 工具栏 ====== -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="quickSearch"
            placeholder="搜索人员姓名或工号"
            clearable
            prefix-icon="Search"
            style="width: 260px"
            @input="handleQuickSearch"
            @clear="loadStaff"
          />
          <el-button
            v-if="authStore.hasPermission('staff', 'update')"
            class="btn-neo-warning btn-neo-sm"
            :disabled="selectedStaffIds.length === 0"
            @click="handleBatchResetPwd"
          >
            批量重置密码
          </el-button>
        </div>
      </div>

      <!-- ====== 人员表格 ====== -->
      <el-table
        :data="displayList"
        stripe
        v-loading="loading"
        @selection-change="handleSelectionChange"
        :row-class-name="tableRowClassName"
        class="staff-table"
      >
        <el-table-column type="selection" width="40" :selectable="isRowSelectable" />
        <el-table-column label="人员信息" min-width="180">
          <template #default="{ row }">
            <div class="staff-cell">
              <div class="staff-avatar" :style="{ backgroundColor: avatarColor(row.id) }">
                {{ row.name.charAt(0) }}
              </div>
              <div class="staff-info">
                <div class="staff-name">{{ row.name }}</div>
                <div class="staff-phone">{{ row.phone || '-' }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="employee_no" label="工号" width="100" />
        <el-table-column label="所属组织" width="130">
          <template #default="{ row }">
            {{ orgNameMap[row.org_id] || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="dark">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="角色+身份标识" min-width="160">
          <template #default="{ row }">
            <div class="tag-group">
              <el-tag
                v-for="role in (row.account_roles || [])"
                :key="'role-' + role"
                size="small"
                type="success"
                effect="dark"
              >
                {{ role }}
              </el-tag>
              <el-tag
                v-for="tag in (row.tag_roles || [])"
                :key="'tag-' + tag.id"
                size="small"
                type="warning"
                effect="dark"
              >
                {{ tag.name }}
              </el-tag>
              <span
                v-if="(!row.account_roles || row.account_roles.length === 0) && (!row.tag_roles || row.tag_roles.length === 0)"
                class="text-muted"
              >-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="登录账号" width="130">
          <template #default="{ row }">
            <template v-if="row.has_account">
              <div class="account-info">
                <span class="account-name">{{ row.account_username }}</span>
                <el-tag :type="row.account_status === 1 ? 'success' : 'danger'" size="small" effect="dark">
                  {{ row.account_status === 1 ? '正常' : '禁用' }}
                </el-tag>
              </div>
            </template>
            <el-tag v-else size="small" type="info" effect="dark">未创建</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="特殊规则" min-width="130">
          <template #default="{ row }">
            <div class="tag-group">
              <el-tag
                v-for="rule in (staffRulesMap[row.id] || [])"
                :key="rule.id"
                size="small"
                type="info"
                effect="dark"
              >
                {{ ruleDesc(rule) }}
              </el-tag>
              <span v-if="!staffRulesMap[row.id] || staffRulesMap[row.id].length === 0" class="text-muted">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="账号" width="50">
          <template #default="{ row }">
            <el-tooltip content="账号管理" placement="top" v-if="authStore.hasPermission('staff', 'update') && !row.is_system_account">
              <el-button size="small" class="neo-icon-btn" @click="handleAccount(row)">
                <el-icon><User /></el-icon>
              </el-button>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="特殊规则" width="60">
          <template #default="{ row }">
            <el-tooltip content="特殊规则" placement="top" v-if="authStore.hasPermission('staff', 'update') && !row.is_system_account">
              <el-button size="small" class="neo-icon-btn" @click="handleSpecialRule(row)">
                <el-icon><Setting /></el-icon>
              </el-button>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="60">
          <template #default="{ row }">
            <el-tooltip :content="row.status === 1 ? '停用' : '启用'" placement="top" v-if="authStore.hasPermission('staff', 'update') && !row.is_system_account">
              <el-button size="small" :class="row.status === 1 ? 'neo-icon-btn neo-icon-warning' : 'neo-icon-btn neo-icon-success'" @click="handleToggleStatus(row)">
                <el-icon v-if="row.status === 1"><SwitchButton /></el-icon>
                <el-icon v-else><CircleCheck /></el-icon>
              </el-button>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <!-- 系统账号：仅 admin 可重置密码 -->
              <template v-if="row.is_system_account">
                <el-tooltip content="重置密码" placement="top" v-if="authStore.hasRole('admin')">
                  <el-button size="small" class="neo-icon-btn neo-icon-warning" @click="handleResetSingle(row)">
                    <el-icon><Key /></el-icon>
                  </el-button>
                </el-tooltip>
              </template>
              <!-- 普通人员：编辑 + 删除 -->
              <template v-else>
                <el-tooltip content="编辑" placement="top" v-if="authStore.hasPermission('staff', 'update')">
                  <el-button size="small" class="neo-icon-btn" @click="handleEdit(row)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="删除" placement="top" v-if="authStore.hasPermission('staff', 'delete')">
                  <el-button size="small" class="neo-icon-btn neo-icon-danger" @click="handleDelete(row)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <span class="pagination-info">显示 {{ paginationInfo.start }}-{{ paginationInfo.end }} 共 {{ total }} 条记录</span>
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

    <!-- ====== 新增/编辑抽屉 ====== -->
    <el-drawer
      v-model="drawerVisible"
      :title="isCreate ? '新增人员' : '编辑人员'"
      size="520px"
      :close-on-click-modal="false"
      class="neo-drawer"
    >
      <div class="drawer-body">
        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-width="90px"
          label-position="right"
        >
          <el-form-item label="姓名" prop="name">
            <el-input v-model="formData.name" placeholder="请输入姓名" />
          </el-form-item>
          <el-form-item v-if="!isCreate" label="工号" prop="employee_no">
            <el-input v-model="formData.employee_no" disabled />
          </el-form-item>
          <el-form-item v-if="isCreate" label="工号">
            <el-input
              v-model="formData.employee_no"
              disabled
              :placeholder="employeeNoLoading ? '生成中...' : '选择组织后自动生成'"
            />
          </el-form-item>
          <el-form-item label="联系方式">
            <el-input v-model="formData.phone" placeholder="请输入联系方式" />
          </el-form-item>
          <el-form-item label="所属组织" prop="org_id">
            <el-select v-model="formData.org_id" placeholder="请选择组织" class="neo-input" @change="onOrgChange">
              <el-option
                v-for="org in orgList"
                :key="org.id"
                :label="org.name"
                :value="org.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="formData.status" class="neo-input">
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
              class="neo-input"
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
              class="neo-input"
            >
              <el-option
                v-for="tag in tagOptions"
                :key="tag.id"
                :label="tag.name"
                :value="tag.id"
              />
            </el-select>
            <div class="form-tip">标识在"角色管理"中创建，类型选择"标识"</div>
          </el-form-item>

          <template v-if="isCreate">
            <el-divider content-position="left">登录账号</el-divider>
            <div class="alert-card alert-card--info">
              <span class="alert-card__icon">ℹ</span>
              <span class="alert-card__content">创建账号后，系统将自动生成用户名（工号）和初始密码（123456）。</span>
            </div>
            <el-form-item label="创建账号">
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.create_account, 'is-disabled': !canEdit }"
                @click="() => { if (canEdit) { formData.create_account = !formData.create_account; onAccountToggle(formData.create_account) } }"
              >
                <span class="neo-switch-knob"></span>
              </span>
              <span class="form-tip">
                {{ formData.create_account ? '用户名=工号，初始密码=123456，角色根据标签自动匹配' : '不创建登录系统账号' }}
              </span>
            </el-form-item>
            <el-form-item v-if="formData.create_account" label="首次改密">
              <span
                class="neo-switch-inline"
                :class="{ 'is-checked': formData.must_change_password, 'is-disabled': !canEdit }"
                @click="() => { if (canEdit) formData.must_change_password = !formData.must_change_password }"
              >
                <span class="neo-switch-knob"></span>
              </span>
              <span class="form-tip">
                {{ formData.must_change_password ? '首次登录需修改密码' : '首次登录不提示修改密码' }}
              </span>
            </el-form-item>
          </template>
        </el-form>
      </div>

      <template #footer>
        <div class="drawer-footer">
          <el-button class="btn-neo-ghost" @click="drawerVisible = false">取消</el-button>
          <el-button class="btn-neo-primary" :loading="saving" @click="handleSave">保存</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- ====== 账号管理抽屉 ====== -->
    <AccountDrawer
      v-model:visible="accountVisible"
      :staff="accountStaff"
      @refresh="refreshAccountData"
    />

    <!-- ====== 特殊规则抽屉 ====== -->
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
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus, Refresh, Search, UserFilled, Edit, User, Setting, Delete,
  Key, SwitchButton, CircleCheck, Check, Coffee, Close,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import SpecialRuleDrawer from './components/SpecialRuleDrawer.vue'
import AccountDrawer from './components/AccountDrawer.vue'
import api from '@/api/index'
import { getSpecialRules, type SpecialRule } from '@/api/special-rule'
import request from '@/utils/request'
import { useConfirm } from '@/composables/useConfirm'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.hasRole('admin'))
const { confirmWarning, confirmDanger } = useConfirm()

// ====== 数据状态 ======
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const quickSearch = ref('')
const deptFilter = ref<number | null>(null)
const statusFilter = ref<number | null>(null)
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
const canEdit = computed(() => isCreate.value)
const employeeNoLoading = ref(false)
const formRef = ref<FormInstance>()

// ====== 统计 ======
const statsActive = ref(0)
const statsLeave = ref(0)
const statsResigned = ref(0)

// ====== 子抽屉状态 ======
const specialRuleVisible = ref(false)
const specialRuleStaffId = ref<number | null>(null)
const specialRuleStaffName = ref('')
const accountVisible = ref(false)
const accountStaff = ref<any>(null)

// ====== 选中状态 ======
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

// ====== 分页信息 ======
const paginationInfo = computed(() => {
  const start = total.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1
  const end = Math.min(page.value * pageSize.value, total.value)
  return { start, end }
})

// ====== 过滤展示列表 ======
const displayList = computed(() => {
  let list = [...(staffList.value || [])]
  if (quickSearch.value) {
    const kw = quickSearch.value.toLowerCase()
    list = list.filter(s =>
      s.name?.toLowerCase().includes(kw) ||
      s.employee_no?.toLowerCase().includes(kw)
    )
  }
  return list
})

// ====== 头像颜色池 ======
const avatarColors = ['#C4B5FD', '#FF6B6B', '#FFD93D', '#10B981', '#06B6D4', '#F59E0B', '#8B5CF6']
function avatarColor(id: number): string {
  return avatarColors[id % avatarColors.length]
}

// ====== 状态映射 ======
function statusLabel(status: number): string {
  const map: Record<number, string> = { 1: '在岗', 2: '请假', 3: '外派', 0: '停用' }
  return map[status] || '未知'
}

function statusType(status: number): string {
  const map: Record<number, string> = { 1: 'success', 2: 'warning', 3: 'info', 0: 'danger' }
  return map[status] || 'info'
}

// ====== 特殊规则描述 ======
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

// ====== 数据加载 ======
const systemAccounts = ref<any[]>([])

async function loadStaff() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (deptFilter.value) params.org_id = deptFilter.value
    if (statusFilter.value !== null && statusFilter.value !== undefined) params.status = statusFilter.value
    const res: any = await api.get('/staffs', { params })
    const list = Array.isArray(res) ? res : (res.items || [])
    staffList.value = list
    total.value = res.total || list.length
    // 统计
    statsActive.value = list.filter((s: any) => s.status === 1).length
    statsLeave.value = list.filter((s: any) => s.status === 2).length
    statsResigned.value = list.filter((s: any) => s.status === 0).length
    await loadAllRules()
    if (isAdmin.value) {
      await loadSystemAccounts()
    }
  } catch {
    staffList.value = []
    total.value = 0
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
    list.forEach((org: any) => { orgNameMap.value[org.id] = org.name })
  } catch {
    orgList.value = []
  }
}

async function loadRoles() {
  try {
    const res: any = await api.get('/roles/options')
    const list = Array.isArray(res) ? res : (res.data || [])
    roleList.value = list.filter((r: any) => r.role_type === 'role')
  } catch {
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
  } catch {
    staffRulesMap.value = {}
  }
}

// ====== 快速搜索（纯客户端过滤，不发请求） ======
function handleQuickSearch() {
  page.value = 1
}

// ====== 关键词搜索（服务端请求，防抖） ======
let searchTimer: ReturnType<typeof setTimeout> | null = null
function debounceSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadStaff()
  }, 300)
}

function handlePageChange(newPage: number) {
  page.value = newPage
  loadStaff()
}

function handleSizeChange(newSize: number) {
  pageSize.value = newSize
  page.value = 1
  loadStaff()
}

// ====== 新增/编辑 ======
function handleCreate() {
  isCreate.value = true
  formData.value = { ...defaultForm, employee_no: '', tag_role_ids: [] }
  drawerVisible.value = true
}

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
  } catch {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

// ====== 选中 ======
function handleSelectionChange(rows: any[]) {
  selectedStaffIds.value = rows.filter(r => !r.is_system_account).map(r => r.id)
}

function isRowSelectable(row: any) {
  return !row.is_system_account
}

function tableRowClassName({ row }: { row: any }) {
  return row.is_system_account ? 'system-account-row' : ''
}

// ====== 账号管理 ======
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

// ====== 特殊规则 ======
function handleSpecialRule(row: any) {
  specialRuleStaffId.value = row.id
  specialRuleStaffName.value = row.name
  specialRuleVisible.value = true
}

// ====== 密码重置 ======
async function handleResetSingle(row: any) {
  if (row.is_system_account && !isAdmin.value) {
    ElMessage.error('系统账号密码仅允许管理员重置')
    return
  }
  try {
    await confirmWarning(
      `确认将 "${row.name}" 的密码重置为默认密码（123456）？重置后首次登录需修改密码。`,
      '重置密码',
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
  } catch {
    // cancel
  }
}

async function handleBatchResetPwd() {
  if (selectedStaffIds.value.length === 0) {
    ElMessage.warning('请先选择要重置的人员')
    return
  }
  try {
    await confirmWarning(
      `确认将选中的 ${selectedStaffIds.value.length} 位人员密码重置为默认密码（123456）？`,
      '批量重置密码',
    )
    const { data: res } = await request.post('/api/staffs/reset-passwords', { staff_ids: selectedStaffIds.value })
    ElMessage.success(res.message || '批量重置完成')
    selectedStaffIds.value = []
    await loadStaff()
    await loadSystemAccounts()
  } catch {
    // cancel
  }
}

// ====== 状态切换 ======
async function handleToggleStatus(row: any) {
  const newStatus = row.status === 1 ? 0 : 1
  try {
    await confirmWarning(newStatus === 1 ? '确认启用该人员？' : '停用后该人员不参与自动排班，确认停用？', '提示')
    await api.put(`/staffs/${row.id}`, { status: newStatus })
    ElMessage.success(newStatus === 1 ? '已启用' : '已停用')
    await loadStaff()
  } catch {
    // cancel
  }
}

// ====== 删除 ======
async function handleDelete(row: any) {
  try {
    await confirmDanger('删除后数据无法恢复，请慎重操作。', '确认删除？')
    await api.delete(`/staffs/${row.id}`)
    ElMessage.success('删除成功')
    await loadStaff()
  } catch {
    // cancel
  }
}

// ====== 初始化 ======
onMounted(() => {
  loadStaff()
  loadOrgs()
  loadRoles()
  loadTagOptions()
})
</script>

<style scoped>
/* ====== 页面容器 ====== */
.staff-page {
  min-height: 100vh;
  background: var(--neo-color-bg-primary);
}

/* ====== 页面头部 ====== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: var(--neo-border-thick) solid var(--neo-color-border);
  background: var(--neo-color-bg-primary);
}

.header-main {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-icon {
  width: 48px;
  height: 48px;
  background: var(--neo-color-accent-red);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--neo-color-text-primary);
  font-size: 24px;
  flex-shrink: 0;
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.header-title {
  margin: 0;
  font-size: 22px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  letter-spacing: 0.3px;
  line-height: 1.2;
}

.header-desc {
  margin: 0;
  font-size: 13px;
  color: var(--neo-color-text-secondary);
  font-weight: 500;
  line-height: 1.4;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* ====== 页面内容区 ====== */
.page-content {
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ====== Neo 卡片通用 ====== */
.neo-card {
  background: var(--neo-color-bg-card);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-hover);
  transition: all 0.2s ease;
}

.neo-card:hover {
  box-shadow: var(--neo-shadow-lg);
  transform: translateY(-1px);
}

/* ====== 搜索卡片 ====== */
.search-card {
  padding: 16px 20px;
}

.search-card:hover {
  transform: none;
  box-shadow: var(--neo-shadow-default);
}

.search-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.search-input-wrap {
  flex: 1;
  min-width: 240px;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--neo-color-text-secondary);
  font-size: 18px;
  pointer-events: none;
  z-index: 1;
}

.search-input-wrap :deep(.el-input__wrapper) {
  padding-left: 38px;
  height: 52px !important;
  border: var(--neo-border-thick) solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-md) !important;
  box-shadow: var(--neo-shadow-default) !important;
  background: var(--neo-color-bg-card) !important;
  transition: all 0.1s ease;
}

.search-input-wrap :deep(.el-input__inner) {
  font-size: 14px;
  font-weight: 600;
  color: var(--neo-color-text-primary);
}

.search-input-wrap :deep(.el-input__inner::placeholder) {
  color: var(--neo-color-text-muted);
  font-weight: 500;
}

.search-input-wrap :deep(.el-input__wrapper:hover),
.search-input-wrap :deep(.el-input__wrapper.is-focus) {
  box-shadow: var(--neo-shadow-md-lg) !important;
  transform: translate(var(--neo-translate-hover), var(--neo-translate-hover));
  background: var(--neo-color-accent-yellow) !important;
}

.neo-select {
  width: 160px;
}

.neo-select :deep(.el-input__wrapper) {
  height: 52px !important;
  border: var(--neo-border-thick) solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-md) !important;
  box-shadow: var(--neo-shadow-default) !important;
  background: var(--neo-color-bg-card) !important;
  transition: all 0.1s ease;
}

.neo-select :deep(.el-input__wrapper:hover),
.neo-select :deep(.el-input__wrapper.is-focus) {
  box-shadow: var(--neo-shadow-md-lg) !important;
  transform: translate(var(--neo-translate-hover), var(--neo-translate-hover));
  background: var(--neo-color-accent-yellow) !important;
}

/* ====== 统计卡片网格 ====== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  padding: 16px 20px;
}

.stat-card:hover {
  transform: none;
  box-shadow: var(--neo-shadow-default);
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.stat-icon {
  flex-shrink: 0;
}

.stat-icon-accent { color: var(--neo-color-accent-red); }
.stat-icon-success { color: var(--neo-color-accent-green); }
.stat-icon-warning { color: var(--neo-color-accent-yellow); }
.stat-icon-danger { color: var(--neo-color-accent-red-hover); }

.stat-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--neo-color-text-secondary);
  letter-spacing: 0.3px;
}

.stat-value {
  display: block;
  font-size: 36px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  line-height: 1.1;
}

/* ====== 工具栏 ====== */
.toolbar {
  display: flex;
  align-items: center;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ====== 表格 ====== */
.staff-table {
  border-radius: 4px;
}

.staff-table :deep(.el-table__header th) {
  background: var(--neo-color-bg-primary) !important;
  border-bottom: var(--neo-border-thick) solid var(--neo-color-border) !important;
  color: var(--neo-color-text-primary) !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  letter-spacing: 0.3px;
  padding: 12px 0 !important;
}

.staff-table :deep(.el-table__body td) {
  border-bottom: var(--neo-border-thin) solid var(--neo-color-border-light) !important;
  padding: 10px 0 !important;
}

.staff-table :deep(.el-table__body tr:hover > td) {
  background: var(--neo-color-bg-primary) !important;
}

/* 人员单元格 */
.staff-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.staff-avatar {
  width: 40px;
  height: 40px;
  border: var(--neo-border-thin) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-active);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
  flex-shrink: 0;
}

.staff-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.staff-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--neo-color-text-primary);
  white-space: nowrap;
}

.staff-phone {
  font-size: 12px;
  color: rgba(var(--neo-color-text-primary), 0.6);
  font-weight: 500;
}

/* 标签组 */
.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.text-muted {
  color: var(--neo-color-text-muted);
  font-weight: 500;
  font-size: 13px;
}

/* 账号信息 */
.account-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.account-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--neo-color-text-primary);
}

/* ====== 操作按钮 —— 原型 A 风格：纯图标方形 neo 按钮 ====== */
.action-group {
  display: flex;
  flex-wrap: nowrap;
  gap: 6px;
  align-items: center;
}

/* 统一图标按钮样式（所有列的操作按钮共用） */
.neo-icon-btn {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 34px !important;
  height: 34px !important;
  padding: 0 !important;
  border: var(--neo-border-thin) solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-md) !important;
  box-shadow: var(--neo-shadow-active) !important;
  background: var(--neo-color-bg-card) !important;
  color: var(--neo-color-text-primary) !important;
  font-size: 14px !important;
  transition: all 0.1s ease !important;
  cursor: pointer !important;
  min-width: 0 !important;
  line-height: 1 !important;
}

.neo-icon-btn:hover {
  box-shadow: var(--neo-shadow-md) !important;
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs)) !important;
}

.neo-icon-btn:active {
  box-shadow: var(--neo-shadow-xs) !important;
  transform: translate(var(--neo-translate-active-sm), var(--neo-translate-active-sm)) !important;
}

.neo-icon-btn:disabled {
  opacity: 0.5 !important;
  cursor: not-allowed !important;
  box-shadow: var(--neo-shadow-active) !important;
  transform: none !important;
}

/* 危险操作 — 红色背景 */
.neo-icon-btn.neo-icon-danger {
  background: var(--neo-color-accent-red) !important;
  color: var(--neo-color-text-primary) !important;
}
.neo-icon-btn.neo-icon-danger:hover {
  background: var(--neo-color-accent-red-hover) !important;
}

/* 警告操作 — 黄色背景 */
.neo-icon-btn.neo-icon-warning {
  background: var(--neo-color-accent-yellow) !important;
  color: var(--neo-color-text-primary) !important;
}
.neo-icon-btn.neo-icon-warning:hover {
  background: var(--neo-color-accent-yellow) !important;
}

/* 成功操作 — 绿色背景 */
.neo-icon-btn.neo-icon-success {
  background: var(--neo-color-accent-green) !important;
  color: var(--neo-color-bg-card) !important;
}
.neo-icon-btn.neo-icon-success:hover {
  background: var(--neo-color-accent-green) !important;
}

/* tooltip 自定义样式 */
:deep(.action-group .el-tooltip__popper) {
  background: var(--neo-color-text-primary) !important;
  color: var(--neo-color-bg-card) !important;
  border: var(--neo-border-thin) solid var(--neo-color-border) !important;
  box-shadow: var(--neo-shadow-md) !important;
  border-radius: var(--neo-radius-sm) !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  padding: 4px 8px !important;
}

:deep(.action-group .el-tooltip__popper::before) {
  border: var(--neo-border-thin) solid var(--neo-color-border) !important;
}

/* ====== 分页 ====== */
.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  flex-wrap: wrap;
  gap: 10px;
}

.pagination-info {
  font-size: 13px;
  font-weight: 600;
  color: var(--neo-color-text-primary);
}

/* ====== 抽屉 ====== */
.drawer-body {
  padding: 8px 24px;
}
.drawer-footer {
  gap: 10px;
  padding: 12px 24px;
}
.form-tip {
  font-weight: 500;
  margin-left: 8px;
  vertical-align: middle;
}

/* ====== 系统账号行 ====== */
:deep(.system-account-row) {
  background-color: var(--neo-color-disabled) !important;
}

:deep(.system-account-row:hover > td) {
  background-color: var(--neo-color-bg-primary) !important;
}

/* ====== 响应式 ====== */
@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
  }

  .page-content {
    padding: 16px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .search-row {
    flex-direction: column;
  }

  .search-input-wrap {
    min-width: 100%;
  }

  .neo-select {
    width: 100% !important;
  }
}
</style>
