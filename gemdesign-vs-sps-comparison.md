# GemDesign 原型 × SPS-System 综合样式对比分析报告

> **分析对象：**
> - **GemDesign 原型** (appuuid: 2072848344459247616) — 7 个页面
> - **SPS-System 当前项目** — 10+ 个页面
>
> **分析目的：** 对比两套样式体系，识别可借鉴点、差异点和融合建议
> **分析日期：** 2026-07-05

---

## 一、设计语言对比总览

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **设计风格** | 新野兽派 (Neo-Brutalism) | 新野兽派 (Neo-Brutalism) |
| **设计一致性** | 原型内高度统一 | 全局一致（来自同一套设计系统） |
| **配色方案** | 6 色 neo 变量系统 | 10+ 色硬编码系统 |
| **字体** | Space Grotesk (Google Fonts CDN) | Space Grotesk (CDN 已注释，fallback 到系统字体) |
| **边框粗细** | 3px-6px 黑色边框 | 2px-4px 黑色边框 |
| **阴影** | 4px-16px 四级硬阴影 | 3px-10px 三级硬阴影 |
| **圆角** | 0-4px | 2-4px |
| **CSS 方案** | Tailwind CSS v3 (CDN) | SCSS + Scoped CSS + global.scss 全局覆盖 |
| **组件库** | 无（纯 HTML + Tailwind 手写） | Element Plus ^2.14.0 |
| **构建工具** | 原型 HTML | Vite 8 + Vue SFC |
| **响应式** | Tailwind 断点 (sm/md/lg/xl) | 手动 media query (768px/1024px/1200px) |

**结论：** 两者同源设计系统，风格高度一致。SPS-System 是 GemDesign 原型的工程化落地版本。

---

## 二、配色方案深度对比

### 2.1 GemDesign 原型配色

```
neo.bg      #FFFDF5  奶油背景
neo.black   #000000  结构黑
neo.accent  #FF6B6B  热红（注意：这是偏粉的红色）
neo.secondary #FFD93D 亮黄
neo.muted   #C4B5FD  柔紫
neo.white   #FFFFFF  纯白
```

### 2.2 SPS-System 当前配色

```
主蓝        #3B82F6  品牌主色（原型无此色）
背景暖黄    #FFFDF5  ← 完全一致
纯白        #FFFFFF  ← 完全一致
纯黑        #000000  ← 完全一致
亮黄        #FFD93D  ← 完全一致
成功绿      #10B981  （原型用紫色 muted 替代）
危险红      #EF4444  （原型用热红 #FF6B6B）
紫罗兰      #8B5CF6  （原型柔紫 #C4B5FD 偏淡）
青色        #06B6D4  （原型无）
浅红        #FF6B6B  （原型 neo.accent）
```

### 2.3 配色差异分析

| 差异点 | 原型 | SPS-System | 原因 |
|--------|------|-----------|------|
| **主品牌色** | 无明确主色 | `#3B82F6` 蓝色 | 企业级应用需要品牌色 |
| **成功色** | 用紫色 muted | `#10B981` 绿色 | 语义化需要（成功=绿） |
| **危险色** | `#FF6B6B` 热红 | `#EF4444` 标准红 | Element Plus 默认色 |
| **警告色** | `#FFD93D` 亮黄 | `#FFD93D` 亮黄 | 一致 |
| **Info 色** | 无 | `#06B6D4` 青色 | 补充了 info 语义 |

**建议：** 原型配色更"艺术化"，SPS-System 配色更"业务化"。原型缺少语义色（成功/警告/危险），这是 SPS-System 的改进方向。

---

## 三、组件样式对比

### 3.1 按钮系统

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **基础样式** | `.neo-btn` Tailwind 类 | `.btn-neo-*` SCSS 类 + EP 覆盖 |
| **高度** | `h-12` (48px) | 继承 EP 默认 + 自定义 |
| **阴影等级** | `shadow-neo-sm` (4px) | `4px 4px 0px 0px #000` |
| **Hover 效果** | `translateY(-4px)` + 阴影增大 | `translate(-2px,-2px)` + 阴影增大 |
| **Active 效果** | `translate(2px,2px)` + 阴影消失 | `translate(2px,2px)` + 阴影减小 |
| **变体数量** | 3 种（primary/secondary/基础） | 8 种（primary/danger/warning/success/info/ghost/accent/sm） |
| **图标按钮** | `p-2 h-auto` 缩小组合 | `.neo-icon-btn` 专用类 |

