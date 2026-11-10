---
name: srs-trace
description: Traces functional requirements from SRS through UML diagrams to code implementation. Use when verifying that code matches SRS requirements, checking UML diagram consistency, or detecting drift between design and implementation.
---

# SRS Traceability Check

Traces a requirement from SRS → UML → code to verify consistency and detect drift. This is critical for the graduation project's documentation integrity.

## Inputs

- **FR code** (e.g., `FR-PAUSE-002`) or **BUSR** / **OS** code.
- If not provided, ask the user.

## Steps

### 1. Locate Requirement in SRS

- Open `docs/srs/srs-v1.0.md`.
- Find the exact FR/BUSR/OS section.
- Extract: preconditions, main flow, exception flows, acceptance criteria.

### 2. Check UML Diagrams

For the identified requirement, verify the following exist and are consistent:

| Diagram | Location | What to check |
|---------|----------|--------------|
| Use Case | `docs/uml/use-case-specifications.md` | Actor, preconditions, flow match SRS |
| Sequence | `docs/uml/sequence-diagrams.md` | Message flow matches SRS main flow |
| Class | `docs/uml/class-diagrams.md` | Entity attributes/methods match domain model |
| State Machine | `docs/uml/state-machines.md` | State transitions match business rules |

### 3. Trace to Code Implementation

Map each SRS flow step to actual code:

| SRS Step | Expected Code Location |
|----------|----------------------|
| Domain entity / attributes | `backend/src/domain/models/` |
| Business rule / validation | `backend/src/domain/services/` or domain model method |
| Use case orchestration | `backend/src/application/use_cases/` |
| Port interface | `backend/src/application/ports/` |
| Repository / adapter | `backend/src/infrastructure/` |
| API endpoint | `backend/src/presentation/api/routes/` |
| Frontend component | `frontend/src/app/features/` |

### 4. Detect Drift

Report any inconsistencies:

- **SRS ↔ UML drift**: Diagram shows flow/entity not in SRS, or vice versa.
- **UML ↔ Code drift**: Class diagram shows method not implemented, or code has method not in diagram.
- **Missing implementation**: FR step exists in SRS but no corresponding code.
- **Extra implementation**: Code exists with no traceability to any FR.

## Report Format

```
SRS Traceability Report — {FR-CODE}
====================================
Requirement: {title}
Status: ✅ Fully traced / ⚠️ Partial / ❌ Missing

UML Coverage:
  Use Case:      ✅ / ❌ (notes)
  Sequence:      ✅ / ❌ (notes)
  Class:         ✅ / ❌ (notes)
  State Machine: ✅ / N/A (notes)

Code Coverage:
  Domain model:    ✅ file.py (notes)
  Use case:        ✅ file.py (notes)
  API endpoint:    ✅ file.py (notes)
  Frontend:        ✅ / ❌ (notes)

Drift Detected:
  - {description of inconsistency}
```
