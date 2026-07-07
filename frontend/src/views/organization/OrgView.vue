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
          class="neo-input"
          style="width: 100%;"
        />
        <!-- 新建顶级组织：需要 organization create 权限 -->
        <el-button
          v-if="authStore.hasPermission('organization', 'create')"
          class="btn-neo-primary"
          @click="handleCreateRoot"
          style="margin-top: 12px; width: 100%"
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
              <span v-if="data.code" class="node-code">{{ data.code }}</span>
              <span v-else class="node-code-empty">未设置</span>
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
              class="neo-input"
            />
          </el-form-item>

          <el-form-item label="组织代码" prop="code">
            <el-input
              v-model="formData.code"
              :placeholder="isCreate ? '留空自动生成（拼音首字母）' : '未设置'"
              maxlength="50"
              show-word-limit
              :disabled="!canEdit"
              class="neo-input"
            />
            <div v-if="isCreate" style="font-size: 12px; color: #909399; margin-top: 4px;">
              留空将根据组织名称自动生成（拼音首字母简称）
            </div>
            <div v-else style="font-size: 12px; color: #909399; margin-top: 4px;">
              <template v-if="formData.code">
                修改后将影响后续生成的工号前缀
              </template>
              <template v-else>
                该组织尚未生成代码，保存时留空将自动生成
              </template>
            </div>
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
              class="neo-input"
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
              class="neo-input"
            />
          </el-form-item>


          <!-- 启用状态：需要 organization update 权限 -->
          <el-form-item v-if="!isCreate" label="启用状态">
            <span
              v-if="authStore.hasPermission('organization', 'update')"
              class="neo-switch-inline"
              :class="{ 'is-checked': formData.status === 1, 'is-disabled': !canEdit }"
              @click="handleToggleStatus(formData.status === 0)"
            >
              <span class="neo-switch-knob"></span>
            </span>
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
                class="btn-neo-primary"
                @click="handleSave"
              >
                保存
              </el-button>
              <!-- 新增下级：需要 organization create 权限 -->
              <el-button
                v-if="authStore.hasPermission('organization', 'create')"
                class="btn-neo-success"
                @click="handleCreateChild"
              >
                新增下级
              </el-button>
              <!-- 删除：需要 organization delete 权限 -->
              <el-button
                v-if="!isCreate && authStore.hasPermission('organization', 'delete')"
                class="btn-neo-danger"
                @click="handleDelete"
              >
                删除
              </el-button>
              <el-button class="btn-neo-ghost" @click="handleCancel">取消</el-button>
            </div>
          </el-form-item>
        </el-form>
      </template>

      <div v-else class="empty-state empty-state--flex">
        <el-icon :size="48" color="#C0C4CC"><OfficeBuilding /></el-icon>
        <p>请从左侧选择组织或点击"新建顶级组织"</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules, type ElTree } from 'element-plus'
import { useConfirm } from '@/composables/useConfirm'
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

const { confirm } = useConfirm()

const treeRef = ref<InstanceType<typeof ElTree>>()

// ==================== 状态 ====================

const loading = ref(false)
const treeData = ref<OrgNode[]>([])
const keyword = ref('')

const selectedOrg = ref<OrgNode | null>(null)
const isCreate = ref(false)

const saving = ref(false)
const formRef = ref<FormInstance>()

