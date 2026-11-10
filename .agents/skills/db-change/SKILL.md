---
name: db-change
description: Guide for database schema changes across the 24 PostgreSQL 16 tables (3NF/BCNF), including SQLAlchemy 2.0 ORM models in Bounded Contexts, Alembic migrations, and schema.sql synchronization.
---

# Database Schema Change (24 Tables across 4 Bounded Contexts + Shared Kernel)

Safely modifies the PostgreSQL 16 database schema while preserving **3NF/BCNF** normalization, **UUIDv7** primary keys, and **Bounded Context table ownership**.

## Table Ownership Reference (24 Tables)

- **`shared_kernel`** (`backend/src/shared_kernel/infrastructure/outbox/models.py`): `outbox_events`, `processed_events` (2 tables)
- **`account`** (`backend/src/account/infrastructure/orm/`): `users`, `learner_profiles`, `availabilities`, `availability_slots`, `webcal_tokens`, `ai_quotas`, `ai_quota_reservations`, `ai_usage_logs`, `payment_transactions` (9 tables)
- **`planning`** (`backend/src/planning/infrastructure/orm/`): `goals`, `roadmaps`, `milestones`, `official_schedules`, `tasks`, `task_dependencies`, `schedule_proposals` (7 tables)
- **`execution`** (`backend/src/execution/infrastructure/orm/`): `study_sessions`, `session_tasks`, `study_notes`, `pause_records` (4 tables)
- **`evaluation`** (`backend/src/evaluation/infrastructure/orm/`): `ai_reviews`, `schedule_change_logs` (2 tables)

## Steps

### 1. Update SQLAlchemy 2.0 ORM Model

- Edit or create the ORM model in `backend/src/{context}/infrastructure/orm/` (or `src/shared_kernel/infrastructure/outbox/models.py`).
- Inherit from `src.shared_kernel.infrastructure.database.session.Base`.
- Use SQLAlchemy 2.0 `Mapped[]` + `mapped_column()` with `UUID(as_uuid=True)` and `uuid7` defaults.
- **Architectural Rule**: Physical Foreign Keys (`ForeignKey("users.id")`) are preserved in PostgreSQL for 3NF/BCNF integrity, but **never define cross-context SQLAlchemy `relationship()` attributes** or perform cross-context ORM JOINs.

### 2. Generate & Review Alembic Migration

```bash
cd backend && uv run alembic revision --autogenerate -m "short_description"
```

- Verify `upgrade()` and `downgrade()` are both complete and reversible.
- Test migration lifecycle:
  ```bash
  cd backend && uv run alembic upgrade head
  cd backend && uv run alembic downgrade -1
  cd backend && uv run alembic upgrade head
  ```

### 3. Synchronize DDL & Documentation Artifacts

- Regenerate the documentation DDL file `docs/database/schema.sql` from the migrated database using the dump script:
  ```bash
  ./backend/scripts/dump_schema.sh
  ```
- Update `docs/database/data-dictionary.md` and `docs/database/database-schema-design.md` so the 24-table documentation stays in 100% sync.
- Update ORM <-> Domain mapping methods in `backend/src/{context}/infrastructure/repositories/`.

## Verification

- `cd backend && uv run pytest -q`
- `cd backend && uv run lint-imports`
