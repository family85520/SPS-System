<template>
  <el-drawer
    :model-value="visible"
    title="调班详情"
    direction="rtl"
    size="480px"
    @close="$emit('update:visible', false)"
  >
    <template v-if="data">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="申请编号">{{ data.request_no }}</el-descriptions-item>
        <el-descriptions-item label="调班类型">
          <el-tag :type="data.swap_type === 'specified' ? '' : 'success'" size="small">
            {{ data.swap_type === 'specified' ? '指定换班' : '开放换班' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="发起人">{{ data.requester_name }}</el-descriptions-item>
        <el-descriptions-item label="发起人班次">
          {{ data.requester_schedule_date }} {{ data.requester_shift_name }}
        </el-descriptions-item>
        <el-descriptions-item label="换班对象" v-if="data.target_name">
          {{ data.target_name }}
        </el-descriptions-item>
        <el-descriptions-item label="对方班次" v-if="data.target_schedule_date">
          {{ data.target_schedule_date }} {{ data.target_shift_name }}
        </el-descriptions-item>
        <el-descriptions-item label="认领人" v-if="data.claimer_name">
          {{ data.claimer_name }}
        </el-descriptions-item>
        <el-descriptions-item label="申请原因">{{ data.reason || '无' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(data.status)" size="small">
            {{ statusLabel(data.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="审批人" v-if="data.approver_name">
          {{ data.approver_name }}
        </el-descriptions-item>
        <el-descriptions-item label="审批时间" v-if="data.approved_at">
          {{ data.approved_at }}
        </el-descriptions-item>
        <el-descriptions-item label="审批意见" v-if="data.approve_comment">
          {{ data.approve_comment }}
        </el-descriptions-item>
        <el-descriptions-item label="申请时间">{{ data.created_at }}</el-descriptions-item>
      </el-descriptions>

      <!-- 状态时间线 -->
      <div style="margin-top: 24px">
        <h4 style="margin-bottom: 12px; font-size: 14px; color: #1F2D3D;">流程状态</h4>
        <el-timeline>
          <el-timeline-item timestamp="发起申请" placement="top" type="primary">
            {{ data.created_at }}
          </el-timeline-item>
          <el-timeline-item
            v-if="data.status !== 'pending_confirm' && data.status !== 'pending_claim'"
            :timestamp="data.swap_type === 'specified' ? '对方确认' : '被人认领'"
            placement="top"
            type="success"
          />
          <el-timeline-item
            v-if="['pending_approve', 'approved', 'completed', 'rejected'].includes(data.status)"
            timestamp="等待审批"
            placement="top"
            type="warning"
          />
          <el-timeline-item
            v-if="['approved', 'completed'].includes(data.status)"
            timestamp="审批通过"
            placement="top"
            type="success"
          >
            {{ data.approved_at }}
          </el-timeline-item>
          <el-timeline-item
            v-if="data.status === 'rejected'"
            timestamp="审批拒绝"
            placement="top"
            type="danger"
          >
            {{ data.approve_comment || '无意见' }}
          </el-timeline-item>
          <el-timeline-item
            v-if="data.status === 'completed'"
            timestamp="已完成"
            placement="top"
            type="success"
          />
          <el-timeline-item
            v-if="data.status === 'cancelled'"
            timestamp="已撤回"
            placement="top"
            type="info"
          />
        </el-timeline>
      </div>
    </template>

    <el-empty v-else description="暂无数据" />
  </el-drawer>
</template>

<script setup lang="ts">
import type { SwapRequestItem } from '@/api/swap'

defineProps<{
  visible: boolean
  data: SwapRequestItem | null
}>()

defineEmits<{
  (e: 'update:visible', value: boolean): void
}>()

const statusLabels: Record<string, string> = {
  pending_confirm: '待确认',
  pending_claim: '待认领',
  pending_approve: '待审批',
  approved: '已通过',
  completed: '已完成',
  cancelled: '已撤回',
  rejected: '已拒绝',
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
  }
  return (map[s] || 'info') as any
}
</script>
