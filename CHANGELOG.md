# 版本发布说明（Changelog）

**文档版本：** V1.0
**最后更新：** 2026-07-10
**维护者：** 开发团队

> 本文件基于 Git 提交历史自动生成初稿，后续每次发布后需人工审核更新。

---

## [Unreleased]

### 新增
- （暂无）

### 修复
- 自动排班调度器检查间隔从 30 分钟改为 5 分钟，提高响应速度
- 月末判断逻辑优化：改用"下月第一天减一天"方式，更准确
- 触发窗口扩大：从精确小时匹配改为配置时间 ±30 分钟的 60 分钟窗口
- 新增防重复执行机制：通过 `auto_schedule_last_run` 配置项防止同一天多次执行

### 变更
- APScheduler job ID 从 `auto_schedule_monthly` 改为 `auto_schedule_check`
- 日志输出更新为"每 5 分钟检查，月末按配置时间自动排班"

---

## [1.0.0] — 2026-07-10

### 新增
- **排班管理优化**
  - 统一导入/导出权限至 `schedule` 模块（`schedule:import` / `schedule:export`）
  - 导出页面增加权限守卫
  - 导出按钮统一使用 `schedule:export` 权限校验
  - 权限 Schema 增加 `import` / `export` 操作

### 修复
- 跨月排班轮换规则修复
- 跨月配对加载顺序修正
- 多月份调度时生成历史同步
- 自动排班引擎槽位分组器引用修复
- 空夜班兜底逻辑修复
- 回退选择公平性排序

### 优化
- 移除调试日志输出
- 清理生成的临时文件
- 同步 .gitignore，忽略 `.superpowers/` 目录
- 强制 LF 换行符（.gitattributes）
- 修复页面标题为"排班管理系统 - SPS"
- 配置 Python 环境并强化节假日检测逻辑

### 重构
- 全面替换硬编码样式值为 CSS 设计令牌（Neo Brutalism 风格）
- 全面重构前端 UI 并清理备份文件

---

## 历史提交摘要（V1.0 之前）

| 日期 | 提交摘要 | 类型 |
|------|---------|------|
| 2026-06-16 | 排班引擎集成设计 | feat |
| 2026-06-13 | 排班引擎 V2 设计（跨月替换） | feat |
| 2026-06-11 | 排班引擎优化 | feat |
| 2026-05-22 | 项目初始基线 | chore |

---

## 版本命名规则

采用 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)：

```
主版本.次版本.修订号
1    .0   .0
↑      ↑    ↑
破坏性 新功能 修复
```

- **主版本**：不兼容的 API 修改
- **次版本**：向下兼容的功能新增
- **修订号**：向下兼容的问题修正

---

## 提交信息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

type 可选值：
- feat:     新功能
- fix:      修复 bug
- docs:     文档变更
- style:    代码格式（不影响代码运行）
- refactor: 重构（不含新功能或 bug 修复）
- test:     测试相关
- chore:    构建过程或辅助工具变动
- perf:     性能优化
```

示例：
```
feat(schedule): unify import/export permissions to schedule module
fix(engine): correct cross-month pairing loading order
docs(api): add endpoint summary documentation
```
