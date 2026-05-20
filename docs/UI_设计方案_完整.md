# 排班管理系统 UI 设计规范（完整整合版）

## 概览

本文档为排班管理系统的完整 UI 设计规范，已整合：

- 方案概览与关键页面设计
- 视觉与配色规范
- 布局与栅格体系
- 组件规范与字段映射
- 页面组件树与移动端结构
- 交互文案与文案规范
- 交互错误流说明
- 操作流程与逻辑

目标读者：产品、设计、前端工程师。

---

## 1. 设计目标

- 以“规则配置 → 自动排班 → 手动微调 → 约束校验 → 发布”作为核心流程。
- 支持三类角色视角：系统管理员、排班管理员、组长、普通队员。
- PC 端为主操作端，移动端为查看与调班入口。
- 界面清晰、状态明确、操作反馈及时、冲突提示直观。
- 提供统一文案与组件规范，降低设计与实现差异。

---

## 2. 视觉体系与配色规范

### 2.1 主要配色

- 主色：#0A63D8
- 次色：#17A2B8
- 成功色：#28A745
- 警告色：#FFC107
- 失败/冲突色：#DC3545
- 背景灰：#F5F7FA
- 面板背景：#FFFFFF
- 文本主色：#1F2D3D
- 文本次色：#556173
- 边框色：#E6EAF0

### 2.2 班次色

- 早班：#FFD166
- 中班：#06D6A0
- 晚班：#118AB2
- 值班领导标签：#F08A5D
- 冲突高亮：#DC3545

### 2.3 颜色使用原则

- 主按钮、活跃状态使用主色 #0A63D8。
- 次要行动使用次色 #17A2B8 或蓝灰色。
- 成功/警告/失败状态保持统一色彩含义。
- 重要提示同时使用图标和色彩，避免单一依赖颜色区分。
- 背景与文本对比度需满足可访问性要求，正文文本与背景对比度 >= 4.5:1。

### 2.4 字体与字号

- 基准字体：系统默认或 `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial`。
- 标题：H1 24px / 600；H2 20px / 600；H3 16px / 600。
- 正文：14px / 400。
- 辅助文案：12px / 400。
- 行高：正文 1.5；标题 1.25。

---

## 3. 布局与排版规范

### 3.1 栅格系统

- 基础栅格：12 列布局。
- 间距：8px 基础单位，常用间距 8、16、24、32、40。
- 大屏容器宽度：1200px；桌面容器宽度：1000px。
- 栅格 gutter（列间距）：16px。

### 3.2 页面布局规则

- 顶栏高度：56px。
- 左侧侧边栏宽度：240px，折叠后 64px。
- 卡片圆角：6px。
- 卡片内边距：16px~24px。
- 主内容区域采用卡片式布局，分区明确。

### 3.3 响应式布局

- 大屏：≥ 1440px，三栏或两栏布局。
- 桌面：≥ 1024px，侧边栏 + 主内容双栏。
- 平板：768px ~ 1023px，侧边栏折叠为顶部导航或抽屉模式。
- 移动：≤ 767px，底部 Tab 导航和单栏内容。

### 3.4 可访问性建议

- 按钮与控件键盘可达，Tab 顺序合理。
- 提供 `aria-label`、`aria-live` 用于动态冲突提示。
- 色彩区分同时提供图标或文本，避免仅靠颜色传达信息。
- 支持大文本模式或字体放大。

---

## 4. 组件规范

### 4.1 关键组件

#### Topbar
- 内容：Logo、系统名、全局搜索（可选）、未读消息角标、用户头像与下拉菜单。
- 高度：56px。
- 行为：消息图标悬浮显示最新 3 条；用户下拉包含“个人信息 / 切换组织 / 退出登录”。

#### Sidebar
- 支持折叠、树形菜单、图标提示。
- 当前激活项左侧有 4px 主色条。

#### Card
- 背景：白色。
- 圆角：6px。
- 阴影：0 1px 4px rgba(31,45,61,0.06)。
- 标题行：16px 加粗。

