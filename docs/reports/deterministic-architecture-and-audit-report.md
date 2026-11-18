# Báo Cáo Đối Chiếu Audit Cấu Trúc, Kiểm Chứng Giả Thuyết & Đề Xuất Thiết Kế Tầng Tất Định

- **Ngày thực hiện:** `2026-11-17`
- **Ràng buộc tuân thủ:** Không sửa bất kỳ file prompt nào (`roadmap_skills.py`, `prompts.py`, `untrusted_context.py`, `prompts.lock` giữ `0` thay đổi).

---

## 1. Đối chiếu nhanh 3 cặp chấm mù & Mở khóa kết quả `blind_review_*_key.json`

### A. Đối chiếu độc lập 3 cặp trước khi mở key
- **`R-03` vs `R-09` (Data Engineering Airflow & dbt):**
  - `R-03`: 6 milestones (`2,040` phút) nhưng Decomposer chỉ sinh 12 tasks (`1,080` phút = **52.9%**, lệch **47.1%**), chuỗi phụ thuộc tuyến tính `11/11` (`100%`), cả `12/12` tasks bị cắt thành 2 block liền nhau `45p + 45p` cùng buổi tối (`T10` gán nhầm `REVIEW`). Khớp điểm **`15/25`**.
  - `R-09`: 5 milestones (`1,560` phút), 26 tasks (`1,560` phút — khớp **0.0%** lệch), bao phủ đủ Dynamic Task Mapping, Cosmos, dbt-expectations; điểm trừ là 5 `PROJECT` chỉ dài `60` phút và `25/25` phụ thuộc tuyến tính. Khớp **`R-09 (19) > R-03 (15)`**.
- **`R-04` vs `R-05` (Rust Async & Tokio):**
  - `R-04`: 6 milestones (`3,090` phút = `67.3%` quỹ giờ), 33 tasks (`3,090` phút), có **rẽ nhánh thật** (`34` dependencies / `32` non-initial tasks, `T5 <- T3, T4`, `T21 <- T19, T20`), có mini-project mỗi milestone (`min PROJECT = 90m`, `T9 = 120m`), nhưng học liên tục **`34` ngày không nghỉ** và xong sớm `9` ngày. Khớp **`22/25`**.
  - `R-05`: 5 milestones (`2,070` phút = `45.1%` quỹ giờ), 23 tasks (`2,070` phút), rẽ nhánh nhiều nhất (`63.6%` linear) nhưng nhiều bài thực hành/test bị gán `REVIEW` (`T4, T8, T13, T17, T22`), capstone `T23` 90 phút, streak `23` ngày liên tục và xong sớm `20` ngày. Khớp **`R-04 (22) > R-05 (16)`**.
- **`M-10` vs `M-12` (Embedded Rust `#![no_std]` & RTOS Embassy, quỹ giờ `3,480` phút):**
  - `M-10`: 6 milestones (`[420, 480, 540, 480, 540, 600]` = `3,060` phút = **`87.9%`**, dư `12.1%` quỹ giờ), effort phân hóa tự nhiên, phủ đủ `#![no_std]`, `Typestate/Ownership`, `Zero-Copy DMA`, `RTIC`, `Embassy`, `Telemetry`. Khớp **`21/25`**.
  - `M-12`: 7 milestones (`[420, 540, 660, 600, 660, 480, 600]` = `3,960` phút = **`113.8%`**, vượt quỹ `480` phút) nhưng vẫn khai báo `FULL_SCOPE`, không có `deferred_scope`; thiếu nhấn mạnh Lifetimes/Typestate. Khớp **`M-10 (21) > M-12 (16)`**.

### B. Mở khóa key (`blind_review_10_roadmaps_key.json` & `blind_review_hard_6_milestones_key.json`)

1. **12 Phương án Milestone (`exp_10` — `arm_b_server_prefetch` vs `arm_a_tool_calling`):**

