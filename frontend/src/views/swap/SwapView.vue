<template>
  <div class="swap-page">
    <el-card shadow="never">
      <!-- 顶部工具栏 -->
      <div class="swap-toolbar">
        <div class="toolbar-left">
          <el-tabs v-model="activeTab" @tab-change="handleTabChange">
            <el-tab-pane label="我的申请" name="mine" />
            <el-tab-pane label="待我处理" name="pending" />
            <el-tab-pane v-if="isAdmin" label="全部记录" name="all" />
          </el-tabs>
        </div>
        <div class="toolbar-right">
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px" @change="fetchData">
            <el-option label="待确认" value="pending_confirm" />
            <el-option label="待认领" value="pending_claim" />
            <el-option label="待审批" value="pending_approve" />
            <el-option label="已完成" value="completed" />
            <el-option label="已撤回" value="cancelled" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="对方已拒绝" value="target_refused" />
          </el-select>
          <el-button v-if="authStore.hasPermission('swap', 'create')" type="primary" @click="showForm = true">
            发起换班申请
          </el-button>
        </div>
      </div>

      <!-- 数据表格 -->
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
    </el-card>

    <!-- 申请表单 -->
    <SwapRequestForm
      v-model:visible="showForm"
      @success="fetchData"
    />

    <!-- 详情抽屉 -->
    <SwapDetailPanel
      v-model:visible="showDetail"
      :data="currentItem"
    />

    <!-- 拒绝换班弹窗 -->
    <el-dialog v-model="showRefuseDialog" title="拒绝换班" width="400px">
      <el-input v-model="refuseComment" type="textarea" :rows="3" placeholder="请输入拒绝原因（选填）" />
      <template #footer>
        <el-button @click="showRefuseDialog = false">取消</el-button>
        <el-button type="danger" :loading="actionLoading" @click="doRefuse">确认拒绝</el-button>
      </template>
    </el-dialog>

    <!-- 审批弹窗 -->
    <el-dialog v-model="showApproveDialog" title="审批意见" width="400px">
      <el-input v-model="approveComment" type="textarea" :rows="3" placeholder="请输入审批意见（选填）" />
      <template #footer>
        <el-button @click="showApproveDialog = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="doApprove">确认通过</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRejectDialog" title="拒绝原因" width="400px">
      <el-input v-model="rejectComment" type="textarea" :rows="3" placeholder="请输入拒绝原因（选填）" />
      <template #footer>
        <el-button @click="showRejectDialog = false">取消</el-button>
        <el-button type="danger" :loading="actionLoading" @click="doReject">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import {
  getSwapList, getAllSwapList, confirmSwap, claimSwap, refuseSwap,
  approveSwap, rejectSwap, cancelSwap,
} from '@/api/swap'
import type { SwapRequestItem } from '@/api/swap'
import SwapRecordTable from './components/SwapRecordTable.vue'
import SwapRequestForm from './components/SwapRequestForm.vue'
import SwapDetailPanel from './components/SwapDetailPanel.vue'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.hasRole('admin') || authStore.hasRole('scheduler') || authStore.hasRole('leader'))

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
        status: statusFilter.value || undefined,
        page: page.value,
        page_size: pageSize.value,
      })
      tableData.value = res.items || []
      total.value = res.total || 0
    } else {
      const role = activeTab.value === 'pending' ? 'target' : 'requester'
      const { data: res } = await getSwapList({
        role,
        status: statusFilter.value || undefined,
        page: page.value,
        page_size: pageSize.value,
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
    await ElMessageBox.confirm('确认与对方换班？', '确认换班', {
      confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning',
    })
    await confirmSwap(row.id)
    ElMessage.success('确认成功')
    fetchData()
  } catch {}
}

const handleClaim = async (row: SwapRequestItem) => {
  try {
    await ElMessageBox.confirm('确认认领该换班申请？', '认领换班', {
      confirmButtonText: '认领', cancelButtonText: '取消', type: 'warning',
    })
    await claimSwap(row.id)
    ElMessage.success('认领成功')
    fetchData()
  } catch {}
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
    await ElMessageBox.confirm('确认撤回该调班申请？', '撤回申请', {
      confirmButtonText: '撤回', cancelButtonText: '取消', type: 'warning',
    })
    await cancelSwap(row.id)
    ElMessage.success('已撤回')
    fetchData()
  } catch {}
}

onMounted(fetchData)
</script>

<style scoped>
.swap-page {
  padding: 0;
}

.swap-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
}
</style>
