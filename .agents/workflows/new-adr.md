---
description: Author a formal Architecture Decision Record (ADR) justifying major technical or architectural choices according to graduation project standards.
---

# /new-adr — Architecture Decision Record Authoring Workflow

Execute this workflow whenever introducing, replacing, or refactoring major architectural patterns, external services, frameworks, concurrency models, or data storage designs in FocusFlow.

---

## Phase 1: Pre-Flight & Trigger Identification

1. **Check Existing Decisions**:
   - List and review all active ADRs in `docs/decisions/`:
// turbo
ls docs/decisions
2. **Determine Next Sequence Number**:
   - Count existing `ADR-xxx-*.md` files and assign the next sequential identifier (e.g., `ADR-011`).
3. **Capture Decision Trigger**:
   - Clarify the architectural challenge or trade-off (e.g., AI caching strategy, token rate-limiting, websocket vs SSE, database indexing strategy).
   - Identify associated functional requirements (`FR-*`) and graduation rubric criteria (e.g., TC2.1, TC2.3).

---

## Phase 2: Options Exploration & Trade-off Analysis

1. **Identify Viable Alternatives**:
   - Formulate at least 2–3 realistic architectural alternatives (e.g., Option A vs Option B vs Option C).
   - For each alternative, assess:
     - Complexity vs Maintainability (team size: 2 graduation students).
     - Hexagonal layer compatibility (domain isolation, testability without real external dependencies).
     - Performance, latency, and resource footprint.
     - Operational overhead (Docker, memory, local development viability).
2. 🛑 **HARD GATE — User Alignment**:
   - Present the alternatives, trade-offs, and recommended choice to the user.
   - Do NOT finalize an ADR until the user confirms the selected decision.

---

## Phase 3: Drafting the ADR Document

Create the document at `docs/decisions/ADR-{NUMBER}-{kebab-case-title}.md` adhering to FocusFlow's standard ADR structure:

```markdown
# ADR-{NUMBER}: {Title of the Architectural Decision}

* **Status:** Approved / Proposed
* **Date:** YYYY-MM-DD
* **Decision Makers:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Evaluation Criteria:** IT Graduation Project Rubric — Criteria TC2.1 & TC2.3
* **Related Requirements:** {Associated FR-*, BUSR-*, or System Non-Functional Requirements}

---

## 1. Context & Problem Statement (Ngữ cảnh & Đặt vấn đề)
- Describe the business and technical context in FocusFlow.
- Detail the challenges, constraints, and why a formal architectural decision is necessary.

## 2. Architectural Decision (Quyết định Kiến trúc)
- State the chosen approach clearly and unambiguously.
- Define which layers of the Hexagonal Architecture are affected (`domain`, `application`, `infrastructure`, `presentation`).

## 3. Options Considered & Comparative Evaluation (Các phương án cân nhắc & So sánh)
- **Option 1 (Chosen)**: Description, pros, cons, and score.
- **Option 2 (Alternative A)**: Description, reasons for rejection.
- **Option 3 (Alternative B)**: Description, reasons for rejection.
- Include a comparative evaluation matrix (Trade-off Matrix) comparing criteria like Complexity, Testability, Performance, and Graduation Rubric alignment.

## 4. Consequences & Trade-offs (Hậu quả & Đánh đổi)
- **Positive Consequences (Lợi ích mang lại)**: What becomes easier or better.
- **Negative Consequences / Trade-offs (Bất lợi & Đánh đổi)**: What becomes harder or requires mitigation.
- **Mitigation Strategy (Chiến lược giảm thiểu rủi ro)**: Concrete technical steps taken to counteract the disadvantages.

## 5. Implementation & Compliance Plan (Kế hoạch Triển khai & Tuân thủ)
- Specific files, modules, or adapters to create or refactor.
- How compliance will be automatically enforced (e.g., via `arch-guard` or automated test suites).
```

---

## Phase 4: Review & Consistency Verification

1. **Consistency Check**:
   - Verify that the new ADR does not silently contradict previous ADRs in `docs/decisions/`.
   - If it supersedes an existing ADR, explicitly update the superseded ADR's status to `Superseded by ADR-xxx`.
2. **Architecture Guard Validation**:
   - Run skill `arch-guard` to ensure current codebase principles remain aligned.

---

## Phase 5: Catalog Update & Handoff

1. **Update ADR Registry**:
   - Update `docs/decisions/README.md` (or index table) to register the newly created ADR with its title, status, and summary.
2. **Senior Delivery Summary**:
   - Provide a brief executive summary of the decision, its key trade-offs, and next implementation steps.
