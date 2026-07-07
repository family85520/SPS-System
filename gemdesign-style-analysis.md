# GemDesign 原型样式分析报告

> **AppUUID:** 2072848344459247616
> **设计主题:** 新野兽派 (Neo-Brutalism) 设计系统
> **页面总数:** 7 个
> **分析日期:** 2026-07-05

---

## 一、设计系统概览

### 1.1 设计语言特征

这是一个采用 **新野兽派 (Neo-Brutalism)** 风格的 UI 系统，核心特征：

- **高对比度**：黑色粗边框 + 明亮色彩
- **硬阴影**：不使用模糊阴影，而是纯黑色偏移阴影（`4px 4px 0px 0px #000`）
- **粗边框**：3px-6px 的黑色实线边框
- **大胆排版**：Space Grotesk 字体，全大写标题，极粗字重
- **互动反馈**：hover 时阴影增大，active 时阴影消失产生"按下"效果

### 1.2 全局配色方案

```
颜色变量       | HEX 值     | 用途
--------------|------------|----------------------------------
neo.bg        | #FFFDF5    | 奶油色背景（画布色）
neo.black     | #000000    | 结构色（边框、文字）
neo.accent    | #FF6B6B    | 热红色（主按钮、强调、危险操作）
neo.secondary | #FFD93D    | 亮黄色（次要按钮、激活态、徽章）
neo.muted     | #C4B5FD    | 柔紫色（信息标签、辅助元素）
neo.white     | #FFFFFF    | 卡片/弹窗背景
```

### 1.3 全局字体

```css
font-family: 'Space Grotesk', sans-serif;
/* 标题使用 font-weight: 900 (font-black)，全大写 uppercase */
```

---

## 二、全局布局样式

### 2.1 顶部导航栏 (Header)

**适用页面：** 所有 7 个页面统一使用

```html
<!-- 固定顶部，高度 72px (h-18)，白色背景，底部粗黑边框 -->
<header class="fixed top-0 left-0 w-full h-18 bg-neo-white border-b-4 border-neo-black z-40">
  <div class="h-full neo-container flex items-center justify-between">
    <!-- Logo 区 -->
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 bg-neo-accent border-3 border-neo-black flex items-center justify-center">
        <i class="fas fa-[icon] text-xl font-bold"></i>
      </div>
      <h1 class="text-xl font-black uppercase tracking-tight">系统名称</h1>
    </div>
    <!-- 桌面导航 -->
    <nav class="hidden md:flex items-center gap-2">
      <!-- 每个导航项: border-3 黑边框，激活态用 bg-neo-secondary 黄色高亮 -->
      <a class="px-4 py-2 font-bold uppercase border-3 border-neo-black bg-neo-white hover:bg-neo-bg transition-colors">
        导航文字
      </a>
    </nav>
    <!-- 移动端汉堡菜单按钮 -->
    <button class="md:hidden neo-btn p-3 h-auto">
      <i class="fas fa-bars text-xl"></i>
    </button>
  </div>
</header>
```

**关键样式要点：**
- Logo 图标块使用 `w-10 h-10` + `bg-neo-accent` + `border-3` + `border-neo-black`
- 导航项默认白底，激活态黄底 (`bg-neo-secondary`)
- 导航项 hover 时变为奶油背景 (`bg-neo-bg`)

### 2.2 主内容区域 (Main)

```html
<main class="pt-18 min-h-screen bg-neo-bg">
  <div class="neo-container py-8">
    <!-- 页面内容 -->
  </div>
</main>
```

- `neo-container` = `max-w-7xl px-4 sm:px-6 lg:px-8`
- 页面标题区通常使用 `flex flex-col gap-4` 布局
- 大标题使用 `neo-h2`，副标题说明使用 `text-lg font-medium`

### 2.3 移动端菜单弹窗

```html
<div class="modal-mask hidden">
  <div class="modal-container p-6">
    <!-- 导航菜单列表 -->
  </div>
</div>
```

---

## 三、核心组件样式

### 3.1 Neo 按钮 (neo-btn)

**三种变体：**

