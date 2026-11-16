# Báo Cáo Tổng Kết Hardening AI Pipeline trên `cobhub` & Google AI Studio Embedding — FocusFlow

- **Nhánh:** `feat/cobhub-hardening`
- **Phạm vi commit:** `cd5989b` (checkpoint baseline) → `4db079f` (Nhóm 6) + **Nhóm 7** (Verification & Reporting)
- **Ngày báo cáo:** `2026-11-16`
- **Gateway LLM kiểm chứng:** `LLM_BASE_URL=http://127.0.0.1:8045` (`cobhub`), chạy **tuần tự** (`concurrency=1`)
- **Endpoint Embedding kiểm chứng:** Google AI Studio (`EMBEDDING_PROVIDER=google_ai_studio`, `EMBEDDING_MODEL=gemini/gemini-embedding-2`, `EMBEDDING_DIMENSIONS=768`, không đi qua `cobhub`)

---

## 1. Danh sách Commit / Nhóm Việc & Trạng thái Xác minh

| Commit | Nhóm việc | Trạng thái | Tóm tắt thay đổi & Lý do xác nhận / sửa / bỏ qua |
|---|---|---|---|
| `cd5989b` | Baseline Checkpoint | **XÁC NHẬN** | Đóng băng trạng thái pre-hardening trước khi triển khai thực nghiệm Nhóm 0–7. |
| `75d5c94` | **Nhóm 0** — Thực nghiệm `cobhub` & Embedding | **XÁC NHẬN (phát hiện 4 giả định SAI)** | Thực nghiệm `0.1`–`0.6` (`docs/experiments/exp_01..06`, `summary.md`) phơi bày 4 sai lệch cốt lõi: (1) `thinking_level` param bị `cobhub` bỏ qua, chỉ `-low/-medium/-high` suffix có tác dụng; (2) `cobhub` không ép `response_json_schema` (0/50); (3) `cobhub` không có endpoint Embedding (`400`/`404`); (4) Judge 8s với `gemini-3.8-flash` mặc định bị timeout 93.3–100%. |
| `f123334` | **Nhóm 4 (4.1–4.5)** — Chuẩn hóa Metric Eval | **ĐÃ SỬA & XÁC NHẬN** | Sửa triệt để cách tính metric trong `eval_runner.py`: tách 4 trạng thái Judge (`PASSED`, `NEEDS_REVIEW`, `REVIEW_PENDING`, `SKIPPED`), tách `weekly_llm_faithfulness_avg` khỏi fallback, loại ca timeout/rỗng khỏi mẫu số `injection_isolation_rate`, thêm `error_breakdown` 6 nhóm (`AIErrorCategory`), `validate_eval_report_totals`, `--concurrency`. Ghi nhận mốc TRƯỚC chuẩn hóa tại `baseline_normalized_metrics.json` (`0/18`). |
| `8ab8ae1` | **Nhóm 1 (1.1–1.5, 4.6)** — Schema Compaction & Repair | **ĐÃ SỬA & XÁC NHẬN** | Áp dụng `LLM_SCHEMA_ENFORCED_BY_GATEWAY=false` (Mode 3: chèn compact schema vào `system_instruction` + giữ `response_json_schema`), taxonomy `AIErrorCategory` 6 nhóm, retry có chọn lọc cho `TIMEOUT`/`GATEWAY_ERROR` (gồm HTTP 500 `Stream interrupted` tối đa 1 lần), 1-shot schema repair tại adapter/execution manager, và ép `ClarificationFollowupLLMOutput` đúng 1 câu hỏi (`min_length=1, max_length=1`). |
| `da981af` | **Nhóm 2** — Thinking Suffix & Measured Budgets | **ĐÃ SỬA & XÁC NHẬN (sửa giả định Nhóm 0)** | Ánh xạ `LLM_THINKING_CONTROL=model_suffix` (`gemini-3.8-flash-{low,medium,high}`), đo `p50/p95` mọi stage (`group2_measurements.json`), thay toàn bộ timeout hardcoded (`18/25/35s`) bằng cấu hình stage budget trong `Settings` (`<= ai_hard_timeout_seconds=55s`). **Sửa giả định Nhóm 0:** thực nghiệm `decomposer_low_vs_medium` và `planner_low_vs_medium` chứng minh `LOW` vượt trội `MEDIUM` (`pass@1` `1.0` vs `0.9074`, `p95` `15.43s` vs `37.12s`, `thinking` `0.83%` vs `54.58%`), nên chuyển `TASK_DECOMPOSER_SKILL`, `MILESTONE_PLANNER_SKILL`, `PROPOSAL_SELF_CORRECTION_PROMPT`, `PROVE_MODE_GRADER_PROMPT` về `LOW`. |
| `675c80a` | **Nhóm 3** — Tách Embedding Google AI Studio | **ĐÃ SỬA & XÁC NHẬN** | Cô lập cấu hình `EMBEDDING_*` (`google_ai_studio`, `gemini/gemini-embedding-2`, `768d`, `EMBEDDING_BASE_URL=""`), sửa lỗi truyền `dimensions` thay cho `output_dimensionality` vào `litellm.aembedding`, ép chuẩn hóa L2, truyền `task_type` (`RETRIEVAL_DOCUMENT`/`RETRIEVAL_QUERY`), xác minh 5/5 retrieval (`group3_embedding_verification.json`). |
| `16e7a4b` | **Nhóm 5** — Parallel Critics + Tier 3 Judge | **ĐÃ SỬA & XÁC NHẬN (BỎ QUA tăng timeout 12s)** | Bổ sung `build_compact_judge_payload`, chạy Dual Critics + Tier 3 Judge **song song** qua `asyncio.gather` với `BufferedWorkflowRepo` (persist tuần tự sau khi `gather` xong). **Bỏ qua** đề xuất tăng `tier3_judge_timeout_seconds` lên `12s` từ Nhóm 0.5 vì giữ **`8.0s`** cùng `gemini-3.8-flash-low` đã đạt `18/18` (`100%`) phán quyết thật và pipeline `p95 = 17.74s <= 55s` (`group5_judge_and_pipeline_budget.json`). |
| `4db079f` | **Nhóm 6** — Security, TZ & Arch Guard | **ĐÃ SỬA & XÁC NHẬN** | Đặt `llm_base_url` mặc định `""` (fail-closed khi thiếu gateway thay vì fallback ngầm), fix bug nhóm ngày theo UTC trong `ExecutionDashboardAdapter` & `WeeklyExecutionMetricsAdapter` (sửa triệt để lỗi pre-existing `test_dashboard_summary_active_user_real_data`), tổng quát hóa regex phân lập untrusted context, thêm test hủy outer quota và architecture guard (`test_ai_architecture_boundaries.py`). |
| *(Nhóm 7)* | **Nhóm 7** — Sync `eval_runner`, Verification & Report | **ĐÃ SỬA & XÁC NHẬN** | Đồng bộ [eval_runner.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/eval_runner.py) để `live=True` mặc định chạy qua `ProposalValidationGateOrchestrator` với `Parallel(Dual Critics + Tier 3 Judge)` (`LOW`, Judge `8.0s`, pipeline `55.0s`), bổ sung đếm `schema_check_calls`, `schema_repair_attempts_total`, `post_repair_schema_mismatch_count`, `post_repair_schema_mismatch_rate`; chạy lại toàn bộ gates, offline/live tests, smoke 14 mục và 3 lần eval 18 goal tuần tự. |