#### Button
- 主要按钮：主色、白字、36px 高、圆角 6px。
- 次要按钮：描边、透明背景。
- 危险按钮：红色。
- 禁用态：#CED6E3，不可交互。

#### 表单与选择器
- 控件高度：36px。
- 下拉支持搜索与分页。
- 日期选择支持范围与单日选择，时间选择用于班次起止时点。

#### 日历与排班格
- 使用月/周视图混合布局。
- 单元格最小高度 80px。
- 班次以色块展示，可拖拽。
- 值班领导小标签放置在色块上方。
- 冲突用红色边框和警告图标提示。

#### 模态对话框
- 默认宽度 640px，移动端 100% 宽。
- 关键确认如发布、撤回、强制放行使用模态。

---

## 5. 页面结构与关键页面设计

### 5.1 全局结构

- 顶部导航：Logo、用户信息、消息、搜索。
- 左侧菜单：模块分组，包括首页、组织与人员、班次模板、约束规则、自动排班、排班日历、调班管理、消息中心、公告管理、系统设置。
- 面包屑导航：当前页面层级说明。
- 主内容区：控制台式布局，必要时右侧展示辅助信息。

### 5.2 角色视图与权限差异

#### 系统管理员
- 可访问全部模块。
- 重点：组织架构、人员管理、角色权限、系统配置。
- 入口页展示总体数据概览：组织数量、人员总数、排班规则状态、待审批调班。

#### 排班管理员
- 重点：班次模板、约束规则、自动排班、排班日历、调班审批。
- 入口页侧重：本期排班进度、自动排班结果、校验警告、待处理调班申请。

#### 组长
- 重点：本组排班查看、调班申请、消息提醒。
- 入口页侧重：本组排班统计、待确认调班、公告通知。

#### 普通队员
- 重点：个人排班查看、调班申请、消息中心。
- 移动端优先：个人排班、调班申请、消息、公告。

### 5.3 关键页面设计

#### 首页看板
- 布局：两列，左侧 2/3 主要卡片，右侧 1/3 快捷入口与通知。
- 模块：排班概览、快捷操作、今日值班、最近公告。
- 风险预警：约束冲突数量、已发布排班是否需撤回。
- 交互：点击冲突数跳转排班日历并高亮冲突项。

#### 组织与人员管理
- 左侧组织架构树，右侧人员列表与组织详情。
- 人员表格列：姓名、工号、岗位、角色、状态、可用岗位、操作。
- 支持搜索、筛选、特殊标签显示。
- 人员详情侧栏展示个人信息、角色权限、标签、排班可用状态。

#### 班次模板管理
- 采用列表 + 详情编辑面板布局。
- 字段：班次名称、起始时间、结束时间、时长、颜色、领导人数范围、人员人数范围、适用日期、启用开关。
- 交互：颜色标签区分，复制模板，跨夜班自动计算时长，启用状态立即生效。

#### 约束规则配置
- 左侧规则列表，右侧规则详情编辑。
- 支持启用/禁用、优先级拖拽、适用范围选择。
- 规则类型包括连续工作上限、最少休息、班次间隔、夜班休息、每日最大班次、周工作时长、节假日模式、周末差异化。
- 编辑时展示规则预览与影响说明。

#### 自动排班
- 页面分区：左侧参数设置，右侧结果预览。
- 设置步骤：选择周期、班次模板、排班范围、约束规则、人员范围，点击生成。
- 结果展示：日历/表格视图、冲突高亮、工作时长分布、夜班均衡、公平性评分。
- 交互：生成后展示冲突统计、建议调整项，一键进入手动微调。

#### 排班日历
- 视图模式：月视图、周视图、人员视图。
- 日期格展示班次色块、值班领导、值班人员。
- 超出内容显示“+X 更多”展开。
- 冲突日期红色边框，悬浮提示违规规则。
- 操作：单击详情、拖拽人员、右键快速操作、发布/撤回/导出/校验。

#### 手动微调
- 支持拖拽排班、点击班次修改、移除人员。
- 侧边栏展示操作说明、违规提示、人员排班详情。
- 支持撤销/重做、保存草稿。
- 实时提示当前操作是否违反规则。

