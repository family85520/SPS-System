/**
 * useConfirm — 统一确认弹窗 composable
 *
 * 用法：
 *   const confirm = useConfirm()
 *   await confirm({ type: 'danger', title: '确认删除', message: '...' })
 *   // 返回 true（用户点击确认）或抛出 Error（用户取消）
 */

import { inject } from 'vue'

export type ConfirmType = 'danger' | 'warning' | 'info' | 'success'

interface ConfirmOptions {
  type?: ConfirmType
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
}

interface ConfirmInstance {
  showDialog: (config: Partial<ConfirmOptions>) => Promise<boolean>
  hideDialog: () => void
}

export type { ConfirmInstance }

const CONFIRM_KEY = 'useConfirm' as never

export function useConfirm() {
  // 通过 inject 获取 App.vue 中注册的 ConfirmDialog 实例
  const dialog = inject<ConfirmInstance>(CONFIRM_KEY, null)

  if (!dialog) {
    throw new Error('[useConfirm] ConfirmDialog not found. Make sure it\'s registered in App.vue.')
  }

  const { showDialog, hideDialog } = dialog

  async function confirm(options: ConfirmOptions): Promise<boolean> {
    return showDialog(options).finally(hideDialog)
  }

  async function confirmDanger(message: string, title?: string): Promise<boolean> {
    return confirm({ type: 'danger', title, message })
  }

  async function confirmWarning(message: string, title?: string): Promise<boolean> {
    return confirm({ type: 'warning', title, message })
  }

  async function confirmInfo(message: string, title?: string): Promise<boolean> {
    return confirm({ type: 'info', title, message })
  }

  async function confirmSuccess(message: string, title?: string): Promise<boolean> {
    return confirm({ type: 'success', title, message })
  }

  return { confirm, confirmDanger, confirmWarning, confirmInfo, confirmSuccess }
}