**SPS-System 优势：** 按钮变体更丰富，覆盖了业务场景的所有需求。

### 3.2 卡片系统

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **边框** | `border-4` (4px) | `border-3` (3px) |
| **阴影** | `shadow-neo-md` (8px) | `6px 6px 0px 0px` |
| **Padding** | `p-6` (24px) | 16-24px 不等 |
| **Hover** | `translateY(-4px)` + `shadow-neo-lg` | `translateY(-1px)` + `8px 8px` |
| **圆角** | 4px | 4px |

**差异：** 原型卡片边框更粗（4px vs 3px），阴影更大（8px vs 6px），视觉冲击力更强。SPS-System 相对克制。

### 3.3 输入框

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **高度** | `h-14` (56px) | 32px (EP 默认) / 56px (.neo-input) |
| **边框** | `border-4` (4px) | 3px (EP 默认) / 4px (.neo-input) |
| **Focus 效果** | `bg-neo-secondary` 黄底 | `box-shadow: 4px 4px #3B82F6` 蓝框 |
| **字体** | `font-bold` | `font-weight: 600-700` |

**差异：** 原型聚焦时变黄色背景（与原型一致），SPS-System 聚焦时蓝色阴影（更符合品牌色）。

### 3.4 徽章/标签

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **边框** | `border-2` (2px) | `border-2` (2px) |
| **阴影** | `2px 2px 0px 0px` | `2px 2px 0px 0px` |
| **Padding** | `px-3 py-1` | 继承 EP `.el-tag` |
| **圆角** | 0 (无 border-radius) | 2px |

**相似度高。**

### 3.5 弹窗/对话框

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **遮罩** | `bg-neo-black/70` (70%) | `rgba(0,0,0,0.5)` + blur(2px) |
| **边框** | `border-6` (6px) | `border-3` (3px) |
| **阴影** | `shadow-neo-lg` (12px) | `8px 8px 0px 0px` |
| **最大宽度** | `max-w-2xl` (672px) | 460px-680px 不等 |
| **标题** | `neo-h3` (28-36px) | `font-weight: 900` |
| **关闭按钮** | `neo-btn` 样式 | 自定义 neo 风格 |

**差异：** 原型弹窗更"重"（6px 边框 + 12px 阴影），SPS-System 更"轻"。原型遮罩不透明，SPS-System 加了模糊效果。

---

## 四、布局结构对比

### 4.1 导航栏

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **高度** | `h-18` (72px) | 64px |
| **边框** | `border-b-4` (4px) | `border-bottom: 3px` |
| **导航项** | 内联 `<a>` + `border-3` | `.menu-item` + `border: 3px` |
| **激活态** | `bg-neo-secondary` 黄底 | `background: #3B82F6` 蓝底 |
| **Logo 区** | `w-10 h-10` 图标块 | `fa-calendar-alt` 图标 + 文字 |
| **移动端** | modal-mask 覆盖层 | 侧边栏折叠 (isCollapse) |

**差异：** 原型导航栏更高（72px vs 64px），激活态用黄色（与原型一致），SPS-System 用蓝色（品牌色）。原型有移动端覆盖层菜单，SPS-System 只有侧边栏折叠。

### 4.2 页面标题区

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **标题样式** | `neo-h2` (48-96px!) | `font-size: 22px, font-weight: 900` |
| **图标装饰** | `w-12 h-12` 彩色方块 | `w-48 h-48` 图标块 (StaffView) |
| **描述文字** | `text-lg font-medium` | `font-size: 13px, color: #666` |
| **布局** | `flex flex-col gap-4` | `flex flex-col gap-6` |

**重大差异：** 原型标题字号极大（`text-4xl md:text-6xl` = 36-60px），而 SPS-System 控制在 22px。原型适合视觉冲击，SPS-System 更适合长时间阅读。