#### 约束校验与发布
- 校验结果分区：已通过、警告、失败。
- 允许标记豁免并填写原因。
- 发布前必须校验，发布后排班锁定。
- 已发布展现状态与撤回按钮。

#### 调班管理
- 支持指定换班与开放换班。
- 申请表单：调班类型、我的班次、换班对象、对方班次、申请原因。
- 审批页展示流程状态、审批操作按钮。
- 记录页支持筛选查询与详情对比。
- 流程提示：对方确认、审批、完成、撤回。

#### 消息中心与公告
- 消息分类 tabs：排班通知、调班通知、审批提醒、公告。
- 列表显示时间倒序、未读角标。
- 点击消息跳转相关页面。
- 公告支持发布、撤回、编辑、范围选择。

---

## 6. 移动端设计

### 6.1 移动端入口

- 底部 Tab 导航：首页、排班、调班、消息、我的。
- 首页展示：今日值班、本周排班、待处理调班、未读消息。
- 移动端优先支持个人排班查看、调班申请、消息通知、公告阅读。

### 6.2 移动页面布局

- 单栏内容，卡片式列表展示。
- 底部固定按钮或悬浮操作。
- 关键页面：我的排班、调班申请、开放认领、消息中心、个人中心。

### 6.3 移动页面组件树

#### MobileHomePage
- TabBar: BottomNav
  - Home
  - Schedule
  - Swap
  - Message
  - Mine
- HomeCardList
  - TodayDutyCard
  - WeeklySummaryCard
  - PendingSwapCard
  - UnreadMessageCard

#### MobileSchedulePage
- Header: DateNavBar
- DayList
  - DayCard
    - ShiftItem
      - ShiftType
      - LeaderName
      - StaffNames
    - ConflictBadge

#### MobileSwapFormPage
- Form: SwapForm
  - SwapTypeSwitch
  - MyShiftSelect
  - TargetStaffSelect
  - TargetShiftSelect
  - ReasonInput
  - SubmitSwapButton

#### MobileOpenSwapPage
- OpenSwapCardList
  - OpenSwapCard
    - ShiftInfo
    - Applicant
    - Status
    - ClaimButton

#### MobileMessagePage
- MessageFilterTabs
- MobileMessageList
  - MessageItem
    - Title
    - Summary
    - Timestamp
    - UnreadBadge
- MobileMessageDetail
  - Content
  - ViewRelated

#### MobileProfilePage
- UserInfoCard
- ActionList
  - MySchedule
  - MyRequests
  - Settings
  - Logout

---

## 7. 页面组件树

### 7.1 登录页

- Page: LoginPage
  - LoginLayout
    - Header: Logo + 系统名
    - LoginCard
      - LoginForm
        - UsernameInput
        - PasswordInput
        - RememberMeCheckbox
        - LoginButton
      - VersionInfo
    - AuthNote

### 7.2 首页看板

- Page: DashboardPage
  - MainLayout
    - Topbar
    - SidebarNav
    - DashboardContent
      - ScheduleOverviewCard
      - ShortcutCard
      - TodayDutyCard
      - PendingTasksCard
      - RecentNoticeCard
      - OperationLogCard

### 7.3 组织与人员管理

- Page: OrgStaffPage
  - SplitLayout
    - OrgTreePanel
      - OrganizationTree
      - OrgActions
        - AddOrgButton
        - RefreshOrgButton
    - OrgStaffPanel
      - OrgSummaryCard
      - OrgStaffToolbar
        - SearchInput
        - FilterTags
        - AddStaffButton
        - ImportStaffButton
      - StaffTable
      - StaffDetailDrawer

### 7.4 班次模板管理

- Page: ShiftTemplatePage
  - SplitLayout
    - TemplateListPanel
    - TemplateEditPanel

### 7.5 约束规则配置

- Page: ConstraintRulePage
  - SplitLayout
    - RuleListPanel
    - RuleDetailPanel

### 7.6 自动排班

