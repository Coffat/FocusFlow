---
description: Perform an exhaustive Senior Code & Architecture Review before merge or commit, verifying hexagonal boundaries, SRS traceability, and test coverage.
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

## Phase 2: Architectural & Hexagonal Boundary Audit

1. **Execute Architecture Guard**:
   - Apply skill `arch-guard`.
   - Verify strict layer dependency compliance:
     - `backend/src/domain/`: Must have zero dependencies on outer layers (no FastAPI, Pydantic, SQLAlchemy). Plain dataclasses only.
     - `backend/src/application/`: Must depend only on `domain/`. No imports from `infrastructure/` or `presentation/`.
     - `backend/src/application/ports/`: Must define Ports as `typing.Protocol`, never `abc.ABC`.
     - `backend/src/infrastructure/`: Repository adapters must map ORM entities to Domain entities. No ORM models returned to upper layers.
     - `backend/src/presentation/`: Controllers must consume DTOs, inject use cases via `Depends`, and return Pydantic schemas.
2. 🛑 **HARD GATE — Architecture Blocker**:
   - If any cross-layer import violation or layer leakage is detected, immediately mark as **BLOCKED** and detail the exact files and lines violating the boundary.

---

## Phase 3: Specification & Traceability Audit

1. **Verify SRS & UML Alignment**:
   - Apply skill `srs-trace`.
   - Map modified code to the target functional requirement (`FR-*`), business rule (`BUSR-*`), or operational scenario (`OS-*`).
   - Check consistency against UML diagrams in `docs/uml/` (Sequence, Class, State Machine).
2. **Check for Unsolicited Changes / Scope Creep**:
   - Verify all code changes directly support the requirement or fix. Flag any gratuitous refactoring or dead code.
3. 🛑 **HARD GATE — Specification Drift**:
   - If code introduces business logic that diverges from `docs/srs/srs-v1.0.md` without an approved ADR or design correction, flag as a specification contradiction.

---

## Phase 4: Code Quality, Security & Automated Verification

1. **Run Full Verification Pipeline**:
   - Run workflow `/pre-commit-check`.
   - Ensure all linters (Ruff), typecheckers (Mypy, Angular typecheck), and test suites (Pytest, Vitest) exit cleanly with code 0.
2. **Security & Data Sanitization Audit**:
   - Check for hardcoded credentials, unvalidated inputs, unsanitized SQL queries, or missing authorization checks.
3. **Frontend Quality Inspection** (if frontend was touched):
   - Verify Angular rules from `rule.md`: `@if`/`@for` control flow, explicit types (no `any`), PrimeNG component usage, proper subscription cleanup (`takeUntilDestroyed`).

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
| **Hexagonal Boundaries** | ✅ Clean / ❌ Leaks | Purity of Domain, Protocol ports, DTO separation |
| **SRS & UML Traceability** | ✅ Traced / ⚠️ Partial | Alignment with SRS v1.0 and UML diagrams |
| **Testing & Verification** | ✅ Passed / ❌ Failed | Automated test coverage and pre-commit results |
| **Security & Quality** | ✅ Compliant / ⚠️ Minor | Error handling, typing, zero warning policy |

## 3. Actionable Recommendations
- **[Must Fix]**: Critical blockers that must be resolved before commit/merge.
- **[Should Fix]**: Architectural improvements or code quality enhancements.
- **[Nit / Suggestion]**: Minor polish or documentation updates.

## 4. Suggested Conventional Commit
`feat(...)` or `fix(...)`: Detailed message following Conventional Commits format.
```
