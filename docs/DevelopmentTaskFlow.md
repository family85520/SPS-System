# 排班管理系统 开发任务流程文档

**文档版本：** V1.0
**基于文档：** PRD V1.0 + UI设计规范（完整整合版）
**更新日期：** 2026年5月16日

---

## 一、开发总览与阶段划分

### 1.1 项目阶段

| 阶段 | 周期 | 核心内容 | 状态 |
|------|------|---------|------|
| 阶段一 | Week 1 | 项目骨架 + 数据库 + 认证 + 基础CRUD | ✅ 已完成 |
| 阶段二 | Week 2 | 配置模块（班次模板、约束规则、特殊规则、角色权限） | 待开发 |
| 阶段三 | Week 3 | 排班核心（自动排班、手动微调、约束校验、发布） | 待开发 |
| 阶段四 | Week 4 | 消息系统 + 公告管理 + 首页看板 | 待开发 |
| 阶段五 | Week 5 | 调班管理（申请、认领、审批、冲突检测） | 待开发 |
| 阶段六 | Week 6 | 移动端 + 数据导出 | 待开发 |
| 阶段七 | Week 7 | 部署脚本 + 集成测试 + 文档 | 待开发 |

### 1.2 技术栈

```
后端：Python 3.12 + FastAPI + SQLAlchemy 2.0 + PostgreSQL
前端：Vue 3 + TypeScript + Element Plus + Pinia + Vue Router
移动端：uni-app (Vue 3)
部署：Nginx + systemd(Linux) / NSSM(Windows)
数据库：scp_db（用户：scp，密码：scp2026）
```

### 1.3 已完成内容（阶段一）

```
后端：
├── FastAPI项目骨架（main.py, config.py, database.py）
├── 全部数据模型（13张表的SQLAlchemy模型）
├── 用户认证（JWT登录、Token验证、权限中间件）
├── 组织架构 CRUD API（5个接口）
├── 人员管理 CRUD API（5个接口）
├── 默认数据初始化（4个角色、admin账号、3条配置）
└── Alembic数据库迁移

前端：
├── Vue3 + Element Plus 项目结构
├── 登录页面（LoginView.vue）
├── 主布局（MainLayout.vue，侧边栏+顶栏）
├── 工作台页面（DashboardView.vue）
├── 路由配置 + 权限守卫
├── Pinia认证状态管理
├── Axios封装 + 拦截器
└── 占位页面（PlaceholderView.vue）
```

---

## 二、视觉规范速查

### 2.1 配色

```scss
// 主色
--primary: #0A63D8;
--secondary: #17A2B8;
--success: #28A745;
--warning: #FFC107;
--danger: #DC3545;

// 背景
--bg-page: #F5F7FA;
--bg-card: #FFFFFF;

// 文本
--text-primary: #1F2D3D;
--text-secondary: #556173;

// 边框
--border-color: #E6EAF0;

// 班次色
--shift-morning: #FFD166;
--shift-afternoon: #06D6A0;
--shift-night: #118AB2;
--shift-leader: #F08A5D;
```

### 2.2 布局

```
顶栏高度：56px
侧边栏宽度：240px（折叠后64px）
卡片圆角：6px
卡片内边距：16px~24px
栅格：12列，gutter 16px
基础间距单位：8px
```

### 2.3 字体

```
标题：H1 24px/600 | H2 20px/600 | H3 16px/600
正文：14px/400
辅助：12px/400
行高：正文1.5 | 标题1.25
```

---

## 三、详细开发任务

---

### 阶段二：配置模块（Week 2）

---

#### 任务 2.1：班次模板管理（后端）

**文件变更：**
- 新建：`app/api/shift_template.py`
- 新建：`app/schemas/shift_template.py`
- 新建：`app/services/shift_template_service.py`
- 修改：`app/main.py`（注册路由）

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/shift-templates | 获取班次模板列表（支持按组织筛选、启用/停用筛选） |
| GET | /api/shift-templates/{id} | 获取单个班次模板详情 |
| POST | /api/shift-templates | 创建班次模板 |
| PUT | /api/shift-templates/{id} | 更新班次模板 |
| DELETE | /api/shift-templates/{id} | 删除班次模板（有关联排班记录时不允许删除） |
| POST | /api/shift-templates/{id}/copy | 复制班次模板 |
| PUT | /api/shift-templates/{id}/status | 启用/停用班次模板 |

**Schema 字段：**

```
ShiftTemplateCreate:
  name: str（必填，1-50字符）
  org_id: int | null（可选，为空表示全局）
  start_time: str（必填，格式HH:MM）
  end_time: str（必填，格式HH:MM）
  duration_hours: float（自动计算，跨夜班特殊处理）
  color: str（必填，HEX颜色值）
  leader_min: int（必填，>=0）
  leader_max: int（必填，>=leader_min）
  leader_pool: list[int] | null（领导候选人员ID列表）
  member_min: int（必填，>=1）
  member_max: int（必填，>=member_min）
  apply_days: list[int]（必填，1-7对应周一到周日）

ShiftTemplateUpdate: 同上，所有字段可选

ShiftTemplateResponse: 同上 + id, status, created_at, updated_at
```

**业务规则：**
- 跨夜班（如22:00-06:00）时长自动计算为8小时
- 班次时长为0或负数时禁止保存
- 同一组织下班次名称不可重复
- 有关联排班记录的模板不允许删除，只能停用
- 复制模板时名称自动加"(副本)"后缀

**验收标准：**
- 所有7个接口正常工作
- 跨夜班时长计算正确
- 业务规则校验生效

---

#### 任务 2.2：班次模板管理（前端）

**文件变更：**
- 新建：`src/api/shift-template.ts`
- 新建：`src/views/shift-template/ShiftTemplateView.vue`
- 修改：`src/router/index.ts`（更新路由指向）

**页面布局（UI规范5.4）：**
采用 SplitLayout 分栏布局：
- 左侧面板：班次模板列表
- 右侧面板：模板编辑表单

**左侧面板 - 模板列表：**
- 每项显示：班次名称、时间范围、颜色标签、适用状态
- 顶部：搜索框 + 新建按钮
- 点击列表项在右侧显示编辑表单
- 支持启用/停用开关切换

**右侧编辑表单字段：**

```
班次名称：  输入框，必填
起始时间：  时间选择器，必填
结束时间：  时间选择器，必填
班次时长：  数值，自动计算显示，不可编辑
颜色标识：  颜色选择器
值班领导：
  - 最少人数：数字输入，>=0
  - 最多人数：数字输入，>=最少人数
  - 候选人员池：人员多选下拉（从标记为领导/带班的人员中选）
值班人员：
  - 最少人数：数字输入，>=1
  - 最多人数：数字输入，>=最少人数
适用日期：  周一~周日 多选复选框
启用状态：  开关

按钮：[保存] [复制] [删除] [取消]
```