### 4.3 统计卡片

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **布局** | `grid auto-fit` | `grid 4列` / `repeat(4, 1fr)` |
| **数字大小** | `text-4xl` (56px) | `font-size: 36px` |
| **图标** | `text-2xl` 彩色图标 | `font-size: 24px` 彩色图标 |
| **趋势指示** | `fa-arrow-up/down` + 百分比 | 有但样式略有不同 |

**相似度较高。**

### 4.4 表格

| 维度 | GemDesign 原型 | SPS-System 当前项目 |
|------|---------------|-------------------|
| **表头背景** | `bg-neo-secondary` 黄色 | `#FFFDF5` 奶油色 |
| **表头文字** | `font-black uppercase` | `font-weight: 700` |
| **行边框** | `border-b-2` | `border-bottom: 2px solid #E6EAF0` |
| **列分隔** | `border-r-2` | 部分表格有 |
| **Hover** | `bg-neo-bg` 奶油色 | `#FFFDF5` |
| **组件** | 手写 `<table>` | Element Plus `el-table` |

**差异：** 原型表头用黄色背景（更醒目），SPS-System 用奶油色（更柔和）。原型手写 table，SPS-System 用 el-table 覆盖。

---

## 五、GemDesign 原型独有但 SPS-System 缺失的样式

### 5.1 可借鉴的新样式

以下样式在原型的某些页面中出现，但 SPS-System 尚未实现：

#### 1. 导出卡片（快速导出区域）
```
原型位置: export_center 页面
特征: 4 列卡片网格，每个卡片含图标块 + 标题 + 描述 + 按钮
hover: 图标块 rotate(3deg) 旋转效果
```
**应用价值：** ⭐⭐⭐⭐⭐ 适合 SPS-System 的 Dashboard 快捷操作区

#### 2. 权限卡片选择（Radio Card）
```
原型位置: StaffManagePage 权限配置弹窗
特征: 每个权限级别是一个独立 neo-card，内含 radio + 标题 + 徽章 + 描述
```
**应用价值：** ⭐⭐⭐⭐ 适合 SPS-System 的角色选择场景

#### 3. 文件拖拽上传区域
```
原型位置: typesetting_param_config 导入弹窗
特征: 虚线边框大区域 + 上传图标 + 提示文字 + 选择文件按钮
```
**应用价值：** ⭐⭐⭐⭐⭐ 适合 SPS-System 的排班导入功能

#### 4. 警告提示卡片
```
原型位置: ScheduleCalendarPage 智能排班确认弹窗
特征: 黄色背景 + 三角警告图标 + 文字说明的一体化卡片
```
**应用价值：** ⭐⭐⭐⭐⭐ 适合 SPS-System 的各种确认提示场景

#### 5. 进度条
```
原型位置: export_center 导出进度弹窗
特征: 6px 高轨道 + 黄色填充 + transition 动画
```
**应用价值：** ⭐⭐⭐⭐ 适合 SPS-System 的导出/导入进度展示

#### 6. 大图标头像（表格内）
```
原型位置: StaffManagePage 员工列表
特征: 48x48 彩色方块 + 首字母 + 3px 黑边框
```
**应用价值：** ⭐⭐⭐⭐⭐ SPS-System 已有类似实现（staff-avatar），但原型版本更大更醒目

#### 7. 全屏预览弹窗
```
原型位置: typesetting_workbench
特征: max-w-5xl 超大宽度弹窗，用于沉浸式预览
```
**应用价值：** ⭐⭐⭐ 适合 SPS-System 的排班详情全屏查看

---

### 5.2 原型独有的装饰特性

#### 1. 背景纹理
```css
/* 半调波点 */
.bg-pattern-dots {
  background-image: radial-gradient(#000 1.5px, transparent 1.5px);
  background-size: 20px 20px;
}
/* 网格纹理 */
.bg-pattern-grid {
  background-size: 40px 40px;
  background-image: linear-gradient(...), linear-gradient(...);
}
```
**应用价值：** ⭐⭐ 可作为登录页或特殊页面的装饰背景

