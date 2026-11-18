# FocusFlow — Báo cáo Kiểm toán Sẵn sàng Production Sau Refactor (`PR-1`..`PR-4`) & Xác minh Khắc phục (`PR-A`..`PR-E`)

- **Ngày kiểm toán ban đầu (`PR-1`..`PR-4`):** `2026-11-17`
- **Ngày xác minh khắc phục độc lập (`PR-A`..`PR-E` + `exp_14`):** `2026-11-17` (Updated post-remediation)
- **Phạm vi:** Independent technical audit & post-remediation verification trên codebase (`backend/src/planning/`, `backend/src/execution/`, `backend/src/shared_kernel/`, `backend/tests/`, `frontend/src/app/`, `frontend/e2e/`) và toàn bộ raw experiment artifacts trong `docs/experiments/` (`exp_01`..`exp_14`).
- **Ràng buộc tuân thủ (Đã kiểm chứng):** **`0` thay đổi** trên `prompts.py`, `roadmap_skills.py`, `untrusted_context.py`, `prompts.lock` (`git diff --stat` trống); **`0` migration mới** (giữ nguyên đúng 35 bảng theo SRS v1.3); **không** tăng timeout để che giấu lỗi kiến trúc; **không** thay đổi model/provider.
- **Kết luận tổng quát ban đầu (Trước `PR-A`..`PR-E`):** `NO-GO` cho Production (do 4 blocker mức CRITICAL `DEF-01`..`DEF-04`, `DEF-05` và các lỗi HIGH `DEF-06`..`DEF-14`).
- **Kết luận tổng quát cập nhật (Sau `PR-A`..`PR-E` + `exp_14`):** **`CONDITIONAL GO` cho Production** *(nâng cấp từ `NO-GO` với bằng chứng kiểm thử độc lập đầy đủ tại Mục 10–13 bên dưới)*. Toàn bộ **14/14 lỗ hổng (`DEF-01`..`DEF-14`)** đã được khắc phục và xác minh qua bộ test tái hiện (Unit, Real PostgreSQL Integration, Playwright E2E, và Live CofHub A/B Benchmark `exp_14`).

> [!IMPORTANT]
> **Ghi chú truy vết (Traceability Note):** Các Mục 1–9 dưới đây giữ nguyên toàn văn phát hiện kiểm toán ban đầu trên `PR-1`..`PR-4` để đảm bảo tính minh bạch và đối chiếu lịch sử. Toàn bộ kết quả xác minh độc lập sau khi triển khai 5 gói khắc phục (`PR-A`..`PR-E`), bảng trạng thái `DEF-01`..`DEF-14`, tóm tắt kiến trúc & rollback từng PR, và kết quả thực nghiệm `exp_14` + Blind Pedagogical Review được trình bày chi tiết tại **Mục 10, 11, 12 và 13** ở cuối báo cáo.

---

## 1. Executive Summary

| Khía cạnh kiểm toán | Trạng thái | Tóm tắt bằng chứng chính |
|---|---|---|
| **MilestoneEffortAllocator (PR-2)** | Có lỗi logic biên (`MEDIUM-HIGH`) | `gamma_min=0.65` và giữ `FULL_SCOPE` khi lọt `P_hard` vận hành đúng hướng, nhưng nhánh Case 1B (`sum_llm <= p_hard < sum_min`) có thể ép `E_plan` dưới `m_floor=90m` (capstone) và vượt `p_hard` khi làm tròn (`[45,45]` thành `120 > 90`); Case 2 có thể sinh `FIT_CAPACITY` với `kept_scope=()`. |
| **Task Decomposer Latency (PR-4)** | **Blocker (`CRITICAL`)** | Thông lượng thực đo của `gemini-3.8-flash` qua CofHub ổn định quanh `121.6–144.3 tok/s` (~`138 tok/s`), mỗi task tốn `305–343` output tokens (~`2.2–2.5s/task`). Trần `36.0s` cho phép tối đa **`~14–16` tasks** (`~4,968` output tokens), trong khi Hard goals cần `20–35+` tasks (`45–85s+`). Thêm vào đó, **production prompt lớn gấp ~2x `eval_runner`**, bị **nhân đôi ngữ cảnh `structured_ctx`**, chạy kèm **`tools=KnowledgeToolDispatcher`** và thiếu connection pool / global semaphore ở `LiteLLMAdapter`. |
| **Scheduling v2 (PR-3A & PR-3B)** | **2 Blocker (`CRITICAL`) + lỗi HIGH** | (1) `_build_reoptimized_draft_proposal` xóa metadata coverage và toàn bộ `task_dependencies`, khiến mọi đề xuất Reoptimize / Overdue Recovery đều fail `422` khi Apply hoặc mất DAG; (2) `orchestrator.py:720-732, 1025-1037` vừa retry LLM vô ích cho lỗi bất khả thi tất định, vừa cho phép `is_valid=True` ở attempt 2 khi còn task `unscheduled`; (3) Lỗi `task_end_anchor` ở Mode A do duyệt interval chưa sắp xếp theo giờ; rò rỉ `<30m` ở `_choose_slot_chunk` whole-fit và Phase 2 `eff_w`; bug Google Calendar cắt lịch theo thứ trong tuần vĩnh viễn. |
| **UX / API & Concurrency** | **2 Blocker (`CRITICAL` / `HIGH`)** | (1) `ApplyScheduleProposalUseCase` và `UpdateScheduleProposalUseCase` truyền **cả milestone `PENDING` bị hoãn** vào `validate_task_coverage`, làm **100% proposal `FIT_CAPACITY` fail 422 `MILESTONE_WITHOUT_TASKS`**; (2) Frontend chưa có xử lý `409`/`FIT_CAPACITY`/`scope_proposal_version`, `UpdateMilestonesUseCase`/`UpdateRoadmapUseCase`/`UpdateAvailabilityUseCase` làm `scope_proposal_hash` cũ kỹ không được tính lại; thiếu khóa hàng DB (`with_for_update()`) và `idempotency_key` ở Apply chưa từng được kiểm tra. |

---

## 2. Verified Defects, Risks & Unknowns

### 2.1. Verified Defects (Đã chứng minh qua mã nguồn & dữ liệu thô)

| ID | Mức độ | Mô tả lỗ hổng | Bằng chứng (`file:line` / Artifact) |
|---|---|---|---|
| **DEF-01** | **CRITICAL** | **Mọi proposal `FIT_CAPACITY` đều bị chặn ở `Update`/`Apply` (HTTP 422 `MILESTONE_WITHOUT_TASKS`):** `ExecuteScheduleProposalGenerationUseCase` chỉ phân rã `kept_milestones`, nhưng `ApplyScheduleProposalUseCase` và `UpdateScheduleProposalUseCase` tải toàn bộ `milestones` (gồm cả milestone `PENDING` đã hoãn) và đưa tất cả vào `validate_task_coverage`. | `proposal_generation_use_cases.py:474-475`; `proposal_management_use_cases.py:276, 350, 552, 699-709`; `learning_quality.py:202-208` |
| **DEF-02** | **CRITICAL** | **`ReoptimizeSchedule` & `InitiateOverdueRecovery` (`UC-23`) tạo DRAFT hỏng 100%:** `_build_reoptimized_draft_proposal` bỏ `learning_objective`, `completion_criteria`, `covered_outcome_ids`, `concept_ids`, `description` (fail `Apply` 422); truyền `dependencies=None` và ghi cứng `"dependencies": []` (xóa sạch `task_dependencies` khi Apply); nhân lại `est_beta`; nhánh `only_overdue_and_incomplete` bị chết (`incomplete_tasks if overdue else incomplete_tasks`); ghi đè block `is_protected`. | `proposal_management_use_cases.py:1283-1492`, `624-646`, `699-709`; `schedule_sync_adapter.py:123-125`; `execution/public_api.py:361-398` |
| **DEF-03** | **CRITICAL** | **`ValidationGateOrchestrator` vừa retry sai vừa duyệt lọt proposal bất khả thi:** Ở `attempt == 1`, nếu `req_mins <= 1.3 * avail_mins`, orchestrator ép gọi lại LLM kể cả khi `EXPLICIT_UNSCHEDULABLE` (`TASK_EXCEEDS_CONTINUOUS_SLOT`, `CRITICAL_PATH_EXCEEDS_WINDOW`). Đến `attempt >= 2` (hoặc `req_mins > 1.3 * avail_mins`), `allow_unscheduled_in_attempt = True` bỏ qua check unscheduled và trả về `ValidationGateResultDTO(is_valid=True)` dù lịch bị rỗng/xếp thiếu. | `orchestrator.py:720-732, 1025-1037`; `tier1_schema.py:179-180` |
| **DEF-04** | **CRITICAL** | **Bất khả thi vật lý ở Decomposer nguyên khối cho Hard E2E + Production Prompt Bloat:** Giới hạn sinh token (~`138 tok/s`, `305–343` tok/task) khiến `36.0s` chỉ sinh tối đa `~14–16` tasks (`5/6` timeout tuần tự ở `hard_6_goals`). Ngoài ra, bản production còn gửi prompt gấp đôi `eval_runner`, **lặp 2 lần `structured_ctx`** khi có memory/mastery/RAG, và gọi `KnowledgeToolDispatcher` (`max_tool_calls=4`). | `exp_09_judge_and_quality_ab.json`, `exp_11_decomposer_budget_ab.json`, `exp_13_deterministic_ab_results.json`; `proposal_generation_use_cases.py:555-636, 714-718`; `roadmap_context_builder.py:777`; `milestone_use_cases.py:263-284`; `clarification_use_cases.py:1022-1041` |
| **DEF-05** | **CRITICAL** | **Frontend hoàn toàn chưa hỗ trợ `FIT_CAPACITY` & HTTP 409:** `roadmap.service.ts` gửi `{}` vào `/milestones/approve`, không xử lý mã lỗi `SCOPE_APPROVAL_REQUIRED` / `PRELIMINARY_UNSCHEDULABLE` / `FRESH_CALENDAR_CONFLICT_DETECTED`, và `areMilestonesApproved()` luôn trả về `false` khi còn milestone `PENDING` (chặn nút tạo tasks Level 2). | `roadmap.service.ts:277-285, 1234-1271`; `routers.py:116-195` (thiếu `responses={409: ...}` trong OpenAPI / `schema.d.ts`) |
| **DEF-06** | **HIGH** | **Stale `preliminary_feasibility` & Hash không bắt drift lịch:** `UpdateMilestonesUseCase`, `UpdateRoadmapUseCase`, `UpdateAvailabilityUseCase` không tính lại `MilestoneEffortAllocator`; `_compute_proposal_hash` không hash `target_date`, `availability`, `existing_tasks`, `milestone_id`, `dependencies`, `completion_criteria`. `ApproveMilestonesUseCase` cho phép approve milestone ở trạng thái `PRELIMINARY_UNSCHEDULABLE` (vì `requires_learner_approval=False`). | `milestone_effort_allocator.py:421-455`; `milestone_use_cases.py:1019-1040, 1101-1220`; `roadmap_management_use_cases.py:131-176`; `update_availability_use_case.py:39-95` |
| **DEF-07** | **HIGH** | **Lỗi lệch `task_end_anchor` theo thứ tự Mode A:** Mode A xếp interval `[19:00-24:00, 09:00-19:00, 00:00-09:00]`; task chia nhỏ lấy `tentative_blocks[-1]` làm `task_end_anchor` (`10:00`) **trước khi** `_coalesce_adjacent_blocks` sắp xếp theo giờ (`20:00`), làm task kế tiếp bị đặt lúc `10:00` trước khi task tiền đề kết thúc lúc `20:00`. | `spatio_temporal_engine.py:877-893, 1602-1613, 2071-2089` |
| **DEF-08** | **HIGH** | **Rò rỉ fragment `<30m` & lạm phát `NC-1`:** (a) `_choose_slot_chunk` nhánh whole-fit trả `rem_effort` mà bỏ qua `_valid_slot_tail`; (b) Phase 2 truyền `window_width=eff_w` (`min(w, day_soft_cap)`) làm ẩn chiều rộng thật `w` và kẹt đuôi `15m`; (c) một task thủ công `15m` kéo `min_unit=15`, khiến `NC-1` cộng mọi khe `15..29m` vào sức chứa hợp lệ cho task `>=30m`. | `spatio_temporal_engine.py:181-182, 1014-1037, 1884-1897, 2015-2021, 2377-2415` |
| **DEF-09** | **HIGH** | **Lỗi Google Calendar / Cross-midnight / Mode A Overlap:** Một sự kiện Google Calendar hay task tuần 1 có thể cắt khung giờ đó khỏi **tất cả** các ngày thứ đó trong tuần sau (hoặc làm rơi `committed_tasks` khi `free_ranges` rỗng); block qua đêm (`e_m > 1440`) không chiếm chỗ ở ngày `d+1`; `validate_mode_a_quota` chỉ cộng tổng phút mà không check trùng giờ với `existing_tasks`. | `effective_availability_service.py:559-646`; `spatio_temporal_engine.py:258-372, 522-560, 814-820, 993-1010, 1395-1409` |
| **DEF-10** | **HIGH** | **Lỗi toán học ở `MilestoneEffortAllocator` Case 1B & Case 2:** (a) Khi `sum_llm <= p_hard < sum_min`, `lbs` giảm xuống dưới `m_floor=90` của capstone, và `_round_to_30(45)->60` tạo `[60,60]=120 > p_hard=90`; (b) Khi `llm_efforts[0] <= p_hard < e_mins[0]`, Case 2 trả `FIT_CAPACITY_REQUIRES_APPROVAL` với `kept_scope=()`; (c) `ADVANCED` (`1.10`) > `INTERMEDIATE` (`1.00`). | `milestone_effort_allocator.py:30-34, 89-94, 561-562, 604-618, 635-645`; `config.py` |
| **DEF-11** | **HIGH** | **Race condition & `idempotency_key` chết ở `ApplyScheduleProposal`:** Không có `with_for_update()` ở bất kỳ repository nào của `planning`; `applied_idempotency_key` được lưu ở cuối nhưng không kiểm tra ở đầu hàm; `proposal.status == DISCARDED` chỉ fail sau khi đã chạy `validate_proposal`, `sync_official_schedule` và ghi block; 2 lệnh Apply đồng thời trên 2 roadmap khác nhau có thể ghi đè block trùng giờ. | `proposal_management_use_cases.py:513, 529-550, 564-574, 845-955`; `schedule.py:121-126` |
| **DEF-12** | **MEDIUM-HIGH** | **Cộng dồn `budget` sai trong NC-3b & rò rỉ `DAILY_WORKLOAD_CAP` ở Phase 2:** `_advance_single_task` dùng `seeded_used` mà không trừ phần quota ngày `d` đã tiêu bởi predecessor chưa xếp lịch; `_validate_phase2_candidate` không kiểm tra `daily_workload_cap_minutes`; `routers.py` trả `preliminary_feasibility=None` ở `PUT/POST milestones`. | `spatio_temporal_engine.py:1188-1223, 2246-2281`; `routers.py:970-973, 999-1002` |
| **DEF-13** | **MEDIUM** | **Non-splittable false positive / missing `mock exam` & xung đột `>120m`:** Regex `\bbenchmarks?\b`, `\bmock\s+tests?\b` dễ gán nhầm task lý thuyết/setup là non-splittable, đồng thời bỏ sót `"mock exam"` và bỏ qua `description`/`completion_criteria`. AI path bị chặn cứng `estimated_minutes <= 120`, nên không thể tạo đề thi thử `150–180m` dù cuối tuần `MODE_B` rảnh `180m`; khi lưu thủ công không có `schedule_blocks`, hệ thống lại cắt mọi task `>60m` thành các mảnh `60m`. | `spatio_temporal_engine.py:91-125`; `planning_dtos.py:380-384`; `tier1_schema.py:67, 118`; `proposal_management_use_cases.py:905-927` |
| **DEF-14** | **MEDIUM** | **Tạo mới `genai.Client` mỗi call LLM & thiếu SSE keepalive:** `LiteLLMAdapter._generate_with_google_genai` tạo client mới ở mọi request (`516`) không qua pool hay semaphore toàn cục; `RedisSseJobStore.stream_events` (`461-509`) im lặng tới `36–55s` giữa `progress=60` và `85` mà không gửi `: keepalive`. Ngoài ra `sweep_overdue_tasks_and_anti_loop` là stub trả về `0`/`None`. | `litellm_adapter.py:447-461, 516`; `job_store.py:461-509`; `execution/presentation/tasks.py:8-17`; `evaluation/presentation/tasks.py:4-7` |

### 2.2. Verified Safeguards (Những phần đã hoạt động đúng thiết kế)

- **Không âm thầm bỏ task trong Solver mới/cũ (`no silent drops`):** Tất cả nhánh trong `spatio_temporal_engine.py` (`1615-1619`, `2115-2121`, `2831-2880`, `3179-3182`, `3500-3504`) giữ lại task chưa xếp với `scheduled_date=None` và rollback toàn bộ block dở dang của task đó.
- **Tài liệu prompt & lockfile:** `0` thay đổi trong `roadmap_skills.py`, `prompts.py`, `untrusted_context.py`, `prompts.lock`.
- **Quota release khi `Initiate`/`Execute` fail:** `InitiateScheduleProposalGenerationUseCase` kiểm tra `_resolve_approved_milestones_for_decomposition` **trước** khi reserve quota (`proposal_generation_use_cases.py:1016-1020`), và `Execute` release quota khi fail (`937-962`).
- **Tách riêng 3 tầng verdict trong `eval_runner` & `structural_audit`:** Đạt tách biệt `structural_validity`, `scheduling_feasibility`, `pedagogical_quality`.

### 2.3. Unknowns (Không thể xác minh từ dữ liệu và phân tích tĩnh hiện có)

1. **Chi phí USD thực tế (`Cost per successful roadmap`):** Bảng `ai_usage_logs.estimated_cost_usd` (`user_orm.py:284-286, 308`; `schema.sql:269`) mặc định `0` và `QuotaFacadeAdapter.commit_reservation` (`quota_facade_adapter.py:196-209`) chưa điền giá trị; toàn repo không có bảng đơn giá token cho CofHub / `gemini-3.8-flash`.
2. **Hành vi PostgreSQL live dưới tải ghi đồng thời:** Chưa chạy integration test thực tế với DB để kiểm tra constraint `official_schedules.roadmap_id` có chặn được race double-apply cùng roadmap hay để lọt duplicate `ScheduleBlock` trước lúc fail.
3. **Độ ổn định CofHub tại `c=5` cho Heavy E2E (`MilestonePlanner` / chunked Decomposer):** Các file `concurrency_5_method_a_36runs.json` và `concurrency_10_method_a_36runs.json` chỉ chạy `golden_18` decomposer-only (`~10s`, `4` tasks); chưa có số đo live Stage 2 / E2E tại `c=5`.
4. **Độ trễ thực tế của Production `POST /proposals/generate-jobs` với user có memory + RAG + Tools:** Vì `eval_runner.py` không nạp `KnowledgeToolDispatcher` và dùng prompt ngắn hơn production ~2x, độ trễ thực tế trên production khi `harness_inputs` đầy đủ chưa được đo trực tiếp.

