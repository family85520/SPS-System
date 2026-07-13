# API 端点速查表

**文档版本：** V1.0
**最后更新：** 2026-07-10
**维护者：** 开发团队

> **自动生成文档：** FastAPI 提供交互式 Swagger UI (`/docs`) 和 ReDoc (`/redoc`)，本表作为快速索引使用。

---

## 1. 端点总览

| 模块 | 前缀 | 端点数 | 认证要求 |
|------|------|--------|---------|
| 认证管理 | `/api/auth` | 4 | 登录无需认证，其余需 Bearer Token |
| 组织架构 | `/api/organizations` | 5 | `organization:read/create/update/delete` |
| 人员管理 | `/api/staffs` | 13 | `staff:read/create/update/delete` |
| 班次模板 | `/api/shift-templates` | 12 | `shift_template:read/create/update/delete` |
| 约束规则 | `/api/constraints` | 7 | `constraint:read/create/update/delete` |
| 特殊规则 | `/api/special-rules` | 5 | `staff:read/update` |
| 角色权限 | `/api/roles` | 13 | 管理员专用（`require_roles("admin")`）|
| 系统配置 | `/api/system` | 4 | `require_roles("admin")` |
| 排班管理 | `/api/schedules` | 20 | `schedule:read/create/update/publish/approve/import/export` |
| 调班管理 | `/api/swaps` | 9 | `swap:read/create/approve` |
| 消息中心 | `/api/messages` / `/api/announcements` | 11 | `message:read/create/delete` |
| 首页看板 | `/api/dashboard` | 1 | 仅需登录 |
| 数据导出 | `/api/export` | 8 | `schedule:export` |

---

## 2. 认证管理

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| POST | `/api/auth/login` | 无 | 用户登录，返回 JWT Token |
| GET | `/api/auth/me` | 无（需登录） | 获取当前用户信息（含角色+权限） |
| POST | `/api/auth/change-password` | 无（需登录） | 修改密码（需提供旧密码） |
| POST | `/api/auth/force-change-password` | 无（需登录） | 首次强制修改密码 |

---

## 3. 组织架构

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/organizations/tree` | `organization:read` | 获取组织树（支持 include_disabled 参数） |
| GET | `/api/organizations` | `organization:read` | 获取组织列表（支持 parent_id 筛选） |
| POST | `/api/organizations` | `organization:create` | 创建组织（自动计算层级，最多 4 级） |
| PUT | `/api/organizations/{org_id}` | `organization:update` | 更新组织信息 |
| DELETE | `/api/organizations/{org_id}` | `organization:delete` | 删除组织（无子组织、无人员、无排班时可删） |

---

## 4. 人员管理

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/staffs` | `staff:read` | 获取人员列表（支持 org_id/status/keyword 筛选） |
| GET | `/api/staffs/options` | 仅登录 | 获取在岗人员选项（下拉用） |
| GET | `/api/staffs/{staff_id}` | `staff:read` | 获取人员详情 |
| POST | `/api/staffs` | `staff:create` | 创建人员（自动创建账号，用户名=工号） |
| PUT | `/api/staffs/{staff_id}` | `staff:update` | 更新人员信息 |
| PUT | `/api/staffs/{staff_id}/account` | `staff:update` | 管理人员关联的登录账号 |
| PUT | `/api/staffs/{staff_id}/sync-roles` | `staff:update` | 同步标签到系统角色 |
| POST | `/api/staffs/{staff_id}/account` | `staff:update` | 为已有人员创建账号 |
| POST | `/api/staffs/reset-password-by-user/{user_id}` | 仅 admin | 通过用户 ID 重置密码 |
| POST | `/api/staffs/reset-passwords` | `staff:update` | 批量重置密码为默认密码 |
| POST | `/api/staffs/migrate-accounts` | `staff:create` | 为历史人员批量创建账号 |
| GET | `/api/staffs/system-accounts` | 仅 admin | 获取系统账号列表 |
| GET | `/api/staffs/next-employee-no` | `staff:read` | 获取下一个工号 |
| DELETE | `/api/staffs/{staff_id}` | `staff:delete` | 删除人员（级联清理所有外键引用） |

---

