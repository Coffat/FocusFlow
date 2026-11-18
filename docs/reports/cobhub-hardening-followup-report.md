# Báo Cáo Tiếp Nối Hardening AI Pipeline (`cobhub`, Container Python 3.12, E2E Eval & Judge Under Load)

- **Ngày thực hiện:** `2026-11-16`
- **Ràng buộc tuân thủ:** Giữ nguyên **100%** nội dung 12 production prompts (`roadmap_skills.py`, `prompts.py`, `untrusted_context.py`, `prompts.lock`), không sửa `.env` thật, chưa triển khai thay đổi Judge dưới tải (chờ chọn phương án ở Mục 8).

---

## Tóm tắt kết quả 9 hạng mục

### 1. Chọn model tường minh theo stage, bỏ fallback ngầm `LLM_MODEL` & mở rộng probe `/v1beta/models`
- **Nguyên nhân gốc ở Holdout Run 3 (`404` với `gemini-3.5-flash`):**
  - Trong [litellm_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py), `_resolve_candidate_models()` ở mode `model_suffix` luôn tự chèn `default_model` (`LLM_MODEL`) vào danh sách `candidates` ngay cả khi `LLM_FALLBACK_MODELS=""`. Khi `.env` đặt `LLM_MODEL=gemini-3.5-flash` (không tồn tại trong `/v1beta/models` của `cobhub`) và `tier_model` gặp lỗi gateway tạm thời, adapter tự fallback ngầm sang `LLM_MODEL` gây `404 NOT_FOUND`. Ngoài ra, `_normalize_thinking_level` trước đây âm thầm mặc định `None -> "MEDIUM"`, và các nhánh thiếu `LLM_MODEL_{LOW,MEDIUM,HIGH}` tự rơi về `LLM_MODEL` hoặc `"gemini-3.8-flash-medium"`.
- **Thay đổi đã thực hiện:**
  - [execution_manager.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/application/harness/execution_manager.py) & [models.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/application/harness/models.py): `AIExecutionManager.execute()` bắt buộc có `thinking_level` tường minh (hoặc lấy từ `prompt_template.thinking_level`), raise `ValueError("AI_MODEL_SELECTION_ERROR: ...")` nếu thiếu.
  - [orchestrator.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/validation_gate/orchestrator.py): truyền tường minh `thinking_level` (fallback tới `TASK_DECOMPOSER_SKILL.thinking_level` nếu trống).
  - [litellm_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py): xóa bỏ chèn ngầm `default_model` vào `candidates`; raise `RuntimeError("AI_PROVIDER_NOT_CONFIGURED: ...")` khi thiếu model của tier (`llm_model_low`/`_medium`/`_high` ở `model_suffix`, hoặc `llm_model` ở `param`/non-Gemini) và raise `ValueError` nếu thiếu `thinking_level` trên Gemini `model_suffix`. Khi `LLM_FALLBACK_MODELS=""`, `candidates` chỉ chứa đúng 1 model tường minh của stage.
  - Mở rộng `probe_cobhub_capabilities()` & `CobhubCapabilityProbeResult`: gọi `GET {resolved_base_url}/v1beta/models`, kiểm tra toàn bộ `LLM_MODEL*` (`llm_model`, `llm_model_low`, `llm_model_medium`, `llm_model_high`, và `llm_fallback_models`), gắn cảnh báo `configured_models_missing_from_gateway` cùng danh sách `missing_gateway_models` vào log `cobhub_capability_mismatch` và `/api/health?probe_ai=true` nếu thiếu.

### 2. Sửa `test_phase_c_google_genai_proxy_and_three_tier_routing` & chạy `pytest` trong container Python 3.12
- Sửa [test_phase_b_c_d_improvements.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_phase_b_c_d_improvements.py) (`test_phase_c_google_genai_proxy_and_three_tier_routing`) và [test_prompt_sanitizer_and_llm_port.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/shared_kernel/test_prompt_sanitizer_and_llm_port.py) (`test_probe_cobhub_capabilities_checks_all_configured_models_against_v1beta_models`) để mock `os.path.exists("/.dockerenv") -> False` và xóa `RUNNING_IN_DOCKER` khi kiểm tra URL `127.0.0.1:8045`, đồng thời kiểm chứng tường minh case `RUNNING_IN_DOCKER="1"` rewrite sang `host.docker.internal:8045`.
- **Kết quả chạy lại sau chỉnh sửa cuối trong container `Python 3.12.12` (`focusflow-backend:latest`):**
  - `ruff check .` → `All checks passed!`
  - `ruff format --check .` → `351 files already formatted`
  - `mypy --strict src` → `Success: no issues found in 271 source files`
  - `lint-imports` → `Contracts: 5 kept, 0 broken.`
  - `python scripts/update_prompts_lock.py --check` → `prompts.lock matches live PromptRegistry (12 prompts).`
  - `pytest -q -m "not live_cobhub and not live_embedding"` → **`535 passed, 3 deselected` (`0 failed`, `67.13s`)**.

### 3. Smoke thật từ container Python 3.12 tới `cobhub` qua `host.docker.internal:8045`
- **Địa chỉ lắng nghe trên máy host (`lsof -nP -iTCP:8045 -sTCP:LISTEN`):**
  - Process `cofhub` (PID `34316`) đang lắng nghe trên **`127.0.0.1:8045`** (IPv4 loopback).
- **Kết nối từ trong container `focusflow-backend:latest` (`Python 3.12.12`, `/.dockerenv = True`, `--add-host=host.docker.internal:host-gateway`):**
  - **Kết nối được bình thường** nhờ Docker Desktop chuyển tiếp `host.docker.internal:8045` tới loopback host (`configured_llm_base_url=http://127.0.0.1:8045` → `resolved_base_url=http://host.docker.internal:8045`).
  - `GET http://host.docker.internal:8045/v1beta/models` → HTTP **`200 OK`**, trả về **`26` models** (`gemini-3.8-flash`, `gemini-3.8-flash-low`, `gemini-3.8-flash-medium`, `gemini-3.8-flash-high`, `gemini-3.5-flash-lite`, ... — không có `gemini-3.5-flash`).
  - `probe_cobhub_capabilities(force=True)` → `status="ok"`, `probe_succeeded=True`, `mismatches=[]`, `missing_gateway_models=[]`.
  - `LiteLLMAdapter.generate_structured(..., thinking_level="LOW")` → thành công (`{'ok': True}`, `actual_model_id=gemini-3.8-flash-low`, `thinking_tokens=16`).