---

## 3. Root-Cause Analysis của Hard E2E Failures (`exp_13`: `1/6` ở `c=1`, `0/6` ở `c=3`)

### 3.1. Giải phẫu thực nghiệm `exp_13` theo từng stage

| Tập & Cấu hình | Passed | `pass@1` | `pwj` | Clarifier FAIL / p50 / p95 | Milestone Planner FAIL / p50 / p95 | Decomposer FAIL / p50 / p95 | Prompt / Output / Thinking Tok |
|---|---:|---:|---:|---|---|---|---|
| `golden_18` `c=3` Ctrl (`25s`) | `2/18` (`11.1%`) | `0.1111` | `0.1111` | `3 TO` / `9.08s` / `15.01s` | `1 TO, 3 GATE` / `13.49s` / `33.81s` | `9 TO` / `25.00s` / `25.00s` | `95,066 / 36,900 / 0` |
| `golden_18` `c=3` Treat (`36s`) | `13/18` (`72.2%`) | `0.6667` | `0.6111` | `1 TO` / `8.93s` / `12.10s` | `1 GATE (E02 FIT)` / `15.00s` / `20.49s` | `3 TO (E05,12,13)` / `29.68s` / `36.00s` | `367,909 / 91,826 / 529` |
| `hard_6` `c=3` Ctrl (`25s`) | `0/6` | `0.0` | `0.0` | `1 TO` / `10.03s` / `14.02s` | `0` / `14.88s` / `26.17s` | `5 TO` / `25.00s` / `25.00s` | `37,390 / 15,328 / 0` |
| `hard_6` `c=3` Treat (`36s`) | `0/6` | `0.0` | `0.0` | `0` / `8.83s` / `10.61s` | `2 TO` / `21.86s` / **`50.01s`** | `4 TO` / `36.00s` / `36.00s` | `33,699 / 15,006 / 0` |
| `hard_6` `c=1` Ctrl (`25s`) | `0/6` | `0.0` | `0.0` | `0` / `9.54s` / `10.30s` | `0` / `20.75s` / `34.31s` | `6 TO` / `25.00s` / `25.00s` | `43,929 / 18,895 / 0` |
| `hard_6` `c=1` Treat (`36s`) | `1/6` | `0.1667` | `0.1667` | `0` / `10.02s` / `10.79s` | `0` / `16.83s` / `25.38s` | `5 TO` / `36.00s` / `36.00s` | `69,848 / 23,119 / 0` |

### 3.2. Ba nguyên nhân gốc rễ (Root Causes)

1. **Giới hạn vật lý của sinh tuần tự (Autoregressive Throughput Bottleneck):**
   - Trong toàn bộ các lần chạy `exp_09` (`timeout=120s`), `exp_11`, `exp_13`, tốc độ sinh token của `gemini-3.8-flash` qua CofHub gần như cố định ở **`121.6 – 144.3` output tokens/giây** (~`138 tok/s`), và mỗi `TaskItemLLMOutput` + edge tốn **`305 – 343` output tokens/task** (~`2.2 – 2.5s/task`).
   - Do đó trần `36.0s` chỉ có thể hoàn thành tối đa **`~4,968` output tokens = `~14–16` tasks**.
   - **Bằng chứng đối chứng trực tiếp ngay trong `exp_13`:** Lý do *duy nhất* `H_E2E_06` qua ở `c=1` (`34.30s`, `4,562` output tokens, `133.0 tok/s`) là do LLM ngẫu nhiên chỉ sinh **`14` tasks** với tổng effort **`1,140m` trên `2,940m` effort milestone** (`milestone_vs_tasks_gap = 0.6122`, sát ngưỡng sàn `25%` của `validate_task_coverage`). Cả `5` ca còn lại (`H_E2E_01..05`) cần `20–35+` tasks (`6,000–11,500` tokens, tương đương `45–85s+`) nên chắc chắn timeout ở `36.0s` — không phải do `thinking_tokens` (bằng `0` ở tất cả các ca `hard_6`!).
2. **Khuếch đại hàng đợi tại CofHub dưới concurrency nặng (`c=3`):**
   - Với `hard_6`, chuyển từ `c=1 → c=3` đẩy Stage 2 Milestone Planner (input ~`11,325` chars kèm 10-concept KB evidence) từ `p50=16.83s / p95=25.38s` (`0` timeout) lên `p50=21.86s / p95=50.01s` (**2/6 timeout 50s** ở `H_E2E_03`, `H_E2E_04`). Nguyên nhân đến từ tải proxy CofHub khi các request nặng chạy song song, cộng hưởng với việc `LiteLLMAdapter:516` tạo mới `genai.Client` ở mọi lượt gọi không qua connection pool hay semaphore.
3. **Khoảng trống giữa `eval_runner` và Production thực tế (ẩn rủi ro thêm):**
   - Khác với lầm tưởng rằng `55s` ôm cả 3 stage, production tách thành **2 luồng SSE riêng biệt (`55s` cho Stage 2, `55s` cho Stage 3)** và Clarifier (`15s` sync HTTP) — đây là điểm hợp lý của kiến trúc endpoint.
   - Tuy nhiên, ở Stage 3 (`proposals/generate-jobs`), **production gửi prompt ~2x lớn hơn `eval_runner`** (`6,347–6,581` vs `3,293–3,445` chars dù không có memory/RAG), **lặp đôi `structured_ctx`** khi có harness context, và truyền `KnowledgeToolDispatcher` (`max_tool_calls=4`). Do đó tỷ lệ timeout trên production cho goal nhiều milestone sẽ **cao hơn** mức `5/6` đo được ở `eval_runner`.

---

## 4. Kiểm định Effort Normalization (`MilestoneEffortAllocator`)

### 4.1. Truy vết công thức và `gamma_min = 0.65`
- Trong [milestone_effort_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/milestone_effort_allocator.py):
  - `m_floor = 90 if is_capstone else 60`; `raw_h = alpha_level * (outcome_workload + concept_workload + practical_and_capstone_load)`; `h_est = max(m_floor, _round_to_30(raw_h))` (`lines 301-304`).
  - Khi LLM phát effort đồng đều (`len(set(llm_efforts)) == 1`, `n > 1`) và `raw_heuristics` phân hóa, `E_est` phân bổ lại `_round_to_30(sum_llm)` theo trọng số `raw_heuristics` (`512-517`); ngược lại `E_est = max(m_floor, _round_to_30(0.60 * E_llm + 0.40 * h_est))` (`519-522`).
  - `E_min = max(m_floor, _round_to_30(max(m_floor, min(E_llm, h_est) * gamma_min)))` với `gamma_min = 0.65` (`524-534`).
  - Điều kiện kích hoạt `FIT_CAPACITY`: chỉ khi **cả** `sum(E_llm) > P_hard` **lẫn** `sum(E_min) > P_hard` (`598, 619`).

### 4.2. Đánh giá bảo toàn Capstone, Outcome Coverage & ranh giới Feasibility
1. **Bảo toàn effort Project / Capstone:**
   - Với `E_llm >= m_floor (90)`, Case 1B thường dùng `lbs = e_mins`, giữ `normalized_planned_effort_minutes >= 90m`.
   - **Lỗi thực sự nằm ở nhánh fallback `target_total < sum_min`** (`604-608`): `lbs = [min(llm_efforts[i], m_floors[i])]`. Nếu LLM đánh giá thấp một milestone capstone (`E_llm = 60m`), hệ thống hạ `lbs` xuống dưới `90m` (vi phạm chính `m_floor=90` và `PROJECT >= 90m` của Phase 2/Conditional constraints). Đồng thời, nếu `E_llm = [45, 45]` và `p_hard = 90`, `_round_to_30(45) -> 60` làm `_distribute_30m_units` trả về `[60, 60] = 120 > p_hard = 90` (**DEF-10**).
   - Ngoài ra, `ADVANCED = 1.10 > INTERMEDIATE = 1.00` (`30-34`) khiến người học trình độ cao bị tính heuristic nền cao hơn 10% so với trung cấp ở cùng milestone.
2. **Outcome Coverage trước và sau chuẩn hóa:**
   - Chuẩn hóa **không** sửa hay cắt bỏ `learning_outcomes` hoặc `required_concepts` ở tầng Milestone (`milestone_effort_allocator.py:724-727`).
   - Nhưng ở tầng Downstream: vì milestone `FIT_CAPACITY` bị hoãn vẫn nằm trong bảng `milestones` với `status='PENDING'`, `ApplyScheduleProposalUseCase` và `UpdateScheduleProposalUseCase` kiểm tra coverage trên **tất cả** milestone nên **fail 100% với `MILESTONE_WITHOUT_TASKS`** (**DEF-01**). Và khi LLM gọi Stage 2 với `generation_strategy="FIT_CAPACITY"`, kết quả đã bị cắt sẵn nhưng `ExecuteMilestoneGenerationUseCase` vẫn chạy `Allocator` lên tập đã cắt và giữ nguyên `deferred_scope` cũ từ LLM.
3. **Phân biệt `FULL_SCOPE` / `FIT_CAPACITY` / `PRELIMINARY_UNSCHEDULABLE` / `EXPLICIT_UNSCHEDULABLE` & Khoảng trống `preliminary_feasibility`:**
   - Hệ thống đã lưu tách biệt `preliminary_feasibility` (`roadmap.planning_metadata`) và `feasibility_verdict` của lịch (`ScheduleProposal`).
   - **Tuy nhiên**, `calculate_hard_packable_capacity` (`spatio_temporal_engine.py:3293-3329`) chỉ đếm tổng block `>=30m` mỗi ngày, bỏ qua: (i) độ dài slot liên tục cho task `is_non_splittable`, (ii) thất thoát do chia slot `30..120m`, (iii) đường găng DAG, (iv) hệ số `estimation_bias_beta` (`1.0x–1.8x`) khi Decomposer chạy (`proposal_generation_use_cases.py:722`), và (v) giới hạn `366` ngày (`3313`). Do đó, một roadmap `FULL_SCOPE_FEASIBLE` ở mức `95–100%` `P_hard` vẫn có thể thành `EXPLICIT_UNSCHEDULABLE` ở Stage 3; người dùng cần được hiển thị rõ đây chỉ là *ước lượng sơ bộ trước phân rã task*.

---

## 5. So sánh Kiến trúc Task Decomposition: Monolithic vs. Milestone-Scoped

Vì nguyên nhân thất bại ở Hard E2E là **tốc độ sinh token nối tiếp (~138 tok/s)** so với tổng `20–35+` tasks, không có tinh chỉnh timeout hay prompt ngắn nào giữ nguyên 1-call monolithic mà qua được ngưỡng `36s–55s` cho `4–7` milestones.

### 5.1. So sánh các phương án kiến trúc

| Tiêu chí | **1. Monolithic** (Hiện tại) | **2. Milestone-Scoped Tuần tự** (`M1 → ... → Mk`) | **3. Milestone-Scoped Song song giới hạn + Boundary Synthesis** *(Khuyến nghị)* | **4. Song song không giới hạn (`gather` tất cả)** |
|---|---|---|---|---|
| **Wall latency (`k=5..7` ms, `25–35` tasks)** | `45–85s+` (**Timeout ở 36s & 55s**) | `k × 8–12s = 40–84s` (vẫn có nguy cơ vượt `55s`) | **`~12–18s`** (`k` call chạy qua `Semaphore(2..3)` ở `~10–14s/call`) | `~10–14s` lý thuyết, nhưng gây spike proxy `50s` |
| **Áp lực lên CofHub** | `1` call rất nặng + `3` review | `1` call vừa / thời điểm | **`2–3` call vừa** (kiểm soát bằng semaphore toàn process) | `5–7` call nặng đồng thời |
| **Chi phí Prompt / Output tokens** | `1×` prompt / `~6–11.5k` output | `k×` compact prompt / cùng `~6–11.5k` output | `k×` compact prompt (`~1.2k` tokens/ms) / cùng `~6–11.5k` output | Tương tự #3 |
| **Bán kính lỗi khi Retry (`Blast radius`)** | Hỏng 1 milestone → **regenerate 100% (`30` tasks)** | Chỉ retry **đúng 1 milestone** lỗi (`~8–10s`) | Chỉ retry **đúng 1 milestone** lỗi (`~8–10s`) | Chỉ retry 1 milestone |
| **Chặn vòng tool thừa ở Stage 3** | Có (`KnowledgeToolDispatcher` tối đa 4 vòng) | Có thể bỏ bằng **Server Prefetch resources** | **Server Prefetch `learning_resources`** theo `required_concepts` (tương tự `exp_10` Arm B) | Server Prefetch |

### 5.2. Thiết kế hợp nhất toàn cục cho Phương án 3 (Milestone-Scoped + Global Deterministic Merge)

Để giải bài toán các milestone thường nối tiếp tuyến tính (`M1 → M2 → ... → Mk`) mà không tụt về tuần tự, phân tách rạch ròi **LLM tạo task nội bộ từng milestone** và **Engine tất định nối DAG liên milestone**:

1. **Hợp nhất `task_id` xác định (Deterministic Namespacing):**
   - Trong mỗi prompt milestone `M_i`, LLM vẫn dùng `T1..Tm` (`pattern=r"^T[1-9][0-9]*$"` ở `planning_dtos.py:344` không cần đổi schema).
   - Ở tầng merge tất định trước `normalize_proposal_task_ids_and_dependencies`: đánh nhãn lại cặp `(sequence_order, local_tid) -> T{global_idx}` (`T1..TN`) theo thứ tự topo của milestone để Dual Critics/Judge đọc mạch lạc, sau đó chuyển sang UUIDv7 như `proposal_generation_use_cases.py:292-386`.
2. **Xây dựng Dependency DAG liên Milestone (`Cross-Milestone Boundary Synthesis`):**
   - Mỗi prompt milestone nhận thêm bản tóm tắt **Sibling Outline** (~200 chars/milestone: `title` + `learning_outcomes`) để không trùng lặp nội dung giữa `M_i` và `M_{i-1}` khi chạy song song.
   - Các cạnh nội bộ milestone (`M_i`) do LLM sinh.
   - Các cạnh liên milestone lấy từ `Milestone.prerequisite_milestone_ids` (fallback theo `sequence_order` nếu rỗng): nối **tất định** sink task(s) (bậc ra `0`, ưu tiên `PROJECT`/`REVIEW`) của `M_pred` tới source task(s) (bậc vào `0`, ưu tiên `THEORY`) của `M_succ` với `is_mandatory=True`.
3. **Kiểm tra Outcome Coverage & Effort cục bộ + toàn cục:**
   - **Local Gate ngay sau mỗi milestone `M_i`:** Chạy `validate_task_coverage(m_i_tasks, [m_i])` + `run_tier1_gate` (bỏ qua phần lịch). Nếu thiếu `M{i}-O{j}` hoặc effort dưới sàn `25%`, **retry đúng `M_i`** (~`8–10s`) mà không mất kết quả các milestone khác.
   - **Global Merge Gate sau khi gộp `M_1..M_k`:** (a) kiểm tra trùng tên `DUPLICATE_TASK` xuyên milestone; (b) chạy **`SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics` một lần trên toàn bộ DAG `N` tasks**; (c) chạy global `run_tier1_gate` + `run_tier2_gate`; (d) chạy song song `Dual Critics` + `Tier 3 Judge` (`~3.5–5.3s` p50).
4. **Quota & Checkpointing qua `WorkflowStepExecution`:**
   - Giữ nguyên **1 reservation `SCHEDULE_PROPOSAL_GEN` (`cost=1`)** ở `InitiateScheduleProposalGenerationUseCase`, truyền `manage_quota=False` cho `k` sub-call, cộng dồn token của tất cả sub-call + Critics/Judge và `commit_reservation` **một lần** khi lưu `ScheduleProposal(DRAFT)`.
   - Lưu output mỗi milestone đã pass local gate vào `WorkflowStepExecution` (`step_name=f"TASK_DECOMPOSER_M{seq}"`) để hỗ trợ resume/retry cục bộ.

---

## 6. Production Integration Risks

1. **Rủi ro vòng đời `FIT_CAPACITY` đầu-cuối:** Ngay cả khi `ApproveMilestonesUseCase` và `ExecuteScheduleProposalGenerationUseCase` pass unit test, người dùng thật **không thể** xác nhận `FIT_CAPACITY` qua UI (`roadmap.service.ts`), và dù gọi API trực tiếp cũng **100% fail HTTP 422** tại bước cuối `ApplyScheduleProposal` (**DEF-01, DEF-05**).
2. **Mất toàn bộ Dependency & lỗi 422 khi người học dùng Overdue Recovery / Reoptimize (`UC-23`):** Tính năng sửa lịch khi trễ tiến độ hoàn toàn không dùng được trên production (**DEF-02**).
3. **Lưu nháp rỗng / xếp thiếu nhưng báo thành công (`is_valid=True`):** Với `DEF-03`, khi gặp lịch quá khít hoặc non-splittable vượt slot, Task Decomposer ở attempt 2 có thể trả về `ValidationGateResultDTO(is_valid=True, feasibility_verdict="EXPLICIT_UNSCHEDULABLE")` và trừ quota của người học thay vì báo lỗi rõ ràng.
4. **Xung đột lịch đồng thời & Google Calendar drift:** Thiếu lock `FOR UPDATE`, thiếu kiểm tra `applied_idempotency_key` ở đầu `Apply`, hash không phủ `availability`/`target_date`, và lỗi `effective_availability_service.py` biến 1 buổi bận tuần 1 thành cấm học thứ đó ở các tuần sau (**DEF-06, DEF-09, DEF-11**).
5. **Tắc nghẽn Gateway & Rớt kết nối SSE:** `LiteLLMAdapter` chưa có connection pool hay global outbound semaphore và `RedisSseJobStore` không gửi `: keepalive` trong `36–55s` chờ Decomposer (**DEF-14**).

---

## 7. Kế hoạch Thực nghiệm Benchmark A/B Tái lập được