**交互要点：**
- 起止时间修改后自动计算时长，跨夜班显示提示
- 颜色选择后实时预览色块
- 保存成功后左侧列表实时更新
- 停用弹窗确认："停用后该班次不参与自动排班，确认停用？"
- 删除弹窗确认：使用UI规范中的确认文案

**验收标准：**
- 表单字段校验完整
- 跨夜班时长实时计算
- 左右联动正常
- 颜色预览正确

---

#### 任务 2.3：约束规则管理（后端）

**文件变更：**
- 新建：`app/api/constraint.py`
- 新建：`app/schemas/constraint.py`
- 新建：`app/services/constraint_service.py`
- 新建：`app/models/constraint.py`（如果sch_constraint表模型未创建）
- 修改：`app/models/__init__.py`
- 修改：`app/main.py`

**数据模型（sch_constraint表）：**

```python
class SchConstraint(Base, TimestampMixin):
    __tablename__ = "sch_constraint"
    
    id: int              # 主键
    rule_type: str       # 规则类型编码
    rule_name: str       # 规则名称
    params: dict (JSON)  # 规则参数
    priority: int        # 优先级（数字越小越优先）
    scope_type: str      # 适用范围类型（all/org）
    scope_ids: list (JSON)  # 适用范围ID列表
    enabled: bool        # 是否启用
```

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/constraints | 获取约束规则列表 |
| GET | /api/constraints/{id} | 获取单个规则详情 |
| POST | /api/constraints | 创建约束规则 |
| PUT | /api/constraints/{id} | 更新约束规则 |
| DELETE | /api/constraints/{id} | 删除约束规则 |
| PUT | /api/constraints/{id}/toggle | 启用/禁用规则 |
| PUT | /api/constraints/batch-priority | 批量更新优先级 |

**预置规则类型（init_data中初始化）：**

| rule_type | rule_name | params结构 |
|-----------|-----------|-----------|
| MAX_CONTINUOUS_DAYS | 连续工作上限 | {"max_days": 5} |
| MIN_REST_AFTER_CONTINUOUS | 连续工作后最少休息 | {"rest_days": 1} |
| MIN_SHIFT_INTERVAL | 班次最少间隔 | {"hours": 8} |
| MIN_REST_AFTER_NIGHT | 夜班后最少休息 | {"hours": 12} |
| MAX_SHIFTS_PER_DAY | 每天最多上班数 | {"count": 1} |
| MAX_WEEKLY_HOURS | 每周最多工作时长 | {"hours": 48} |
| HOLIDAY_MODE | 节假日排班模式 | {"mode": "normal"} |
| WEEKEND_DIFF | 周末差异化 | {"enabled": false} |

**业务规则：**
- 预置规则不可删除，只能启用/禁用和修改参数
- 自定义规则可创建、修改、删除
- 优先级允许拖拽排序
- 适用范围为all时全局生效，为org时仅对指定组织生效

**验收标准：**
- 8种预置规则初始化正确
- CRUD接口正常
- 启用/禁用即时生效
- 优先级排序正确

---

#### 任务 2.4：约束规则管理（前端）

**文件变更：**
- 新建：`src/api/constraint.ts`
- 新建：`src/views/constraint/ConstraintView.vue`
- 修改：`src/router/index.ts`

**页面布局（UI规范5.5）：**
采用 SplitLayout 分栏布局：
- 左侧面板：规则列表
- 右侧面板：规则详情编辑

**左侧 - 规则列表：**
- 每项显示：规则名称、启用状态开关、优先级序号
- 支持拖拽排序调整优先级
- 顶部：新建自定义规则按钮

**右侧 - 规则详情编辑：**

```
规则名称：  输入框
规则类型：  下拉选择（预置类型只读，自定义可选）
启用状态：  开关
优先级：    数字输入
适用范围：  全部 / 指定组织
指定组织：  组织多选（scope_type为org时显示）

参数区域（根据规则类型动态变化）：
  连续工作上限 → 最多连续上班天数：[数字输入]
  班次最少间隔 → 最少间隔小时数：[数字输入]
  夜班后最少休息 → 最少休息小时数：[数字输入]
  每天最多上班数 → 每天最多排几个班：[数字输入]
  每周最多工作时长 → 每周累计小时上限：[数字输入]
  节假日模式 → 正常轮转/特殊安排：[单选]
  周末差异化 → 启用/禁用：[开关]

按钮：[保存] [删除]（预置规则删除按钮禁用）
```

**交互要点：**
- 切换规则类型时参数表单动态切换
- 启用/禁用开关即时生效
- 拖拽排序后自动保存优先级
- 保存时校验参数合理性

**验收标准：**
- 8种规则的参数表单正确展示
- 拖拽排序正常
- 启用/禁用即时生效
- 适用范围选择正确

---

#### 任务 2.5：特殊角色排班规则（后端）

**文件变更：**
- 新建：`app/api/special_rule.py`
- 新建：`app/schemas/special_rule.py`
- 新建：`app/services/special_rule_service.py`
- 修改：`app/main.py`

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/special-rules | 获取特殊规则列表（支持按人员筛选） |
| GET | /api/special-rules/{id} | 获取单个特殊规则详情 |
| POST | /api/special-rules | 创建特殊规则 |
| PUT | /api/special-rules/{id} | 更新特殊规则 |
| DELETE | /api/special-rules/{id} | 删除特殊规则 |

**Schema 字段：**

```
SpecialRuleCreate:
  staff_id: int（必填，关联人员）
  rule_type: str（必填，规则类型）
  params: dict（必填，规则参数，结构因类型而异）
  effective_from: date | null（可选，生效开始日期）
  effective_to: date | null（可选，生效结束日期）
  reason: str | null（可选，备注原因）

rule_type 类型：
  exclude_shift     → 不排某班次        params: {"exclude_shift_ids": [1,3]}
  include_shift     → 仅排某班次        params: {"include_shift_ids": [1]}
  exclude_post      → 不排某岗位        params: {"exclude_post_ids": [2]}
  must_pair         → 必须搭配某人      params: {"must_pair_staff_ids": [5]}
  exclude_date      → 特定日期不排班    params: {"exclude_dates": ["2026-06-15"]}
  exclude_weekday   → 特定星期不排某班  params: {"exclude_weekdays": [3], "exclude_shift_ids": [3]}
```

