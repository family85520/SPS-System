<template>
  <!-- ====== 通用确认弹窗 ====== -->
  <teleport to="body">
    <transition name="modal-fade">
      <div v-if="state.visible" class="confirm-overlay" @click.self="handleCancel">
        <transition name="modal-slide">
          <div v-if="state.visible" class="confirm-dialog" :class="`confirm-dialog--${state.type}`">
            <!-- 图标 -->
            <div class="confirm-icon-wrap" :class="`confirm-icon--${state.type}`">
              <i class="confirm-icon-text">{{ iconMap[state.type] }}</i>
            </div>

            <!-- 标题 -->
            <h3 class="confirm-title">{{ state.title }}</h3>

            <!-- 消息 -->
            <p class="confirm-message">{{ state.message }}</p>

            <!-- 按钮 -->
            <div class="confirm-actions">
              <button class="btn-neo-ghost flex-1" @click="handleCancel">
                {{ state.cancelText }}
              </button>
              <button
                class="flex-1 confirm-btn-confirm"
                :class="`confirm-btn--${state.type}`"
                @click="handleConfirm"
                :disabled="loading"
              >
                {{ state.confirmText }}
              </button>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { ConfirmType } from '@/composables/useConfirm'

interface ConfirmState {
  visible: boolean
  type: ConfirmType
  title: string
  message: string
  confirmText: string
  cancelText: string
}

const state = ref<ConfirmState>({
  visible: false,
  type: 'danger',
  title: '确认操作',
  message: '',
  confirmText: '确认',
  cancelText: '取消',
})

const loading = ref(false)
let resolveFn: ((value: boolean) => void) | null = null
let rejectFn: ((reason?: unknown) => void) | null = null

const iconMap: Record<ConfirmType, string> = {
  danger: '✕',
  warning: '⚠',
  info: 'ℹ',
  success: '✓',
}

function handleConfirm() {
  loading.value = true
  resolveFn?.(true)
}

function handleCancel() {
  loading.value = false
  rejectFn?.(new Error('Cancelled'))
}

function showDialog(config: Partial<Omit<ConfirmState, 'visible'>>) {
  // 如果有未完成的 promise，先 reject 掉（防止竞态）
  if (resolveFn) {
    resolveFn(false)
  }

  state.value = {
    visible: true,
    type: config.type ?? 'danger',
    title: config.title ?? '确认操作',
    message: config.message ?? '',
    confirmText: config.confirmText ?? '确认',
    cancelText: config.cancelText ?? '取消',
  }
  loading.value = false

  return new Promise<boolean>((resolve, reject) => {
    resolveFn = () => {
      state.value.visible = false
      resolve(true)
    }
    rejectFn = () => {
      state.value.visible = false
      reject(new Error('Cancelled'))
    }
  })
}

function hideDialog() {
  state.value.visible = false
  loading.value = false
  resolveFn = null
  rejectFn = null
}

// 暴露给 composable 使用
defineExpose({ showDialog, hideDialog })
</script>

<style scoped>
/* --- 遮罩层 --- */
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* --- 弹窗主体 --- */
.confirm-dialog {
  background: var(--neo-color-bg-card);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-lg);
  max-width: 480px;
  width: 90%;
  padding: 28px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
}

/* --- 图标 --- */
.confirm-icon-wrap {
  width: 80px;
  height: 80px;
  border: var(--neo-border-ultra) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-default);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.confirm-icon-text {
  font-size: 42px;
  font-weight: 900;
  line-height: 1;
  color: var(--neo-color-bg-card);
}
.confirm-icon--danger { background: var(--neo-color-accent-red); }
.confirm-icon--warning { background: var(--neo-color-accent-yellow); }
.confirm-icon--info    { background: var(--neo-color-accent-blue); }
.confirm-icon--success { background: var(--neo-color-accent-green); }

/* --- 标题 --- */
.confirm-title {
  margin: 0;
  font-size: 24px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
}

/* --- 消息 --- */
.confirm-message {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--neo-color-text-secondary);
  line-height: 1.6;
  max-width: 380px;
}

/* --- 按钮 --- */
.confirm-actions {
  display: flex;
  gap: 12px;
  width: 100%;
  padding-top: 8px;
  border-top: var(--neo-border-ultra) solid var(--neo-color-border);
}

.confirm-btn-confirm {
  border-color: var(--neo-color-border) !important;
}

/* 危险按钮 — 红色 */
.confirm-btn--danger {
  background: var(--neo-color-accent-red) !important;
  color: var(--neo-color-bg-card) !important;
}
.confirm-btn--danger:hover:not(:disabled) {
  background: var(--neo-color-accent-red-hover) !important;
}
.confirm-btn--danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 警告按钮 — 黄色 */
.confirm-btn--warning {
  background: var(--neo-color-accent-yellow) !important;
  color: var(--neo-color-text-primary) !important;
}
.confirm-btn--warning:hover:not(:disabled) {
  background: var(--neo-color-accent-yellow-hover) !important;
}
.confirm-btn--warning:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 信息按钮 — 蓝色 */
.confirm-btn--info {
  background: var(--neo-color-accent-blue) !important;
  color: var(--neo-color-bg-card) !important;
}
.confirm-btn--info:hover:not(:disabled) {
  background: var(--neo-color-accent-blue-hover) !important;
}
.confirm-btn--info:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 成功按钮 — 绿色 */
.confirm-btn--success {
  background: var(--neo-color-accent-green) !important;
  color: var(--neo-color-bg-card) !important;
}
.confirm-btn--success:hover:not(:disabled) {
  background: var(--neo-color-accent-green-hover) !important;
}
.confirm-btn--success:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* --- 动画 --- */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-slide-enter-active {
  transition: transform 0.2s ease;
}
.modal-slide-enter-from,
.modal-slide-leave-to {
  transform: translateY(20px) scale(0.95);
  opacity: 0;
}

/* --- 响应式 --- */
@media (max-width: 768px) {
  .confirm-dialog {
    width: 95%;
    padding: 20px;
  }
  .confirm-icon-wrap {
    width: 64px;
    height: 64px;
  }
  .confirm-icon-text {
    font-size: 32px;
  }
  .confirm-title {
    font-size: 20px;
  }
  .confirm-message {
    font-size: 14px;
  }
}
</style>
