# 权限模型说明

**文档版本：** V1.0
**最后更新：** 2026-07-10
**维护者：** 开发团队

---

## 1. 模型概述

系统采用 **基于角色的访问控制（RBAC）**，支持模块级和操作级权限。权限体系分为两个维度：

| 维度 | 表 | 用途 |
|------|------|------|
| **系统角色** | `sys_role` + `sys_user_role` | 控制功能权限（菜单、API 访问） |
| **人员标识** | `sys_role` (role_type=tag) + `org_staff_role` | 控制排班身份标记（领导/带班等），不影响功能权限 |

> **关键区分：** 同一个 `sys_role` 表同时承载"系统角色"和"人员标识"两种语义，通过 `role_type` 字段区分。

---

## 2. 角色体系

### 2.1 预置系统角色

| 角色编码 | 角色名称 | role_type | 内置 | 权限范围 |
|---------|---------|-----------|------|---------|
| `admin` | 超级管理员 | role | ✅ | 全部权限（permissions={"all": true}） |
| `scheduler` | 排班管理员 | role | ✅ | 排班/配置/导入导出 |
| `leader` | 组长 | role | ✅ | 本组排班/审批/查看 |
| `member` | 普通队员 | role | ✅ | 个人排班/查看/申请调班 |

### 2.2 人员标识（Tag）

用于排班引擎的身份判断，不控制功能权限：

| 常见标识 | 用途 |
|---------|------|
| "带班领导" | 自动排班时优先分配到领导组 |
| "新入职" | 配对管理中作为新员工标记 |
| "特殊人员" | 进入特殊人员轮换池 |

---

## 3. 权限结构

### 3.1 模块×操作矩阵

由 `/api/roles/permission-schema` 返回的权限规格：

```json
{
  "modules": [
    { "key": "organization", "label": "组织管理",   "actions": ["read", "create", "update", "delete"] },
    { "key": "staff",        "label": "人员管理",   "actions": ["read", "create", "update", "delete"] },
    { "key": "shift_template","label": "班次模板",   "actions": ["read", "create", "update", "delete"] },
    { "key": "constraint",   "label": "约束规则",   "actions": ["read", "create", "update", "delete"] },
    { "key": "schedule",     "label": "排班管理",   "actions": ["read", "create", "update", "delete", "publish", "approve", "import", "export"] },
    { "key": "swap",         "label": "调班管理",   "actions": ["read", "create", "approve"] },
    { "key": "message",      "label": "消息中心",   "actions": ["read", "create", "delete"] }
  ],
  "actions": [
    { "key": "read",    "label": "查看" },
    { "key": "create",  "label": "创建" },
    { "key": "update",  "label": "编辑" },
    { "key": "delete",  "label": "删除" },
    { "key": "publish", "label": "发布" },
    { "key": "approve", "label": "审批" },
    { "key": "import",  "label": "导入" },
    { "key": "export",  "label": "导出" }
  ]
}
```

### 3.2 权限存储格式

每个角色的 `permissions` JSON 字段存储方式：

```json
{
  "organization": ["read", "create", "update", "delete"],
  "staff": ["read", "create", "update", "delete"],
  "shift_template": ["read", "create", "update", "delete"],
  "constraint": ["read", "create", "update", "delete"],
  "schedule": ["read", "create", "update", "delete", "publish", "approve", "import", "export"],
  "swap": ["read", "create", "approve"],
  "message": ["read", "create"]
}
```

> **超级管理员**使用特殊标记 `{"all": true}`，后端在合并权限时直接跳过逐模块检查。

### 3.3 权限合并逻辑

用户在 `/api/auth/me` 获取信息时，后端按以下规则合并多角色权限：

```python
# 1. 任一角色有 {"all": true} → 拥有全部权限
# 2. 否则，合并所有角色的各模块 actions 为并集
for role in user.roles:
    if role.permissions and role.permissions.get("all"):
        permissions = {"all": True}
        break
    for resource, actions in role.permissions.items():
        if resource not in permissions:
            permissions[resource] = []
        permissions[resource].extend(actions)
        permissions[resource] = list(set(permissions[resource]))  # 去重
```

---

## 4. 后端权限中间件

### 4.1 依赖注入链

```
请求进入 → deps.get_current_user → JWT 验证 → 加载用户+角色+权限
                                              ↓
                              ┌───────────────┴───────────────┐
                              │  路由是否需要额外权限校验？    │
                              └───────────────┬───────────────┘
                                        是  ↓  否
                              ┌───────────┐  └──→ 放行
                              │           │
                              │ require_roles(["admin"])
                              │   → 检查用户角色 code 是否匹配
                              │
                              │ require_permissions("schedule", "publish")
                              │   → 检查用户权限合并结果中是否包含
                              │     schedule.publish
                              │
                              └───────────┘
```

### 4.2 三种权限守卫模式

| 装饰器 | 使用场景 | 校验逻辑 | 典型路由 |
|--------|---------|---------|---------|
| `get_current_user` | 仅需登录 | 验证 JWT 有效且用户状态启用 | `/auth/me`, `/dashboard/overview` |
| `require_roles(["admin"])` | 角色精确匹配 | 用户所有角色的 code 列表中必须包含指定值 | `/roles`, `/system/config` |
| `require_permissions("module", "action")` | 模块化权限 | 用户合并权限中 module.action 存在 | `/schedules/publish` |

### 4.3 权限校验代码示例