**业务规则：**
- 个人特殊规则优先于通用约束规则
- 有有效期的规则到期自动失效
- 同一人员同一规则类型可有多条（不同参数）

**验收标准：**
- 6种规则类型CRUD正常
- 有效期逻辑正确
- 参数结构校验完整

---

#### 任务 2.6：特殊角色排班规则（前端）

**文件变更：**
- 新建：`src/api/special-rule.ts`
- 新建：`src/views/staff/components/SpecialRuleDrawer.vue`
- 修改：`src/views/staff/StaffView.vue`（人员详情中增加特殊规则入口）

**页面交互：**
在人员管理页面，点击人员行的"特殊规则"按钮，从右侧滑出抽屉：

```
抽屉标题：{人员姓名} - 特殊排班规则

规则列表：
  - 规则类型（文字标签）
  - 规则参数（文字描述）
  - 有效期（起止日期）
  - 备注
  - 操作：编辑 | 删除

按钮：[新增规则]

新增/编辑表单：
  规则类型：下拉选择
  参数区域：（根据类型动态展示对应表单）
  有效期：日期范围选择器
  备注：文本输入框
  按钮：[保存] [取消]
```

**验收标准：**
- 抽屉交互正常
- 6种规则类型的参数表单正确
- 有效期范围选择正确
- 列表与后端数据同步

---

#### 任务 2.7：角色权限管理（后端）

**文件变更：**
- 新建：`app/api/role.py`
- 新建：`app/schemas/role.py`
- 修改：`app/main.py`

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/roles | 获取角色列表 |
| GET | /api/roles/{id} | 获取角色详情（含权限配置） |
| POST | /api/roles | 创建自定义角色 |
| PUT | /api/roles/{id} | 更新角色（名称、权限） |
| DELETE | /api/roles/{id} | 删除自定义角色（系统内置角色不可删除） |
| POST | /api/users/{user_id}/roles | 为用户分配角色 |
| GET | /api/users/{user_id}/roles | 获取用户的角色列表 |

**业务规则：**
- 系统内置4个角色（admin/scheduler/leader/member）不可删除
- 权限结构：{"resource": ["action1", "action2"]}
- admin角色拥有全部权限，无需配置

**验收标准：**
- 角色CRUD正常
- 系统角色不可删除
- 权限结构存储正确
- 用户角色分配正常

---

#### 任务 2.8：角色权限管理（前端）

**文件变更：**
- 新建：`src/views/role/RoleView.vue`
- 新建：`src/api/role.ts`
- 修改：`src/router/index.ts`

**页面布局：**
左侧角色列表 + 右侧权限配置面板

```
左侧角色列表：
  - 角色名称
  - 系统内置标记（lock图标）
  - 用户数量
  - 操作：编辑 | 删除（系统角色删除按钮禁用）

右侧权限配置：
  权限矩阵表格：
  行 = 功能模块（组织管理、人员管理、班次模板、约束规则、排班管理、调班管理、消息、导出）
  列 = 操作（查看、创建、编辑、删除、发布、审批）
  每个交叉点 = 复选框

  按钮：[保存权限]
```

**验收标准：**
- 权限矩阵交互正常
- 系统角色只读显示
- 自定义角色可编辑

---

#### 任务 2.9：系统配置管理（后端+前端）

**文件变更：**
- 新建：`app/api/system.py`
- 新建：`src/views/system/SystemView.vue`
- 新建：`src/api/system.ts`
- 修改：`app/main.py`
- 修改：`src/router/index.ts`

**后端接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/system/config | 获取所有系统配置 |
| PUT | /api/system/config | 更新系统配置（批量） |

**前端页面字段：**

```
系统名称：  输入框
单位名称：  输入框
调班审批开关：开关（开启/关闭）

按钮：[保存配置]
```

**验收标准：**
- 配置读取和保存正常
- 审批开关状态即时生效

---

### 阶段三：排班核心（Week 3）

---

#### 任务 3.1：手动排班API（后端）

**文件变更：**
- 新建：`app/api/schedule.py`
- 新建：`app/schemas/schedule.py`
- 新建：`app/services/schedule_service.py`
- 修改：`app/main.py`

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/schedules | 获取排班列表（按日期范围+组织筛选） |
| GET | /api/schedules/calendar | 获取排班日历数据（月/周视图） |
| GET | /api/schedules/{id} | 获取排班记录详情 |
| POST | /api/schedules | 创建单条排班记录 |
| PUT | /api/schedules/{id} | 更新排班记录（修改人员） |
| DELETE | /api/schedules/{id} | 删除排班记录（仅草稿状态可删） |
| POST | /api/schedules/batch | 批量创建/更新排班 |
| POST | /api/schedules/assign-staff | 为排班分配人员（含领导） |
| POST | /api/schedules/remove-staff | 移除排班中的人员 |
| GET | /api/schedules/staff-summary/{staff_id} | 获取人员排班统计（已排天数、累计时长等） |

**日历数据结构：**

```
GET /api/schedules/calendar?start=2026-06-01&end=2026-06-30&org_id=1

返回：
{
  "dates": [
    {
      "date": "2026-06-01",
      "shifts": [
        {
          "schedule_id": 1,
          "shift_template_id": 1,
          "shift_name": "早班",
          "shift_color": "#FFD166",
          "start_time": "08:00",
          "end_time": "16:00",
          "leader": {"staff_id": 5, "name": "王队"},
          "members": [
            {"staff_id": 1, "name": "张三"},
            {"staff_id": 2, "name": "李四"}
          ],
          "status": 0,
          "conflicts": []
        }
      ]
    }
  ]
}
```

**业务规则：**
- 已发布排班不可直接修改，需通过调班流程
- 手动排班时实时校验约束规则
- 人员分配时检查是否重复排班
- 支持从草稿状态直接修改

**验收标准：**
- 日历接口返回结构正确
- CRUD接口正常
- 草稿/已发布状态控制正确
- 人员分配/移除逻辑正确

---

#### 任务 3.2：排班日历视图（前端）

**文件变更：**
- 新建：`src/views/schedule/ScheduleCalendarView.vue`
- 新建：`src/views/schedule/components/CalendarGrid.vue`
- 新建：`src/views/schedule/components/ShiftCell.vue`
- 新建：`src/views/schedule/components/ShiftDetailDrawer.vue`
- 新建：`src/views/schedule/components/StaffSelector.vue`
- 新建：`src/api/schedule.ts`
- 修改：`src/router/index.ts`

**页面布局（UI规范5.7）：**

