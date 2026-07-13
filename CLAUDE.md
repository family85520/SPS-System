# CLAUDE.md

排班管理系统 (Scheduling Management System) — 面向 7×24 值守场景的班次排班系统，支持基于约束的自动排班、调班管理、组织架构层级管理和角色权限控制。

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL, APScheduler
- **Frontend:** Vue 3 + TypeScript + Vite, Element Plus, Pinia, Vue Router, ECharts
- **Auth:** JWT (python-jose + bcrypt)
- **Build:** vue-tsc type-check, unplugin-auto-import (Vue/Element Plus APIs), unplugin-vue-components

## Development Commands

### Backend
```bash
cd backend
python -m venv venv && venv\Scripts\activate          # Windows
source venv/bin/activate                               # Linux/macOS
pip install -r requirements.txt                        # 安装依赖
uvicorn app.main:app --reload --port 8000              # 启动开发服务器
alembic upgrade head                                   # 数据库迁移
```

### Frontend
```bash
cd frontend
npm install                                          # 安装依赖
npm run dev                                          # 启动开发服务器 (localhost:5173)
npm run build                                        # 生产构建
npm run preview                                      # 预览构建产物
```

### Database
- 数据库名: `scp_db`，用户: `scp / scp2026`
- 连接字符串: `postgresql+asyncpg://scp:scp2026@localhost:5432/scp_db`
- 启动时自动执行 `init_db()` → 创建表 + 默认数据 + 约束规则

## Architecture

### Key Architecture Decisions

- **API 层分离:** FastAPI routers → HTTP 关注点; services → 业务逻辑; engine → 纯领域逻辑（零框架依赖）
- **Auth 流程:** Bearer JWT。`deps.py` 提供 `get_current_user`, `require_roles()`（精确匹配）, `require_permissions()` 作为 FastAPI 依赖注入。前端路由守卫检查 `requiresAuth`, `mustChangePassword`, 和 RBAC。HTTP 拦截器自动附加 Bearer token 并处理 401/403。
- **Database:** 启动时自动迁移 (`_auto_migrate_columns` in `database.py`)。`get_db()` **不自动 commit** — 事务边界由每个 Service 独立管理。自动为用户创建账号（用户名=工号，密码 123456）。
- **Frontend auto-imports:** `unplugin-auto-import` 自动导入 Vue/Element Plus APIs; `unplugin-vue-components` 自动注册 Element Plus 组件。无需手动导入 `ref`, `computed`, `ElMessage` 等。

### Scheduling Engine (critical domain logic)

Located in `backend/app/engine/`. Uses a **slot-based rotation** model:

- Staff grouped into slots (3 slots for standard scenarios)
- Each slot has day-group and night-group (new + experienced staff paired)
- Rotation: `(day-1) % n_slots` picks slot; `rotation_number % 2` determines white/night assignment
- **Cross-month:** Previous month's pairings persisted in `sch_pairing` table, loaded for 1:1 replacement
- **Special personnel:** Pool members alternate between shifts monthly (admin ↔ day/night swap)
- **CandidateFilter pipeline:** special rules → constraint rules (max per day, max continuous, min interval) before slot selection
- `SchShiftTemplate` has composite flags: `leader_enabled`, `special_enabled`, `member_enabled` for three-tier staffing
- `rotation_frequency` fields use string values: `"day"`, `"week"`, `"month"`

### Permission Model

- Roles have composite permissions organized by module (organization, staff, shift_template, constraint, schedule, swap, message, export) and action (read, create, update, delete, publish, approve).
- `schedule:import` and `schedule:export` replaced standalone `import`/`export` module permissions.
- Frontend permission guards use `useConfirm` composable for destructive actions.
- Admin role has `permissions: {"all": true}`.

### Database Tables

Tables use prefix conventions: `org_*` (Organization & Staff), `sch_*` (Scheduling), `sys_*` (System), `swap_*` (Swap Management), `export_*` (Export).

| Prefix | Table | Purpose |
|--------|-------|---------|
| `org_` | organization | Organization hierarchy (tree) |
| `org_` | staff | Personnel info |
| `org_` | staff_role | Personnel identity tags (领导/新员工) |
| `sys_` | user | System users (login accounts) |
| `sys_` | role | Role definitions + permissions |
| `sys_` | user_role | User-role assignments (M:N) |
| `sys_` | config | System configuration (key-value) |
| `sys_` | audit_log | Operation audit trail |
| `sys_` | message | Notification messages |
| `sys_` | announcement | Announcements |
| `sch_` | shift_template | Shift template definitions |
| `sch_` | constraint | Constraint rules |
| `sch_` | special_rule | Special personnel rules |
| `sch_` | schedule | Schedule records (by date+shift) |
| `sch_` | schedule_detail | Schedule details (staff per shift) |
| `sch_` | pairing | Cross-month pairing relationships |
| `sch_` | duty_team | Duty teams per shift template |
| `swap_` | swap_request | Swap request records |
| `exp_` | export_template | Custom export templates |

### Module Structure

**Backend:**
```
backend/app/
├── api/              # HTTP routers (auth, organization, staff, shift_template, constraint, special_rule, role, system, schedule, swap, message, dashboard, export)
├── models/           # SQLAlchemy models (13 tables)
├── services/         # Business logic (schedule_service, shift_template_service, constraint_service, swap_service, message_service, etc.)
├── engine/           # Pure domain logic (scheduler.py, constraint_checker.py, scoring.py, pairing_manager.py)
├── schemas/          # Pydantic request/response models
└── utils/            # Helpers (security, init_data, employee_no, time_helper)
```

**Frontend:**
```
frontend/src/
├── api/              # API wrappers (mirrors backend routers)
├── views/            # Page-level components (11 views with view-specific sub-components)
├── stores/           # Pinia stores (auth, system, message)
├── layouts/          # MainLayout (sidebar + header)
├── router/           # Vue Router with navigation guards
└── composables/      # Shared composition functions (useConfirm)
```

## Important Patterns

- All dates use ISO format strings (`YYYY-MM-DD`) in engine internals; database uses `Date` type.
- `SchShiftTemplate` has three-tier staffing: `leader_enabled`, `special_enabled`, `member_enabled`.
- Manual test scripts (`test_auto_schedule.py`, `test_cross_month.py`) are standalone async Python scripts in repo root, not pytest.
- Frontend API files mirror backend routers exactly; adding a new endpoint requires updates in both `backend/app/api/` and `frontend/src/api/`.
- Views are page-level components; view-specific sub-components live in `[view]/components/`. Only `ConfirmDialog.vue` is a global shared component.
- Auto-scheduler runs every 5 minutes via APScheduler, checks if today is last day of month, then generates next month's schedule.