---

## 2. Kết quả Nhóm 0 (`cobhub` & Google AI Studio Baseline)

### 2.1. Độ trễ nền `cobhub` (Exp `0.1`, 10 call tuần tự tối thiểu)

Prompt `'Trả về JSON {"ok":true}'`, `model="gemini-3.8-flash"`, `thinking_level="MEDIUM"`:

- Thành công: `10/10`
- Latency (ms): `min = 1,748.2` | `p50 = 2,528.6` | `p95 = 4,087.6` | `max = 4,134.9` | `mean = 2,689.0`
- Tokens: `prompt = 9`, `candidate = 10`, `thinking = 91..208` (`p50 = 158.5`, `p95 = 205.3`)

### 2.2. Thí nghiệm Thinking Arms `A/B/C/D/E/F` (Exp `0.2`, 60 call xen kẽ)

Cùng prompt thật `goal-clarifier` (`ClarificationQuestionsLLMOutput`), 10 vòng round-robin:

| Arm | Model yêu cầu | `thinking_level` gửi | `actual_model_id` | OK | Latency `min / p50 / p95 / max` (ms) | `thinking_tokens` `min / p50 / p95 / max` | `total_tokens` `p50` |
|---|---|---|---|---:|---|---:|---:|
| **A** | `gemini-3.8-flash` | `LOW` | `gemini-3.8-flash` | 10/10 | `21,516.5 / 24,213.2 / 28,556.2 / 29,081.3` | `1,715 / 2,083.5 / 2,809.5 / 2,859` | 3,648.0 |
| **B** | `gemini-3.8-flash-low` | *(Không gửi)* | `gemini-3.8-flash-low` | 10/10 | **`7,325.0 / 9,099.0 / 11,390.0 / 11,805.0`** | **`0 / 149.5 / 313.6 / 314`** | **1,564.0** |
| **C** | `gemini-3.8-flash` | `HIGH` | `gemini-3.8-flash` | 10/10 | `19,299.0 / 25,919.0 / 29,909.0 / 30,455.0` | `1,444 / 2,419.0 / 2,908.1 / 2,940` | 3,907.0 |
| **D** | `gemini-3.8-flash-high` | *(Không gửi)* | `gemini-3.8-flash-high` | 10/10 | `21,543.0 / 23,888.0 / 28,741.0 / 28,871.0` | `1,701 / 2,005.0 / 2,710.5 / 2,872` | 3,552.5 |
| **E** | `gemini-3.8-flash` | *(Không gửi)* | `gemini-3.8-flash` | 10/10 | `22,361.0 / 24,623.0 / 31,310.0 / 32,541.0` | `1,731 / 2,122.5 / 3,047.6 / 3,080` | 3,697.5 |
| **F** | `gemini-3.8-flash-tiered` | *(Không gửi)* | `gemini-3.8-flash-tiered` | 10/10 | `20,671.0 / 23,605.0 / 29,218.0 / 29,305.0` | `1,642 / 2,143.5 / 2,917.8 / 2,970` | 3,599.5 |

### 2.3. Enforce Schema qua `cobhub` (Exp `0.3`, 5 bài × 3 chế độ × 10 lần = 150 call)

Đánh giá bằng Pydantic `model_validate(parsed)` thuần (không qua normalizer):

| Bài thử | Mode 1: `response_json_schema` only | Mode 2: Compact schema trong `system_instruction` | Mode 3: Compact schema + `response_json_schema` |
|---|---|---|---|
| **1. `SimpleCheckSchema`** | **0/10 (0%)** *(9 sai field, 1 HTTP 500)* | **10/10 (100%)** (`p50=3.01s`) | **10/10 (100%)** (`p50=3.13s`) |
| **2. `SampleRoadmapOutput`** | **0/10 (0%)** *(10 `JSONDecodeError`)* | **9/10 (90%)** *(1 HTTP 500 stream; `p50=5.25s`)* | **9/10 (90%)** *(1 HTTP 500 stream; `p50=5.88s`)* |
| **3. `CriticQualityLLMOutput`** | **0/10 (0%)** *(10 sai field/enum)* | **10/10 (100%)** (`p50=9.67s`) | **10/10 (100%)** (`p50=9.32s`) |
| **4. `ProveQuestionsLLMOutput`** | **0/10 (0%)** *(7 `JSONDecodeError`, 3 sai cấu trúc)* | **7/10 (70%)** *(1 HTTP 500, 2 `JSONDecodeError`; `p50=9.01s`)* | **9/10 (90%)** *(1 HTTP 500 stream; `p50=7.83s`)* |
| **5. `tool -> JSON` (2 lượt)** | **0/10 (0%)** *(10 thiếu `status/summary/milestones`)* | **10/10 (100%)** (`p50=4.51s`) | **10/10 (100%)** (`p50=4.11s`) |
| **Tổng cộng** | **0 / 50 (0.0%)** | **46 / 50 (92.0%)** | **48 / 50 (96.0%)** *(48/48 = 100% ngoài lỗi HTTP 500 stream)* |