- Page: AutoSchedulePage
  - SplitLayout
    - ParameterPanel
    - PreviewPanel

### 7.7 排班日历

- Page: ScheduleCalendarPage
  - CalendarLayout
    - CalendarToolbar
    - CalendarGrid
    - ShiftDetailDrawer

### 7.8 手动微调

- Page: ManualAdjustPage
  - TwoColumnLayout
    - StaffPoolPanel
    - AdjustCalendarPanel
    - OperationInfoPanel

### 7.9 约束校验与发布

- Page: ValidationPublishPage
  - ValidationSummaryCard
  - ValidationResultTabs
  - ValidationList
  - ActionPanel
  - PublishConfirmDialog

### 7.10 调班管理

- Page: SwapManagementPage
  - TabbedPage
  - SwapToolbar
  - SwapRequestTable
  - SwapDetailPanel
  - SwapRequestForm

### 7.11 消息中心与公告

- Page: MessageNoticePage
  - TabbedPage
  - MessageToolbar
  - MessageList
  - MessageDetailDrawer
  - AnnouncementsSection

### 7.12 我的与设置

- Page: ProfilePage
  - UserProfileCard
  - OrganizationSwitcher
  - QuickLinks
  - LogoutButton

---

## 8. 页面组件字段级 Props / Event 映射

### 8.1 通用组件映射

#### Topbar
- props:
  - userName: string
  - unreadCount: number
  - navItems: Array<{ label: string; path: string; icon?: string }>
- events:
  - onSearch(query: string)
  - onNotificationClick()
  - onUserMenuSelect(action: string)

#### Sidebar
- props:
  - collapsed: boolean
  - menuItems: Array<{ label: string; icon: string; path: string; badge?: number }>
- events:
  - onToggleCollapse()
  - onMenuSelect(path: string)

#### Card
- props:
  - title: string
  - footer?: string
  - status?: 'normal' | 'warning' | 'error' | 'success'
- events:
  - onClick?()

#### Button
- props:
  - type: 'primary' | 'secondary' | 'danger' | 'text'
  - disabled?: boolean
  - loading?: boolean
  - icon?: string
- events:
  - onClick()

#### Table
- props:
  - columns: Array<{ key: string; title: string; width?: number; sortable?: boolean; align?: 'left' | 'center' | 'right' }>
  - dataSource: Array<Record<string, any>>
  - rowKey: string
  - pagination?: { current: number; pageSize: number; total: number }
- events:
  - onRowClick(record: any)
  - onSortChange(sorter: { column: string; order: 'ascend' | 'descend' })
  - onPageChange(page: number, pageSize: number)

### 8.2 页面级组件映射

#### OrgTreePanel
- props:
  - treeData: Array<{ id: string; title: string; children?: any[]; disabled?: boolean }>
  - selectedKey: string
- events:
  - onSelect(key: string)
  - onExpand(keys: string[])

#### StaffTable
- props:
  - staffList: Array<{ id: string; name: string; employeeNo: string; post: string; role: string; status: string; tags: string[] }>
  - columns: TableColumn[]
- events:
  - onEdit(record: any)
  - onDelete(record: any)
  - onSelect(record: any)

#### TemplateForm
- props:
  - value: {
      name: string;
      startTime: string;
      endTime: string;
      color: string;
      leaderMin: number;
      leaderMax: number;
      staffMin: number;
      staffMax: number;
      days: string[];
      enabled: boolean;
    }
  - loading: boolean
- events:
  - onChange(value)
  - onSubmit(value)
  - onCancel()

#### RuleForm
- props:
  - value: {
      name: string;
      type: string;
      params: Record<string, any>;
      scope: string;
      enabled: boolean;
    }
  - ruleTypes: Array<{ value: string; label: string }>
- events:
  - onChange(value)
  - onSave(value)
  - onCancel()

#### AutoSchedulePage
- props:
  - scheduleRange: { start: string; end: string }
  - selectedTemplates: string[]
  - selectedScope: string
  - selectedStaff: string[]
  - selectedRules: string[]
  - generating: boolean
