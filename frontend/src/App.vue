<template>
  <router-view />
  <ConfirmDialog ref="confirmDialogRef" />
</template>

<script setup lang="ts">
import { provide, ref } from 'vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import type { ConfirmInstance } from '@/composables/useConfirm'

const confirmDialogRef = ref<InstanceType<typeof ConfirmDialog>>(null!)

// 通过 provide 注入 confirm 方法给所有子组件
provide('useConfirm', {
  get showDialog() { return confirmDialogRef.value?.showDialog },
  get hideDialog() { return confirmDialogRef.value?.hideDialog },
})
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
</style>