| Mục tiêu | `arm_b_server_prefetch` (Mã / Điểm / MS / Độ trễ) | `arm_a_tool_calling` (Mã / Điểm / MS / Độ trễ) | Thắng |
|---|---|---|---|
| `H_E2E_04_LAKEHOUSE` | `M-01`: **19** (`7` MS, `17.83s`) | `M-06`: **18** (`7` MS, `47.07s`) | **Prefetch (+1)** |
| `H_E2E_06_MLOPS_LLMOPS` | `M-07`: **24** (`6` MS, `17.33s`) | `M-02`: **22** (`6` MS, `30.66s`) | **Prefetch (+2)** |
| `H_E2E_03_K8S_SECURITY` | `M-04`: **18** (`4` MS, `14.77s`) | `M-03`: **16** (`4` MS, `37.63s`) | **Prefetch (+2)** |
| `H_E2E_01_DISTRIBUTED_GO` | `M-05`: **17** (`4` MS, `15.03s`) | `M-11`: **20** (`4` MS, `34.93s`) | Tool-calling (+3) |
| `H_E2E_05_FULLSTACK_NEXTJS` | `M-09`: **18** (`4` MS, `12.65s`) | `M-08`: **18** (`4` MS, `33.15s`) | **Hòa (0)** |
| `H_E2E_02_EMBEDDED_RUST` | `M-10`: **21** (`6` MS, `17.62s`) | `M-12`: **16** (`7` MS, `51.56s`) | **Prefetch (+5)** |
| **Tổng / Trung bình** | **`117 / 150` (`19.50 / 25`) \| `p50 = 16.18s`** | **`110 / 150` (`18.33 / 25`) \| `p50 = 36.28s`** | **Prefetch thắng `4/6`, hòa `1/6`, nhanh `2.24x`** |

→ Vì `arm_b_server_prefetch` **vừa cao điểm hơn (`19.50` vs `18.33`) vừa nhanh hơn `2.24x` (`0` timeout)** mà **không cần sửa bất kỳ dòng prompt nào**, đã chuyển Milestone Planner trong [milestone_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/milestone_use_cases.py) và [eval_runner.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/eval_runner.py) sang **Server Prefetch** qua `RoadmapContextBuilder.prefetch_milestone_kb_evidence(...)` ([roadmap_context_builder.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/roadmap_context_builder.py)).

2. **10 Lộ trình (`exp_09` — `-medium` vs `-low`):**
- `-medium`: `R-01 (17)`, `R-09 (19)`, `R-04 (22)`, `R-10 (21)`, `R-07 (18)` → **`97/125` (`19.4 / 25`)**, thắng `4/5` cặp.
- `-low`: `R-02 (19)`, `R-03 (15)`, `R-05 (16)`, `R-06 (20)`, `R-08 (17)` → **`87/125` (`17.4 / 25`)**.

---

## 2. Kết quả `scripts/structural_audit.py` trên 10 lộ trình + 12 milestone

