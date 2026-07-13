# 测试计划

**文档版本：** V1.0
**最后更新：** 2026-07-10
**维护者：** 开发团队

---

## 1. 测试范围

| 模块 | 测试类型 | 覆盖内容 |
|------|---------|---------|
| 登录认证 | 功能 + 安全 | 登录/登出、Token 过期、密码修改、强制改密 |
| 组织架构 | CRUD + 边界 | 树形结构、层级限制（4级）、停用/删除约束 |
| 人员管理 | CRUD + 账号 | 创建/更新/删除、账号关联、批量操作、密码重置 |
| 班次模板 | CRUD + 业务规则 | 跨夜班时长计算、启用/停用、值班组管理 |
| 约束规则 | CRUD + 预置规则 | 预置规则不可删除、优先级排序、开关控制 |
| 特殊规则 | CRUD + 冲突校验 | 6种规则类型、有效期、互斥校验 |
| 排班管理 | 日历 + 自动 + 手动 | 日历视图、拖拽、约束校验、发布/撤回 |
| 自动排班 | 算法 + 公平性 | 生成结果合规性、跨月配对、耗时 |
| 调班管理 | 状态机 + 审批 | 指定换班/开放换班、冲突检测、审批流程 |
| 消息中心 | 推送 + 已读 | 消息列表、未读计数、公告发布 |
| 数据导出 | 格式 + 内容 | Excel/PDF 正确性、范围筛选 |
| 角色权限 | RBAC + 守卫 | 权限矩阵、路由守卫、API 中间件 |

---

## 2. 集成测试用例集

### 2.1 认证模块

| 用例 ID | 场景 | 前置条件 | 操作步骤 | 预期结果 |
|---------|------|---------|---------|---------|
| AUTH-001 | 正常登录 | 存在有效用户 | 输入正确用户名密码 | 返回 Token，must_change_password 根据用户状态决定 |
| AUTH-002 | 错误密码 | 存在有效用户 | 输入正确用户名+错误密码 | 返回 401 "用户名或密码错误" |
| AUTH-003 | 禁用用户登录 | 用户 status=0 | 尝试登录 | 返回 403 "用户已被禁用" |
| AUTH-004 | Token 过期 | 已登录 | 等待 Token 过期后请求 | 返回 401 "Token无效或已过期" |
| AUTH-005 | 强制改密 | must_change_password=true | 登录后访问任意页面 | 跳转登录页，必须修改密码 |
| AUTH-006 | 修改密码 | 已登录 | 输入旧密码+新密码 | 密码更新成功，must_change_password=false |
| AUTH-007 | 获取当前用户 | 已登录 | GET /api/auth/me | 返回用户信息+角色+合并权限 |

### 2.2 组织架构模块

| 用例 ID | 场景 | 操作步骤 | 预期结果 |
|---------|------|---------|---------|
| ORG-001 | 创建顶级组织 | POST /organizations {name:"测试部"} | 创建成功，level=1 |
| ORG-002 | 创建子组织 | POST /organizations {parent_id:1, name:"科室A"} | 创建成功，level=2 |
| ORG-003 | 超过最大层级 | 创建 level>4 的组织 | 返回 400 "组织层级最多支持4级" |
| ORG-004 | 同级重名 | POST 同名组织 | 返回 400 "同级组织名称已存在" |
| ORG-005 | 停用有人员的组织 | PUT status=0 | 返回 400 "该组织下有人员，只能停用不能删除" |
| ORG-006 | 删除有子组织的组织 | DELETE | 返回 400 "该组织下有子组织，无法删除" |
| ORG-007 | 获取组织树 | GET /organizations/tree | 返回完整树形结构 |

### 2.3 人员管理模块