#### 2. 文本描边效果
```css
.text-stroke-black {
  -webkit-text-stroke: 2px black;
  color: transparent;
}
```
**应用价值：** ⭐ 适合大标题装饰，业务场景中慎用

#### 3. 旋转动画
```css
.rotate-1 / rotate-2 / rotate-3 (-1/-2/-3)
```
**应用价值：** ⭐⭐ 适合图标 hover 微交互

---

## 六、SPS-System 独有但原型缺失的样式

### 6.1 业务级样式

以下样式在 SPS-System 中存在，但 GemDesign 原型未涉及：

| 样式 | 来源文件 | 说明 |
|------|---------|------|
| **ElMessageBox 自定义** | global.scss:269-446 | emoji 图标 + 自定义按钮，原型使用原生 alert |
| **Day Selector 按钮** | global.scss:905-960 | 自定义星期选择按钮组 |
| **Neo Switch Inline** | global.scss:963-1012 | 自定义开关组件 |
| **Panel Header** | ConstraintView 等 | 左右分栏模式的 .panel-header |
| **Violation Item** | ScheduleCalendarView | 约束校验报告的警告/错误行 |
| **Legend Dot** | ScheduleCalendarView | 班次图例色块 |
| **Tab Bar** | ScheduleCalendarView | 自定义 Tab 栏（非 EP tabs） |
| **Search Input Wrap** | StaffView | 搜索框 + 图标定位 |
| **Pagination Wrapper** | StaffView | 分页信息 + 分页器组合 |
| **System Account Row** | StaffView | 系统账号行特殊样式 |
| **Login Decorator** | LoginView | 登录页装饰性定位元素 |

---

## 七、融合建议矩阵

### 7.1 强烈推荐采纳（高价值，低改动成本）

| 序号 | 借鉴内容 | 目标页面 | 理由 |
|------|---------|---------|------|
| 1 | **导出卡片网格**（图标+按钮组合） | DashboardView 快捷操作区 | 视觉吸引力强，提升 UX |
| 2 | **文件拖拽上传区域** | ScheduleCalendarView 导入功能 | 比原生 file input 友好得多 |
| 3 | **警告提示卡片**（黄色+图标） | 所有确认弹窗 | 统一确认提示样式 |
| 4 | **进度条样式** | ExportDialog | 导出/导入进度可视化 |
| 5 | **权限 Radio Card** | 角色管理页面 | 比纯文字列表更直观 |

### 7.2 推荐采纳（有价值，需适量改动）

| 序号 | 借鉴内容 | 目标页面 | 改动点 |
|------|---------|---------|--------|
| 6 | **表格表头黄色背景** | 所有表格页面 | 修改 global.scss 表头样式 |
| 7 | **更大统计数字**（56px vs 36px） | Dashboard / 统计卡片 | 调整 stat-value 字号 |
| 8 | **图标 hover 旋转** | 导出卡片等 | 添加 transform 动画 |
| 9 | **搜索框聚焦黄底** | 所有搜索框 | 原型已有，SPS-System 已有类似实现 |

### 7.3 可选采纳（视需求而定）

| 序号 | 借鉴内容 | 适用场景 | 注意事项 |
|------|---------|---------|---------|
| 10 | **背景纹理**（波点/网格） | 登录页、空状态页 | 可能干扰业务数据展示 |
| 11 | **文本描边效果** | 大标题装饰 | 仅英文场景可用 |
| 12 | **旋转动画** | 图标微交互 | 避免过度使用 |

### 7.4 不建议采纳

| 序号 | 内容 | 理由 |
|------|------|------|
| 13 | **超大标题字号**（48-96px） | 业务系统中过于夸张，影响信息密度 |
| 14 | **6px 弹窗边框** | 对于企业级应用过于粗重 |
| 15 | **70% 不透明遮罩** | 遮挡太多，影响上下文感知 |

---

## 八、样式统一化建议

### 8.1 引入 SCSS 变量层

当前两个项目都存在**硬编码色值**问题。建议在 SPS-System 中引入变量层：

