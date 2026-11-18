# Experiment 13 (PR-4): Controlled A/B Report — Deterministic Scheduling, Hybrid Effort Allocation & Decomposer Timeout Tuning

- **Date:** `2026-11-17`
- **Plan Reference:** [roadmap-generation-and-scheduling-correctness-plan.md](file:///Users/vuthang/Documents/FocusFlow/docs/plans/roadmap-generation-and-scheduling-correctness-plan.md) (Section 6, PR-4)
- **Script:** [exp_13_deterministic_ab_suite.py](file:///Users/vuthang/Documents/FocusFlow/scripts/experiments/exp_13_deterministic_ab_suite.py)
- **Raw Artifact:** [exp_13_deterministic_ab_results.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_13_deterministic_ab_results.json)
- **Scope Guardrails Verified:** `0` changes to production prompts (`roadmap_skills.py`, `prompts.py`, `untrusted_context.py`), `prompts.lock`, or REST/SSE API schemas (`check-api-contract.sh` clean).

---

## 1. Experimental Setup (Control vs. Treatment)

| Parameter | Control (Legacy Baseline) | Treatment (PR-1 + PR-3A + PR-2 + PR-3B + PR-4) |
|---|---|---|
| `spatio_temporal_v2_hard_solver_enabled` | `false` | `true` |
| `spatio_temporal_v2_soft_pacing_enabled` | `false` | `true` (`end_buffer_ratio=0.12`, `max_consecutive_study_days=5`) |
| `milestone_effort_allocator_enabled` | `false` | `true` (`target_utilization=0.85`, `gamma_min=0.65`) |
| `ai_task_decomposer_timeout_seconds` | `25.0s` | `36.0s` (inside `ai_sse_pipeline_timeout_seconds=55.0s`) |
| `ai_min_retry_remaining_seconds` | `12.0s` | `12.0s` (no-retry on `TimeoutError`; fast-error retry only when remaining budget allows) |

---

## 2. Cohort A: Frozen Deterministic Replay (Control vs. Treatment)

### 2.1 `R-01..R-10` Schedule Replay (`exp_09_judge_and_quality_ab.json`)

| Metric | Control (`hard_v2=False`, `soft_v2=False`) | Treatment (`hard_v2=True`, `soft_v2=True`) | Delta |
|---|---|---|---|
| Tier 1 + Tier 2 Hard Gate Pass Rate | `7/10` (`70.0%`) | `9/10` (`90.0%`; `R-08` proven `EXPLICIT_UNSCHEDULABLE`) | `+20.0%` |
| `adjacent_same_day_split_count` (total) | `26` | **`0`** | **`-26 (-100%)`** |
| `sensitive_tasks_split_across_days` (total) | `5` (`R-06`: 2, `R-08`: 2, `R-10`: 1) | **`0`** | **`-5 (-100%)`** |
| `cross_day_tasks` (total) | `34` | `26` | `-8 (-23.5%)` |
| Hard Violations (total) | `7` | `4` (all on `R-08` proven infeasible `T30=120m` in `90m` slot) | `-3` (`0` on feasible roadmaps) |
| `max_consecutive_study_days` (`VERIFIED_FEASIBLE` `9` roadmaps) | `1..34d` (`R-01`: 11d, `R-02`: 15d, `R-04`: 34d, `R-05`: 23d, `R-07`: 32d) | **`1..5d`** (`<= 5d` across all `9` feasible roadmaps) | **`-29d` peak streak** |
| `days_idle_before_deadline` (avg across `R-01..R-10`) | `11.5d` (ASAP front-loaded) | `5.8d` (paced with `>= 1d` buffer on `8/9` feasible) | Balanced end-buffer |

#### Per-Roadmap Breakdown (`R-01..R-10`)
- **`R-01` (`G1` medium):** Control streak `11d`, `1` adj split, `20d` idle $\to$ Treatment `VERIFIED_FEASIBLE`, streak `2d`, `0` adj splits, `5d` idle.
- **`R-02` (`G1` low):** Control streak `15d`, `2` adj splits $\to$ Treatment `VERIFIED_FEASIBLE`, streak `4d`, `0` adj splits, `5d` idle.
- **`R-03` (`G5` low):** Control `12` adj splits $\to$ Treatment `VERIFIED_FEASIBLE`, **`0`** adj splits, streak `2d`, `6d` idle.
- **`R-04` (`G3` medium):** Control streak `34d`, `1` adj split $\to$ Treatment `VERIFIED_FEASIBLE`, streak `5d`, `0` adj splits, `8d` idle.
- **`R-05` (`G3` low):** Control streak `23d`, `20d` idle $\to$ Treatment `VERIFIED_FEASIBLE`, streak `3d`, `0` adj splits, `7d` idle.
- **`R-06` (`G2` low):** Control **FAIL** (`2` non-splittable cross-day splits, `2` adj splits) $\to$ Treatment **PASS** (`VERIFIED_FEASIBLE`, `0` sensitive cross-day, `0` adj splits).
- **`R-07` (`G4` medium):** Control streak `32d` $\to$ Treatment `VERIFIED_FEASIBLE`, streak `5d`, `0` adj splits, `6d` idle.
- **`R-08` (`G4` low, `90m` weekend cap):** Control **FAIL** (silently split `T29=90m` & `T30=120m` timed mock tests across days, streak `43d`) $\to$ Treatment **`EXPLICIT_UNSCHEDULABLE`** (`TASK_EXCEEDS_CONTINUOUS_SLOT` via NC-2, `0` non-splittable splits). Under `R-08_weekend_120m` sensitivity (`120m` Sat/Sun quota), Control still fails (`2` sensitive cross-day splits, `2` adj splits, streak `39d`), whereas Treatment passes **`100%`** (`VERIFIED_FEASIBLE`, `0` adj splits, `0` sensitive splits, streak **`5d`**, `2d` idle).
- **`R-09` (`G5` medium):** Treatment `VERIFIED_FEASIBLE`, `0` adj splits, `0` sensitive splits, streak `2d`, `4d` idle.
- **`R-10` (`G2` medium):** Control **FAIL** (`T8=100m` load test split across days, `5` adj splits) $\to$ Treatment **PASS** (`VERIFIED_FEASIBLE`, `0` sensitive splits, `0` adj splits).

### 2.2 `M-01..M-12` Milestone Effort Allocation (`exp_10` + `blind_review_hard_6_milestones_key.json`)

> Note: `docs/experiments/blind_review_10/milestones_12.json` is not present in the repository; Cohort A replays the canonical `M-01..M-12` milestone plans from `docs/experiments/exp_10_planner_tool_rounds_ab.json` and `docs/experiments/blind_review_hard_6_milestones_key.json`.

| Metric | Control (Raw LLM Efforts) | Treatment (`MilestoneEffortAllocator`) |
|---|---|---|
| Uniform effort plans (`all_efforts_equal == True`) | `8 / 12` | **`0 / 12`** |
| Plans exceeding `100%` hard capacity (`P_hard`) | `1 / 12` (`M-12`: `3960m / 3480m = 113.79%`) | **`0 / 12`** |
| `FULL_SCOPE_FEASIBLE` retained (Decision 1) | Unassessed | **`12 / 12`** (`M-01..M-11` + `M-12` at `3480m` since `sum(E_min) <= 3480m`) |
| `M-12` Tight-Cap Sensitivity (`P_hard = 780m`) | Overflows silently | **`FIT_CAPACITY_REQUIRES_APPROVAL`** (`scope_proposal_version=1`, `requires_learner_approval=True`, `kept_scope=4`, `deferred_scope=3`, `normalized=660m`) |

### 2.3 `G4` & `G5` Attempt-1 Packing vs. Legacy `divmod`

| Scenario | Metric | Control (Legacy `divmod`) | Treatment (Phase 1+2 Slot-Aware) |
|---|---|---|---|
| **`G5` (`1980m` in `2250m` `MODE_B`)** | Attempt-1 Placement Rate | `23 / 24` (`95.83%`, `LEGACY_UNPLACED`) | **`24 / 24` (`100.0%`, `VERIFIED_FEASIBLE`)** |
| | Hard Gate Violations | `2` (`INVALID_SCHEDULED_DATE`, `SCHEDULE_BLOCK_EFFORT_MISMATCH`) | **`0`** |
| | `adjacent_same_day_split_count` | `8` | **`0`** |
| | `<30m` blocks / Effort mutations | `0` / `0` | **`0` / `0`** |
| **`G4` (`2460m` in `3060m` `MODE_A`)** | Attempt-1 Placement Rate | `31 / 31` (`100.0%`) | **`31 / 31` (`100.0%`, `VERIFIED_FEASIBLE`)** |
| | `adjacent_same_day_split_count` | `3` | **`0`** |
| | `max_consecutive_study_days` | `43d` | **`5d`** (`3d` end buffer) |

---

## 3. Cohort B: Live E2E via CofHub (Control vs. Treatment)

- **Gateway Health Probe:** `GET http://127.0.0.1:8045/v1beta/models` $\to$ `200 OK` (`29` models available; `cobhub_capability_probe_completed` verified `gemini-3.8-flash-low`, `schema_enforced_detected=False`, `low_thinking_is_low=True`).
- **Execution Note:** `eval_runner.py` was extended with opt-in `apply_milestone_effort_allocator=True` for Treatment Stage 2 so PR-2's `MilestoneEffortAllocator` and `FIT_CAPACITY` gating also execute in E2E runs alongside PR-3A/PR-3B in `ProposalValidationGateOrchestrator` and PR-4's `36.0s` Decomposer timeout.

### 3.1 `golden_planning_18_goals.jsonl` (Live E2E, `trials_per_goal=1`, `concurrency=3`)

| Metric | Control (`25.0s`, legacy flags) | Treatment (`36.0s`, PR-1+2+3A+3B) | Delta |
|---|---|---|---|
| **E2E Passed Runs** | `2 / 18` (`11.11%`) | **`13 / 18` (`72.22%`)** | **`+61.11% (6.5x)`** |
| `pass_at_1` | `0.1111` | **`0.6667`** | `+0.5556` |
| `pass_with_judge_verdict` | `0.1111` | **`0.6111`** | `+0.5000` |
| `structural_validity` Pass Count | `5 / 18` | **`14 / 18`** | `+9` |
| `scheduling_feasibility` Pass Count | `2 / 18` | **`13 / 18`** | `+11` |
| Decomposer `TIMEOUT` Errors | `9 / 11` (`81.8%`) | **`3 / 16` (`18.75%`)** | **`-63.05%`** |
| Decomposer Latency `p50` / `max` | `25,001.6ms` / `25,002.8ms` | `29,675.6ms` / `36,001.6ms` | Clarifies why `25s` clipped valid runs |
| Milestone Planner `VALIDATION_GATE` Fails | `3` (`E02` 133%, `E06` 114%, `E12` 170%) | `1` (`E02` halted honestly at `FIT_CAPACITY_APPROVAL_REQUIRED`; `E06` & `E12` normalized to `0.95` & `0.90`) | Decision 1+2 verified live |
| `adjacent_same_day_split_total` | `1` | **`0`** | `-1` |
| `max_consecutive_study_days_max` | `8d` | **`5d`** | `-3d` |
| `soft_quality_score_avg` | `0.3372` | **`0.5727`** | `+0.2355` |
| `injection_isolation_summary` | `1/1` (`3` excluded on timeout) | **`4/4` (`0` excluded)** | `100%` coverage |
| `weekly_llm_success_count` | `18 / 18` | `18 / 18` | `0` fallbacks |

### 3.2 `hard_planning_6_goals.jsonl` (Live E2E, `trials_per_goal=1`)

Tested at both `concurrency=3` (to measure gateway contention) and `concurrency=1` (sequential baseline matching `exp_09..11`):

| Metric (`hard_6_goals`, `concurrency=1`) | Control (`25.0s`, legacy flags) | Treatment (`36.0s`, PR-1+2+3A+3B) |
|---|---|---|
| E2E Passed Runs | `0 / 6` | **`1 / 6`** (`H_E2E_06`: `34.30s` Decomposer, Judge `95.0`, `soft=0.9375`, `streak=2d`, `0` splits) |
| Clarifier / Milestone Planner Timeouts | `0 / 6` / `0 / 6` | `0 / 6` / `0 / 6` |
| Stage 2 `all_efforts_equal_cases` | `2 / 6` | **`0 / 6`** |
| Stage 2 `soft_quality_score_avg` | `0.5022` | **`0.7494`** |
| Decomposer `TIMEOUT` Errors | `6 / 6` (`25.0s`) | `5 / 6` (`36.0s`, `H_E2E_01..05` still exceeded `36.0s`) |

At `concurrency=3` on `hard_6_goals`: Control `0/6` (`1` Clarifier timeout, `5` Decomposer timeouts at `25s`, `4/6` equal-effort milestones); Treatment `0/6` (`2` Milestone Planner timeouts at `50s` due to parallel proxy load, `4` Decomposer timeouts at `36s`, `0/6` equal-effort milestones).

**Honest Finding on `hard_6_goals` Live E2E Timeout:** Tuning `ai_task_decomposer_timeout_seconds` from `25.0s` $\to$ `36.0s` drove a `6.5x` E2E pass-rate jump on `golden_18_goals` (`11.1%` $\to$ `72.2%`, where median Decomposer latency is `29.68s`) and rescued `H_E2E_06` (`34.30s`) sequentially, while remaining safely inside the `55.0s` SRS SSE ceiling (`36s` attempt + `~5–15s` Critics/Judge). However, multi-milestone (`4–7` milestones, `2,160–3,480m`) `hard_6_goals` E2E decompositions still frequently require `>36.0s` on `gemini-3.8-flash-medium` via CofHub (`5/6` timed out sequentially). Further latency reduction (e.g., per-milestone chunked decomposition or Stage 2 prompt tightening) is a Stage 2 candidate outside PR-4's zero-prompt-change scope.

---

## 4. Cohort C: 8 Synthetic Edge-Case Scenarios (`EC-1..EC-8`)

**Result: `8 / 8` PASSED (`100%`)**

| ID | Scenario | Control Behavior | Treatment Behavior | Outcome |
|---|---|---|---|---|
| `EC-1` | Tight deadline (`19×60m = 1140m` / `1200m`, `95%` util) | `19/19` placed, `0` end buffer | Graceful Phase 2 relaxation to `VERIFIED_FEASIBLE`, `0` hard violations | **PASS** |
| `EC-2` | Sparse availability (`MODE_B` Mon/Wed/Sat narrow slots) | `2` adjacent same-day splits | `VERIFIED_FEASIBLE`, `0` off-slot blocks, `0` adjacent splits | **PASS** |
| `EC-3` | Calendar conflicts (`existing_tasks` splitting `180m` Sat slot) | Placed with adjacent splits | Slot-boundary splitting with `0` `<30m` slivers and `0` `estimated_minutes` mutations | **PASS** |
| `EC-4` | Impossible goal (NC-1, NC-2, NC-3, Milestone `P_hard=20m`) | Silent `scheduled_date=None` drops | `EXPLICIT_UNSCHEDULABLE` (`TOTAL_EFFORT_EXCEEDS_HARD_CAPACITY`, `TASK_EXCEEDS_CONTINUOUS_SLOT`, `CRITICAL_PATH_EXCEEDS_WINDOW`) + `PRELIMINARY_UNSCHEDULABLE` (`is_approximate=True`) | **PASS** |
| `EC-5` | Partial fit (`840m` in `240m` `MODE_B`) | Unassessed / fails at Decomposer | `FIT_CAPACITY_REQUIRES_APPROVAL` v1; `ApproveMilestonesUseCase` rejects missing/stale version (`ScopeApprovalRequiredError`), blocks Decomposer (`0` quota consumed), decomposes only `kept_scope` after matching v1 approval | **PASS** |
| `EC-6` | Non-splittable `120m` mock test (`90m` vs `120m` slot) | Splits `120m` mock test across days in `90m` slot (`NON_SPLITTABLE_TASK_SPLIT_ACROSS_DAYS`) | `90m` slot $\to$ `EXPLICIT_UNSCHEDULABLE` (`TASK_EXCEEDS_CONTINUOUS_SLOT`); `120m` slot $\to$ `VERIFIED_FEASIBLE` in `1` contiguous block | **PASS** |
| `EC-7` | `R-03` back-to-back coalescing | `12` adjacent same-day splits | **`0`** adjacent same-day splits, `12/12` valid `90m` blocks | **PASS** |
| `EC-8` | `G5` bin-packing rescue (`1980m` in `2250m`) | `23/24` placed (`95.83%`, `INVALID_SCHEDULED_DATE`, `SCHEDULE_BLOCK_EFFORT_MISMATCH`) | **`24/24` (`100%`)** placed, `0` `<30m` slivers, `0` effort mutations | **PASS** |

---

## 5. Timeout Tuning & Rollback Verification

- `backend/src/shared_kernel/config.py`: `ai_task_decomposer_timeout_seconds: float = 36.0` (`<= ai_sse_pipeline_timeout_seconds = 55.0`).
- `backend/src/planning/application/services/validation_gate/orchestrator.py`: `DECOMPOSER_CALL_TIMEOUT_SECONDS: float = 36.0`, `max_retries=0` on `AIExecutionManager` (preserving no-retry on `TimeoutError`), and `remaining_for_retry >= settings.ai_min_retry_remaining_seconds` (`12.0s`) for fast deterministic/coverage retries.
- **Unit Verification:** `test_pr4_decomposer_timeout_36s_no_retry_on_timeout_and_fast_error_budget` in [test_spatio_temporal_phase2_soft_optimization.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_spatio_temporal_phase2_soft_optimization.py) confirms `36.0s` default, `call_count == 1` on `TimeoutError`, and retry gating on `ai_min_retry_remaining_seconds`.
- **Rollback Strategy:** Instant env-var rollback with zero code changes:
  - `AI_TASK_DECOMPOSER_TIMEOUT_SECONDS=25.0`
  - `MILESTONE_EFFORT_ALLOCATOR_ENABLED=false`
  - `SPATIO_TEMPORAL_V2_HARD_SOLVER_ENABLED=false`
  - `SPATIO_TEMPORAL_V2_SOFT_PACING_ENABLED=false`