```
Page: ScheduleCalendarPage
├── CalendarToolbar
│   ├── 日期导航：[◀ 上月] [今天] [下月 ▶]
│   ├── 视图切换：[月视图] [周视图]
│   ├── 组织筛选：下拉选择
│   ├── 状态筛选：全部/草稿/已发布
│   └── 操作按钮：[发布] [撤回] [导出] [校验]
│
├── CalendarGrid（月视图）
│   ├── 表头：周一 ~ 周日
│   ├── 日期格子（每月一行一周）
│   │   ├── 日期数字
│   │   └── ShiftCell（每个班次一个色块）
│   │       ├── 领导标签（小标签，班次色上方）
│   │       ├── 班次名称
│   │       ├── 值班人员列表
│   │       └── 冲突标记（红色边框+⚠图标）
│   └── 超出显示 "+X更多"
│
└── ShiftDetailDrawer（右抽屉）
    ├── 班次信息（名称、时间、人员）
    ├── 值班领导选择
    ├── 值班人员选择
    ├── 冲突提示列表
    └── 操作按钮：[保存] [删除] [取消]
```

**交互要点：**
- 班次色块按班次模板颜色显示
- 冲突位置红色边框+警告图标
- 点击色块打开详情抽屉
- 拖拽人员从左侧人员池到班次格子
- 领导和人员分别选择
- 月/周视图切换

**日历单元格样式：**

```scss
.shift-cell {
  min-height: 80px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 4px;
  
  &.has-conflict {
    border-color: var(--danger);
    border-width: 2px;
  }
}

.shift-block {
  border-radius: 3px;
  padding: 2px 6px;
  margin-bottom: 2px;
  font-size: 12px;
  
  .leader-tag {
    background: var(--shift-leader);
    color: white;
    border-radius: 2px;
    padding: 0 4px;
    font-size: 10px;
  }
}
```

**验收标准：**
- 月视图/周视图切换正常
- 班次色块颜色正确
- 冲突高亮显示
- 抽屉交互正常
- 人员选择正确

---

#### 任务 3.3：约束校验引擎（后端）

**文件变更：**
- 新建：`app/engine/constraint_checker.py`
- 新建：`app/engine/models.py`（引擎内部数据模型）

**引擎接口：**

```python
class ConstraintChecker:
    def check_all(self, schedules, staff_list, constraints) -> CheckResult:
        """全局约束校验"""
        pass
    
    def check_single(self, schedule, staff, all_schedules, constraints) -> list[Violation]:
        """单条排班校验"""
        pass

class CheckResult:
    passed: list[RuleCheck]      # 通过的规则
    warnings: list[Violation]    # 警告（建议调整）
    failed: list[Violation]      # 失败（必须修正）

class Violation:
    rule_type: str        # 违反的规则类型
    rule_name: str        # 规则名称
    message: str          # 违规描述
    schedule_id: int      # 相关排班记录ID
    staff_id: int         # 相关人员ID
    date: str             # 相关日期
    severity: str         # warning / error
```

**校验逻辑（按优先级排序）：**
1. 每班最少人数检查
2. 每班必须含值班领导（如配置要求）
3. 班次间隔检查
4. 每人每天最多上班数检查
5. 连续工作天数检查
6. 连续工作后最少休息检查
7. 夜班后最少休息检查
8. 每周最多工作时长检查
9. 特殊角色规则检查

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/schedules/validate | 对指定范围排班执行全局约束校验 |
| POST | /api/schedules/validate-single | 单条排班实时校验（手动排班时调用） |

**验收标准：**
- 8类约束规则校验逻辑正确
- 校验结果结构完整
- 通过/警告/失败分类正确
- 校验响应时间：20人×30天 < 5秒

---

#### 任务 3.4：约束校验报告页面（前端）

**文件变更：**
- 新建：`src/views/schedule/components/ValidationReport.vue`
- 修改：`src/views/schedule/ScheduleCalendarView.vue`（集成校验按钮和报告）

**页面布局（UI规范5.9）：**

```
校验报告（模态框或独立页面）：
├── ValidationSummaryCard
│   ├── 已通过数量（绿色数字）
│   ├── 警告数量（黄色数字）
│   └── 失败数量（红色数字）
│
├── ValidationResultTabs
│   ├── Tab: 已通过（8条）
│   │   └── 规则列表，每行显示规则名称 + ✅
│   ├── Tab: 警告（2条）
│   │   └── 违规列表，每行显示：
│   │       ├── ⚠ 规则名称
│   │       ├── 违规描述（如"6月15日晚班值班领导刘组已连续值班3天"）
│   │       └── 操作：[返回修改] [标记豁免]
│   └── Tab: 失败（0条）
│       └── 违规列表，每行显示：
│           ├── ❌ 规则名称
│           ├── 违规描述
│           └── 操作：[返回修改]
│
├── 豁免原因输入（点击"标记豁免"后展开）
│   └── 文本输入框 + [确认豁免] [取消]
│
└── ActionPanel
    ├── [返回微调]
    └── [确认发布]（存在失败项时禁用）
```

**交互要点：**
- Tab切换显示不同严重级别的结果
- 标记豁免时要求填写原因
- 存在未处理的失败项时，"确认发布"按钮禁用
- 点击"返回微调"关闭报告并聚焦到日历视图

**验收标准：**
- 校验结果展示正确
- Tab切换正常
- 豁免流程完整
- 发布按钮状态控制正确

---

#### 任务 3.5：排班发布与撤回（后端+前端）

**文件变更：**
- 修改：`app/api/schedule.py`（新增发布/撤回接口）
- 修改：`app/services/schedule_service.py`
- 修改：`src/views/schedule/ScheduleCalendarView.vue`
- 新建：`src/views/schedule/components/PublishConfirmDialog.vue`

**后端接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/schedules/publish | 发布排班（指定日期范围+组织） |
| POST | /api/schedules/recall | 撤回排班 |

**发布流程：**
1. 前端点击"确认发布"
2. 弹窗确认："确认发布2026年6月排班表？发布后排班将被锁定，变更需通过调班流程。"
3. 后端检查：
   - 是否已执行过校验
   - 是否存在未处理的失败项
4. 校验通过 → 更新状态为"已发布" → 记录发布时间和发布人 → 发送系统消息通知
5. 校验不通过 → 返回错误提示

**撤回流程：**
1. 前端点击"撤回排班"
2. 弹窗确认："撤回后排班将变为草稿，相关人员将收到通知。"
3. 后端更新状态为"已撤回" → 发送通知

**验收标准：**
- 发布前校验逻辑正确
- 发布后排班锁定
- 撤回后恢复草稿状态
- 确认弹窗文案符合UI规范

---

#### 任务 3.6：自动排班算法引擎（后端）