```css
/* 基础按钮 - 白底黑框，硬阴影 */
.neo-btn {
  @apply relative inline-flex items-center justify-center h-12 px-8 py-3
         border-4 border-neo-black bg-neo-white text-neo-black
         font-bold uppercase tracking-wider text-sm
         shadow-neo-sm transition-all duration-100 ease-linear
         hover:-translate-y-1 hover:shadow-neo-md
         active:translate-x-[2px] active:translate-y-[2px] active:shadow-none;
}

/* 主按钮 - 红色背景 */
.neo-btn-primary {
  @apply bg-neo-accent text-neo-black;
}

/* 次要按钮 - 黄色背景 */
.neo-btn-secondary {
  @apply bg-neo-secondary text-neo-black;
}
```

**小尺寸按钮（图标按钮）：**
```html
<button class="neo-btn p-2 h-auto">
  <i class="fas fa-edit"></i>
</button>
```

**按钮动画效果：**
- 默认：`shadow-neo-sm` (4px 偏移)
- hover：上移 1 单位 + `shadow-neo-md` (8px 偏移)
- active：右移+下移 2px + 阴影消失（模拟按下效果）

### 3.2 Neo 卡片 (neo-card)

```css
.neo-card {
  @apply bg-neo-white border-4 border-neo-black p-6
         shadow-neo-md transition-all duration-200
         hover:-translate-y-1 hover:shadow-neo-lg;
}
```

**卡片使用场景：**
- 筛选/搜索面板容器
- 数据展示分组
- 统计信息卡片
- 表单容器

**统计数字卡片（card stat）：**
```html
<div class="p-4 border-3 border-neo-black bg-neo-secondary">
  <div class="text-3xl font-black">2,847</div>
  <div class="text-sm font-bold uppercase tracking-wide">总字符数</div>
</div>
```

### 3.3 Neo 徽章/标签 (neo-badge)

```css
.neo-badge {
  @apply inline-flex items-center px-3 py-1 border-2 border-neo-black
         bg-neo-secondary text-xs font-black uppercase tracking-widest
         shadow-[2px_2px_0px_0px_#000];
}
```

**使用场景：**
- 状态标签（成功/失败/进行中）
- 部门/分类标识
- 权限等级标记
- 页面标题旁的计数标签

**变体颜色：**
- 默认黄色 (`bg-neo-secondary`)
- 紫色 (`style="background-color: #C4B5FD;"`)
- 红色 (`bg-neo-accent text-neo-white`)
- 黑色 (`bg-neo-black text-neo-white`)
- 白色 (`bg-neo-white`)

### 3.4 Neo 输入框 (neo-input)

```css
.neo-input {
  @apply w-full h-14 px-4 bg-neo-white border-4 border-neo-black
         text-neo-black font-bold placeholder-gray-500
         focus:outline-none focus:bg-neo-secondary focus:shadow-neo-sm
         transition-colors duration-100;
}
```

**特点：**
- 固定高度 56px (h-14)
- 聚焦时变黄色背景
- 粗体文字
- textarea 使用 `h-32 resize-none`

### 3.5 Neo 标题

```css
.neo-h1 { font-black text-6xl md:text-8xl uppercase; }  /* 页面主标题 */
.neo-h2 { font-black text-4xl md:text-6xl uppercase; }  /* 页面标题 */
.neo-h3 { font-bold text-2xl md:text-3xl uppercase; }   /* 区块标题 */
```

---

## 四、弹窗/对话框样式

### 4.1 通用弹窗结构

```html
<!-- 遮罩层 -->
<div class="modal-mask hidden">
  <!-- 弹窗容器 -->
  <div class="modal-container p-6">
    <!-- 标题栏 -->
    <div class="flex items-center justify-between pb-4 border-b-4 border-neo-black">
      <h3 class="neo-h3">弹窗标题</h3>
      <button class="neo-btn p-3 h-auto">
        <i class="fas fa-times text-xl"></i>
      </button>
    </div>
    <!-- 内容区 -->
    <div class="pt-4 flex flex-col gap-4">...</div>
    <!-- 操作按钮 -->
    <div class="flex gap-3 pt-4">
      <button class="neo-btn flex-1">取消</button>
      <button class="neo-btn neo-btn-primary flex-1">确认</button>
    </div>
  </div>
</div>
```

