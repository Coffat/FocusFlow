---
description: Implement a Functional Requirement (FR) from SRS specification to verified code adhering to Context-First Modular Monolith and Hexagonal Architecture.
---

# /implement-fr — Senior Feature Implementation Workflow

Execute this workflow when developing any new functional requirement (FR, BUSR, or OS) in FocusFlow.

---

## Phase 1: Pre-Flight & Context Ingestion

1. **Identify Requirement Identifier**:
   - Check if an FR code was provided (e.g., `FR-PAUSE-002`, `FR-AVAIL-001`, or UC-01..UC-25). If not provided, ask the user.
2. **Read Specifications & Design Artifacts**:
   - Locate and read the exact requirement in `docs/srs/srs-v1.0.md` (and `docs/srs/` companion docs).
   - Trace associated Business Rules (`BUSR-*`) and Operational Scenarios (`OS-*`).
   - Identify the owning Bounded Context: `account`, `planning`, `execution` (study execution), or `evaluation` (analytics/adaptation), plus `shared_kernel`.
   - Check `docs/engineering/known-design-corrections.md` and skill reference `spec-conflicts.md` to ensure the feature does not contradict recorded architectural corrections.
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
   - Identify context boundaries and layer impacts:
     - Target Bounded Context: `backend/src/<context>/` (`account`, `planning`, `execution`, `evaluation`) or `shared_kernel`.
     - Cross-Context Boundary Rules:
       - Cross-context reads MUST invoke Query Ports exposed in `src.<context>.public_api` (never import internal packages across contexts).
       - Cross-context writes / reactions MUST use Outbox domain events via `uow.collect_domain_events(agg)` (never direct cross-context calls or Redis dual-writes).
     - Layer impacts within each Bounded Context (`presentation -> infrastructure -> application -> domain`):
       - `domain`: Pure Python entities, Value Objects, Domain Exceptions, Domain Events (zero I/O, no framework imports, no direct `datetime.now()` calls).
       - `application`: Port Protocols (`typing.Protocol`), Use Cases (orchestrated in `async with uow:`), DTOs.
       - `infrastructure`: Database ORM models (SQLAlchemy 2.0 `Mapped[]`), Repositories (add/flush only, mapping ORM ↔ Domain), External adapters.
       - `presentation`: Pydantic v2 Request/Response schemas, FastAPI routers, `deps.py` (Composition Root).
3. 🛑 **HARD GATE — Stop & Ask User if ANY of the following occur**:
   - SRS specifications contradict UML diagrams or existing code.
   - Ambiguities in business rules or acceptance criteria affect implementation.
   - Requirement implies a new external dependency, infrastructure service, or database schema change (altering 24 tables or 3NF/BCNF constraints).
   *Do NOT make assumptions or proceed with implementation until resolved.*

---

## Phase 3: Phased Implementation

Always implement inward-to-outward or test-first adhering to Context-First Modular Monolith rules. Do not leak layers or boundaries.

1. **Database Schema & Migrations** (if persistent state changes):
   - Apply skill `db-change`.
   - Update ORM models in `backend/src/<context>/infrastructure/orm/` using SQLAlchemy 2.0 `Mapped[]` style (preserving 24 tables, no cross-context relationship/JOIN).
   - Generate and review Alembic migration (verify bidirectional upgrade/downgrade).
   - Sync schema with `docs/database/schema.sql`.
2. **Core Domain & Application Layer**:
   - Apply skill `focusflow-backend`.
   - Implement plain dataclass models and aggregates in `backend/src/<context>/domain/models/` (pure Python, zero framework imports, no I/O, inject Clock/time).
   - Define Ports in `backend/src/<context>/application/ports/` as `typing.Protocol` (never `abc.ABC`).
   - Implement Use Cases in `backend/src/<context>/application/use_cases/` accepting/returning DTOs, managing transactions via `AsyncUnitOfWork`, enforcing IDOR checks (`resource.user_id == current_user.id`), and emitting Outbox events via `uow.collect_domain_events(agg)`.
   - Expose cross-context read contracts in `backend/src/<context>/public_api.py` via Query Ports and immutable DTOs if other contexts need this data.
   - Write comprehensive unit tests for domain entities, invariants, and use cases with mocked ports.
