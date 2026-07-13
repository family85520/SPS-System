# 项目文档导航

> SPS-System（排班管理系统）全链路文档索引

---

## 文档分类

### 📋 需求与设计

| 文档 | 版本 | 说明 |
|------|------|------|
| [产品需求文档 PRD](排班管理系统%20产品需求文档PRD_V1.0.md) | V1.0 | 功能需求、用户故事、验收标准 |
| [UI 设计方案](UI_设计方案_完整.md) | — | 视觉规范、布局规范、组件样式 |
| [开发任务流程](DevelopmentTaskFlow.md) | V1.0 | 分阶段开发任务、API 设计、验收标准 |

### 🏗️ 架构设计 (`architecture/`)

| 文档 | 优先级 | 说明 |
|------|--------|------|
| [系统架构设计](architecture/system-architecture.md) | P0 | 技术栈、模块划分、架构图、数据流、设计决策 |
| [数据库设计](architecture/database-design.md) | P0 | ER 图、表结构、索引策略、迁移历史 |
| [排班引擎 V2 设计](superpowers/specs/2026-06-13-scheduling-engine-v2-design.md) | P0 | 跨月替换规则、配对关系持久化 |
| [排班引擎集成设计](superpowers/specs/2026-06-16-scheduling-engine-integrated-design.md) | P0 | 统一班次模板三档人员结构 |

### 🔌 API 文档 (`api/`)

| 文档 | 说明 |
|------|------|
| [API 端点速查表](api/endpoint-summary.md) | 全部端点汇总、权限标识、方法路径 |
| [Swagger UI](http://localhost:8000/docs) | 交互式 API 文档（运行时） |
| [ReDoc](http://localhost:8000/redoc) | 静态 API 文档（运行时） |

### 🔒 安全文档 (`security/`)

| 文档 | 说明 |
|------|------|
| [权限模型说明](security/permission-model.md) | RBAC 角色体系、权限矩阵、前后端守卫逻辑 |

### 📊 项目管理

| 文档 | 说明 |
|------|------|
| [项目状态](ProjectStatus.md) | 已完成/进行中/待开发模块跟踪 |
| [Week1 总结](Week1_Summary.md) | 第一周工作成果 |
| [Week2 总结](Week2_Summary.md) | 第二周工作成果 |

### 📖 用户文档（待编写）

| 文档 | 优先级 | 说明 |
|------|--------|------|
| [管理员操作手册](../user/admin-manual.md) | P1 | 后台管理功能操作指南 |
| [普通用户操作手册](../user/user-manual.md) | P1 | 排班查看、调班申请等日常操作 |
| [常见问题 FAQ](../user/faq.md) | P2 | 用户高频问题汇总 |

### 🚀 部署运维（待编写）

| 文档 | 优先级 | 说明 |
|------|--------|------|
| [Linux 部署手册](../deploy/linux-deployment.md) | P0 | 生产环境安装配置步骤 |
| [Windows 部署手册](../deploy/windows-deployment.md) | P1 | Windows 环境部署指南 |
| [Docker 容器化指南](../deploy/docker-guide.md) | P1 | 容器化部署方案 |
| [Nginx 配置说明](../deploy/nginx-config.md) | P1 | 反向代理与 WebSocket 配置 |
| [故障排查手册](../operations/troubleshooting.md) | P1 | 常见故障诊断与处理流程 |

### 🧪 测试文档（待编写）

| 文档 | 优先级 | 说明 |
|------|--------|------|
| [测试计划](../testing/test-plan.md) | P1 | 测试策略、范围、资源安排 |
| [集成测试用例](../testing/integration-tests.md) | P1 | 端到端测试场景 |

---

## 文档维护规则

1. **所有文档纳入 Git 版本管理**
2. **命名规范**：文件名使用 kebab-case，目录按类别分组
3. **变更同步**：代码合入前确认相关文档是否需要更新
4. **自动生成**：`docs/superpowers/` 下的 spec/plan 由开发流程自动生成，不手动编辑
5. **定期回顾**：每完成一个里程碑，回顾文档一致性和完整性

---

## 最近更新记录

| 日期 | 变更内容 | 影响文档 |
|------|---------|---------|
| 2026-07-11 | 自动排班调度器优化：5 分钟检查间隔、防重复执行 | system-architecture, admin-manual, faq, troubleshooting, changelog |
| 2026-07-10 | 初始文档体系构建（15 份文档） | 全部 |
