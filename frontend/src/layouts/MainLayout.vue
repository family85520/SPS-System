<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <span v-show="!isCollapse" class="title">{{ systemStore.systemName }}</span>
        <span v-show="isCollapse" class="title">{{ systemStore.systemName.slice(0, 2) }}</span>
      </div>
      <el-menu :default-active="currentRoute" :collapse="isCollapse" router background-color="#304156" text-color="#bfcbd9" active-text-color="#409eff">
        <template v-for="route in menuRoutes" :key="route.path">
          <el-menu-item v-if="hasRoutePermission(route) && !route.meta?.hidden" :index="'/' + route.path">
            <el-icon><component :is="route.meta?.icon" /></el-icon>
            <template #title>{{ route.meta?.title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" /><Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentTitle">{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- ★ 新增：消息角标 -->
          <el-badge :value="messageStore.unreadCount" :hidden="messageStore.unreadCount === 0" :max="99" class="msg-badge">
            <el-icon class="msg-icon" @click="router.push('/message')"><Bell /></el-icon>
          </el-badge>
          <el-dropdown trigger="click">
            <div class="user-info">
              <span class="username">{{ authStore.staffName || authStore.username }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'
import { Bell, Fold, Expand } from '@element-plus/icons-vue'
import router from '@/router'
import { useSystemStore } from '@/stores/system'
import { useMessageStore } from '@/stores/message'

const route = useRoute()
const authStore = useAuthStore()
const isCollapse = ref(false)
const systemStore = useSystemStore()

// ★ 未读消息计数（全局 Store，任何页面标记已读后自动同步）
const messageStore = useMessageStore()

onMounted(() => {
  if (authStore.hasPermission('message', 'read')) {
    messageStore.startPolling(30000)
  }
})

onUnmounted(() => {
  messageStore.stopPolling()
})

const menuRoutes = computed(() => {
  const mainRoute = router.options.routes.find(r => r.path === '/')
  return mainRoute?.children || []
})

const currentRoute = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title as string || '')

function hasRoutePermission(routeItem: any): boolean {
  const meta = routeItem.meta
  if (!meta) return true

  // 优先检查动态权限（来自角色权限矩阵）
  if (meta.permission) {
    return authStore.hasAnyPermission(meta.permission)
  }

  // 其次检查硬编码角色（仅用于无法用权限矩阵控制的场景，如系统配置）
  const roles = meta.roles
  if (!roles || roles.length === 0) return true
  return roles.some((role: string) => authStore.hasRole(role))
}

function handleLogout() {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => { authStore.logout() }).catch(() => {})
}
</script>

<style lang="scss" scoped>
.layout-container { height: 100vh; }
.aside { background-color: #304156; transition: width 0.3s; overflow: hidden; }
.logo { height: 60px; display: flex; align-items: center; justify-content: center; color: #fff; .title { font-size: 16px; font-weight: 600; white-space: nowrap; } }
.header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e6e6e6; background: #fff; }
.header-left { display: flex; align-items: center; gap: 16px; }
.collapse-btn { font-size: 20px; cursor: pointer; color: #666; &:hover { color: #409eff; } }
.header-right { display: flex; align-items: center; gap: 20px; }
.user-info { display: flex; align-items: center; gap: 8px; cursor: pointer; .username { font-size: 14px; color: #333; } }
.main { background: #f5f7fa; padding: 20px; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ★ 新增：消息图标样式 */
.msg-icon {
  font-size: 20px;
  cursor: pointer;
  color: #666;
  &:hover { color: #409eff; }
}
.msg-badge {
  :deep(.el-badge__content) {
    font-size: 11px;
  }
}
</style>
