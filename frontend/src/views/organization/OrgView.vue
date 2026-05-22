<template>
  <div class="org-page">
    <!-- 左侧面板：组织树 -->
    <div class="left-panel">
      <div class="panel-header">
        <el-input
          v-model="keyword"
          placeholder="搜索组织"
          clearable
          prefix-icon="Search"
        />
        <!-- 新建顶级组织：需要 organization create 权限 -->
        <el-button
          v-if="authStore.hasPermission('organization', 'create')"
          type="primary"
          @click="handleCreateRoot"
          style="margin-top: 8px; width: 100%"
        >
          <el-icon><Plus /></el-icon>
          新建顶级组织
        </el-button>
      </div>

      <div class="tree-list" v-loading="loading">
        <el-tree
          ref="treeRef"
          :data="filteredTree"
          :props="treeProps"
          node-key="id"
          highlight-current
          default-expand-all
          :expand-on-click-node="false"
          :filter-node-method="filterNode"
          @node-click="handleNodeClick"
        >
          <template #default="{ node, data }">
            <div class="tree-node" :class="{ disabled: data.status === 0 }">
              <span class="node-name">{{ data.name }}</span>
              <el-tag v-if="data.status === 0" size="small" type="info">停用</el-tag>
              <span class="node-level">L{{ data.level }}</span>
            </div>
          </template>
        </el-tree>

        <el-empty v-if="!loading && treeData.length === 0" description="暂无组织数据" />
      </div>
    </div>

    <!-- 右侧面板：编辑表单 -->
    <div class="right-panel">
      <template v-if="selectedOrg !== null">
        <div class="panel-header">
          <h3>{{ isCreate ? '新建组织' : '编辑组织' }}</h3>
        </div>

        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-width="100px"
          label-position="right"
          class="edit-form"
          v-loading="saving"
        >
          <el-form-item label="组织名称" prop="name">
            <el-input
              v-model="formData.name"
              placeholder="请输入组织名称"
              maxlength="100"
              show-word-limit
              :disabled="!canEdit"
            />
          </el-form-item>

          <el-form-item label="上级组织">
            <el-tree-select
              v-model="formData.parent_id"
              :data="treeData"
              :props="{ value: 'id', label: 'name', children: 'children' }"
              placeholder="无（顶级组织）"
              clearable
              check-strictly
              :render-after-expand="false"
              style="width: 100%"
              :disabled="!isCreate || !canEdit"
            />
          </el-form-item>

          <el-form-item label="排序序号" prop="sort_order">
            <el-input-number
              v-model="formData.sort_order"
              :min="0"
              :max="9999"
              controls-position="right"
              :disabled="!canEdit"
            />
          </el-form-item>

          <!-- 启用状态：需要 organization update 权限 -->
          <el-form-item v-if="!isCreate" label="启用状态">
            <el-switch
              v-if="authStore.hasPermission('organization', 'update')"
              :model-value="formData.status === 1"
              active-text="启用"
              inactive-text="停用"
              @change="handleToggleStatus"
            />
            <el-tag v-else :type="formData.status === 1 ? 'success' : 'info'" size="small">
              {{ formData.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </el-form-item>

          <el-form-item v-if="!isCreate" label="层级深度">
            <el-tag type="info">第 {{ selectedOrg.level }} 级</el-tag>
          </el-form-item>

          <el-form-item v-if="!isCreate" label="子组织">
            <el-tag>{{ selectedOrg.children?.length || 0 }} 个子组织</el-tag>
          </el-form-item>

          <el-form-item>
            <div class="form-actions">
              <!-- 保存：新建需要 create，编辑需要 update -->
              <el-button
                v-if="authStore.hasPermission('organization', isCreate ? 'create' : 'update')"
                type="primary"
                @click="handleSave"
              >
                保存
              </el-button>
              <!-- 新增下级：需要 organization create 权限 -->
              <el-button
                v-if="authStore.hasPermission('organization', 'create')"
                @click="handleCreateChild"
              >
                新增下级
              </el-button>
              <!-- 删除：需要 organization delete 权限 -->
              <el-button
                v-if="!isCreate && authStore.hasPermission('organization', 'delete')"
                type="danger"
                @click="handleDelete"
              >
                删除
              </el-button>
              <el-button @click="handleCancel">取消</el-button>
            </div>
          </el-form-item>
        </el-form>
      </template>

      <div v-else class="empty-state">
        <el-icon :size="48" color="#C0C4CC"><OfficeBuilding /></el-icon>
        <p>请从左侧选择组织或点击"新建顶级组织"</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type ElTree } from 'element-plus'
import { Plus, OfficeBuilding } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import {
  getOrgTree,
  createOrg,
  updateOrg,
  deleteOrg,
  type OrgNode,
  type OrgCreateForm,
} from '@/api/organization'

const authStore = useAuthStore()

// 编辑权限：新建时需要 create，编辑时需要 update
const canEdit = computed(() => {
  if (isCreate.value) return authStore.hasPermission('organization', 'create')
  return authStore.hasPermission('organization', 'update')
})

// ==================== 树配置 ====================

const treeProps = {
  children: 'children',
  label: 'name',
}

const treeRef = ref<InstanceType<typeof ElTree>>()

// ==================== 状态 ====================

const loading = ref(false)
const treeData = ref<OrgNode[]>([])
const keyword = ref('')

const selectedOrg = ref<OrgNode | null>(null)
const isCreate = ref(false)

const saving = ref(false)
const formRef = ref<FormInstance>()

const defaultForm: OrgCreateForm & { status: number } = {
  name: '',
  parent_id: null,
  sort_order: 0,
  status: 1,
}

const formData = ref({ ...defaultForm })

// ==================== 搜索过滤 ====================

const filteredTree = computed(() => treeData.value)

watch(keyword, (val) => {
  treeRef.value?.filter(val)
})

function filterNode(value: string, data: OrgNode): boolean {
  if (!value) return true
  return data.name.includes(value)
}

// ==================== 表单校验 ====================

const rules: FormRules = {
  name: [
    { required: true, message: '请输入组织名称', trigger: 'blur' },
    { max: 100, message: '组织名称不能超过100个字符', trigger: 'blur' },
  ],
}

// ==================== 加载树 ====================

async function loadTree() {
  loading.value = true
  try {
    treeData.value = await getOrgTree(true)
  } catch (e) {
    // interceptor handles error
  } finally {
    loading.value = false
  }
}

// ==================== 树节点点击 ====================

function handleNodeClick(data: OrgNode) {
  isCreate.value = false
  selectedOrg.value = data
  formData.value = {
    name: data.name,
    parent_id: data.parent_id,
    sort_order: data.sort_order,
    status: data.status,
  }
}

// ==================== 新建 ====================

function handleCreateRoot() {
  isCreate.value = true
  selectedOrg.value = { id: -1 } as OrgNode
  formData.value = { ...defaultForm }
}

function handleCreateChild() {
  if (!selectedOrg.value || selectedOrg.value.level >= 4) {
    ElMessage.warning('组织层级最多支持4级')
    return
  }
  isCreate.value = true
  formData.value = {
    name: '',
    parent_id: selectedOrg.value.id,
    sort_order: 0,
    status: 1,
  }
}

// ==================== 保存 ====================

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isCreate.value) {
      await createOrg({
        name: formData.value.name,
        parent_id: formData.value.parent_id,
        sort_order: formData.value.sort_order,
      })
      ElMessage.success('创建成功')
      await loadTree()
      selectedOrg.value = null
    } else {
      const updated = await updateOrg(selectedOrg.value!.id, {
        name: formData.value.name,
        sort_order: formData.value.sort_order,
      })
      ElMessage.success('保存成功')
      await loadTree()
      const refreshed = findNodeById(treeData.value, updated.id)
      if (refreshed) handleNodeClick(refreshed)
    }
  } catch (e) {
    // interceptor handles error
  } finally {
    saving.value = false
  }
}

