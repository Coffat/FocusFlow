---
description: Audit traceability and detect drift between SRS requirements, UML models, database schemas, and codebase implementation.
---

# /audit-traceability — Specification & Model Traceability Audit Workflow

Execute this workflow to verify the integrity, consistency, and completeness of FocusFlow's requirements, architectural models, and codebase. Essential for academic milestone reviews and thesis defense preparation.

---

## Phase 1: Pre-Flight & Scope Selection

1. **Select Audit Scope**:
   - Prompt the user to choose:
     - **Full System Audit**: Scans all core requirements and architectural subsystems.
     - **Subsystem Audit**: Scans a specific domain (e.g., `Schedule & Availability`, `Learning Plan`, `AI Adaptation`, `Authentication`).
     - **Specific Requirement**: Focuses on a single `FR-*`, `BUSR-*`, or `OS-*` code.
2. **Catalog Authoritative Sources of Truth**:
   - **Requirements**: `docs/srs/srs-v1.0.md` and `docs/srs/`
   - **Architecture & ADRs**: `docs/decisions/` and `docs/architecture/`
   - **UML Diagrams**: `docs/uml/` (Use Case, Sequence, Class, State Machine)
   - **Database Schema**: `docs/database/schema.sql` and `backend/src/infrastructure/database/orm/`
   - **Implementation**: `backend/src/` and `frontend/src/app/`

---

## Phase 2: Requirements-to-Model Traceability Analysis

Apply skill `srs-trace` to perform bidirectional checks:

1. **Forward Traceability (SRS → UML & Code)**:
   - For each target FR:
     - Is there an associated Use Case Specification in `docs/uml/use-case-specifications.md`?
     - Is there a corresponding Sequence Diagram capturing the main and alternative flows?
     - Are domain entities modeled in Class Diagrams (`docs/uml/class-diagrams.md`)?
     - Does the domain model exist in `backend/src/domain/models/`?
     - Is the use case implemented in `backend/src/application/use_cases/`?
     - Is the API endpoint exposed in `backend/src/presentation/api/routes/`?
2. **Reverse Traceability (Code → SRS)**:
   - Identify unmapped codebase features: Does any route, use case, or Celery task exist that lacks a traceable `FR-*` or `BUSR-*`?

---

## Phase 3: Model-to-Code Drift Detection

1. **Class Diagram vs Domain Entities**:
   - Compare entity attributes and methods in UML Class diagrams against actual Python dataclasses in `backend/src/domain/models/`.
   - Identify missing fields, renamed methods, or structural drift.
2. **Sequence Diagram vs Use Case Flow**:
   - Trace message exchanges in sequence diagrams: Does the Use Case call the exact Port methods in the specified sequence?
3. **Database Schema vs ORM Models**:
   - Cross-check `docs/database/schema.sql` with SQLAlchemy ORM models in `backend/src/infrastructure/database/orm/`.
   - Flag missing tables, mismatched column types, or unindexed foreign keys.
4. 🛑 **HARD GATE — Contradiction Escalation**:
   - If an irreconcilable contradiction is discovered between the SRS, UML, and active code, **STOP**.
   - Do NOT edit code or diagrams automatically. Detail the contradiction and ask the user which artifact is authoritative.

---

## Phase 4: Verification & Test Coverage Audit

1. **Automated Test Mapping**:
   - Verify that each acceptance criterion of the audited FR has an automated test in `backend/tests/` or `frontend/src/`.
2. **Architecture Compliance Check**:
   - Run skill `arch-guard` on the audited subsystem to ensure hexagonal layer compliance.

---

## Phase 5: Graduation Traceability Matrix & Audit Report

Generate a formal thesis-grade traceability report:

```markdown
# 📋 FocusFlow Specification & Traceability Audit Report

- **Scope**: [ Subsystem / FR-ID / Full System ]
- **Date**: YYYY-MM-DD
- **Overall Traceability Score**: [ % ]

## 1. Traceability Matrix
| Requirement ID | Title | Use Case | Sequence | Class Diagram | Code (Backend) | Code (Frontend) | Test Status |
|---|---|---|---|---|---|---|---|
| `FR-XXX-001` | ... | ✅ / ❌ | ✅ / ❌ | ✅ / ❌ | `src/.../` | `app/.../` | ✅ Covered |

## 2. Drift Findings & Discrepancies
### A. Specification ↔ Code Drift
- Discrepancy details (e.g., business rule implemented differently than SRS).

### B. UML Model Drift
- Missing or outdated UML diagrams that need synchronizing with code.

### C. Database Drift
- Discrepancies between `schema.sql` and active ORM models.

## 3. Recommended Remediation Plan
1. [High Priority] Action items to resolve drift before thesis submission.
2. [Medium Priority] Documentation and diagram synchronization.
```