```python
# 模块权限校验
@router.post("/publish")
async def publish_schedules(
    ...
    current_user: SysUser = Depends(require_permissions("schedule", "publish")),
):
    ...

# 角色精确匹配
@router.get("")
async def list_roles(
    ...
    current_user: SysUser = Depends(require_roles("admin")),
):
    ...
```

---

## 5. 前端权限守卫

### 5.1 路由守卫 (`router.beforeEach`)

```typescript
// frontend/src/router/index.ts

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 1. 未登录 → 跳转登录页
  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    next('/login')
    return
  }

  // 2. 强制改密 → 停留在登录页
  if (authStore.mustChangePassword && to.path !== '/login') {
    next('/login')
    return
  }

  // 3. 刷新页面 → 先加载用户信息
  if (authStore.isAuthenticated && authStore.roles.length === 0) {
    await authStore.fetchUserInfo()
    // ...
  }

  // 4. 模块权限校验
  const requiredPermission = to.meta.permission as string | undefined
  if (requiredPermission && !authStore.hasAnyPermission(requiredPermission)) {
    next('/dashboard')  // 无权限 → 跳回工作台
    return
  }

  // 5. 角色精确匹配校验
  const requiredRoles = to.meta.roles as string[] | undefined
  if (requiredRoles?.length && !requiredRoles.some(role => authStore.hasRole(role))) {
    next('/dashboard')
    return
  }

  next()
})
```

### 5.2 路由权限声明

```typescript
// 模块权限路由
{
  path: 'organizations',
  name: 'Organizations',
  component: () => import('@/views/organization/OrgView.vue'),
  meta: { title: '组织架构', icon: 'OfficeBuilding', permission: 'organization' }
}

// 角色精确匹配路由
{
  path: 'roles',
  name: 'Roles',
  component: () => import('@/views/role/RoleView.vue'),
  meta: { title: '角色权限', icon: 'Key', roles: ['admin'] }
}
```

### 5.3 Auth Store 权限方法

```typescript
// stores/auth.ts

// 检查是否有任一指定权限（模块:操作）
hasAnyPermission(permission: string): boolean {
  // 全权限标记
  if (this.permissions.all) return true
  // 解析 "module:action" 格式
  const [module, action] = permission.split(':')
  const moduleActions = this.permissions[module] || []
  return moduleActions.includes(action)
}

// 检查是否有指定角色
hasRole(role: string): boolean {
  return this.roles.includes(role)
}
```

---

## 6. 权限与路由映射速查

| 前端路由 | 组件 | meta.permission | meta.roles | 后端权限要求 |
|---------|------|-----------------|------------|-------------|
| `/login` | LoginView | — | — | 无 |
| `/dashboard` | DashboardView | — | — | 仅登录 |
| `/organizations` | OrgView | `organization` | — | organization:read |
| `/staffs` | StaffView | `staff` | — | staff:read |
| `/shift-templates` | ShiftTemplateView | `shift_template` | — | shift_template:read |
| `/constraints` | ConstraintView | `constraint` | — | constraint:read |
| `/roles` | RoleView | — | `["admin"]` | require_roles("admin") |
| `/schedule` | ScheduleCalendarView | `schedule` | — | schedule:read |
| `/swap` | SwapView | `swap` | — | swap:read |
| `/message` | MessageView | `message` | — | message:read |
| `/system` | SystemView | — | `["admin"]` | require_roles("admin") |

---

## 7. 特殊权限处理

### 7.1 轻量选项接口

部分下拉选项接口只需登录即可访问，无需模块权限：

| 路径 | 守卫 | 用途 |
|------|------|------|
| `/api/shift-templates/options` | `get_current_user` | 班次模板下拉选项 |
| `/api/staffs/options` | `get_current_user` | 人员下拉选项 |
| `/api/schedules/by-staff` | `get_current_user` | 人员排班下拉选项 |
| `/api/messages/options/*` | `get_current_user` | 组织/角色/人员选项 |

### 7.2 公开配置接口

| 路径 | 守卫 | 用途 |
|------|------|------|
| `/api/system/config/public` | 无需登录 | 系统名称、单位名称 |
| `/health` | 无需登录 | 健康检查 |

### 7.3 调班审批开关

调班审批流程受 `sys_config` 中 `swap_approval_enabled` 配置控制：

```
审批关闭: pending_confirm → completed（跳过审批）
          pending_claim → completed

审批开启: pending_confirm → pending_approve → approved → completed
                                    ↓
                                 rejected
```

### 7.4 排班审核开关

排班发布受 `sys_config` 中 `schedule_approval_enabled` 配置控制：

```
审批关闭: 发布 → 直接已发布
审批开启: 发布 → 待审核 → 管理员审批 → 已发布
```

### 7.5 自动排班防重复机制

自动排班通过 `sys_config` 中的 `auto_schedule_last_run` 配置项记录上次执行日期：

```python
# 检查今天是否已执行过
last_run_cfg = await db.execute(select(SysConfig).where(
    SysConfig.config_key == "auto_schedule_last_run"
))
if last_run_cfg and last_run_cfg.config_value == today.isoformat():
    return  # 跳过执行
```

**优势：**
- 避免因调度器重启或延迟导致重复执行
- 易于人工干预（手动删除配置项可强制重新执行）

---

## 8. 权限变更流程

当需要新增或修改权限时：

1. **新增模块/操作** → 更新 `/api/roles/permission-schema` 返回的规格表
2. **修改预置角色权限** → 更新数据库中对应 `sys_role.permissions` JSON
3. **新增自定义角色** → 通过 `/api/roles` API 创建，前端权限矩阵动态渲染
4. **前端路由权限** → 在路由 `meta` 中声明 `permission` 或 `roles`