**遮罩层样式：**
- `fixed top-0 left-0 w-full h-full bg-neo-black/70 z-50`
- 70% 透明度黑色背景

**弹窗容器样式：**
- `bg-neo-white border-6 border-neo-black shadow-neo-lg`
- `max-w-2xl w-full max-h-[90%] overflow-auto`

### 4.2 各页面弹窗清单

| 页面 | 弹窗名称 | 用途 | 特殊样式 |
|------|---------|------|---------|
| 工作台 | 全屏预览弹窗 | 预览排版效果 | `max-w-5xl` 大宽度 |
| 工作台 | 快速导出弹窗 | 选择导出格式 | 格式选择使用网格卡片 |
| 排班日历 | 编辑排班弹窗 | 编辑单日排班 | 员工+班次选择器+备注 |
| 排班日历 | 智能排班确认弹窗 | 确认自动排班 | 警告提示卡片 (bg-neo-secondary + 三角图标) |
| 考勤统计 | 员工考勤详情弹窗 | 查看个人详情 | 双列信息展示 + 图表 |
| 导出中心 | 导出进度弹窗 | 显示导出进度 | 进度条 (h-6 轨道 + 填充动画) |
| 员工管理 | 新增/编辑员工弹窗 | 表单录入 | 两列网格布局表单 |
| 员工管理 | 排班权限配置弹窗 | 选择权限级别 | Radio 卡片选择 (每个选项是一个 neo-card) |
| 员工管理 | 删除确认弹窗 | 二次确认删除 | 居中大图标 + 警告三角 |
| 参数配置 | 新建模板弹窗 | 表单录入 | 复杂表单含多个字段 |
| 参数配置 | 导入配置弹窗 | 文件上传 | 虚线边框拖拽区域 |
| 参数配置 | 删除确认弹窗 | 二次确认删除 | 居中图标 + 警告 |
| 班次配置 | 新增/编辑班次弹窗 | 表单录入 | 时间选择器+重复规则 |
| 班次配置 | 删除确认弹窗 | 二次确认删除 | 居中图标 + 警告 |
| 班次配置 | 班次详情弹窗 | 查看详情 | 只读信息展示 |
| 班次配置 | 约束规则配置弹窗 | 复杂规则表单 | 多个规则项列表 |

### 4.3 删除确认弹窗样式

```html
<div class="modal-container p-6 max-w-md">
  <div class="flex flex-col items-center text-center gap-4">
    <div class="w-20 h-20 bg-neo-accent border-4 border-neo-black flex items-center justify-center">
      <i class="fas fa-exclamation-triangle text-3xl text-white"></i>
    </div>
    <h2 class="neo-h3">确认删除</h2>
    <p class="text-lg font-medium text-neo-black/80">
      您确定要删除吗？此操作不可恢复！
    </p>
  </div>
  <div class="flex gap-3">
    <button class="neo-btn flex-1">取消</button>
    <button class="neo-btn neo-btn-primary flex-1">确认删除</button>
  </div>
</div>
```

### 4.4 警告提示卡片

```html
<div class="p-4 border-4 border-neo-black bg-neo-secondary">
  <div class="flex items-start gap-3">
    <i class="fas fa-exclamation-triangle text-2xl"></i>
    <p class="font-bold">系统将根据预设规则自动生成，是否确认执行？</p>
  </div>
</div>
```

---

## 五、表格样式

### 5.1 表格结构

```html
<table class="w-full border-collapse">
  <thead>
    <tr class="bg-neo-secondary border-b-4 border-neo-black">
      <th class="p-4 text-left font-black uppercase border-r-2 border-neo-black">
        <!-- 表头内容 -->
      </th>
    </tr>
  </thead>
  <tbody>
    <tr class="border-b-2 border-neo-black hover:bg-neo-bg transition-colors">
      <td class="p-4 border-r-2 border-neo-black">
        <!-- 单元格内容 -->
      </td>
    </tr>
  </tbody>
</table>
```