**文件变更：**
- 新建：`app/engine/scheduler.py`
- 新建：`app/engine/scoring.py`
- 修改：`app/api/schedule.py`（新增自动排班接口）
- 修改：`app/services/schedule_service.py`

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/schedules/auto-generate | 自动排班生成 |

**请求参数：**

```json
{
  "start_date": "2026-06-01",
  "end_date": "2026-06-30",
  "org_id": 1,
  "shift_template_ids": [1, 2, 3],
  "constraint_ids": [1, 2, 3, 4],
  "staff_ids": [1, 2, 3, 4, 5]
}
```

**算法核心逻辑：**

```
输入参数：
  ├─ 排班日期范围
  ├─ 班次模板列表（含值班领导/人员人数范围）
  ├─ 可用人员列表（排除请假/停用/外派人员）
  ├─ 已启用的约束规则列表
  ├─ 特殊角色排班规则
  └─ 历史排班数据（用于公平性计算）

处理流程：
  Step 1: 按优先级排序约束规则
  Step 2: 对排班周期内每一天循环处理
    Step 2.1: 获取当天需排的班次列表
    Step 2.2: 对每个班次
      ├─ 先排值班领导：
      │   ├─ 从领导候选池筛选可用人员
      │   ├─ 应用特殊规则过滤
      │   ├─ 按约束规则过滤（连续工作、间隔等）
      │   ├─ 按公平性打分（休息天数多者优先）
      │   └─ 选择最优人员
      └─ 再排值班人员：
          ├─ 筛选可用人员
          ├─ 应用特殊规则过滤
          ├─ 按约束规则过滤
          ├─ 按公平性打分
          └─ 在人数范围内选择最优人员组合
  Step 3: 全局约束校验
  Step 4: 输出排班表 + 冲突报告

公平性打分因素：
  ├─ 近期休息天数（越多越优先排班）
  ├─ 累计工作时长（越少越优先排班）
  ├─ 夜班次数均衡（夜班少的优先排夜班）
  └─ 周末/节假日均衡
```

**响应结构：**

```json
{
  "schedules": [...],
  "report": {
    "total_shifts": 90,
    "total_staff": 8,
    "avg_hours_per_person": 45,
    "night_shift_distribution": {...},
    "conflicts": [...]
  }
}
```

**验收标准：**
- 20人×1个月排班在10秒内完成
- 排班结果符合所有已启用约束
- 公平性分布合理
- 冲突报告准确

---

#### 任务 3.7：自动排班页面（前端）

**文件变更：**
- 新建：`src/views/schedule/AutoScheduleView.vue`
- 新建：`src/views/schedule/components/AutoScheduleParams.vue`
- 新建：`src/views/schedule/components/AutoScheduleReport.vue`
- 修改：`src/router/index.ts`

**页面布局（UI规范5.6）：**

```
Page: AutoSchedulePage
├── ParameterPanel（左侧1/3）
│   ├── 排班周期：日期范围选择器
│   ├── 班次模板：多选列表（显示名称+时间+颜色）
│   ├── 排班范围：组织树选择
│   ├── 人员范围：人员多选（根据组织筛选）
│   ├── 约束规则：多选列表（显示已启用的规则）
│   └── 按钮：[一键生成]
│
└── PreviewPanel（右侧2/3）
    ├── 生成报告
    │   ├── 排班总数
    │   ├── 人均工时
    │   ├── 夜班分布图
    │   └── 冲突统计
    ├── 冲突高亮列表
    ├── 日历预览（可切换表格/日历视图）
    └── 按钮：[进入微调] [保存草稿] [重新生成]
```

**交互要点：**
- 参数不完整时"一键生成"按钮禁用，tooltip提示缺少的参数
- 生成过程中显示loading动画
- 生成完成后自动切换到预览面板
- 冲突项点击跳转到日历视图对应位置
- "进入微调"跳转到排班日历页面

**前端校验提示：**
- 未选择排班周期："请先选择排班周期"
- 未选择班次模板："请至少选择一个班次模板"
- 未选择排班范围："请选择排班范围"
- 未选择人员范围："请选择人员范围"

**验收标准：**
- 参数选择完整后才能生成
- 生成结果正确展示
- 报告数据准确
- 跳转微调正常

---

### 阶段四：消息系统 + 首页看板（Week 4）

---

#### 任务 4.1：消息系统（后端）

**文件变更：**
- 新建：`app/api/message.py`
- 新建：`app/schemas/message.py`
- 新建：`app/services/message_service.py`
- 新建：`app/services/notification.py`
- 修改：`app/main.py`（WebSocket路由）

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/messages | 获取消息列表（分页+类型筛选） |
| GET | /api/messages/unread-count | 获取未读消息数量 |
| PUT | /api/messages/{id}/read | 标记单条消息为已读 |
| PUT | /api/messages/read-all | 全部标记已读 |
| WebSocket | /ws/messages | 实时消息推送 |

**消息触发场景（在对应服务中调用notification模块）：**

| 触发事件 | 通知对象 | 消息类型 | 消息模板 |
|---------|---------|---------|---------|
| 排班表发布 | 排班范围内全体 | schedule | "{org_name}{year}年{month}月排班表已发布，请查看您的值班安排" |
| 排班表撤回 | 排班范围内全体 | schedule | "{org_name}{year}年{month}月排班表已撤回，请等待重新发布" |
| 排班修改 | 被影响人员 | schedule | "您{date}的班次已调整为{shift_name}，请查看" |
| 调班申请（指定） | 被换人 | swap | "{applicant}申请与您换班：{date}{shift}" |
| 调班申请（开放） | 全组 | swap | "{applicant}发布了一个替班申请：{date}{shift}，快来认领" |
| 审批提醒 | 审批人 | approve | "有一条新的调班申请待审批" |
| 审批结果 | 申请人 | approve | "您的换班申请已通过/已拒绝" |

**WebSocket连接流程：**
1. 客户端连接 ws://localhost:8000/ws/messages?token=xxx
2. 服务端验证token
3. 建立连接后，消息变化时实时推送
4. 推送格式：{"type": "new_message", "data": {...}}

**验收标准：**
- 消息CRUD正常
- WebSocket连接稳定
- 消息触发场景覆盖完整
- 未读计数正确

---

#### 任务 4.2：消息中心页面（前端）

**文件变更：**
- 新建：`src/views/message/MessageView.vue`
- 新建：`src/views/message/components/MessageList.vue`
- 新建：`src/views/message/components/MessageDetailDrawer.vue`
- 新建：`src/api/message.ts`
- 修改：`src/layouts/MainLayout.vue`（顶栏消息角标+WebSocket）
- 修改：`src/router/index.ts`