// ==================== 状态切换 ====================

async function handleToggleStatus(val: boolean) {
  if (!selectedOrg.value) return
  const tip = val ? '确认启用该组织？' : '停用后该组织不参与排班，确认停用？'
  try {
    await ElMessageBox({
      title: '确认操作？',
      message: tip,
      showCancelButton: true,
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const updated = await updateOrg(selectedOrg.value.id, {
      status: val ? 1 : 0,
    })
    formData.value.status = updated.status
    ElMessage.success(updated.status === 1 ? '已启用' : '已停用')
    await loadTree()
    const refreshed = findNodeById(treeData.value, updated.id)
    if (refreshed) handleNodeClick(refreshed)
  } catch (e) {
    // 用户取消或接口错误
  }
}

// ==================== 删除 ====================

async function handleDelete() {
  if (!selectedOrg.value) return

  if (selectedOrg.value.children && selectedOrg.value.children.length > 0) {
    ElMessage.warning('该组织下有子组织，无法删除')
    return
  }

  try {
    await ElMessageBox({
      title: '确认删除？',
      message: `确认删除组织「${selectedOrg.value.name}」？删除后数据无法恢复。`,
      showCancelButton: true,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteOrg(selectedOrg.value.id)
    ElMessage.success('删除成功')
    selectedOrg.value = null
    await loadTree()
  } catch (e) {
    // 用户取消或接口错误
  }
}

// ==================== 取消 ====================

function handleCancel() {
  selectedOrg.value = null
}

// ==================== 工具函数 ====================

function findNodeById(tree: OrgNode[], id: number): OrgNode | null {
  for (const node of tree) {
    if (node.id === id) return node
    if (node.children) {
      const found = findNodeById(node.children, id)
      if (found) return found
    }
  }
  return null
}

// ==================== 初始化 ====================

onMounted(() => {
  loadTree()
})
</script>

<style scoped>
.org-page {
  display: flex;
  height: calc(100vh - 56px - 40px);
  gap: 16px;
  padding: 16px;
  background: #F5F7FA;
  overflow-x: auto;
  min-width: 700px;
}

.left-panel {
  width: 320px;
  min-width: 280px;
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
}

.tree-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  padding-right: 8px;
  overflow: hidden;
}

.tree-node.disabled {
  opacity: 0.55;
}

.node-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.node-level {
  font-size: 11px;
  color: #C0C4CC;
  background: #F5F7FA;
  padding: 0 6px;
  border-radius: 3px;
  flex-shrink: 0;
}

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

.right-panel .panel-header {
  padding: 16px 24px;
}

.right-panel .panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1F2D3D;
}

.edit-form {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px 24px;
}

.form-actions {
  display: flex;
  gap: 8px;
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