**关键样式：**
- 表头：黄色背景 (`bg-neo-secondary`) + 4px 底边框
- 表格行：2px 底边框 + hover 奶油背景
- 列分隔：`border-r-2 border-neo-black`
- 表头文字：`font-black uppercase`（最粗+全大写）
- 单元格文字：`font-bold`

### 5.2 表格内嵌组件

**员工头像（首字母缩写）：**
```html
<div class="w-12 h-12 bg-neo-muted border-3 border-neo-black flex items-center justify-center">
  <span class="font-black text-lg">张</span>
</div>
```

**操作按钮组：**
```html
<div class="flex items-center gap-2">
  <button class="edit-btn neo-btn p-2 h-auto"><i class="fas fa-edit"></i></button>
  <button class="neo-btn p-2 h-auto"><i class="fas fa-user-shield"></i></button>
  <button class="delete-btn neo-btn p-2 h-auto"><i class="fas fa-trash"></i></button>
</div>
```

---

## 六、统计卡片样式

### 6.1 数据概览卡片（Dashboard Stats）

```html
<div class="neo-card">
  <div class="flex flex-col gap-3">
    <!-- 标题行 -->
    <div class="flex items-center justify-between">
      <span class="neo-badge">总出勤</span>
      <i class="fas fa-user-check text-2xl text-neo-accent"></i>
    </div>
    <!-- 大数字 -->
    <div>
      <span class="text-4xl font-black">1286</span>
      <span class="text-sm font-bold text-neo-black/60">本月累计出勤人次</span>
    </div>
    <!-- 趋势指示 -->
    <div class="flex items-center gap-2">
      <i class="fas fa-arrow-up text-neo-accent"></i>
      <span class="font-bold text-neo-accent">+12.5%</span>
      <span class="text-sm font-medium text-neo-black/60">较上月</span>
    </div>
  </div>
</div>
```

### 6.2 小统计方块（卡片内嵌）

```html
<div class="p-4 border-3 border-neo-black bg-neo-secondary">
  <div class="text-3xl font-black">2,847</div>
  <div class="text-sm font-bold uppercase tracking-wide">总字符数</div>
</div>
```

四个一组使用 grid 布局：
```html
<div class="grid grid-cols-2 gap-4">
  <div class="p-4 border-3 border-neo-black bg-neo-secondary">...</div>
  <div class="p-4 border-3 border-neo-black bg-neo-muted">...</div>
  <div class="p-4 border-3 border-neo-black bg-neo-white">...</div>
  <div class="p-4 border-3 border-neo-black bg-neo-accent">...</div>
</div>
```

---

## 七、日历组件样式

### 7.1 日历单元格

```css
.calendar-cell {
  @apply border-3 border-neo-black p-2 min-h-[80px] bg-neo-white
         transition-all duration-100 cursor-pointer
         hover:bg-neo-secondary;
}
.calendar-cell.selected {
  @apply bg-neo-accent text-neo-black font-bold;
}
.calendar-cell.today {
  @apply border-neo-accent border-4;
}
```

### 7.2 班次标签（日历内）

```html
<span class="text-xs p-1 bg-neo-accent border-2 border-neo-black">
  张三 早班
</span>
```

### 7.3 班次图例

```html
<div class="flex items-center gap-2">
  <div class="w-6 h-6 bg-neo-accent border-2 border-neo-black"></div>
  <span class="font-bold">早班 (08:00-16:00)</span>
</div>
```

---

## 八、表单样式

### 8.1 表单布局模式

**单列表单：**
```html
<div class="flex flex-col gap-4">
  <div class="flex flex-col gap-2">
    <label class="block font-bold uppercase text-sm mb-2">
      字段名 <span class="text-neo-accent">*</span>
    </label>
    <input type="text" class="neo-input" placeholder="请输入...">
  </div>
</div>
```

**两列网格表单：**
```html
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
  <div>...</div>
  <div>...</div>
</div>
```

### 8.2 复选框/单选框

```html
<!-- 复选框 -->
<label class="flex items-center gap-2 cursor-pointer">
  <input type="checkbox" class="w-6 h-6 border-3 border-neo-black">
  <span class="font-bold uppercase">选项文字</span>
</label>

<!-- 单选框（权限配置使用卡片式） -->
<input type="radio" name="permission-level" class="w-6 h-6 border-4 border-neo-black">
```

