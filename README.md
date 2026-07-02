# 排班管理系统 (SPS - Scheduling Management System)

基于 FastAPI + Vue 3 的 7×24 值班排班管理系统，支持约束驱动的自动排班、调班申请审批、组织架构管理和完整的权限控制。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12, FastAPI, SQLAlchemy (async), APScheduler |
| 前端 | Vue 3 + TypeScript + Vite 8, Element Plus, Pinia |
| 数据库 | PostgreSQL |

## 功能模块

- **组织架构** — 树形结构管理，支持多级部门
- **人员管理** — 人员 CRUD、账号绑定、特殊规则设置
- **班次模板** — 定义班次类型（白班/夜班等）和轮转频率
- **排班规则** — 约束条件管理（每日最多班次、连续班次上限、最小间隔等）
- **自动排班** — 基于约束引擎的月度自动排班，支持跨月替换
- **排班日历** — 可视化日历查看/编辑，支持导入导出
- **调班管理** — 员工发起调班申请、审批流程
- **消息中心** — 系统通知、公告发布、已读管理
- **角色权限** — RBAC 权限矩阵，细粒度资源控制
- **系统配置** — 系统名称、组织信息、自动排班开关等

## 快速开始

### 前置要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 安装依赖
pip install fastapi uvicorn sqlalchemy[asyncio] asyncpg pydantic-settings \
    python-jose[cryptography] bcrypt apscheduler alembic

# 配置数据库
# 编辑 backend/.env 文件，修改 DATABASE_URL
# 示例: postgresql+asyncpg://user:password@localhost:5432/dbname

# 启动开发服务器
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端 API 文档：`http://localhost:8000/docs`

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端访问：`http://localhost:5173`

### 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 超级管理员 |

> ⚠️ 首次登录需强制修改密码

## 项目结构

```
SPS-System/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── config.py            # 环境变量配置
│   │   ├── database.py          # 数据库连接与自动迁移
│   │   ├── api/                 # REST API 路由
│   │   │   ├── auth.py          # 登录/注册/密码修改
│   │   │   ├── organization.py  # 组织架构 CRUD
│   │   │   ├── staff.py         # 人员管理
│   │   │   ├── schedule.py      # 排班管理（含自动排班）
│   │   │   ├── swap.py          # 调班申请与审批
│   │   │   ├── message.py       # 消息与公告
│   │   │   └── ...
│   │   ├── services/            # 业务逻辑层
│   │   │   ├── schedule_service.py
│   │   │   └── auto_schedule_job.py  # APScheduler 定时任务
│   │   ├── engine/              # 排班算法引擎
│   │   │   ├── scheduler.py     # AutoScheduler + CandidateFilter
│   │   │   ├── scoring.py       # 公平性评分
│   │   │   └── constraint_checker.py
│   │   ├── models/              # SQLAlchemy ORM 模型
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   └── utils/               # 工具函数（JWT、加密、初始化数据）
│   └── tests/                   # 测试用例
├── frontend/
│   ├── src/
│   │   ├── api/                 # API 客户端（Axios 封装）
│   │   ├── layouts/             # 布局组件
│   │   ├── views/               # 页面组件
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── router/              # 路由配置
│   │   └── styles/              # 全局样式
│   └── vite.config.ts           # Vite 配置
└── CLAUDE.md                    # 开发者指南
```

## 排班引擎

排班引擎采用**槽位轮换**模型：

1. 人员分组为若干槽位（标准 12 人场景为 3 个槽位）
2. 每个槽位分为白班组和夜班组（新老搭配）
3. 轮换公式：`(day - 1) % num_slots` 选择槽位，`rotation_number % 2` 决定白/夜班
4. 跨月排班通过 `sch_pairing` 表持久化配对关系，确保连续性
5. 特殊人员池按月交替轮换班次

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/auth/me` | 获取当前用户信息 |
| POST | `/api/auth/force-change-password` | 强制修改密码 |
| GET | `/api/organizations` | 获取组织列表 |
| GET | `/api/staffs` | 获取人员列表 |
| GET | `/api/schedules/calendar` | 获取排班日历 |
| POST | `/api/schedules/auto-generate` | 触发自动排班 |
| POST | `/api/schedules/publish` | 发布排班 |
| GET | `/api/swaps` | 获取调班列表 |
| PUT | `/api/swaps/{id}/approve` | 审批调班 |
| GET | `/api/messages` | 获取消息列表 |
| GET | `/api/announcements` | 获取公告列表 |

完整 API 文档：`http://localhost:8000/docs`

## 环境变量

后端 `.env` 文件配置：

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=480
DEBUG=true
ALLOWED_ORIGINS=http://localhost:5173
```

## 开发命令

### 后端测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_bugfixes.py -v

# 手动测试脚本
python test_auto_schedule.py
python test_cross_month.py
```

### 前端构建

```bash
# 类型检查 + 构建
npm run build

# 预览生产构建
npm run preview
```

## 许可证

MIT
