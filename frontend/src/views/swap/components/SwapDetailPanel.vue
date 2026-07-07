<template>
  <el-drawer
    :model-value="visible"
    title="调班详情"
    direction="rtl"
    size="480px"
    class="swap-drawer"
    @close="$emit('update:visible', false)"
  >
    <template v-if="data">
      <!-- 基本信息 — Neo 卡片化 el-descriptions -->
      <div class="info-section neo-card">
        <div class="info-section-header">
          <span class="info-section-title">基本信息</span>
          <el-tag :type="data.swap_type === 'specified' ? '' : 'success'" size="small" effect="dark">
            {{ data.swap_type === 'specified' ? '指定换班' : '开放换班' }}
          </el-tag>
        </div>
        <el-descriptions :column="1" border class="neo-descriptions">
          <el-descriptions-item label="申请编号">
            <span class="td-value">{{ data.request_no }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="发起人">{{ data.requester_name }}</el-descriptions-item>
          <el-descriptions-item label="发起人班次">
            <div class="desc-multi-line">
              <span class="desc-line">{{ data.requester_schedule_date }}</span>
              <span class="desc-line">{{ data.requester_shift_name }}</span>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="换班对象" v-if="data.target_name">
            <span class="td-value">{{ data.target_name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="对方班次" v-if="data.target_schedule_date">
            <div class="desc-multi-line">
              <span class="desc-line">{{ data.target_schedule_date }}</span>
              <span class="desc-line">{{ data.target_shift_name }}</span>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="认领人" v-if="data.claimer_name">
            <span class="td-value">{{ data.claimer_name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="申请原因">{{ data.reason || '<span class="text-muted">无</span>' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(data.status)" size="small" effect="dark">
              {{ statusLabel(data.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="审批人" v-if="data.approver_name">
            <span class="td-value">{{ data.approver_name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="审批时间" v-if="data.approved_at">
            <span class="td-value">{{ data.approved_at }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="审批意见" v-if="data.approve_comment">
            <span class="td-value">{{ data.approve_comment }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="申请时间">
            <span class="td-value">{{ data.created_at }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 流程状态 — Neo 风格时间线 -->
      <div class="timeline-section neo-card">
        <div class="section-title">
          <el-icon><Clock /></el-icon>
          流程状态
        </div>
        <el-timeline class="neo-timeline">
          <!-- 节点1：发起申请 -->
          <el-timeline-item
            timestamp="发起申请"
            placement="top"
            type="primary"
            :size="16"
            class="neo-timeline-item"
          >
            <span class="timeline-text">{{ data.created_at }}</span>
          </el-timeline-item>

          <!-- 节点2：等待对方确认 -->
          <el-timeline-item
            v-if="data.swap_type === 'specified'"
            :timestamp="data.swap_type === 'specified' ? '等待对方确认' : ''"
            placement="top"
            :type="data.status === 'pending_confirm' ? 'warning' : (data.status === 'target_refused' ? 'danger' : 'success')"
            :size="16"
            class="neo-timeline-item"
          >
            <template v-if="data.status === 'pending_confirm'">
              <span class="timeline-text timeline-waiting">等待对方确认中...</span>
            </template>
            <template v-else-if="data.status === 'target_refused'">
              <span class="timeline-text timeline-refused">对方已拒绝 {{ data.refused_at || '' }}</span>
              <div v-if="data.refuse_comment" class="timeline-reason">
                原因：{{ data.refuse_comment }}
              </div>
            </template>
            <template v-else>
              <span class="timeline-text">{{ data.confirmed_at || '' }}</span>
            </template>
          </el-timeline-item>

          <!-- 节点2b：等待认领 -->
          <el-timeline-item
            v-if="data.swap_type === 'open'"
            :timestamp="'等待认领'"
            placement="top"
            :type="data.status === 'pending_claim' ? 'warning' : 'success'"
            :size="16"
            class="neo-timeline-item"
          >
            <template v-if="data.status === 'pending_claim'">
              <span class="timeline-text timeline-waiting">等待他人认领中...</span>
            </template>
            <template v-else>
              <span class="timeline-text">已被认领</span>
            </template>
          </el-timeline-item>

          <!-- 节点3：等待审批 -->
          <el-timeline-item
            v-if="['pending_approve', 'approved', 'completed', 'rejected'].includes(data.status)"
            :timestamp="'等待审批'"
            placement="top"
            :type="data.status === 'pending_approve' ? 'warning' : 'success'"
            :size="16"
            class="neo-timeline-item"
          />

          <!-- 节点4a：审批通过 -->
          <el-timeline-item
            v-if="['approved', 'completed'].includes(data.status)"
            :timestamp="'审批通过'"
            placement="top"
            type="success"
            :size="16"
            class="neo-timeline-item"
          >
            <span class="timeline-text">{{ data.approved_at }}</span>
          </el-timeline-item>

          <!-- 节点4b：审批拒绝 -->
          <el-timeline-item
            v-if="data.status === 'rejected'"
            :timestamp="'审批拒绝'"
            placement="top"
            type="danger"
            :size="16"
            class="neo-timeline-item"
          >
            <span class="timeline-text timeline-rejected">{{ data.approve_comment || '无意见' }}</span>
          </el-timeline-item>

          <!-- 节点5：已完成 -->
          <el-timeline-item
            v-if="data.status === 'completed'"
            :timestamp="'已完成'"
            placement="top"
            type="success"
            :size="16"
            class="neo-timeline-item"
          />

          <!-- 已撤回 -->
          <el-timeline-item
            v-if="data.status === 'cancelled'"
            :timestamp="'已撤回'"
            placement="top"
            type="info"
            :size="16"
            class="neo-timeline-item"
          />
        </el-timeline>
      </div>
    </template>

    <el-empty v-else description="暂无数据" />
  </el-drawer>
</template>

<script setup lang="ts">
import { Clock } from '@element-plus/icons-vue'
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
/* 抽屉 — 覆盖全局 .el-drawer */
.swap-drawer :deep(.el-drawer) {
  border: 4px solid #000000 !important;
  border-radius: 0 !important;
  box-shadow: -10px 0px 0px 0px #000000 !important;
  background: #FFFDF5 !important;
}

.swap-drawer :deep(.el-drawer__header) {
  border-bottom: 3px solid #000000 !important;
  background: #FFFDF5 !important;
  padding: 18px 24px !important;
  margin-bottom: 0 !important;
}

.swap-drawer :deep(.el-drawer__title) {
  font-weight: 900 !important;
  color: #000000 !important;
  font-size: 18px !important;
  letter-spacing: 0.5px !important;
}

.swap-drawer :deep(.el-drawer__close-btn) {
  font-weight: 900 !important;
  color: #000000 !important;
}

/* 信息卡片 — 利用全局 .neo-card，仅加内边距 */
.info-section {
  margin-bottom: 20px;
}

.info-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 3px solid #000000;
  background: #FFFDF5;
}

.info-section-title {
  font-size: 14px;
  font-weight: 900;
  color: #000000;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Neo 风格 el-descriptions */
.neo-descriptions :deep(.el-descriptions__label) {
  font-weight: 700 !important;
  color: #555555 !important;
  background: #FFFDF5 !important;
  border: 2px solid #000000 !important;
  font-size: 13px !important;
}

.neo-descriptions :deep(.el-descriptions__content) {
  font-weight: 600 !important;
  color: #000000 !important;
  font-size: 13px !important;
}

.neo-descriptions :deep(.el-descriptions__cell) {
  border-bottom: 2px solid #000000 !important;
  padding: 10px 16px !important;
}

.neo-descriptions :deep(.el-descriptions__border .el-descriptions__cell) {
  border-left: 2px solid #000000 !important;
}

/* 多行描述 */
.desc-multi-line {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.desc-line {
  font-weight: 600;
  color: #000000;
}

.text-muted {
  color: #999999;
  font-style: italic;
}

.td-value {
  font-weight: 700;
  color: #000000;
}

/* 流程状态区域 */
.timeline-section {
  padding: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 900;
  color: #000000;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Neo 风格时间线 */
.neo-timeline :deep(.el-timeline) {
  padding-left: 4px !important;
}

.neo-timeline-item :deep(.el-timeline-item__timestamp) {
  font-weight: 700 !important;
  color: #000000 !important;
  font-size: 12px !important;
  background: #FFFDF5 !important;
  border: 2px solid #000000 !important;
  border-radius: 3px !important;
  padding: 3px 10px !important;
  box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.1) !important;
}

.neo-timeline-item :deep(.el-timeline-item__node) {
  border: 3px solid #000000 !important;
  box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.15) !important;
}

.neo-timeline-item :deep(.el-timeline-item__tail) {
  border-left: 3px solid #000000 !important;
}

.timeline-text {
  font-size: 13px;
  font-weight: 600;
  color: #000000;
}

.timeline-waiting {
  color: #F59E0B;
  font-weight: 700;
}

.timeline-refused {
  color: #EF4444;
  font-weight: 700;
}

.timeline-rejected {
  color: #EF4444;
  font-weight: 700;
}

.timeline-reason {
  font-size: 12px;
  color: #EF4444;
  font-weight: 600;
  margin-top: 4px;
  padding: 4px 8px;
  background: #FEE2E2;
  border: 2px solid #000000;
  border-left: 3px solid #EF4444;
  border-radius: 2px;
}

/* ============================================
   移动端适配
   ============================================ */

@media (max-width: 768px) {
  .swap-drawer :deep(.el-drawer) {
    width: 100% !important;
  }

  .info-section-header {
    padding: 10px 12px;
  }

  .timeline-section {
    padding: 14px;
  }

  .neo-timeline-item :deep(.el-timeline-item__timestamp) {
    font-size: 11px !important;
    padding: 2px 6px !important;
  }
}
</style>
