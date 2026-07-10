# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

排班管理系统 (Scheduling Management System) — 面向 7×24 值守场景的班次排班系统，支持基于约束的自动排班、调班管理和组织架构层级管理。

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL, APScheduler
- **Frontend:** Vue 3 + TypeScript + Vite, Element Plus, Pinia, Vue Router, ECharts
- **Auth:** JWT (python-jose + bcrypt)
- **Build tools:** vue-tsc type-check, unplugin-auto-import (Vue/Element Plus APIs), unplugin-vue-components (auto-import components)

## Development Commands

### Backend

```bash
cd backend
# Activate virtual environment
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux

# Install dependencies manually as needed (no requirements.txt)
pip install fastapi uvicorn sqlalchemy[asyncio] asyncpg pydantic-settings python-jose[cryptography] bcrypt apscheduler alembic

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run pytest tests
python -m pytest tests/ -v
python -m pytest tests/test_pairing.py -v   # single test file

# Standalone test scripts (async, require activated venv)
python test_auto_schedule.py
python test_cross_month.py

# Database migrations
alembic revision -m "description"
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # Vite dev server on port 5173, proxies /api → localhost:8000
npm run build     # vue-tsc type-check + Vite build
npm run preview   # preview production build
```

### Deployment

```bash
# Linux
bash deploy/linux/install.sh    # one-click install (DB + venv + migration)
bash deploy/linux/start.sh      # start backend service

# Windows
deploy\windows\start.bat        # activate venv + start uvicorn
```

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI app with lifespan (DB init, APScheduler startup)
│   ├── config.py            # Pydantic Settings (.env → DATABASE_URL, JWT, CORS)
│   ├── database.py          # async engine, session factory, Base, init_db (auto-migrate columns)
│   ├── api/                 # FastAPI routers — one per domain resource
│   │   ├── deps.py          # get_current_user (JWT), require_roles(), require_permissions()
│   │   ├── auth.py, organization.py, staff.py, schedule.py, swap.py, message.py, ...
│   ├── services/            # Business logic layer
│   │   ├── schedule_service.py   # CRUD, auto_generate, publish
│   │   ├── auto_schedule_job.py  # Monthly APScheduler trigger
│   │   ├── swap_service.py, export_service.py, ...
│   ├── engine/              # Pure scheduling algorithm (no framework deps)
│   │   ├── scheduler.py     # AutoScheduler + IndividualStrategy + SlotGrouper + CandidateFilter
│   │   ├── scoring.py       # FairnessScorer
│   │   ├── constraint_checker.py
│   │   └── pairing_manager.py  # Persists slot/group pairings (sch_pairing table)
│   ├── models/              # SQLAlchemy ORM (DeclarativeBase)
│   ├── schemas/             # Pydantic request/response schemas
│   └── utils/               # security (JWT/bcrypt), init_data, time_helper, employee_no
├── tests/                   # pytest test suite
├── deploy/                  # Production deployment scripts
└── alembic/                 # DB migrations
```

```
frontend/
├── src/
│   ├── main.ts              # App entry
│   ├── App.vue
│   ├── api/                 # Typed API client functions (mirrors backend routers)
│   │   ├── index.ts         # Shared axios instance (baseURL: '/api', auto token injection)
│   │   ├── auth.ts, schedule.ts, staff.ts, swap.ts, ...
│   ├── router/index.ts      # Route definitions + beforeEach guards (auth, password change, RBAC)
│   ├── stores/              # Pinia stores
│   │   ├── auth.ts          # Login state, token management
│   │   ├── system.ts        # User info, permissions, roles
│   │   └── message.ts       # Message notifications
│   ├── views/               # Page-level components (one per route)
│   │   ├── login/LoginView.vue
│   │   ├── dashboard/DashboardView.vue
│   │   ├── schedule/ScheduleCalendarView.vue  # Main calendar with ExportDialog, ShiftDetailDrawer
│   │   ├── staff/StaffView.vue
│   │   ├── organization/OrgView.vue
│   │   ├── shift-template/ShiftTemplateView.vue
│   │   ├── constraint/ConstraintView.vue
│   │   ├── swap/SwapView.vue
│   │   ├── message/MessageView.vue
│   │   ├── role/RoleView.vue
│   │   ├── system/SystemView.vue
│   │   └── [view]/components/  # View-scoped sub-components
│   ├── layouts/MainLayout.vue
│   ├── components/ConfirmDialog.vue  # Global reusable dialog wrapper
│   ├── composables/useConfirm.ts   # Confirm dialog composable
│   └── utils/request.ts         # (removed — all API files now use shared api instance)
└── vite.config.ts           # Vite config with proxy, auto-import plugins
```

### Key Architecture Decisions

- **API layer separation**: FastAPI routers → HTTP concerns; services → business logic; engine → pure domain logic with zero framework dependencies.
- **Auth flow**: Bearer JWT. `deps.py` provides `get_current_user`, `require_roles()` (exact match), `require_permissions()` as FastAPI dependencies. Frontend router guards check `requiresAuth`, `mustChangePassword`, and RBAC via `meta.permission`/`meta.roles`. HTTP interceptor auto-attaches Bearer token and handles 401/403.
- **Database**: Auto-migration on startup (`_auto_migrate_columns` in `database.py`). Alembic available but base schema created by `Base.metadata.create_all`. Auto-creates user accounts for staff without them. `get_db()` no longer auto-commits — transaction boundaries managed per-service.
- **Frontend auto-imports**: `unplugin-auto-import` auto-imports Vue/Element Plus APIs; `unplugin-vue-components` auto-registers Element Plus components. No manual imports needed for `ref`, `computed`, `ElMessage`, etc.

### Scheduling Engine (critical domain logic)

Located in `backend/app/engine/scheduler.py`. Uses a **slot-based rotation** model:

- Staff grouped into slots (3 slots for 12-person standard scenarios)
- Each slot has day-group and night-group (new + experienced staff paired)
- Rotation: `(day-1) % n_slots` picks slot; `rotation_number % 2` determines white/night assignment
- **Cross-month**: Previous month's pairings persisted in `sch_pairing` table, loaded for 1:1 replacement
- **Special personnel**: Pool members alternate between shifts monthly (admin ↔ day/night swap)
- **CandidateFilter pipeline**: special rules → constraint rules (max per day, max continuous, min interval) before slot selection
- `SchShiftTemplate` controls rotation frequency (`day`/`week`/`month`), leader groups, special groups, constraint rule binding per template

### Permission Model

- Roles have composite permissions organized by module (organization, staff, shift_template, constraint, schedule, swap, message, export) and action (read, create, update, delete, publish, approve).
- `schedule:import` and `schedule:export` replaced standalone `import`/`export` module permissions (commit `f92f5b7`).
- Frontend permission guards use `useConfirm` composable for destructive actions.

### Database Tables (prefix convention)

| Prefix | Domain | Key Tables |
|--------|--------|------------|
| `org_*` | Organization & Staff | org_dept, org_staff, org_user |
| `sch_*` | Scheduling | sch_template, sch_constraint, sch_schedule, sch_special_rule, sch_pairing |
| `sys_*` | System | sys_user, sys_role, sys_message, sys_audit_log, sys_config |
| `swap_*` | Swap Management | swap_request |
| `export_*` | Export | export_template |

## Important Patterns

- All dates use ISO format strings (`YYYY-MM-DD`) in engine internals; database uses `Date` type.
- `SchShiftTemplate` has composite flags: `leader_enabled`, `special_enabled`, `member_enabled` for three-tier staffing.
- `rotation_frequency` fields use string values: `"day"`, `"week"`, `"month"`.
- Manual test scripts (`test_auto_schedule.py`, `test_cross_month.py`) are standalone async Python scripts in repo root, not pytest.
- Frontend API files mirror backend routers exactly; adding a new endpoint requires updates in both `backend/app/api/` and `frontend/src/api/`.
- Views are page-level components; view-specific sub-components live in `[view]/components/`. Only `ConfirmDialog.vue` is a global shared component.