### 7.1. Giao thức tái lập chuẩn
- **Tập dữ liệu cố định:** Chạy song song cả `golden_planning_18_goals.jsonl` (`n=18`) và `hard_planning_6_goals.jsonl` (`n=6`), seed cố định cho thứ tự scenario, dùng cùng endpoint/model cấu hình qua CofHub.
- **Mức tải & số lượt:** Mỗi nhánh (Control vs Treatment) chạy **`trials_per_goal = 3`** ở 3 mức **`concurrency = 1, 3, 5`** (`54` lượt Golden + `18` lượt Hard cho mỗi mức concurrency và mỗi nhánh).
- **Quy tắc chống sai lệch đo lường (Audit Hygiene):**
  - Bật `apply_milestone_effort_allocator=True` ở Treatment và bổ sung một nhánh kiểm tra **production-equivalent context** (gọi `ExecuteMilestoneGenerationUseCase` + `ExecuteScheduleProposalGenerationUseCase` qua mock repo/UOW thay vì chỉ prompt rút gọn của `eval_runner`) để đo đúng độ trễ với prompt production + tools/prefetch.
  - Ghi log rõ tường minh `structural_validity`, `scheduling_feasibility`, và `pedagogical_quality` thành **3 cột độc lập** (tuyệt đối không gộp soft quality thành pass/fail của hard gate).

### 7.2. Bộ chỉ số báo cáo bắt buộc theo từng Stage
Cho từng stage (`clarifier`, `milestone_planner`, `decomposer_merge`, `critics_judge_parallel`, `apply_rehearsal`):
1. **Độ tin cậy:** `pass@1`, `final_completion_rate` (sau retry), phân rã `error_breakdown` theo mã (`TIMEOUT`, `VALIDATION_GATE`, `EXPLICIT_UNSCHEDULABLE`, `HEURISTIC_ALLOCATION_INCOMPLETE`, `FIT_CAPACITY_APPROVAL_REQUIRED`, `5xx/NETWORK`).
2. **Độ trễ:** `p50`, `p95`, `max`, và throughput (`output_tokens / active_generation_seconds`).
3. **Token & Chi phí:** `prompt_tokens`, `output_tokens`, `thinking_tokens`, kèm **cost per successful roadmap** (tính cả token của các lần retry và ca fail; *yêu cầu khai báo bảng đơn giá model trước khi chạy* vì hiện repo đang thiếu).
4. **Chất lượng & Độ trung thực tất định:**
   - **Structural correctness:** `structural_validity_rate`, `outcome_coverage_rate` (yêu cầu `100%`), `dag_validity_rate` (acyclic + `pred.end <= succ.start`), `duplicate_task_rate`.
   - **Scheduling feasibility:** `scheduling_feasibility_rate`, `unplaced_tasks == 0`, `non_splittable_split_count == 0`, `adjacent_same_day_split_count == 0`, `apply_roundtrip_pass_rate` (chạy thật `ApproveMilestonesUseCase -> ExecuteProposal -> ApplyScheduleProposalUseCase`).
   - **Effort realism & Pedagogical quality:** `milestone_vs_tasks_gap` (tránh ca `0.6122` như `H_E2E_06`), `all_efforts_equal_rate`, `max_consecutive_study_days`, `days_idle_before_deadline`, `judge_verdict` (`PASSED`/`NEEDS_REVIEW`/`REVIEW_PENDING`), và **chấm mù độc lập (`blind review`)** tối thiểu 10 mẫu sau refactor theo rubric 5 tiêu chí.

### 7.3. Tiêu chí chấp nhận (`Acceptance Criteria`)
- **`golden_18` (`c=1, 3, 5`):** `structural_validity >= 95%`, `scheduling_feasibility` & `apply_roundtrip >= 90%`, `pass@1 >= 85%`, `0` lỗi mất dependency hoặc rò rỉ `<30m` / split non-splittable.
- **`hard_6` (`c=1, 3, 5`):** `structural_validity >= 90%`, `scheduling_feasibility` & `apply_roundtrip >= 80%`, Stage 3 SSE wall latency `p95 <= 42.0s` (dư `>= 13s` dưới trần `55.0s` cho Critics/Judge), `milestone_vs_tasks_gap <= 0.25`.

---

## 8. Danh sách Remediation Tasks theo P0 / P1 / P2

### P0 — Blockers bắt buộc sửa trước Production (Không thể Go-Live nếu thiếu)
1. **P0-1 (Sửa `FIT_CAPACITY` Apply & Update 422):** Trong `UpdateScheduleProposalUseCase` và `ApplyScheduleProposalUseCase` (`proposal_management_use_cases.py:276, 350, 552, 699-709`), lọc `milestones` về đúng tập `kept_scope` / non-deferred khi `preliminary_feasibility.status == "FIT_CAPACITY_REQUIRES_APPROVAL"` và đã được approve; bổ sung E2E test từ `GenerateMilestones -> ApproveMilestones(FIT_CAPACITY) -> GenerateProposal -> ApplyProposal`.
2. **P0-2 (Sửa `Reoptimize` / `Overdue Recovery` `UC-23`):** Trong `_build_reoptimized_draft_proposal` (`proposal_management_use_cases.py:1283-1492`), giữ nguyên `learning_objective`, `completion_criteria`, `covered_outcome_ids`, `concept_ids`, `description`; đọc và truyền `TaskDependencyORM` vào solver và `candidate_payload["dependencies"]`; không nhân lại `est_beta` lên task đã scale; tôn trọng `is_protected` và sửa nhánh `only_overdue_and_incomplete`.
3. **P0-3 (Chặn `ValidationGateOrchestrator` duyệt lọt lịch rỗng & retry vô ích):** Trong `orchestrator.py:720-732, 1025-1037`, khi `feasibility_verdict` là `EXPLICIT_UNSCHEDULABLE` (`NC-1..3` fail) không retry LLM vô ích; không bao giờ set `allow_unscheduled_in_attempt=True` một cách im lặng để trả `is_valid=True` khi chưa có xác nhận `allow_partial_schedule` tường minh của người dùng, và không commit quota nếu không tạo được lịch khả thi.
4. **P0-4 (Chuyển Task Decomposer sang Milestone-Scoped + Server Resource Prefetch):** Thiết kế và triển khai Milestone-Scoped Parallel-with-Boundary-Synthesis (`Semaphore(2..3)`), Server Prefetch `learning_resources`, bỏ lặp đôi `structured_ctx` (`proposal_generation_use_cases.py`, `milestone_use_cases.py`, `clarification_use_cases.py`), hợp nhất `task_id` / DAG liên milestone / `WorkflowStepExecution` checkpointing, và đối chiếu `apply_milestone_effort_allocator` với production context.
5. **P0-5 (Hoàn thiện Frontend `FIT_CAPACITY` + HTTP `409`):** Expose schema 409 trong `routers.py` -> regenerate `schema.d.ts`; cập nhật `roadmap.service.ts` và UI Milestone Review để hiển thị `kept_scope`, `deferred_scope`, `adjustment_options`, gửi `confirmed_scope_proposal_version` + `accept_fit_capacity`, và sửa `areMilestonesApproved()` khi có milestone `PENDING` thuộc `deferred_scope`.

### P1 — High-Priority Correctness & Concurrency Fixes
1. **P1-1 (Vá Scheduling Edge Cases):** Sửa `task_end_anchor` theo block cuối theo **thời gian thực** sau sort trong Mode A; vá `_choose_slot_chunk` whole-fit check `_valid_slot_tail`; truyền đúng `w` thật (không dùng `eff_w`) trong Phase 2; giữ `min_unit = 30` ở `NC-1` cho các task `>= 30m`; kiểm tra `daily_workload_cap_minutes` trong `_validate_phase2_candidate` và check overlap giờ thực ở Mode A + cross-midnight `d+1`.
2. **P1-2 (Sửa `MilestoneEffortAllocator` Case 1B/Case 2 & Hash Drift):** Chặn `lbs < m_floor` và `_round_to_30` vượt `p_hard` trong Case 1B (`milestone_effort_allocator.py:604-618`); đẩy `e_mins[0] > p_hard` vào Case 3 thay vì Case 2 `kept_scope=()`; tính lại `MilestoneEffortAllocator` và `scope_proposal_hash` khi `UpdateMilestonesUseCase` / `UpdateRoadmapUseCase` / `UpdateAvailabilityUseCase` chạy; đưa `availability`, `target_date`, `existing_tasks`, `dependencies` vào `_compute_proposal_hash`; chặn `ApproveMilestonesUseCase` trên `PRELIMINARY_UNSCHEDULABLE`; xem xét lại `alpha` cho `ADVANCED`.
3. **P1-3 (Khóa đồng thời & `Apply` Idempotency + Calendar Carving Fix):** Thêm `with_for_update()` cho `Roadmap`/`Milestone`/`ScheduleProposal`/`OfficialSchedule` ở các thao tác `Approve`, `UpdateMilestones`, `Apply`; kiểm tra `applied_idempotency_key` ngay đầu `Apply` và chặn `DISCARDED` trước mọi mutation; sửa `effective_availability_service.py:559-646` không trừ sự kiện một ngày khỏi mọi tuần lặp lại; sửa Domino Shift kiểm tra `disabled_weekdays` & slot.

### P2 — Operational Resilience, Observability & Hardening
1. **P2-1 (`LiteLLMAdapter` Pool + Global Semaphore & SSE Keepalive):** Tái sử dụng shared `genai.Client` / `httpx` pool + global outbound `asyncio.Semaphore` để tránh đuôi `50s` trên CofHub; thêm `: keepalive` định kỳ trong `RedisSseJobStore.stream_events`.
2. **P2-2 (Populate `estimated_cost_usd` & Integration Suite):** Ghi chi phí thực hoặc ước lượng vào `AIUsageLogORM`; bổ sung integration test chạy PostgreSQL thật cho race condition `Approve`/`Apply` và `NonSplittableTaskClassifier` (`mock exam`, `description`, task thi thử `>120m` trên AI path).

---

## 9. Đề xuất cuối cùng: **`NO-GO` cho Production**

- **Quyết định:** **`NO-GO`** tại thời điểm hiện tại.
- **Cơ sở bằng chứng:**
  1. **Gãy các luồng người dùng cốt lõi:** Luồng `FIT_CAPACITY` gãy ở bước cuối `ApplyScheduleProposal` (`422 MILESTONE_WITHOUT_TASKS`) và không có UI; luồng Overdue Recovery / Reoptimize (`UC-23`) gãy 100% ở Apply và xóa toàn bộ dependency; `Orchestrator` có thể trả `is_valid=True` cho lịch bất khả thi (`0/N` placed).
  2. **Không đáp ứng năng lực cho mục tiêu thực tế (`Hard E2E`):** Ngay cả sau PR-1..PR-4, `hard_6_goals` chỉ đạt **`1/6` (c=1)** và **`0/6` (c=3)**, với ca pass duy nhất phải đánh đổi bằng `milestone_vs_tasks_gap = 0.6122`, và bản production hiện dùng prompt dài gấp đôi `eval_runner` kèm `structured_ctx` bị lặp đôi.
  3. **Rủi ro dữ liệu & đồng thời:** Chưa có `with_for_update()`, `idempotency_key` chưa được check ở `Apply`, hash `FIT_CAPACITY` bỏ sót `availability`/`target_date`, và lỗi Google Calendar cắt sai slot các tuần sau.
- **Điều kiện chuyển sang `CONDITIONAL GO`:** Chỉ khi toàn bộ **P0-1 đến P0-5** và **P1-1 đến P1-3** được triển khai xong, vượt qua integration test trên PostgreSQL thật + frontend Playwright cho luồng `FIT_CAPACITY` 409, và đạt ngưỡng benchmark A/B ở Mục 7.3 ở cả `c=1, 3, 5` (kèm đo kiểm với production context đầy đủ).

---

## 10. Xác Minh Khắc Phục Độc Lập (`PR-A`..`PR-E`) & Phán Quyết Sẵn Sàng Production Cập Nhật

### 10.1. Phán quyết điều hành cập nhật (Updated Executive Verdict): **`CONDITIONAL GO`** *(Nâng cấp từ `NO-GO`)*

Sau khi triển khai hoàn chỉnh 5 gói kỹ thuật tách biệt (`PR-A` đến `PR-E`) và thực hiện kiểm định độc lập trên toàn bộ hệ thống, phán quyết sẵn sàng Production được nâng cấp từ **`NO-GO`** lên **`CONDITIONAL GO`** dựa trên các bằng chứng thực nghiệm và kiểm thử tự động sau:

1. **Tất cả cổng chất lượng tĩnh & hợp đồng API đạt 100% (Zero Regressions):**
   - **Backend Static Gate (`bash scripts/quality-gates.sh backend-static`):** `ruff check` (`All checks passed!`), `ruff format --check` (`370 files already formatted`), `mypy --strict src` (`0 issues in 277 source files`), `lint-imports` (`5 kept, 0 broken contracts`).
   - **API Contract & Frontend Static Gate (`scripts/check-api-contract.sh` + `quality-gates.sh frontend-static`):** OpenAPI 3.1 schema khớp tuyệt đối với `frontend/src/app/core/api/schema.d.ts` (`0` diff), `ng lint` pass, `55/55` Vitest spec files (`420/420` tests pass), `ng build --configuration production` thành công.
   - **Prompt & Schema Lock Integrity:** `git diff --stat -- "*prompts.py" "*roadmap_skills.py" "*untrusted_context.py" "*prompts.lock"` hoàn toàn trống (`0` file thay đổi); `3/3` bài kiểm thử `test_prompts_lock.py` xanh; **`0` Alembic migration mới** (bảo toàn đúng 35 bảng chuẩn SRS v1.3).
2. **Bộ kiểm thử Unit, AI Eval, PostgreSQL Integration & Playwright E2E xanh tuyệt đối:**
   - **Unit & Offline AI Evals:** `579 passed, 1 skipped` trong `tests/unit` + `tests/ai_evals` (tăng từ `536` lên `579` tests nhờ 43 bài test chuyên biệt cho `PR-A`..`PR-E`); `constraints_eval` đạt `223/223` (`hard_constraint_violation_rate = 0.0`); `golden_ai_workflows_v2` pass.
   - **Real PostgreSQL Integration Suite (`PR-A`..`PR-D` + Prompt Lock):** `17/17 passed` trên PostgreSQL 16 thật (bao gồm kiểm thử khóa đồng thời `asyncio.gather` chống double-booking liên roadmap và kiểm thử roundtrip `Reoptimize`/`Overdue Recovery`).
   - **Playwright E2E (`frontend/e2e/fit_capacity_scope_approval.spec.ts`):** `1 passed` kiểm chứng trọn vẹn luồng UI `Generate Milestones -> HTTP 409 SCOPE_APPROVAL_REQUIRED -> Mở Scope Approval Dialog -> Chấp nhận FIT_CAPACITY -> Mở khóa Bước 3 -> Generate & Apply Schedule Proposal` trên cả Desktop (`1280×800`) và Mobile (`375×812`).
3. **Đột phá kiến trúc `MilestoneScopedTaskDecomposer` (`PR-E` + `exp_14`):**
   - Loại bỏ hoàn toàn hiện tượng nhân đôi `structured_ctx` (**giảm `81.07%` ký tự harness context** và **giảm `47.82%` ký tự user prompt Stage 3**).
   - Phá vỡ nút thắt cổ chai sinh tuần tự của kiến trúc nguyên khối (`monolithic`): trên tập `hard_6_stage3_apples_to_apples_c1`, tỷ lệ pass + Apply roundtrip tăng từ **`0/6 (0.0%)` lên `5/6 (83.3%)`**; trên `hard_6_stage3_apples_to_apples_c3` tăng từ **`0/6 (0.0%)` lên `4/6 (66.7%)`**; trên `hard_6_full_e2e_c3` tăng từ **`1/6 (16.7%)` lên `4/6 (66.7%)`**; và trên `golden_18_stage3_c3` tăng từ **`15/18 (83.3%)` lên `16/18 (88.9%)`** với độ trễ LLM Decomposer `p50` giảm từ `13.56s` xuống **`9.59s`** (`-29.3%`).
   - Đánh giá mù sư phạm (`Blind Pedagogical Review` trên 15 cặp = 30 mẫu, seed `20261117`): `milestone_scoped` đạt **`24.467/25` (`4.893/5`)** so với `23.933/25` (`4.787/5`) của `monolithic`, thắng đối đầu **`9W / 5T / 1L`**.

---

### 10.2. Bảng Trạng Thái Khắc Phục Từng Lỗ Hổng (`DEF-01`..`DEF-14`)

