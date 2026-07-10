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

See `backend/` and `frontend/` directories for project-specific setup.

## Architecture

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

### Database Tables

Tables use prefix conventions: `org_*` (Organization & Staff), `sch_*` (Scheduling), `sys_*` (System), `swap_*` (Swap Management), `export_*` (Export).

## Important Patterns

- All dates use ISO format strings (`YYYY-MM-DD`) in engine internals; database uses `Date` type.
- `SchShiftTemplate` has composite flags: `leader_enabled`, `special_enabled`, `member_enabled` for three-tier staffing.
- `rotation_frequency` fields use string values: `"day"`, `"week"`, `"month"`.
- Manual test scripts (`test_auto_schedule.py`, `test_cross_month.py`) are standalone async Python scripts in repo root, not pytest.
- Frontend API files mirror backend routers exactly; adding a new endpoint requires updates in both `backend/app/api/` and `frontend/src/api/`.
- Views are page-level components; view-specific sub-components live in `[view]/components/`. Only `ConfirmDialog.vue` is a global shared component.
