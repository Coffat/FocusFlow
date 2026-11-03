---
name: arch-guard
description: Checks Context-First Modular Monolith and Hexagonal Architecture boundary compliance by verifying import-linter contracts, layer dependencies, and port/adapter patterns. Use after implementing features, during code review, or as part of pre-commit checks.
---

# Architecture Guard (Context-First Modular Monolith + Hexagonal)

Validates that the FocusFlow codebase respects both **Bounded Context Isolation** (`account`, `planning`, `execution`, `evaluation`, `shared_kernel`) and **Hexagonal Layer Purity** (`presentation -> infrastructure -> application -> domain`). Run this skill after any backend code change.

## Automated Fitness Function Check (`import-linter`)

```bash
cd backend && uv run lint-imports
```

This verifies all contracts configured in `backend/pyproject.toml`:
1. **Bounded Context Isolation (`forbidden`)**: No context (`account`, `planning`, `execution`, `evaluation`) may import internal packages (`domain`, `application`, `infrastructure`, `presentation`) of another context. Cross-context imports are strictly limited to `src.<context>.public_api` and `src.shared_kernel`.
2. **Hexagonal Layer Purity (`layers`)**: Within every Bounded Context and `shared_kernel`, dependencies flow strictly inward: `presentation -> infrastructure -> application -> domain`.

## Manual Boundary Checks

### 1. Domain Layer Purity Across All Bounded Contexts

Verify `backend/src/*/domain/` has **zero** imports from outer layers or frameworks:

```bash
grep -rn "from src\..*\.application\|from src\..*\.infrastructure\|from src\..*\.presentation\|import fastapi\|import sqlalchemy\|import pydantic\|import taskiq" backend/src/*/domain/ || echo "✅ Domain layers are pure"
```

**Allowed imports in domain**: `src.shared_kernel.domain.*`, Python stdlib (`dataclasses`, `typing`, `datetime`, `uuid`, `enum`), `uuid6`.

### 2. Cross-Context Isolation Check

Verify no Bounded Context imports another context's internal packages (only `.public_api` is permitted):

```bash
grep -rnE "from src\.(account|planning|execution|evaluation)\.(domain|application|infrastructure|presentation)" backend/src/{account,planning,execution,evaluation}/ || echo "✅ Cross-context isolation is clean"
```

### 3. Application Layer Isolation

Verify `backend/src/*/application/` does not import `infrastructure` or `presentation` or ORM/HTTP frameworks:

```bash
grep -rn "from src\..*\.infrastructure\|from src\..*\.presentation\|import fastapi\|import sqlalchemy" backend/src/*/application/ || echo "✅ Application layers are clean"
```

### 4. Port Definitions (`typing.Protocol`)

Verify all ports in `application/ports/` and `public_api.py` use `typing.Protocol`, not `ABC`:

```bash
grep -rn "from abc import\|class.*ABC" backend/src/*/application/ports/ backend/src/*/public_api.py && echo "⚠️ Use typing.Protocol instead of ABC" || echo "✅ All ports use typing.Protocol"
```

### 5. Repository Return Types (No ORM Leakage)

Verify repositories in `backend/src/*/infrastructure/repositories/` return domain models, not SQLAlchemy ORM models:

```bash
grep -rn "-> .*ORM" backend/src/*/infrastructure/repositories/ && echo "⚠️ Repositories must return Domain Aggregates/Entities" || echo "✅ Repositories return Domain models"
```

## Report Format

After running all checks, report:

```text
Architecture Guard Report
========================
Import-Linter Gate:     ✅ / ❌ (details)
Domain purity:          ✅ / ❌ (details)
Cross-context boundary: ✅ / ❌ (details)
Application isolation:  ✅ / ❌ (details)
Port definitions:       ✅ / ❌ (details)
Repository types:       ✅ / ❌ (details)
```