**页面布局（UI规范5.11）：**

```
Page: MessageNoticePage
├── MessageToolbar
│   ├── 分类Tab：全部 | 排班通知 | 调班通知 | 审批提醒 | 公告
│   ├── 操作：[全部已读]
│   └── 搜索框
│
├── MessageList
│   └── MessageItem（每条消息）
│       ├── 未读圆点（蓝色）
│       ├── 消息标题
│       ├── 消息摘要（截取前50字）
│       ├── 时间（相对时间：刚刚/5分钟前/昨天）
│       ├── 消息类型标签
│       └── 点击打开详情抽屉
│
└── MessageDetailDrawer
    ├── 标题
    ├── 内容
    ├── 时间
    ├── 跳转按钮：[查看排班] [查看调班申请]（根据消息类型）
    └── 操作：[标记已读]
```

**顶栏集成：**
- 消息图标旁显示未读数量角标
- 悬浮显示最新3条消息
- WebSocket收到新消息时实时更新角标和列表

**验收标准：**
- 分类筛选正确
- 已读/未读状态正确
- 实时推送正常
- 跳转关联页面正确

---

#### 任务 4.3：公告管理（后端+前端）

**文件变更：**
- 修改：`app/api/message.py`（新增公告接口）
- 修改：`app/services/message_service.py`
- 新建：`src/views/message/components/AnnouncementSection.vue`

**后端接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/announcements | 发布公告 |
| PUT | /api/announcements/{id} | 编辑公告 |
| DELETE | /api/announcements/{id} | 撤回公告 |
| GET | /api/announcements | 获取公告列表 |

**前端：**
在消息中心页面增加"公告"Tab，管理员角色显示"发布公告"按钮。

**验收标准：**
- 公告CRUD正常
- 公告发布后推送给指定范围人员

---

#### 任务 4.4：首页看板（后端+前端）

**文件变更：**
- 新建：`app/api/dashboard.py`
- 新建：`app/services/dashboard_service.py`
- 修改：`src/views/dashboard/DashboardView.vue`
- 新建：`src/views/dashboard/components/`（各个卡片组件）
- 修改：`app/main.py`

**后端接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/dashboard/overview | 获取首页看板数据 |

**响应结构：**

```json
{
  "org_count": 3,
  "staff_count": 15,
  "active_rules_count": 6,
  "pending_swap_count": 2,
  "today_duty": [
    {"shift_name": "早班", "leader": "王队", "members": ["张三","李四"]},
    {"shift_name": "中班", "leader": "刘组", "members": ["赵六","王五"]}
  ],
  "unread_messages": 3,
  "recent_notices": [...],
  "constraint_warnings": 0,
  "schedule_status": "published"
}
```

**前端页面（UI规范5.2，按角色差异化显示）：**

```
Page: DashboardPage
├── 排班概览卡片（左上大卡片）
│   ├── 本期排班状态（草稿/已发布）
│   ├── 排班进度
│   └── 约束冲突数量（可点击跳转）
│
├── 今日值班卡片（右上）
│   ├── 今日各班次值班人员
│   └── 值班领导
│
├── 快捷操作卡片（左中）
│   ├── [自动排班] [排班日历] [调班申请] [消息中心]
│   └── 根据角色显示不同操作
│
├── 待处理事项卡片（右中）
│   ├── 待审批调班数量
│   ├── 待确认换班数量
│   └── 未读消息数量
│
├── 最近公告卡片（左下）
│   └── 最近5条公告标题+时间
│
└── 人员统计卡片（右下，管理员可见）
    ├── 人员总数
    ├── 在岗/请假/外派统计
    └── 组织分布
```

**角色差异化：**
- 管理员：全部卡片 + 人员统计 + 系统配置入口
- 排班管理员：排班概览 + 今日值班 + 待处理事项 + 快捷操作
- 组长：本组排班统计 + 待确认调班 + 公告通知
- 普通队员：个人排班 + 我的申请 + 未读消息

**验收标准：**
- 数据加载正确
- 角色差异化显示
- 跳转链接正确
- 卡片样式符合UI规范

---

### 阶段五：调班管理（Week 5）

---

#### 任务 5.1：调班管理（后端）

**文件变更：**
- 新建：`app/api/swap.py`
- 新建：`app/schemas/swap.py`
- 新建：`app/services/swap_service.py`
- 修改：`app/main.py`

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/swaps | 获取调班申请列表（支持状态/类型筛选） |
| GET | /api/swaps/{id} | 获取调班申请详情 |
| POST | /api/swaps | 发起调班申请（指定换班/开放换班） |
| PUT | /api/swaps/{id}/confirm | 对方确认换班 |
| PUT | /api/swaps/{id}/claim | 认领开放换班 |
| PUT | /api/swaps/{id}/approve | 审批通过 |
| PUT | /api/swaps/{id}/reject | 审批拒绝 |
| PUT | /api/swaps/{id}/cancel | 撤回申请 |

**状态机：**

```
指定换班：
  pending_confirm → pending_approve → approved → completed
       ↓                ↓
    cancelled        cancelled/rejected

开放换班：
  pending_claim → pending_approve → approved → completed
       ↓               ↓
    cancelled       cancelled/rejected

当审批开关关闭时：
  pending_confirm → completed（跳过审批）
  pending_claim → completed
```

**业务规则：**
- 申请前检查：班次是否存在、是否已发布、申请人是否在该班次
- 确认/认领前检查：冲突检测（约束规则校验）
- 审批由系统配置中的"调班审批开关"控制
- 冲突检测失败时阻止操作，管理员可强制放行（需填写原因）
- 所有操作记录到操作日志

**验收标准：**
- 两种调班模式流程正确
- 状态机流转正确
- 冲突检测生效
- 审批开关控制正确

---

#### 任务 5.2：调班管理页面（前端）

**文件变更：**
- 新建：`src/views/swap/SwapView.vue`
- 新建：`src/views/swap/components/SwapRequestForm.vue`
- 新建：`src/views/swap/components/SwapDetailPanel.vue`
- 新建：`src/views/swap/components/SwapRecordTable.vue`
- 新建：`src/api/swap.ts`
- 修改：`src/router/index.ts`

**页面布局（UI规范5.10）：**

