# Tổng hợp Thực nghiệm Nhóm 0 — Baseline `cobhub` (`gemini-3.8-flash`) & Google AI Studio Embedding

- **Nhánh:** `feat/cobhub-hardening` (commit checkpoint `cd5989b`)
- **Gateway LLM đo kiểm:** `LLM_BASE_URL=http://127.0.0.1:8045` (`cobhub`), chạy **tuần tự** 100% qua helper dùng chung `LiteLLMAdapter.build_google_genai_client` & `LiteLLMAdapter.build_generate_content_config`.
- **Endpoint Embedding đo kiểm:** Google AI Studio mặc định (không qua `cobhub`), dùng `GEMINI_API_KEY` (không fallback `LLM_API_KEY`).
- **Artifacts JSON:**
  - [exp_01_cobhub_baseline.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_01_cobhub_baseline.json)
  - [exp_02_thinking_hypothesis.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_02_thinking_hypothesis.json)
  - [exp_03_schema_enforcement.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_03_schema_enforcement.json)
  - [exp_04_embedding_studio.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_04_embedding_studio.json)
  - [exp_05_judge_ab_experiment.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_05_judge_ab_experiment.json)
  - [exp_06_eval_baseline.json](file:///Users/vuthang/Documents/FocusFlow/docs/experiments/exp_06_eval_baseline.json)

---

## 0.1 — Độ trễ nền `cobhub` (10 call tuần tự tối thiểu)

Prompt: `'Trả về JSON {"ok":true}'`, `model="gemini-3.8-flash"`, `thinking_level="MEDIUM"`, `response_mime_type="application/json"`.

| Chỉ số | Success | `min` | `p50` | `p95` | `max` | `mean` |
|---|---:|---:|---:|---:|---:|---:|
| Latency (ms) | 10/10 | 1,748.2 | 2,528.6 | 4,087.6 | 4,134.9 | 2,689.0 |
| `prompt_tokens` | 10/10 | 9 | 9.0 | 9.0 | 9 | 9.0 |
| `candidate_tokens` | 10/10 | 10 | 10.0 | 10.0 | 10 | 10.0 |
| `thinking_tokens` | 10/10 | 91 | 158.5 | 205.3 | 208 | 152.3 |
| `total_tokens` | 10/10 | 110 | 177.5 | 224.3 | 227 | 171.3 |

**Nhận xét:** Độ trễ mạng + proxy nền của `cobhub` ở mức **~1.75–4.13s** (`p50 ≈ 2.53s`, `p95 ≈ 4.09s`), ngay cả với câu 10 output tokens vẫn phát sinh `91..208` thinking tokens trên `gemini-3.8-flash`.

---

## 0.2 — Giả thuyết Thinking trên `cobhub` (60 call xen kẽ A–F × 10 vòng)

Cùng 1 prompt thật `goal-clarifier` (`ClarificationQuestionsLLMOutput`), chạy round-robin xen kẽ từng vòng 1..10:

| Arm | Model yêu cầu | `thinking_level` gửi | `actual_model_id` | OK | Latency `min / p50 / p95 / max` (ms) | `thinking_tokens` `min / p50 / p95 / max` | `total_tokens` `p50` |
|---|---|---|---|---:|---|---:|---:|
| **A** | `gemini-3.8-flash` | `LOW` | `gemini-3.8-flash` | 10/10 | `21,516 / 24,213 / 28,556 / 29,081` | `1,715 / 2,083.5 / 2,809.5 / 2,859` | 3,648.0 |
| **B** | `gemini-3.8-flash-low` | *Không gửi* | `gemini-3.8-flash-low` | 10/10 | **`7,325 / 9,099 / 11,390 / 11,805`** | **`0 / 149.5 / 313.6 / 314`** | **1,564.0** |
| **C** | `gemini-3.8-flash` | `HIGH` | `gemini-3.8-flash` | 10/10 | `19,299 / 25,919 / 29,909 / 30,455` | `1,444 / 2,419.0 / 2,908.1 / 2,940` | 3,907.0 |
| **D** | `gemini-3.8-flash-high` | *Không gửi* | `gemini-3.8-flash-high` | 10/10 | `21,543 / 23,888 / 28,741 / 28,871` | `1,701 / 2,005.0 / 2,710.5 / 2,872` | 3,552.5 |
| **E** | `gemini-3.8-flash` | *Không gửi* | `gemini-3.8-flash` | 10/10 | `22,361 / 24,623 / 31,310 / 32,541` | `1,731 / 2,122.5 / 3,047.6 / 3,080` | 3,697.5 |
| **F** | `gemini-3.8-flash-tiered` | *Không gửi* | `gemini-3.8-flash-tiered` | 10/10 | `20,671 / 23,605 / 29,218 / 29,305` | `1,642 / 2,143.5 / 2,917.8 / 2,970` | 3,599.5 |

> [!IMPORTANT]
> **Kết luận dứt khoát cho 0.2:**
> 1. Tham số `thinking_config.thinking_level` (`LOW` vs `HIGH` vs không gửi) **KHÔNG có tác dụng trên `cobhub`** đối với `gemini-3.8-flash`: Arm A (`LOW`: `p50=24.21s`, `t_tok=2,083.5`), Arm C (`HIGH`: `p50=25.92s`, `t_tok=2,419`), Arm D (`-high`: `p50=23.89s`, `t_tok=2,005`), Arm E (mặc định: `p50=24.62s`, `t_tok=2,122.5`), Arm F (`-tiered`: `p50=23.60s`, `t_tok=2,143.5`) gần như giống hệt nhau. Log lỗi stream của `cobhub` ở thực nghiệm 0.3 cũng lộ ra `model=gemini-3.8-flash-high` khi gọi `gemini-3.8-flash` — chứng tỏ `gemini-3.8-flash` mặc định map lên tier `high`.
> 2. **Chỉ hậu tố tên model (`-low` / `-medium` / `-high`) mới điều khiển được ngân sách suy nghĩ qua `cobhub`**: `gemini-3.8-flash-low` giảm `thinking_tokens` `p50` **~14 lần** (`2,083.5 → 149.5`, thậm chí 3/10 lượt = `0`), giảm `total_tokens` **~2.3 lần** (`3,648 → 1,564`), và giảm độ trễ `p50` **2.66 lần** (`24.21s → 9.10s`, `p95 = 11.39s`).
> 3. Lưu ý phụ từ `0.2`: Khi không chèn schema vào `system_instruction` (chỉ truyền `response_json_schema`), `schema_valid_count` trên `goal-clarifier` chỉ đạt 3/10..7/10 ngay cả khi HTTP 200.

---

## 0.3 — Enforce Schema qua `cobhub` (5 bài thử × 3 chế độ × 10 lần = 150 call)

Đánh giá bằng `model_validate(parsed)` thuần (không qua `_normalize_schema_and_validate`), `model="gemini-3.8-flash"`, `thinking_level="LOW"`:

| Bài thử | Mode 1: `response_json_schema` only | Mode 2: Compact schema trong `system_instruction` only | Mode 3: Compact schema + `response_json_schema` |
|---|---|---|---|
| **1. `SimpleCheckSchema`** | **0/10 (0%)** *(9/10 sai field, 1 ServerError 500)* | **10/10 (100%)** (`p50=3.01s`) | **10/10 (100%)** (`p50=3.13s`) |
| **2. `SampleRoadmapOutput`** | **0/10 (0%)** *(10/10 `JSONDecodeError`)* | **9/10 (90%)** *(1/10 ServerError 500 stream; `p50=5.25s`)* | **9/10 (90%)** *(1/10 ServerError 500 stream; `p50=5.88s`)* |
| **3. `CriticQualityLLMOutput`** *(prompt thật)* | **0/10 (0%)** *(10/10 sai tên field / enum)* | **10/10 (100%)** (`p50=9.67s`) | **10/10 (100%)** (`p50=9.32s`) |
| **4. `ProveQuestionsLLMOutput`** *(prompt thật)* | **0/10 (0%)** *(7/10 `JSONDecodeError`, 3/10 sai cấu trúc)* | **7/10 (70%)** *(1 ServerError 500, 2 `JSONDecodeError`; `p50=9.01s`)* | **9/10 (90%)** *(1 ServerError 500 stream; `p50=7.83s`)* |
| **5. Luồng 2 lượt `tool -> JSON`** (`FunctionResponse` role=`user`) | **0/10 (0%)** *(10/10 thiếu `status/summary/milestones`)* | **10/10 (100%)** (`p50=4.51s`) | **10/10 (100%)** (`p50=4.11s`) |
| **Tổng cộng** | **0 / 50 (0.0%)** | **46 / 50 (92.0%)** | **48 / 50 (96.0%)** *(48/48 = 100% trên mọi lượt không dính 500 stream)* |

**Kết luận cho 0.3:**
- **`cobhub` không ép `response_json_schema` xuống backend sinh JSON** (Mode 1 đạt **0/50 = 0%** khớp Pydantic thuần, kể cả schema 2 trường `ok: bool, note: str` lẫn luồng `tool -> JSON`).
- **Mode 3** (chèn compact schema spec vào `system_instruction` + giữ `response_json_schema` cho gateway tương thích) đạt **48/50 (96%)** chung cuộc và **100% (48/48)** trên mọi phản hồi không gặp lỗi mạng/stream HTTP 500 của `cobhub`, đồng thời nhanh hơn Mode 2 ở cả Bài 3 (`9.32s` vs `9.67s`), Bài 4 (`7.83s` vs `9.01s`), Bài 5 (`4.11s` vs `4.51s`). Chi phí prompt token tăng rất nhỏ (~`+65..+196` tokens).

---

## 0.4 — Embedding Google AI Studio (không qua `cobhub`)

Danh sách model trả về từ `client.models.list()`: `models/gemini-embedding-001`, `models/gemini-embedding-2`, `models/gemini-embedding-2-preview`.

| Kiểm tra | SDK | Model | Tham số | Kết quả | Dim | L2 Norm (`\|\|v\|\|_2`) | Latency (ms) |
|---|---|---|---|---|---:|---:|---:|
| Prefix chuẩn LiteLLM | `litellm.aembedding` | `gemini/gemini-embedding-2` | mặc định | **OK** | 3072 | `1.0` | 752.2 |
| Thiếu prefix `gemini/` | `litellm.aembedding` | `gemini-embedding-2` | mặc định | **FAIL (`APIConnectionError`)** — rơi vào Vertex ADC | — | — | 9,118.7 |
| Truyền `dimensions=768` | `litellm.aembedding` | `gemini/gemini-embedding-2` | `dimensions=768` | **OK** | **768** | **`1.0`** | 495.8 |
| Truyền `output_dimensionality=768` | `litellm.aembedding` | `gemini/gemini-embedding-2` | `output_dimensionality=768` | **Bị bỏ qua** (ra 3072) | 3072 | `1.0` | 478.5 |
| `task_type=RETRIEVAL_DOCUMENT` | `litellm.aembedding` | `gemini/gemini-embedding-2` | `dimensions=768, task_type="RETRIEVAL_DOCUMENT"` | **OK** | **768** | **`1.0`** | 491.4 |
| `task_type=RETRIEVAL_QUERY` | `litellm.aembedding` | `gemini/gemini-embedding-2` | `dimensions=768, task_type="RETRIEVAL_QUERY"` | **OK** | **768** | **`1.000001`** | 477.9 |
| So sánh SDK trực tiếp | `google.genai` | `gemini-embedding-2` | `output_dimensionality=768`, `task_type` | **OK** | **768** | **`1.0` / `1.000001`** | 521.7–557.3 |
| So sánh model cũ `001` | `google.genai` | `gemini-embedding-001` | `output_dimensionality=768` | OK nhưng **chưa norm L2** | 768 | **`0.588..0.592`** | 491.8–501.3 |

- **Sanity Retrieval (`gemini/gemini-embedding-2` @ 768d, `RETRIEVAL_QUERY` vs `RETRIEVAL_DOCUMENT`):**
  - `sim(query, relevant_doc) = 0.837932` vs `sim(query, other_doc) = 0.627321` → **top-1 chính xác** (margin `+0.2106`).
- **Lưu ý quan trọng cho code `litellm.aembedding` (đã xác minh cả nguồn `litellm`):** `litellm` ánh xạ `dimensions` → `outputDimensionality` và `task_type` → `taskType`; **không** truyền `output_dimensionality` (snake_case) vào `litellm.aembedding` vì sẽ bị drop về `3072`. Bắt buộc giữ prefix `gemini/gemini-embedding-2` và vẫn kiểm tra + chuẩn hóa L2 phòng vệ ở phía ứng dụng.

---

## 0.5 — Tier 3 Pedagogical Judge: Payload gọn (`LOW` vs `MEDIUM` suffix vs Base)

Chạy xen kẽ 5 vòng × 2 proposal (`good_proposal` + `flawed_proposal` có lỗi đảo phụ thuộc `PROJECT` trước `THEORY` và objective mơ hồ) = 10 call/nhánh, giữ đủ `depends_on_task_ids`/`dependencies`, `learning_objective`, `completion_criteria`, `milestones_summary`, `learner_level`, bỏ trường nội bộ thừa, dùng compact schema trong `system_instruction`:

| Nhánh | Model | OK | Phán quyết đúng | `good` PASS | `flawed` FAIL | Tỷ lệ `<= 8s` | Latency `min / p50 / p95 / max` (ms) | `thinking_tokens` `min / p50 / p95 / max` | `total_tokens` `p50` |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| **`LOW_SUFFIX`** | `gemini-3.8-flash-low` | **10/10** | **10/10 (100%)** | 5/5 | 5/5 | **80% (8/10)** | `3,470 / 5,614 / 24,884 / 34,455` | **`0 / 0.0 / 0.0 / 0`** | **1,755** |
| **`MEDIUM_SUFFIX`** | `gemini-3.8-flash-medium` | **10/10** | **10/10 (100%)** | 5/5 | 5/5 | 10% (1/10) | `7,905 / 10,757 / 28,511 / 30,771` | `411 / 755.0 / 1,034.3 / 1,131` | 2,575 |
| **`BASE_MEDIUM`** | `gemini-3.8-flash` | 9/10 *(1 timeout 45s)* | 9/10 (90%) | 4/5 | 5/5 | **0% (0/10)** | `8,552 / 9,968 / 12,569 / 12,892` *(+1 timeout 45s)* | `1,786 / 2,065.0 / 2,482.8 / 2,612` | 3,780 |

**Nhận xét 0.5:**
- `BASE_MEDIUM` (`gemini-3.8-flash`) có **0/10 lượt xong dưới 8s** — giải thích trực tiếp hiện tượng `judge_timeout_rate ≈ 93–100%` ở cấu hình cũ (`TIER3_JUDGE_TIMEOUT_SECONDS = 8.0`).
- `gemini-3.8-flash-low` (`LOW_SUFFIX`) đạt độ chính xác phán quyết **10/10 (100%)** ngang `MEDIUM_SUFFIX`, tiêu tốn **0 thinking tokens**, `p50 = 5.61s` (8/10 lượt đạt `3.47s..6.59s`, chỉ có 2 spike gateway `13.19s` và `34.46s`).

---

## 0.6 — Mốc "TRƯỚC" của Eval 18 Goal tuần tự (`live=True`, `trials_per_goal=1`)

Chạy `eval_runner.run_planning_eval_suite(trials_per_goal=1, live=True)` qua `cobhub` (`model=gemini-3.8-flash`), tổng thời gian chạy tường **977.87s (~16.3 phút)**:

| Metric hiện tại (`eval_runner.py` v1.0) | Giá trị mốc TRƯỚC | Ghi chú quan sát trực tiếp |
|---|---:|---|
| `pass_at_1` | **0.8333 (15/18)** | 3 ca fail (`E01`, `E13`, `E16`) đều chết vì `TimeoutError` tại ngưỡng cứng `35.0s` |
| `post_retry_recovery_rate` | **0.8333 (15/18)** | Không phục hồi ca nào (`avg_retries = 0.0`) |
| `avg_retries` | **0.0** | — |
| `prompt_tokens_total` | **18,803** | 3 ca timeout ghi `0` token (mất telemetry) |
| `output_tokens_total` | **43,345** | Gồm cả thinking tokens |
| `thinking_tokens_total` | **27,797 (64.1% output)** | Tỷ trọng thinking quá cao do `gemini-3.8-flash` mặc định tier HIGH |
| `latency_p50_ms` | **19,499.177 ms** | ~19.5s mỗi scenario |
| `latency_p95_ms` | **35,015.992 ms** | Đụng trần `call_timeout=35.0s` trong `litellm_adapter.py` |
| `judge_timeout_rate` | **0.9333 (14/15)** | 14/15 proposal hợp lệ bị `REVIEW_PENDING` do `tier3_timeout=8.0s`; chỉ `E11` `PASSED` |
| `weekly_fallback_rate` | **1.0000 (18/18)** | 17/18 `TimeoutError` (`WEEKLY_REVIEW_TIMEOUT`) + 1/18 `ValidationError` (`WEEKLY_REVIEW_SCHEMA_ERROR` ở `E16`) |
| `weekly_faithfulness_avg` | **1.0000** | **Ảo 100%** vì thực tế 18/18 đều dùng deterministic fallback |
| `injection_isolation_rate` | **1.0000 (4/4)** | 4 ca injection (`E03`, `E06`, `E09`, `E14`) đều pass Tier 1 & không rò rỉ chuỗi cấm |

*(Ghi chú môi trường: `.env` hiện có `LLM_MODEL=gemini-3.5-flash` nhưng `/v1/models` của `cobhub` không có `gemini-3.5-flash`, chỉ có `gemini-3.5-flash-lite` và `gemini-3.8-flash{,-low,-medium,-high,-tiered}`; ở Nhóm 6 sẽ rà lại `.env.example` và safe config).*

---

## Đề xuất Phương án & Tiêu chí Chấp nhận bằng số cho Nhóm 1–5

### 1. Nhóm 4 (4.1–4.5) — Chuẩn hóa Metric Eval/Smoke (Làm ngay trước Nhóm 1)
- Giữ nguyên kế hoạch tách đủ `judge_passed_rate`, `judge_needs_review_rate`, `judge_review_pending_rate`, `judge_skipped_rate`; tách `weekly_llm_faithfulness_avg` (sẽ là `0.0 / N/A` khi `weekly_fallback_rate = 1.0`, phơi bày đúng thực trạng mốc TRƯỚC) vs `weekly_fallback_faithfulness_avg`; mẫu số rõ cho `injection_isolation_rate`; bảng phân rã `AIErrorCategory` khớp 100% `total_runs`; thêm `--concurrency N` (mặc định `1`).
- **Tiêu chí chấp nhận:** 100% unit test công thức + self-check tổng khớp chi tiết từng dòng pass; `eval_runner` chạy được `--concurrency 1` và `--concurrency 4`.

### 2. Nhóm 1 (1.1–1.5 + 4.6) — Schema Compaction + Targeted Repair + Taxonomy
- **Chốt cấu hình từ 0.3:** `LLM_SCHEMA_ENFORCED_BY_GATEWAY=false` làm mặc định an toàn cho `cobhub` → luôn chèn compact schema spec vào `system_instruction` **và** giữ `response_json_schema` (Mode 3, đạt **48/48 = 100%** trên các lượt không lỗi HTTP 500 stream).
- **Chốt retry & repair:**
  - `default_ai_retry_predicate` retry `TIMEOUT` và `GATEWAY_ERROR` (gồm cả HTTP 500 `Stream interrupted` / 429 / 503 từ `cobhub` ở `litellm_adapter.py`).
  - Repair tối đa **1 lượt** cho `SCHEMA_MISMATCH`: stage không tool tại `AIExecutionManager`, stage có tool ở lượt JSON cuối tại `LiteLLMAdapter` (0 lượt gọi lại tool).
  - `ClarificationFollowupLLMOutput` ép `min_length=1, max_length=1`, fail-safe `release_reservation` và trả `None` nếu vẫn lỗi.
- **Tiêu chí chấp nhận:**
  - Unit test pass 100%.
  - Live `@pytest.mark.live_cobhub` đạt **`>= 4/5` lần liên tiếp** cho mỗi ca: `critic`, `prove-question-generator`, `goal-clarifier-followup`, `test_live_cobhub_gateway_capabilities`.

### 3. Nhóm 2 — Chiến lược Thinking (Suffix Mapping) & Stage Timeouts
- **Chốt chiến lược Thinking từ 0.2 & 0.5:**
  - Ánh xạ qua model suffix trên `cobhub` (`LLM_MODEL_LOW=gemini-3.8-flash-low`, `LLM_MODEL_MEDIUM=gemini-3.8-flash-medium`, `LLM_MODEL_HIGH=gemini-3.8-flash-high` hoặc `gemini-3.8-flash`), **đồng thời** vẫn truyền `thinking_level` tương ứng trong `GenerateContentConfig` cho khả năng tương thích gateway chuẩn.
  - Phân bổ tầng gợi ý:
    - `LOW` (`gemini-3.8-flash-low`): `goal-clarifier`, `goal-clarifier-followup`, `coverage-prerequisite-critic`, `learner-fit-actionability-critic`, `quality-arbiter`, `pedagogical-quality-judge`, `weekly-review-advisor`, `prove-question-generator`.
    - `MEDIUM` (`gemini-3.8-flash-medium`): `learning-milestone-planner`, `learning-task-decomposer`, `proposal-self-correction`, `prove-mode-grader`.
- **Chốt Stage Timeouts từ số đo `p95 × 1.3..1.5`:**
  - `goal-clarifier` / `goal-clarifier-followup` (sync HTTP, `LOW`, `p95=11.39s`): đặt **`16.0s`** (`11.39 × 1.4 = 15.95s`).
  - `coverage-prerequisite-critic` / `learner-fit-actionability-critic` / `quality-arbiter` (`LOW`, Mode 3 `p95 ~10–12s`): đặt **`18.0s`** (song song `gather`, mỗi critic không vượt `18s`).
  - `weekly-review-advisor` (`LOW`, hiện timeout 25s bị 17/18 fail khi chạy `BASE_MEDIUM`, chuyển `LOW` dự kiến `p95 ~8–10s`): đặt **`20.0s`** (thừa đủ cho 1 retry/repair nếu cần).
  - `learning-milestone-planner` / `learning-task-decomposer` (SSE background, `MEDIUM` + tool turn, baseline `p50=19.5s`, `p95 > 35s` ở `BASE`, chuyển `MEDIUM` sẽ giảm mạnh nhưng vẫn có tail): đặt **`35.0s`** cho tool+final mỗi lượt hoặc **`45.0s`** cho `TASK_DECOMPOSER` final JSON turn, với `AI_HARD_TIMEOUT_SECONDS=55.0` (hoặc `60.0` cho SSE background pipeline để không chạm hard cap khi có 1 lần retry).
  - Xóa bỏ `18.0`, `25.0`, `35.0` hardcoded trong `litellm_adapter.py`; nhận `call_timeout` từ stage config qua `AIExecutionManager`.
- **Tiêu chí chấp nhận:**
  - `thinking_tokens` giảm **>= 60%** so với mốc `27,797` ở 0.6.
  - **0/3 lần chạy liên tiếp** chạm timeout trên mọi stage bình thường.
  - `weekly_fallback_rate` giảm từ **`1.0` xuống `<= 0.10`**.

### 4. Nhóm 3 — Embedding riêng qua Google AI Studio
- **Chốt thông số từ 0.4:**
  - `EMBEDDING_PROVIDER=google_ai_studio`, `EMBEDDING_MODEL=gemini/gemini-embedding-2`, `EMBEDDING_DIMENSIONS=768`, `EMBEDDING_BASE_URL=""`.
  - Truyền `dimensions=self.dimensions` (KHÔNG truyền `output_dimensionality` vào `litellm.aembedding`) và `task_type` (`RETRIEVAL_DOCUMENT` khi ingest, `RETRIEVAL_QUERY` khi truy vấn); kiểm tra `len(vec) == 768` và ép chuẩn hóa L2 nếu `abs(||v||_2 - 1.0) > 1e-3`.
  - Kiểm tra DB `knowledge_chunks` read-only trước khi chạy ingest mới.
- **Tiêu chí chấp nhận:** Unit test cô lập `LLM_BASE_URL` vs `EMBEDDING_*` pass 100%; `@pytest.mark.live_embedding` xác nhận `len == 768`, L2 norm ∈ `[0.99, 1.01]`, `provenance_json` đủ metadata, mini retrieval top-1 đạt **`>= 4/5`** truy vấn mẫu.

### 5. Nhóm 5 — Judge Tier 3 Payload gọn + Phán quyết thật
- **Chốt phương án từ 0.5:** Chọn **`gemini-3.8-flash-low` (`LOW_SUFFIX`) + payload rút gọn** (giữ `depends_on_task_ids`/`dependencies`, `learning_objective`, `completion_criteria`, `milestones_summary`, `learner_level`, bỏ trường nội bộ thừa) + Mode 3 compact schema.
- **Chốt timeout Judge:** Với `LOW_SUFFIX`, `p50 = 5.61s` (`80% <= 8s`), nhưng thỉnh thoảng có tail gateway `13.2s` (`p95 = 24.88s` do 1 spike `34.46s`). Đề xuất nâng `TIER3_JUDGE_TIMEOUT_SECONDS` cấu hình từ `8.0s` lên **`12.0s`** (hoặc `15.0s` trong budget còn lại của pipeline SSE) để đạt **>= 90%** ca nhận phán quyết thật mà không chặn pipeline khi hết ngân sách.
- **Tiêu chí chấp nhận:** Trên tập proposal hợp lệ ở eval live, **`>= 80%` (mục tiêu `>= 85%`)** nhận phán quyết thật (`PASSED` / `NEEDS_REVIEW`), giảm `judge_timeout_rate` từ **`0.9333` xuống `<= 0.15`**.