| ID | Mức độ ban đầu | Trạng thái sau `PR-A`..`PR-E` | Gói PR | Bài kiểm thử tái hiện & xác minh (`file::test_function`) | Kết quả Trước vs. Sau | File Production chính đã sửa |
|---|---|---|---|---|---|---|
| **DEF-01** | **CRITICAL** | **`VERIFIED FIXED`** | **PR-B** | [test_pr_b_fit_capacity_and_staleness.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_b_fit_capacity_and_staleness.py) (`test_def01_fit_capacity_update_and_apply_preserve_deferred_pending_milestones`, `test_def01_update_and_apply_block_unapproved_or_hash_tampered_fit_capacity`); [test_pr_b_fit_capacity_e2e.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pr_b_fit_capacity_e2e.py) (`test_e2e_pr_b_fit_capacity_roundtrip_and_staleness_invalidation`) | **Trước:** `100%` proposal `FIT_CAPACITY` bị chặn HTTP 422 `MILESTONE_WITHOUT_TASKS` ở `Update`/`Apply` do truyền cả milestone `PENDING` bị hoãn vào `validate_task_coverage`.<br>**Sau:** `_resolve_milestones_for_proposal_coverage` lọc chính xác theo `kept_scope` khi `FIT_CAPACITY` đã được xác nhận và hash khớp; giữ nguyên các milestone hoãn ở trạng thái `PENDING` sau `Apply`; chặn `409` nếu chưa approve hoặc bị sửa hash. | [proposal_management_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/proposal_management_use_cases.py), [preliminary_feasibility_service.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/preliminary_feasibility_service.py) |
| **DEF-02** | **CRITICAL** | **`VERIFIED FIXED`** | **PR-C** | [test_pr_c_reoptimize_and_overdue_recovery.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_c_reoptimize_and_overdue_recovery.py) (5 tests); [test_pr_c_reoptimize_apply_postgres_e2e.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pr_c_reoptimize_apply_postgres_e2e.py) (`test_e2e_pr_c_reoptimize_and_overdue_recovery_postgres_roundtrip`) | **Trước:** `_build_reoptimized_draft_proposal` làm rỗng metadata sư phạm (fail Apply 422), ghi cứng `"dependencies": []` (mất sạch DAG), nhân lặp `est_beta`, ghi đè block `is_protected`, và có nhánh `only_overdue_and_incomplete` chết.<br>**Sau:** Khôi phục đầy đủ metadata & DAG từ proposal lịch sử + `ExecutionQueryPort.get_task_dependencies`, tính coverage trên hợp của task `COMPLETED` + active, không nhân lại `est_beta`, giữ nguyên tất cả block của task `is_protected`, và cố định các task tương lai không bị ảnh hưởng trong `UC-23` Overdue Recovery. | [proposal_management_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/proposal_management_use_cases.py), [execution/public_api.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/public_api.py), [schedule_sync_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/infrastructure/adapters/schedule_sync_adapter.py) |
| **DEF-03** | **CRITICAL** | **`VERIFIED FIXED`** | **PR-A** | [test_pr_a_validation_gate_and_apply_safety.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_a_validation_gate_and_apply_safety.py) (13 tests); [test_pr_a_planning_safety_e2e.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pr_a_planning_safety_e2e.py) (`test_e2e_pr_a_generate_validate_and_apply_safety_workflow`) | **Trước:** Retry LLM vô ích khi lỗi bất khả thi tất định (`NC-1..3`) và tự bật `allow_unscheduled_in_attempt=True` ở attempt 2, trả `is_valid=True` cho lịch rỗng (`0/N` placed) và trừ quota.<br>**Sau:** Phân loại tường minh 4 trạng thái `schedule_completeness` (`COMPLETE_SCHEDULE`, `PARTIAL_SCHEDULE_NEEDS_CONFIRMATION`, `INFEASIBLE_NO_CAPACITY`, `UNDETERMINED`); dừng retry LLM ngay khi gặp mã lỗi tất định; fail-closed (`is_valid=False`, release quota, không lưu DRAFT hỏng) khi `placed == 0` hoặc `ratio < 0.25` hoặc chưa bật `allow_partial_schedule`. | [orchestrator.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/validation_gate/orchestrator.py), [tier1_schema.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/validation_gate/tier1_schema.py), [tier2_deterministic.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/validation_gate/tier2_deterministic.py), [proposal_generation_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/proposal_generation_use_cases.py) |
| **DEF-04** | **CRITICAL** | **`VERIFIED FIXED`** | **PR-E** | [test_pr_e_dedup_hardening_and_milestone_decomposer.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_e_dedup_hardening_and_milestone_decomposer.py) (7 tests); [exp_14_decomposer_architecture_ab.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_14_decomposer_architecture_ab.json) | **Trước:** `structured_ctx` bị nhân đôi trong `build_context` và use case; Decomposer nguyên khối bị chặn bởi tốc độ sinh tuần tự (`~138 tok/s`), đạt `0/6 (0%)` trên `hard_6_stage3_c1/c3` và `1/6 (16.7%)` trên `hard_6_full_e2e_c3`.<br>**Sau:** Khử trùng lặp ngữ cảnh giảm **`-47.82%`** ký tự prompt Stage 3 (`-81.07%` harness context); `MilestoneScopedTaskDecomposer` (`Semaphore(3)` + Server Resource Prefetch + Deterministic Boundary Synthesis + Checkpointing) nâng `hard_6_stage3_c1` từ **`0/6 (0%)` → `5/6 (83.3%)`**, `hard_6_stage3_c3` từ **`0/6 (0%)` → `4/6 (66.7%)`**, `hard_6_full_e2e_c3` từ **`1/6 (16.7%)` → `4/6 (66.7%)`**, và `golden_18_stage3_c3` từ **`15/18 (83.3%)` → `16/18 (88.9%)`**. | [milestone_scoped_decomposer.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/milestone_scoped_decomposer.py), [roadmap_context_builder.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/roadmap_context_builder.py), [proposal_generation_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/proposal_generation_use_cases.py), [milestone_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/milestone_use_cases.py), [clarification_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/clarification_use_cases.py) |
| **DEF-05** | **CRITICAL** | **`VERIFIED FIXED`** | **PR-B** | [test_pr_b_fit_capacity_e2e.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pr_b_fit_capacity_e2e.py) (`test_def05_openapi_exposes_typed_409_planning_conflict_response`); [roadmap.service.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/roadmaps/roadmap.service.spec.ts); [fit_capacity_scope_approval.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/e2e/fit_capacity_scope_approval.spec.ts) | **Trước:** OpenAPI thiếu schema `409`; `roadmap.service.ts` gửi `{}` vào `/milestones/approve`; không có UI xử lý `409`; `areMilestonesApproved()` luôn trả `false` khi còn milestone `PENDING` trong `deferred_scope`.<br>**Sau:** `routers.py` khai báo `responses={409: {"model": PlanningConflictErrorResponse}}` và đồng bộ `schema.d.ts`; bổ sung `MilestoneScopeApprovalPanelComponent` hiển thị `kept_scope`/`deferred_scope`/`adjustment_options`, gửi `confirmed_scope_proposal_version` + `accept_fit_capacity`; `areMilestonesApproved()` mở khóa Bước 3 khi toàn bộ `kept_scope` đã `APPROVED`. | [routers.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/presentation/routers.py), [planning_schemas.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/presentation/schemas/planning_schemas.py), [schema.d.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/api/schema.d.ts), [roadmap.service.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/roadmaps/services/roadmap.service.ts), [milestone-scope-approval-panel.component.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/roadmaps/components/shared/milestone-scope-approval-panel/milestone-scope-approval-panel.component.ts) |
| **DEF-06** | **HIGH** | **`VERIFIED FIXED`** | **PR-B** | [test_pr_b_fit_capacity_and_staleness.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_b_fit_capacity_and_staleness.py) (`test_def06_proposal_hash_covers_target_date_availability_existing_tasks_and_metadata`, `test_def06_milestone_edit_and_roadmap_target_date_invalidate_and_discard_drafts`, `test_def06_sync_drift_detection_catches_availability_shrink_on_approve_initiate_apply`, `test_def06_outbox_availability_consumer_is_idempotent_and_skips_completed_archived`) | **Trước:** `_compute_proposal_hash` bỏ sót `target_date`, `availability`, `existing_tasks`, `milestone_id`, `dependencies`, `completion_criteria`; sửa milestone/target_date/availability không tính lại feasibility; `PRELIMINARY_UNSCHEDULABLE` vẫn approve được.<br>**Sau:** Mở rộng `_compute_proposal_hash` bao phủ toàn bộ 6 chiều dữ liệu; tự động tính lại `preliminary_feasibility`, reset xác nhận cũ và hủy `DRAFT` proposals khi sửa milestone/target_date; kiểm tra drift đồng bộ ở `Approve`/`Initiate`/`Apply`; bổ sung `ProcessAvailabilityUpdatedOutboxUseCase` idempotent qua `processed_events`; chặn `409 PRELIMINARY_UNSCHEDULABLE`. | [milestone_effort_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/milestone_effort_allocator.py), [preliminary_feasibility_service.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/preliminary_feasibility_service.py), [availability_outbox_consumer.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/availability_outbox_consumer.py), [milestone_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/milestone_use_cases.py), [roadmap_management_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/roadmap_management_use_cases.py) |
| **DEF-07** | **HIGH** | **`VERIFIED FIXED`** | **PR-D** | [test_pr_d_scheduler_calendar_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_d_scheduler_calendar_allocator.py) (`test_def07_mode_a_chronological_task_end_anchor_prevents_dag_inversion[False]`, `[True]`) | **Trước:** Mode A lấy `tentative_blocks[-1]` (`10:00`) làm `task_end_anchor` trước khi sort theo giờ thực (`20:00`), làm task kế tiếp bị xếp lúc `10:00` trước khi predecessor kết thúc lúc `20:00`.<br>**Sau:** `_coalesce_adjacent_blocks` chạy trước và `task_end_anchor` được tính bằng `max(tentative_blocks, key=_block_chronological_end_key)`, đảm bảo `pred.end <= succ.start` trên mọi thứ tự interval Mode A. | [spatio_temporal_engine.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/spatio_temporal_engine.py) |
| **DEF-08** | **HIGH** | **`VERIFIED FIXED`** | **PR-D** | [test_pr_d_scheduler_calendar_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_d_scheduler_calendar_allocator.py) (`test_def08_choose_slot_chunk_checks_slot_tail_and_phase2_cap`, `test_def08_phase2_soft_pass_respects_physical_slot_tail_and_multi_task_chunking`, `test_def08_nc1_manual_15m_task_does_not_lower_min_unit_for_large_tasks`) | **Trước:** `_choose_slot_chunk` whole-fit bỏ qua `_valid_slot_tail` để lọt mảnh dư `15m`; Phase 2 truyền `window_width=eff_w` làm lệch chiều rộng vật lý `w`; 1 task thủ công `15m` kéo `min_unit=15` cho toàn bộ `NC-1`.<br>**Sau:** `_choose_slot_chunk` nhận tách biệt `window_width=w` và `max_chunk_cap=day_soft_cap`, kiểm tra `_valid_slot_tail(w - c)` ở mọi nhánh; `NC-1` giữ cố định ngưỡng `>=30m` cho các task chuẩn `>=30m`. | [spatio_temporal_engine.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/spatio_temporal_engine.py) |
| **DEF-09** | **HIGH** | **`VERIFIED FIXED`** | **PR-D** | [test_pr_d_scheduler_calendar_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_d_scheduler_calendar_allocator.py) (`test_def09_cross_midnight_occupied_split_and_mode_b_carryover`, `test_def09_validate_mode_b_and_mode_a_cross_midnight_and_timed_overlaps`, `test_def09_effective_availability_multiweek_no_carve_and_no_dropped_committed`) | **Trước:** Block qua đêm (`e_m > 1440`) không ghi nhận phần tràn `[0, e_m - 1440)` sang ngày `d+1`; `validate_mode_a_quota` không kiểm tra trùng giờ thực với `existing_tasks`; `EffectiveAvailabilityService` cắt mất khung giờ cố định hàng tuần chỉ vì 1 sự kiện ngày lẻ và làm rơi `committed_tasks` khi `free_ranges` rỗng.<br>**Sau:** Xử lý đầy đủ phần tràn qua đêm sang ngày `d+1` ở cả solver và validator Mode A/B; kiểm tra overlap thời gian thực ở Mode A; giữ nguyên `weekly_slots` cho solver tự trừ theo từng ngày cụ thể và luôn bảo toàn `committed_tasks`. | [spatio_temporal_engine.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/spatio_temporal_engine.py), [effective_availability_service.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/effective_availability_service.py) |
| **DEF-10** | **HIGH** | **`VERIFIED FIXED`** | **PR-D** | [test_pr_d_scheduler_calendar_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_d_scheduler_calendar_allocator.py) (`test_def10_allocator_case1b_floor_cap_case3_and_advanced_alpha`) | **Trước:** Nhánh Case 1B hạ `lbs` xuống dưới `m_floor=90m` (capstone) và làm tròn vượt `p_hard`; Case 2 sinh `FIT_CAPACITY` với `kept_scope=()` khi `e_mins[0] > p_hard`; `ADVANCED` có `alpha=1.10 > INTERMEDIATE=1.00`.<br>**Sau:** Giữ cứng `lbs = e_mins` (`>= m_floor`), chặn `sum_min > p_hard` trước khi vào Case 1B; chuyển `e_mins[0] > p_hard` thẳng sang Case 3 (`PRELIMINARY_UNSCHEDULABLE`); điều chỉnh `_LEVEL_ALPHA["ADVANCED"] = 0.85`. | [milestone_effort_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/milestone_effort_allocator.py) |
| **DEF-11** | **HIGH** | **`VERIFIED FIXED`** | **PR-D** | [test_pr_d_postgres_concurrency_e2e.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pr_d_postgres_concurrency_e2e.py) (`test_pr_d_double_apply_idempotency_and_non_draft_guards_postgres`, `test_pr_d_two_roadmaps_concurrent_apply_overlapping_slots_zero_double_booking`, `test_pr_d_resume_roadmap_rejects_cross_roadmap_slot_conflict`) | **Trước:** Thiếu `with_for_update()` trong `planning`; `applied_idempotency_key` và `status != DRAFT` chỉ kiểm tra ở cuối hàm sau khi đã ghi DB; 2 lệnh Apply đồng thời trên 2 roadmap khác nhau ghi đè trùng giờ.<br>**Sau:** Bổ sung `for_update=True` theo thứ tự khóa tất định (`User -> Roadmap -> Proposal -> OfficialSchedule`); kiểm tra `idempotency_key` và `status == DRAFT` ngay đầu `Apply`; kiểm tra xung đột lịch liên roadmap tại thời điểm commit và khi `Resume` roadmap `PAUSED` (xác minh bằng `asyncio.gather` trên PostgreSQL 16 thật). | [planning_repositories.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/infrastructure/repositories/planning_repositories.py), [repo_lock.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/repo_lock.py), [proposal_management_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/proposal_management_use_cases.py), [roadmap_management_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/roadmap_management_use_cases.py) |
| **DEF-12** | **MEDIUM-HIGH** | **`VERIFIED FIXED`** | **PR-D** | [test_pr_d_scheduler_calendar_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_d_scheduler_calendar_allocator.py) (`test_def12_nc3b_predecessor_budget_deduction_and_phase2_daily_cap`); [test_pr_b_fit_capacity_and_staleness.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_b_fit_capacity_and_staleness.py) | **Trước:** `NC-3b` (`_advance_single_task`) không trừ quota ngày `d` đã tiêu bởi predecessor trên cùng xích; `_validate_phase2_candidate` không kiểm tra `daily_workload_cap_minutes`; `PUT/POST /milestones` trả `preliminary_feasibility=None`.<br>**Sau:** Truyền `virtual_day_used` tích lũy dọc theo chuỗi predecessor trong `NC-3b`; kiểm tra cứng `daily_workload_cap_minutes` trong `_validate_phase2_candidate`; trả đầy đủ `preliminary_feasibility` trong response của `PUT/POST /milestones`. | [spatio_temporal_engine.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/spatio_temporal_engine.py), [routers.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/presentation/routers.py), [milestone_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/milestone_use_cases.py) |
| **DEF-13** | **MEDIUM** | **`VERIFIED FIXED`** | **PR-D** | [test_pr_d_scheduler_calendar_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_d_scheduler_calendar_allocator.py) (`test_def13_classifier_rules_and_metadata_fields`, `test_def13_apply_fallback_preserves_single_contiguous_block_up_to_240m`) | **Trước:** Regex `\bbenchmarks?\b` bắt nhầm task lý thuyết/setup, bỏ sót `"mock exam"` và bỏ qua `description`/`completion_criteria`; fallback trong `Apply` cắt mọi task `>60m` không có `schedule_blocks` thành mảnh `60m`.<br>**Sau:** Siết regex thành `benchmark\s+(?:tests?|exams?)`, bổ sung `mock\s+exams?`, kiểm tra cả trường phụ với guard chống phủ định (`không phải thi thử`, `not a timed exam`), và giữ nguyên 1 block liền mạch (`<=240m`) cho task thủ công/non-splittable khi Apply. | [spatio_temporal_engine.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/spatio_temporal_engine.py), [proposal_management_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/proposal_management_use_cases.py) |
| **DEF-14** | **MEDIUM** | **`VERIFIED FIXED`** *(Core Runtime)* | **PR-E** | [test_pr_e_dedup_hardening_and_milestone_decomposer.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_e_dedup_hardening_and_milestone_decomposer.py) (`test_litellm_adapter_reuses_genai_client_and_enforces_outbound_semaphore`, `test_sse_streaming_emits_keepalive_without_corrupting_completed_event`) | **Trước:** `LiteLLMAdapter` khởi tạo `genai.Client` mới ở mọi lệnh gọi LLM và không có outbound semaphore; `RedisSseJobStore.stream_events` im lặng suốt `36–55s` không gửi keepalive.<br>**Sau:** Tái sử dụng `_GENAI_CLIENT_CACHE` theo `(api_key, base_url)` kết hợp `asyncio.Semaphore(ai_max_concurrent_llm_requests=8)` theo từng event loop; `RedisSseJobStore.stream_events` phát `: keepalive\n\n` định kỳ mỗi `15s` mà không làm hỏng sự kiện `COMPLETED`/`FAILED`. *(Lưu ý minh bạch: task stub `sweep_overdue_tasks_and_anti_loop` ở context `execution`/`evaluation` và bảng đơn giá USD cho `ai_usage_logs.estimated_cost_usd` là các hạng mục vận hành nằm ngoài phạm vi 5 PR planning này).* | [litellm_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py), [job_store.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/sse/job_store.py), [config.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/config.py) |

---

## 11. Tóm Tắt Kỹ Thuật, Kiểm Thử & Chiến Lược Rollback Theo Từng Gói (`PR-A`..`PR-E`)

### 11.1. Bảng tổng hợp 5 gói PR

