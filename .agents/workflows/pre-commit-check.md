---
description: Execute the complete backend and frontend quality verification pipeline (lint, typecheck, arch-guard, tests) before commit or handoff.
---

# /pre-commit-check — Full-Stack Quality Pipeline Workflow

Execute this workflow before every commit or task completion. Every check must pass cleanly with exit code 0.

---

## Phase 1: Pre-Flight

1. **Verify Git Working Tree**:
// turbo
git status --short

---

## Phase 2: Backend Quality Gate

Run each backend verification command sequentially. If any step fails, fix the root cause and restart from that step.

1. **Backend Linter & Formatter**:
// turbo
cd backend && uv run ruff check . && uv run ruff format --check .

2. **Backend Static Type Checking**:
// turbo
cd backend && uv run mypy src

3. **Backend Architecture Boundary Check**:
// turbo
cd backend && uv run lint-imports || true

4. **Deep Architectural Guard Check**:
   - Apply skill `arch-guard` to verify:
     - Domain layer purity (zero framework or outer layer imports).
     - Application layer isolation (no infrastructure or presentation imports).
     - Ports defined with `typing.Protocol`.
     - Repositories return Domain models, not ORM models.

5. **Backend Automated Tests (Unit & Integration)**:
// turbo
cd backend && uv run pytest -q

---

## Phase 3: Frontend Quality Gate

1. **Frontend Static Type Checking**:
// turbo
cd frontend && pnpm typecheck

2. **Frontend Linter**:
// turbo
cd frontend && pnpm lint

3. **Frontend Automated Unit Tests**:
// turbo
cd frontend && pnpm test --run

---

## Phase 4: Git & Security Hygiene Gate

1. **Check for Unwanted or Sensitive Files**:
   - Verify no `.env`, `.pem`, secret tokens, or temporary files (`.DS_Store`, cache dumps) are staged.
// turbo
git status -s | grep -E "\.env|\.pem|\.key|\.log" && echo "⚠️ Sensitive files detected!" || echo "✅ Git working tree clean of secrets"

2. **Check Migration Downgrade Safety** (if Alembic files were created/modified):
   - Ensure newly created migration files contain a fully implemented `downgrade()` function (never empty or `pass`).

---

## Phase 5: Pipeline Verdict & Failure Recovery

1. **Evaluation Rules**:
   - **Zero Tolerance Policy**: Never suppress errors with `# noqa`, `# type: ignore`, or disable linter rules without explicit user approval.
   - Never modify assertions in existing tests just to make a failing build pass.
2. **Pipeline Status Output**:
   Report a clean, tabular summary:
   ```
   Full-Stack Quality Gate Results
   ===============================
   Backend Lint & Format:    ✅ Passed / ❌ Failed
   Backend Typecheck (Mypy): ✅ Passed / ❌ Failed
   Backend Arch Guard:       ✅ Passed / ❌ Failed
   Backend Tests (Pytest):   ✅ Passed / ❌ Failed
   Frontend Typecheck:       ✅ Passed / ❌ Failed
   Frontend Lint:            ✅ Passed / ❌ Failed
   Frontend Tests (Vitest):  ✅ Passed / ❌ Failed
   Hygiene & Security:       ✅ Passed / ❌ Failed
   ```