- events:
  - onRangeChange(range)
  - onTemplateChange(selected)
  - onScopeChange(value)
  - onStaffChange(value)
  - onRulesChange(value)
  - onGenerate()

#### ScheduleCalendar
- props:
  - viewMode: 'month' | 'week' | 'staff'
  - scheduleData: Array<any>
  - filters: { organization?: string; staff?: string; post?: string }
  - selectedDate?: string
- events:
  - onViewModeChange(mode)
  - onDateSelect(date)
  - onShiftClick(shift)
  - onFilterChange(filters)
  - onPublish()
  - onRecall()
  - onExport()
  - onValidate()

#### ManualAdjustPage
- props:
  - staffPool: Array<any>
  - scheduleDraft: Array<any>
  - selectedStaffId?: string
  - conflictHints: Array<string>
- events:
  - onStaffSelect(staffId)
  - onShiftDrop(payload)
  - onUndo()
  - onRedo()
  - onSaveDraft()
  - onConfirm()

#### SwapRequestForm
- props:
  - value: { type: string; myShiftId: string; targetStaffId: string; targetShiftId: string; reason: string }
  - staffOptions: Array<any>
  - shiftOptions: Array<any>
  - loading: boolean
- events:
  - onChange(value)
  - onSubmit(value)
  - onCancel()

#### MessageList
- props:
  - messages: Array<{ id: string; title: string; summary: string; time: string; unread: boolean; type: string }>
- events:
  - onItemClick(messageId)
  - onMarkAllRead()

---

## 9. 交互文案规范

### 9.1 按钮文案规范

| 类型 | 文案示例 | 说明 |
|------|---------|------|
| 主要操作 | 保存、提交、确认、生成、发布、发起申请、认领 | 关键主流程按钮 |
| 次要操作 | 取消、返回、关闭、编辑、导出、撤回、重新校验 | 辅助操作 |
| 危险操作 | 删除、强制发布、强制放行、拒绝、撤销 | 破坏性操作 |
| 文本按钮 | 查看详情、全部已读、标记为已读、继续 | 轻量操作 |
| 切换/选择 | 月视图、周视图、列表视图、按组织、按人员 | 视图/筛选切换 |

#### 常用按钮
- 登录
- 新建
- 保存
- 生成排班
- 进入微调
- 一键校验
- 确认发布
- 撤回排班
- 立即认领
- 申请换班
- 提交申请
- 同意
- 拒绝
- 标记为已读
- 发布公告
- 重新运行

### 9.2 交互提示文案

#### 成功提示
- 操作成功
- 已保存
- 发布成功
- 提交成功
- 认领成功
- 撤回成功
- 标记成功

#### 错误提示
- 操作失败，请重试
- 网络异常，请稍后再试
- 数据加载失败，请刷新页面
- 当前排班存在冲突，无法执行该操作
- 请选择排班周期后再生成
- 请选择至少一个班次模板
- 请选择排班范围
- 请选择人员范围

#### 警告提示
- 当前操作可能违反排班规则
- 已检测到潜在冲突，是否继续？
- 该操作会覆盖当前排班，请确认
- 该申请可能需要审批，继续提交？
- 变更后可能影响其他人员排班

#### 说明提示
- 该规则修改后将用于下一次自动排班
- 已发布排班仅能通过调班流程变更
- 关闭审批后，换班申请将直接生效
- 已停用人员不会参与自动排班
- 跨夜班时长将自动计算

### 9.3 弹窗与确认文案

#### 发布确认
- 标题：确认发布排班表？
- 内容：发布后排班将被锁定，变更需通过调班流程。
- 按钮：确认发布 / 取消

#### 撤回确认
- 标题：确认撤回排班？
- 内容：撤回后排班将变为草稿，相关人员将收到通知。
- 按钮：确认撤回 / 取消

#### 强制放行
- 标题：是否继续执行该操作？
- 内容：当前操作会违反排班规则，是否填写豁免原因后继续？
- 按钮：继续并填写理由 / 取消

