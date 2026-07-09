<template>
  <div class="swap-page">
    <!-- Neo 卡片容器 — 使用全局 neo-card 类 -->
    <div class="swap-card neo-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <!-- Tab 栏 -->
        <div class="filter-card-group">
          <el-tabs v-model="activeTab" class="swap-tabs" @tab-change="handleTabChange">
            <el-tab-pane label="我的申请" name="mine" />
            <el-tab-pane label="待我处理" name="pending" />
            <el-tab-pane v-if="canViewAll && authStore.hasPermission('swap', 'read')" label="全部记录" name="all" />
          </el-tabs>
        </div>

        <!-- 状态筛选 -->
        <div class="filter-card-group">
          <span class="filter-card-label">状态</span>
          <el-select v-model="statusFilter" placeholder="全部状态" clearable class="toolbar-filter" @change="fetchData">
            <el-option label="待确认" value="pending_confirm" />
            <el-option label="待认领" value="pending_claim" />
            <el-option label="待审批" value="pending_approve" />
            <el-option label="已完成" value="completed" />
            <el-option label="已撤回" value="cancelled" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="对方已拒绝" value="target_refused" />
          </el-select>
        </div>

        <!-- 操作按钮 -->
        <div class="filter-card-group filter-card-actions">
          <el-button v-if="authStore.hasPermission('swap', 'create')" class="btn-neo-primary btn-neo-sm" @click="showForm = true">
            <el-icon><Plus /></el-icon>
            发起换班申请
          </el-button>
        </div>
      </div>

      <!-- 表格区域 -->
      <div class="table-area">
        <SwapRecordTable
          :items="tableData"
          :loading="loading"
          :total="total"
          :page-size="pageSize"
          @detail="handleDetail"
          @confirm="handleConfirm"
          @refuse="handleRefuse"
          @claim="handleClaim"
          @approve="handleApprove"
          @reject="handleReject"
          @cancel="handleCancel"
          @page-change="handlePageChange"
        />
      </div>
    </div>

    <SwapRequestForm v-model:visible="showForm" @success="fetchData" />
    <SwapDetailPanel v-model:visible="showDetail" :data="currentItem" />

    <el-dialog v-model="showRefuseDialog" title="拒绝换班" width="420px" class="swap-dialog">
      <div class="alert-card alert-card--danger">
        <span class="alert-card__icon">⚠</span>
        <span class="alert-card__content">拒绝后将通知申请人，请认真填写拒绝原因。</span>
      </div>
      <el-input v-model="refuseComment" type="textarea" :rows="3" placeholder="请输入拒绝原因（选填）" style="margin-top:12px;" />
      <template #footer>
        <el-button class="btn-neo-ghost btn-neo-sm" @click="showRefuseDialog = false">取消</el-button>
        <el-button class="btn-neo-danger btn-neo-sm" :loading="actionLoading" @click="doRefuse">确认拒绝</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showApproveDialog" title="审批意见" width="420px" class="swap-dialog">
      <div class="alert-card alert-card--info">
        <span class="alert-card__icon">ℹ</span>
        <span class="alert-card__content">审批通过后，该调班申请将生效并通知相关人员。</span>
      </div>
      <el-input v-model="approveComment" type="textarea" :rows="3" placeholder="请输入审批意见（选填）" style="margin-top:12px;" />
      <template #footer>
        <el-button class="btn-neo-ghost btn-neo-sm" @click="showApproveDialog = false">取消</el-button>
        <el-button class="btn-neo-primary btn-neo-sm" :loading="actionLoading" @click="doApprove">确认通过</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRejectDialog" title="拒绝原因" width="420px" class="swap-dialog">
      <div class="alert-card alert-card--danger">
        <span class="alert-card__icon">✕</span>
        <span class="alert-card__content">对方已拒绝您的调班申请，请填写拒绝原因。</span>
      </div>
      <el-input v-model="rejectComment" type="textarea" :rows="3" placeholder="请输入拒绝原因（选填）" style="margin-top:12px;" />
      <template #footer>
        <el-button class="btn-neo-ghost btn-neo-sm" @click="showRejectDialog = false">取消</el-button>
        <el-button class="btn-neo-danger btn-neo-sm" :loading="actionLoading" @click="doReject">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import {
  getSwapList, getAllSwapList, confirmSwap, claimSwap, refuseSwap,
  approveSwap, rejectSwap, cancelSwap,
} from '@/api/swap'
import { Plus } from '@element-plus/icons-vue'
import type { SwapRequestItem } from '@/api/swap'
import SwapRecordTable from './components/SwapRecordTable.vue'
import { useConfirm } from '@/composables/useConfirm'
import SwapRequestForm from './components/SwapRequestForm.vue'
import SwapDetailPanel from './components/SwapDetailPanel.vue'

const authStore = useAuthStore()
const route = useRoute()
const { confirmInfo, confirmWarning } = useConfirm()
const canViewAll = computed(() => authStore.hasRole('admin') || authStore.hasRole('scheduler') || authStore.hasRole('leader'))