3. **Infrastructure Adapters**:
   - Implement repository adapters in `backend/src/<context>/infrastructure/repositories/` mapping ORM models ↔ Domain models (never leaking ORM instances to upper layers, `add()`/`flush()` only, no `commit()`).
   - Implement external adapters (AI via `LLMProviderPort`, caching, Taskiq background workers) in `backend/src/<context>/infrastructure/adapters/`.
4. **Presentation & API Contract**:
   - Apply skill `api-contract`.
   - Create Pydantic v2 schemas in `backend/src/<context>/presentation/schemas/`.
   - Implement FastAPI route in `backend/src/<context>/presentation/routers.py` and register dependencies in `backend/src/<context>/presentation/deps.py` (Composition Root).
   - Regenerate TypeScript types via `openapi-typescript`: run `npm run api:gen` in `frontend/` to update `frontend/src/app/core/api/schema.d.ts`. Never write handwritten interfaces for API data.
5. **Frontend UI Implementation** (if user-facing):
   - Apply skill `focusflow-frontend`.
   - Implement within target feature slice in `frontend/src/app/features/<slice>/` (`auth`, `dashboard`, `planning`, `workspace`, `calendar`, `tasks`, `analytics`, `settings`, `admin`).
   - Angular 21+ Standalone, Zoneless (`provideZonelessChangeDetection`), `OnPush` change detection.
   - Signal-based state management (`signal`, `computed`, `linkedSignal`, `input()`, `output()`, `model()`) — no NgRx, no `BehaviorSubject` for state.
   - Modern control flow: `@if`, `@for(track)`, `@switch`, `@defer`.
   - PrimeNG v21 UI components, Tailwind CSS v4 layout/styling using semantic CSS variables, Lucide icons (`lucide-angular`).
   - Two-stage SSE streaming for AI jobs (`POST` -> 202 `{job_id}` -> `GET .../stream` SSE), human-in-the-loop draft review before apply (BUSR-02).
   - Handle all UI states: loading, empty, error (with `correlation_id`), offline, disabled. Ensure a11y (Lighthouse ≥ 90) and responsive 375–1024px.

---

## Phase 4: Quality & Architectural Gates

Run all automated verification steps sequentially. If any step fails, fix the root cause and restart from that step.

1. **Context & Hexagonal Boundary Verification**:
   - Apply skill `arch-guard`.
   - Run `cd backend && uv run lint-imports` to ensure 0 broken contracts (context isolation + layer purity).
   - Verify zero ORM/framework leakage into domain or application layers.
2. **Execute Full Pre-Commit Suite**:
   - Run workflow `/pre-commit-check`.

---

## Phase 5: Traceability, Packaging & Delivery

1. **Update Documentation & Traceability**:
   - If schema changed, verify `docs/database/schema.sql` reflects current state.
   - If UML or class structure evolved, record delta for diagram updates.
2. **Senior Handoff Report**:
   - Provide a concise summary containing:
     - **Requirement Covered**: `FR-XXX` (Title & Scope) / `UC-XX`.
     - **Bounded Context**: Target context (`account`, `planning`, `execution`, `evaluation`).
     - **Changes Made**: File list grouped by Context and Layer (`domain`, `application`, `infrastructure`, `presentation`, `frontend`).
     - **Tests Added**: Unit & integration tests created with test coverage summary.
     - **Architecture Audit**: `arch-guard` results (`lint-imports`).
     - **Draft Conventional Commit**: e.g., `feat(execution): implement pause session domino shift (FR-PAUSE-002)`.