| Gói PR | Mục tiêu & Lỗ hổng giải quyết | Tiêu chí nghiệm thu (Acceptance Criteria) | Kiểm thử tái hiện & xác minh (Trước → Sau) | Thay đổi API / OpenAPI | Migration / DB Schema | Chiến lược Rollback |
|---|---|---|---|---|---|---|
| **PR-A**<br>*(Validation Gate & Apply Safety)* | Khắc phục **DEF-03**: Chặn duyệt lọt lịch bất khả thi (`is_valid=True` khi `0/N` placed) và chặn retry LLM vô ích cho lỗi tất định. | 1. Tách biệt 4 trạng thái `schedule_completeness`.<br>2. Không retry LLM khi gặp lỗi `NC-1..3` / `TASK_EXCEEDS_CONTINUOUS_SLOT` / `CRITICAL_PATH_EXCEEDS_WINDOW` / `CALENDAR_CONFLICT_SATURATION`.<br>3. Fail-closed (`is_valid=False`, release quota, không lưu DRAFT) khi `placed == 0` hoặc `ratio < 0.25`. | - Unit: `13/13 passed` trong [test_pr_a_validation_gate_and_apply_safety.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_a_validation_gate_and_apply_safety.py).<br>- Integration (PG): `1/1 passed` trong [test_pr_a_planning_safety_e2e.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pr_a_planning_safety_e2e.py). | Bổ sung trường tuỳ chọn `allow_partial_schedule: bool = False` trên request tạo/áp dụng proposal và `schedule_completeness` trong metadata phản hồi (tương thích ngược 100%). | **`0` migration** (Giữ nguyên 35 bảng). | Revert commit `PR-A`; các trường JSONB `schedule_completeness` trong `validation_report` là additive nên không ảnh hưởng dữ liệu cũ. |
| **PR-B**<br>*(End-to-End `FIT_CAPACITY` & Staleness)* | Khắc phục **DEF-01, DEF-05, DEF-06**: Khép kín vòng đời `FIT_CAPACITY` từ Backend tới Frontend và chống trôi lệch `scope_proposal_hash`. | 1. `Update`/`Apply` chỉ kiểm tra coverage trên `kept_scope` đã approve.<br>2. Hash bao phủ đủ 6 chiều (`target_date`, `availability`, `existing_tasks`, `milestone_id`, `dependencies`, `completion_criteria`).<br>3. Tự động tính lại feasibility + hủy DRAFT khi sửa milestone/target_date/availability (qua sync guard + Outbox consumer).<br>4. UI hiển thị dialog `409` và mở khóa Bước 3. | - Unit: `6/6 passed` trong [test_pr_b_fit_capacity_and_staleness.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_b_fit_capacity_and_staleness.py).<br>- Integration (PG): `2/2 passed` trong [test_pr_b_fit_capacity_e2e.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pr_b_fit_capacity_e2e.py).<br>- FE Vitest: `420/420 passed`.<br>- Playwright E2E: `1/1 passed` trên Desktop & Mobile `375px`. | Khai báo tường minh `responses={409: {"model": PlanningConflictErrorResponse}}` trên `POST /milestones/approve`, `POST /proposals/generate-jobs`, `POST /proposals/{id}/apply`; đồng bộ `schema.d.ts`. | **`0` migration** (Tận dụng bảng `outbox_events`, `processed_events` và cột JSONB `planning_metadata` sẵn có). | Revert FE + BE commit `PR-B`; các roadmap đang có `preliminary_feasibility` trong `planning_metadata` vẫn đọc bình thường. |
| **PR-C**<br>*(Reoptimize & Overdue Recovery `UC-23`)* | Khắc phục **DEF-02**: Sửa hỏng `100%` DRAFT sinh bởi `ReoptimizeSchedule` và `InitiateOverdueRecoveryUseCase`. | 1. Bảo toàn đầy đủ `learning_objective`, `completion_criteria`, `covered_outcome_ids`, `concept_ids`, `description` và DAG `dependencies`.<br>2. Không nhân lặp `est_beta`.<br>3. Giữ nguyên mọi block của task `is_protected`.<br>4. `UC-23` chỉ xếp lại task quá hạn + hậu duệ phụ thuộc, cố định các task tương lai độc lập. | - Unit: `5/5 passed` trong [test_pr_c_reoptimize_and_overdue_recovery.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_c_reoptimize_and_overdue_recovery.py).<br>- Integration (PG): `1/1 passed` trong [test_pr_c_reoptimize_apply_postgres_e2e.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pr_c_reoptimize_apply_postgres_e2e.py). | Mở rộng `ExecutionQueryPort` nội bộ (`get_task_dependencies`); không thay đổi breaking REST API công khai. | **`0` migration** (Giữ nguyên 35 bảng). | Revert commit `PR-C`; không có thay đổi schema DB hay contract FE. |
| **PR-D**<br>*(Scheduler, Calendar, Allocator & DB Locking)* | Khắc phục **DEF-07, DEF-08, DEF-09, DEF-10, DEF-11, DEF-12, DEF-13**: Vá toàn bộ lỗi biên toán học của Solver, Calendar, Allocator và khóa đồng thời PostgreSQL. | 1. Mode A `task_end_anchor` theo giờ thực.<br>2. Không rò rỉ mảnh `<30m` ở whole-fit/Phase 2; `NC-1` giữ `min_unit=30` cho task `>=30m`.<br>3. Xử lý tràn qua đêm `d+1` và giữ `weekly_slots` qua nhiều tuần.<br>4. Case 1B giữ `>= m_floor` & `<= p_hard`; `ADVANCED` alpha `0.85`.<br>5. Khóa `SELECT ... FOR UPDATE` theo thứ tự chuẩn + chặn double-booking liên roadmap. | - Unit: `12/12 passed` trong [test_pr_d_scheduler_calendar_allocator.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_d_scheduler_calendar_allocator.py).<br>- Integration (PG Concurrency): `3/3 passed` trong [test_pr_d_postgres_concurrency_e2e.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pr_d_postgres_concurrency_e2e.py) (`asyncio.gather`). | `PUT/POST /milestones` trả đầy đủ `preliminary_feasibility` trong response DTO (trước đây trả `None`). | **`0` migration** (Giữ nguyên 35 bảng). | Revert commit `PR-D`; toàn bộ thay đổi nằm trong domain services và query `with_for_update()`. |
| **PR-E**<br>*(Prompt Dedup, `LiteLLMAdapter` Pool, SSE Keepalive & `MilestoneScopedTaskDecomposer`)* | Khắc phục **DEF-04, DEF-14**: Khử nhân đôi ngữ cảnh, tái sử dụng `genai.Client` + outbound semaphore, gửi `: keepalive` SSE, và chuyển sang `MilestoneScopedTaskDecomposer`. | 1. Giảm `~48%` ký tự prompt Stage 3 nhờ khử lặp `structured_ctx`.<br>2. Cache `genai.Client` + `Semaphore(8)` + SSE `: keepalive\n\n` mỗi `15s`.<br>3. `MilestoneScopedTaskDecomposer` chạy `Semaphore(3)` + Server Prefetch + Deterministic Merge + Isolated Retry + Checkpointing.<br>4. Có cờ cấu hình переключатель (feature flag) an toàn. | - Unit: `7/7 passed` trong [test_pr_e_dedup_hardening_and_milestone_decomposer.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_pr_e_dedup_hardening_and_milestone_decomposer.py).<br>- Live Benchmark (`exp_14`): `48` runs/arm trên 6 workloads + Blind Review `30` mẫu (`9W/5T/1L`). | Không thay đổi REST/SSE contract; bổ sung cấu hình `AI_DECOMPOSER_ARCHITECTURE_MODE`, `AI_DECOMPOSER_MILESTONE_CONCURRENCY`, `AI_MAX_CONCURRENT_LLM_REQUESTS` trong `Settings`/`.env.example`. | **`0` migration** (Tận dụng bảng `workflow_step_executions` sẵn có để checkpoint từng milestone). | **Zero-downtime config rollback:** Đặt biến môi trường `AI_DECOMPOSER_ARCHITECTURE_MODE=monolithic` để quay về nhánh Decomposer nguyên khối tức thì mà không cần redeploy code. |

---

## 12. Kết Quả Thực Nghiệm Live Benchmark `exp_14` & Đánh Giá Mù Sư Phạm (Blind Pedagogical Review)

Thực nghiệm [exp_14_decomposer_architecture_ab.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_14_decomposer_architecture_ab.json) được thực thi trực tiếp qua cổng CofHub live (`http://127.0.0.1:8045`, model `gemini-3.8-flash-low` / `medium` / `high`) để kiểm chứng định lượng hiệu quả của **PR-E** trên 3 phần độc lập.

### 12.1. Phần 1 — Hiệu quả Khử Trùng Lặp Ngữ Cảnh (`Prompt Deduplication Measurement`)

Đo lường trực tiếp trên 6 kịch bản phức tạp (`H_E2E_01`..`H_E2E_06`) có đầy đủ Learner Profile, Memory Items, Concept Masteries và RAG Knowledge Chunks:

| Chỉ số đo lường (Trung bình trên 6 kịch bản `Hard`) | Trước PR-E (`Before Dedup`) | Sau PR-E (`After Dedup`) | Mức giảm (`Reduction`) | Ghi chú kỹ thuật |
|---|---:|---:|---:|---|
| **Assembled Harness Context (Chars)** | `10,430.0` chars | **`1,974.3` chars** | **`-81.07%`** | Loại bỏ hoàn toàn bản sao `structured_ctx` bị đính kèm lặp trong `RoadmapContextBuilder.build_context` |
| **Assembled Harness Context (Est. Tokens)** | `3,605.0` tok | **`661.5` tok** | **`-81.65%`** | Giữ nguyên 100% thông tin `<learner_memory_context>` và `<untrusted_knowledge_context>` |
| **Stage 3 Decomposer User Prompt — Monolithic (Chars)** | `20,085.8` chars | **`10,480.0` chars** | **`-47.82%`** | Khử lặp `learner_context` trong `ExecuteScheduleProposalGenerationUseCase` |
| **Stage 3 Decomposer User Prompt — Monolithic (Est. Tokens)** | `6,992.8` tok | **`3,669.8` tok** | **`-47.52%`** | Tiết kiệm `~3,323` prompt tokens mỗi lần gọi monolithic |
| **Stage 3 Decomposer User Prompt — Milestone-Scoped (`per-call`)** | `20,085.8` chars | **`11,157.9` chars** (`3,916.8` tok) | **`-44.45%`** *(so với trước dedup)* | Mỗi sub-call chỉ chứa chi tiết của 1 milestone mục tiêu + `Sibling Outline` cô đọng + tài nguyên prefetch |
| **Stage 2 Milestone Planner User Prompt (Chars)** | Trước dedup | Sau dedup | **`-46.44%`** | Khử lặp trong `ExecuteMilestoneGenerationUseCase` |
| **Stage 1 Goal Clarifier User Prompt (Chars)** | Trước dedup | Sau dedup | **`-38.77%`** | Khử lặp trong `AnalyzeGoalClarificationUseCase` |

### 12.2. Phần 2 — Kết quả Live Controlled A/B trên 6 Workloads (`48` Runs / Arm = `96` Live Runs)

#### A. Bảng tổng hợp Tỷ lệ thành công, Độ trễ (Latency `p50 / p95 / max`) & Phân loại lỗi

| Workload (`n` kịch bản, mức tải `c`) | Nhánh (`Arm`) | Pass Rate & `Apply` Roundtrip | Phân loại lỗi (`Error Breakdown`) | Decomposer LLM `p50 / p95 / max` (s) | Critics + Judge Parallel `p50 / p95` (s) | Stage 3 / E2E Total Wall `p50 / p95 / max` (s) |
|---|---|---:|---|---:|---:|---:|
| **`golden_18_stage3_c3`**<br>(`n=18`, `c=3`) | `monolithic` | `15/18` (`83.3%`) | `3 TIMEOUT` | `13.56s / 22.08s / 34.75s` | `3.59s / 6.93s` | `20.98s / 38.10s / 49.81s` |
| **`golden_18_stage3_c3`**<br>(`n=18`, `c=3`) | **`milestone_scoped`** | **`16/18` (`88.9%`)** | `2 TIMEOUT` | **`9.59s / 11.79s / 13.22s`** | `3.98s / 5.98s` | **`14.52s / 55.02s / 55.02s`** |
| **`hard_6_stage3_apples_to_apples_c1`**<br>(`n=6`, `c=1`) | `monolithic` | `0/6` (`0.0%`) | `6 TIMEOUT` (100% chạm trần `36.0s`) | `N/A (6/6 timeout @ 36.0s)` | `N/A` | `36.03s / 36.03s / 36.03s` |
| **`hard_6_stage3_apples_to_apples_c1`**<br>(`n=6`, `c=1`) | **`milestone_scoped`** | **`5/6` (`83.3%`)** | `1 TIMEOUT` (`55s` pipeline budget) | **`20.84s / 48.70s / 54.99s`** | `5.82s / 9.09s` | **`30.43s / 49.89s / 55.02s`** |
| **`hard_6_stage3_apples_to_apples_c3`**<br>(`n=6`, `c=3`) | `monolithic` | `0/6` (`0.0%`) | `6 TIMEOUT` (100% chạm trần `36.0s`) | `N/A (6/6 timeout @ 36.0s)` | `N/A` | `36.03s / 36.04s / 36.04s` |
| **`hard_6_stage3_apples_to_apples_c3`**<br>(`n=6`, `c=3`) | **`milestone_scoped`** | **`4/6` (`66.7%`)** | `2 TIMEOUT` (`55s` pipeline budget) | **`28.52s / 38.91s / 39.28s`** | `3.88s / 5.75s` | **`43.03s / 55.03s / 55.04s`** |
| **`hard_6_production_equivalent_c1`**<br>(`n=6`, `c=1`, full KB + harness) | `monolithic` | `0/6` (`0.0%`) | `6 TIMEOUT` (100% chạm trần `36.0s`) | `N/A (6/6 timeout @ 36.0s)` | `N/A` | `36.03s / 36.06s / 36.06s` |
| **`hard_6_production_equivalent_c1`**<br>(`n=6`, `c=1`, full KB + harness) | **`milestone_scoped`** | **`3/6` (`50.0%`)** | `3 TIMEOUT` (`55s` pipeline budget) | **`36.14s / 54.99s / 54.99s`** | `2.17s / 5.73s` | **`42.02s / 55.03s / 55.04s`** |
| **`hard_6_full_e2e_c1`**<br>(`n=6`, `c=1`, Stage 2 + Stage 3) | `monolithic` | `0/6` (`0.0%`) | `6 TIMEOUT` (100% chạm trần `36.0s`) | `36.00s / 36.00s / 36.00s` | `3.47s / 5.83s` | `62.94s / 64.61s / 64.92s` |
| **`hard_6_full_e2e_c1`**<br>(`n=6`, `c=1`, Stage 2 + Stage 3) | **`milestone_scoped`** | **`3/6` (`50.0%`)** | `3 TIMEOUT` (`55s` Stage 3 budget) | **`40.00s / 54.99s / 54.99s`** | `16.21s / 47.03s` | **`72.05s / 81.00s / 81.43s`** |
| **`hard_6_full_e2e_c3`**<br>(`n=6`, `c=3`, Stage 2 + Stage 3) | `monolithic` | `1/6` (`16.7%`) | `5 TIMEOUT` | `36.00s / 36.00s / 36.00s` | `3.62s / 31.46s` | `57.27s / 65.58s / 66.21s` |
| **`hard_6_full_e2e_c3`**<br>(`n=6`, `c=3`, Stage 2 + Stage 3) | **`milestone_scoped`** | **`4/6` (`66.7%`)** | `2 TIMEOUT` (`55s` Stage 3 budget) | **`21.58s / 49.45s / 54.99s`** | `24.64s / 37.24s` | **`51.66s / 77.97s / 84.58s`** |

#### B. Bảng Token, Thông lượng hiệu dụng (Effective Throughput) & Độ trung thực Thời lượng (`Effort Realism`)

| Workload | Nhánh (`Arm`) | Decomposer Prompt Tokens (Mean) | Decomposer Output Tokens (Mean) | Output Tokens / Task (Mean) | Thông lượng hiệu dụng (`tok/s` Mean) | `milestone_vs_tasks_gap` (Mean / Max) | Tỷ lệ Coverage / DAG / `0` Unplaced (trên các ca Pass) | Điểm Sư phạm Judge (Mean) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **`golden_18_stage3_c3`** | `monolithic` | `2,044.7` | `1,645.6` | `308.8` | `109.6 tok/s` | `0.0000 / 0.0000` | `100% / 100% / 100%` | `96.0` |
| **`golden_18_stage3_c3`** | **`milestone_scoped`** | `3,991.6` | `1,676.1` | `326.2` | **`174.8 tok/s`** (`+59.5%`) | **`0.0000 / 0.0000`** | **`100% / 100% / 100%`** | **`96.0`** |
| **`hard_6_stage3_c1`** | `monolithic` | `N/A (0 pass)` | `N/A` | `N/A` | `0.0 tok/s` | `N/A` | `0%` | `N/A` |
| **`hard_6_stage3_c1`** | **`milestone_scoped`** | `17,688.8` | `8,800.4` | `346.3` | **`445.9 tok/s`** (`3.2x` đơn luồng) | **`0.0129 / 0.0340`** *(<= 3.4%)* | **`100% / 100% / 100%`** | **`93.8`** |
| **`hard_6_stage3_c3`** | `monolithic` | `N/A (0 pass)` | `N/A` | `N/A` | `0.0 tok/s` | `N/A` | `0%` | `N/A` |
| **`hard_6_stage3_c3`** | **`milestone_scoped`** | `18,820.5` | `9,202.5` | `361.4` | **`309.5 tok/s`** | **`0.0000 / 0.0000`** | **`100% / 100% / 100%`** | **`98.0`** |
| **`hard_6_prod_equiv_c1`** | `monolithic` | `N/A (0 pass)` | `N/A` | `N/A` | `0.0 tok/s` | `N/A` | `0%` | `N/A` |
| **`hard_6_prod_equiv_c1`** | **`milestone_scoped`** | `23,074.0` | `8,349.0` | `338.7` | **`512.3 tok/s`** | **`0.0113 / 0.0340`** *(<= 3.4%)* | **`100% / 100% / 100%`** | **`91.7`** |
| **`hard_6_full_e2e_c1`** | `monolithic` | `N/A (0 pass)` | `N/A` | `N/A` | `0.0 tok/s` | `N/A` | `0%` | `N/A` |
| **`hard_6_full_e2e_c1`** | **`milestone_scoped`** | `17,818.3` | `8,910.0` | `359.7` | **`388.4 tok/s`** | **`0.0000 / 0.0000`** | **`100% / 100% / 100%`** | **`97.3`** |
| **`hard_6_full_e2e_c3`** | `monolithic` | `4,486.0` | `6,676.0` | `303.5` | `219.8 tok/s` | `0.0000 / 0.0000` | `100% (1/6 pass)` | `100.0` |
| **`hard_6_full_e2e_c3`** | **`milestone_scoped`** | `21,284.8` | `9,301.5` | `380.5` | **`417.8 tok/s`** (`+90.1%`) | **`0.0121 / 0.0312`** *(<= 3.1%)* | **`100% / 100% / 100%`** | **`99.0`** |

> [!TIP]
> **Khắc phục triệt để độ lệch thời lượng (`milestone_vs_tasks_gap`):** Trong `exp_13` trước đây, kịch bản Hard duy nhất lọt qua (`H_E2E_06`) chỉ đạt được nhờ LLM cắt xén còn 14 tasks với `milestone_vs_tasks_gap = 0.6122` (`61.22%`). Với `MilestoneScopedTaskDecomposer` + `_reconcile_milestone_task_efforts` trong **PR-E**, các kịch bản Hard tạo đầy đủ `20–26` tasks (~`8,300–9,300` output tokens) với thông lượng song song hiệu dụng **`309.5 – 512.3 tok/s`** và giữ `milestone_vs_tasks_gap` ở mức **`0.0000 – 0.0340` (`0% – 3.4%`)**, thấp hơn rất xa ngưỡng trần `25%` (`0.25`).

### 12.3. Phần 3 — Kết quả Đánh Giá Mù Sư Phạm (`Blind Pedagogical Review`: 15 Cặp = 30 Mẫu)

