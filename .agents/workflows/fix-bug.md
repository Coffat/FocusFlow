---
description: Systematically isolate, reproduce, fix, and verify bugs with root cause analysis and zero regression.
---

# /fix-bug — Senior Bug Resolution Workflow

Execute this workflow whenever diagnosing and fixing defects, regressions, or unexpected system behavior in FocusFlow.

---

## Phase 1: Pre-Flight & Triage

1. **Capture Incident Details**:
   - Identify affected component: Backend API, Celery worker, Domain logic, Database, or Frontend UI.
   - Clarify symptoms: Error logs, stack traces, expected vs actual behavior, environment.
2. **Check Current Working Tree**:
// turbo
git status --short

---

## Phase 2: Root Cause Analysis & Reproduction (TDD Red)

1. **Trace Call Stack & Execution Flow**:
   - Trace backwards from the failure point through the hexagonal layers (Presentation/Router → Use Case → Domain Model/Service → Infrastructure/Adapter).
   - Check relevant business rules (`BUSR-*`) in `docs/srs/srs-v1.0.md` or technical specifications in `docs/architecture/`.
2. **Author Reproducing Test (MANDATORY)**:
   - Write a minimal failing automated unit or integration test reproducing the exact issue.
   - Run the reproducing test to confirm deterministic failure:
// turbo
cd backend && uv run pytest path/to/reproducing_test.py -v
   *(For frontend issues, write a failing Vitest test in `frontend/src/app/.../*.spec.ts`).*
3. 🛑 **HARD GATE — Stop & Ask User if ANY of the following occur**:
   - The bug is caused by contradictory specifications in the SRS, UML, or ADRs.
   - Fixing the bug requires changing a public API schema, database schema, or breaking existing contracts.
   - The intended correct behavior is ambiguous.
   *Do NOT guess or alter business rules silently.*

---

## Phase 3: Surgical Implementation (TDD Green)

1. **Implement Minimal Root-Cause Fix**:
   - Fix the defect at its actual origin (e.g., Domain invariant validation, edge-case math in domain service, or query mapping in repository).
   - **Do NOT** patch symptoms in the outer layer (e.g., do not swallow exceptions in Presentation or hack frontend types).
   - Follow strict minimal diff principles: touch only necessary code, no unsolicited formatting or refactoring.
2. **Verify Fix**:
   - Re-run the reproducing test to confirm it now passes:
// turbo
cd backend && uv run pytest path/to/reproducing_test.py -v

---

## Phase 4: Regression Testing & Quality Gates

1. **Run Full Subsystem Suite**:
   - Run all existing tests for the affected module to guarantee zero regression:
// turbo
cd backend && uv run pytest tests/ -k "relevant_module" -v
2. **Run Architecture Boundary Check**:
   - Apply skill `arch-guard` to ensure the bugfix did not introduce boundary leaks or illegal cross-layer imports.
3. **Execute Pre-Commit Verification**:
   - Run workflow `/pre-commit-check`.

---

## Phase 5: Packaging & Senior Post-Mortem Handoff

1. **Provide Senior Bug Handoff Report**:
   - **Root Cause**: Deep explanation of why the bug occurred (underlying invariant failure, edge case, or state race).
   - **Resolution Summary**: Architectural description of the fix across touched layers.
   - **Regression Defense**: Path and explanation of the newly added automated regression test.
   - **Quality Verification**: Results of `/pre-commit-check` and `arch-guard`.
   - **Draft Conventional Commit**: e.g., `fix(domain): enforce non-negative buffer minutes in calendar shift (BUSR-04)`.