```scss
// 建议新增: frontend/src/assets/styles/variables.scss
$neo-bg: #FFFDF5;
$neo-black: #000000;
$neo-accent: #FF6B6B;       // 热红（原型 neo.accent）
$neo-yellow: #FFD93D;       // 亮黄（原型 neo.secondary）
$neo-purple: #C4B5FD;       // 柔紫（原型 neo.muted）
$neo-white: #FFFFFF;

$neo-brand: #3B82F6;        // 品牌蓝（SPS-System 独有）
$neo-success: #10B981;      // 成功绿
$neo-danger: #EF4444;       // 危险红
$neo-info: #06B6D4;         // Info 青

// 阴影等级
$neo-shadow-sm: 4px 4px 0px 0px #000000;
$neo-shadow-md: 8px 8px 0px 0px #000000;
$neo-shadow-lg: 12px 12px 0px 0px #000000;
$neo-shadow-xl: 16px 16px 0px 0px #000000;
$neo-shadow-hover: 10px 10px 0px 0px #000000;

// 边框
$neo-border: 3px solid #000000;
$neo-border-thick: 4px solid #000000;
$neo-border-thicker: 6px solid #000000;
```

### 8.2 统一阴影等级

| 等级 | 原型 | SPS-System | 建议统一为 | 用途 |
|------|------|-----------|-----------|------|
| 小 | `4px` | `3px` | `4px` | 按钮、小卡片 |
| 中 | `8px` | `6px` | `8px` | 标准卡片 |
| 大 | `12px` | `8px` | `12px` | 弹窗、大面板 |
| 超大 | `16px` | 无 | `16px` | 特殊强调 |

### 8.3 统一按钮尺寸

| 类型 | 原型 | SPS-System | 建议 |
|------|------|-----------|------|
| 标准按钮高度 | 48px (h-12) | 32-36px (EP 默认) | 统一为 40-44px |
| Neo Input 高度 | 56px (h-14) | 32px / 56px (.neo-input) | 保留两套 |
| 图标按钮 | 48px | 34px (.neo-icon-btn) | 图标按钮保持 34px |

---

## 九、原型页面与 SPS-System 页面映射

| GemDesign 原型页面 | SPS-System 对应页面 | 相似度 | 备注 |
|-------------------|-------------------|--------|------|
| 自动排版工作台 | DashboardView | ⭐⭐ | 功能不同，但布局模式可借鉴 |
| 排班日历 | ScheduleCalendarView | ⭐⭐⭐⭐⭐ | 功能几乎一致，样式可对齐 |
| 考勤数据统计 | DashboardView (统计区) | ⭐⭐⭐ | 统计卡片布局可借鉴 |
| 导出中心 | ExportDialog | ⭐⭐⭐⭐ | 导出卡片网格可直接复用 |
| 员工管理 | StaffView | ⭐⭐⭐⭐⭐ | 功能一致，样式已高度相似 |
| 班次规则配置 | ShiftTemplateView | ⭐⭐⭐⭐⭐ | 功能一致，样式已高度相似 |
| 排版参数配置 | ConstraintView / SystemView | ⭐⭐⭐ | 表单布局可借鉴 |

---

## 十、总结

### 10.1 核心发现

1. **同源设计系统**：两个项目共享 Neo-brutalism 设计语言，风格一致
2. **原型更激进**：GemDesign 原型在边框粗细、阴影大小、字号上更夸张
3. **SPS-System 更克制**：企业级应用需要更好的可读性和信息密度
4. **原型补充了业务场景缺失的样式**：导出卡片、拖拽上传、警告提示、进度条等

### 10.2 最佳融合策略

**取原型的"组件"，保留项目的"克制"**：
- 借鉴原型的卡片网格、上传区域、进度条等组件设计
- 保持 SPS-System 的边框 3px、阴影 4-8px、字号 13-22px
- 统一配色变量，建立 SCSS 变量层
- 原型的大标题风格仅用于装饰性场景

### 10.3 下一步行动建议

1. **立即实施**：导出卡片网格、拖拽上传区域、警告提示卡片、进度条
2. **短期规划**：统一阴影等级、引入 SCSS 变量层
3. **长期优化**：补充背景纹理装饰、图标 hover 微交互

---

*本报告仅供决策参考，不包含代码实施。*
