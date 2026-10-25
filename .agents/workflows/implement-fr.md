---
description: Implement a Functional Requirement (FR) from SRS specification to verified code adhering to Hexagonal Architecture.
---

# /implement-fr — Senior Feature Implementation Workflow

Execute this workflow when developing any new functional requirement (FR, BUSR, or OS) in FocusFlow.

---

## Phase 1: Pre-Flight & Context Ingestion

1. **Identify Requirement Identifier**:
   - Check if an FR code was provided (e.g., `FR-PAUSE-002`, `FR-AVAIL-001`). If not provided, ask the user.
2. **Read Specifications & Design Artifacts**:
   - Locate and read the exact requirement in `docs/srs/srs-v1.0.md` (and `docs/srs/` companion docs).
   - Trace associated Business Rules (`BUSR-*`) and Operational Scenarios (`OS-*`).
   - Check `docs/engineering/known-design-corrections.md` to ensure the feature does not contradict recorded architectural corrections.
3. **Verify Git State**:
// turbo
git status --short

---

## Phase 2: Analysis, Design & Hard Decision Gates

1. **Synthesize Requirement Scope** (keep under 10 lines):
   - Pre-conditions
   - Primary flow
   - Exception flows
   - Acceptance criteria
2. **Model & Architecture Cross-Check**:
   - Invoke skill `srs-trace` to verify if Use Case, Sequence, or Class diagrams exist in `docs/uml/`.
   - Identify layer impacts across the hexagonal architecture:
     - `domain`: Entities, Value Objects, Domain Exceptions, Domain Services.
     - `application`: Port Protocols (`typing.Protocol`), Use Cases, DTOs (`application/dtos/`).
     - `infrastructure`: Database ORM models, Repositories, External AI/Calendar adapters.
     - `presentation`: Pydantic Request/Response schemas, FastAPI routers, Angular UI.
3. 🛑 **HARD GATE — Stop & Ask User if ANY of the following occur**:
   - SRS specifications contradict UML diagrams or existing code.
   - Ambiguities in business rules or acceptance criteria affect implementation.
   - Requirement implies a new external dependency, infrastructure service, or database schema change.
   *Do NOT make assumptions or proceed with implementation until resolved.*

---

## Phase 3: Phased Implementation

Always implement inward-to-outward or test-first. Do not leak layers.

1. **Database Schema & Migrations** (if persistent state changes):
   - Apply skill `db-change`.
   - Update ORM models in `backend/src/infrastructure/database/orm/` using SQLAlchemy 2.0 `Mapped[]` style.
   - Generate and review Alembic migration (verify bidirectional upgrade/downgrade).
2. **Core Domain & Application Layer**:
   - Apply skill `backend-feature`.
   - Implement plain dataclass models in `backend/src/domain/models/` (zero framework imports).
   - Define Ports in `backend/src/application/ports/` as `typing.Protocol`.
   - Implement Use Cases in `backend/src/application/use_cases/` accepting/returning DTOs.
   - Write comprehensive unit tests for domain services and use cases using mocked ports.
3. **Infrastructure Adapters**:
   - Implement repository adapters mapping ORM models ↔ Domain models (never leaking ORM instances).
   - Implement external adapters (AI, caching, workers).
4. **Presentation & API Contract**:
   - Apply skill `api-contract`.
   - Create Pydantic schemas in `backend/src/presentation/api/schemas/`.
   - Implement FastAPI route with dependency injection via `Depends`.
   - Sync TypeScript interfaces in `frontend/src/app/core/models/`.
5. **Frontend UI Implementation** (if user-facing):
   - Apply skill `frontend-feature`.
   - Implement standalone component, signal-based state, PrimeNG UI, SCSS styles, and i18n keys.

---

## Phase 4: Quality & Architectural Gates

Run all automated verification steps sequentially. If any step fails, fix the root cause and restart from that step.

1. **Hexagonal Boundary Verification**:
   - Apply skill `arch-guard` to ensure zero boundary leaks (domain purity, port Protocol, no presentation leaks).
2. **Execute Full Pre-Commit Suite**:
   - Run workflow `/pre-commit-check`.

---

## Phase 5: Traceability, Packaging & Delivery

1. **Update Documentation & Traceability**:
   - If schema changed, verify `docs/database/schema.sql` reflects current state.
   - If UML or class structure evolved, record delta for diagram updates.
2. **Senior Handoff Report**:
   - Provide a concise summary containing:
     - **Requirement Covered**: `FR-XXX` (Title & Scope).
     - **Changes Made**: File list grouped by Hexagonal Layer (`domain`, `application`, `infrastructure`, `presentation`, `frontend`).
     - **Tests Added**: Unit & integration tests created with test coverage summary.
     - **Architecture Audit**: `arch-guard` results.
     - **Draft Conventional Commit**: e.g., `feat(learning-plan): implement pause session domino shift (FR-PAUSE-002)`.