### 8.3 下拉选择框

```html
<select class="neo-input">
  <option>选项1</option>
  <option>选项2</option>
</select>
```

---

## 九、进度条样式

```html
<div class="w-full h-6 bg-neo-bg border-4 border-neo-black overflow-hidden">
  <div class="h-full bg-neo-secondary w-3/4 transition-all duration-500"></div>
</div>
```

---

## 十、分页组件样式

```html
<div class="flex items-center gap-2">
  <button class="neo-btn p-2 h-auto"><i class="fas fa-chevron-left"></i></button>
  <button class="neo-btn neo-btn-secondary p-2 h-auto">1</button>
  <button class="neo-btn p-2 h-auto">2</button>
  <button class="neo-btn p-2 h-auto">3</button>
  <button class="neo-btn p-2 h-auto"><i class="fas fa-chevron-right"></i></button>
</div>
```

---

## 十一、背景纹理

### 11.1 半调波点纹理

```css
.bg-pattern-dots {
  background-image: radial-gradient(#000 1.5px, transparent 1.5px);
  background-size: 20px 20px;
}
```

### 11.2 网格纹理

```css
.bg-pattern-grid {
  background-size: 40px 40px;
  background-image:
    linear-gradient(to right, rgba(0, 0, 0, 0.1) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(0, 0, 0, 0.1) 1px, transparent 1px);
}
```

---

## 十二、ECharts 图表集成

原型中使用 ECharts 进行数据可视化，图表风格与新野兽派保持一致：

### 12.1 图表样式特征

- **线条图**：4px 实线 + 黑色边框 + 3px 项边框
- **柱状图**：25% 柱宽 + 3px 黑边框
- **饼图**：40%-70% 环形 + 4px 黑边框
- **Tooltip**：标准样式
- **文字**：Space Grotesk 字体 + bold 字重

### 12.2 图表配色复用

| 图表元素 | 颜色 |
|----------|------|
| 正常出勤/主要数据 | `#FFD93D` (黄色) |
| 迟到/次要数据 | `#C4B5FD` (紫色) |
| 缺勤/警告数据 | `#FF6B6B` (红色) |
| 加班/深色数据 | `#000000` (黑色) |
| 请假/中性数据 | `#FFFFFF` (白色+黑边框) |

---

## 十三、动画与交互效果

### 13.1 卡片悬浮效果

```css
/* 卡片 hover 上浮 + 阴影增大 */
.neo-card:hover {
  transform: translateY(-4px);
  box-shadow: 12px 12px 0px 0px #000;
}
```

### 13.2 按钮交互

```css
/* 按钮 hover 上浮 */
.neo-btn:hover {
  transform: translateY(-4px);
  box-shadow: 8px 8px 0px 0px #000;
}

/* 按钮 active 按下 */
.neo-btn:active {
  transform: translateX(2px) translateY(2px);
  box-shadow: none;
}
```

### 13.3 导出卡片悬停旋转

```css
.group:hover > .export-icon {
  transform: rotate(3deg);
}
```

### 13.4 进度条动画

```css
.transition-all.duration-500
```

---

## 十四、响应式断点

| 断点 | 说明 | 布局变化 |
|------|------|---------|
| `sm` (640px) | 小屏 | 容器 padding 增加 |
| `md` (768px) | 中屏 | 导航栏显示，表单变两列 |
| `lg` (1024px) | 大屏 | 完整三列/四列布局 |
| `xl` (1280px) | 超大屏 | 最大容器宽度 |

**移动端适配策略：**
- 桌面导航隐藏 (`hidden md:flex`)
- 汉堡菜单按钮显示 (`md:hidden`)
- 网格从多列变为单列 (`grid-cols-1 md:grid-cols-4`)
- 移动端菜单使用 modal-mask 覆盖层

---

## 十五、与当前项目的适配建议

### 15.1 可直接借鉴的样式

以下样式可以直接应用到当前 SPS-System 项目中：