### 2.4. Embedding Google AI Studio (Exp `0.4`)

- `cobhub` không hỗ trợ embedding (`400 Unsupported method` / `404`), còn Google AI Studio cung cấp `models/gemini-embedding-001`, `models/gemini-embedding-2`, `models/gemini-embedding-2-preview`.
- `litellm.aembedding` bắt buộc prefix `gemini/gemini-embedding-2` (thiếu prefix `gemini/` bị rơi vào Vertex ADC lỗi `APIConnectionError`), truyền `dimensions=768` (truyền `output_dimensionality=768` bị `litellm` bỏ qua về 3072) và `task_type` (`RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY`).
- Vector trả về từ `gemini/gemini-embedding-2` có dim `768`, L2 norm `1.0..1.000001` (so với `gemini-embedding-001` chưa norm L2 `0.588..0.592`), sanity retrieval top-1 chính xác (`0.8379` vs `0.6273`, margin `+0.2106`).

### 2.5. Judge Tier 3 A/B (Exp `0.5`, 30 call)

| Nhánh | Model | OK | Phán quyết đúng | `<= 8s` | Latency `min / p50 / p95 / max` (ms) | `thinking_tokens` `min / p50 / p95 / max` | `total_tokens` `p50` |
|---|---|---:|---:|---:|---|---:|---:|
| **`LOW_SUFFIX`** | `gemini-3.8-flash-low` | **10/10** | **10/10 (100%)** | **80% (8/10)** | `3,470.2 / 5,613.7 / 24,883.9 / 34,455.0` | **`0 / 0.0 / 0.0 / 0`** | **1,755.0** |
| **`MEDIUM_SUFFIX`** | `gemini-3.8-flash-medium` | **10/10** | **10/10 (100%)** | 10% (1/10) | `7,905.0 / 10,757.2 / 28,510.6 / 30,770.9` | `411 / 755.0 / 1,034.3 / 1,131` | 2,574.5 |
| **`BASE_MEDIUM`** | `gemini-3.8-flash` | 9/10 *(1 timeout 45s)* | 9/10 (90%) | **0% (0/10)** | `8,552.5 / 9,968.2 / 12,569.1 / 12,892.1` | `1,786 / 2,065.0 / 2,482.8 / 2,612` | 3,780.0 |

### 2.6. Mốc Eval Baseline `0.6` & Quyết định rút ra

- `exp_06_eval_baseline.json` (code cũ `eval_runner` v1.0, `gemini-3.8-flash` qua `cobhub`): `pass_at_1 = 0.8333` (`15/18`), `thinking_tokens = 27,797 / 43,345` (`64.1%`), `latency_p95 = 35,015.99ms`, `judge_timeout_rate = 0.9333` (`14/15` `REVIEW_PENDING`), `weekly_fallback_rate = 1.0` (`18/18` fallback nhưng báo ảo `faithfulness = 1.0`).
- **Quyết định rút ra (được tinh chỉnh thêm ở Nhóm 2 & Nhóm 5):**
  1. Dùng `LLM_THINKING_CONTROL=model_suffix` (`gemini-3.8-flash-{low,medium,high}`) làm cơ chế điều khiển suy nghĩ chính trên `cobhub`.
  2. Dùng `LLM_SCHEMA_ENFORCED_BY_GATEWAY=false` (Mode 3) + 1-shot schema repair + retry HTTP 500 stream/timeout.
  3. Cô lập Google AI Studio Embedding (`768d`, L2 norm, `task_type`).
  4. Áp dụng tầng `LOW` (`gemini-3.8-flash-low`) cho toàn bộ 12 production prompts sau khi thực nghiệm Nhóm 2 (`group2_measurements.json`) chứng minh `LOW` vượt trội `MEDIUM` cả về `pass@1` lẫn `p95` ở `Task Decomposer` và `Milestone Planner`, đồng thời giữ `tier3_judge_timeout_seconds = 8.0s` chạy song song với Dual Critics.

---

## 3. Bảng Metric TRƯỚC / SAU & Đối chiếu 7 Tiêu chí Chấp nhận

### 3.1. Smoke 14 mục thật (12 Production Prompts + Prove `"a"`/injection + Google AI Studio Embedding)