## 5. 班次模板

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/shift-templates` | `shift_template:read` | 获取班次模板列表 |
| GET | `/api/shift-templates/options` | 仅登录 | 获取启用状态的班次选项（下拉用） |
| GET | `/api/shift-templates/{template_id}` | `shift_template:read` | 获取单个模板详情 |
| POST | `/api/shift-templates` | `shift_template:create` | 创建班次模板 |
| PUT | `/api/shift-templates/{template_id}` | `shift_template:update` | 更新班次模板 |
| DELETE | `/api/shift-templates/{template_id}` | `shift_template:delete` | 删除班次模板 |
| POST | `/api/shift-templates/{template_id}/copy` | `shift_template:create` | 复制班次模板 |
| PUT | `/api/shift-templates/{template_id}/status` | `shift_template:update` | 启用/停用班次模板 |
| GET | `/api/shift-templates/{template_id}/duty-teams` | `shift_template:read` | 获取值班组列表 |
| POST | `/api/shift-templates/{template_id}/duty-teams` | `shift_template:update` | 创建值班组 |
| PUT | `/api/shift-templates/{template_id}/duty-teams/{team_id}` | `shift_template:update` | 更新值班组 |
| DELETE | `/api/shift-templates/{template_id}/duty-teams/{team_id}` | `shift_template:delete` | 删除值班组 |

---

## 6. 约束规则

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/constraints` | `constraint:read` | 获取约束规则列表 |
| GET | `/api/constraints/{constraint_id}` | `constraint:read` | 获取单个规则详情 |
| POST | `/api/constraints` | `constraint:create` | 创建约束规则 |
| PUT | `/api/constraints/{constraint_id}` | `constraint:update` | 更新约束规则 |
| DELETE | `/api/constraints/{constraint_id}` | `constraint:delete` | 删除约束规则 |
| PUT | `/api/constraints/{constraint_id}/toggle` | `constraint:update` | 启用/禁用规则 |
| PUT | `/api/constraints/batch/priority` | `constraint:update` | 批量更新优先级 |

---

## 7. 特殊排班规则

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/special-rules` | `staff:read` | 获取特殊规则列表（支持 staff_id 筛选） |
| GET | `/api/special-rules/{rule_id}` | `staff:read` | 获取单个特殊规则详情 |
| POST | `/api/special-rules` | `staff:update` | 创建特殊规则（含冲突校验） |
| PUT | `/api/special-rules/{rule_id}` | `staff:update` | 更新特殊规则 |
| DELETE | `/api/special-rules/{rule_id}` | `staff:update` | 删除特殊规则 |

---

## 8. 角色权限

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/roles/permission-schema` | 仅 admin | 获取权限规格表（前端动态渲染权限矩阵） |
| GET | `/api/roles/options` | 仅登录 | 获取角色选项列表（支持 type 筛选） |
| GET | `/api/roles` | 仅 admin | 获取角色列表 |
| GET | `/api/roles/{role_id}` | 仅 admin | 获取角色详情 |
| POST | `/api/roles` | 仅 admin | 创建自定义角色 |
| PUT | `/api/roles/{role_id}` | 仅 admin | 更新角色（名称+权限） |
| DELETE | `/api/roles/{role_id}` | 仅 admin | 删除自定义角色 |
| GET | `/api/roles/user/{user_id}` | 仅 admin | 获取用户的角色列表 |
| POST | `/api/roles/user/{user_id}` | 仅 admin | 为用户分配角色 |
| GET | `/api/roles/staff/{staff_id}/tags` | `staff:read` | 获取人员的标识列表 |
| POST | `/api/roles/staff/{staff_id}/tags` | 仅 admin | 为人员分配标识（全量替换） |
| DELETE | `/api/roles/staff/{staff_id}/tags/{role_id}` | 仅 admin | 移除人员的单个标识 |

---

## 9. 系统配置

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/system/config/public` | 无需登录 | 获取公开系统配置 |
| GET | `/api/system/config/overview` | 仅登录 | 获取系统概要配置 |
| GET | `/api/system/config` | 仅 admin | 获取所有系统配置 |
| PUT | `/api/system/config` | 仅 admin | 更新系统配置（批量） |

---

## 10. 排班管理

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/schedules` | `schedule:read` | 获取排班列表（分页+多条件筛选） |
| GET | `/api/schedules/calendar` | `schedule:read` | 获取排班日历数据 |
| GET | `/api/schedules/by-staff` | 仅登录 | 获取指定人员的排班列表（下拉用） |
| GET | `/api/schedules/statistics` | `schedule:read` | 排班工作量统计 |
| GET | `/api/schedules/import-template` | `schedule:create` | 下载标准排班导入模板 |
| POST | `/api/schedules/import` | `schedule:import` | 导入标准排班模板（.xlsx） |
| GET | `/api/schedules/{schedule_id}` | `schedule:read` | 获取排班详情 |
| POST | `/api/schedules` | `schedule:create` | 创建排班 |
| PUT | `/api/schedules/{schedule_id}` | `schedule:update` | 更新排班 |
| DELETE | `/api/schedules/{schedule_id}` | `schedule:delete` | 删除排班 |
| POST | `/api/schedules/{schedule_id}/assign-staff` | `schedule:update` | 分配人员 |
| POST | `/api/schedules/{schedule_id}/remove-staff` | `schedule:update` | 移除人员 |
| POST | `/api/schedules/{schedule_id}/swap-staff/{other_id}` | `schedule:update` | 互换两个班次人员 |
| POST | `/api/schedules/batch` | `schedule:create` | 批量创建/更新排班明细 |
| POST | `/api/schedules/publish` | `schedule:publish` | 发布排班 |
| POST | `/api/schedules/approve` | `schedule:approve` | 审核通过排班 |
| POST | `/api/schedules/reject` | `schedule:approve` | 审核拒绝排班 |
| POST | `/api/schedules/recall` | `schedule:publish` | 撤回排班（按 ID） |
| POST | `/api/schedules/recall-month` | `schedule:publish` | 按月撤回排班 |
| POST | `/api/schedules/delete-drafts` | `schedule:delete` | 一键删除草稿排班 |
| GET | `/api/schedules/staff-summary/{staff_id}` | `schedule:read` | 人员排班统计 |
| POST | `/api/schedules/auto-generate` | `schedule:create` | 自动排班生成 |
| POST | `/api/schedules/validate` | `schedule:create` | 全局约束校验 |
| POST | `/api/schedules/validate-single` | `schedule:read` | 单条排班实时校验 |