```
Page: SwapManagementPage
├── TabbedPage
│   ├── Tab: 我的申请
│   │   ├── SwapToolbar
│   │   │   ├── 状态筛选：全部/待确认/待审批/已完成/已拒绝
│   │   │   └── 按钮：[发起换班申请] [发起替班申请]
│   │   └── SwapRequestTable
│   │       ├── 列：申请编号、类型、班次信息、对象、状态、申请时间、操作
│   │       └── 操作：查看详情、撤回（仅待确认/待审批状态）
│   │
│   ├── Tab: 待我处理
│   │   └── SwapRequestTable
│   │       ├── 列：申请人、类型、班次信息、申请时间、操作
│   │       └── 操作：确认/认领、拒绝
│   │
│   └── Tab: 全部记录（管理员可见）
│       ├── SwapToolbar
│       │   ├── 时间范围筛选
│       │   ├── 人员筛选
│       │   └── 状态筛选
│       └── SwapRecordTable
│
├── SwapRequestForm（模态框）
│   ├── 调班类型：[指定换班] / [开放换班]
│   ├── 我的班次：下拉（显示自己的排班）
│   ├── 换班对象：人员下拉（指定换班时）
│   ├── 对方班次：下拉（指定换班时）
│   ├── 申请原因：文本输入
│   └── 按钮：[提交申请] [取消]
│
└── SwapDetailPanel（侧边抽屉）
    ├── 申请信息
    ├── 流程状态时间线
    ├── 原始班次 vs 调整后班次对比
    ├── 审批信息（如有）
    └── 操作按钮（根据状态显示）
```

**交互要点：**
- 申请表单中"我的班次"只显示自己已排的班次
- 指定换班时选择对方后，只显示对方的班次
- 状态时间线展示完整流程
- 待处理Tab有未读角标提示
- 认领操作弹窗确认

**验收标准：**
- 两种申请模式表单正确
- 状态流转展示正确
- 操作按钮与状态匹配
- 冲突提示正确

---

### 阶段六：移动端 + 导出（Week 6）

---

#### 任务 6.1：移动端基础搭建

**文件变更：**
- 新建：`frontend/mobile/`（uni-app项目）
- 创建页面结构（参考UI规范6.3）

**底部Tab导航：**
- 首页（Home）
- 排班（Schedule）
- 调班（Swap）
- 消息（Message）
- 我的（Profile）

**核心页面：**

```
MobileHomePage
├── TodayDutyCard（今日值班）
├── WeeklySummaryCard（本周排班摘要）
├── PendingSwapCard（待处理调班）
└── UnreadMessageCard（未读消息）

MobileSchedulePage
├── DateNavBar（日期导航）
└── DayCard列表
    ├── ShiftItem（班次+领导+人员）
    └── ConflictBadge（冲突标记）

MobileSwapFormPage
├── SwapTypeSwitch
├── MyShiftSelect
├── TargetStaffSelect
├── TargetShiftSelect
├── ReasonInput
└── SubmitButton

MobileMessagePage
├── MessageFilterTabs
└── MessageList
```

**验收标准：**
- 底部导航切换正常
- 核心页面可用
- 接口复用后端API
- H5和小程序编译通过

---

#### 任务 6.2：数据导出（后端）

**文件变更：**
- 新建：`app/api/export.py`
- 新建：`app/services/export_service.py`
- 修改：`app/main.py`

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/export/schedule/excel | 导出排班表Excel |
| GET | /api/export/schedule/pdf | 导出排班表PDF |
| GET | /api/export/statistics/excel | 导出统计报表Excel |

**Excel导出字段：**
- 排班表：日期、班次、值班领导、值班人员、组织
- 统计表：人员、排班天数、累计工时、夜班次数

**PDF导出：**
- 适配A4纸张
- 含单位名称、排班周期、公章位置、签章栏

**验收标准：**
- Excel文件格式正确，可正常打开
- PDF排版美观，适配A4打印
- 导出范围和维度筛选正确

---

#### 任务 6.3：导出页面入口（前端）

**文件变更：**
- 新建：`src/views/schedule/components/ExportDialog.vue`

**模态框：**
```
导出排班表
├── 导出格式：[Excel] [PDF]
├── 导出范围：日期范围选择
├── 导出维度：按组织 / 按人员 / 按岗位
├── 选择组织：组织下拉
└── 按钮：[导出] [取消]
```

---

### 阶段七：部署 + 测试（Week 7）

---

#### 任务 7.1：Linux部署脚本

**文件变更：**
- 新建：`deploy/linux/install.sh`
- 新建：`deploy/linux/start.sh`
- 新建：`deploy/linux/stop.sh`
- 新建：`deploy/linux/restart.sh`
- 新建：`deploy/linux/backup.sh`
- 新建：`deploy/linux/nginx.conf`

---

#### 任务 7.2：Windows部署脚本

**文件变更：**
- 新建：`deploy/windows/install.bat`
- 新建：`deploy/windows/start.bat`
- 新建：`deploy/windows/stop.bat`
- 新建：`deploy/windows/backup.bat`
- 新建：`deploy/windows/nginx.conf`

---

#### 任务 7.3：集成测试

**测试清单：**

| 模块 | 测试项 |
|------|--------|
| 登录认证 | 登录/登出/Token过期/权限控制 |
| 组织架构 | CRUD/层级/停用删除限制 |
| 人员管理 | CRUD/状态切换/特殊标签 |
| 班次模板 | CRUD/跨夜班计算/启用停用 |
| 约束规则 | CRUD/启用禁用/优先级排序 |
| 特殊规则 | 各类型CRUD/有效期 |
| 自动排班 | 生成/冲突报告/公平性 |
| 手动排班 | 日历视图/拖拽/实时校验 |
| 约束校验 | 全部规则/豁免流程 |
| 排班发布 | 发布/撤回/锁定 |
| 调班管理 | 指定换班/开放换班/审批 |
| 消息通知 | 推送/已读/分类 |
| 数据导出 | Excel/PDF |
| 移动端 | 核心功能可用 |

---

#### 任务 7.4：文档编写

| 文档 | 内容 |
|------|------|
| 部署手册 | 环境要求、安装步骤、配置说明、启动命令 |
| 用户手册 | 功能操作说明、角色权限说明、常见问题 |
| API文档 | FastAPI自动生成（/docs） |

---

## 四、上下文溢出解决方案

当对话上下文过长时，以下方法可以帮助在新对话中快速恢复上下文：

### 方法一：项目状态文档接力

在每次重大里程碑后，生成一份**项目状态快照文档**，内容包括：

```
1. 已完成功能清单（每个模块的状态：✅已完成 / 🔧进行中 / ⏳待开发）
2. 当前正在开发的任务编号和进度
3. 已知未解决的问题/待修复的Bug
4. 下一步计划
5. 关键技术决策记录（如：为什么用bcrypt替代passlib）
6. 数据库连接信息
7. 项目目录结构
```

在新对话中发送这份文档 + 你的需求，即可无缝衔接。

### 方法二：对话摘要模板