#### 删除/停用
- 标题：确认删除？
- 内容：删除后数据无法恢复，请慎重操作。
- 按钮：删除 / 取消

### 9.4 表单字段文案

#### 登录页
- 账号
- 密码
- 记住我
- 登录

#### 组织与人员管理
- 组织名称
- 上级组织
- 组织状态
- 人员姓名
- 工号
- 联系方式
- 所属组织
- 角色
- 状态
- 可用岗位
- 特殊标签

#### 班次模板
- 班次名称
- 起始时间
- 结束时间
- 班次时长
- 颜色标识
- 值班领导最少人数
- 值班领导最多人数
- 值班人员最少人数
- 值班人员最多人数
- 适用日期
- 启用/停用

#### 自动排班
- 排班周期
- 班次模板
- 排班范围
- 人员范围
- 约束规则
- 一键生成
- 生成报告

#### 调班申请
- 调班类型
- 我的班次
- 换班对象
- 对方班次
- 申请原因
- 提交申请
- 认领申请

### 9.5 状态标签与流程文案

#### 排班状态
- 草稿
- 已发布
- 已撤回
- 未发布
- 待发布

#### 校验状态
- 已通过
- 警告
- 失败
- 待校验
- 已校验

#### 调班状态
- 待确认
- 待审批
- 已通过
- 已拒绝
- 已完成
- 已撤回

#### 消息状态
- 未读
- 已读
- 系统消息
- 审批提醒
- 调班通知
- 公告

### 9.6 移动端文案

#### 底部导航
- 首页
- 排班
- 调班
- 消息
- 我的

#### 移动卡片文案
- 今日值班
- 本周排班
- 待处理调班
- 未读消息
- 我的申请

#### 移动提示
- 请选择需调整的班次
- 请填写申请原因
- 认领成功，请等待审批
- 查看排班详情
- 已更新个人排班

### 9.7 文案风格准则与禁用词

- 明确、简洁、可操作。
- 使用动词开头的按钮文案。
- 保持一致性，同一类场景使用同一套词汇。
- 避免模糊词，如“进行”“处理”“操作”。
- 避免双重否定或复杂表达。
- 错误提示要说明问题与下一步。
- 用词正式但不口语化。
- 状态文案优先使用“已 + 动词”或“待 + 名词”。
- 警告与确认使用“是否”句式并给出明确后果。

#### 禁用词列表
- 进行
- 处理
- 操作
- 事项
- 这个
- 那个
- 可能
- 目标
- 执行
- 建议改为

---

## 10. 交互错误流说明

### 10.1 自动排班错误流

1. 用户点击“生成排班”。
2. 前端校验必填项：排班周期、班次模板、排班范围、人员范围。
   - 若校验失败，展示提示： “请先选择排班周期” / “请至少选择一个班次模板”。
3. 参数完整后发送请求。
4. 后端返回失败：
   - 网络异常： “网络异常，请稍后再试。”
   - 参数缺失： “请选择排班范围后再生成。”
   - 算法失败或冲突过多： “当前排班存在冲突，无法生成。请调整规则或人员范围。”
5. 修改参数后按钮恢复可点击。

### 10.2 手动微调错误流

1. 用户拖拽人员或点击班次变更。
2. 前端快速校验：每日最多 1 班、最少间隔、发布锁定等。
   - 强制违规：阻止落子并提示 “该操作会违反‘每人每天最多1个班’规则，请调整。”
   - 建议违规：允许继续并提示 “当前操作可能违反‘连续工作上限’，是否继续？”
3. 若后端校验失败，回滚变更并展示对话框。
4. 变更成功后显示 toast “排班调整已保存。”

### 10.3 约束校验错误流

1. 用户点击“一键校验”。
2. 后端返回结果：
   - 通过：显示“已通过”列表，启用“确认发布”。
   - 警告：显示“警告”列表，提供“标记豁免”。
   - 失败：显示“失败”列表，提示“请返回微调修改。”
3. 标记豁免时要求填写原因。
   - 未填写： “请填写豁免原因后继续。”
   - 已填写：返回校验页面并更新状态。