| 可借鉴项 | 来源 | 说明 |
|----------|------|------|
| **Neo 按钮样式** | 全局 | 硬阴影按钮风格，适合操作按钮 |
| **Neo 卡片样式** | 全局 | 带边框的卡片容器 |
| **Neo 徽章** | 全局 | 状态标签、分类标签 |
| **删除确认弹窗** | 员工管理/参数配置 | 居中图标+警告样式 |
| **统计卡片布局** | 考勤统计 | 4 列数据概览卡片 |
| **表格样式** | 员工管理/考勤统计 | 带分隔线的表格 |
| **进度条** | 导出中心 | 文件导出进度展示 |
| **警告提示卡片** | 排班日历 | 带图标的黄色警告框 |
| **表单布局** | 全局 | 两列网格表单 |
| **分页组件** | 员工管理/考勤统计 | 按钮式分页 |
| **图标头像** | 员工管理 | 首字母圆形头像 |
| **日历单元格** | 排班日历 | 排班日历格子样式 |
| **班次图例** | 排班日历 | 颜色块+文字说明 |

### 15.2 需要调整的样式

| 样式 | 需要调整的原因 |
|------|---------------|
| **配色方案** | 当前项目可能已有自己的品牌色，需要替换 neo 色系 |
| **字体** | Space Grotesk 是外部字体，可能需要替换为项目默认字体 |
| **粗边框** | 4px 边框在 Element Plus 中可能过于醒目，建议调整为 2px |
| **硬阴影** | 硬阴影风格比较激进，可根据项目调性调整偏移量 |
| **全大写标题** | 中文环境下 uppercase 无效，英文内容才需要 |
| **neo-input 高度** | h-14 (56px) 偏大，Element Plus 默认更小 |

### 15.3 不建议直接使用的样式

- **背景纹理**（波点/网格）— 可能干扰业务数据展示
- **新野兽派整体风格** — 如果当前项目是更传统的企业管理风格，建议只提取单个组件而非整体风格

---

## 十六、Tailwind 配置完整副本

如需在新项目中复现此设计系统，以下是完整的 tailwind.config：

```javascript
tailwind.config = {
  theme: {
    extend: {
      colors: {
        neo: {
          bg: '#FFFDF5',      // 奶油背景
          black: '#000000',   // 结构黑
          accent: '#FF6B6B',  // 热红
          secondary: '#FFD93D', // 亮黄
          muted: '#C4B5FD',   // 柔紫
          white: '#FFFFFF',
        }
      },
      fontFamily: {
        sans: ['"Space Grotesk"', 'sans-serif'],
        display: ['"Space Grotesk"', 'sans-serif'],
      },
      boxShadow: {
        'neo-sm': '4px 4px 0px 0px #000',
        'neo-md': '8px 8px 0px 0px #000',
        'neo-lg': '12px 12px 0px 0px #000',
        'neo-xl': '16px 16px 0px 0px #000',
        'neo-hover': '10px 10px 0px 0px #000',
      },
      borderWidth: { '3': '3px', '4': '4px', '6': '6px', '8': '8px' },
      spacing: { '18': '4.5rem', '22': '5.5rem' },
      rotate: { '1': '1deg', '2': '2deg', '3': '3deg', '-1': '-1deg', '-2': '-2deg', '-3': '-3deg' }
    }
  }
}
```

---

## 十七、原型页面清单

| # | 页面名称 | PageUUID | 核心功能 |
|---|---------|----------|---------|
| 1 | 自动排版工作台 | typesetting_workbench | 文本导入、实时预览、排版参数调整 |
| 2 | 排班日历页面 | ScheduleCalendarPage | 月历视图、排班编辑、智能排班 |
| 3 | 考勤数据统计页面 | AttendanceStatPage | 数据概览、ECharts 图表、明细表格 |
| 4 | 导出中心页面 | export_center | 多格式导出、进度显示、历史记录 |
| 5 | 员工管理页面 | StaffManagePage | 员工列表、CRUD 操作、权限配置 |
| 6 | 班次规则配置页面 | ShiftRuleConfigPage | 班次管理、约束规则配置 |
| 7 | 排版参数配置页面 | typesetting_param_config | 模板管理、参数导入导出 |
