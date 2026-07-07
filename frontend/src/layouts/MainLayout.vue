<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '72px' : '240px'" class="aside">
      <div class="aside-inner">
        <!-- Logo -->
        <div class="logo" @click="router.push('/dashboard')">
          <i class="fas fa-calendar-alt logo-icon"></i>
          <span v-show="!isCollapse" class="logo-title">{{ systemStore.systemName }}</span>
          <span v-show="isCollapse" class="logo-title-short">{{ (systemStore.systemName || 'SPS').slice(0, 2) }}</span>
        </div>

        <!-- 菜单 -->
        <nav class="menu">
          <template v-for="route in menuRoutes" :key="route.path">
            <a
              v-if="hasRoutePermission(route) && !route.meta?.hidden"
              :class="['menu-item', { active: '/' + route.path === currentRoute }]"
              :href="'/' + route.path"
              :title="String(route.meta?.title ?? '')"
            >
              <el-icon><component :is="route.meta?.icon" /></el-icon>
              <span v-show="!isCollapse">{{ route.meta?.title }}</span>
            </a>
          </template>
        </nav>

        <!-- 用户信息（折叠时只显示头像） -->
        <div class="aside-footer">
          <div class="user-avatar" :title="authStore.staffName || authStore.username">
            {{ (authStore.staffName || authStore.username || '?').charAt(0) }}
          </div>
          <div v-show="!isCollapse" class="user-info">
            <span class="user-name">{{ authStore.staffName || authStore.username }}</span>
          </div>
        </div>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" /><Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentTitle">{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- 消息角标 -->
          <el-badge
            v-if="authStore.hasPermission('message', 'read')"
            :value="messageStore.unreadCount"
            :hidden="messageStore.unreadCount === 0"
            :max="99"
            class="msg-badge"
          >
            <el-icon class="msg-icon" @click="router.push('/message')"><Bell /></el-icon>
          </el-badge>
          <!-- 用户下拉 -->
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-dropdown-trigger">
              <span class="username">{{ authStore.staffName || authStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Bell, Fold, Expand, ArrowDown } from '@element-plus/icons-vue'
import router from '@/router'
import { useSystemStore } from '@/stores/system'
import { useMessageStore } from '@/stores/message'
import { useConfirm } from '@/composables/useConfirm'

const route = useRoute()
const authStore = useAuthStore()
const isCollapse = ref(false)
const systemStore = useSystemStore()
const messageStore = useMessageStore()
const { confirmWarning } = useConfirm()

const currentRoute = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title as string || '')

const menuRoutes = computed(() => {
  const mainRoute = router.options.routes.find(r => r.path === '/')
  return mainRoute?.children || []
})

function hasRoutePermission(routeItem: any): boolean {
  const meta = routeItem.meta
  if (!meta) return true
  if (meta.permission) {
    return authStore.hasAnyPermission(meta.permission)
  }
  const roles = meta.roles
  if (!roles || roles.length === 0) return true
  return roles.some((role: string) => authStore.hasRole(role))
}

onMounted(() => {
  if (authStore.hasPermission('message', 'read')) {
    messageStore.startPolling(30000)
  }
})

onUnmounted(() => {
  messageStore.stopPolling()
})

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    confirmWarning('确定要退出登录吗？', '提示')
      .then(() => { authStore.logout() })
      .catch(() => {})
  }
}
</script>

<style lang="scss" scoped>
/* ===== 整体容器 ===== */
.layout-container {
  height: 100vh;
  display: flex;
}

/* ===== 侧边栏 ===== */
.aside {
  background: #FFFFFF;
  border-right: 3px solid #000000;
  transition: width 0.2s ease;
  overflow: hidden;
  z-index: 100;
  flex-shrink: 0;
}

.aside-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* Logo */
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-bottom: 3px solid #000000;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
  padding: 0 12px;
}
.logo:hover {
  background: #FFFDF5;
}
.logo-icon {
  font-size: 22px;
  color: #3B82F6;
  flex-shrink: 0;
}
.logo-title {
  font-size: 16px;
  font-weight: 900;
  color: #000000;
  white-space: nowrap;
  letter-spacing: 0.5px;
}
.logo-title-short {
  font-size: 14px;
  font-weight: 900;
  color: #000000;
}

/* 菜单 */
.menu {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 3px solid #000000;
  border-radius: 4px;
  font-weight: 700;
  font-size: 14px;
  color: #000000;
  text-decoration: none;
  transition: all 0.1s ease;
  cursor: pointer;
  white-space: nowrap;
  background: #FFFFFF;
  box-shadow: 3px 3px 0px 0px #000000;
}
.menu-item:hover:not(.active) {
  background: #FFFDF5;
  box-shadow: 4px 4px 0px 0px #000000;
  transform: translate(-1px, -1px);
}
.menu-item.active {
  background: #3B82F6 !important;
  color: #FFFFFF !important;
  box-shadow: 4px 4px 0px 0px #000000;
}
.menu-item .el-icon {
  font-size: 18px;
  flex-shrink: 0;
}

/* 侧边栏底部用户区 */
.aside-footer {
  border-top: 3px solid #000000;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 3px solid #000000;
  background: #FFD93D;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 16px;
  color: #000000;
  flex-shrink: 0;
}
.user-info {
  overflow: hidden;
}
.user-name {
  font-size: 13px;
  font-weight: 700;
  color: #000000;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== 主内容区 ===== */
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 顶栏 */
.header {
  height: 64px;
  background: #FFFFFF;
  border-bottom: 3px solid #000000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  z-index: 50;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.collapse-btn {
  font-size: 22px;
  cursor: pointer;
  color: #000000;
  transition: color 0.15s;
  user-select: none;
}
.collapse-btn:hover {
  color: #3B82F6;
}
.breadcrumb {
  font-weight: 600;
}
.breadcrumb :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #3B82F6;
  font-weight: 700;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.msg-badge :deep(.el-badge__content) {
  font-weight: 900;
  font-size: 11px;
}
.msg-icon {
  font-size: 22px;
  cursor: pointer;
  color: #000000;
  transition: color 0.15s;
}
.msg-icon:hover {
  color: #3B82F6;
}
.user-dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 700;
  color: #000000;
  padding: 6px 12px;
  border: 3px solid transparent;
  border-radius: 4px;
  transition: all 0.1s;
}
.user-dropdown-trigger:hover {
  border-color: #000000;
  background: #FFFDF5;
  box-shadow: 2px 2px 0px 0px #000000;
}
.username {
  font-size: 14px;
}

/* 主内容 */
.main-content {
  flex: 1;
  background: #FFFDF5;
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 页面切换动画 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.15s ease;
}
.page-fade-enter-from {
  opacity: 0;
}
.page-fade-leave-to {
  opacity: 0;
}
</style>
