<template>
  <el-table :data="items" v-loading="loading" stripe>
    <el-table-column prop="request_no" label="申请编号" width="160" />
    <el-table-column label="类型" width="100">
      <template #default="{ row }">
        <el-tag :type="row.swap_type === 'specified' ? '' : 'success'" size="small">
          {{ row.swap_type === 'specified' ? '指定换班' : '开放换班' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="发起人" prop="requester_name" width="100" />
    <el-table-column label="发起人班次" min-width="160">
      <template #default="{ row }">
        <div>{{ row.requester_schedule_date }}</div>
        <div style="font-size: 12px; color: #8492a6;">{{ row.requester_shift_name }}</div>
      </template>
    </el-table-column>
    <el-table-column label="对方/认领人" min-width="120">
      <template #default="{ row }">
        {{ row.target_name || row.claimer_name || '-' }}
      </template>
    </el-table-column>
    <el-table-column label="对方班次" min-width="160">
      <template #default="{ row }">
        <template v-if="row.target_schedule_date">
          <div>{{ row.target_schedule_date }}</div>
          <div style="font-size: 12px; color: #8492a6;">{{ row.target_shift_name }}</div>
        </template>
        <span v-else>-</span>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="120">
      <template #default="{ row }">
        <el-tag :type="statusTagType(row.status)" size="small">
          {{ statusLabel(row.status) }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="申请时间" width="170">
      <template #default="{ row }">
        {{ row.created_at?.slice(0, 16) }}
      </template>
    </el-table-column>
    <el-table-column label="操作" width="200" fixed="right">
      <template #default="{ row }">
        <el-button type="primary" text size="small" @click="$emit('detail', row)">
          详情
        </el-button>
        <!-- 待确认：被换人可确认/拒绝 -->
        <template v-if="row.status === 'pending_confirm' && row.target_id === currentUserId">
          <el-button type="success" text size="small" @click="$emit('confirm', row)">
            确认
          </el-button>
          <el-button type="danger" text size="small" @click="$emit('refuse', row)">
            拒绝
          </el-button>
        </template>
        <!-- 待认领：其他人可认领 -->
        <template v-if="row.status === 'pending_claim' && row.requester_id !== currentUserId">
          <el-button type="success" text size="small" @click="$emit('claim', row)">
            认领
          </el-button>
        </template>
        <!-- 待审批：管理员可审批 -->
        <template v-if="row.status === 'pending_approve' && isAdmin">
          <el-button type="success" text size="small" @click="$emit('approve', row)">
            通过
          </el-button>
          <el-button type="danger" text size="small" @click="$emit('reject', row)">
            拒绝
          </el-button>
        </template>
        <!-- 待确认/待认领/待审批：发起人可撤回 -->
        <template v-if="['pending_confirm', 'pending_claim', 'pending_approve'].includes(row.status) && row.requester_id === currentUserId">
          <el-button type="warning" text size="small" @click="$emit('cancel', row)">
            撤回
          </el-button>
        </template>
      </template>
    </el-table-column>
  </el-table>

  <div class="table-pagination" v-if="total > pageSize">
    <el-pagination
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      @current-change="$emit('page-change', currentPage)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { SwapRequestItem } from '@/api/swap'

const props = defineProps<{
  items: SwapRequestItem[]
  loading?: boolean
  total?: number
  pageSize?: number
}>()

defineEmits<{
  (e: 'detail', row: SwapRequestItem): void
  (e: 'confirm', row: SwapRequestItem): void
  (e: 'refuse', row: SwapRequestItem): void
  (e: 'claim', row: SwapRequestItem): void
  (e: 'approve', row: SwapRequestItem): void
  (e: 'reject', row: SwapRequestItem): void
  (e: 'cancel', row: SwapRequestItem): void
  (e: 'page-change', page: number): void
}>()

const authStore = useAuthStore()
const currentUserId = computed(() => authStore.userId)
const isAdmin = computed(() => authStore.hasRole('admin') || authStore.hasRole('scheduler'))

const currentPage = ref(1)

const statusLabels: Record<string, string> = {
  pending_confirm: '待确认',
  pending_claim: '待认领',
  pending_approve: '待审批',
  approved: '已通过',
  completed: '已完成',
  cancelled: '已撤回',
  rejected: '已拒绝',
  target_refused: '对方已拒绝',
}

const statusLabel = (s: string) => statusLabels[s] || s

const statusTagType = (s: string) => {
  const map: Record<string, string> = {
    pending_confirm: 'warning',
    pending_claim: 'warning',
    pending_approve: 'warning',
    approved: '',
    completed: 'success',
    cancelled: 'info',
    rejected: 'danger',
    target_refused: 'danger',
  }
  return (map[s] || 'info') as any
}
</script>

<style scoped>
.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
