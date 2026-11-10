---
description: Perform an exhaustive Senior Code & Architecture Review before merge or commit, verifying Context-First Modular Monolith isolation, hexagonal boundaries, SRS traceability, and test coverage.
---

# /review-changes — Senior Code & Architecture Review Workflow

Execute this workflow before staging, committing, or merging changes to ensure compliance with university graduation project rubrics and enterprise engineering standards.

---

## Phase 1: Pre-Flight & Scope Inspection

1. **Inspect Working Tree & Diff**:
// turbo
git status && git diff --stat
2. **Review Detailed Code Changes**:
// turbo
git diff -U3

---

## Phase 2: Architectural, Modular Monolith & Hexagonal Boundary Audit

1. **Execute Architecture Guard**:
   - Apply skill `arch-guard`.
   - Run automated fitness functions:
     ```bash
     cd backend && uv run lint-imports
     ```
     Ensure **0 broken contracts** reported across all Bounded Contexts.
2. **Verify Context-First Modular Monolith Isolation**:
   - **4 Bounded Contexts**: `account`, `planning`, `execution` (study execution), `evaluation` (analytics/adaptation) + `shared_kernel`.
   - **Cross-Context Boundaries**:
     - No context may import internal packages (`domain`, `application`, `infrastructure`, `presentation`) of another context.
     - Cross-context reads MUST only use `src.<context>.public_api` Query Ports returning immutable DTOs.
     - Cross-context writes / reactions MUST use Outbox domain events via `uow.collect_domain_events(agg)`.
     - Zero ORM `relationship()` or cross-context SQL `JOIN` between tables of different contexts.
3. **Verify Hexagonal Layer Purity Within Each Context** (`presentation -> infrastructure -> application -> domain`):
   - `backend/src/<context>/domain/`: Pure Python entities and dataclasses only. Zero dependencies on outer layers or frameworks (no FastAPI, Pydantic, SQLAlchemy, Taskiq, Redis). Zero I/O, no direct `datetime.now()` calls (inject Clock/time parameter).
   - `backend/src/<context>/application/`: Depends only on `domain/` and `shared_kernel`. Zero imports from `infrastructure/` or `presentation/`. No FastAPI, SQLAlchemy, or Taskiq imports.
   - `backend/src/<context>/application/ports/` & `public_api.py`: Ports MUST be defined as `typing.Protocol`, never `abc.ABC`.
   - `backend/src/<context>/infrastructure/`: Repository adapters map ORM models ↔ Domain models without leaking ORM entities to upper layers. Repositories only `add()` and `flush()`, never `commit()` (transactions handled by `AsyncUnitOfWork`).
   - `backend/src/<context>/presentation/`: Controllers consume DTOs and return Pydantic v2 schemas. Dependency injection (`Depends`/`TaskiqDepends`) restricted to `deps.py` (Composition Root).
4. **Security & IDOR Check**:
   - Verify every use case accessing user resources checks `resource.user_id == current_user.id` (returns 404 for unowned resources, avoiding IDOR).
5. 🛑 **HARD GATE — Architecture Blocker**:
   - If any cross-context leakage, cross-layer import violation, or database relationship leak is detected, immediately mark as **BLOCKED** and detail the exact files and lines violating the boundary.

---

## Phase 3: Specification & Traceability Audit

1. **Verify SRS & UML Alignment**:
   - Apply skill `srs-trace`.
   - Map modified code to the target functional requirement (`FR-*`), business rule (`BUSR-*`), or operational scenario (`OS-*`). Use SRS v1.2 UC-01..UC-25 numbering.
   - Check consistency against UML diagrams in `docs/uml/` (Activity, Sequence, Class, State Machine).
2. **Check for Unsolicited Changes / Scope Creep**:
   - Verify all code changes directly support the requirement or fix. Flag any gratuitous refactoring or dead code.
3. 🛑 **HARD GATE — Specification Drift**:
   - If code introduces business logic that diverges from `docs/srs/srs-v1.0.md` without an approved ADR or design correction, flag as a specification contradiction.

---

## Phase 4: Code Quality, Security & Automated Verification

1. **Run Full Verification Pipeline**:
   - Run workflow `/pre-commit-check`.
   - Ensure all linters (Ruff), typecheckers (Mypy `--strict`, Angular typecheck), and test suites (Pytest, Vitest) exit cleanly with code 0.
2. **Security & Data Sanitization Audit**:
   - Check for hardcoded credentials, unvalidated inputs, unsanitized SQL queries, or missing authorization checks.
   - Auth tokens: HttpOnly cookies with `withCredentials: true`, no tokens in `localStorage`.
   - AI endpoints: LLM calls route through `LLMProviderPort` with 2-phase quota reservation (`RESERVE -> COMMIT | RELEASE`), input sanitization via `PromptSanitizer`.
3. **Frontend Quality Inspection** (if frontend was touched):
   - Apply skill `focusflow-frontend`.
   - **Angular 21+ Standalone & Zoneless**: `ChangeDetectionStrategy.OnPush`, `provideZonelessChangeDetection()`, zero `zone.js` dependencies.
   - **Signal State**: State managed with Angular Signals (`signal`, `computed`, `linkedSignal`, `input()`, `output()`, `model()`). No NgRx, no `BehaviorSubject` for state. Subscriptions cleaned up via `toSignal()` or `takeUntilDestroyed()`.
   - **Template Control Flow**: Modern `@if`, `@for(track)`, `@switch`, `@defer`. Zero `*ngIf/*ngFor`.
   - **API Contracts**: All API types strictly derived from `src/app/core/api/schema.d.ts` (generated via `openapi-typescript`). Zero handwritten API interfaces, no `any`.
   - **UI System & Accessibility**: PrimeNG v21 components, Tailwind CSS v4 styling with semantic variables, `lucide-angular` icons. Responsive from 375px to ≥1024px and Lighthouse a11y ≥ 90.

---

## Phase 5: Senior Review Report & Recommendations

Provide a comprehensive, structured code review report using this format:

```markdown
# 🏛️ Senior Architecture & Code Review Report

## 1. Executive Verdict
- **Status**: [ APPROVED | CHANGES REQUESTED | ARCHITECTURAL BLOCKER ]
- **Summary**: Concise assessment of changes, architecture impact, and readiness.

## 2. Review Findings by Category
| Category | Status | Notes / Observations |
|---|---|---|
| **Bounded Context Isolation** | ✅ Clean / ❌ Leaks | Cross-context reads via public_api only, outbox events for writes |
| **Hexagonal Layer Purity** | ✅ Pure / ❌ Leaks | Domain purity, Protocol ports, DTO separation, no ORM leaks |
| **SRS & UML Traceability** | ✅ Traced / ⚠️ Partial | Alignment with SRS v1.2 (UC-01..25) and UML diagrams |
| **Testing & Verification** | ✅ Passed / ❌ Failed | Automated test coverage and pre-commit results |
| **Frontend Signals & Zoneless** | ✅ Compliant / ⚠️ Minor | Angular 21 OnPush, Signals, control flow, schema.d.ts types |
| **Security & Quality** | ✅ Compliant / ⚠️ Minor | HttpOnly cookies, IDOR checks, zero warning policy |

## 3. Actionable Recommendations
- **[Must Fix]**: Critical blockers that must be resolved before commit/merge.
- **[Should Fix]**: Architectural improvements or code quality enhancements.
- **[Nit / Suggestion]**: Minor polish or documentation updates.

## 4. Suggested Conventional Commit
`feat(...)` or `fix(...)`: Detailed message following Conventional Commits format.
```
