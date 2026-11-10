---
name: api-contract
description: Guide for creating or modifying REST and 2-Stage SSE API endpoints across FocusFlow Bounded Contexts, including Pydantic v2 schemas, FastAPI routers, OpenAPI 3.1 verification, and TypeScript type generation via openapi-typescript.
---

# API Contract Management

Creates or modifies API endpoints inside a Bounded Context (`account`, `planning`, `execution`, `evaluation`) and synchronizes frontend TypeScript types.

## Pre-flight

1. Identify the Use Case (`UC-01`..`UC-19`) and owning Bounded Context (`backend/src/{account,planning,execution,evaluation}/`).
2. Check existing routes in `backend/src/{context}/presentation/routers.py` and `backend/src/main.py`.

## Steps

### 1. Define Pydantic v2 Schemas (`backend/src/{context}/presentation/schemas/`)

- Create request/response schemas in `backend/src/{context}/presentation/schemas/`.
- Naming convention: `Create{Resource}Request`, `Update{Resource}Request`, `{Resource}Response`.
- Use `model_config = ConfigDict(from_attributes=True)` when mapping from Domain/DTO objects.

### 2. Create/Update FastAPI Router (`backend/src/{context}/presentation/routers.py`)

- Standard CRUD endpoints under `/api/v1/{resource}` (`201` for create, `200` for get/update, `204` for delete).
- For AI generation endpoints (`ADR-005` 2-Stage SSE):
  - **Stage 1 (`POST /api/v1/{resource}/generate-jobs`)**: Reserves ACID AI Quota (`202 Accepted`) and returns `{ "job_id": "...", "reservation_id": "...", "stream_url": "..." }`.
  - **Stage 2 (`GET /api/v1/{resource}/generate-jobs/{job_id}/stream`)**: Streams Server-Sent Events (`text/event-stream`).

### 3. Wire Composition Root (`backend/src/{context}/presentation/deps.py` & `backend/src/main.py`)

- Wire `AsyncSession` -> Repository -> Use Case in `presentation/deps.py`.
- Ensure the context router is included in `backend/src/main.py`.

### 4. Sync Frontend OpenAPI Types (`openapi-typescript`)

1. Start the backend or export OpenAPI JSON:
   ```bash
   cd backend && uv run uvicorn src.main:app --reload
   ```
2. Generate TypeScript definitions in `frontend/`:
   ```bash
   cd frontend && npm run gen:api-types
   ```
3. Update `frontend/src/app/core/constants/api-endpoints.ts` and the corresponding Angular service.

## Verification

- `cd backend && uv run pytest -q` — API tests pass.
- `cd backend && uv run lint-imports` — Hexagonal & Context boundaries remain intact.
