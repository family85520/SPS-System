import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '工作台', icon: 'Odometer' }
      },
      {
        path: 'organizations',
        name: 'Organizations',
        component: () => import('@/views/organization/OrgView.vue'),
        meta: { title: '组织架构', icon: 'OfficeBuilding', roles: ['admin'] },
      },
      {
        path: 'staffs',
        name: 'Staffs',
        component: () => import('@/views/staff/StaffView.vue'),
        meta: { title: '人员管理', icon: 'User', roles: ['admin', 'scheduler'] },
      },
      {
        path: 'shift-templates',
        name: 'ShiftTemplates',
        component: () => import('@/views/shift-template/ShiftTemplateView.vue'),
        meta: { title: '班次模板', icon: 'Clock', roles: ['admin', 'scheduler'] },
      },
      {
        path: 'constraints',
        name: 'Constraints',
        component: () => import('@/views/constraint/ConstraintView.vue'),
        meta: { title: '排班规则', icon: 'Setting', roles: ['admin', 'scheduler'] },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/user/UserView.vue'),
        meta: { title: '用户管理', icon: 'UserFilled', roles: ['admin'] },
      },
      {
        path: 'roles',
        name: 'Roles',
        component: () => import('@/views/role/RoleView.vue'),
        meta: { title: '角色权限', icon: 'Key', roles: ['admin'] },
      },
      {
        path: 'schedule',
        name: 'Schedule',
        component: () => import('@/views/schedule/ScheduleCalendarView.vue'),
        meta: { title: '排班管理', icon: 'Calendar', roles: ['admin', 'scheduler'] },
      },
      {
        path: 'schedule/auto',
        name: 'AutoSchedule',
        component: () => import('@/views/placeholder/PlaceholderView.vue'),
        meta: { title: '自动排班', icon: 'MagicStick', roles: ['admin', 'scheduler'] },
      },
      {
        path: 'swap',
        name: 'Swap',
        component: () => import('@/views/swap/SwapView.vue'),
        meta: { title: '调班管理', icon: 'Switch' },
      },
      {
        path: 'message',
        name: 'Message',
        component: () => import('@/views/message/MessageView.vue'),
        meta: { title: '消息中心', icon: 'Bell' }
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/system/SystemView.vue'),
        meta: { title: '系统配置', icon: 'Tools', roles: ['admin'] },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const { useSystemStore } = await import('@/stores/system')
  const systemStore = useSystemStore()

  // 未登录跳登录页
  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    next('/login')
    return
  }

  // 已登录但需要强制改密，必须停留在登录页
  if (authStore.isAuthenticated && authStore.mustChangePassword) {
    if (to.path !== '/login') {
      next('/login')
      return
    }
    next()
    return
  }

  // 已登录但用户信息未加载（刷新页面场景），先加载用户信息
  if (authStore.isAuthenticated && authStore.roles.length === 0) {
    try {
      await authStore.fetchUserInfo()
      await systemStore.fetchConfig()
    } catch (e) {
      authStore.logout()
      next('/login')
      return
    }
    // fetchUserInfo 内部若发现 must_change_password 会自动 logout
    if (!authStore.isAuthenticated) {
      next('/login')
      return
    }
  }

  // 已登录去登录页，跳工作台
  if (to.path === '/login' && authStore.isAuthenticated) {
    next('/dashboard')
    return
  }

  next()
})

export default router