- **TRƯỚC** ([live-real-test-report.md](file:///Users/vuthang/Documents/FocusFlow/docs/reports/live-real-test-report.md)): **5/14 PASS** *(thực tế chỉ **4/14** thực sự hoàn tất hợp lệ vì `pedagogical-quality-judge` timeout ở `8,019.37 ms` rồi fail-open sang `REVIEW_PENDING`)*; `9/14 FAIL` do `ValidationError` (thiếu schema enforcement ở `cobhub`), `TimeoutError` (`25s`/`30s`), và `NotFoundError` trên Embedding.
- **SAU** ([group7_smoke_results.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/group7_smoke_results.json)): **14/14 PASS (0 FAIL)**, tất cả đều thành công ngay ở lượt 1 (`attempts=1`, `repair_attempts=0`, `degraded_model_used=false`), tổng `thinking_tokens` trên 13 mục LLM chỉ là `653 / 8,130` output tokens (`8.03%`):

| # | `prompt_id` / Adapter | TRƯỚC (`live-real-test-report.md`) | SAU (`group7_smoke_results.json`) | Model (`actual_model_id`) | Tokens (`P / O / T`) | Latency (ms) | Invariant kiểm chứng |
|---:|---|---|---|---|---:|---:|---|
| 1 | `goal-clarifier` | PASS (`20,816.82 ms`) | **PASS** | `gemini-3.8-flash-low` | `1,029 / 598 / 0` | `7,843.05` | `questions=2, other_last=True` |
| 2 | `goal-clarifier-followup` | FAIL (`questions=[]`) | **PASS** | `gemini-3.8-flash-low` | `757 / 255 / 0` | `4,026.82` | `questions=1, other_last=True` |
| 3 | `learning-milestone-planner` | FAIL (`TimeoutError 30s`) | **PASS** | `gemini-3.8-flash-low` | `1,048 / 1,252 / 0` | `10,541.62` | `milestones=4, contiguous_seq=True` |
| 4 | `learning-task-decomposer` | FAIL (`TimeoutError 30s`) | **PASS** | `gemini-3.8-flash-low` | `1,236 / 2,336 / 653` | `18,911.29` | `tasks=6, valid_mids=True, dur_30_120=True` |
| 5 | `coverage-prerequisite-critic` | FAIL (`ValidationError`) | **PASS** | `gemini-3.8-flash-low` | `2,236 / 32 / 0` | `4,592.88` | `critic_status=PASS, issues=0` |
| 6 | `learner-fit-actionability-critic` | FAIL (`TimeoutError 25s`) | **PASS** | `gemini-3.8-flash-low` | `2,231 / 403 / 0` | `4,974.88` | `critic_status=WARN, issues=2` |
| 7 | `quality-arbiter` | FAIL (`TimeoutError 25s`) | **PASS** | `gemini-3.8-flash-low` | `2,314 / 31 / 0` | `2,488.47` | `arbiter_status=PASS, issues=0` |
| 8 | `pedagogical-quality-judge` | PASS *(fail-open timeout `8,019ms`)* | **PASS** *(phán quyết thật)* | `gemini-3.8-flash-low` | `2,249 / 291 / 0` | `5,565.09` | `judge_status=PASSED, score=92.0, skipped=False` |
| 9 | `proposal-self-correction` | PASS (`26,556.10 ms`) | **PASS** | `gemini-3.8-flash-low` | `1,373 / 1,604 / 0` | `12,549.53` | `tasks=6, dur_30_120=True` |
| 10 | `prove-question-generator` | FAIL (`ValidationError`) | **PASS** | `gemini-3.8-flash-low` | `797 / 209 / 0` | `4,546.04` | `questions=3, ids=['q1', 'q2', 'q3']` |
| 11a | `prove-mode-grader` (tốt) | PASS (`14,647.32 ms`) | **PASS** | `gemini-3.8-flash-low` | `1,267 / 335 / 0` | `4,943.81` | `server_score=88, server_status=PASSED` |
| 11b | `prove-mode-grader` (`"a"`/inj) | PASS (`6,839.47 ms`) | **PASS** | `gemini-3.8-flash-low` | `1,108 / 324 / 0` | `5,112.93` | `server_score=0, server_status=NEEDS_REVIEW, addressed=[False, False, False]` |
| 12 | `weekly-review-advisor` | FAIL (`TimeoutError 25s`) | **PASS** | `gemini-3.8-flash-low` | `800 / 460 / 0` | `6,371.89` | `fallback=False, faithfulness=1.0` |
| 13 | `LiteLLMEmbeddingAdapter` | FAIL (`NotFoundError`) | **PASS** | `gemini/gemini-embedding-2` | — | `2,350.86` | `count=2, dims=[768, 768], l2_norms=[1.0, 1.0]` |

### 3.2. Eval 18 Goal Tuần tự (`concurrency=1`, `trials_per_goal=1`) — TRƯỚC vs 3 lần chạy SAU

> **Ghi chú về mốc TRƯỚC:** [baseline_normalized_metrics.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/baseline_normalized_metrics.json) (đo sau khi chuẩn hóa metric ở Nhóm 4, trước Nhóm 1/2) ghi nhận **`0/18`** do độ trễ cao của `gemini-3.8-flash` (mặc định tier `HIGH`) chạm trần `35s` (`16 TIMEOUT`, `1 SCHEMA_MISMATCH`, `1 GATEWAY_ERROR`); trước đó [exp_06_eval_baseline.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_06_eval_baseline.json) đạt `15/18` (`0.8333`) với `27,797` thinking tokens (`64.13%`), `14/15` judge timeout và `18/18` weekly fallback; còn [live-real-test-report.md](file:///Users/vuthang/Documents/FocusFlow/docs/reports/live-real-test-report.md) đạt `1/18` (`0.0556`).
>
> **Ghi chú về phạm vi token ở SAU:** Trong `eval_runner` (`Parallel(Critics + Judge)`), `prompt_tokens_total` / `output_tokens_total` / `thinking_tokens_total` gộp toàn bộ bước lập lịch (`TASK_DECOMPOSER` + `2 Critics` + `Arbiter nếu có` + `PEDAGOGICAL_JUDGE`), còn `schema_check_calls = 90` mỗi run gồm `18` decomposer + `36` critics + `18` judge + `18` weekly.

| Metric chuẩn hóa (Nhóm 4 + Nhóm 7) | TRƯỚC (`baseline_normalized_metrics.json`) | TRƯỚC tham chiếu (`exp_06_eval_baseline.json`) | **SAU — Run 1** (`group7_eval_run_1.json`) | **SAU — Run 2** (`group7_eval_run_2.json`) | **SAU — Run 3** (`group7_eval_run_3.json`) |
|---|---:|---:|---:|---:|---:|
| `passed_runs / total_runs` | `0 / 18` | `15 / 18` | **`18 / 18`** | **`18 / 18`** | **`18 / 18`** |
| `pass_at_1` | `0.0000` (`0/18`) | `0.8333` (`15/18`) | **`1.0000`** (`18/18`) | **`1.0000`** (`18/18`) | **`1.0000`** (`18/18`) |
| `post_retry_recovery_rate` | `0.0000` (`0/18`) | `0.8333` (`15/18`) | **`1.0000`** (`18/18`) | **`1.0000`** (`18/18`) | **`1.0000`** (`18/18`) |
| `avg_retries` | `0.0` | `0.0` | **`0.0`** | **`0.0`** | **`0.0`** |
| `schema_check_calls` | — | — | `90` | `90` | `90` |
| `schema_repair_attempts_total` | — | — | `0` | `0` | `0` |
| `post_repair_schema_mismatch_count / rate` | `1` *(decomposer)* | — | **`0 / 90` (`0.00%`)** | **`0 / 90` (`0.00%`)** | **`0 / 90` (`0.00%`)** |
| `prompt_tokens_total` | `0` *(timeout mất telemetry)* | `18,803` *(chưa gộp critics)* | `155,165` | `154,244` | `153,816` |
| `output_tokens_total` | `0` | `43,345` | `26,851` | `24,714` | `25,537` |
| `thinking_tokens_total` (`% output`) | `0` (`N/A`) | `27,797` (`64.13%`) | **`651` (`2.42%`)** | **`0` (`0.00%`)** | **`428` (`1.68%`)** |
| `latency_p50_ms` | `35,015.909 ms` | `19,499.177 ms` | **`15,148.374 ms`** | **`13,232.764 ms`** | **`13,828.656 ms`** |
| `latency_p95_ms` *(kèm max)* | `35,020.536 ms` | `35,015.992 ms` | **`19,780.503 ms`** *(max `28.14s`)* | **`15,634.679 ms`** *(max `16.15s`)* | **`15,490.738 ms`** *(max `16.43s`)* |
| `pedagogical_score_avg` | `None` | — | **`97.78`** *(min `95.0`)* | **`97.78`** *(min `95.0`)* | **`96.94`** *(min `95.0`)* |
| Judge: `PASSED` / `NEEDS_REVIEW` / `REVIEW_PENDING` / `SKIPPED` | `0 / 0 / 0 / 18` | `1 / 0 / 14 / 3` | **`18 / 0 / 0 / 0`** | **`18 / 0 / 0 / 0`** | **`18 / 0 / 0 / 0`** |
| Judge phán quyết thật (`PASSED + NEEDS_REVIEW`) | `0/18` (`0.0%`) | `1/18` (`5.56%`; `1/15=6.67%` valid) | **`18/18` (`100.0%`)** | **`18/18` (`100.0%`)** | **`18/18` (`100.0%`)** |
| `judge_timeout_rate` (`REVIEW_PENDING / attempted`) | `0.0000` (`0/0`) | `0.9333` (`14/15`) | **`0.0000` (`0/18`)** | **`0.0000` (`0/18`)** | **`0.0000` (`0/18`)** |
| `weekly_llm_success_count / weekly_checks` | `0 / 18` (`0.0%`) | `0 / 18` (`0.0%`) | **`18 / 18` (`100.0%`)** | **`18 / 18` (`100.0%`)** | **`18 / 18` (`100.0%`)** |
| `weekly_fallback_rate` | `1.0000` (`18/18`) | `1.0000` (`18/18`) | **`0.0000` (`0/18`)** | **`0.0000` (`0/18`)** | **`0.0000` (`0/18`)** |
| `weekly_llm_faithfulness_avg` | `null` *(0 ca LLM)* | `null` *(ảo `1.0` ở v1.0)* | **`0.9840`** | **`0.9698`** | **`0.9508`** |
| `weekly_fallback_faithfulness_avg` | `1.0000` (`18/18`) | `1.0000` (`18/18`) | `null` (`0/18`) | `null` (`0/18`) | `null` (`0/18`) |
| `injection_isolation_summary` *(mẫu số valid output)* | `0/0 valid (4 excluded)` | `4/4` *(v1.0)* | **`4/4 valid outputs (0 excluded)`** | **`4/4 valid outputs (0 excluded)`** | **`4/4 valid outputs (0 excluded)`** |

#### Bảng phân rã lỗi theo `AIErrorCategory` (TRƯỚC vs SAU)

| Stage / Nhóm lỗi | `SCHEMA_MISMATCH` | `TIMEOUT` | `GATEWAY_ERROR` | `VALIDATION_GATE` | `QUOTA` | `OTHER` | Tổng lỗi |
|---|---:|---:|---:|---:|---:|---:|---:|
| **TRƯỚC (`baseline_normalized_metrics.json`) — Decomposer** | 1 | 16 | 1 | 0 | 0 | 0 | **18** |
| **TRƯỚC (`baseline_normalized_metrics.json`) — Judge** | 0 | 0 | 0 | 0 | 0 | 0 | **0** *(18 skipped)* |
| **TRƯỚC (`baseline_normalized_metrics.json`) — Weekly** | 0 | 18 | 0 | 0 | 0 | 0 | **18** |
| **TRƯỚC — Tổng cộng** | **1** | **34** | **1** | **0** | **0** | **0** | **36** |
| **SAU — Run 1 (Decomposer / Judge / Weekly / Total)** | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | **0** |
| **SAU — Run 2 (Decomposer / Judge / Weekly / Total)** | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | **0** |
| **SAU — Run 3 (Decomposer / Judge / Weekly / Total)** | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | **0** |

### 3.3. Đối chiếu 7 Tiêu chí Chấp nhận

| # | Tiêu chí chấp nhận | Ngưỡng | Run 1 | Run 2 | Run 3 | Kết luận |
|---:|---|---|---:|---:|---:|---|
| 1 | `pass_at_1 >= 0.94` ở `>= 2/3` lần chạy | `>= 0.94` (`>= 2/3` runs) | `1.0000` (`18/18`) | `1.0000` (`18/18`) | `1.0000` (`18/18`) | **ĐẠT (3/3 runs)** |
| 2 | Judge ra phán quyết thật (`PASSED + NEEDS_REVIEW`) | `>= 80%` | `100.0%` (`18/18`) | `100.0%` (`18/18`) | `100.0%` (`18/18`) | **ĐẠT (3/3 runs)** |
| 3 | `weekly_fallback_rate` | `<= 10%` | `0.0%` (`0/18`) | `0.0%` (`0/18`) | `0.0%` (`0/18`) | **ĐẠT (3/3 runs)** |
| 4 | `SCHEMA_MISMATCH` sau repair | `<= 2%` | `0.0%` (`0/90`) | `0.0%` (`0/90`) | `0.0%` (`0/90`) | **ĐẠT (3/3 runs)** |
| 5 | `thinking_tokens` trên `output_tokens` | `<= 25%` *(giảm `>= 60%` vs `27,797`)* | `2.42%` (`651/26,851`) | `0.00%` (`0/24,714`) | `1.68%` (`428/25,537`) | **ĐẠT (3/3 runs, giảm >97%)** |
| 6 | Pipeline `p95` | `<= 55s` | `19.78s` | `15.63s` | `15.49s` | **ĐẠT (3/3 runs)** |
| 7 | `injection_isolation_rate` & Embedding 768d + `0/3` timeout | `100%` (`4/4`) & `>= 4/5` top-1 | `100%` (`4/4`), `0` timeout | `100%` (`4/4`), `0` timeout | `100%` (`4/4`), `0` timeout | **ĐẠT** *(kèm Embedding `5/5` top-1, norm `1.0`, Smoke `14/14`)* |

---

## 4. Kết quả Test, Quality Gates & Contract Checks

Tất cả các cổng kiểm tra dưới đây được chạy trực tiếp ở Nhóm 7 sau bản chỉnh sửa cuối trên `eval_runner.py` và `test_eval_runner_and_dataset.py`:

| Cổng kiểm tra | Lệnh thực thi | Kết quả | Chi tiết đo được |
|---|---|---|---|
| Ruff Lint | `bash scripts/quality-gates.sh backend-static` | **PASS** | `All checks passed!` |
| Ruff Format | `bash scripts/quality-gates.sh backend-static` | **PASS** | `351 files already formatted` |
| Mypy Strict | `bash scripts/quality-gates.sh backend-static` | **PASS** | `Success: no issues found in 271 source files` |
| Import-Linter | `bash scripts/quality-gates.sh backend-static` | **PASS** | `Analyzed 263 files, 745 dependencies. Contracts: 5 kept, 0 broken.` |
| Prompts Lock | `cd backend && .venv/bin/python scripts/update_prompts_lock.py --check` | **PASS** | `prompts.lock matches live PromptRegistry (12 prompts).` |
| API Contract | `bash scripts/check-api-contract.sh` | **PASS** | `openapi-typescript 7.13.0` sinh `schema.d.ts` khớp 100% (`92.7ms`) |
| Offline Pytest | `cd backend && ENVIRONMENT=test EMAIL_BACKEND=console REDIS_URL=redis://localhost:6379/0 .venv/bin/pytest -q -m "not live_cobhub and not live_embedding"` | **PASS** | **524 passed, 3 deselected** (`71.68s`) — không còn lỗi pre-existing UTC timezone |
| Live `cobhub` Pytest | `cd backend && ENVIRONMENT=test EMAIL_BACKEND=console REDIS_URL=redis://localhost:6379/0 RUN_LIVE_GEMINI_SDK_TEST=1 LLM_BASE_URL=http://127.0.0.1:8045 .venv/bin/pytest -q -m "live_cobhub" -rs` | **PASS** | **2 passed, 525 deselected** (`143.01s`) |
| Live Embedding Pytest | `cd backend && .venv/bin/pytest -q -m "live_embedding" -rs` | **PASS** | **1 passed, 526 deselected** (`7.32s`) — dim `768`, L2 norm `1.0`, retrieval `5/5` |

---

## 5. Thay đổi Cấu hình / API / DB & Biến môi trường mới

- **Cơ sở dữ liệu (DB Migrations):** **Không có migration DB** (`git diff cd5989b..HEAD -- backend/alembic/ backend/src/**/orm/` rỗng). Giữ nguyên toàn bộ 35 bảng thiết kế SRS / 28 bảng migration hiện hành.
- **API Contract (REST / SSE / OpenAPI):** **Không có breaking change API**. `bash scripts/check-api-contract.sh` xác nhận `frontend/src/app/core/api/schema.d.ts` đồng bộ 100% với OpenAPI schema của `create_app()`.
- **Biến môi trường mới / cập nhật trong `Settings` ([config.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/config.py)), [.env.example](file:///Users/vuthang/Documents/FocusFlow/.env.example) và [docker-compose.yml](file:///Users/vuthang/Documents/FocusFlow/docker-compose.yml):**

| Biến môi trường | Mặc định trong `Settings` | Ý nghĩa & Ràng buộc |
|---|---|---|
| `LLM_THINKING_CONTROL` | `"model_suffix"` | Chọn `"model_suffix"` (dùng `LLM_MODEL_{LOW,MEDIUM,HIGH}` cho `cobhub`) hoặc `"param"` (`thinking_config`). |
| `LLM_MODEL` | `"gemini-3.8-flash-medium"` | Model dự phòng mặc định trên gateway. |
| `LLM_MODEL_LOW` / `_MEDIUM` / `_HIGH` | `"gemini-3.8-flash-{low,medium,high}"` | Model theo tier `LOW`/`MEDIUM`/`HIGH`. |
| `LLM_BASE_URL` | `""` *(bắt buộc set ở runtime, vd `http://127.0.0.1:8045`)* | Fail-closed (`AI_PROVIDER_NOT_CONFIGURED`) nếu rỗng khi `LLM_PROVIDER=gemini`. |
| `LLM_FALLBACK_MODELS` | `""` | Danh sách fallback model trên cùng gateway (phân cách dấu phẩy). |
| `LLM_SCHEMA_ENFORCED_BY_GATEWAY` | `false` | `false` bật Mode 3 (compact schema trong `system_instruction` + `response_json_schema`). |
| `EMBEDDING_PROVIDER` | `"google_ai_studio"` | Tách riêng provider embedding khỏi `cobhub`. |
| `EMBEDDING_API_KEY` / `GEMINI_API_KEY` | `""` | Key dùng riêng cho Google AI Studio Embedding. |
| `EMBEDDING_MODEL` | `"gemini/gemini-embedding-2"` | Bắt buộc giữ prefix `gemini/` cho `litellm.aembedding`. |
| `EMBEDDING_BASE_URL` | `""` | Rỗng = dùng endpoint Google AI Studio mặc định (không dùng `LLM_BASE_URL`). |
| `EMBEDDING_DIMENSIONS` | `768` | Chiều vector đầu ra (`> 0`); ép chuẩn hóa L2 ở adapter. |
| `AI_HARD_TIMEOUT_SECONDS` | `55.0` | Trần cứng toàn hệ thống; mọi stage budget không được vượt quá giá trị này. |
| `AI_SSE_PIPELINE_TIMEOUT_SECONDS` | `55.0` | Ngân sách pipeline SSE (`<= AI_HARD_TIMEOUT_SECONDS`). |
| `AI_CLARIFIER_TIMEOUT_SECONDS` | `15.0` | Budget `goal-clarifier` (`p95 * ~1.5`). |
| `AI_CLARIFIER_FOLLOWUP_TIMEOUT_SECONDS` | `7.5` | Budget `goal-clarifier-followup`. |
| `AI_MILESTONE_PLANNER_TIMEOUT_SECONDS` | `50.0` | Budget `learning-milestone-planner` (có tool). |
| `AI_TASK_DECOMPOSER_TIMEOUT_SECONDS` | `25.0` | Budget mỗi attempt `learning-task-decomposer`. |
| `AI_TOOL_CALL_TIMEOUT_SECONDS` | `40.0` | Budget vòng tool (`<= AI_MILESTONE_PLANNER_TIMEOUT_SECONDS`). |
| `AI_QUALITY_CRITIC_TIMEOUT_SECONDS` | `15.0` | Budget từng critic trong `run_dual_quality_critics`. |
| `AI_QUALITY_ARBITER_TIMEOUT_SECONDS` | `14.5` | Budget `quality-arbiter` khi hai critic bất đồng. |
| `TIER3_JUDGE_TIMEOUT_SECONDS` | `8.0` | Budget `pedagogical-quality-judge` (giữ nguyên `8.0s`). |
| `AI_WEEKLY_REVIEW_TIMEOUT_SECONDS` | `10.5` | Budget `weekly-review-advisor`. |
| `AI_PROVE_QUESTION_TIMEOUT_SECONDS` | `8.5` | Budget `prove-question-generator`. |
| `AI_PROVE_GRADER_TIMEOUT_SECONDS` | `7.5` | Budget `prove-mode-grader`. |
| `AI_MIN_CRITIC_REMAINING_SECONDS` | `6.0` | Ngưỡng ngân sách tối thiểu còn lại để chạy Dual Critics. |
| `AI_MIN_JUDGE_REMAINING_SECONDS` | `3.0` | Ngưỡng ngân sách tối thiểu còn lại để chạy Tier 3 Judge. |
| `AI_MIN_RETRY_REMAINING_SECONDS` | `12.0` | Ngưỡng tối thiểu còn lại để thực hiện self-correction retry. |

---

## 6. Việc còn tồn đọng, Rủi ro & Câu hỏi mở (kèm Giả định mặc định)

### 6.1. Tồn đọng & Rủi ro đã quan sát
1. **Tail spike ở `cobhub` & Milestone Planner (`50s`):** Trên gateway `cobhub` vẫn có xác suất nhỏ gặp latency spike > 20–30s hoặc HTTP 500 `Stream interrupted` (đã có retry 1 lần và fail-open/fallback an toàn, nhưng nếu user chạy ở môi trường mạng yếu, `learning-milestone-planner` có tool call vẫn là stage nặng nhất với `p95 ~38.4s` ở Nhóm 2).
2. **Môi trường Python `.venv` hiện tại là `3.14` vs Docker `3.12`:** Các số đo Nhóm 0–7 chạy trên `.venv` cục bộ (Python 3.14); trước khi đóng release production vẫn nên chạy smoke kiểm tra lại trong container Docker Compose Python 3.12.
3. **File `.env` cục bộ của developer:** Không chạm `.env` thật trong quá trình verification; nếu dev chạy local không truyền env override, cần tự đảm bảo `.env` có `LLM_BASE_URL=http://127.0.0.1:8045` (khi dùng `cobhub`) và `GEMINI_API_KEY` (cho Embedding) do mặc định `llm_base_url=""` hiện fail-closed.
4. **Dữ liệu vector cũ trong `knowledge_chunks` (nếu có):** Bảng `knowledge_chunks` không bị đụng migration, nhưng nếu môi trường dev/staging từng ingest bằng model embedding cũ (chưa chuẩn hóa L2 hoặc dim khác 768) thì cần re-ingest cho đồng bộ với `gemini/gemini-embedding-2` (`768d`).

### 6.2. Tối đa 5 câu hỏi mở & Giả định mặc định
1. **Có cần bật `LLM_FALLBACK_MODELS=gemini-3.8-flash-medium` làm fallback cho stage `LOW` hay giữ rỗng?**
   - *Giả định mặc định:* Giữ `LLM_FALLBACK_MODELS=""` (rỗng) để không âm thầm tăng latency/thinking token khi `cobhub` gặp lỗi tạm thời; chỉ cấu hình qua env khi cần dự phòng sự cố model.
2. **Ngưỡng `TIER3_JUDGE_TIMEOUT_SECONDS=8.0s` có giữ cố định lâu dài hay nâng nhẹ lên `10.0s`?**
   - *Giả định mặc định:* Giữ **`8.0s`** vì thực nghiệm Nhóm 5 & Nhóm 7 đều đạt `18/18` (`100%`) phán quyết thật và pipeline `p95 <= 19.8s`.
3. **Khi `KnowledgeSource` chuyển sang Google AI Studio Embedding (`768d`), có cần thêm job re-embed toàn bộ `knowledge_chunks` cũ ở staging không?**
   - *Giả định mặc định:* Chưa chạy migration/backfill tự động trong phạm vi hardening này; chỉ re-ingest thủ công nếu DB đã có dữ liệu trước `675c80a`.
4. **Weekly Review `quantitative_faithfulness` đạt `0.95–0.98` (đã qua `QuantitativeFaithfulnessValidator` sanitize số ngoài nguồn) có cần siết prompt để đạt `1.00` thô trước sanitize không?**
   - *Giả định mặc định:* Giữ nguyên prompt `weekly-review-advisor@v2.0.0` vì validator tất định đã khóa an toàn đầu ra và tỷ lệ fallback LLM đã về `0%`.
5. **Có giữ toàn bộ 12 production prompts dưới dạng Python constants thay vì chuyển sang `.md` không?**
   - *Giả định mặc định:* **Giữ trong Python** theo dữ liệu Mục 7 bên dưới.

---

## 7. Dữ liệu Định lượng cho Quyết định Lưu trữ `.md`

Dữ liệu trích trực tiếp từ `git log --oneline --since="3 months ago"` trên các file nguồn prompt và [analyze_prompt_maintenance.py](file:///Users/vuthang/Documents/FocusFlow/backend/scripts/analyze_prompt_maintenance.py):

- **Số lượng prompt production hiện có:** **12 prompts** (tất cả ở version `2.0.0`, tổng **`107` dòng / `16,696` ký tự / `~4,168` tokens `len/4` / `~6,128` conservative VI tokens**).
- **Vị trí lưu trữ:**
  1. [roadmap_skills.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/roadmap_skills.py) (`745` LOC): `goal-clarifier`, `goal-clarifier-followup`, `learning-milestone-planner`, `learning-task-decomposer`, `pedagogical-quality-judge`, `proposal-self-correction`, `coverage-prerequisite-critic`, `learner-fit-actionability-critic`, `quality-arbiter` (9 prompts).
  2. [prompts.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/application/prompts.py) (`226` LOC): `prove-question-generator`, `prove-mode-grader`, `weekly-review-advisor` (3 prompts).
  3. [untrusted_context.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/application/harness/untrusted_context.py) (`250` LOC): hằng số bảo mật dùng chung `UNTRUSTED_DATA_SYSTEM_RULE` và helper bao bọc `<untrusted_*>` tags.
- **Lịch sử & Tần suất sửa trong 3 tháng (`git log --oneline --since="3 months ago"`):**
  - Tổng số commit chạm 3 file trên: **8 commits** (trong tổng 152 commits từ `2026-09-29` → `2026-11-16`):
    - `4db079f` (`feat(ai-security): enforce empty default base_url, user tz dashboard, generic untrusted regex, and arch guard`)
    - `16e7a4b` (`feat(ai-judge): run tier3 judge in parallel with critics and enforce pipeline budget`)
    - `da981af` (`feat(ai-harness): add model_suffix thinking control and measured stage budgets`)
    - `8ab8ae1` (`feat(ai-harness): add schema compaction, error taxonomy, and 1-shot repair`)
    - `cd5989b` (`chore: checkpoint pre-cobhub-hardening baseline`)
    - `a13f19f` (`feat(planning): implement Phase 4 AI Harness runtime and resilience architecture`)
    - `32a56ed` (`feat(planning): implement spatio-temporal engine and roadmap-schedule separation`)
    - `7543af2` (`feat(backend): implement gemini 3.8 flash roadmap engine and learning resources tool`)
  - Phân theo file: `roadmap_skills.py` **7 commits**, `prompts.py` **2 commits**, `untrusted_context.py` **2 commits**.
- **Tác giả chỉnh sửa:** **1 tác giả** (`CoffatDev`: 8/8 commits).
- **Mức độ đồng biến đổi (Co-change coupling):** `8/8` commit chạm prompt đều đồng thời sửa Use Cases/Services, `7/8` đồng thời sửa Tests, và `5/8` đồng thời sửa DTO/Schema/`prompts.lock`.
- **Độ trùng lặp giữa system/user prompts (66 cặp system prompts):**
  - Trung bình `SequenceMatcher`: **`0.4854`** | Trung bình `Token Jaccard`: **`0.3948`**
  - Cặp trùng cao nhất: `coverage-prerequisite-critic` ↔ `learner-fit-actionability-critic` (`SequenceMatcher = 0.7845`, `Jaccard = 0.6536`) và `learner-fit-actionability-critic` ↔ `quality-arbiter` (`SequenceMatcher = 0.7132`), chủ yếu do tái sử dụng trực tiếp `UNTRUSTED_DATA_SYSTEM_RULE` và khung chỉ thị Critic bằng biến Python.
- **Kết luận cho quyết định `.md`:** **Không tách ra file `.md` ở giai đoạn hiện tại**; giữ prompt trong Python cùng `PromptRegistry` + `prompts.lock` CI drift check vì quy mô nhỏ (107 dòng), co-change gần 100% với Pydantic schema/use case/test, chỉ có 1 tác giả kỹ thuật, và cần tái sử dụng an toàn hằng số bảo mật `UNTRUSTED_DATA_SYSTEM_RULE` bằng Python import mà không phát sinh parser/template engine ngoài.
