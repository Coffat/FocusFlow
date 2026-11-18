# Báo Cáo Kiểm Thử Thực Tế Toàn Diện (Live Real Test Report) — FocusFlow

**Ngày cập nhật:** 2026-11-16 (`09:44–10:08 +07:00`)  
**Phạm vi:** Backend Python 3.12+ / FastAPI / PostgreSQL 16 (`localhost:5432`) / Redis 7 (`localhost:6379`) / **cobhub gateway (`http://127.0.0.1:8045`) + `gemini-3.8-flash`**  
**Nguyên tắc:** Đo đạc trực tiếp trên hạ tầng và gateway `cobhub` (`http://127.0.0.1:8045`) thật, **tuyệt đối không fallback sang Google API trực tiếp**, không bịa số liệu, không che giấu timeout/validation error/endpoint error, không ghi lộ bất kỳ API key, password, secret hay PII nào.

---

## 1. Chuẩn hóa cấu hình sang `cobhub` & `gemini-3.8-flash`

### 1.1. Các thay đổi đã triển khai & Zero-Mock Scan
- **Cấu hình mặc định & đồng bộ model (`gemini-3.8-flash`):**
  - [config.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/config.py#L56-L66): đặt `llm_provider = "gemini"`, `llm_base_url = "http://127.0.0.1:8045"`, đồng bộ `llm_model`, `llm_model_low`, `llm_model_medium`, `llm_model_high` về `"gemini-3.8-flash"`, giữ `llm_embedding_model = "gemini/gemini-embedding-2"`.
  - [litellm_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py#L150-L228):
    - `_validate_provider_config()` **fail-closed** với `RuntimeError("AI_PROVIDER_NOT_CONFIGURED: Missing LLM_BASE_URL for cobhub gateway.")` khi `llm_provider == "gemini"` mà `llm_base_url` rỗng (bỏ hoàn toàn fallback gọi Google API trực tiếp).
    - `_resolve_candidate_models()` xóa sạch mọi candidate/fallback Google cứng (`gemini-3-flash-*`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3.8-flash-low/medium`), chỉ dùng model cấu hình theo tier (`llm_model_low` / `llm_model_medium` / `llm_model_high`) và thêm `llm_model` làm fallback cấu hình nếu khác tier model (mặc định `"gemini-3.8-flash"`). Giữ rewrite `127.0.0.1` / `localhost` → `host.docker.internal` trong Docker container.
  - [embedding_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/external_ai/embedding_adapter.py#L8-L115):
    - Đọc `self._base_url` từ `settings.llm_base_url` (kèm Docker host rewrite), xóa sạch `GEMINI_FALLBACK_MODELS` (`text-embedding-005`, `gemini-embedding-001`), chỉ dùng `self._model` từ `settings.llm_embedding_model` (`gemini/gemini-embedding-2`), truyền `api_base=self._base_url or None` và fail-closed khi thiếu `llm_base_url` hoặc khi `litellm.aembedding` thất bại.
  - Đồng bộ model mặc định `"gemini-3.8-flash"` trong [docker-compose.yml](file:///Users/vuthang/Documents/FocusFlow/docker-compose.yml#L66-L73), [.env.example](file:///Users/vuthang/Documents/FocusFlow/.env.example#L41-L50), [public_api.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/public_api.py#L167), [user_orm.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/orm/user_orm.py#L279-L301), [quota_facade_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/adapters/quota_facade_adapter.py#L153-L200), [clarification_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/clarification_use_cases.py#L1167-L1193) và các unit/integration test liên quan. Giữ nguyên `GoogleCalendarAdapter`.
- **Zero-Mock Scan (`backend/src/`):**
  - `rg -n "MockLLMAdapter|MockEmbeddingAdapter|MockCalendarAdapter" backend/src/` → **0 kết quả** (`ZERO_MOCK_OK`).
- **Stale Google Model Scan:**
  - `rg -n "gemini-(1\.5|2\.5|3\.0|3\.1|3\.5|3\.6|3-flash)|gemini-3\.8-flash-(high|low|medium)|text-embedding-005|gemini-embedding-001" backend/src/ backend/tests/ docker-compose.yml .env.example` → **0 kết quả**.

### 1.2. ⚠️ Lưu ý quan trọng cho người dùng về file `.env` cục bộ
Theo nguyên tắc an toàn, kiểm thử **không chỉnh sửa file `.env` thật** và chạy với environment overrides trỏ về `cobhub`. Kiểm tra `get_settings()` không override cho thấy `.env` hiện tại của máy vẫn đang giữ cấu hình Google trực tiếp cũ:
- `llm_base_url = ""` (rỗng — sẽ bị `LiteLLMAdapter` và `LiteLLMEmbeddingAdapter` chặn fail-closed với lỗi `AI_PROVIDER_NOT_CONFIGURED: Missing LLM_BASE_URL for cobhub gateway.`)
- `llm_model = "gemini-3.5-flash"` (lệch với `gemini-3.8-flash` ở `llm_model_{low,medium,high}`)

**Các biến người dùng cần tự cập nhật trong `.env` cục bộ (nếu muốn runtime mặc định chạy qua `cobhub`):**
```dotenv
LLM_PROVIDER=gemini
LLM_BASE_URL=http://127.0.0.1:8045
LLM_MODEL=gemini-3.8-flash
LLM_MODEL_LOW=gemini-3.8-flash
LLM_MODEL_MEDIUM=gemini-3.8-flash
LLM_MODEL_HIGH=gemini-3.8-flash
LLM_EMBEDDING_MODEL=gemini/gemini-embedding-2
```
*(Nếu dùng `LLM_API_KEY` riêng cho `cobhub`, giữ nguyên key hợp lệ trong `.env`; không xóa biến Google Calendar OAuth `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `CALENDAR_ENCRYPTION_KEY`).*

---

## 2. Kết quả Static Gates & Contract Checks (sau lần sửa cuối)

| Cổng kiểm tra | Lệnh | Kết quả | Chi tiết đo được |
|---|---|---|---|
| Ruff Lint & Format | `bash scripts/quality-gates.sh backend-static` | **PASS** | `All checks passed!`, `344 files already formatted` |
| Mypy Strict | `bash scripts/quality-gates.sh backend-static` | **PASS** | `Success: no issues found in 271 source files` |
| Import-Linter | `bash scripts/quality-gates.sh backend-static` | **PASS** | `Analyzed 263 files, 736 dependencies` — `Contracts: 5 kept, 0 broken.` |
| Prompt Registry Lock | `cd backend && .venv/bin/python scripts/update_prompts_lock.py --check` | **PASS** | `prompts.lock matches live PromptRegistry (12 prompts).` |
| API Contract (OpenAPI → TS) | `bash scripts/check-api-contract.sh` | **PASS** | `openapi-typescript 7.13.0` sinh `schema.d.ts` trong `98.2ms` |

---

## 3. Kết quả Full Test Suite qua `cobhub` (`http://127.0.0.1:8045`)

- **Lệnh:**
  ```bash
  cd backend && ENVIRONMENT=test EMAIL_BACKEND=console REDIS_URL=redis://localhost:6379/0 \
  RUN_LIVE_GEMINI_SDK_TEST=1 LLM_PROVIDER=gemini LLM_BASE_URL=http://127.0.0.1:8045 \
  LLM_MODEL=gemini-3.8-flash LLM_MODEL_LOW=gemini-3.8-flash \
  LLM_MODEL_MEDIUM=gemini-3.8-flash LLM_MODEL_HIGH=gemini-3.8-flash \
  .venv/bin/pytest -q -rs
  ```
- **Tổng hợp:** **472 passed, 2 failed, 0 skipped** (tổng 474 tests, `38.87s`).
- **Chi tiết 2 test fail:**
  1. `test_live_google_genai_sdk_contract` ([test_prompt_sanitizer_and_llm_port.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/shared_kernel/test_prompt_sanitizer_and_llm_port.py#L606-L634)):
     - **Kết quả thực tế từ cobhub:** `gemini-3.8-flash` gọi tool `search_learning_concepts` thành công và trả JSON ở bước cuối, nhưng fail `pydantic_core._pydantic_core.ValidationError: 3 validation errors for SampleRoadmapOutput` (thiếu `status`, `summary`, `milestones.0.sequence_order`; model tự trả `{'milestones': [{'id': 'milestone-python-fundamentals', ...}]}`).
     - **Nguyên nhân:** Gateway `cobhub` (`http://127.0.0.1:8045`) chấp nhận `response_mime_type="application/json"` nhưng **không enforce `response_json_schema`** ở phía proxy, trong khi `_generate_with_google_genai` hiện chỉ truyền `schema_dict` qua `GenerateContentConfig.response_json_schema` mà không chèn JSON Schema vào `final_system_instruction`.
  2. `test_dashboard_summary_active_user_real_data` ([test_dashboard_summary_real_data.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/evaluation/test_dashboard_summary_real_data.py#L268)):
     - **Lỗi pre-existing (không liên quan AI/cobhub):** Fail `AssertionError: assert 1 >= 2` (`streak_days=1`) do chạy lúc `02:45 UTC` (`09:45 +07:00`), khiến `now - timedelta(hours=3)` lùi về `23:45 UTC` ngày hôm trước trong khi [execution_dashboard_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/infrastructure/adapters/execution_dashboard_adapter.py#L164-L188) nhóm ngày theo `.date()` UTC.

---

## 4. Kết quả 18-Goal `eval_runner` (`trials_per_goal=1`, `live=True`) qua `cobhub`

- **Artifact JSON:** [live_eval_cobhub_report.json](file:///Users/vuthang/.gemini/antigravity/brain/f37afde2-1ddf-4211-8ee6-6401461d20ce/scratch/live_eval_cobhub_report.json)
- **Model & Gateway:** `http://127.0.0.1:8045` + `gemini-3.8-flash` (không fallback Google trực tiếp).

### 4.1. Bảng so sánh Mock Baseline vs Google trực tiếp (`gemini-3.5-flash`) vs `cobhub` (`gemini-3.8-flash`)

| Chỉ số | Mock Baseline (`live=False`) | Google trực tiếp (`gemini-3.5-flash`, lần trước) | **`cobhub` (`http://127.0.0.1:8045`, `gemini-3.8-flash`)** | Nhận xét thực tế qua `cobhub` |
|---|---:|---:|---:|---|
| `pass_at_1` | `1.0` (`18/18`) | `1.0` (`18/18`) | **`0.0556` (`1/18`)** | Chỉ `E09_FRONTEND_ADVANCED_WIDE_A_INJ3` hoàn thành trong budget `35s` |
| `post_retry_recovery_rate` | `1.0` (`18/18`) | `1.0` (`18/18`) | **`0.0556` (`1/18`)** | `16/18` bị `TimeoutError` tại `35.0s`, `1/18` (`E16`) bị `ServerError` (`10.37s`) |
| `avg_retries` | `0.0` | `0.0` | **`0.0`** | Timeout/ServerError dừng ở attempt 1 của `ProposalValidationGateOrchestrator` |
| `prompt_tokens_total` | `2,304` | `50,544` | **`1,093`** | Chỉ tính 1 case thành công (`E09`) |
| `output_tokens_total` | `4,608` | `38,690` | **`3,177`** | Chỉ 1 case (`E09`: `3,177` output tokens) |
| `thinking_tokens_total` | `0` | `19,665` | **`1,947`** | `E09` tiêu tốn `1,947` thinking tokens (`61.3%` tổng output tokens) |
| `latency_p50_ms` | `9.675 ms` | `9,243.957 ms` | **`35,017.572 ms`** | Đụng trần `call_timeout=35.0s` của `LiteLLMAdapter` |
| `latency_p95_ms` | `13.523 ms` | `29,093.508 ms` | **`35,020.554 ms`** | Đụng trần `35.0s` |
| `judge_timeout_rate` | `0.1667` | `0.3333` (`6/18`) | **`1.0` (`1/1` có proposal)** | `E09` vào Tier 3 Judge vượt ngưỡng `8.0s` → fail-open `REVIEW_PENDING` (`17/18` là `SKIPPED_NO_PROPOSAL`) |
| `weekly_fallback_rate` | `0.2222` | `0.0` (`0/18`) | **`1.0` (`18/18`)** | Tất cả 18/18 `GenerateWeeklyReviewUseCase` timeout ở `25.0s` (`LOW` tier `final_call_timeout`) → fallback tất định an toàn |
| `weekly_faithfulness_avg` | `1.0` | `1.0` | **`1.0`** | Fallback tất định giữ nguyên 100% độ trung thực số liệu |
| `injection_isolation_rate` | `1.0` (`4/4`) | `1.0` (`4/4`) | **`1.0` (`4/4`)** | Không có substring injection lọt ra ở cả 4 case injection (`E03`, `E06`, `E09`, `E14`) |

---

## 5. Kết quả Live Smoke Check qua `cobhub` (12 Production Prompts + Embedding)

Chạy [run_live_smoke.py](file:///Users/vuthang/.gemini/antigravity/brain/f37afde2-1ddf-4211-8ee6-6401461d20ce/scratch/run_live_smoke.py) qua `http://127.0.0.1:8045` với `gemini-3.8-flash` ([live_smoke_results.json](file:///Users/vuthang/.gemini/antigravity/brain/f37afde2-1ddf-4211-8ee6-6401461d20ce/scratch/live_smoke_results.json)):
- **Tổng hợp:** **5/14 PASS, 9/14 FAIL** (không dùng model fallback, `degraded_model_used=False`).

| # | `prompt_id` / Adapter | Trạng thái | `actual_model_id` | Prompt / Output / Thinking tokens | Latency (`ms`) | Kết quả / Lỗi thực tế từ `cobhub` |
|---:|---|---|---|---:|---:|---|
| 1 | `goal-clarifier` | **PASS** | `gemini-3.8-flash` | `750 / 2,769 / 2,276` | `20,816.82` | `questions=2, other_last=True` |
| 2 | `goal-clarifier-followup` | **FAIL** | `gemini-3.8-flash` | `570 / 1,845 / 1,620` | `16,076.27` | Model trả `questions=[]` (`questions=0, other_last=False`) do thiếu ràng buộc schema |
| 3 | `learning-milestone-planner` | **FAIL** | — | — | `30,003.63` | `TimeoutError` (vượt budget `30.0s` của smoke harness) |
| 4 | `learning-task-decomposer` | **FAIL** | — | — | `30,006.16` | `TimeoutError` (vượt budget `30.0s` của smoke harness) |
| 5 | `coverage-prerequisite-critic` | **FAIL** | — | — | `5,034.54` | `ValidationError` cho `CriticQualityLLMOutput`: model trả `{'critic_name': 'coverage...'}` thiếu `status` (`response_json_schema` không được enforce) |
| 6 | `learner-fit-actionability-critic` | **FAIL** | — | — | `25,022.20` | `TimeoutError` (chạm `final_call_timeout=25.0s` của tier `LOW`) |
| 7 | `quality-arbiter` | **FAIL** | — | — | `25,034.94` | `TimeoutError` (chạm `final_call_timeout=25.0s` của tier `LOW`) |
| 8 | `pedagogical-quality-judge` | **PASS** *(fail-open)* | `gemini-3.8-flash` | `0 / 0 / 0` | `8,019.37` | Quá ngưỡng `8.0s` → `tier3_pedagogical_judge_timeout`, fail-open về `REVIEW_PENDING` (`skipped=True`) |
| 9 | `proposal-self-correction` | **PASS** | `gemini-3.8-flash` | `1,141 / 3,987 / 2,694` | `26,556.10` | `tasks=6, dur_30_120=True` |
| 10 | `prove-question-generator` | **FAIL** | — | — | `5,710.31` | `ValidationError` cho `ProveQuestionsLLMOutput`: model trả `{'q1': '...'}` thay vì `{'questions': [...]}` |
| 11a | `prove-mode-grader` (tốt) | **PASS** | `gemini-3.8-flash` | `1,049 / 1,749 / 1,374` | `14,647.32` | `server_score=97, server_status=PASSED` |
| 11b | `prove-mode-grader` (injection/`"a"`) | **PASS** | `gemini-3.8-flash` | `890 / 1,465 / 1,134` | `6,839.47` | `server_score=0, server_status=NEEDS_REVIEW, addressed=[False, False, False]` |
| 12 | `weekly-review-advisor` | **FAIL** | `deterministic-fallback` | — | `25,005.11` | `WEEKLY_REVIEW_TIMEOUT` (`TimeoutError` tại `25.0s`), fallback `faithfulness=1.0` |
| 13 | `LiteLLMEmbeddingAdapter` | **FAIL** | `gemini/gemini-embedding-2` | — | `1,934.40` | `RuntimeError: AI_EMBEDDING_FAILED: Embedding model failed (gemini/gemini-embedding-2): litellm.NotFoundError: GeminiException - ` |

### 5.1. Kiểm tra trực tiếp các endpoint trên `cobhub` (`http://127.0.0.1:8045`)
- `GET /v1beta/models` → **`200 OK`**: danh sách model hỗ trợ `generateContent` và `countTokens`, trong đó có `models/gemini-3.8-flash`, `models/gemini-3.8-flash-high`, `models/gemini-3.8-flash-low`, `models/gemini-3.8-flash-medium`, `models/gemini-3.8-flash-tiered`, `models/gemini-3.5-flash-lite`. Không có bất kỳ model embedding nào trong danh sách.
- `POST /v1beta/models/gemini-embedding-2:embedContent` → **`400 Unsupported method: embedContent`**.
- `POST /v1beta/models/gemini-embedding-2:batchEmbedContents` → **`400 Unsupported method: batchEmbedContents`**.
- `POST /v1/embeddings` → **`404`** (empty body).

---

## 6. Trạng thái tích hợp ngoài & Giới hạn kiểm thử

1. **Google Calendar OAuth & Webhook:** `GoogleCalendarAdapter` được giữ nguyên hoàn toàn. Không test OAuth callback/webhook end-to-end với Google thật trong CLI vì cần đăng nhập trình duyệt và public HTTPS URL.
2. **Payment Webhook (SePay):** `payment_provider="mock"` (chưa có router thanh toán production trong `account/presentation/`).
3. **Mailpit / SMTP:** Chạy suite với `EMAIL_BACKEND=console` do không bật container Mailpit trên `:1025`.

---

## 7. Chẩn đoán nguyên nhân & Khuyến nghị tiếp theo

1. **`cobhub` không enforce `response_json_schema` trên `/v1beta/...:generateContent`:**
   - Bằng chứng: `test_live_google_genai_sdk_contract`, `goal-clarifier-followup`, `coverage-prerequisite-critic`, `prove-question-generator` đều nhận JSON hợp lệ về mặt cú pháp nhưng sai tên trường so với Pydantic schema.
   - **Khuyến nghị:** Trong `LiteLLMAdapter._generate_with_google_genai`, khi `schema_dict` khác rỗng, chèn JSON Schema (hoặc tóm tắt schema) vào `final_system_instruction` tương tự nhánh `acompletion` để model luôn thấy rõ tên trường bắt buộc ngay cả khi proxy bỏ qua `response_json_schema`.
2. **Độ trễ `gemini-3.8-flash` trên `cobhub` vượt timeout hiện tại (`25s` / `35s`):**
   - Bằng chứng: ngay cả ở `thinking_level="LOW"`, `gemini-3.8-flash` trên `cobhub` sinh `1,134–2,694` `thinking_tokens` mỗi lượt và mất `15–35+ giây`, gây `16/18` timeout ở `eval_runner` và `4/13` LLM timeout ở smoke check.
   - **Khuyến nghị:** Kiểm tra cấu hình thinking budget trên `cobhub` (ví dụ truyền `thinking_budget` nhỏ hơn cho `LOW`/`MEDIUM` nếu `cobhub` hỗ trợ, hoặc nâng `final_call_timeout` lên `50s` phù hợp `AI_HARD_TIMEOUT_SECONDS=55` cho tác vụ nặng như `learning-milestone-planner` và `learning-task-decomposer`, ngoại trừ Tier 3 Judge vẫn giữ fail-open `8.0s`).
3. **`cobhub` chưa hỗ trợ endpoint Embedding (`400 Unsupported method` / `404`):**
   - **Khuyến nghị:** RAG `LiteLLMEmbeddingAdapter` hiện fail-closed đúng thiết kế khi chạy qua `cobhub` (`http://127.0.0.1:8045`). Nếu cần chạy RAG embedding thật trên môi trường dùng `cobhub`, cần bổ sung route `:embedContent` / `/v1/embeddings` trên gateway `cobhub` hoặc tách riêng `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` cho embedding provider.
4. **Biên ngày UTC vs Timezone người dùng ở `ExecutionDashboardAdapter`:**
   - `test_dashboard_summary_active_user_real_data` tiếp tục fail khi chạy trong khung `07:00–10:00 +07:00` (`00:00–03:00 UTC`) do [execution_dashboard_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/infrastructure/adapters/execution_dashboard_adapter.py#L164-L188) nhóm `study_dates` theo UTC `.date()`.