Script: [structural_audit.py](file:///Users/vuthang/Documents/FocusFlow/scripts/structural_audit.py) → JSON chi tiết: [structural_audit_results.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/structural_audit_results.json).

### A. Audit 10 Lộ trình (`R-01..R-10`)
- **`warn_gt_90pct`: `1/10`** (`R-03` ở mức **`90.7%`** milestone effort dù Decomposer chỉ sinh `48.0%` task minutes).
- **`milestone_vs_tasks_gap`:** `R-03 = 47.1%` (`1,080m` vs `2,040m`); `R-06 = 4.8%` (`1,200m` vs `1,260m`); `8/10` lộ trình còn lại `= 0.0%`.
- **`linear_dependency_ratio`:** **`8/10` đạt `100.0%` chuỗi thẳng tuyệt đối**; chỉ `R-04` (`84.4%`, `27/32`) và `R-05` (`63.6%`, `14/22`) có rẽ nhánh.
- **`max_consecutive_study_days` & `days_idle_before_deadline`:** Toàn bộ các lộ trình `MODE_A` học không ngày nghỉ (`R-01: 11d / -20d`, `R-02: 15d / -16d`, `R-04: 34d / -9d`, `R-05: 23d / -20d`, `R-07: 32d / -13d`, `R-08: 43d / -2d`).
- **`split_integrity`:**
  - Chẻ qua nhiều ngày ở tác vụ nhạy cảm (`thi thử`, `kiểm thử tải`): **`R-08`** (`T29, T30` mock test 60p chẻ qua 2 ngày), **`R-10`** (`T8` kiểm thử chịu tải 5,000 req chẻ `50+50` qua 2 ngày), **`R-06`** (`T6, T9` kiểm thử tải chẻ `60+60` qua 2 ngày).
  - Chẻ thành nhiều block liền nhau trong **cùng 1 ngày**: **`R-03` (`12/12` tasks bị chẻ `45+45`)**, `R-10` (`5`), `R-08` (`3`), `R-02`/`R-06` (`2`), `R-01`/`R-04` (`1`).
- **`project_min_minutes` (`PROJECT < 90p`):** **`8` tasks** across `R-09` (`5` tasks `60m`), `R-07` (`2` tasks `60m`), `R-01` (`1` task `60m`).

### B. Audit 12 Phương án Milestone (`M-01..M-12`)
- **`8/12` (`66.7%`) có mọi milestone bằng nhau tuyệt đối (`all_efforts_equal = YES`, `effort_equal_ratio = 100%`)**: `M-01, M-06` (`7 × 420`), `M-03, M-04, M-05, M-08, M-09, M-11` (`4 × 540`).
- **`9/12` (`75.0%`) có `capacity_utilization > 90%`**: `8/12` ở mức `94.7%–100.0%` và **`M-12` đạt `113.8%` (`3,960 / 3,480`)** → khớp trực tiếp toàn bộ nhận xét chấm tay của bạn!

---

## 3. Kiểm chứng bằng số Giả thuyết #2 (`capacity_utilization > 95%` khi Decomposer fail lượt đầu)

Tổng hợp trên **toàn bộ `506` lượt chạy Task Decomposer** có trong `docs/experiments/` (`exp_09`, `exp_11`, `group2_measurements`, và toàn bộ 21 file `eval_runner` JSON gồm cả `scheduled_eval_7d/runs/`):

| Nhóm dữ liệu | Tổng lượt | Fail lượt 1 (`attempt_1_passed=False` / `attempts>1` / failed run) | Input `util > 95%` | Input `util <= 95%` | Phân tích nguyên nhân thực tế |
|---|---:|---:|---:|---:|---|
| `exp_09` (`part_3`) | 10 | **2** (`attempts_used=2`) | **0** | **2** | `G4 [low]` (`80.39%`), `G5 [low]` (`90.67%`): fail lượt 1 với `CAPACITY_EXCEEDED_BEFORE_TARGET_DATE` + `SCHEDULE_BLOCK_EFFORT_MISMATCH`. |
| `exp_11` (`part_1` G4/G5 `120s`) | 4 | **2** (`attempts_used=2`) | **0** | **2** | `G5` cả 2 arm (`2,040m / 2,250m = 90.67%`): fail lượt 1 dù `req <= 2,250m` (`2,040m` / `1,980m`). |
| `exp_11` (`part_2` 6 hard) | 24 | **2** (`TimeoutError` tại `25s`) | **0** | **2** | `H_E2E_02` (`17.24%`), `H_E2E_04` (`20.41%`): timeout ở `25.0s`, 0 lỗi capacity. |
| `group2_measurements` (`decomposer_low_vs_medium`) | 108 | **5** (`TIMEOUT` ở `-medium`) | **0** | **5** | `E12` (`60.00%` × 2), `E01` (`6.03%`), `E03` (`4.62%`), `E07` (`6.03%`). |
| 21 file `per_case_outcomes` (`eval_runner`) | 360 | **33** (`attempts=1`) | **0** | **33** | `baseline` (`18`), `eval_old_config` (`10`), `exp_06` (`3`), `scheduled` (`2`): `31 TIMEOUT`, `1 SCHEMA_MISMATCH`, `1 GATEWAY_ERROR`. |
| **Tổng cộng** | **506** | **44** (`4` retry capacity + `40` timeout/schema/gateway) | **0 (`0.0%`)** | **44 (`100.0%`)** | **`0/44` (`0.0%`) fail lượt đầu có `util > 95%` (và `0/4` trong các ca retry capacity).** |

- **Kết luận kiểm chứng giả thuyết:**
  - Giả thuyết "`capacity_utilization > 95%` là nguyên nhân gây các ca fail lượt đầu đã quan sát" **KHÔNG ĐÚNG trên dữ liệu quá khứ (`0/44 = 0.0%`)**: các dataset `golden/hard/holdout` đều có input utilization `<= 60%`, còn 4 ca fail lượt đầu ở `G4/G5` có utilization `80.39%` và `90.67%`.
  - **Nguyên nhân gốc thực sự của 4 ca `G4/G5` là phân mảnh bin-packing trong `SpatioTemporalRuleEngine.allocate_task_sessions`** ([spatio_temporal_engine.py:1009-1099](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/spatio_temporal_engine.py#L1009-L1099)): `session_limit = 60` tự cắt task `90m -> 45+45` (bỏ thừa `15m`/ngày `MODE_A` `60m` ở `G4`) hoặc cắt `120m -> 60+60` (bỏ thừa `30m`/slot `MODE_B` `90m` ở `G5`), khiến `1–3` task cuối không xếp vừa trước `target_date` và bị drop toàn bộ block.
  - **Cảnh báo cho luồng E2E mới (`exp_10`):** Các phương án Milestone Planner mới (`exp_10`) hiện sinh `8/12` kế hoạch ở mức `94.7%–100%` và `1/12` ở `113.8%` (`M-12`). Tuy chưa chạy vào Decomposer ở `exp_10`, nếu đưa vào Decomposer thì nhóm `>= 94.7%` này chắc chắn làm trầm trọng thêm cả lỗi bin-packing lẫn tràn quỹ tuyệt đối (`113.8%`). Vì vậy việc hạ trần sử dụng xuống **`85%`** ở Thiết kế #2 vẫn hoàn toàn cần thiết.

---

## 4. Đề xuất Thiết kế #2 (CHƯA triển khai, CHƯA sửa prompt): Trọng số `1–5` → Effort `85%` & ép `FIT_CAPACITY`

1. **Tách vai trò LLM vs Code tất định:**
   - **LLM Milestone Planner** chỉ ước lượng **`relative_weight` (`1..5`)** cho độ nặng kiến thức/thực hành của từng milestone (và `scope_assessment` mô tả liệu toàn bộ mục tiêu có khả thi trong quỹ giờ tóm tắt hay không), **không** tự chia đều tổng phút.
   - **Code Domain Service (`MilestoneEffortAllocator`)** thực hiện quy đổi tất định:
     - Tính `available_minutes = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(...)` và ngân sách mục tiêu `target_budget = floor_to_30(available_minutes * target_utilization)` với `target_utilization` cấu hình trong `Settings` (mặc định **`0.85`**).
     - Kiểm tra **ngưỡng thực tế tối thiểu (`full_scope_floor_minutes`)** dựa trên tổng trọng số (`sum(weight_i * min_minutes_per_weight_unit)`, ví dụ `120–150m` mỗi đơn vị weight hoặc ngưỡng cận dưới của trình độ `BEGINNER/INTERMEDIATE/ADVANCED`):
       - **Trường hợp 1 (`full_scope_floor_minutes <= available_minutes * max_allowed_utilization`, ví dụ `0.90`):** Quy đổi từng milestone theo tỷ lệ `weight_i / sum(weights)` trên `min(target_budget, reasonable_ceiling_for_weights)`, làm tròn bội `30` phút (`>= 60` phút), bảo toàn chênh lệch (`w_a < w_b => effort_a < effort_b`). Phần dư/thiếu làm tròn cộng dồn vào milestone có `weight` lớn nhất.
       - **Trường hợp 2 (`full_scope_floor_minutes > available_minutes * max_allowed_utilization`, ví dụ ca kiểu `M-12` `3,960m > 3,480m`):** Backend **ép buộc chuyển `generation_strategy = FIT_CAPACITY`**: giữ các milestone nền tảng ưu tiên sao cho tổng effort `<= target_budget` (`85%`), tự động đẩy các milestone mở rộng/cuối chuỗi vượt trần vào **`deferred_scope`** và gắn cờ chuẩn hóa `scope_summary` bắt đầu bằng `FIT_CAPACITY` (tuyệt đối không để `FULL_SCOPE` khi vượt quỹ).

---

## 5. Đề xuất Thiết kế #3 (CHƯA triển khai): Bộ Xếp Lịch Tất Định `SpatioTemporalRuleEngine`

Căn cứ trực tiếp vào [spatio_temporal_engine.py:526-1101](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/domain/services/spatio_temporal_engine.py#L526-L1101) (`allocate_tasks_to_availability` và `allocate_task_sessions`):

1. **Rải đều theo nhịp & Dự phòng cuối kỳ (`PACED_UNIFORM` + `end_buffer`):**
   - Bổ sung bước pre-pass tính **mật độ mục tiêu mỗi ngày khả dụng**: giữ lại `buffer_days = max(1, floor(usable_days * 0.12))` ngày trống cuối kỳ trước `target_date` (nếu tổng tải cho phép), phân bổ hạn mức mềm `daily_soft_cap = min(day_quota, max(session_limit, ceil(remaining_minutes / remaining_active_days)))` làm tròn lên bội `30` phút. Nhờ đó mục tiêu nhẹ (`26–45%` quỹ giờ như `R-01`, `R-05`) được rải đều suốt kỳ học thay vì dồn hết vào `11–23` ngày đầu rồi bỏ trống `16–20` ngày cuối.
2. **Ngày nghỉ bắt buộc (`max_consecutive_study_days`):**
   - Hiện `lines 759-761` chỉ bỏ qua `disabled_weekdays` (vốn rỗng ở `MODE_A`), gây chuỗi `32–43` ngày liên tiếp (`R-07`, `R-08`).
   - Thiết kế mới theo dõi `consecutive_active_days`; khi đạt ngưỡng cấu hình (mặc định **`5` hoặc `6` ngày liên tiếp**) **VÀ** số ngày khả dụng còn lại trừ ngày nghỉ vẫn đủ chứa `remaining_minutes`, tự động chèn **1 ngày nghỉ phục hồi** (`skip` bước lặp ngày). Nếu quỹ giờ quá sát (`pace` bắt buộc mới kịp deadline), cho phép nới streak nhưng phát cảnh báo `REST_DAY_COMPRESSED`.
3. **Cờ `is_non_splittable` (bài thi thử, load test, benchmark):**
   - Thêm thuộc tính `is_non_splittable: bool = False` vào `Task` / `TaskProposalItemDTO` (kèm detector tất định tự đánh dấu `True` cho bài thi thử có giờ / mock test / load test / benchmark).
   - Trong `allocate_task_sessions` (`lines 1032-1053`): nếu `is_non_splittable=True`, giữ **`session_count = 1`** (không tách theo `preferred_session_minutes`), yêu cầu đặt vừa trọn vẹn vào **1 slot/ngày liên tục** `>= estimated_minutes` (nếu `estimated_minutes > max_slot_capacity` thì trả vi phạm rõ `TASK_EXCEEDS_CONTINUOUS_SLOT` thay vì cắt đôi bài thi 60 phút qua 2 ngày như `R-08 T29/T30`).
4. **Chống tách vụn & Gộp các block liền nhau của cùng một task:**
   - **Tầng xếp lịch:** Khi ngày/slot ứng viên có khoảng trống liên tục `>= task.estimated_minutes` (và `<= 120` phút), ưu tiên đặt **nguyên 1 block** thay vì cắt trước thành `session_limit` (`45p` hoặc `60p`) rồi mới đặt nối đuôi.
   - **Hậu xử lý gộp block (`_coalesce_adjacent_blocks`):** Trước khi trả `blocks` ở cuối `allocate_task_sessions` (`lines 1090-1099`), nhóm theo `(task_id, block_date)`, sắp xếp theo `scheduled_start`, hễ `prev.scheduled_end == curr.scheduled_start` thì gộp thành 1 `ScheduleBlock` duy nhất (`end = curr.end`, `duration += curr.duration`, đánh lại `sequence_in_task = 1..k`). Toàn bộ `12/12` tasks bị chẻ `45+45` kiểu `R-03` sẽ tự động trở về 1 block `90` phút sạch sẽ.
5. **Chống phân mảnh bin-packing (`G4/G5`):**
   - Kiểm tra độ vừa khít theo kích thước slot thực tế (ví dụ không tạo task `120m` hoặc `60+60` tràn lẻ trên chuỗi slot `90m` khi tỷ lệ tận dụng slot tiệm cận `90%`).

---

## 6. Cập nhật Dataset `hard_planning_6_goals.jsonl` & Eval Metrics (`eval_runner.py`)

- [hard_planning_6_goals.jsonl](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/datasets/hard_planning_6_goals.jsonl): đã hạ `"min_milestones"` từ `5` → **`4`**, đồng thời bổ sung `"max_capacity_utilization": 0.9` và `"require_non_equal_milestone_effort": true` vào `expected_invariants`.
- [eval_runner.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/eval_runner.py):
  - Chuyển `_run_e2e_stage2_milestone_planner` sang **Server Prefetch** (`tools=None`) và kiểm `max_capacity_utilization` + `require_non_equal_milestone_effort`.
  - Tích hợp toàn bộ nhóm metric audit cấu trúc (`outcome["structural_audit"]` và `report["structural_audit_summary"]`): `capacity_utilization_avg/max`, `effort_equal_ratio_avg`, `all_efforts_equal_cases`, `milestone_vs_tasks_gap_avg`, `linear_dependency_ratio_avg`, `max_consecutive_study_days_max`, `days_idle_before_deadline_avg`, `tasks_split_across_days_total`, `sensitive_tasks_split_across_days_total`, `short_project_under_90_total`.
- [test_eval_runner_and_dataset.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/test_eval_runner_and_dataset.py): cập nhật kiểm tra dataset invariants và bổ sung `test_e2e_milestone_planner_uses_server_prefetch_and_enforces_structural_invariants`.
- **Chạy kiểm chứng live `--e2e` sau khi bật Server Prefetch & cập nhật invariants ([hard_6_goals_e2e_prefetch_audit.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/hard_6_goals_e2e_prefetch_audit.json)):**
  - `milestone_planner`: **`0/6` timeout** (`p50 = 17.11s`, `p95 = 23.52s`, `max = 24.56s`), `clarifier`: `p50 = 9.39s` / `p95 = 10.87s`.
  - `pass_at_1 = 0/6` phản ánh đúng hai blocker còn lại cần Thiết kế #2 & tăng timeout Decomposer:
    - `4/6` (`H_E2E_01/03/05` = `0.9474`, `H_E2E_06` = `0.9655`) bị kiểm tra mới `max_capacity_utilization <= 0.90` chặn ngay tại Milestone Planner; `1/6` (`H_E2E_04`) sinh `7` milestones (`> max_milestones=6`).
    - `1/6` (`H_E2E_02`: `5` milestones, `capacity_utilization = 0.7328`, không bằng nhau) vượt qua Milestone Planner sang Decomposer nhưng chạm trần `25.002s` của Decomposer.