const defaultForm: OrgCreateForm & { status: number; daily_max_scheduled_ratio: number | null } = {
  name: '',
  parent_id: null,
  code: '',
  sort_order: 0,
  status: 1,
  daily_max_scheduled_ratio: null,
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
    code: data.code || '',
    parent_id: data.parent_id,
    sort_order: data.sort_order,
    status: data.status,
    daily_max_scheduled_ratio: data.daily_max_scheduled_ratio ?? null,
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
    code: '',
    sort_order: 0,
    status: 1,
    daily_max_scheduled_ratio: null,
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
        code: formData.value.code || undefined,
        sort_order: formData.value.sort_order,
      })
      ElMessage.success('创建成功')
      await loadTree()
      selectedOrg.value = null
    } else {
      const updateData: any = {
        name: formData.value.name,
        sort_order: formData.value.sort_order,
        daily_max_scheduled_ratio: formData.value.daily_max_scheduled_ratio,
      }
      // code 为空时不传（后端不会覆盖），有值时传递
      if (formData.value.code) {
        updateData.code = formData.value.code
      }
      const updated = await updateOrg(selectedOrg.value!.id, updateData)
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
    await confirm({
      type: 'warning',
      title: '确认操作？',
      message: tip,
      confirmText: '确认',
      cancelText: '取消',
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
    await confirm({
      type: 'danger',
      title: '确认删除？',
      message: `确认删除组织「${selectedOrg.value.name}」？删除后数据无法恢复。`,
      confirmText: '删除',
      cancelText: '取消',
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
  background: #FFFDF5;
  overflow-x: auto;
  min-width: 700px;
}

/* --- OrgView 特有：树形组件样式 --- */
.tree-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 12px 12px 0px;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.tree-node {
  padding: 10px 12px;
  background: #FFFDF5;
  border: 3px solid #000000;
  border-radius: 4px;
  box-shadow: 2px 2px 0px 0px #000000;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.15s ease;
  /* 宽度填满 el-tree-node__content 的可用空间 */
  width: 100%;
  box-sizing: border-box;
}
.tree-node:hover:not(.disabled) {
  background: #FFFFFF;
  box-shadow: 4px 4px 0px 0px #000000;
  transform: translate(-1px, -1px);
}
.tree-node.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.tree-node.is-current > .tree-node {
  background: #DBEAFE;
  border-color: #3B82F6;
}
.node-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 700;
  color: #000000;
}
.node-level {
  font-size: 11px;
  color: #999;
  background: #F5F5F0;
  padding: 0 6px;
  border-radius: 2px;
  border: 1px solid #DDD;
  flex-shrink: 0;
  font-weight: 700;
}
.node-code {
  font-size: 11px;
  color: #3B82F6;
  background: #EFF6FF;
  padding: 0 6px;
  border-radius: 2px;
  border: 1px solid #3B82F6;
  flex-shrink: 0;
  font-weight: 700;
}
.node-code-empty {
  font-size: 0;
  width: 0;
  height: 0;
  padding: 0;
  margin: 0;
  border: 0;
  background: none;
  display: none;
}

/* 覆盖 Element Plus 原生树节点样式 */
/*
 * DOM 结构：
 *   .el-tree-node (每个节点的外层容器)
 *     ├── .el-tree-node__content   ← 包含展开箭头 + .tree-node 卡片
 *     └── .el-tree-node__children  ← 子节点列表（如果有的话）
 *
 * 间距模型（统一用 .el-tree-node__children 的 padding-top 控制）：
 *   - 父子间距 = 父节点 .el-tree-node__children 的 padding-top
 *   - 兄弟间距 = 前一个兄弟 .el-tree-node__children 的 padding-top
 *   - 两者都来自同一个 CSS 规则，视觉上必然一致
 */

/* 每个节点基础重置 */
.tree-list :deep(.el-tree-node) {
  padding-left: 0 !important;
  padding-bottom: 0 !important;
  outline: none;
}

/* 所有层级统一 .el-tree-node__content 的左缩进，确保卡片宽度一致 */
.tree-list :deep(.el-tree-node > .el-tree-node__content) {
  height: auto !important;
  min-height: auto !important;
  padding-left: 16px !important;
  border-radius: 0;
}

/* 展开/收起图标微调 */
.tree-list :deep(.el-tree-node__expand-icon) {
  margin-left: 4px;
  margin-right: 4px;
}

/* 核心间距规则：所有 .el-tree-node__children 统一 padding-top
   无论是父子之间还是兄弟之间，间距都来自同一个值 */
.tree-list :deep(.el-tree-node > .el-tree-node__children) {
  padding-top: 16px !important;
}

/* 子节点缩进：通过 .tree-node 的 margin-left 实现，不影响宽度计算 */
.tree-list :deep(.el-tree-node .el-tree-node > .tree-node) {
  margin-left: 12px;
}
.tree-list :deep(.el-tree-node .el-tree-node .el-tree-node > .tree-node) {
  margin-left: 24px;
}
.tree-list :deep(.el-tree-node .el-tree-node .el-tree-node .el-tree-node > .tree-node) {
  margin-left: 36px;
}

/* 覆盖全局 .left-panel/.right-panel 宽度 + 添加 neo 卡片视觉 */
.left-panel {
  width: 460px;
  min-width: 360px;
  max-width: 600px;
  background: #FFFFFF;
  border: 3px solid #000000;
  border-radius: 4px;
  box-shadow: 4px 4px 0px 0px #000000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.left-panel:hover {
  box-shadow: 6px 6px 0px 0px #000000;
  transform: translate(-1px, -1px);
  transition: all 0.15s ease;
}
.left-panel .panel-header {
  padding: 20px 16px;
  border-bottom: 3px solid #000000;
  background: #FFFDF5;
}
.right-panel {
  flex: 1;
  min-width: 400px;
  background: #FFFFFF;
  border: 3px solid #000000;
  border-radius: 4px;
  box-shadow: 4px 4px 0px 0px #000000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.right-panel:hover {
  box-shadow: 6px 6px 0px 0px #000000;
  transform: translate(-1px, -1px);
  transition: all 0.15s ease;
}
.right-panel .panel-header { padding: 20px 24px; }
</style>