每次对话结束前，让我生成一份摘要：

```
【对话摘要】
- 本次完成：XXX
- 当前阶段：Week X，任务 X.X
- 修改的文件：文件A、文件B、文件C
- 下一步：XXX
- 已知问题：XXX
```

新对话中发送摘要 + 本开发任务文档，即可继续。

### 方法三：推荐的实际操作

**最佳实践是组合使用以上两个方法：**

1. 每完成一个任务（如任务2.1班次模板后端），在新对话中发送：
   - 本开发任务流程文档（标注当前任务编号）
   - 本次对话摘要
   - 你的下一个需求

2. 新对话的开场白模板：

```
我在开发一个排班管理系统。
技术栈：Python FastAPI + Vue3 + PostgreSQL。
数据库：scp_db，用户scp，密码scp2026。

附上开发任务流程文档（标注已完成的任务）：
[粘贴本文档，用✅标记已完成的任务]

上一次对话摘要：
- 已完成：任务2.1、2.2（班次模板后端+前端）
- 正在进行：任务2.3（约束规则后端）
- 修改的文件：xxx
- 已知问题：xxx

本次需求：继续开发任务2.3约束规则后端。
```

这样即使在全新对话中，也能完整恢复上下文继续开发。

---

## 五、文件变更总清单

### 后端新增文件

```
app/api/shift_template.py        # 班次模板API
app/api/constraint.py            # 约束规则API
app/api/special_rule.py          # 特殊规则API
app/api/role.py                  # 角色权限API
app/api/system.py                # 系统配置API
app/api/schedule.py              # 排班管理API
app/api/message.py               # 消息通知API
app/api/swap.py                  # 调班管理API
app/api/dashboard.py             # 首页看板API
app/api/export.py                # 导出API

app/models/constraint.py         # 约束规则模型

app/schemas/shift_template.py    # 班次模板Schema
app/schemas/constraint.py        # 约束规则Schema
app/schemas/special_rule.py      # 特殊规则Schema
app/schemas/role.py              # 角色权限Schema
app/schemas/schedule.py          # 排班管理Schema
app/schemas/message.py           # 消息Schema
app/schemas/swap.py              # 调班Schema

app/services/shift_template_service.py   # 班次模板服务
app/services/constraint_service.py       # 约束规则服务
app/services/special_rule_service.py     # 特殊规则服务
app/services/schedule_service.py         # 排班服务
app/services/swap_service.py             # 调班服务
app/services/message_service.py          # 消息服务
app/services/notification.py             # 通知推送服务
app/services/export_service.py           # 导出服务
app/services/dashboard_service.py        # 看板服务

app/engine/scheduler.py                  # 自动排班算法
app/engine/constraint_checker.py         # 约束校验引擎
app/engine/scoring.py                    # 公平性打分
app/engine/models.py                     # 引擎数据模型
```

### 后端修改文件

```
app/main.py                    # 注册新路由
app/models/__init__.py         # 导出新模型
app/utils/init_data.py         # 初始化约束规则数据
```

### 前端新增文件

```
src/api/shift-template.ts      # 班次模板API
src/api/constraint.ts          # 约束规则API
src/api/special-rule.ts        # 特殊规则API
src/api/role.ts                # 角色权限API
src/api/system.ts              # 系统配置API
src/api/schedule.ts            # 排班API
src/api/message.ts             # 消息API
src/api/swap.ts                # 调班API
src/api/export.ts              # 导出API

src/views/shift-template/ShiftTemplateView.vue     # 班次模板页面
src/views/constraint/ConstraintView.vue            # 约束规则页面
src/views/role/RoleView.vue                        # 角色权限页面
src/views/system/SystemView.vue                    # 系统配置页面
src/views/schedule/ScheduleCalendarView.vue        # 排班日历页面
src/views/schedule/AutoScheduleView.vue            # 自动排班页面
src/views/message/MessageView.vue                  # 消息中心页面
src/views/swap/SwapView.vue                        # 调班管理页面

src/views/schedule/components/CalendarGrid.vue         # 日历网格
src/views/schedule/components/ShiftCell.vue            # 班次格子
src/views/schedule/components/ShiftDetailDrawer.vue    # 班次详情抽屉
src/views/schedule/components/StaffSelector.vue        # 人员选择器
src/views/schedule/components/ValidationReport.vue     # 校验报告
src/views/schedule/components/PublishConfirmDialog.vue # 发布确认
src/views/schedule/components/AutoScheduleParams.vue   # 自动排班参数
src/views/schedule/components/AutoScheduleReport.vue   # 自动排班报告
src/views/schedule/components/ExportDialog.vue         # 导出弹窗
src/views/message/components/MessageList.vue           # 消息列表
src/views/message/components/MessageDetailDrawer.vue   # 消息详情
src/views/message/components/AnnouncementSection.vue   # 公告模块
src/views/swap/components/SwapRequestForm.vue          # 调班申请表单
src/views/swap/components/SwapDetailPanel.vue          # 调班详情
src/views/swap/components/SwapRecordTable.vue          # 调班记录表
src/views/dashboard/components/*.vue                   # 首页卡片组件

src/views/staff/components/SpecialRuleDrawer.vue       # 特殊规则抽屉
```

### 前端修改文件

```
src/router/index.ts                # 更新路由
src/layouts/MainLayout.vue         # 顶栏消息角标
src/views/dashboard/DashboardView.vue  # 首页看板
src/views/staff/StaffView.vue      # 人员管理（增加特殊规则入口）
```

### 移动端新增文件

```
frontend/mobile/                   # uni-app项目
├── pages/
│   ├── home/index.vue             # 首页
│   ├── schedule/index.vue         # 排班
│   ├── swap/index.vue             # 调班
│   ├── message/index.vue          # 消息
│   └── profile/index.vue          # 我的
├── components/
│   ├── TabBar.vue
│   ├── DutyCard.vue
│   ├── ShiftItem.vue
│   └── MessageItem.vue
└── api/（复用PC端API封装）
```

### 部署文件

```
deploy/linux/install.sh
deploy/linux/start.sh
deploy/linux/stop.sh
deploy/linux/restart.sh
deploy/linux/backup.sh
deploy/linux/nginx.conf

deploy/windows/install.bat
deploy/windows/start.bat
deploy/windows/stop.bat
deploy/windows/backup.bat
deploy/windows/nginx.conf
```

---

以上是完整的开发任务流程文档，覆盖从阶段二到阶段七的全部开发内容。

建议你将本文档保存为 `docs/DevelopmentTaskFlow.md`，后续对话中发送本文档（标注已完成任务）+ 对话摘要，即可在任何新对话中无缝衔接开发。