| 用例 ID | 场景 | 操作步骤 | 预期结果 |
|---------|------|---------|---------|
| STAFF-001 | 创建人员+账号 | POST /staffs {create_account:true} | 人员+账号同时创建，用户名=工号 |
| STAFF-002 | 重复工号 | POST 已有工号 | 返回 400 "工号已存在" |
| STAFF-003 | 重置单个密码 | POST /staffs/{id}/reset-password | 密码重置为 123456，需强制改密 |
| STAFF-004 | 批量重置密码 | POST /staffs/reset-passwords | 批量重置，返回成功/失败列表 |
| STAFF-005 | 删除人员 | DELETE /staffs/{id} | 级联清理排班明细、特殊规则、账号等 |
| STAFF-006 | 同步标签到角色 | PUT /staffs/{id}/sync-roles | 系统角色根据标签自动更新 |

### 2.4 排班模块

| 用例 ID | 场景 | 操作步骤 | 预期结果 |
|---------|------|---------|---------|
| SCH-001 | 创建排班草稿 | POST /schedules {status:0} | 创建成功 |
| SCH-002 | 发布排班 | POST /schedules/publish | 状态变为 1=已发布 |
| SCH-003 | 撤回排班 | POST /schedules/recall | 状态变为 2=已撤回 |
| SCH-004 | 修改已发布排班 | PUT 已发布记录 | 返回 400（LOCKED_STATUSES 保护） |
| SCH-005 | 自动排班生成 | POST /schedules/auto-generate | 生成草稿状态排班 |
| SCH-006 | 全局约束校验 | POST /schedules/validate | 返回通过/警告/失败分类结果 |
| SCH-007 | 导入排班模板 | POST /schedules/import (.xlsx) | 批量导入成功 |
| SCH-008 | 月末自动排班 | APScheduler 触发 | 月末最后一天在配置时间 ±30 分钟窗口内自动执行，防重复机制生效 |

### 2.5 调班模块

| 用例 ID | 场景 | 操作步骤 | 预期结果 |
|---------|------|---------|---------|
| SWAP-001 | 发起指定换班 | POST /swaps {swap_type:"specified"} | 状态 pending_confirm |
| SWAP-002 | 对方确认 | PUT /swaps/{id}/confirm | 状态 → pending_approve |
| SWAP-003 | 审批通过 | PUT /swaps/{id}/approve | 状态 → approved → completed |
| SWAP-004 | 发起开放换班 | POST /swaps {swap_type:"open"} | 状态 pending_claim |
| SWAP-005 | 认领开放换班 | PUT /swaps/{id}/claim | 状态 → pending_approve |
| SWAP-006 | 拒绝换班 | PUT /swaps/{id}/refuse | 状态 → cancelled |
| SWAP-007 | 撤回申请 | PUT /swaps/{id}/cancel | 状态 → cancelled |

---

## 3. 手动测试脚本说明

项目根目录包含两个独立测试脚本：

| 脚本 | 用途 | 运行方式 |
|------|------|---------|
| `test_auto_schedule.py` | 测试自动排班引擎 | `python test_auto_schedule.py` |
| `test_cross_month.py` | 测试跨月配对关系 | `python test_cross_month.py` |

> 这两个是开发期手动验证脚本，不建议纳入自动化测试框架。

---

## 4. 测试环境

| 项目 | 值 |
|------|------|
| 数据库 | PostgreSQL 15+, 数据库名 `scp_db` |
| 后端地址 | http://localhost:8000 |
| 前端地址 | http://localhost:5173 |
| 测试账号 | admin / admin123 |

---

## 5. 测试执行顺序

```
1. 初始化测试数据库
2. 运行后端启动 → 验证 /health 端点
3. 执行认证测试（AUTH-001 ~ AUTH-007）
4. 执行基础 CRUD 测试（ORG/STAFF/SCH_TEMPLATE/CONSTRAINT）
5. 执行核心流程测试（排班生成→校验→发布→调班）
6. 执行边界测试（权限不足、重复操作、数据冲突）
7. 执行导出功能测试
```