const activeTab = ref('mine')
const statusFilter = ref('')
const loading = ref(false)
const tableData = ref<SwapRequestItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const showForm = ref(false)
const showDetail = ref(false)
const currentItem = ref<SwapRequestItem | null>(null)

const showApproveDialog = ref(false)
const showRejectDialog = ref(false)
const showRefuseDialog = ref(false)
const approveComment = ref('')
const rejectComment = ref('')
const refuseComment = ref('')
const actionLoading = ref(false)
let actionTargetId = 0

const fetchData = async () => {
  loading.value = true
  try {
    if (activeTab.value === 'all') {
      const { data: res } = await getAllSwapList({
        status: statusFilter.value || undefined, page: page.value, page_size: pageSize.value,
      })
      tableData.value = res.items || []
      total.value = res.total || 0
    } else {
      const role = activeTab.value === 'pending' ? 'target' : 'requester'
      const { data: res } = await getSwapList({
        role, status: statusFilter.value || undefined, page: page.value, page_size: pageSize.value,
      })
      tableData.value = res.items || []
      total.value = res.total || 0
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '获取数据失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

const handleTabChange = () => {
  page.value = 1
  statusFilter.value = ''
  fetchData()
}

const handlePageChange = (p: number) => {
  page.value = p
  fetchData()
}

const handleDetail = (row: SwapRequestItem) => {
  currentItem.value = row
  showDetail.value = true
}

const handleConfirm = async (row: SwapRequestItem) => {
  try {
    await confirmInfo('确认与对方换班？', '确认换班')
    await confirmSwap(row.id)
    ElMessage.success('确认成功')
    fetchData()
  } catch (e) {
    if (e instanceof Error && e.message === 'Cancelled') return
    ElMessage.error('操作失败')
  }
}

const handleClaim = async (row: SwapRequestItem) => {
  try {
    await confirmInfo('确认认领该换班申请？', '认领换班')
    await claimSwap(row.id)
    ElMessage.success('认领成功')
    fetchData()
  } catch (e) {
    if (e instanceof Error && e.message === 'Cancelled') return
    ElMessage.error('操作失败')
  }
}

const handleApprove = (row: SwapRequestItem) => {
  actionTargetId = row.id
  approveComment.value = ''
  showApproveDialog.value = true
}

const doApprove = async () => {
  actionLoading.value = true
  try {
    await approveSwap(actionTargetId, approveComment.value || undefined)
    ElMessage.success('审批通过')
    showApproveDialog.value = false
    fetchData()
  } catch {} finally {
    actionLoading.value = false
  }
}

const handleReject = (row: SwapRequestItem) => {
  actionTargetId = row.id
  rejectComment.value = ''
  showRejectDialog.value = true
}

const doReject = async () => {
  actionLoading.value = true
  try {
    await rejectSwap(actionTargetId, rejectComment.value || undefined)
    ElMessage.success('已拒绝')
    showRejectDialog.value = false
    fetchData()
  } catch {} finally {
    actionLoading.value = false
  }
}

const handleRefuse = (row: SwapRequestItem) => {
  actionTargetId = row.id
  refuseComment.value = ''
  showRefuseDialog.value = true
}

const doRefuse = async () => {
  actionLoading.value = true
  try {
    await refuseSwap(actionTargetId, refuseComment.value || undefined)
    ElMessage.success('已拒绝')
    showRefuseDialog.value = false
    fetchData()
  } catch {} finally {
    actionLoading.value = false
  }
}

const handleCancel = async (row: SwapRequestItem) => {
  try {
    await confirmWarning('确认撤回该调班申请？', '撤回申请')
    await cancelSwap(row.id)
    ElMessage.success('已撤回')
    fetchData()
  } catch (e) {
    if (e instanceof Error && e.message === 'Cancelled') return
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  // 从 URL query 读取初始 tab
  const tab = route.query.tab as string | undefined
  if (tab) {
    activeTab.value = tab
  }
  fetchData()
})
</script>

<style scoped>
/* 页面容器 — 仅布局，不重复定义全局样式 */
.swap-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px - 40px);
  overflow-x: auto;
}

/* 外层包装 — 利用全局 neo-card 的样式 */
.swap-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin: 20px;
  overflow: hidden;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: var(--neo-border-thick) solid var(--neo-color-border);
  background: var(--neo-color-bg-primary);
  flex-wrap: wrap;
}

/* 筛选小组 — 复用全局 neo-card 或独立小卡 */
.filter-card-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
  background: var(--neo-color-bg-card);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-default);
  padding: 8px 12px;
  transition: all 0.12s ease;
}

.filter-card-group:hover {
  box-shadow: var(--neo-shadow-hover);
  transform: translate(var(--neo-translate-xs), var(--neo-translate-xs));
}

