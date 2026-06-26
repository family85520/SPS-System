# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

排班管理系统 (Scheduling Management System) — a shift scheduling system for 7×24 duty management with flexible constraint-based automatic scheduling, swap management, and organizational hierarchy.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL, APScheduler
- **Frontend:** Vue 3 + TypeScript + Vite 8, Element Plus, Pinia, Vue Router
- **Auth:** JWT (python-jose + bcrypt)

## Development Commands

### Backend

```bash
cd backend
# Create & activate virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
source venv/bin/activate       # Linux

# Install dependencies (no requirements.txt — pip install as needed)
pip install fastapi uvicorn sqlalchemy[asyncio] asyncpg pydantic-settings python-jose[cryptography] bcrypt apscheduler alembic

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run specific test
python -m pytest tests/test_bugfixes.py -v

# Run all tests
python -m pytest tests/ -v

# Manual test scripts (standalone, not pytest)
python test_auto_schedule.py
python test_cross_month.py

# Database migrations
cd backend
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # Vite dev server on port 5173, proxies /api → localhost:8000
npm run build     # vue-tsc type-check + Vite build
```

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI app with lifespan (DB init, APScheduler)
│   ├── config.py            # Pydantic Settings (DATABASE_URL, JWT, CORS)
│   ├── database.py          # async engine, session factory, Base, init_db (auto-migrate)
│   ├── api/                 # FastAPI routers — one per domain resource
│   │   ├── deps.py          # get_current_user (JWT), require_roles, require_permissions
│   │   ├── auth.py, organization.py, staff.py, schedule.py, ...
│   ├── services/            # Business logic — called by API routers
│   │   ├── schedule_service.py   # CRUD, auto_generate (orchestrates engine), publish
│   │   ├── auto_schedule_job.py  # Monthly trigger job (APScheduler, last-day-of-month)
│   │   ├── swap_service.py, message_service.py, ...
│   ├── engine/              # Scheduling algorithm (domain core, no FastAPI deps)
│   │   ├── scheduler.py     # AutoScheduler + IndividualStrategy + SlotGrouper + CandidateFilter
│   │   ├── scoring.py       # FairnessScorer
│   │   ├── constraint_checker.py
│   │   └── pairing_manager.py  # Persists slot/group pairings in sch_pairing table
│   ├── models/              # SQLAlchemy ORM models (DeclarativeBase)
│   ├── schemas/             # Pydantic request/response schemas
│   └── utils/               # security (JWT/bcrypt), init_data, time_helper
├── tests/                   # pytest tests
├── alembic/                 # DB migrations
└── deploy/                  # linux/windows start scripts
```

### Key Architecture Decisions

- **API layer**: FastAPI routers handle HTTP concerns; services handle business logic; engine is pure domain logic with no framework dependencies.
- **Auth**: Bearer token JWT. `deps.py` provides `get_current_user`, `require_roles()` (exact match), `require_permissions()` as FastAPI dependencies.
- **Database**: Auto-migration runs on startup (`_auto_migrate_columns` in `database.py`). Alembic is available but base schema is created by `Base.metadata.create_all`. Auto-creates user accounts for staff without them. `get_db()` no longer auto-commits — transaction boundaries are managed per-service.
- **Frontend routing**: Protected routes via `router.beforeEach` — checks `requiresAuth`, `mustChangePassword`, and RBAC via `meta.permission` and `meta.roles`. HTTP interceptor auto-attaches Bearer token and handles 401/403.

### Scheduling Engine (critical domain logic)

Located in `backend/app/engine/scheduler.py`. The engine uses a **slot-based rotation** model:

- Staff are grouped into slots (3 slots for 12-person standard scenarios)
- Each slot has a day-group and night-group (new + experienced staff paired)
- Rotation: `(day-1) % n_slots` picks the slot; `rotation_number % 2` determines white/night assignment
- **Cross-month**: Previous month's pairings are persisted in `sch_pairing` table and loaded for 1:1 replacement
- **Special personnel**: Pool members alternate between shifts monthly (e.g., admin ↔ day/night swap)
- **CandidateFilter** pipeline: applies special rules → constraint rules (max per day, max continuous, min interval) before slot selection
- `SchShiftTemplate` controls rotation frequency (`day`/`week`/`month`), leader groups, special groups, and constraint rule binding per template

### Frontend API Layer

`frontend/src/api/` mirrors backend API modules. Each file exports typed functions using the shared axios instance from `api/index.ts` (auto-injects token via `localStorage`, handles errors). `utils/request.ts` has been removed — all API files now use the single `api` instance with `baseURL: '/api'`.

## Database

- **Server:** PostgreSQL (default: `scp:scp2026@localhost:5432/scp_db`)
- **Config:** `backend/.env` (read by pydantic-settings)

Key tables (prefix convention):
- `org_*` — Organization & staff
- `sch_*` — Scheduling domain (templates, constraints, schedules, special rules, pairings)
- `sys_*` — System (users, roles, messages, audit log, config)

## Important Patterns

- All dates use ISO format strings (`YYYY-MM-DD`) in engine internals; database uses `Date` type.
- `SchShiftTemplate` has composite flags: `leader_enabled`, `special_enabled`, `member_enabled` for three-tier staffing.
- `rotation_frequency` fields use string values: `"day"`, `"week"`, `"month"`.
- Manual test scripts (`test_auto_schedule.py`, `test_cross_month.py`) are standalone async Python scripts, not pytest.