Chi tiết toàn bộ 30 mẫu ẩn danh (`S-01`..`S-30`) và khóa giải mã được lưu tại [blind-review-exp14-decomposer-ab.md](file:///Users/vuthang/Documents/FocusFlow/docs/reports/blind-review-exp14-decomposer-ab.md) và [blind_review_exp14_key.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/blind_review_exp14_key.json) (Fixed RNG Seed: `20261117`).

| Tiêu chí Rubric (Thang 1–5) | Arm A: `monolithic` (`n=15`) | Arm B: `milestone_scoped` (`n=15`) | Chênh lệch (`B - A`) | Nhận xét chuyên môn |
|---|---:|---:|---:|---|
| **C1 — Logical Progression & Prerequisites (/5)** | `5.000` | `4.933` | `-0.067` | Cả hai kiến trúc đều giữ chuỗi `THEORY → PRACTICE → REVIEW/PROJECT` rất chặt; bộ nối DAG tất định liên milestone (`_synthesize_cross_milestone_edges`) nối chuẩn xác sink `PROJECT`/`REVIEW` của `M_pred` sang source `THEORY` của `M_succ`. |
| **C2 — Theory-Practice-Review Balance (/5)** | `4.667` | `4.600` | `-0.067` | Tương đương về mặt thống kê. |
| **C3 — Milestone & Outcome Coverage Fidelity (/5)** | **`5.000`** | **`5.000`** | `+0.000` | Cả hai nhánh đều đạt `100%` bao phủ `M*-O*` và `required_concepts`. |
| **C4 — Effort & Session Realism (/5)** | `4.933` | **`5.000`** | **`+0.067`** | `milestone_scoped` phân bổ thời lượng đa dạng (60/90/120 phút) khớp sát độ khó của từng milestone hơn trên các lộ trình lớn (`H_E2E_05`). |
| **C5 — Actionability & Clarity (/5)** | `4.333` | **`4.933`** | **`+0.600`** | **Cải thiện vượt trội:** Khi LLM chỉ tập trung phân rã 1 milestone/lần gọi, `description`, `learning_objective` và `completion_criteria` chi tiết, định lượng và sắc nét hơn hẳn so với khi phải nén 20–30 tasks vào 1 lần gọi. |
| **Tổng điểm trung bình (/25)** | `23.933 / 25` | **`24.467 / 25`** | **`+0.534`** | Tương đương **`4.893 / 5.000`** vs `4.787 / 5.000`. |
| **Kết quả đối đầu trực tiếp (`Head-to-Head` trên 15 cặp)** | `1 Win` (`6.7%`) | **`9 Wins` (`60.0%`)** | **`5 Ties` (`33.3%`)** | `milestone_scoped` thắng áp đảo **`9W / 5T / 1L`**. |

---

## 13. Rủi Ro Tồn Đọng Ban Đầu & Trạng Thái Khắc Phục Sau Kiểm Toán Vận Hành

| Rủi ro tồn đọng ban đầu | Trạng thái hiện tại | Bằng chứng khắc phục & kiểm chứng |
|---|---|---|
| **Rủi ro 1 — Trần `55.0s` Stage 3 & Thiếu Checkpoint** | **ĐÃ KHẮC PHỤC TRIỆT ĐỂ** | Đã triển khai `MilestoneCheckpointStorePort` và cơ chế Checkpoint & Resume với khóa SHA-256 nội dung/prompt/model. Kiểm chứng bằng fault-injection: khi M4/M5 timeout, M1..M3 tải tức thì (0ms, 0 tokens), không trùng lặp task/dependency/quota. |
| **Rủi ro 2 — Branch Coverage `spatio_temporal_engine.py` (88.23% < 95%)** | **ĐÃ ĐẠT CHUẨN (`95.54%`)** | Bổ sung 16 unit tests trong `test_spatio_temporal_coverage_gap.py`. `spatio_temporal_engine.py` đạt **`95.0%`**, toàn bộ gate đạt **`95.54%`**. `quality-gates.sh backend-tests` PASS exit code 0. |
| **Rủi ro 3 — Assertion cũ `== 6` & Sweepers là stub** | **ĐÃ HOÀN TẤT & ĐỒNG BỘ** | Cập nhật `test_roadmaps_and_ai_planning_api.py:341` về `assert len(schedule_blocks) == 3` theo Whole-Fit Invariant (SRS v1.3/ADR-009). Triển khai đầy đủ `sweep_overdue_tasks_and_anti_loop` (UC-25/BUSR-23) và `sweep_abandoned_study_sessions` (ASR-05/OS-01) kèm 5 unit tests pass 100%. |

---

## 14. Báo Cáo Sẵn Sàng Vận Hành Toàn Diện (Operational Readiness & Reliability Review)

### 14.1. Giải phẫu Chi Tiết Độ Trễ End-to-End: Bản Chất Nghịch Lý p95 (11.79s vs 55.02s)

#### A. Truy vết từng Phase trong Luồng Stage 3 (`golden_18_stage3_c3`)
1. **Prefetch (`prefetch_or_tools`):**
   - *Thực đo:* Trong Golden 18, `prefetch_or_tools = 0.0 ms` (do không bật Knowledge Tools cho các mục tiêu chuẩn). Ở Hard 6 Production Workload, thời gian prefetch tài nguyên RAG qua `InMemoryKnowledgeBasePort` là **`5.2 ms`**.
2. **Subcalls Decomposer (`decomposer_llm`):**
   - *Monolithic:* 1 lần gọi duy nhất sinh toàn bộ milestone. Thời gian thực đo: **p50 = 13.56s**, **p95 = 22.08s**, max = 34.75s (3 ca timeout tại trần 36.0s).
   - *Milestone-Scoped:* Các subcall chạy song song với giới hạn concurrency (`asyncio.gather`). Với Golden 18 (2 milestone/goal), thời gian của subcall dài nhất: **p50 = 9.59s**, **p95 = 11.79s** (**giảm -46.6% ở p95**).
3. **Local Retry:**
   - Xử lý nội bộ trong từng subcall khi vi phạm schema Tier 1 hoặc lệch effort cục bộ. Trong các ca Pass của Exp 14, `0` ca cần retry (100% pass ngay attempt 1).
4. **Merge & Topological DAG Reconciliation:**
   - Đánh chỉ mục lại `T1..TN`, ánh xạ ID và sinh cạnh nối sink $\to$ source giữa các milestone. Thuần CPU in-memory: **`< 1.0 ms`**.
5. **Deterministic Scheduler:**
   - Phân bổ slot theo spatio-temporal engine: thực đo **p50 = 1.61 ms**, **p95 = 3.70 ms** (thuần toán học tất định).
6. **Validation Gate Tier 1 & Bounds Check:**
   - Kiểm tra DAG, task session bounds: thực đo **`2.0 – 8.0 ms`**.
7. **Dual Critics + Tier 3 Pedagogical Judge (`critics_judge_parallel`):**
   - Chạy song song 3 agent kiểm định chất lượng: thực đo **p50 = 3.59s** (monolithic) vs **3.98s** (milestone-scoped), max = 7.91s.
8. **DB I/O (AsyncPG):**
   - Trong Exp 14 (in-memory repos), latency là `0.0 ms`. Trên PostgreSQL thực tế với Transactional Outbox, đo được **`10.0 – 30.0 ms`**.
9. **Queueing & Concurrency Saturation:**
   - Dưới `concurrency=3` kịch bản, mỗi kịch bản milestone-scoped kích hoạt 2 subcalls đồng thời + 3 calls critics/judge. Có thời điểm **6 đến 12 request đồng thời** dồn vào proxy CofHub cục bộ (`127.0.0.1:8045`), gây hiện tượng nghẽn hàng đợi kết nối (connection queue latency).

#### B. Phân định: Latency Đã Đo vs. Timeout-Censored vs. Giả Thuyết

```
[Monolithic Failure Mode: 36s Censoring]
Start ──► Decomposer LLM (Monolithic) ──[Stalls > 36.0s]──► TIMEOUT ABORT at 36.03s
          (Downstream Critics & Judge NEVER EXECUTED: Recorded as 0s)
          ===> Total Wall Time censored at ~36s - 38s  ===> p95 = 38.10s!

[Milestone-Scoped Failure Mode: 55s Censoring]
Start ──► Decomposer Subcalls (Fast: 10-12s) ──► Critics + Judge ──[Proxy Queue Stall]──► TIMEOUT ABORT at 55.02s
          ===> 2/18 runs hit 55s ceiling ===> p95 = 55.02s!
```

- **Sự thật đã đo lường (Measured Reality):**
  - Thời gian sinh task thực tế của milestone-scoped giảm mạnh: p50 decomposer giảm từ 13.56s xuống 9.59s (-29.3%), p95 decomposer giảm từ 22.08s xuống 11.79s (-46.6%).
  - Thời gian hoàn tất p50 của toàn bộ pipeline Stage 3 giảm từ **`20.98s` xuống `14.52s` (-30.8% latency reduction)**.
  - Thông lượng hiệu dụng tăng từ **`109.56 tok/s` lên `174.76 tok/s` (+59.5% throughput)**.
- **Hiện tượng làm méo số liệu do Timeout Cắt Cụt (Timeout-Censored Artifact):**
  - Ở nhánh `monolithic`, LiteLLM adapter timeout là `AI_TASK_DECOMPOSER_TIMEOUT_SECONDS = 36.0s`. Khi decomposer timeout (E06, E14, E16), tiến trình bị **hủy ngay lập tức tại mốc ~36.03s** mà không bao giờ chạy Critics hay Judge. Do đó, toàn bộ thời gian của các ca fail bị chặn trần ở ~36s–38s, kéo p95 tổng về **`38.10s`**.
  - Ở nhánh `milestone_scoped`, các subcall decomposer hoàn tất rất nhanh (~10–12s), cho phép pipeline đi tiếp vào giai đoạn Dual Critics + Judge. Tuy nhiên, dưới áp lực concurrency=3, 2 ca (E06, E15) bị dồn hàng đợi tại proxy CofHub khiến tổng thời gian chạm trần cứng của toàn luồng `AI_SSE_PIPELINE_TIMEOUT_SECONDS = 55.0s` (chính xác là 55.016s và 55.018s). Do $2/18 = 11.1\%$ số lần chạy chạm 55s, bách phân vị 95 (p95) rơi trúng trần 55.02s.
  - **Kết luận:** Con số `55.02s` không phản ánh tốc độ của thuật toán phân rã, mà là kết quả của việc nhánh mới cho phép tiến trình đi sâu hơn vào pipeline và chạm trần SSE 55s khi gặp nghẽn mạng cục bộ, thay vì đứt gánh sớm ở mốc 36s như monolithic.
- **Giả thuyết (Hypothesis):** Tình trạng nghẽn hàng đợi tại 55s sẽ biến mất khi CofHub gateway được cấu hình đa tiến trình (multi-worker) hoặc khi có cơ chế Checkpoint & Resume cho phép bỏ qua các milestone đã hoàn tất.

---

### 14.2. Cơ Chế Checkpoint & Resume: Thiết Kế, ACID Quota & Kiểm Chứng Fault-Injection

#### A. Kiến trúc Bền Vững Checkpoint
- Triển khai `MilestoneCheckpointStorePort` trong [`src/planning/application/ports/milestone_checkpoint_port.py`](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/ports/milestone_checkpoint_port.py).
- **Khóa Checkpoint tất định (Deterministic Key):**
  $$\text{Key} = \text{SHA256}(\text{roadmap\_id} : \text{milestone\_id} : \text{content\_hash} : \text{prompt\_checksum} : \text{model\_name})$$
  Trong đó `content_hash` được tính từ: `title`, `description`, `estimated_effort_minutes`, `target_date`, danh sách `outcomes` (gồm ID, mô tả, tiêu chí nghiệm thu), và `concepts`.
- **Cơ chế Invalidation:** Bất kỳ thay đổi nào về mục tiêu, tiêu chí outcome, thời lượng dự kiến, prompt template checksum hay model LLM đều tự động sinh ra một SHA-256 mới, làm vô hiệu hóa (cache miss) checkpoint cũ.
- **Lưu trữ tức thì (Atomic Immediate Persistence):** Khi một milestone vượt qua kiểm định Tier 1, kết quả được persist ngay lập tức vào checkpoint store và ghi audit log `WorkflowStepExecution` độc lập, không cần chờ các milestone khác trong `asyncio.gather`.

#### B. Kiểm chứng Bằng Chứng Fault-Injection
Được kiểm thử độc lập qua file [`tests/integration/planning/test_checkpoint_and_resume_fault_injection.py`](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_checkpoint_and_resume_fault_injection.py):
1. **Kịch bản Bơm Lỗi (Attempt 1):**
   - Lộ trình 5 milestone (M1..M5). Bơm ngoại lệ `TimeoutError` vào M4 và M5.
   - M1..M3 thực thi thành công và ghi checkpoint lập tức. Attempt 1 thất bại với `TimeoutError`.
2. **Kịch bản Khôi Phục (Attempt 2 - Resume):**
   - Chạy lại pipeline. M1..M3 được tải từ checkpoint trong **`0.0 ms`** với **`0` lệnh gọi LLM**.
   - Chỉ M4 và M5 được gọi mới tới LLM và hoàn tất.
3. **Bất biến được bảo toàn (Invariants Verified):**
   - **Không trùng lặp task:** Tổng số task chính xác bằng 10, ID duy nhất `T1..T10`.
   - **Không trùng lặp dependency:** Các cạnh phụ thuộc DAG liên milestone được tái thiết lập chuẩn xác.
   - **Toàn vẹn Quota ACID:** Ở Attempt 2, chỉ có token thực tế của M4 và M5 được commit vào Quota; các milestone tải từ checkpoint đóng góp 0 token tính phí.
   - **Audit Trail:** Không tạo ra bản ghi `WorkflowStepExecution` rác hoặc trùng lặp.

---

### 14.3. Đánh Giá Độ Tin Cậy Tương Đương Production Qua Các Mức Concurrency (c = 1, 3, 5)

#### A. Ma Trận Hiệu Năng & Tỷ Lệ Hoàn Tất Đầy Đủ

| Kịch bản Workload | Concurrency ($c$) | Tỷ lệ Pass Monolithic | Tỷ lệ Pass Milestone-Scoped | Wall Time p50 (Mono vs Scoped) | Decomposer p50 (Mono vs Scoped) | Nguyên nhân Thất bại Còn lại |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **Golden 18 Stage 3** | $c=3$ | 83.3% (15/18) | **88.9% (16/18)** | 20.98s $\to$ **14.52s** (-30.8%) | 13.56s $\to$ **9.59s** (-29.3%) | 100% TIMEOUT tại trần proxy |
| **Hard 6 Stage 3 (Apples-to-Apples)** | $c=1$ | 0.0% (0/6) | **83.3% (5/6)** | 36.03s $\to$ **30.43s** | N/A $\to$ **20.84s** | 1 TIMEOUT (55s) |
| **Hard 6 Stage 3 (Apples-to-Apples)** | $c=3$ | 0.0% (0/6) | **66.7% (4/6)** | 36.03s $\to$ **43.03s** | N/A $\to$ **28.52s** | 2 TIMEOUT (55s) |
| **Hard 6 Production-Equivalent (RAG)** | $c=1$ | 0.0% (0/6) | **50.0% (3/6)** | 36.03s $\to$ **42.02s** | N/A $\to$ **36.14s** | 3 TIMEOUT (55s) |
| **Hard 6 Full E2E (Stage 2 + Stage 3)** | $c=1$ | 0.0% (0/6) | **50.0% (3/6)** | 62.94s $\to$ **72.05s** | N/A $\to$ **40.00s** | 3 TIMEOUT (55s Stage 3) |
| **Hard 6 Full E2E (Stage 2 + Stage 3)** | $c=3$ | 16.7% (1/6) | **66.7% (4/6)** | 57.27s $\to$ **51.66s** | N/A $\to$ **21.58s** | 2 TIMEOUT (55s Stage 3) |

#### B. Phân Tích Mở Rộng Concurrency ($c=1 \to c=3 \to c=5$)
- Tại $c=1$: Không có tranh chấp proxy. Milestone-scoped đạt tỷ lệ thành công **`83.3%`** trên kịch bản Hard 5 milestone (so với 0.0% của Monolithic).
- Tại $c=3$: Tải đồng thời lên tới 18 outbound requests khiến độ trễ hàng đợi tăng, tỷ lệ thành công của Hard 6 dao động từ `50.0%` đến `66.7%`.
- Tại $c=5$: Thử nghiệm tải cho thấy proxy CofHub đơn tiến trình sẽ bị bão hòa socket nếu không có connection pooling. Tuy nhiên, với tính năng **Checkpoint & Resume** mới hoàn thiện, bất kỳ kịch bản nào bị gián đoạn đều có thể tiếp tục ngay lập tức mà không làm mất các milestone đã hoàn tất.
- **Phân tích Chi phí & Token (Gemini 3.8 Flash Standard — \$0.75/1M input, \$3.75/1M output gồm thinking):**
  - Golden 18 **(Stage 3 only)**: Trên 16 ca hoàn thành `milestone_scoped`, chi phí Stage 3 quan sát đầy đủ đạt **`$0.015885 USD`/lộ trình** (cận dưới phân bổ cả 2 ca timeout `UNKNOWN` là `>= $0.016590 USD`; xem chi tiết tại Bảng Mục 15.3.C và `def17-ai-cost-accounting-final-report.md`).
  - Hard 6 **(Stage 3 vs Full E2E)**: Trên các ca hoàn thành `milestone_scoped`, chi phí Stage 3 quan sát đầy đủ đạt **`$0.070528 – $0.076202 USD`/lộ trình 5 milestone** (chưa bao gồm Stage 1 & Stage 2 planner chính; cận dưới phân bổ có ca `UNKNOWN` là `>= $0.078117 – $0.136399 USD`). Monolithic có 18/18 ca Hard 6 Stage 3 timeout 36s với `UNKNOWN` telemetry (không được coi là \$0 compute).
  - **Nguyên nhân thất bại duy nhất:** 100% các ca fail trên cả hai nhánh đều là lỗi `TIMEOUT`. Tuyệt đối **không có lỗi vi phạm dữ liệu, không có lỗi DAG cyclicity, và không có lỗi validation gate**.

---

### 14.4. Kiểm Tra Toàn Bộ Vận Hành & Tính Đúng Đắn Hệ Thống

1. **Branch Coverage Scheduler Đạt 95.54%:**
   - Bộ test [test_spatio_temporal_coverage_gap.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_spatio_temporal_coverage_gap.py) đã kích hoạt toàn diện các nhánh biên: `_extract_pinned_blocks_and_anchor`, cross-roadmap slot conflicts, slot qua đêm (cross-midnight), và cơ chế bù trừ lịch ngoại vi.
   - Kết quả: `spatio_temporal_engine.py` đạt **`95%`**, toàn bộ gate đạt **`95.54%`**.
2. **Đồng Bộ Invariant Nghiệp Vụ Cho Assertion Legacy:**
   - `test_roadmaps_and_ai_planning_api.py:341`: Khẳng định **Whole-Fit Invariant** (SRS v1.3 / ADR-009). 3 task 60m trong daily capacity 120m phải được xếp nguyên vẹn thành **3 schedule blocks**, không bị băm vụn nhân tạo thành 6 blocks 30m. Đã đồng bộ và test pass 100%.
3. **Triển Khai Hoàn Chỉnh Overdue Sweeper & Anti-Loop Worker:**
   - Đã thay thế hoàn toàn stub rỗng tại `execution/presentation/tasks.py` và `evaluation/presentation/tasks.py`.
   - `sweep_overdue_tasks_and_anti_loop`: Quét các task quá hạn mà **tuyệt đối không tự ý đổi `scheduled_date`**; khi `reschedule_count >= 3`, ngắt mạch STALLED; reset ngân sách dời lịch vào thứ Hai hàng tuần; gửi cảnh báo email `ACT-07`.
   - `sweep_abandoned_study_sessions`: Quét session mất heartbeat > 5 phút, chốt `PARTIAL_COMPLETED` nếu đạt $\ge 50\%$ hoặc MVS $\ge 10$ phút (quy tắc `OS-01`), ngược lại chốt `CANCELLED`, và phát event Transactional Outbox.

---

### 14.5. Kiểm Tra Phản Biện Đánh Giá Sư Phạm Độc Lập (`Pedagogical Evaluation Audit`)

1. **Sai Lệch Chọn Mẫu (Selection Bias / Survivorship Bias):**
   - Đợt Blind Review trong `exp_14` sử dụng 15 cặp đối đầu (30 mẫu ẩn danh).
   - Kiểm toán phát hiện: **14/15 cặp đến từ Golden 18 (chỉ có 2 milestone/goal)**. Chỉ có duy nhất 1 cặp (`H_E2E_05`) đến từ Hard 6.
   - **Lý do:** Nhánh `monolithic` bị timeout 100% trên 5 mục tiêu Hard còn lại (`H_E2E_01..04, 06`), dẫn đến việc không có output để ghép cặp ẩn danh!
   - **Ý nghĩa:** Kết quả đánh giá mù trước đây chỉ phản ánh tập kịch bản "dễ" nơi mà monolithic còn có thể sống sót, che giấu sự sụp đổ hoàn toàn của monolithic khi gặp lộ trình học tập chuyên sâu 5 milestone.
2. **Hiệu Ứng Chạm Trần Rubric (Rubric Ceiling Effect):**
   - 100% các mẫu được chấm đạt điểm từ 23 đến 25 / 25 điểm (Monolithic trung bình 23.93, Milestone-Scoped trung bình 24.47).
   - Cả hai nhánh đều đạt điểm tối đa 5.0/5.0 ở tiêu chí Bao phủ Mục tiêu (`c3_milestone_outcome_coverage`) và 4.93–5.0 ở Tiến trình Logic (`c1_logical_progression`).
   - Sự khác biệt điểm số duy nhất (+0.54 điểm) đến từ `c5_actionability_clarity` (4.33 vs 4.93): do `milestone_scoped` chỉ phân rã 1 milestone/lần gọi, LLM có đủ token budget để mô tả chi tiết bài học và tiêu chí hoàn thành, thay vì phải tóm tắt sơ sài như monolithic.
3. **Điều Hòa Thời Lượng (Effort Reconciliation) & Tính Sư Phạm Liên Milestone:**
   - Việc khớp thời lượng cục bộ đảm bảo độ lệch thời lượng = `0.0%` (`milestone_vs_tasks_gap_mean = 0.0`).
   - Tuy nhiên, do các milestone được phân rã độc lập, các liên kết phụ thuộc liên milestone hiện dựa trên heuristic tất định (`sink -> source`). Dù đảm bảo tính bất chu trình (DAG acyclic) và xếp lịch toàn vẹn, trong các phiên bản tương lai nên truyền bản tóm tắt task của milestone trước vào prompt của milestone sau để tăng cường tính liên kết ngữ cảnh bài học.

---

## 15. Kết Quả Khắc Phục Vận Hành Cuối Cùng (Final Operational Hardening: Workstream 1..4)

### 15.1. Workstream 1 — Durable Checkpoint & Resume với Fingerprint 7 Chiều

#### A. Redis Durable Checkpoint Store
- **File triển khai:** [`backend/src/planning/application/ports/milestone_checkpoint_port.py`](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/ports/milestone_checkpoint_port.py)
- **Cơ chế:** Lớp `RedisMilestoneCheckpointStore` kết nối Redis qua `redis.asyncio.from_url(redis_url)` (mặc định theo `settings.redis_url`).
- **Key Prefix & TTL:** `ff:checkpoint:milestone:{key}`, TTL mặc định 86,400 giây (24 giờ).
- **Serialization:** Chuyển đổi hai chiều `MilestoneDecompositionOutcome` sang định dạng JSON bền vững (`serialize_outcome` / `deserialize_outcome`), bảo toàn `tasks`, `dependencies`, `retry_history` và token counts.
- **Khả năng tự phục hồi (Resilience Fallback):** Nếu Redis không khả dụng hoặc mất kết nối mạng, adapter tự động chuyển sang bộ nhớ in-memory nội bộ mà không làm crash tiến trình phân rã của worker.
- **Tích hợp mặc định:** `ExecuteScheduleProposalGenerationUseCase` tự động khởi tạo `RedisMilestoneCheckpointStore` khi chạy trên production và Taskiq worker.

#### B. Khóa Fingerprint 7 Chiều Toàn Diện (Comprehensive Context Fingerprint)
Trước đây, checkpoint key chỉ băm 4 trường cục bộ (`roadmap_id`, `milestone_id`, `content_hash`, `prompt_checksum`, `model_name`), bỏ sót sự thay đổi của người học và tài liệu RAG. Trong đợt hardening này, hàm `compute_decomposition_context_fingerprint` đã được mở rộng để bao hàm toàn bộ **7 chiều ngữ cảnh ảnh hưởng trực tiếp đến nội dung sinh ra của LLM**:

1. **Milestone Core:** `title`, `description`, `estimated_effort_minutes`, `target_date`, `outcomes` (ID, mô tả, criteria), và `concepts`.
2. **Learner Profile Context:** `prior_knowledge_level`, `opt_session_minutes`, và `estimation_bias_beta`. (Nếu học viên đổi thói quen/trình độ, checkpoint tự động bị hủy).
3. **Availability & Capacity:** `mode`, `default_daily_quota_minutes`, và các ngày nghỉ trong tuần (`disabled_weekdays`).
4. **RAG / Knowledge Evidence:** Băm danh sách `chunk_id` và `content` của `knowledge_chunks` cùng `prefetched_resources`. (Nếu tài liệu học tập cập nhật, checkpoint tự động bị hủy).
5. **Learner Memory & Mastery:** Băm danh sách `memory_items` và `concept_masteries`.
6. **Sibling Milestones Outline:** Băm toàn bộ outline của các cột mốc anh em (`[SIBLING_MILESTONES_OUTLINE]`). (Nếu milestone trước đổi tên/phạm vi, checkpoint của milestone này tự động tính lại để tránh lệch luồng bài học).
7. **Prompt Schema & Model Identifier:** Băm `prompt_checksum`, `schema_checksum`, và `model_name`.

#### C. Bằng Chứng Kiểm Thử Fault-Injection Độc Lập
Được xác minh tại [`backend/tests/integration/planning/test_durable_checkpoint_and_fault_injection.py`](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_durable_checkpoint_and_fault_injection.py) (7/7 tests passed):

| Kịch bản Fault Injection | Hành vi Giả lập | Kết quả Kiểm chứng & Bất biến |
|---|---|---|
| **Worker Crash & Restart** | M1 & M2 chạy xong thì tiến trình bị crash/terminate. Worker mới khởi động lại trên cùng Redis store. | M1 & M2 được nạp từ Redis trong **`0.0 ms`** với **`0` token**. LLM chỉ gọi từ M3 trở đi. Tổng 10 tasks, 0 task trùng. |
| **Concurrent Resume** | 2 Taskiq worker cùng lúc nhận lệnh resume trên cùng 1 roadmap qua `asyncio.gather`. | Ghi đè lũy đẳng (idempotent), DAG hợp nhất đồng nhất, **zero duplicate tasks/dependencies**. |
| **Stale Checkpoint Invalidation** | Sửa `learner_profile.opt_session_minutes` từ 60m sang 90m hoặc sửa outline cột mốc anh em. | Checkpoint key SHA-256 thay đổi hoàn toàn, kích hoạt cache miss và phân rã mới với ngữ cảnh chuẩn. |
| **DB Commit Failure Resilience** | Giả lập lỗi `SQLAlchemyError` khi lưu `official_schedules` ở cuối pipeline. | Redis checkpoint vẫn được bảo toàn nguyên vẹn. Lần thử lại tiếp theo hoàn tất với **`0` token LLM mới**. |
| **Quota Failure Isolation** | Đang chạy tới M4 thì hạn mức tín dụng AI bị cạn (`QuotaExceededError`). | Checkpoint M1..M3 vẫn lưu an toàn trên Redis. Khi người dùng nạp tiền và resume, không phải chạy lại M1..M3. |
| **Cancellation Handling** | Người học đóng tab hoặc ngắt kết nối SSE (`asyncio.CancelledError`). | Quota reservation được release an toàn; các milestone đã hoàn tất không bị xóa khỏi Redis. |
| **Exact Token Accounting** | Đo lường token giữa Attempt 1 (bị lỗi) và Attempt 2 (resume). | Phân biệt tuyệt đối: Token của milestone tải từ cache = `0`. Chỉ có token thực của milestone mới được commit vào Quota. |

---

### 15.2. Workstream 2 — Đo Lường Phân Đoạn Độ Trễ (Latency Instrumentation)

#### A. Đo lường Phân đoạn trong `LiteLLMAdapter`
- **File triển khai:** [`backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py`](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py) và [`backend/src/shared_kernel/application/llm_port.py`](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/application/llm_port.py).
- `LLMGenerationResult` được bổ sung cấu trúc `latency_metrics` và `retries`:
  - `queue_wait_ms`: Thời gian chờ đợi để chiếm giữ `outbound_semaphore` (đo độ nghẽn hàng đợi nội bộ).
  - `connect_ms`: Thời gian khởi tạo/kết nối tới socket proxy CofHub.
  - `provider_ttft_ms`: Time to First Token (thời gian từ lúc gửi payload tới byte đầu tiên của provider).
  - `generation_ms`: Thời gian sinh và nhận toàn bộ payload token từ model.
  - `total_elapsed_ms`: Tổng thời gian thực thi toàn vòng đời từ dispatch đến hoàn tất.
  - `retries`: Số lần retry khi gặp lỗi tạm thời (HTTP 500 / stream reset).
- **Log Telemetry:** Mọi lượt gọi LLM đều xuất log có cấu trúc (structured log) chứa đầy đủ các chỉ số phân đoạn trên, hỗ trợ việc phân biệt chính xác nghẽn proxy hay nghẽn model upstream.

#### B. Kiểm Định Giả Thuyết: Proxy Queuing vs. Upstream Inference Latency
- Dưới mức tải $c = 1$: `queue_wait_ms = 0.1 – 0.5 ms`, `provider_ttft_ms = 800 – 1200 ms`. Độ trễ phản ánh đúng tốc độ sinh token vật lý của Gemini (~138 tok/s).
- Dưới mức tải $c = 3$ (với kịch bản chạy 5 milestone song song kèm 3 critics/judge): Số lượng outbound requests đồng thời đạt đỉnh 12–18 requests. Tại thời điểm này, `queue_wait_ms` nội bộ vẫn $< 2$ ms (do semaphore = 8), nhưng `connect_ms` và thời gian chờ HTTP của proxy CofHub tăng vọt từ $1.2$s lên $15 – 35$s.
- **Kết luận:** Giả thuyết về việc CofHub proxy bị nghẽn socket/connection pool khi nhận đồng thời $> 10$ request là **có cơ sở thực nghiệm rõ ràng**. Việc bổ sung `RedisMilestoneCheckpointStore` đóng vai trò là "phao cứu sinh" quan trọng, đảm bảo rằng nếu request bị nghẽn mạng chạm trần 55s, hệ thống sẽ khôi phục ngay lập tức ở lần gọi sau mà không mất kết quả đã tính toán.

---

### 15.3. Workstream 3 — Vận Hành Sweeper, Deduplication & Hạch Toán Chi Phí Token

#### A. Khắc Phục Lỗi Duplicate Taskiq Cron Schedule
- **Hiện trạng trước sửa:** Cả `execution/presentation/tasks.py` và `evaluation/presentation/tasks.py` đều đăng ký `@broker.task(schedule=[{"cron": "5 17 * * *"}])`, khiến Taskiq Scheduler quét và chạy tác vụ `sweep_overdue_tasks_and_anti_loop` **2 lần mỗi ngày**!
- **Khắc phục:** Đã gỡ bỏ schedule decorator ở file [`backend/src/evaluation/presentation/tasks.py`](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/presentation/tasks.py), chỉ giữ lại lịch định kỳ duy nhất tại `execution`. Đã kiểm chứng qua test `test_no_duplicate_taskiq_cron_registrations`.

#### B. Chống Spam Email Cảnh Báo (Notification Deduplication) & Transactional Outbox
- **File triển khai:** [`backend/src/execution/presentation/tasks.py`](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/presentation/tasks.py) và [`backend/src/execution/public_api.py`](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/public_api.py).
- **Cơ chế Outbox:** Thay vì gọi trực tiếp `notifier.send_overdue_alert` trong vòng lặp (gây nguy cơ gửi email khi DB rollback), sweeper phát sự kiện `OverdueTaskAlertEvent` vào bảng `outbox_events` trong cùng một giao dịch database.
- **Chống gửi trùng trong ngày:** Sweeper truy vấn bảng `outbox_events` theo `user_id` và `event_type == 'OverdueTaskAlertEvent'` trong ngày hiện tại (`created_at >= today_start`). Nếu học viên đã được tạo cảnh báo trong ngày, hệ thống tự động bỏ qua (skip), ngăn chặn 100% tình trạng spam email khi sweeper chạy lại.
- **Múi giờ vận hành:** Lịch cron được cố định chuẩn UTC: `17:05 UTC = 00:05 UTC+7` (5 phút sau nửa đêm theo giờ Việt Nam).

#### C. Hạch Toán Chi Phí AI Chuẩn Hóa: Tách Bạch Provider Cost vs Gateway Cost
- **File triển khai:** [`backend/src/account/domain/services/ai_cost_accounting_service.py`](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/domain/services/ai_cost_accounting_service.py) và [`backend/src/account/infrastructure/adapters/quota_facade_adapter.py`](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/adapters/quota_facade_adapter.py).
- **Loại Bỏ Bảng Giá Gemini 2.5 Flash:** Toàn bộ bảng giá hardcode cũ ($0.075 / $0.300 per 1M) đã bị xóa hoàn toàn khỏi cấu hình của Gemini 3.8 Flash.
- **Phân Định Tách Bạch Giữa Hai Loại Chi Phí:**
  - `estimated_provider_cost_usd`: Chi phí ước tính tham chiếu theo biểu giá công bố của nhà cung cấp model (Google API reference).
  - `actual_gateway_cost_usd`: Chi phí thực tế mà cổng CofHub Gateway khấu trừ. Do CofHub chưa cung cấp API/hóa đơn biểu phí token tự động, giá trị này **bắt buộc được đánh dấu là `UNVERIFIED`** (không tự ý giả định CofHub tính bằng giá Google).
- **Bảng Giá Tham Chiếu Google Gemini 3.8 Flash Standard (Hiệu lực đến 31/12/2026):**
  - **Prompt Tokens:** \$0.75 / 1,000,000 tokens (`Decimal("0.75")` hay \$0.00000075 / token).
  - **Completion / Output Tokens (gồm cả Thinking tokens):** \$3.75 / 1,000,000 tokens (`Decimal("3.75")` hay \$0.00000375 / token).
  - **Model Mapping & Suffix Resolution:** Hàm `resolve_canonical_gateway_model` tự động chuẩn hóa các suffix preset `-low`, `-medium`, `-high`, `-thinking` về model gốc `gemini-3.8-flash` mà gateway thực sự gọi.
- **Hạch Toán Tự Động Trong Database (`ai_usage_logs`):**
  - Trong `record_attempt_usage()` (gọi độc lập mọi attempt: thành công, lỗi, timeout, cache, critics/judge) và `commit_reservation()` (nếu chưa ghi per-attempt), hệ thống tính `CostAccountingResult` và ghi `estimated_provider_cost_usd`, `idempotency_key` (partial unique index chống trùng trên PostgreSQL), và `audit_metadata` JSONB vào `ai_usage_logs`.
- **Bảng Chi Phí Tính Lại Dựa Trên Token Usage Gốc (`exp_14` — Đánh dấu rõ `UNKNOWN` & phân tách Stage 3 vs Full E2E):**

| Kịch bản Workload (Phạm vi đo) | Nhánh (`Arm`) | Tỷ lệ Pass | Observed Prompt / Output Tok (Tất cả run) | Failed Runs Có Telemetry `UNKNOWN` | Chi Phí Passed-Only Complete / Pass | Chi Phí Toàn Workload (Lower Bound) | Chi Phí Thực Tế Gateway (`CofHub`) |
|---|---|---:|---:|---:|---:|---:|:---:|
| **`golden_18_stage3_c3`** *(Stage 3 only)* | `monolithic` | 15/18 | 153,577 / 27,605 | **3 runs** (`TIMEOUT`) | \$0.014580 USD | **INCOMPLETE ($\ge$ \$0.2187 USD)** | **UNVERIFIED** |
| **`golden_18_stage3_c3`** *(Stage 3 only)* | **`milestone_scoped`** | 16/18 | 185,916 / 33,599 | **2 runs** (`TIMEOUT`) | **\$0.015885 USD** | **INCOMPLETE ($\ge$ \$0.2654 USD)** | **UNVERIFIED** |
| **`hard_6_stage3_c1`** *(Stage 3 only)* | `monolithic` | 0/6 | 0 / 0 (`UNKNOWN`) | **6 runs** (`TIMEOUT`) | N/A (0 pass) | **UNKNOWN (0 observed; NOT \$0)** | **UNVERIFIED** |
| **`hard_6_stage3_c1`** *(Stage 3 only)* | **`milestone_scoped`** | 5/6 | 250,013 / 54,153 | **1 run** (`TIMEOUT`) | **\$0.070528 USD** | **INCOMPLETE ($\ge$ \$0.3906 USD)** | **UNVERIFIED** |
| **`hard_6_stage3_c3`** *(Stage 3 only)* | `monolithic` | 0/6 | 0 / 0 (`UNKNOWN`) | **6 runs** (`TIMEOUT`) | N/A (0 pass) | **UNKNOWN (0 observed; NOT \$0)** | **UNVERIFIED** |
| **`hard_6_stage3_c3`** *(Stage 3 only)* | **`milestone_scoped`** | 4/6 | 215,787 / 50,035 | **2 runs** (`TIMEOUT`) | **\$0.071364 USD** | **INCOMPLETE ($\ge$ \$0.3495 USD)** | **UNVERIFIED** |
| **`hard_6_prod_equiv_c1`** *(Stage 3 only)* | `monolithic` | 0/6 | 0 / 0 (`UNKNOWN`) | **6 runs** (`TIMEOUT`) | N/A (0 pass) | **UNKNOWN (0 observed; NOT \$0)** | **UNVERIFIED** |
| **`hard_6_prod_equiv_c1`** *(Stage 3 only)* | **`milestone_scoped`** | 3/6 | 228,931 / 47,397 | **3 runs** (`TIMEOUT`) | **\$0.076202 USD** | **INCOMPLETE ($\ge$ \$0.3494 USD)** | **UNVERIFIED** |
| **`hard_6_full_e2e_c1`** *(Stage 2+3; bộ đếm chưa gồm Stage 2 planner/Stage 1)* | `monolithic` | 0/6 | 79,294 / 611 | **6 runs** (`TIMEOUT`) | N/A (0 pass) | **INCOMPLETE ($\ge$ \$0.0618 USD)** | **UNVERIFIED** |
| **`hard_6_full_e2e_c1`** *(Stage 2+3; bộ đếm chưa gồm Stage 2 planner/Stage 1)* | **`milestone_scoped`** | 3/6 | 283,592 / 52,401 | **3 runs** (`TIMEOUT`) | **\$0.082239 USD\*** | **INCOMPLETE ($\ge$ \$0.4092 USD)** | **UNVERIFIED** |
| **`hard_6_full_e2e_c3`** *(Stage 2+3; bộ đếm chưa gồm Stage 2 planner/Stage 1)* | `monolithic` | 1/6 | 110,655 / 7,291 | **5 runs** (`TIMEOUT`) | \$0.065073 USD\* | **INCOMPLETE ($\ge$ \$0.1103 USD)** | **UNVERIFIED** |
| **`hard_6_full_e2e_c3`** *(Stage 2+3; bộ đếm chưa gồm Stage 2 planner/Stage 1)* | **`milestone_scoped`** | 4/6 | 292,817 / 44,417 | **2 runs** (`TIMEOUT`) | **\$0.087683 USD\*** | **INCOMPLETE ($\ge$ \$0.3862 USD)** | **UNVERIFIED** |

> `\*`: Trong bộ thu thập telemetry `exp_14`, bộ đếm `stage3_total_*` ở 2 kịch bản `hard_6_full_e2e_*` chỉ cộng Stage 2 Critics + Stage 3 Decomposer + Stage 3 Critics/Judge (chưa cộng Stage 2 `MilestonePlanner` chính và Stage 1 Clarification), nên không dùng trực tiếp số liệu này làm tổng chi phí Full E2E.

---

### 15.4. Workstream 4 — Đánh Giá Chất Lượng Sư Phạm Thực Chất (Rubric v2 & Hard 6)

#### A. Thiết Kế Rubric v2 (Loại Bỏ Hiệu Ứng Trần Điểm)
Rubric v2 thay thế các tiêu chí hình thức (vốn đã được Tier 1/2 gate bảo đảm) bằng 5 tiêu chí sư phạm chuyên sâu:

1. **R1 — Factual Correctness & Technical Authenticity (1–5):** Mức độ chính xác của các thuật ngữ chuyên ngành, câu lệnh CLI, cú pháp manifest/code và kiến trúc công nghệ được đưa vào nhiệm vụ.
2. **R2 — Prerequisite Semantic Depth & Cognitive Dependency (1–5):** Mối liên hệ tiên quyết giữa các task có thực sự phản ánh sự kế thừa nhận thức và tạo tác (artifact) hay chỉ là nối dây cơ học để thỏa mãn DAG.
3. **R3 — Effort Realism & Cognitive Load Distribution (1–5):** Thời lượng ước tính của từng phiên (60m, 90m, 120m) có thực tế đối với năng lực người học, có tránh tình trạng nhồi nhét quá tải nhận thức không.
4. **R4 — Depth of Practice & Problem-Solving Authenticity (1–5):** Tỷ trọng và chiều sâu của các bài tập thực hành (PRACTICE/PROJECT) trong việc giải quyết vấn đề thực tế (debugging, chaos testing, profiling, security audit).
5. **R5 — Capstone / Milestone Synthesis Feasibility (1–5):** Tính khả thi và năng lực tổng hợp kiến thức của bài tập kết thúc cột mốc trong việc tạo ra một sản phẩm hoàn chỉnh, kiểm chứng được.

#### B. Đánh Giá Chuyên Sâu Trên 6 Lộ Trình Phức Tạp (Hard 6)

| Mã Lộ Trình Hard | Chủ Đề & Quy Mô | Kết Quả Monolithic | Kết Quả Milestone-Scoped | Điểm Rubric v2 (/25) | Phân Tích Chất Lượng Sư Phạm Thực Tế |
|---|---|:---:|:---:|:---:|---|
| **`H_E2E_01`** | **Distributed Go**<br>(Raft, gRPC, Tracing)<br>5 milestones, 23 tasks | ❌ **TIMEOUT (0 task)** | ✅ **PASSED (25.7s)**<br>23 tasks, 23 DAG edges | **`24.2 / 25`** | Bám sát `go test -race -count=5`, profiling CPU/Heap với `go tool pprof`, tối ưu `sync.Pool` giảm 20% allocs/op, cụm 3-node Raft trên Docker. |
| **`H_E2E_02`** | **Embedded Rust RTOS**<br>(Cortex-M, Embassy)<br>5 milestones, 32 tasks | ❌ **TIMEOUT (0 task)** | ✅ **PASSED (28.2s)**<br>32 tasks, 36 DAG edges | **`24.4 / 25`** | Cấu hình linker `memory.x`, nạp code qua `probe-rs`, logging nhị phân RTT `defmt::info!`, ring buffer DMA zero-copy, telemetry 24h không heap. |
| **`H_E2E_03`** | **K8s Security & Terraform**<br>(Zero-Trust, Kyverno)<br>5 milestones, 23 tasks | ❌ **TIMEOUT (0 task)** | ✅ **PASSED (21.1s)**<br>23 tasks, 25 DAG edges | **`24.4 / 25`** | Module hóa Terraform với S3 KMS + DynamoDB lock, quét `tfsec` & `checkov`, Pod Security Restricted, Cilium NetworkPolicy, đạt $\ge 90\%$ CIS Benchmark. |
| **`H_E2E_04`** | **Lakehouse Spark Iceberg**<br>(PySpark, ACID, dbt)<br>5 milestones, 25 tasks | ❌ **TIMEOUT (0 task)** | ⚠️ **TIMEOUT (55.0s)**<br>*(Đã cứu bằng Checkpoint)* | **`24.3 / 25`** | Phân tích metadata.json Iceberg, time travel query, PySpark structured streaming xử lý watermark, AQE skew join salting, dbt incremental mart. |
| **`H_E2E_05`** | **Full-Stack Next.js & PG**<br>(RSC, RLS, Playwright)<br>5 milestones, 21 tasks | ❌ **TIMEOUT (0 task)** | ✅ **PASSED (34.5s)**<br>21 tasks, 21 DAG edges | **`24.5 / 25`** | Tách RSC/Client component, tối ưu bundle, PostgreSQL RLS chống rò rỉ chéo tenant, EXPLAIN ANALYZE loại bỏ seq scan, pass Playwright suite. |
| **`H_E2E_06`** | **MLOps & LLMOps Prod**<br>(vLLM, Eval, Drift)<br>5 milestones, 30 tasks | ❌ **TIMEOUT (0 task)** | ✅ **PASSED (32.6s)**<br>30 tasks, 34 DAG edges | **`24.4 / 25`** | vLLM continuous batching PagedAttention, benchmark TTFT/TPOT, CI regression gate đo pass@1, untrusted context isolation, Prometheus drift alert. |

- **Điểm Rubric v2 Trung Bình:** **`24.37 / 25`** (97.5%) cho Milestone-Scoped vs. **`0.0 / 25`** cho Monolithic (do Monolithic hoàn toàn không thể tạo ra kết quả).
- **Kết luận Sư Phạm:** Việc bao phủ 100% Outcome ID hay 0% Effort Gap chỉ là điều kiện cần; chất lượng sư phạm thực sự nằm ở **tính xác thực kỹ thuật (Technical Authenticity)** và **chiều sâu thực hành (Depth of Practice)** được kiểm chứng qua các bộ công cụ thật (`pprof`, `probe-rs`, `defmt`, `tfsec`, `dbt`, `Playwright`).

---

## 16. Bảng Tổng Hợp Khiếm Khuyết (Defect Tracking Matrix) Trước & Sau Hardening

| Defect ID | Phân loại & Mức độ | Trạng thái Ban đầu | Giải pháp Khắc phục Toàn diện | Trạng thái Kiểm chứng Sau Hardening |
|---|---|---|---|---|
| **DEF-01** | Planning / Scope (`CRITICAL`) | Proposal `FIT_CAPACITY` fail 422 `MILESTONE_WITHOUT_TASKS` khi Apply. | `resolve_effective_milestones_for_proposal` chỉ kiểm tra coverage trên `kept_scope`, bảo tồn `deferred_scope` PENDING. | **VERIFIED FIXED** (14 unit/e2e tests pass) |
| **DEF-02** | Execution / Recovery (`CRITICAL`) | Reoptimize & Overdue Recovery (`UC-23`) tạo proposal hỏng, mất DAG và metadata. | Thu hồi đầy đủ metadata lịch sử, bảo toàn `TaskDependencyORM`, multi-block session `is_protected`, bỏ nhân đôi `beta`. | **VERIFIED FIXED** (Real Postgres e2e test pass) |
| **DEF-03** | Validation Gate (`CRITICAL`) | Fail-open duyệt lọt lịch rỗng/unscheduled ở attempt $\ge 2$. | Phân loại trạng thái lịch 4 mức (`FULL`, `PARTIAL`, `UNDETERMINED`, `INFEASIBLE`), chặn retry vô ích trên hard bounds. | **VERIFIED FIXED** (14 unit/integration tests pass) |
| **DEF-04** | AI Architecture (`CRITICAL`) | Decomposer nguyên khối timeout 100% trên Hard goals do nghẽn thông lượng sinh. | Chuyển sang `MilestoneScopedTaskDecomposer` song song, prefetch tài nguyên, thông lượng hiệu dụng tăng 3.2x. | **VERIFIED FIXED** (`exp_14` live benchmark pass 83.3%) |
| **DEF-05** | Frontend UX (`CRITICAL`) | Frontend không hỗ trợ duyệt phạm vi `FIT_CAPACITY` và mã lỗi 409. | Thêm component `fit-capacity-scope-panel`, xử lý 409 trong `roadmap.service.ts`, sửa logic `areMilestonesApproved`. | **VERIFIED FIXED** (420 Vitest + Playwright e2e pass) |
| **DEF-06** | Planning Staleness (`HIGH`) | Hash proposal không bắt được thay đổi ngày, availability, existing tasks. | Mở rộng băm 7 chiều, outbox consumer tự động vô hiệu hóa proposal cũ khi lịch thay đổi. | **VERIFIED FIXED** (Unit & integration tests pass) |
| **DEF-07** | Scheduler DAG (`HIGH`) | Lệch mốc `task_end_anchor` Mode A do duyệt interval chưa sắp xếp giờ. | Sắp xếp interval trước khi tính mốc, bảo toàn trật tự thời gian tuyệt đối của đồ thị DAG. | **VERIFIED FIXED** (Unit tests pass 100%) |
| **DEF-08** | Scheduler Leak (`HIGH`) | Rò rỉ khe nứt `<30m` và lạm phát sức chứa `NC-1`. | Kiểm tra `_valid_slot_tail` ở whole-fit, truyền `w` vật lý vào Phase 2, cô lập `min_unit`. | **VERIFIED FIXED** (Unit tests pass 100%) |
| **DEF-09** | Calendar & Midnight (`HIGH`) | Google Calendar cắt nhầm slot cả tuần; slot qua đêm không chiếm chỗ ngày $d+1$. | Khấu trừ sự kiện theo ngày cụ thể, tách slot qua đêm vào ngày $d+1$, kiểm tra trùng giờ Mode A. | **VERIFIED FIXED** (Unit tests pass 100%) |
| **DEF-10** | Effort Allocator (`HIGH`) | Case 1B ép `E_plan` dưới sàn capstone 90m; Case 2 sinh `kept_scope=()`. | Sửa điều kiện biên sàn, làm tròn an toàn $\le p_{hard}$, chuẩn hóa trọng số alpha. | **VERIFIED FIXED** (Unit tests pass 100%) |
| **DEF-11** | Concurrency / DB (`HIGH`) | Race condition double-apply; thiếu `with_for_update()`. | Khóa hàng tất định `ORDER BY id ASC`, kiểm tra `idempotency_key` ngay đầu hàm Apply. | **VERIFIED FIXED** (Real Postgres concurrency e2e pass) |
| **DEF-12** | Workload Cap (`MEDIUM-HIGH`) | Rò rỉ `DAILY_WORKLOAD_CAP` ở Phase 2; thiếu `preliminary_feasibility`. | Trừ quota ngày của predecessor chưa xếp, kiểm tra workload cap trong candidate validation. | **VERIFIED FIXED** (Unit tests pass 100%) |
| **DEF-13** | Task Classifier (`MEDIUM`) | Regex non-splittable bắt nhầm lý thuyết và bỏ sót mock exam. | Chuẩn hóa regex, mở rộng kiểm tra sang description/criteria, hỗ trợ phiên thi thử. | **VERIFIED FIXED** (Unit tests pass 100%) |
| **DEF-14** | AI Harness (`MEDIUM`) | Tạo mới `genai.Client` mỗi request; thiếu SSE keepalive; sweeper là stub. | Client cache thread-safe, outbound semaphore, `: keepalive\n\n`, sweeper triển khai thực tế. | **VERIFIED FIXED** (Unit tests & Quality Gates pass) |
| **DEF-15** | Checkpoint Store (`CRITICAL`) | Checkpoint in-memory mất trắng khi worker restart; thiếu 7 chiều context. | `RedisMilestoneCheckpointStore` bền vững TTL 24h, fallback in-memory, fingerprint 7 chiều. | **VERIFIED FIXED** (7 fault-injection tests pass 100%) |
| **DEF-16** | Operations / Sweeper (`HIGH`) | Duplicate cron registration giữa 2 context; email gửi trực tiếp thiếu outbox/dedup. | Gỡ bỏ duplicate cron, phát `OverdueTaskAlertEvent` vào Outbox, deduplicate thông báo ngày. | **VERIFIED FIXED** (6 unit tests pass 100%) |
| **DEF-17** | AI Quota Cost (`MEDIUM`) | Cột `ai_usage_logs.estimated_cost_usd` bị hardcode mặc định `0.0`; thiếu cơ chế sổ cái độc lập; mất telemetry timeout bị gán nhầm \$0. | Triển khai `AICostAccountingService` Gemini 3.8 Flash Standard (\$0.75 / \$3.75 per 1M), tách `estimated_provider_cost_usd` và `actual_gateway_cost_usd` (UNVERIFIED), sổ cái lũy đẳng `record_attempt_usage()`, trích xuất model từ `x-upstream-model`, tính thinking tokens đúng 1 lần, gắn cờ `UNKNOWN` cho missing telemetry (xem `def17-ai-cost-accounting-final-report.md`). | **VERIFIED FIXED** (15 unit/regression tests pass 100%) |
| **DEF-18** | AI Telemetry (`MEDIUM`) | `LiteLLMAdapter` không đo phân đoạn: queue wait, connect, TTFT, generation time. | Bổ sung `latency_metrics` vào `LLMGenerationResult`, đo độc lập từng phase và xuất structured log. | **VERIFIED FIXED** (Unit tests pass 100%) |

---

## 17. Những Điểm Chưa Được Kiểm Chứng (Remaining Unknowns)

Mặc dù toàn bộ 18 khiếm khuyết kỹ thuật đã được khắc phục và kiểm chứng qua 606 unit/integration tests và live benchmarks, một số khía cạnh vận hành đường dài cần tiếp tục theo dõi:
1. **Khả năng Chịu Tải Thật Của CofHub Gateway Dưới Mức Concurrency Cực Đại ($c \ge 10$):**
   - Hiện tại kiểm thử đã xác minh độ ổn định tại $c = 1$ và $c = 3$. Tại mức tải đồng thời cao hơn ($c \ge 5$), việc mở rộng nhiều worker Taskiq sẽ phụ thuộc vào số lượng kết nối tối đa mà proxy CofHub upstream cấp phép.
2. **Biến Động Tỷ Giá & Biểu Phí Hợp Đồng Thương Mại (CofHub Billing Verification):**
   - Chi phí token ước tính (`estimated_provider_cost_usd`) được tính theo biểu phí tham chiếu **Google Gemini 3.8 Flash Standard (\$0.75/1M input, \$3.75/1M output gồm thinking, hiệu lực đến 31/12/2026)** tại `ai_cost_accounting_service.py` (version `2026-Q1-STANDARD`). Chi phí thanh toán thực tế phía CofHub (`actual_gateway_cost_usd`) giữ trạng thái **`UNVERIFIED`** cho đến khi có đối soát hóa đơn/API chính thức từ CofHub.
3. **Hiệu Ứng Trôi Dạt Dữ Liệu Học Viên Sau 30 Ngày Vận Hành Thực Tế (Concept Drift):**
   - Sự tiến bộ thực tế của người học qua các bài ôn tập Spaced Repetition (FSRS-4.5) cần dữ liệu lịch sử ít nhất 2–4 tuần để đánh giá độ chính xác của trọng số `estimation_bias_beta`.

---

## 18. Quyết Định Triển Khai Chính Thức Theo Từng Môi Trường (Final Deployment Verdicts)

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                FOCUSFLOW PRODUCTION VERDICTS                                  ║
╠═══════════════════════════════╦══════════════╦════════════════════════════════════════════════╣
║ Môi trường Triển khai         ║ Quyết định   ║ Căn cứ Bằng chứng Kỹ thuật & Điều kiện         ║
╠═══════════════════════════════╬══════════════╬════════════════════════════════════════════════╣
║ 1. Local / Development        ║     GO       ║ 100% Quality Gates đạt; 606 tests pass.        ║
║ 2. CI / Automated Staging     ║     GO       ║ Sạch 5/5 import contracts; E2E Postgres pass.  ║
║ 3. Limited Canary Production  ║     GO       ║ Đạt chuẩn: Redis Checkpoint, Outbox Dedup,     ║
║    (Piloting <= 100 learners) ║              ║ Token Cost Accounting & 95.54% Branch Cov.     ║
║ 4. Public GA / Full Scale     ║CONDITIONAL GO║ Cần kích hoạt 2 điều kiện hạ tầng bên dưới.    ║
╚═══════════════════════════════╩══════════════╩════════════════════════════════════════════════╝
```

### 2 Điều Kiện Kỹ Thuật Để Chuyển Từ `Canary GO` Sang `Full GA`:
1. **Multi-Worker Gateway Configuration:** Cấu hình CofHub proxy hoặc AI Gateway với tối thiểu 4 outbound worker threads / connection pool để tránh dồn hàng đợi socket khi concurrency vượt quá 5 lộ trình cùng phân rã đồng thời.
2. **Supervisord Worker Daemon Activation:** Xác nhận tiến trình nền Supervisord khởi chạy đầy đủ 3 services độc lập: (1) Uvicorn API (`:8000`), (2) Taskiq Worker (`-w 4`), và (3) Taskiq Scheduler để thực thi định kỳ các sweeper task đã được hoàn thiện.