### 10.4 发布与撤回错误流

1. 用户点击“确认发布”。
2. 若未校验，提示“尚未执行校验，请先校验后发布。”
3. 若校验失败，提示“当前排班存在失败项，无法发布。”
4. 发布成功： “发布成功，系统已通知相关人员。”
5. 发布失败： “发布失败，请重试。”

1. 用户点击“撤回排班”。
2. 弹窗说明“撤回后排班将变为草稿”。
3. 撤回成功： “撤回成功，排班已恢复为草稿状态。”
4. 撤回失败： “撤回失败，请稍后重试。”

### 10.5 调班申请错误流

1. 用户提交调班申请。
2. 前端校验必填：调班类型、我的班次、申请原因。
   - 若缺失：提示“请填写申请原因”。
3. 后端返回失败：
   - 申请类型错误： “请选择有效的调班类型。”
   - 班次不可用： “所选班次已被占用，请重新选择。”
   - 审批配置问题： “当前审批规则不允许提交该申请。”
4. 提交成功： “申请提交成功，等待对方确认。”

### 10.6 消息与公告错误流

1. 用户点击“标记为已读”或“发布公告”。
2. 网络异常： “网络异常，操作未完成，请重试。”
3. 目标消息/公告已失效： “该消息已失效，请刷新页面。”
4. 操作成功： “操作成功”。

---

## 11. 操作流程与逻辑

### 11.1 自动排班流程

- 页面入口：自动排班。
- 用户步骤：选择周期 → 选择班次模板 → 选择排班范围 → 选择约束规则 → 点击生成。
- 系统行为：前端校验必填项 → 请求后端生成 → 展示结果与冲突摘要 → 提供进入手动微调与校验入口。
- 关键节点：生成前必须校验参数；生成后如有冲突应高亮提示；可直接进入微调或保存草稿。

### 11.2 手动微调流程

- 页面入口：排班日历或自动排班结果。
- 用户步骤：选中班次 → 拖拽人员/修改人员 → 查看实时提示 → 保存或撤销。
- 系统行为：变更前端即时校验规则；强制违规阻止操作；建议违规允许继续并记录豁免；变更成功后更新草稿。

### 11.3 约束校验与发布流程

- 页面入口：校验发布。
- 用户步骤：点击一键校验 → 处理警告/失败项 → 点击确认发布。
- 系统行为：校验结果分为通过/警告/失败；失败项必须修正或标记豁免后才可发布；发布后排班锁定，仅通过调班流程调整。

### 11.4 调班申请与审批流程

- 调班模式：指定换班、开放认领。
- 用户流程：
  - 指定换班：发起人选择自己班次与对方班次，提交后等待对方确认。
  - 开放认领：发起人发布替班申请，候选人员认领后进入审批。
- 审批逻辑：
  - 审批开关 ON：对方确认后进入管理员审批。
  - 审批开关 OFF：对方确认即可生效。
- 关键校验：认领前检测班次可用性；执行前检测冲突与规则违背；强制放行需填写豁免原因并记录日志。

### 11.5 消息与通知逻辑

- 触发事件：排班发布、排班修改、调班申请、审批结果、公告发布。
- 消息类型：排班通知、调班通知、审批提醒、公告。
- 消息行为：未读角标计数、点击跳转相关页面、可标记已读/全部已读。
- 失败处理：网络异常时提示“消息发送失败，请重试”。

---

## 12. 交付建议

- 高保真线框（Figma / Sketch）：覆盖首页、自动排班页、日历页、调班详情页。
- 组件库实现：基于设计 tokens 实现 Button / Card / Modal / Calendar / Form / Tag。
- API 交互契约文档：接口示例、参数、错误码。

---

## 13. 附：交互示例文本

- 拖拽违规提示："⚠ 张三连续上班已达 5 天，继续操作将违反'连续工作上限'规则。要继续并记录豁免吗？"
- 发布确认弹窗："确认发布 2026 年 6 月排班表？发布后排班将被锁定，变更需通过调班流程。"