### 4. Phân biệt rõ Pass@1 lượt đầu vs sau retry (`-low` vs `-medium` trong `exp_09`)
- Đã cập nhật Mục `8.3` trong [cobhub-hardening-report.md](file:///Users/vuthang/Documents/FocusFlow/docs/reports/cobhub-hardening-report.md) dựa trên dữ liệu gốc [exp_09_judge_and_quality_ab.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_09_judge_and_quality_ab.json):
  - **Pass@1 lượt đầu (`attempts_used == 1`):** `-low` đạt **`3/5` (`60.0%`)** vs `-medium` đạt **`5/5` (`100.0%`)**.
  - **Kết quả sau retry (`attempts_used <= 2`):** `-low` đạt **`5/5` (`100.0%`)** vs `-medium` đạt **`5/5` (`100.0%`)**.
  - **Hai mục tiêu làm `-low` fail ở lượt đầu:**
    1. **`G4_BEGINNER_IELTS_WRITING`**: Fail lượt 1 với `CAPACITY_EXCEEDED_BEFORE_TARGET_DATE` + `SCHEDULE_BLOCK_EFFORT_MISMATCH` (`T26`), tự sửa đạt ở lượt 2.
    2. **`G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT`**: Fail lượt 1 với `CAPACITY_EXCEEDED_BEFORE_TARGET_DATE` + `SCHEDULE_BLOCK_EFFORT_MISMATCH` (`T25`, `T26`), tự sửa đạt ở lượt 2.

### 5. Eval 6 mục tiêu khó (5–6 milestone, nhiều ràng buộc) & luồng E2E `clarifier -> milestone planner -> decomposer`
- Đã tạo dataset [hard_planning_6_goals.jsonl](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/datasets/hard_planning_6_goals.jsonl) (6 mục tiêu khó đa ngành, `MODE_B` nhiều slot + `disabled_weekdays`, `min_milestones: 5`, `max_milestones: 6`, `min_tasks: 10`, kèm `clarification_answers`) và bổ sung chế độ `--e2e` vào [eval_runner.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/eval_runner.py).
- **Kết quả đo live (`--e2e`, `hard_6_goals_e2e_eval.json`):**
  - `clarifier` (`count=6`): **`p50 = 9,956.06 ms` | `p95 = 11,691.71 ms`** (`max = 12,091.63 ms`, `6/6` đạt dưới budget `15.0s`).
  - `milestone_planner` (`count=6`): **`p50 = 40,452.34 ms` | `p95 = 50,005.14 ms`** (`2/6` `TIMEOUT` tại `50.0s` ở `H_E2E_02`, `H_E2E_04`; `4/6` hoàn tất trong `36.79s–41.01s` nhưng sinh `4` milestones thay vì `>= 5` nên vướng `VALIDATION_GATE` — trong lần chạy trước đó khi `H_E2E_06` qua được Milestone Planner, Decomposer chạm `25,002.50 ms` `TIMEOUT`).
  - `weekly` (`count=6`): `p50 = 6,248.26 ms` | `p95 = 7,081.29 ms` (`faithfulness = 0.9653`).
  - `e2e_total` (`count=6`): **`p50 = 50,376.13 ms` | `p95 = 61,696.30 ms`** | `pass_at_1 = 0.0 (0/6)`, `pass_with_judge_verdict = 0.0 (0/6)`.
- **Kết quả đối chứng `Decomposer + Critics + Judge` trên 5 milestones của chính 6 mục tiêu khó này (`hard_6_goals_decomposer_only_eval.json`):**
  - `pass_at_1 = 1.0 (6/6)` | `pass_with_judge_verdict = 1.0 (6/6)` (`pedagogical_score_avg = 94.0`).
  - `decomposer`: **`p50 = 21,089.19 ms` | `p95 = 23,897.75 ms`** (`max = 24,326.27 ms`, sát trần `25.0s`).
  - `critics_judge_parallel`: **`p50 = 4,520.93 ms` | `p95 = 6,501.56 ms`**.
  - **Nhận xét kỹ thuật (chưa sửa prompt):** Với bài toán khó 5–6 milestones, bottleneck E2E nằm ở `MILESTONE_PLANNER` (nhiều vòng tool call khiến `p50 = 40.5–45.2s`, `p95 = 49.0–50.0s` và mặc định hay chọn `4` milestones) và trần `25.0s` của `TASK_DECOMPOSER` (`p95 = 23.90s`).

### 6. Metric `pass_with_judge_verdict` (`pass@1` lượt đầu ĐỒNG THỜI `judge_status == "PASSED"`)
Đã tích hợp `pass_with_judge_verdict` và `pass_with_judge_verdict_count` vào [eval_runner.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/eval_runner.py) và `validate_eval_report_totals`. Đối chiếu trên toàn bộ các lần chạy:

| Artifact / Lần chạy | `total_runs` | `pass_at_1` | `pass_with_judge_verdict` | `judge_passed` / `review_pending` |
|---|---:|---:|---:|---:|
| `baseline_normalized_metrics.json` | 18 | `0.0000` (`0/18`) | `0.0000` (`0/18`) | `0` / `0` (`18` skipped) |
| `eval_old_config_new_runner.json` | 18 | `0.4444` (`8/18`) | `0.1667` (`3/18`) | `3` / `5` |
| `group7_eval_run_1..3.json` | 18 × 3 | `1.0000` (`18/18`) | `1.0000` (`18/18`) | `18` / `0` |
| `group7_eval_evening.json` | 18 | `1.0000` (`18/18`) | `0.9444` (`17/18`) | `17` / `1` |
| `holdout_eval_run_1.json` & `run_2.json` | 12 × 2 | `1.0000` (`12/12`) | `1.0000` (`12/12`) | `12` / `0` |
| `holdout_eval_run_3.json` | 12 | `1.0000` (`12/12`) | `0.9167` (`11/12`) | `11` / `1` |
| `concurrency_5_eval.json` | 18 | `1.0000` (`18/18`) | `0.8333` (`15/18`) | `15` / `3` |
| `concurrency_10_eval.json` | 18 | `1.0000` (`18/18`) | `0.9444` (`17/18`) | `17` / `1` |
| `golden_18_goals_post_explicit_routing.json` *(mới)* | 18 | **`1.0000` (`18/18`)** | **`1.0000` (`18/18`)** | `18` / `0` |
| Scheduled run `20261116_231643` (`18` goals) *(mới)* | 18 | `0.9444` (`17/18`) | `0.9444` (`17/18`) | `17` / `0` (`1` timeout Decomposer) |
| `hard_6_goals_decomposer_only_eval.json` *(mới)* | 6 | **`1.0000` (`6/6`)** | **`1.0000` (`6/6`)** | `6` / `0` |
| `hard_6_goals_e2e_eval.json` *(mới)* | 6 | `0.0000` (`0/6`) | `0.0000` (`0/6`) | `0` / `0` (`6` skipped) |

### 7. Bộ chấm mù 10 lộ trình
- Sinh qua [build_blind_review_pack.py](file:///Users/vuthang/Documents/FocusFlow/scripts/experiments/build_blind_review_pack.py) từ 10 lộ trình của `exp_09`:
  - Tài liệu chấm mù (đã ẩn toàn bộ `-low`/`-medium`, `model_id`, `thinking_tokens`, `attempts_used`, điểm Judge): [blind-review-10-roadmaps.md](file:///Users/vuthang/Documents/FocusFlow/docs/reports/blind-review-10-roadmaps.md) (nhãn `R-01`..`R-10`, bảng chấm 1–5 theo 5 tiêu chí `C1..C5`).
  - File key đối chiếu tách riêng: [blind_review_10_roadmaps_key.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/blind_review_10_roadmaps_key.json).

### 8. Đề xuất phương án cho Judge dưới tải (CHƯA TRIỂN KHAI — chờ lựa chọn)
- **Số đo thực tế tại `concurrency=5` & `concurrency=10` (`tier3_judge_timeout_seconds=8.0s`):**
  - `concurrency=1` (tối): `critics_judge_parallel` `p50=3.41–3.99s`, `p95=5.11–7.17s`, Judge timeout `0%`.
  - `concurrency=5` ([concurrency_5_eval.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/concurrency_5_eval.json)): `decomposer p95=11.84s` (`max=14.46s`), `critics_judge_parallel` **`p95=10.61s` (`max=14.84s`)**, Judge **`3/18` (`16.67%`) `TIMEOUT` -> `REVIEW_PENDING`**, khiến `pass_with_judge_verdict` tụt xuống **`0.8333` (`15/18`)** dù `pass_at_1 = 1.0`.
  - `concurrency=10` ([concurrency_10_eval.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/concurrency_10_eval.json)): `decomposer p95=14.84s` (`max=15.07s`), `critics_judge_parallel` **`p95=11.93s` (`max=11.93s`)**, Judge **`1/18` (`5.56%`) `TIMEOUT` -> `REVIEW_PENDING`**, `pass_with_judge_verdict = 0.9444` (`17/18`).

- **So sánh 3 phương án kiến trúc đề xuất:**

| Tiêu chí | Phương án A: Timeout động trong pipeline `55s` | Phương án B: Chạy nền Taskiq + `REVIEW_PENDING` UI | Phương án C: Hybrid (Động `12s` + Fallback Taskiq nền) *(Khuyến nghị)* |
|---|---|---|---|
| **Cơ chế** | Cấp Judge `min(12.0..15.0s, max(ai_min_judge_remaining_seconds, remaining_pipeline_budget))` bên trong nhánh `asyncio.gather` cùng Dual Critics. | Giữ `8.0s` (hoặc `5.0s`) trong luồng SSE; nếu quá hạn, trả ngay `DRAFT` với `judge_status="REVIEW_PENDING"`, hiển thị badge trên UI, đồng thời enqueue Taskiq job chấm lại và cập nhật DB/thông báo SSE/polling. | Bước 1 dùng timeout động tối đa `12.0s` trong luồng SSE (nhờ Decomposer `p95 <= 14.8s` tại `c=10`, dư `~40s` trong budget `55s`). Bước 2 nếu vẫn `REVIEW_PENDING` (spike >12s hoặc `GATEWAY_ERROR`), tự enqueue Taskiq job hậu kiểm cập nhật `PASSED`/`NEEDS_REVIEW` trước khi user bấm Apply. |
| **Ảnh hưởng `pass_with_judge_verdict`** | Kéo `critics_judge_parallel` về `<= 12.0–15.0s` → xử lý gần hết spike `c=5/10` (`p95=10.61–11.93s`, `max=14.84s`) ngay trong request đầu. | Request đầu vẫn ra `REVIEW_PENDING` với xác suất `5.6–16.7%` dưới tải `c=5/10`, cần user đợi thêm hoặc xác nhận cảnh báo. | Giảm tỷ lệ `REVIEW_PENDING` ngay lúc tạo xuống sát `0%` ở `c=5/10`, đồng thời không bao giờ bỏ kẹt trạng thái `REVIEW_PENDING` mãi mãi nếu gateway chập chờn. |
| **Rủi ro & Chi phí** | Thay đổi nhỏ (`config.py` + `orchestrator.py` + `tier3_judge.py`), không thêm độ phức tạp queue/UI, nhưng vẫn có thể timeout nếu tail spike `> 15s` hoặc Decomposer retry lâu (`~30s`). | Cần Taskiq task mới + idempotency + UI polling/refresh trạng thái `ScheduleProposal` + xử lý race condition nếu user bấm `Apply` trước khi background job xong. | Phức tạp trung bình (cần Taskiq job + cập nhật proposal), đổi lại tối ưu cả UX lẫn độ tin cậy dưới tải cao và tuân thủ trần `55s` SRS. |

### 9. Lịch chạy eval hằng ngày 7 ngày theo stage và theo giờ
- Đã tạo [run_scheduled_eval.py](file:///Users/vuthang/Documents/FocusFlow/scripts/run_scheduled_eval.py) và [install_eval_schedule.sh](file:///Users/vuthang/Documents/FocusFlow/scripts/install_eval_schedule.sh).
- Đã cài đặt và nạp agent `com.focusflow.eval7d` vào `launchd` (`~/Library/LaunchAgents/com.focusflow.eval7d.plist`) chạy 3 khung giờ hằng ngày (`09:00`, `14:00`, `21:00` local time) trong cửa sổ `7` ngày (`start_date = 2026-11-16`), tự dừng sau 7 ngày.
- Đã chạy thử 1 lượt live thực tế (`20261116_231643_golden_planning_18_goals.json`), ghi nhận kết quả theo stage & giờ (`23`) vào [hourly_stage_metrics.csv](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/scheduled_eval_7d/hourly_stage_metrics.csv) và [hourly_stage_metrics.jsonl](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/scheduled_eval_7d/hourly_stage_metrics.jsonl).

---

## Phần B — Làm rõ, Đo sâu & Chuẩn bị quyết định (`2026-11-17`, 9 hạng mục tiếp theo)

> **Ràng buộc tuân thủ:** Tiếp tục **giữ nguyên 100%** nội dung prompt production (`roadmap_skills.py`, `prompts.py`, `untrusted_context.py`, `prompts.lock`), chưa chuyển Milestone Planner production sang prefetch, và chỉ triển khai **Phương án A** cho Judge (`12.0s` dynamic timeout trong `gather`, chưa làm B/C).

### B1. Tách rõ E2E `0/6` là Blocker, `decomposer-only` (`6/6`) không đại diện & chú thích cắt cụt `p95 = 50.005s`
- **Kết quả End-to-End 6 mục tiêu khó (`hard_6_goals_e2e_eval.json`, `--e2e`):** `pass_at_1 = 0.0 (0/6)` và `pass_with_judge_verdict = 0.0 (0/6)` → **đây là BLOCKER thực tế cho luồng E2E 5–6 milestone nhiều ràng buộc**.
- **`decomposer-only` (`hard_6_goals_decomposer_only_eval.json`) = `6/6` KHÔNG đại diện cho E2E:** Chạy này bỏ qua `clarifier` và `milestone_planner`, dùng thẳng 5 milestones gõ sẵn trong fixture [hard_planning_6_goals.jsonl](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/datasets/hard_planning_6_goals.jsonl). Ở chạy E2E thật, không có ca nào vượt qua `milestone_planner` (`decomposer.count = 0`).
- **Số đo `milestone_planner p95 = 50.005s` bị cắt cụt bởi timeout (right-censored):** Trên 6 mục tiêu khó E2E (`count = 6`, `p50 = 40.452s`), **`2/6` ca chạm đúng trần `50.0s`** (`ai_milestone_planner_timeout_seconds = 50.0`, đo được `50.005s` và `max = 50.005s`), nên phân vị `p95 = 50.005s` là giá trị bị cắt tại timeout chứ không phải độ trễ hoàn tất thực của mô hình. `4/6` ca còn lại xong dưới `50s` nhưng bị `VALIDATION_GATE` vì sinh `4` milestones thay vì `>= 5`.

### B2. Xác minh nguồn gốc `min_milestones: 5` & Mở rộng Bộ chấm mù (thêm Milestone Planner 6 mục tiêu khó)
- **`min_milestones: 5` CHỈ là kỳ vọng của dataset/eval harness, KHÔNG phải quy tắc của gate production:**
  - **Kỳ vọng dataset & kiểm tra tại eval:** Khai báo `"min_milestones": 5` trong [hard_planning_6_goals.jsonl:1-6](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/datasets/hard_planning_6_goals.jsonl#L1-L6) và chỉ bị chặn trong [eval_runner.py:1097-1104](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/eval_runner.py#L1097-L1104) (`if min_ms is not None and len(sorted_items) < int(min_ms): raise ProposalValidationGateError(...)`).
  - **Gate production:** [milestone_use_cases.py:350-352](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/milestone_use_cases.py#L350-L352) gọi `validate_ai_milestones_tier1` ([tier1_schema.py:30-34](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/validation_gate/tier1_schema.py#L30-L34)) → `validate_adaptive_milestones` ([learning_quality.py:121-179](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/learning_quality.py#L121-L179)). Hàm này tại [learning_quality.py:125-135](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/learning_quality.py#L125-L135) chỉ kiểm tối thiểu `>= 1` milestone (`EMPTY_MILESTONE_LIST`), hoàn toàn không có ngưỡng `>= 5`. `MILESTONE_PLANNER_SKILL` ([roadmap_skills.py:88-116](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/roadmap_skills.py#L88-L116)) cũng không quy định số milestone tối thiểu.
- **Bộ chấm mù mở rộng cho đầu ra Milestone Planner (`M-01..M-12`):**
  - Sinh qua [build_blind_review_pack.py](file:///Users/vuthang/Documents/FocusFlow/scripts/experiments/build_blind_review_pack.py) từ toàn bộ 6 mục tiêu khó trong [exp_10_planner_tool_rounds_ab.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_10_planner_tool_rounds_ab.json) (gồm cả các ca ra `4` milestones lẫn `6–7` milestones):
    - Tài liệu chấm mù 12 phương án Milestone (`M-01..M-12`, ẩn toàn bộ arm tool-calling vs server-prefetch, độ trễ, số vòng): [blind-review-hard-6-milestones.md](file:///Users/vuthang/Documents/FocusFlow/docs/reports/blind-review-hard-6-milestones.md)
    - File key đối chiếu: [blind_review_hard_6_milestones_key.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/blind_review_hard_6_milestones_key.json)
    - Bộ 10 lộ trình đầy đủ (`R-01..R-10`): [blind-review-10-roadmaps.md](file:///Users/vuthang/Documents/FocusFlow/docs/reports/blind-review-10-roadmaps.md)

### B3. Đo từng vòng Tool của Milestone Planner & Thử nghiệm A/B Server Prefetch (`exp_10`)
- Chạy thí nghiệm đo lường [exp_10_planner_tool_rounds_ab.py](file:///Users/vuthang/Documents/FocusFlow/scripts/experiments/exp_10_planner_tool_rounds_ab.py) trên 6 mục tiêu khó (`timeout = 120s`, `thinking_level = LOW`), lưu tại [exp_10_planner_tool_rounds_ab.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_10_planner_tool_rounds_ab.json) (**chưa thay đổi production**):

| Chỉ số (`6` mục tiêu khó) | Arm (a): Tool-calling hiện tại | Arm (b): Server Prefetch (`tools=None`) | So sánh (b vs a) |
|---|---:|---:|---|
| Hợp lệ Tier 1 (`validate_ai_milestones_tier1`) | `6/6` | `6/6` | Ngang bằng |
| Số vòng gọi LLM (`total_rounds`) | `p50 = 3.0`, `max = 4.0` (`p95 = 3.75`) | **`1`** (single turn) | Giảm `2–3` round-trips |
| Số lần gọi tool thực tế | `p50 = 1.0`, `max = 2.0` (`search_learning_concepts`: `7` lần) | Prefetch in-memory trước khi gọi LLM | Không cần tool-calling loop |
| Thời gian thực thi tool/prefetch tại server | `0.15–0.67 ms`/lần | `p50 = 1.79 ms`, `max = 2.43 ms` | Gần như `0 ms` |
| Thời gian LLM các vòng `tool_round` | `p50 = 7,546.30 ms`, `p95 = 26,538.38 ms`, `max = 27,366.74 ms` (`13` turns) | `0 ms` | Cắt bỏ hoàn toàn |
| Thời gian LLM vòng `final_json` / turn duy nhất | `p50 = 15,743.87 ms`, `p95 = 20,535.20 ms`, `max = 21,243.63 ms` | `p50 = 16,175.55 ms`, `p95 = 17,774.96 ms`, `max = 17,827.79 ms` | Tương đương |
| **Tổng độ trễ End-to-End (`wall_ms` / `total_ms`)** | **`p50 = 36,278.10 ms` \| `p95 = 50,440.21 ms`** (`max = 51,562.93 ms`) | **`p50 = 16,180.56 ms` \| `p95 = 17,780.05 ms`** (`max = 17,832.72 ms`) | **Nhanh hơn `2.242x` ở `p50`**, **`-64.7%` ở `p95`** |
| Tổng tokens (Prompt / Output) | `56,044` / `26,950` | `30,595` (`-45.4%`) / `12,045` (`-55.3%`) | Tiết kiệm >50% output tokens |

- **Phát hiện nguyên nhân gốc độ trễ `tool_round` (chưa đụng prompt):** Thực thi tool `search_learning_concepts` trên server chỉ mất **`0.15–0.67 ms`**, nhưng vòng lặp trong `LiteLLMAdapter` tạo ra một lượt lãng phí rất nặng:
  - *Round 1 (`tool_round`):* LLM mất `1.73–7.55s` chỉ để xin gọi `search_learning_concepts` (`~38–45` output tokens).
  - *Round 2 (`tool_round`):* Sau khi nhận kết quả tool, LLM mất **`13.56–27.37s`** sinh **`1,818–3,520` output tokens** rồi trả `finish_reason=STOP` với `function_calls_requested=[]` — phần output này bị vòng `while` bỏ qua để chuyển sang *Round 3 (`final_json`)* ép structured schema (lại mất **`12.02–21.24s`**, sinh lại `1,612–2,498` tokens). Riêng `H_E2E_05` còn gọi `search_learning_concepts` ở cả Round 1 & Round 2 (`4` rounds).
- **Phân bổ số milestones:** Cả Arm (a) và Arm (b) đều ra số milestones lần lượt `[4, 7, 4, 7, 4, 6]` và `[4, 6, 4, 7, 4, 6]`, tức vẫn có 3 ca tight-4-tuần ra `4` milestones ở cả hai arm.

### B4. Ngân sách tính sẵn cho Decomposer (`precomputed_schedule_budget`) & Đo Trước/Sau (`exp_11`)
- **Đã triển khai vào ngữ cảnh:** [RoadmapContextBuilder.compute_schedule_budget](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/roadmap_context_builder.py) tính sẵn từ `availability`, `milestones`, `start_date`, `target_date`, `opt_session_minutes` các trường `max_available_minutes_until_target_date`, `recommended_task_count_range` (`min_tasks`, `max_tasks`), `recommended_minutes_per_task`, `capacity_fit_ratio`, `fits_milestone_effort` và gắn vào `[SYSTEM_DERIVED_FACTS]` của [proposal_generation_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/proposal_generation_use_cases.py) (không sửa nội dung prompt trong `roadmap_skills.py`/`prompts.lock`).
- **Kết quả đo A/B thực tế ([exp_11_decomposer_budget_ab.py](file:///Users/vuthang/Documents/FocusFlow/scripts/experiments/exp_11_decomposer_budget_ab.py) → [exp_11_decomposer_budget_ab.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_11_decomposer_budget_ab.json)):**

| Tập kiểm thử / Cấu hình | Arm | Attempt-1 Pass@1 | Final Pass | Retry Rate | Latency `p50` / `p95` / `max` | Ghi chú vi phạm lượt 1 |
|---|---|---:|---:|---:|---|---|
| **G4 & G5** (`120s`, `tools=True` giống `exp_09`) | `before_no_budget` | `1/2` (`50%`: G4 pass, G5 fail) | `2/2` (`100%`) | `50%` | `102.78s` / `134.43s` / `137.95s` | G5: `CAPACITY_EXCEEDED_BEFORE_TARGET_DATE` (`2040 <= 2250m` nhưng overflow slot rời rạc `T31–T33`) |
| **G4 & G5** (`120s`, `tools=True` giống `exp_09`) | `after_with_budget` | `1/2` (`50%`: G4 pass, G5 fail) | `2/2` (`100%`) | `50%` | `105.15s` / `136.81s` / `140.33s` | G5 giảm tổng phút dự kiến (`2040 -> 1980m`), vẫn tràn 3 task cuối do đóng gói vào slot `MODE_B` (60/120p vào slot 90p) |
| **6 Hard Goals** (`25.0s` trần hiện tại, `tools=False`) | `before_no_budget` | `4/6` (`66.67%`) | `4/6` (`66.67%`) | `0%` | `22.82s` / `25.01s` / `25.01s` | `2/6` `TimeoutError` (`H_E2E_02` `25.01s`, `H_E2E_04` `25.01s`) |
| **6 Hard Goals** (`25.0s` trần hiện tại, `tools=False`) | **`after_with_budget`** | **`6/6` (`100.0%`)** | **`6/6` (`100.0%`)** | `0%` | **`21.77s` / `22.51s` / `22.54s`** | **0 timeout, giảm `-1.05s p50` / `-2.50s p95`, rút gọn xuống dưới trần `25s`** |
| **6 Hard Goals** (`40.0s`, `tools=False`) | `before_no_budget` | `6/6` (`100.0%`) | `6/6` (`100.0%`) | `0%` | `23.50s` / `24.56s` / `24.67s` | Đều đạt 100% ở ngưỡng `40s` |
| **6 Hard Goals** (`40.0s`, `tools=False`) | **`after_with_budget`** | **`6/6` (`100.0%`)** | **`6/6` (`100.0%`)** | `0%` | **`22.14s` / `23.44s` / `23.59s`** | **Giảm `-1.36s p50`, `-1.12s p95`, `-1.50s mean`** |

- **Nhận xét kỹ thuật:** Với 6 mục tiêu khó (`tools=False`), `precomputed_schedule_budget` loại bỏ hoàn toàn tình trạng chạm ngưỡng `25.0s` (`6/6` pass ở lượt đầu thay vì `4/6`), giảm `p95` từ `24.56–25.01s` xuống `22.51–23.44s`. Tuy nhiên, trên ca nhiều task dài 4–6 tuần (`G5` `MODE_B`, ~30–33 tasks, cộng thêm overhead gọi tool), con số tổng phút chưa đủ chống tràn biên các slot 90 phút nếu LLM chọn task 60/120 phút không khớp bội số slot.

### B5. Đề xuất cấu hình Timeout Decomposer (`35–40s`, retry chỉ cho lỗi nhanh) & Bảng ngân sách theo bước cho CẢ HAI cách hiểu trần `55s`

- **Cơ sở từ SRS & code hiện tại:** [srs-v1.3.md:1788-1790](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.3.md#L1788-L1790) (`NFR-PERF-001`) quy định hiển thị `<= 60s` và **Hard Timeout backend ở giây `55`**, đồng thời `EVAL-07` ([srs-v1.3.md:1880](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.3.md#L1880)) yêu cầu **P95 `<= 35s`**, max `< 55s`. Trong code hiện tại ([config.py:86-101](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/config.py#L86-L101), [clarification_use_cases.py:1061](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/clarification_use_cases.py#L1061), [milestone_use_cases.py:271-290](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/milestone_use_cases.py#L271-L290), [orchestrator.py:485-566](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/validation_gate/orchestrator.py#L485-L566)), 3 pha `Clarifier`, `Milestone Planner`, và `Decomposer + Critics/Judge` chạy ở **3 HTTP/SSE request tách biệt** (xen kẽ bước người dùng trả lời câu hỏi làm rõ và duyệt milestones).
- **Đề xuất cấu hình Decomposer (`Task Decomposer` + Self-Correction Retry):**
  - Đặt **`ai_task_decomposer_timeout_seconds = 36.0s`** (trong vùng `35–40s`, bảo đảm biên an toàn ~`1.5x` trên `p95 = 22.5–24.6s` của 6 mục tiêu khó).
  - **Quy tắc Retry chỉ dành cho lỗi nhanh (`SCHEMA_MISMATCH` / `VALIDATION_GATE` Tier 1–2):**
    - Nếu lượt 1 lỗi sớm (thường `10–24s` với lỗi schema/coverage/capacity) **VÀ** ngân sách còn lại `remaining_seconds >= 15.0s` (gồm ít nhất `12s` cho Decomposer retry + `3s` tối thiểu cho Critics, hoặc `ai_min_retry_remaining_seconds = 15.0s`), cho phép **tối đa 1 retry** (`attempt=2`, không gọi tools).
    - Nếu lượt 1 gặp **`TimeoutError` (đã tiêu tốn đủ `35–40s`)** hoặc **`GATEWAY_ERROR`/circuit open**: **KHÔNG retry** (dừng ngay và trả lỗi có cấu trúc `DECOMPOSER_TIMEOUT` kèm phương án thủ công `FR-PLAN-004` trước mốc `55s`). *(Lưu ý: `orchestrator.py:499-533` đã đặt `max_retries=0` ở `AIExecutionManager`, nên `TimeoutError` văng thẳng ra ngoài và không retry; khi nâng trần lượt 1 lên `36s`, cần giữ chặt bất biến `no-retry on TimeoutError` này).*

- **Bảng ngân sách theo bước cho Cách hiểu 1: Trần `55s` tính trên TỪNG BƯỚC / TỪNG SSE JOB độc lập (khớp UX hiện tại):**

| Bước / SSE Job độc lập | Thành phần con | `p50` / `p95` đo được | Budget đề xuất (cấu hình) | Worst-case Job dưới trần `55s` |
|---|---|---|---:|---:|
| **Job 1: Clarifier** | `Clarifier LLM` | `9.96s` / `11.69s` (6 hard) | `15.0s` (chỉ 1 lượt, no retry) | **`15.0s`** (`<= 55s`) |
| **Job 2: Milestone Planner** | Tool-calling hiện tại / *(nếu dùng Prefetch `exp_10`)* + Milestone Critics | Hiện tại `40.45s` / `>50.0s` \| *Prefetch `16.18s` / `17.78s`* | Hiện tại `45.0s` \| *Nếu dùng Prefetch: `28.0s`* + `6.0s` critics reserve | Hiện tại **`50.0–55.0s`** *(dễ chạm trần)* \| *Prefetch: `34.0s` (`<= 55s`)* |
| **Job 3: Schedule Proposal SSE** | **Attempt 1 Decomposer** *(không tool hoặc `<=2` tool)* | `9.68–22.14s` / `14.56–23.44s` | **`36.0s`** | Lượt 1 pass: `<= 36.0s` + Critics/Judge parallel (`p95=6.2–7.4s`, cap **`12.0s`**) = **`<= 48.0s`** (`< 55s`) |
| ↳ *(Nhánh lỗi nhanh trên Job 3)* | Attempt 1 fail nhanh ở `<=25s` + **1 Retry** + **Critics/Judge** | Retry mất thêm `~10–22s` (không tool) | Điều kiện vào retry: `remaining >= 15.0s`; timeout retry = `min(25s, remaining - 8s)` | `<= 25s + 22s + 8s = 55.0s` (cắt cứng đúng **`55.0s`** tại `pipeline_deadline`) |

- **Bảng ngân sách theo bước cho Cách hiểu 2: Trần `55s` tính cho TOÀN LUỒNG nối tiếp (End-to-End 1 mạch không dừng):**

| Kịch bản ghép nối toàn trình | Clarifier | Milestone Planner | Task Decomposer | Critics + Judge (`gather`) | Tổng `p50` / `p95` / Worst-case | Khả thi với trần `55s` & `EVAL-07 (P95<=35s)`? |
|---|---:|---:|---:|---:|---|---|
| **2A. Giữ kiến trúc hiện tại** (`Clarifier + Planner tool-calling + Decomposer`) | `9.96s` / `11.69s` | `36.3–40.5s` / `>50.0s` | `21.1–22.1s` / `23.4–23.9s` | `3.5s` / `7.4s` | `p50 ≈ 68–76s`, `p95 > 92s` | **KHÔNG KHẢ THI** (vượt xa `55s`; E2E blocker `0/6`) |
| **2B. Nếu Clarifier tách bước UX, ghép `Planner (Prefetch exp_10) + Decomposer (budget) + Critics/Judge`** | *(tách riêng trước khi bấm Generate)* | Prefetch: `16.18s` / `17.78s` (cap `22.0s`) | Budget (`tools=False`): `21.77s` / `22.51s` (cap `26.0s`) | Dynamic `<= 7.0s–12.0s`: `3.5s` / `6.5–7.4s` | `p50 ≈ 41.5s`, `p95 ≈ 45–48s`, cap `55.0s` | **Sát trần `55s`**, nhưng **không còn chỗ retry Decomposer** và **`p95 > 35s` (`EVAL-07`)** cho goal 5–6 milestone |
| **2C. Ghép cả 3 bước (`Clarifier + Planner + Decomposer + Judge`) trong 1 cửa sổ `55s` duy nhất** | `9.96s` / `11.69s` | Prefetch `16.18s` / `17.78s` | `21.77s` / `22.51s` | `3.5s` / `7.4s` | `p50 ≈ 51.4s`, `p95 ≈ 59s+` | **VƯỢT TRẦN `55s` ở tail/p95** — trừ phi ghép hoặc song song hóa/rút gọn model nhỏ hơn |

> **Kết luận kiến trúc về trần `55s`:** `NFR-PERF-001` (`55s` Hard Timeout) trong FocusFlow hợp lý nhất khi áp dụng cho **từng SSE/API job độc lập (Cách hiểu 1)**, vì người dùng thực tế dừng lại ở bước trả lời Clarifier và bước duyệt/sửa Milestones. Tuy nhiên, nếu muốn **giai đoạn hậu-Clarifier (hoặc nút "Tạo ngay") chạy 1 mạch dưới `55s`**, **bắt buộc** phải bỏ tool-calling loop chậm của Milestone Planner (chuyển sang Server Prefetch để rút `50s -> 17.8s`) và giữ `ai_task_decomposer_timeout_seconds` trong khung `26–36s` tùy việc ghép hay tách Job.

### B6. Thực thi & Đo kiểm Judge Phương án A (`<= 12s` timeout động trong `gather`, `>= 36` lượt ở `c=5` và `c=10`)
- **Đã triển khai Phương án A (không làm B/C):**
  - [config.py:95](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/config.py#L95): `tier3_judge_timeout_seconds = 12.0` (và [tier3_judge.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/validation_gate/tier3_judge.py) `TIER3_JUDGE_TIMEOUT_SECONDS = 12.0`).
  - [orchestrator.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/validation_gate/orchestrator.py): Trong `asyncio.gather(_run_critics_coro(), _run_judge_coro())`, tính `dynamic_judge_cap = min(configured_judge_timeout (12.0s), remaining_budget)` truyền vào Judge để bảo đảm tổng thời gian vẫn nằm dưới `pipeline_deadline` `55s`.
  - Unit test mới `test_judge_method_a_dynamic_timeout_in_gather` trong [test_group5_judge_parallel.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_group5_judge_parallel.py).
- **Kết quả chạy lại live (`--trials-per-goal 2` trên `golden_planning_18_goals.jsonl` = `36` lượt/mức, `18` judge checks/mức):**

| Mức đồng thời & Phiên bản | `total_runs` | `pass_at_1` | `pass_with_judge_verdict` | `critics_judge_parallel` `p50` / `p95` / `max` | `REVIEW_PENDING` count / rate |
|---|---:|---:|---:|---|---|
| Trước Phương án A (`c=5`, `8.0s`, [concurrency_5_eval.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/concurrency_5_eval.json)) | 18 | `1.0000` (`18/18`) | `0.8333` (`15/18`) | `4.20s` / `10.61s` / `14.84s` | **`3/18` (`16.67%`)** |
| **Sau Phương án A (`c=5`, `<=12s`, [concurrency_5_method_a_36runs.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/concurrency_5_method_a_36runs.json))** | **36** | **`1.0000` (`36/36`)** | **`1.0000` (`36/36`)** | **`3.50s` / `6.20s` / `6.43s`** | **`0/18` (`0.00%`)** |
| Trước Phương án A (`c=10`, `8.0s`, [concurrency_10_eval.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/concurrency_10_eval.json)) | 18 | `1.0000` (`18/18`) | `0.9444` (`17/18`) | `4.41s` / `11.93s` / `11.93s` | **`1/18` (`5.56%`)** |
| **Sau Phương án A (`c=10`, `<=12s`, [concurrency_10_method_a_36runs.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/concurrency_10_method_a_36runs.json))** | **36** | **`1.0000` (`36/36`)** | **`1.0000` (`36/36`)** | **`3.04s` / `7.43s` / `8.04s`** | **`0/18` (`0.00%`)** |

> Phương án A đưa **`REVIEW_PENDING` về `0.00%` (`0/36` runs, `0/18` judge checks)** ở cả `c=5` lẫn `c=10`, `pass_with_judge_verdict = 1.0000`, `decomposer p95 = 14.56–14.64s`, không cần độ phức tạp của Phương án B/C ở ngưỡng tải `c <= 10`.

### B7. Chạy lại toàn bộ Smoke 14 mục sau thay đổi bắt buộc `thinking_level` (`exp_12`)
- Script: [exp_12_smoke_14_items.py](file:///Users/vuthang/Documents/FocusFlow/scripts/experiments/exp_12_smoke_14_items.py) → Kết quả: [exp_12_smoke_14_items.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_12_smoke_14_items.json)
- **Kết quả tổng: `14/14 PASS` (`0 FAIL`)**, toàn bộ 13 mục LLM dùng tường minh `gemini-3.8-flash-low` (`degraded_model_used=False`):
  - `goal-clarifier`: **`6,048.60 ms`** (`questions=2`, `other_last=True`)
  - `goal-clarifier-followup`: **`2,633.49 ms`** (`questions=1`, `other_last=True`)
  - `learning-milestone-planner`: **`30,766.49 ms`** (`milestones=4`, `tier1_viols=0`)
  - `learning-task-decomposer`: **`23,601.64 ms`** (`tasks=9`, `dur_30_120=True`)
  - `coverage-prerequisite-critic`: **`2,497.41 ms`** (`PASS`)
  - `learner-fit-actionability-critic`: **`2,604.73 ms`** (`PASS`)
  - `quality-arbiter`: **`1,991.61 ms`** (`PASS`)
  - `pedagogical-quality-judge`: **`2,777.16 ms`** (`PASSED`, `score=96.0`)
  - `proposal-self-correction`: **`27,382.03 ms`** (`tasks=7`, `repair_attempts=1`)
  - **`prove-question-generator`**: **`4,248.40 ms`** (`questions=3`, `ids=['q1', 'q2', 'q3']`)
  - **`prove-mode-grader (good)`**: **`3,426.52 ms`** (`server_score=100`, `server_status=PASSED`)
  - **`prove-mode-grader (injection/gibberish)`**: **`4,358.28 ms`** (`server_score=0`, `server_status=NEEDS_REVIEW`, `addressed=[False, False, False]`)
  - `weekly-review-advisor`: **`5,731.37 ms`** (`fallback=False`, `faithfulness=0.875`)
  - **`LiteLLMEmbeddingAdapter`**: **`2,887.02 ms`** (`gemini/gemini-embedding-2`, `count=2`, `dims=[768, 768]`, `l2_norms=[1.0, 1.0]`)

### B8. Probe chỉ kiểm tra các model mà chế độ hiện tại dùng & Cập nhật `.env.example`
- Trong [litellm_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py): `_collect_configured_models()` kiểm tra theo chế độ `LLM_THINKING_CONTROL` đang kích hoạt:
  - Chế độ `model_suffix`: chỉ thu thập `LLM_MODEL_LOW`, `LLM_MODEL_MEDIUM`, `LLM_MODEL_HIGH` (+ `LLM_FALLBACK_MODELS` nếu có); **không** kiểm tra biến `LLM_MODEL` không dùng tới.
  - Chế độ `param` (hoặc non-Gemini): chỉ thu thập `LLM_MODEL` (+ `LLM_FALLBACK_MODELS` nếu có).
- Đã cập nhật chú thích rõ ràng trong [.env.example](file:///Users/vuthang/Documents/FocusFlow/.env.example) và kiểm chứng bằng `test_probe_cobhub_capabilities_checks_all_configured_models_against_v1beta_models` trong [test_prompt_sanitizer_and_llm_port.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/shared_kernel/test_prompt_sanitizer_and_llm_port.py).

### B9. Lịch `launchd` ghi nhận các khung giờ bị bỏ lỡ (`MISSED_SLEEP`, `DELAYED_WAKE`, `COBHUB_UNREACHABLE`) vào CSV
- Đã nâng cấp [run_scheduled_eval.py](file:///Users/vuthang/Documents/FocusFlow/scripts/run_scheduled_eval.py) và bổ sung unit test [test_run_scheduled_eval.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/test_run_scheduled_eval.py) (`3 passed`):
  - Bổ sung 3 cột mới vào `hourly_stage_metrics.csv`: `scheduled_slot`, `status` (`OK`, `DELAYED_WAKE`, `MISSED_SLEEP`, `COBHUB_UNREACHABLE`, `EVAL_ERROR`), `reason`, kèm hàm `migrate_csv_if_needed()` tự chuyển đổi CSV 12 cột cũ sang 15 cột khi ghi lượt mới.
  - Backfill tự động mọi khung `(09:00, 14:00, 21:00)` bị trôi qua giữa `last_run_at` và lần chạy hiện tại do máy ngủ thành dòng `MISSED_SLEEP`; nếu chạy trễ `> 30` phút so với slot gần nhất sẽ gắn nhãn `DELAYED_WAKE`; nếu pre-check `cobhub /v1beta/models` thất bại sẽ ghi dòng `COBHUB_UNREACHABLE` kèm lý do cụ thể.