.filter-card-label {
  font-size: 10px;
  font-weight: 900;
  color: var(--neo-color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  line-height: 1;
}

.filter-card-actions {
  justify-content: flex-end;
  display: flex;
  align-items: flex-start;
}

/* Tab 栏 — 覆盖全局 el-tabs__item 样式 */
.swap-tabs :deep(.el-tabs__header) {
  border-bottom: none !important;
  margin-bottom: 0 !important;
  padding: 0 !important;
}

.swap-tabs :deep(.el-tabs__item) {
  font-weight: 700 !important;
  color: var(--neo-color-text-primary) !important;
  border: 3px solid transparent !important;
  border-bottom: none !important;
  transition: all 0.12s ease !important;
  padding: 8px 20px !important;
  font-size: 14px !important;
  letter-spacing: 0.3px !important;
}

.swap-tabs :deep(.el-tabs__item.is-active) {
  background: var(--neo-color-accent-blue) !important;
  border: 3px solid var(--neo-color-border) !important;
  border-bottom: 3px solid var(--neo-color-bg-primary) !important;
  color: var(--neo-color-bg-card) !important;
  font-weight: 900 !important;
  transform: translateY(1px);
}

.swap-tabs :deep(.el-tabs__active-bar) {
  display: none !important;
}

/* 筛选下拉框 — 覆盖全局 .el-select__wrapper */
.filter-bar .toolbar-filter {
  width: 180px !important;
  flex: 0 0 auto;
}

.filter-bar .toolbar-filter .el-select__wrapper {
  height: 38px !important;
  min-height: 38px !important;
  border: 3px solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-md) !important;
  box-shadow: var(--neo-shadow-md) !important;
  background: var(--neo-color-bg-card) !important;
  padding: 0 10px !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  transition: all 0.1s ease !important;
}

.filter-bar .toolbar-filter .el-select__wrapper:hover {
  box-shadow: 4px 4px 0px 0px var(--neo-color-border) !important;
  background: var(--neo-color-bg-primary) !important;
}

.filter-bar .toolbar-filter .el-select__wrapper.is-focused {
  box-shadow: 4px 4px 0px 0px var(--neo-color-accent-yellow) !important;
  border-color: var(--neo-color-border) !important;
  background: var(--neo-color-bg-primary) !important;
}

.filter-bar .toolbar-filter .el-input__inner {
  font-weight: 700 !important;
  font-size: 13px !important;
  color: var(--neo-color-text-primary) !important;
}

.filter-bar .toolbar-filter .el-input__inner::placeholder {
  color: var(--neo-color-text-muted) !important;
  font-weight: 600 !important;
}

/* 表格区域 */
.table-area {
  flex: 1;
  overflow: auto;
  padding: 16px 20px 20px;
}

/* 分页 */
.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* 弹窗 — 覆盖全局 .el-dialog */
.swap-dialog :deep(.el-dialog) {
  border: var(--neo-border-ultra) solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-md) !important;
  box-shadow: 10px 10px 0px 0px #000000 !important;
  background: var(--neo-color-bg-primary) !important;
}

.swap-dialog :deep(.el-dialog__header) {
  border-bottom: 3px solid var(--neo-color-border) !important;
  background: var(--neo-color-bg-primary) !important;
  padding: 16px 20px !important;
  margin: 0 !important;
}

.swap-dialog :deep(.el-dialog__title) {
  font-weight: 900 !important;
  color: var(--neo-color-text-primary) !important;
  font-size: 16px !important;
  letter-spacing: 0.3px !important;
}

.swap-dialog :deep(.el-dialog__body) {
  padding: 20px !important;
  background: var(--neo-color-bg-primary) !important;
}

.swap-dialog :deep(.el-dialog__footer) {
  border-top: 3px solid var(--neo-color-border) !important;
  padding: 14px 20px !important;
  background: var(--neo-color-bg-primary) !important;
}

.swap-dialog :deep(.el-textarea__inner) {
  border: 3px solid var(--neo-color-border) !important;
  border-radius: var(--neo-radius-md) !important;
  box-shadow: var(--neo-shadow-md) !important;
  background: var(--neo-color-bg-card) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  transition: all 0.1s ease !important;
}

.swap-dialog :deep(.el-textarea__inner:focus) {
  box-shadow: 4px 4px 0px 0px var(--neo-color-accent-yellow) !important;
  background: var(--neo-color-bg-primary) !important;
}

/* ============================================
   移动端适配
   ============================================ */

@media (max-width: 768px) {
  .swap-page {
    height: auto;
    min-height: calc(100vh - 56px - 40px);
  }

  .swap-card {
    margin: 12px;
  }

  .filter-bar {
    padding: 12px;
    gap: 8px;
  }

  .filter-card-group {
    flex: 1 1 calc(50% - 8px);
    min-width: 120px;
    padding: 6px 8px;
  }

  .filter-card-actions {
    flex: 1 1 100%;
  }

  .filter-card-actions .btn-neo-primary {
    width: 100%;
    justify-content: center;
  }

  .table-area {
    padding: 0 12px 12px;
  }

  .filter-bar .toolbar-filter {
    width: 100% !important;
  }

  .filter-bar .toolbar-filter .el-select__wrapper {
    width: 100% !important;
  }
}

@media (max-width: 480px) {
  .swap-card {
    margin: 8px;
  }

  .filter-card-group {
    flex: 1 1 100%;
  }
}
</style>
