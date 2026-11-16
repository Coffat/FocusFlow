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

---

## 8. Xác minh bổ sung trước khi merge (Mục 1–9 & A–G)

Phần này bổ sung toàn bộ kết quả kiểm chứng sau mốc `fd5549b` và `8f97544` (hiệu chuẩn Judge A/B, so sánh chất lượng `-low` vs `-medium`, tập Holdout 12 mục tiêu mới, tải đồng thời `--concurrency 5/10`, kiểm tra đa khung giờ ngày `2026-11-16`, chạy toàn bộ cổng kiểm tra trong container **Python 3.12**, rà soát Timeout `< 1.5 × p95`, truy vết `weekly_faithfulness < 1.0`, quét lịch sử git & phân tách 7 PR, và đối soát Prompt `v2.0.0`).

### 8.1. Giải thích định lượng mốc "TRƯỚC" (4 artifact chuẩn hóa & đối chiếu công bằng)

Các báo cáo trước sử dụng 4 mốc baseline ở các thời điểm và phiên bản `eval_runner` khác nhau. Bảng dưới đây đặt 4 mốc cạnh nhau để tránh nhầm lẫn khi so sánh:

| Mốc / Artifact | Commit / Phiên bản | Model & Cấu hình | `pass_at_1` | `latency p50 / p95` | `thinking_tokens` (`% output`) | Judge & Weekly | Nguyên nhân chênh lệch |
|---|---|---|---:|---:|---:|---|---|
| [live-real-test-report.md](file:///Users/vuthang/Documents/FocusFlow/docs/reports/live-real-test-report.md) | Pre-Group 0 (`eval_runner` v1) | `gemini-3.8-flash` (mặc định `HIGH`), timeout `35s` | `0.0556` (`1/18`) | `35.02s / 35.02s` | `1,947 / 3,177` (`61.3%`, chỉ `E09`) | Judge `1/1 REVIEW_PENDING`; Weekly `18/18` fallback | `16/18` timeout `35s`, `1/18` `ServerError`. |
| [exp_06_eval_baseline.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_06_eval_baseline.json) | `75d5c94` (Nhóm 0, `eval_runner` v1.0) | `gemini-3.8-flash` (chưa `-low`, chưa Mode 3) | `0.8333` (`15/18`) | `19.50s / 35.02s` | `27,797 / 43,345` (`64.13%`) | Judge `14/15 REVIEW_PENDING` (`93.3%` timeout); Weekly `18/18` fallback nhưng báo ảo `faithfulness=1.0` | `eval_runner` v1 chưa tách `REVIEW_PENDING` và gộp `faithfulness=1.0` của fallback vào tổng. |
| [baseline_normalized_metrics.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/baseline_normalized_metrics.json) | `f123334` (Nhóm 4, `eval_runner` v2) | `gemini-3.8-flash` (mặc định `HIGH`), chưa Nhóm 1/2 | `0.0000` (`0/18`) | `35.02s / 35.02s` | `0` *(timeout mất telemetry)* | Judge `18/18 SKIPPED`; Weekly `18/18` timeout → fallback; `0/0` valid injection (`4 excluded`) | Đụng trần `35s` trên `16 TIMEOUT`, `1 SCHEMA_MISMATCH`, `1 GATEWAY_ERROR` ở Decomposer + `18 TIMEOUT` ở Weekly. |
| [eval_old_config_new_runner.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/eval_old_config_new_runner.json) | Cùng `eval_runner` v2 (`8f97544`) | Cấu hình cũ (`gemini-3.8-flash` base, chưa `-low`) chạy trên harness mới | **`0.4444` (`8/18`)** | `35.02s / 46.16s` | `71,460 / 90,010` (`79.39%`) | Judge `5/8` timeout (`62.5%`); Weekly `18/18` LLM (`faithfulness=1.0`); `3/3` injection valid (`1 excluded`) | Đối chứng công bằng nhất trên cùng `eval_runner` v2: cấu hình cũ vẫn `10/18` Decomposer timeout (`55.6%`) và `79.39%` thinking tokens. |

---

### 8.2. Phân bố điểm Judge trên 54 runs & Hiệu chuẩn trên 16 Proposal xấu

Số liệu từ [exp_09_judge_and_quality_ab.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_09_judge_and_quality_ab.json) (`part_2a` và `part_2b`):

1. **Phân bố điểm Judge trên 54 runs hợp lệ (`group7_eval_run_{1,2,3}.json`):**
   - `54/54 PASSED` (`100.0%`), `0 NEEDS_REVIEW`, `0 REVIEW_PENDING`, `0 SKIPPED`.
   - Thống kê điểm: `min = 95.0`, `median = 97.5`, `p95 = 100.0`, `max = 100.0`, `mean = 97.5` (chính xác `27` runs đạt `95.0` và `27` runs đạt `100.0`).
2. **Hiệu chuẩn Judge trên 16 proposal cố tình làm xấu (5 nhóm lỗi):**
   - **Nhóm lỗi kiểm thử:** `outcome_coverage_gap` (3 ca), `dependency_cycle_or_inverted_order` (3 ca), `duration_exceeds_120m` (3 ca: `150m`, `180m`, `240m`), `unmeasurable_criteria` (3 ca), `off_domain_or_level_mismatch` (4 ca).
   - **`judge_low` (`gemini-3.8-flash-low`, timeout `8.0s`):**
     - Bắt được **`13/16` (`81.25%`)** (`NEEDS_REVIEW`), `0/16` vượt `8.0s` (`p50 = 5.21s`, `p95 = 6.34s`, `max = 7.54s`), điểm `min = 0.0 / median = 25.0 / p95 = 75.0 / max = 75.0 / mean = 28.12`.
     - Bắt **`100%` (`13/13`)** trên 4 nhóm: `outcome_coverage_gap` (`25–35`), `dependency_cycle_or_inverted_order` (`15`), `unmeasurable_criteria` (`35`), `off_domain_or_level_mismatch` (`0`).
     - Bỏ lọt **`3/3` (`0%`)** ở nhóm `duration_exceeds_120m`: `BAD_07_DURATION_150M` (`75.0`, `PASSED`), `BAD_08_DURATION_180M` (`65.0`, `PASSED`), `BAD_09_DURATION_240M` (`75.0`, `PASSED`) — lý do vì Judge phát hiện vấn đề nhưng chỉ gắn mức `WARNING` thay vì `CRITICAL`/`ERROR` (`score < 60`).
   - **`judge_medium` (`gemini-3.8-flash-medium`, budget `25.0s` thử nghiệm):**
     - Bắt được **`15/16` (`93.75%`)**, bắt thêm `BAD_08_DURATION_180M` (`55.0`, `NEEDS_REVIEW`) và `BAD_09_DURATION_240M` (`50.0`, `NEEDS_REVIEW`), chỉ bỏ lọt `BAD_07_DURATION_150M` (`80.0`, `PASSED`).
     - Tuy nhiên **`15/16` (`93.75%`)** vượt ngưỡng `8.0s` (`p50 = 11.02s`, `p95 = 17.12s`, `max = 23.72s`).
   - **Ý nghĩa vận hành:** Trong pipeline thật, lỗi `duration > 120m` đã bị Tier 2 Deterministic Validator (`30 <= estimated_minutes <= 120`) chặn cứng trước khi tới Judge; với các lỗi sư phạm thuộc thẩm quyền Judge, `judge_low` bắt **`13/13` (`100%`)** mà không bị timeout ở `concurrency=1`.

---

### 8.3. So sánh chất lượng `-low` vs `-medium` trên 5 mục tiêu / 10 lộ trình tách khỏi timeout

Thực nghiệm `part_3_quality_ab_low_vs_medium` trong [exp_09_judge_and_quality_ab.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_09_judge_and_quality_ab.json) cấp `timeout_budget_seconds = 120.0s` cho cả `LOW` (`gemini-3.8-flash-low`) và `MEDIUM` (`gemini-3.8-flash-medium`) trên 5 mục tiêu đa dạng, sau đó chấm chéo tất cả 10 lộ trình bằng cả `judge_low` lẫn `judge_medium`:

- **Tổng hợp theo arm (`5` mục tiêu/arm):**
  - **Tỷ lệ qua Tier 1+2:** `5/5` (`100%`) ở cả `LOW` và `MEDIUM`.
  - **Độ trễ & Thinking tokens:** `LOW` Planner `p95 = 40.07s` (`max 41.96s`), Decomposer `p95 = 114.94s` *(gộp toàn bộ 4–6 milestones trong 1 prompt)*, **`0` thinking tokens**; `MEDIUM` Planner `p95 = 58.33s` (`max 65.04s > 55s`), Decomposer `p95 = 87.90s`, tiêu tốn **`18,868` thinking tokens** (`6,033` Planner + `12,835` Decomposer).
  - **Quy mô cấu trúc:** `LOW` trung bình `5.2` milestones / `19.2` tasks vs `MEDIUM` `5.0` milestones / `23.8` tasks.
  - **Điểm Judge chấm chéo:** `LOW` đạt `judge_low_mean = 96.8` / `judge_medium_mean = 95.8` vs `MEDIUM` đạt `judge_low_mean = 96.8` / `judge_medium_mean = 96.2`.

| Mục tiêu | Arm | Planner (`ms` / `out` / `think`) | Decomposer (`ms` / `out` / `think`) | Milestones / Tasks | `judge_low` | `judge_medium` | Nhận xét chất lượng |
|---|---|---:|---:|---:|---:|---:|---|
| `G1_BEGINNER_PYTHON_FASTAPI` | `low` | `14,972` / `1,386` / `0` | `40,707` / `5,454` / `0` | `5 / 18` | `96.0` (`PASSED`) | `92.0` (`PASSED`) | Chia bước Python→Pydantic→FastAPI→Pytest rõ; đủ `THEORY→PRACTICE→PROJECT`. |
| `G1_BEGINNER_PYTHON_FASTAPI` | `medium` | `22,394` / `2,136` / `924` | `43,616` / `6,292` / `2,599` | `4 / 12` | `100.0` (`PASSED`) | `100.0` (`PASSED`) | Ít task hơn (`12`), tổng hợp gọn; tốn `3,523` thinking tokens. |
| `G2_INTERMEDIATE_SYSTEM_DESIGN_CACHE` | `low` | `32,487` / `3,122` / `0` | `29,610` / `3,601` / `0` | `4 / 12` | `100.0` (`PASSED`) | `96.0` (`PASSED`) | Nhanh gấp ~2× ở Decomposer; phủ đủ caching/sharding/consistency. |
| `G2_INTERMEDIATE_SYSTEM_DESIGN_CACHE` | `medium` | `28,107` / `2,760` / `1,129` | `58,665` / `8,433` / `3,175` | `4 / 16` | `98.0` (`PASSED`) | `95.0` (`PASSED`) | Chi tiết task hơn nhẹ nhưng tốn `4,304` thinking tokens. |
| `G3_ADVANCED_RUST_ASYNC_TOKIO` | `low` | `41,960` / `4,162` / `0` | `50,766` / `6,692` / `0` | `5 / 23` | `98.0` (`PASSED`) | `100.0` (`PASSED`) | Đạt `100.0` ở `judge_medium`; cấu trúc `tokio`/pinning/backpressure chặt. |
| `G3_ADVANCED_RUST_ASYNC_TOKIO` | `medium` | `31,423` / `3,141` / `955` | `82,730` / `11,088` / `1,032` | `6 / 33` | `96.0` (`PASSED`) | `98.0` (`PASSED`) | Tách 33 task chi tiết hơn nhưng `decomposer` chậm `82.7s`. |
| `G4_BEGINNER_IELTS_WRITING` | `low` | `26,482` / `2,345` / `0` | `123,383` / `17,445` / `0` | `6 / 31` | `95.0` (`PASSED`) | `95.0` (`PASSED`) | Cả hai arm đều bị trừ `5` điểm vì thiếu task `REVIEW` riêng hoặc dồn lịch. |
| `G4_BEGINNER_IELTS_WRITING` | `medium` | `65,036` / `7,189` / `1,908` | `88,239` / `12,649` / `2,619` | `6 / 32` | `95.0` (`PASSED`) | `98.0` (`PASSED`) | Planner `65.0s > 55s` dù không đổi mức `judge_low` (`95.0`). |
| `G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT` | `low` | `25,592` / `2,169` / `0` | `81,154` / `10,961` / `0` | `6 / 12` | `95.0` (`PASSED`) | `96.0` (`PASSED`) | Tiến độ `THEORY→PRACTICE→PROJECT` đều, cảnh báo dồn 3 task/ngày nghỉ. |
| `G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT` | `medium` | `31,487` / `3,253` / `1,117` | `86,528` / `11,377` / `3,410` | `5 / 26` | `95.0` (`PASSED`) | `90.0` (`PASSED`) | Bị `judge_medium` chấm thấp hơn `low` (`90.0` vs `96.0`) do dồn tải & thiếu `REVIEW`. |

- **Kết luận:** Tách khỏi giới hạn timeout, chất lượng sư phạm giữa `-low` và `-medium` **gần như đồng nhất** (`96.8` vs `96.8` trên `judge_low`; `95.8` vs `96.2` trên `judge_medium`), nên giữ tầng `LOW` là tối ưu về chi phí token và độ trễ dưới trần `55s`.

---

### 8.4. Giải trình `thinking_tokens` Run 2 & hạch toán Quota `completion_tokens`

1. **Vì sao `group7_eval_run_2.json` có `thinking_tokens_total = 0`?**
   - Ở cấu hình `gemini-3.8-flash-low`, model hầu như tắt suy luận nội bộ (`0` thinking tokens trên phần lớn request) và chỉ đôi khi phát sinh lượng nhỏ thoughts ở các case Decomposer phức tạp (`651 / 26,851 = 2.42%` ở Run 1; `0 / 24,714 = 0.00%` ở Run 2; `428 / 25,537 = 1.68%` ở Run 3). Đây là biến thiên ngẫu nhiên thực tế của `0/18` case trên `-low`.
   - Tại commit `8f97544`, [eval_runner.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/eval_runner.py#L957-L964) cũng đã sửa thiếu sót trước đó để cộng đủ `weekly_prompt_tokens`, `weekly_output_tokens`, `weekly_thinking_tokens` vào tổng telemetry.
2. **Xác nhận quota `completion_tokens` luôn bao gồm `thinking_tokens`:**
   - Trong [litellm_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py#L629-L639), `_accumulate_usage()` tính `total_completion_tokens += cand_tokens + thought_tokens` và `total_thinking_tokens += thought_tokens`.
   - Trong [execution_manager.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/application/harness/execution_manager.py#L313-L330), `_commit_once()` tính `billable_completion_tokens = max(int(c_tokens or 0), int(t_tokens or 0))` và gọi `self._quota.commit_reservation(..., completion_tokens=billable_completion_tokens)`. Nhờ đó quota không bao giờ bỏ sót `thinking_tokens`.

---

### 8.5. Trạng thái `EMBEDDING_API_KEY` trong `embedding_adapter` & `.env`

- Tại commit `8f97544`, [embedding_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/embedding_adapter.py#L79-L85) chỉ đọc `settings.embedding_api_key` (`EMBEDDING_API_KEY`), **không** fallback sang `GEMINI_API_KEY` hay `LLM_API_KEY`, và fail-closed với `AI_EMBEDDING_PROVIDER_NOT_CONFIGURED: Missing valid EMBEDDING_API_KEY for embeddings.` khi giá trị rỗng hoặc placeholder.
- **Trạng thái thực tế trên máy hiện tại (kiểm tra tên biến không in secret):** `.env` và `backend/.env` chỉ có `GEMINI_API_KEY` (khác rỗng), **chưa khai báo `EMBEDDING_API_KEY`**. Do đó ở chế độ production không override env, các luồng RAG/Embedding sẽ **fail-closed** cho tới khi người vận hành đặt `EMBEDDING_API_KEY` hợp lệ trong `.env`.

---

### 8.6. Truy vết cơ chế `weekly_faithfulness < 1.0` (`QuantitativeFaithfulnessValidator`)

Kiểm tra trực tiếp [evaluation/domain/services/__init__.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/domain/services/__init__.py#L12-L74), [intelligence.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/application/use_cases/intelligence.py#L779-L799), và [eval_runner.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/ai_evals/eval_runner.py#L965-L989):

1. **`compute_raw_faithfulness` đo trên output LLM thô trước khi sanitize:**
   - Trong `GenerateWeeklyReviewUseCase.execute()` (`intelligence.py:779-784, 899`), `raw_faithfulness` được tính trên bộ 3 chuỗi thô `(s_fb, b_fb, a_rec)` trả về từ LLM so với `allowed_numbers | {0, 1, 2, 3, 7, 100}` (tức `_STRUCTURAL_NUMBERS`), rồi ghi vào `output_payload["quantitative_faithfulness"]`.
   - Trong `eval_runner.py`, fixture `_EvalWeeklyMetricsPort` cung cấp tập số nền gồm `180, 240, 4, 3, 4, 0, 75.0` và `period_days = 8`. Khi LLM diễn giải tự nhiên có kèm 1–2 con số nội suy (ví dụ `60` phút còn lại từ `240 - 180`, hoặc `45` phút/phiên từ `180 / 4`), `raw_faithfulness` ghi nhận `< 1.0`: ví dụ ở `holdout_eval_run_1.json`, `H02_K8S_TF_INTERMEDIATE_TIGHT_B` đạt `0.8462` (`11/13` số khớp) và `H05_APPSEC_INTERMEDIATE_WIDE_B` đạt `0.9231` (`12/13` số khớp); ở `group7_eval_evening.json`, `E01` đạt `0.9412` (`16/17`) và `E03` đạt `0.9231` (`12/13`).
2. **`validate_or_sanitize` thay thế nguyên section vi phạm và giữ nguyên các section đạt `100%`:**
   - Ngay sau bước đo `raw_faithfulness`, `GenerateWeeklyReviewUseCase` gọi `QuantitativeFaithfulnessValidator.validate_or_sanitize` **độc lập cho từng mục** (`strengths_feedback`, `bottlenecks_feedback`, `action_recommendations` tại `intelligence.py:785-798`).
   - Tại `validate_or_sanitize()` (`__init__.py:64-74`): nếu một mục có `matched < total` (chỉ cần 1 số nằm ngoài `allowed_numbers | {0, 1, 2, 3, 7, 100}`), **toàn bộ mục đó** được thay bằng câu fallback tất định tương ứng (`default_strengths` / `default_bottlenecks` / `default_actions`) để đảm bảo độ trung thực đầu ra `1.0` — **không** cắt xóa lẻ từng chữ số trong câu và **không** loại bỏ các mục còn lại đang đạt `100%`.

---

### 8.7. Kết quả Holdout 12 mục tiêu mới × 3 lần (`holdout_planning_12_goals.jsonl`)

Tập holdout gồm **12 mục tiêu hoàn toàn mới** thuộc 12 lĩnh vực (`rust_systems`, `kubernetes_terraform`, `data_engineering`, `flutter_mobile`, `appsec_owasp`, `uiux_design_systems`, `quantitative_python`, `embedded_rtos`, `typescript_nextjs`, `graphql_postgresql`, `mlops`, `ielts_academic`), kèm 2 ca prompt injection (`H03`, `H10`):

| Metric | Holdout Run 1 ([holdout_eval_run_1.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/holdout_eval_run_1.json)) | Holdout Run 2 ([holdout_eval_run_2.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/holdout_eval_run_2.json)) | Holdout Run 3 ([holdout_eval_run_3.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/holdout_eval_run_3.json)) |
|---|---:|---:|---:|
| `pass_at_1` (`passed / total`) | **`1.0000` (`12/12`)** | **`1.0000` (`12/12`)** | **`1.0000` (`12/12`)** |
| `avg_retries` / `post_repair_schema_mismatch` | `0.0` / `0/60 (0%)` | `0.0` / `0/60 (0%)` | `0.0` / `0/60 (0%)` |
| `thinking_tokens` (`% output`) | `795 / 22,519` (`3.53%`) | `2,394 / 25,061` (`9.55%`) | `2,302 / 23,958` (`9.61%`) |
| Pipeline `p50` / `p95` (ms) | `14,723.3` / **`20,412.3`** | `16,125.1` / **`23,111.0`** | `15,369.9` / **`23,966.3`** |
| Decomposer `p95` / `max` (ms) | `14,846.4` / `14,849.1` | `19,535.4` / `20,809.5` | `19,605.0` / `22,071.1` |
| Critics+Judge `p95` / `max` (ms) | `6,289.6` / `8,070.0` | `5,851.8` / `5,857.2` | `5,115.6` / `5,183.8` |
| Judge `PASSED / REVIEW_PENDING` (`avg score`) | **`12 / 0`** (`96.25`) | **`12 / 0`** (`97.92`) | **`11 / 1`** (`GATEWAY_ERROR`; `96.82`) |
| Weekly LLM (`fallback_rate` / `faithfulness`) | `12/12` (`0%` / `0.9637`) | `12/12` (`0%` / `0.9861`) | `12/12` (`0%` / `0.9702`) |
| `injection_isolation` | **`2/2` (`100%`)** | **`2/2` (`100%`)** | **`2/2` (`100%`)** |

---

### 8.8. Kết quả `--concurrency 5` & `--concurrency 10` và Đối chiếu đa khung giờ (`2026-11-16`)

1. **Kiểm tra tải đồng thời (`18` goals):**

| Metric | `concurrency=1` tối (Run evening) | `concurrency=5` ([concurrency_5_eval.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/concurrency_5_eval.json)) | `concurrency=10` ([concurrency_10_eval.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/concurrency_10_eval.json)) |
|---|---:|---:|---:|
| `pass_at_1` (`passed / total`) | `1.0000` (`18/18`) | **`1.0000` (`18/18`)** | **`1.0000` (`18/18`)** |
| `post_repair_schema_mismatch` | `0/90` (`0.0%`) | `0/90` (`0.0%`) | `0/90` (`0.0%`) |
| `thinking_tokens` (`% output`) | `0 / 31,679` (`0.00%`) | `0 / 30,568` (`0.00%`) | `933 / 33,096` (`2.82%`) |
| Pipeline `p50` / `p95` (ms) | `14,249.1` / `16,025.4` | `14,203.2` / `20,661.5` | `15,198.7` / `21,106.7` |
| `stage_latency_stats`: Decomposer `p95` (`max`) | `11,056.9` (`11,777.8`) | `11,835.5` (`14,460.7`) | `14,842.8` (`15,066.4`) |
| `stage_latency_stats`: Critics+Judge `p95` (`max`) | `5,748.9` (`6,870.3`) | `10,607.8` (`14,839.6`) | `11,929.2` (`11,931.8`) |
| `stage_latency_stats`: Weekly `p95` (`max`) | `6,234.1` (`7,039.0`) | `6,581.0` (`6,612.2`) | `6,130.3` (`6,273.3`) |
| Judge `PASSED / REVIEW_PENDING` (`avg score`) | `17 / 1` (`GATEWAY_ERROR`; `97.53`) | `15 / 3` (**`TIMEOUT 16.67%`**; `97.33`) | `17 / 1` (**`TIMEOUT 5.56%`**; `97.35`) |
| `error_category_rates` (`total` error rate) | Judge `GATEWAY_ERROR 5.56%` (`total 1.85%`) | Judge `TIMEOUT 16.67%` (`total 5.56%`) | Judge `TIMEOUT 5.56%` (`total 1.85%`) |
| Weekly LLM (`fallback` / `faithfulness`) | `18/18` (`0%` / `0.9671`) | `18/18` (`0%` / `0.9708`) | `18/18` (`0%` / `0.9486`) |

2. **Đối chiếu 3 khung giờ đo (lưu ý trung thực về phạm vi thời gian):**
   - **Khung 1 (`18:45–18:57 +07:00` ngày `2026-11-16`, `group7_eval_run_1..3.json`):** `18/18` pass@1 (`3/3`), `p95 = 15.49–19.78s`, Judge `18/18 PASSED` (`0%` lỗi).
   - **Khung 2 (`20:52–21:31 +07:00` ngày `2026-11-16`, `exp_09`, `holdout_1..3`, `concurrency_5/10`):** Holdout `12/12` × 3 (`p95 = 20.41–23.97s`, 1 `GATEWAY_ERROR` ở Judge tại Run 3), Concurrency `18/18` (`p95 = 20.66–21.11s`, `3/18` và `1/18` Judge `TIMEOUT` ở ngưỡng `8.0s`).
   - **Khung 3 (`21:37 +07:00` ngày `2026-11-16`, [group7_eval_evening.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/group7_eval_evening.json)):** `18/18` pass@1, `p95 = 16.03s`, Judge `17/18 PASSED` + `1/18 REVIEW_PENDING` (`GATEWAY_ERROR`), Weekly `18/18` (`faithfulness = 0.9671`).
   - **Giới hạn đã biết:** Cả 3 khung giờ đo đều nằm trong **cùng một ngày `2026-11-16`** (`18:45–21:37 +07:00`), **chưa** kiểm chứng lặp lại qua 3 ngày khác nhau.

---

### 8.9. Kết quả kiểm tra toàn diện trong Container Python 3.12 (Mục E)

Chạy trực tiếp trên image `focusflow-backend:latest` (`FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim`) mount repo host vào `/app`, cài `dev` extras vào venv tạm `/tmp/venv312` trong container (không sửa đổi `.venv` hay file nào trên host), kết nối PostgreSQL `:5432` & Redis `:6379` qua `host.docker.internal`:

| Kiểm tra trong Container Python 3.12 | Kết quả | Chi tiết quan sát trực tiếp |
|---|---|---|
| `python --version` | **PASS** | **`Python 3.12.12`** |
| `ruff check .` | **PASS** | `All checks passed!` |
| `ruff format --check .` | **PASS** | `351 files already formatted` |
| `mypy --strict src` | **PASS** | `Success: no issues found in 271 source files` |
| `lint-imports` | **PASS** | `Analyzed 263 files, 746 dependencies. Contracts: 5 kept, 0 broken.` |
| `python scripts/update_prompts_lock.py --check` | **PASS** | `prompts.lock matches live PromptRegistry (12 prompts).` |
| `pytest -q -m "not live_cobhub and not live_embedding"` | **526 passed, 1 failed, 3 deselected** (`63.30s`) | **1 test fail:** `tests/unit/planning/test_phase_b_c_d_improvements.py::test_phase_c_google_genai_proxy_and_three_tier_routing:127` (`AssertionError: assert 'http://host.docker.internal:8045' == 'http://127.0.0.1:8045'`). **Nguyên nhân:** `_rewrite_docker_localhost()` trong [litellm_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py#L75-L83) tự chuyển `127.0.0.1` → `host.docker.internal` khi tồn tại `/.dockerenv` trong container, trong khi unit test chưa mock `os.path.exists` hoặc chấp nhận `host.docker.internal`. |

---

### 8.10. Kiểm tra Timeout `< 1.5 × p95` trên mọi Stage & Khung giờ (Mục F)

Tổng hợp `p95` lớn nhất đo được từ toàn bộ artifact (`group2_measurements.json`, `group5`, `group7`, `group7_evening`, `holdout_1..3`, `concurrency_5/10`, `exp_09`) so với ngưỡng cấu hình hiện tại trong [config.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/config.py#L86-L101):

| Stage / Pipeline | Timeout cấu hình | `p95` lớn nhất đo được (nguồn) | Tỷ lệ `Timeout / p95` | Đạt `>= 1.5×`? | Ghi chú & Đề xuất điều chỉnh |
|---|---:|---:|---:|:---:|---|
| `goal-clarifier` | `15.0s` | `10.16s` (`group2.stage_measurements`) | `1.48×` | Gần đạt (`< 1.5×`) | Nâng nhẹ lên `15.5s–16.0s` (`>= 1.52×`). |
| `goal-clarifier-followup` | `7.5s` | `4.96s` (`group2.stage_measurements`, `max 5.17s`) | **`1.51×`** | **ĐẠT** | Sát biên `1.5×`; cân nhắc `8.0s` (`1.61×`) nếu chạy giờ cao điểm. |
| `learning-milestone-planner` | `50.0s` *(trần `55.0s`)* | `38.39s` (`group2.part_c`) / **`40.07s`** (`exp_09.part_3`, `max 41.96s`) | **`1.25×`–`1.30×`** | **CHƯA ĐẠT (`< 1.5×`)** | `1.5 × 40.07s = 60.1s > 55s` trần SRS; cần prefetch/giới hạn tool rounds hoặc tách theo phase thay vì chỉ tăng timeout tĩnh. |
| `learning-task-decomposer` | `25.0s` *(per attempt)* | **`19.61s`** (`holdout_eval_run_3`, `max 22.07s`; riêng `exp_09.part_3` gộp toàn bộ milestones `114.94s`) | **`1.27×`** | **CHƯA ĐẠT (`< 1.5×`)** | Dùng **dynamic runtime budget** = `min(30.0s, remaining_pipeline_budget - reserve)` (`30/19.61 = 1.53×`) và chia batch theo từng milestone nếu roadmap nhiều milestone. |
| `coverage-prerequisite-critic` | `15.0s` | `10.91s` (`group2.part_c`, `max 11.11s`) | `1.37×` | **CHƯA ĐẠT (`< 1.5×`)** | Cấp ngân sách động `min(16.5s, remaining_budget)` (`16.5/10.91 = 1.51×`) khi Decomposer chạy nhanh. |
| `learner-fit-actionability-critic` | `15.0s` | `10.06s` (`group2.stage_measurements`) | `1.49×` | Gần đạt (`< 1.5×`) | Dùng chung ngân sách Critic động `min(16.5s, remaining_budget)` (`1.64×`). |
| `quality-arbiter` | `14.5s` | `9.74s` (`group2.stage_measurements`, `max 10.15s`) | `1.49×` | Gần đạt (`< 1.5×`) | Tăng nhẹ lên `15.0s` (`1.54×`) hoặc giới hạn theo `remaining_budget`. |
| `pedagogical-quality-judge` | **`8.0s`** | `6.34s` (`exp_09.part_2b`, `concurrency=1`) / **`11.93s`** *(wall khối `critics_judge_parallel` ở `concurrency=10`)* | **`1.26×`** (`c=1`) / **`0.67×`** (`c=10`) | **CHƯA ĐẠT (`< 1.5×`)** | Dưới `concurrency 5/10` phát sinh `3/18` (`16.7%`) và `1/18` (`5.6%`) Judge timeout. Đề xuất nâng lên **`10.0s–12.0s`** hoặc cấp động `min(12.0s, remaining_budget)` trong nhánh `asyncio.gather` cùng Critics. |
| `weekly-review-advisor` | `10.5s` | `7.20s` (`group2.stage_measurements`, `max 7.62s`; `holdout` `6.96s`) | **`1.46×`** | **CHƯA ĐẠT (`< 1.5×`)** | Nâng lên **`11.5s`** (`1.60×` vs `7.20s`), vẫn rất an toàn cho request riêng của Weekly Review. |
| `prove-question-generator` | `8.5s` | `5.72s` (`group2.stage_measurements`, `max 5.81s`) | `1.49×` | Gần đạt (`< 1.5×`) | Nâng nhẹ lên **`9.0s`** (`1.57×`). |
| `prove-mode-grader` | `7.5s` | `5.01s` (`group2.stage_measurements`, `max 5.13s`) | **`1.50×`** | **ĐẠT (biên)** | Cân nhắc **`8.0s`** (`1.60×`) để có biên an toàn hơn khi có jitter. |
| **Schedule Pipeline Total** | **`55.0s`** | **`23.97s`** (`holdout_eval_run_3`) | **`2.29×`** | **ĐẠT** | Luôn giữ trần cứng `AI_HARD_TIMEOUT_SECONDS = 55.0s` theo SRS v1.3. |

- **Kiến trúc Dynamic Runtime Budget khuyến nghị:** Giữ nguyên trần cứng `55.0s` của SRS (`ai_hard_timeout_seconds=55.0`) làm deadline tổng của request/SSE job (`deadline = monotonic() + 55.0`); thay vì cộng dồn cứng timeout từng stage, mỗi stage nhận `min(stage_cap_s, max(floor_s, remaining_deadline - downstream_reserve_s))` (ví dụ `Decomposer` được mở rộng tới `30.0s` nếu đây là bước đầu của `proposal_generation`, còn `Critics` & `Tier 3 Judge` nhận phần dư song song tối đa `12.0s–16.5s` với sàn tối thiểu `ai_min_critic_remaining_seconds=6.0` và `ai_min_judge_remaining_seconds=3.0`). Riêng `learning-milestone-planner` cần tối ưu giảm số vòng tool nối tiếp để `p95` tụt về `< 33s` thay vì vượt trần `55s`.

---

### 8.11. Live Capability Probe `cobhub` & Logging `actual_model_id` (`#8`)

Kết quả từ `part_1_live_capability_probe` trong [exp_09_judge_and_quality_ab.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_09_judge_and_quality_ab.json):

- `probe_cobhub_capabilities()` và `run_startup_ai_probe()` qua `http://127.0.0.1:8045`: `probe_succeeded=true`, `status="ok"`, `schema_enforced_detected=false` (khớp `configured_schema_enforced=false`), `requested_low_model="gemini-3.8-flash-low"`, **`actual_model_id="gemini-3.8-flash-low"`**, `low_model_thinking_tokens=0`, `low_thinking_is_low=true`, `mismatches=[]`.
- Endpoint `GET /health?probe_ai=true`: trả HTTP **`200 OK`**, `status="healthy"`, trường `ai_gateway` phản hồi đầy đủ metadata probe không chứa secret.
- Logging runtime: [litellm_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py#L551-L568,L871-L879) ghi `actual_model_id` (lấy từ `resp.model_version` hoặc model yêu cầu) vào `last_model_used` và sự kiện log `llm_generation_completed`.

---

### 8.12. Quét lịch sử Git (Secret/PII) & Phân tách `cd5989b` thành 7 PR

- **Kiểm tra lịch sử `cd5989b~1..HEAD`:** `0` file `.env` thật được commit (chỉ có `.env.example`); không có API key/secret/PII thật bị lộ (`AIza...` chỉ xuất hiện 1 lần làm chuỗi giả lập trong `test_embedding_adapter.py`, `antigravity-proxy-key` là placeholder test).
- **Phân tách `150` files trong checkpoint `cd5989b` thành 7 PR độc lập** (chi tiết từng đường dẫn xem [checkpoint_pr_breakdown.md](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/checkpoint_pr_breakdown.md)):
  - **PR1 (4 files):** Docs, Plans, SRS & Reports (`ai-prompt-hardening-plan.md`, `live-real-test-report.md`, `prompt-md-decision-metrics.md`, `srs-v1.3.md`).
  - **PR2 (4 files):** DB Migrations `0011–0012` & ORM Models (`user_orm.py`, `planning_orm.py`).
  - **PR3 (23 files):** Shared Kernel AI Harness, `prompts.lock`, `litellm_adapter`, `embedding_adapter`, Docker/env config.
  - **PR4 (37 files):** Planning Domain, `validation_gate/` package, Critics, Clarification Gap Analysis, Use Cases & Presentation.
  - **PR5 (22 files):** Account Calendar/Quota adapters, `WeeklyExecutionMetricsAdapter`, Evaluation Prompts & Intelligence Use Cases.
  - **PR6 (32 files):** Frontend Angular UI, `schema.d.ts`, `ai-sse.service`, wizard dialogs & spec tests.
  - **PR7 (28 files):** Backend unit, integration & AI eval dataset/runner tests.

---

### 8.13. Đối soát Prompt hiện tại (`v2.0.0`) vs Checklist Review trước (Read-only Audit)

Audit nguyên trạng 12 prompt trong [roadmap_skills.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/services/roadmap_skills.py), [prompts.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/application/prompts.py), và [untrusted_context.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/application/harness/untrusted_context.py) (không chỉnh sửa nội dung prompt, `prompts.lock` giữ nguyên 100%):

| Hạng mục Checklist Review trước | Trạng thái | Bằng chứng dòng code / Chi tiết còn thiếu |
|---|---|---|
| **1. Mục Đầu vào (Context, Action-last, chống trùng lặp, tách confidence)** | **ĐÃ LÀM** *(có 1 lưu ý nhỏ)* | - `roadmap_skills.py:322-479` (`build_goal_clarifier_prompt`, `followup`, `milestone_planner`, `task_decomposer`): đưa dữ liệu untrusted/context trước, `"Yêu cầu hành động"` ở cuối, không lặp `known_dimensions`, bỏ yêu cầu tự nhân `beta`.<br>- `roadmap_skills.py:482-669` (`build_pedagogical_judge_prompt`): truyền `learner_level`, `milestones_summary`, rút gọn payload qua `build_compact_judge_payload`.<br>- `prompts.py:111-199`: tách `<milestone_data>`, `<learner_answer>` (**không gửi `confidence`** vào grader), `<learner_reflection>` qua `redact_sensitive_keys`.<br>- *Lưu ý (`CHƯA LÀM`):* `PROPOSAL_SELF_CORRECTION_PROMPT` (`roadmap_skills.py:209-211`) không đính kèm payload cũ nên buộc sinh lại toàn bộ; `build_pedagogical_judge_prompt` dùng `[PROPOSAL_PAYLOAD]` thay vì thẻ XML `<proposal_payload>` (dù nội dung đã qua `sanitize_untrusted_value`). |
| **2. Quy ước ID task, outcome & resource** | **ĐÃ LÀM** | - `roadmap_skills.py:100, 106` (`MILESTONE_PLANNER_SKILL`): `sequence_order` liên tục từ 1, outcomes gán mã `M{sequence_order}-O{index}`.<br>- `roadmap_skills.py:139-146` (`TASK_DECOMPOSER_SKILL`): `task_id` tuần tự `T1, T2, T3...`, `covered_outcome_ids` phủ 100% `M{seq}-O{i}`, tối đa 3 `resource_ids` trích nguyên văn từ tool.<br>- `prompts.py:52-55` (`PROVE_QUESTION_GENERATOR_PROMPT`): đúng 3 ID `q1, q2, q3`. |
| **3. Giới hạn độ dài / Bounds / Range** | **ĐÃ LÀM** *(thiếu bound số task/độ dài văn bản)* | - **Đã làm:** Clarifier tối đa `3` câu (`<= gaps`), tối đa `4` phương án + `'Khác'` (`roadmap_skills.py:72-80`); Follow-up đúng `1` câu (`188`); Planner `estimated_effort_minutes >= 15` (khuyến nghị `60..600`, `108`); Decomposer `30 <= estimated_minutes <= 120`, tối đa `3` `resource_ids`, `max_tool_calls=4` (`129, 142-144`); Weekly `1..3` actions (`prompts.py:100`).<br>- **Chưa làm:** Chưa đặt giới hạn số task tối đa hoặc giới hạn số từ/ký tự cho `title`/`description` trong prompt Decomposer/Planner (khi gộp nhiều milestone ở `exp_09 part_3`, Decomposer sinh tới 31–32 tasks trong 1 call). |
| **4. Rubric Judge / Grader / Critics / Arbiter** | **ĐÃ LÀM 1 PHẦN** | - **Đã làm:** Judge neo 5 mốc `0/40/60/80/100`, nêu `score < 60` hoặc `CRITICAL/ERROR/FAIL` → FAIL, bắt buộc `evidence` + `task_ref` (`roadmap_skills.py:163-173`); Critics/Arbiter yêu cầu `evidence` + `task_ref` xác thực (`227-262`); Prove Grader tách 3 thành phần `0..40`, `0..30`, `0..30`, cấm xuất `status` và không xét `confidence` (`prompts.py:72-80`).<br>- **Chưa làm:** Rubric `PEDAGOGICAL_JUDGE_SKILL` chưa quy định mức `CRITICAL/ERROR` cho task có `estimated_minutes > 120` hoặc `< 30`, khiến `judge_low` chỉ gán `WARNING` (`score 65–75`) và bỏ lọt `3/3` ca `duration_exceeds_120m` trong hiệu chuẩn `exp_09` (`part_2b`). Ngoài ra chưa tinh chỉnh văn phong/rubric sau `exp_09` vì Đợt 2C đóng băng prompt `v2.0.0`. |
| **5. Định nghĩa `FULL_SCOPE` / `FIT_CAPACITY` / `deferred_scope`** | **ĐÃ LÀM** | - `roadmap_skills.py:110-113, 439-440` (`MILESTONE_PLANNER_SKILL`): định nghĩa tường minh `FULL_SCOPE` (`deferred_scope=[]`, bao phủ toàn bộ mục tiêu gốc) và `FIT_CAPACITY` (thu hẹp về phạm vi khả thi theo quỹ thời gian/deadline, `deferred_scope` liệt kê rõ nội dung bị hoãn và không tuyên bố đạt toàn bộ mục tiêu gốc). |
| **6. Quy tắc dữ liệu ngoài / Chống hallucination / Chống injection** | **ĐÃ LÀM** *(có gợi ý cải thiện Weekly)* | - **Đã làm:** Nhúng `UNTRUSTED_DATA_SYSTEM_RULE` (`untrusted_context.py:12-19`) vào 12/12 system prompts; chuẩn hóa NFKC, loại ký tự vô hình, che PII/secret, lọc injection, `html.escape`, trung hòa tổng quát mọi `[...]` giả mạo (`_FAKE_SECTION_HEADER_RE`, `untrusted_context.py:46-57, 95-206`); cấm bịa `concept_id` (`roadmap_skills.py:102-104`), cấm bịa `resource_ids`/URL (`144-145`), cấm nội suy số liệu mới trong Weekly (`prompts.py:98-99`).<br>- **Chưa làm (gợi ý v2.1.0):** `WEEKLY_REVIEW_ADVISOR_PROMPT` dù đã cấm nội suy số, LLM `-low` vẫn thỉnh thoảng tự tính hiệu số/trung bình (`raw_faithfulness = 0.85..0.94`, đang được `QuantitativeFaithfulnessValidator` chặn an toàn); nếu nâng version sau này nên thêm 1 ví dụ phủ định ngắn (không tự trừ `planned - completed`). |