---

## 11. 调班管理

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/swaps` | `swap:read` | 获取调班申请列表（支持 role/status/swap_type 筛选） |
| GET | `/api/swaps/all` | `swap:read` | 获取全部调班记录（管理员） |
| GET | `/api/swaps/{request_id}` | `swap:read` | 获取调班申请详情 |
| POST | `/api/swaps` | `swap:create` | 发起调班申请 |
| PUT | `/api/swaps/{request_id}/confirm` | `swap:create` | 对方确认换班 |
| PUT | `/api/swaps/{request_id}/claim` | `swap:create` | 认领开放换班 |
| PUT | `/api/swaps/{request_id}/approve` | `swap:approve` | 审批通过 |
| PUT | `/api/swaps/{request_id}/reject` | `swap:approve` | 审批拒绝 |
| PUT | `/api/swaps/{request_id}/refuse` | `swap:create` | 对方拒绝换班 |
| PUT | `/api/swaps/{request_id}/cancel` | `swap:create` | 撤回申请 |

---

## 12. 消息中心

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/messages` | `message:read` | 获取消息列表（分页+类型筛选） |
| GET | `/api/messages/unread-count` | `message:read` | 获取未读消息数量 |
| PUT | `/api/messages/{message_id}/read` | `message:read` | 标记单条消息为已读 |
| PUT | `/api/messages/read-all` | `message:read` | 全部标记已读 |
| POST | `/api/messages/broadcast` | `message:create` | 广播消息（管理员） |
| GET | `/api/announcements` | `message:read` | 获取公告列表 |
| POST | `/api/announcements` | `message:create` | 发布公告 |
| PUT | `/api/announcements/{ann_id}` | `message:create` | 编辑公告 |
| POST | `/api/announcements/{ann_id}/withdraw` | `message:delete` | 撤回公告 |
| DELETE | `/api/announcements/{ann_id}` | `message:delete` | 永久隐藏公告 |
| GET | `/api/options/organizations` | 仅登录 | 获取组织选项列表 |
| GET | `/api/options/roles` | 仅登录 | 获取角色选项列表 |
| GET | `/api/options/staffs` | 仅登录 | 搜索人员选项列表 |

---

## 13. 首页看板

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/dashboard/overview` | 仅登录 | 获取首页看板数据（按角色差异化返回） |

---

## 14. 数据导出

| 方法 | 路径 | 权限标识 | 说明 |
|------|------|---------|------|
| GET | `/api/export/schedule/excel` | `schedule:export` | 导出排班表 Excel |
| GET | `/api/export/statistics/excel` | `schedule:export` | 导出统计报表 Excel |
| GET | `/api/export/templates/variables` | 仅登录 | 获取可用的模板变量列表 |
| GET | `/api/export/templates/default/download` | 仅登录 | 下载默认模板文件 |
| GET | `/api/export/templates` | 仅登录 | 获取导出模板列表 |
| POST | `/api/export/templates/upload` | `schedule:update` | 上传自定义导出模板 (.xlsx) |
| DELETE | `/api/export/templates/{template_id}` | `schedule:delete` | 删除导出模板 |
| POST | `/api/export/templates/{template_id}/set-default` | `schedule:update` | 设为默认模板 |

---

## 15. 公共端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 应用信息（名称、版本、状态） |
| GET | `/health` | 健康检查 |
| GET | `/docs` | Swagger UI（交互式 API 文档） |
| GET | `/redoc` | ReDoc（静态 API 文档） |

---

## 16. 错误响应格式

所有 API 统一遵循以下错误响应格式：

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码：

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 / 业务规则校验失败 |
| 401 | 未授权（Token 无效/过期） |
| 403 | 无权访问（权限不足） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
