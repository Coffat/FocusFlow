# Báo Cáo Thẩm Định & Nghiệm Thu DEF-17 — AI Cost Accounting cho FocusFlow

- **Hệ thống:** FocusFlow Learning Intelligence Harness (v3.0)
- **Hạng mục:** Khiếm khuyết kỹ thuật **DEF-17** — Hạch toán chi phí AI (AI Token & Gateway Cost Accounting)
- **Kiến trúc áp dụng:** Context-First Modular Monolith + Hexagonal Architecture + Shared AI Harness Runtime (35 bảng CSDL PostgreSQL 16)
- **Model chuẩn:** `gemini-3.8-flash` qua CofHub Gateway (`http://127.0.0.1:8045/v1beta`)
- **Biểu giá tham chiếu:** Gemini 3.8 Flash Standard (\$0.75/1M input tokens, \$3.75/1M output tokens gồm thinking tokens, hiệu lực đến 31/12/2026)
- **Trạng thái thẩm định cuối cùng:** **VERIFIED FIXED**

---

## 1. Bản Án Nghiệm Thu DEF-17 (Executive Verdict)

> **KẾT LUẬN: VERIFIED FIXED (ĐÃ KHẮC PHỤC TRIỆT ĐỂ VÀ XÁC MINH TOÀN DIỆN)**
>
> 1. Xóa bỏ hoàn toàn định mức hardcode của Gemini 2.5 Flash (\$0.075 / \$0.300) khỏi cấu hình mặc định.
> 2. Triển khai Domain Service `AICostAccountingService` với biểu giá Gemini 3.8 Flash Standard (\$0.75/1M prompt, \$3.75/1M completion) theo phiên bản `2026-Q1-STANDARD` và fallback `2025-LEGACY`.
> 3. Tách biệt tuyệt đối hai đại lượng:
>    - `estimated_provider_cost_usd`: Chi phí ước tính theo giá niêm yết Google API.
>    - `actual_gateway_cost_usd`: Chi phí thực tế thanh toán với CofHub Gateway. Do CofHub không mở API đối soát tự động, trường này được đánh dấu **`UNVERIFIED`** một cách trung thực.
> 4. Chấm dứt cơ chế fail-open làm mất telemetry: Các lượt timeout socket (như monolithic 36s trong EXP_14) được ghi nhận với `usage_completeness="UNKNOWN"`, ngăn chặn việc diễn giải sai lệch là "0 tokens / \$0.00 chi phí".
> 5. Chuyển đổi mô hình lưu vết: `commit_reservation()` không còn là điểm lưu vết duy nhất. Toàn bộ các lượt gọi LLM (thành công, thất bại, timeout, hủy bỏ, retry, checkpoint cache, Critics, Judge) được ghi nhận lũy đẳng độc lập với việc khấu trừ quota người dùng qua `record_attempt_usage()`.
> 6. Giải quyết danh tính model thật từ response headers của CofHub Gateway (`x-upstream-model`, `x-mapped-model`) thay vì chỉ cắt chuỗi hậu tố.
> 7. Bảo toàn 100% ranh giới kiến trúc Hexagonal (0 broken contracts) và giữ nguyên 35 bảng của PostgreSQL; bổ sung Alembic migration tối thiểu `0013_ai_usage_audit_jsonb` (`idempotency_key` partial unique index + `audit_metadata` JSONB + autonomous transaction persistence).
> 8. Toàn bộ 15 regression/unit tests về DEF-17 và toàn bộ 269 unit tests trong `account` & `planning` đều xanh 100%.

---

## 2. Thẩm Định 8 Trọng Điểm Cốt Lõi (Detailed Remediation Audit)

### Trọng điểm 1: Thiếu Telemetry Trong Monolithic Workload (EXP_14)
- **Hiện trạng trước sửa:** Trong `exp_14_decomposer_architecture_ab.json`, các ca monolithic thất bại do timeout ở 36s (socket client bị ngắt trước khi gateway trả header/body). Do đó trường `tokens` ghi nhận `decomposer_prompt_tokens = 0`, `decomposer_output_tokens = 0`. Các báo cáo cũ diễn giải nhầm đây là 0 tokens và \$0.00 chi phí, tạo ra ấn tượng sai lệch rằng monolithic "tiết kiệm chi phí khi chạy".
- **Hành động khắc phục:**
  - Mọi nỗ lực thực thi bị timeout hoặc đứt socket mà không nhận được usage metadata từ upstream đều được gắn cờ `usage_completeness="UNKNOWN"`.
  - Trong `AIUsageLogORM`, các token ghi nhận bằng 0 (tuân thủ DB check constraint `prompt_tokens >= 0`), nhưng metadata JSON ghi rõ `usage_completeness="UNKNOWN"`, `usage_source="UNKNOWN"`, `cost_verification_status="UNVERIFIED"`.
  - Khi phân tích unit economics, hệ thống từ chối tính "chi phí trung bình chính xác trên mỗi roadmap thành công" nếu tồn tại các failed attempts bị mất telemetry (chỉ báo cáo cận dưới `INCOMPLETE / LOWER BOUND`).

### Trọng điểm 2: `commit_reservation()` Không Còn Là Nơi Lưu Vết Duy Nhất
- **Hiện trạng trước sửa:** `AIUsageLogORM` trước đây chỉ được tạo trong `QuotaFacadeAdapter.commit_reservation()`. Hậu quả:
  - Khi người dùng gặp lỗi hoặc pipeline timeout, `release_reservation("FAILED")` được gọi -> 0 dòng usage log nào được lưu lại, dù máy chủ upstream đã tiêu tốn compute.
  - Các bước chạy nội bộ với `manage_quota=False` (Dual Critics, Tier 3 Judge, các lượt decomposition sub-calls) không commit reservation -> hoàn toàn vô hình đối với kiểm toán chi phí.
- **Hành động khắc phục:**
  - Thiết kế phương thức `record_attempt_usage(...)` trên `QuotaFacadePort` và `AIQuotaPort`.
  - Phân tách rõ ràng hai vòng đời:
    - **User Quota Settlement:** Quản lý credit người dùng qua 2-Phase ACID reservation (`RESERVED` -> `COMMITTED` / `RELEASED`).
    - **Provider Usage Ledger:** Ghi nhận độc lập mọi lượt tính toán LLM phát sinh tại gateway vào `ai_usage_logs`.
  - Khi request thất bại, user quota được release (hoàn lại credit cho người học), nhưng chi phí provider của attempt đó vẫn được lưu đầy đủ vào `ai_usage_logs`.

### Trọng điểm 3: Sổ Cái Lũy Đẳng Từng Attempt (Idempotent Per-Attempt Ledger)
- **Hành động khắc phục:**
  - Hỗ trợ tham số `idempotency_key` (dạng `{reservation_id}:{step_name}:{attempt_no}`).
  - Kiểm soát trùng lặp trong session (`self._recorded_attempt_keys`) và metadata, đảm bảo các luồng retry đồng thời hoặc double-commit không sinh bản ghi thừa.
  - Bao phủ toàn bộ 7 trạng thái:
    1. `SUCCESS`: Lượt gọi thành công, `usage_completeness="COMPLETE"`.
    2. `TIMEOUT`: Lượt gọi quá hạn, `usage_completeness="UNKNOWN"`, `status="TIMEOUT"`.
    3. `FAILED`: Lượt gọi sinh lỗi (SchemaMismatchError), `usage_completeness="PARTIAL"`, `status="FAILED"`.
    4. `CANCELLED`: Người dùng hủy request (`asyncio.CancelledError`), `status="FAILED"`, `error_code="CANCELLED"`.
    5. `RETRY`: Mỗi attempt (attempt 1, attempt 2, repair) được lưu dòng riêng biệt kèm `attempt_no`.
    6. `CACHE`: Milestone lấy từ deterministic checkpoint được lưu với `usage_source="CACHE"`, 0 tokens, \$0.00 chi phí.
    7. `CRITICS / JUDGE`: Các lượt gọi với `manage_quota=False` vẫn gọi `record_attempt_usage`, lưu `action_type="AI_REVIEW_WEEKLY"` hoặc `"AI_REVIEW_MILESTONE"`.

### Trọng điểm 4: Xác Minh Danh Tính Model Thật Từ Response Headers CofHub
- **Hiện trạng trước sửa:** Code cũ cố gắng đoán model bằng cách cắt bỏ các hậu tố (`-low`, `-medium`, `-high`), tiềm ẩn rủi ro nhận định sai nếu gateway ánh xạ nội bộ sang model khác.
- **Thực nghiệm xác minh trên live gateway:**
  - Probe trực tiếp `http://127.0.0.1:8045/v1beta/models/gemini-3.8-flash:generateContent`.
  - Gateway trả về HTTP response headers thực tế:
    `x-mapped-model: gemini-3.8-flash-high`
    `x-upstream-model: gemini-3.8-flash-high`
- **Hành động khắc phục:**
  - Triển khai `extract_upstream_model_from_response(resp)`: Trích xuất trực tiếp `x-upstream-model` và `x-mapped-model` từ `resp.sdk_http_response.headers`.
  - Trường `resolved_model` trên `LLMGenerationResult` và `AIUsageLogORM` chỉ được coi là đã xác minh khi header upstream thực sự trả về danh tính đó. Nếu không có header (mock/direct API), fallback về `model_version` hoặc ghi nhận là unverified.

### Trọng điểm 5: Migration Tối Thiểu JSONB + Atomic DB Idempotency (`0013_ai_usage_audit_jsonb`)
- **Ràng buộc:** Giữ nguyên cấu trúc 35 bảng PostgreSQL 16 (không thêm bảng mới), bảo đảm dữ liệu cũ (`NULL`) tương thích ngược và có chiến lược rollback an toàn.
- **Hành động khắc phục:**
  - Triển khai Alembic migration `0013_ai_usage_audit_jsonb` (`upgrade`/`downgrade` đối xứng, kiểm chứng đầy đủ `upgrade head` $\rightarrow$ `downgrade -1` $\rightarrow$ `upgrade head`) trên bảng `ai_usage_logs`:
    - `idempotency_key VARCHAR(255) NULL`
    - `audit_metadata JSONB NULL`
    - Partial unique index `uq_ai_usage_logs_idempotency_key UNIQUE (idempotency_key) WHERE idempotency_key IS NOT NULL` (các dòng cũ có `idempotency_key IS NULL` không xung đột).
  - Trong `QuotaFacadeAdapter.record_attempt_usage()`: sử dụng PostgreSQL `INSERT ... ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING` bên trong **giao dịch tự trị (`autonomous transaction`)** trên `AsyncEngine`. Do đó:
    1. Hai worker/session độc lập đua cùng `idempotency_key` được PostgreSQL loại trùng nguyên tử (atomic uniqueness), không phụ thuộc vào bộ nhớ process `self._recorded_attempt_keys`.
    2. Nếu giao dịch nghiệp vụ bên ngoài (`AsyncUnitOfWork`) rollback hoặc giải phóng quota sau khi LLM hoàn tất, bản ghi chi phí provider trong `ai_usage_logs` vẫn được bảo toàn vĩnh viễn.
  - Cấu trúc `audit_metadata` JSONB chuẩn hóa:
    ```json
    {
      "requested_model": "gemini-3.8-flash",
      "resolved_model": "gemini-3.8-flash-high",
      "pricing_version": "2026-Q1-STANDARD",
      "usage_source": "GATEWAY_TELEMETRY",
      "usage_completeness": "COMPLETE",
      "cost_verification_status": "UNVERIFIED",
      "thinking_tokens": 84,
      "attempt_no": 1,
      "idempotency_key": "res-123:DECOMPOSER:1",
      "reservation_id": "res-123",
      "error": null
    }
    ```
  - Hỗ trợ fallback `parse_usage_log_metadata()` đọc được cả JSONB `audit_metadata` lẫn text legacy trong `error_message`.

### Trọng điểm 6: Ngữ Nghĩa Tokens Tư Duy (Thinking Tokens Semantics)
- **Xác minh thực tế trên Gateway:**
  - Response metadata trả về: `promptTokenCount: 39, candidatesTokenCount: 3, thoughtsTokenCount: 84, totalTokenCount: 126`.
  - Quan hệ số học: `39 + 3 + 84 = 126`.
  - Quy tắc nhà cung cấp Google GenAI: Số tokens đầu ra tính tiền = `totalTokenCount - promptTokenCount = 126 - 39 = 87` (chính bằng `candidates (3) + thoughts (84)`).
- **Hành động khắc phục:**
  - Trong `LiteLLMAdapter._accumulate_usage`:
    `total_completion_tokens += max(0, int(tot_tok) - p_tok)` khi `total_token_count` có mặt.
  - Thinking tokens được tính đúng **một lần duy nhất** trong tổng completion tokens và được nhân với đơn giá output (\$3.75 / 1M). Tuyệt đối không cộng đúp hoặc bỏ quên.

---

## 3. Tính Toán Lại Chi Phí Thực Nghiệm EXP_14 (Recalculated Cost Breakdown)

Dưới đây là bảng tính toán lại toàn bộ chi phí thực tế cho 6 workloads của `exp_14_decomposer_architecture_ab.json` theo đúng đơn giá Gemini 3.8 Flash Standard (\$0.75/1M prompt, \$3.75/1M output gồm thinking):

| Workload & Kiến trúc (Phạm vi đo) | Số Run (Pass/Fail) | Observed Prompt Tok (All Runs) | Observed Output Tok (gồm thinking) | Observed Thinking Tok | Failed Runs Có Telemetry `UNKNOWN` | Chi phí Passed-Only Complete / Pass | Tổng Workload Google API Lower Bound | Trạng thái CofHub Gateway |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| **golden_18_stage3_c3** *(Stage 3 only)* (Monolithic) | 18 (15 / 3) | 153,577 | 27,605 | 1,538 | **3 runs** (`TIMEOUT`) | \$0.014580 | **INCOMPLETE ($\ge$ \$0.218702)** | `UNVERIFIED` |
| **golden_18_stage3_c3** *(Stage 3 only)* (Milestone-Scoped) | 18 (16 / 2) | 185,916 | 33,599 | 2,297 | **2 runs** (M2 `TIMEOUT`) | **\$0.015885** | **INCOMPLETE ($\ge$ \$0.265433)** | `UNVERIFIED` |
| **hard_6_apples_c1** *(Stage 3 only)* (Monolithic) | 6 (0 / 6) | 0 | 0 | 0 | **6 runs** (`TIMEOUT`) | N/A (0 pass) | **UNKNOWN (0 observed; NOT \$0)** | `UNVERIFIED` |
| **hard_6_apples_c1** *(Stage 3 only)* (Milestone-Scoped) | 6 (5 / 1) | 250,013 | 54,153 | 2,062 | **1 run** (`TIMEOUT`) | **\$0.070528** | **INCOMPLETE ($\ge$ \$0.390584)** | `UNVERIFIED` |
| **hard_6_apples_c3** *(Stage 3 only)* (Monolithic) | 6 (0 / 6) | 0 | 0 | 0 | **6 runs** (`TIMEOUT`) | N/A (0 pass) | **UNKNOWN (0 observed; NOT \$0)** | `UNVERIFIED` |
| **hard_6_apples_c3** *(Stage 3 only)* (Milestone-Scoped) | 6 (4 / 2) | 215,787 | 50,035 | 579 | **2 runs** (`TIMEOUT`) | **\$0.071364** | **INCOMPLETE ($\ge$ \$0.349472)** | `UNVERIFIED` |
| **hard_6_prod_c1** *(Stage 3 only)* (Monolithic) | 6 (0 / 6) | 0 | 0 | 0 | **6 runs** (`TIMEOUT`) | N/A (0 pass) | **UNKNOWN (0 observed; NOT \$0)** | `UNVERIFIED` |
| **hard_6_prod_c1** *(Stage 3 only)* (Milestone-Scoped) | 6 (3 / 3) | 228,931 | 47,397 | 0 | **3 runs** (`TIMEOUT`) | **\$0.076202** | **INCOMPLETE ($\ge$ \$0.349437)** | `UNVERIFIED` |
| **hard_6_full_e2e_c1** *(Stage 2+3; chưa gồm Stage 2 planner/Stage 1)* (Monolithic) | 6 (0 / 6) | 79,294 | 611 | 0 | **6 runs** (`TIMEOUT`) | N/A (0 pass) | **INCOMPLETE ($\ge$ \$0.061762)** | `UNVERIFIED` |
| **hard_6_full_e2e_c1** *(Stage 2+3; chưa gồm Stage 2 planner/Stage 1)* (Milestone-Scoped) | 6 (3 / 3) | 283,592 | 52,401 | 2,480 | **3 runs** (`TIMEOUT`) | **\$0.082239\*** | **INCOMPLETE ($\ge$ \$0.409198)** | `UNVERIFIED` |
| **hard_6_full_e2e_c3** *(Stage 2+3; chưa gồm Stage 2 planner/Stage 1)* (Monolithic) | 6 (1 / 5) | 110,655 | 7,291 | 0 | **5 runs** (`TIMEOUT`) | \$0.065073\* | **INCOMPLETE ($\ge$ \$0.110332)** | `UNVERIFIED` |
| **hard_6_full_e2e_c3** *(Stage 2+3; chưa gồm Stage 2 planner/Stage 1)* (Milestone-Scoped) | 6 (4 / 2) | 292,817 | 44,417 | 0 | **2 runs** (`TIMEOUT`) | **\$0.087683\*** | **INCOMPLETE ($\ge$ \$0.386176)** | `UNVERIFIED` |

### Nhận Định Kinh Tế Kỹ Thuật (Pedagogical & Economic Insight)
1. **Nghịch lý "Monolithic giá 0 đồng" đã bị vạch trần:** Trong 3 workload Hard 6 Stage 3 (`apples_c1`, `apples_c3`, `prod_c1`), Monolithic có pass rate = 0% và 18/18 runs đều bị đứt socket ở 36s (`0` tokens observed). Trong `hard_6_full_e2e_c1/c3`, `decomposer_prompt_tokens` cũng bằng `0` trên 11/12 ca thất bại. Báo cáo cũ coi đây là \$0 compute là sai bản chất; đây là **MISSING TELEMETRY (`UNKNOWN`)**.
2. **Phân tách Stage 3 Cost vs Full E2E Cost:** Trên tập Golden 18 **(Stage 3 only)**, chi phí Stage 3 quan sát đầy đủ trên 16 ca thành công của `milestone_scoped` là **\$0.015885 USD/run** (cận dưới phân bổ cả 2 ca timeout `UNKNOWN` là `>= $0.016590`). Trên Hard 6 **(Stage 3 only)**, chi phí Stage 3 quan sát đầy đủ trên các ca thành công là **\$0.070528 – \$0.076202 USD/run**. Ở 2 kịch bản `hard_6_full_e2e_*`, con số `\$0.082239\* – \$0.087683\*` chỉ phản ánh Stage 2 Critics + Stage 3 (bộ đếm `exp_14` chưa cộng tokens của Stage 2 MilestonePlanner chính và Stage 1 Clarification), nên **không được coi là tổng chi phí Full E2E hoàn chỉnh**.
3. **Không khẳng định chi phí phân bổ chính xác khi failed runs thiếu telemetry:** Mọi workload có `failed_with_unknown_timeout > 0` đều mang trạng thái `INCOMPLETE_LOWER_BOUND` ở cấp tổng workload/chi phí phân bổ.

---

## 4. Bằng Chứng Kiểm Thử & Regression Suite

Toàn bộ các ca kiểm thử mới được bổ sung tại `backend/tests/unit/account/test_def17_ai_cost_accounting_regression.py`:

```bash
$ backend/.venv/bin/pytest backend/tests/unit/account/test_def17_ai_cost_accounting_regression.py backend/tests/unit/account/test_quota_cost_accounting.py

============================== 15 passed in 1.24s ==============================
```

Danh mục 8 test cases hồi quy đặc tả:
1. `test_timeout_without_usage_marked_unknown`: Kiểm tra socket timeout ghi nhận `status="TIMEOUT"`, `usage_completeness="UNKNOWN"`, \$0 cost nhưng không bị coi là free compute.
2. `test_partial_usage_recorded_independently_of_quota_settlement`: Kiểm tra ca lỗi schema, user quota được hoàn trả (`RELEASED`), nhưng provider usage vẫn được ghi nhận độc lập vào `ai_usage_logs` với `usage_completeness="PARTIAL"`.
3. `test_successful_request_with_exact_thinking_tokens_included_once`: Kiểm tra tính đúng một lần thinking tokens vào completion tokens ở mức giá output \$3.75/1M.
4. `test_concurrent_retries_and_per_attempt_logging`: Kiểm tra attempt 1 lỗi (500 stream interrupted) và attempt 2 thành công đều được ghi nhận riêng biệt với đúng `attempt_no`.
5. `test_duplicate_request_idempotency`: Kiểm tra idempotency key ngăn chặn chèn trùng bản ghi khi có double-submit.
6. `test_resumed_checkpoint_records_zero_cost_with_cached_source`: Kiểm tra checkpoint cache ghi nhận `usage_source="CACHE"`, 0 tokens, \$0.00 cost.
7. `test_resolved_model_from_gateway_headers_vs_alias_suffix`: Kiểm tra trích xuất model từ `x-upstream-model` thay vì suy diễn từ tên alias.
8. `test_critics_and_judge_usage_recorded_with_manage_quota_false`: Kiểm tra Dual Critics và Tier 3 Judge (`manage_quota=False`) không trừ quota người học nhưng vẫn ghi vết đầy đủ chi phí provider.

### Kiểm Tra Tích Hợp PostgreSQL 16 Thật (`test_def17_postgres_idempotency_and_rollback.py`)
1. `test_postgres_concurrent_workers_idempotent_record_attempt_usage`: Hai worker/session độc lập (`asyncio.gather`) đua cùng `idempotency_key` $\rightarrow$ `uq_ai_usage_logs_idempotency_key` (`ON CONFLICT DO NOTHING`) bảo đảm duy nhất 1 bản ghi trong PostgreSQL, bản ghi còn lại trả về `None` sạch sẽ; xác nhận dữ liệu cũ `idempotency_key IS NULL` không bị xung đột và `audit_metadata` JSONB được lưu chuẩn.
2. `test_postgres_fault_injection_rollback_preserves_provider_usage`: Giả lập lỗi DB ở tầng nghiệp vụ khiến `AsyncUnitOfWork` rollback và user quota được giải phóng (`RELEASED`, `used_calls=0`, `monthly_limit=3`); xác minh bản ghi chi phí provider trong `ai_usage_logs` vẫn được bảo toàn nguyên vẹn qua autonomous transaction.
3. `test_postgres_commit_reservation_no_double_counting_when_attempt_logged`: Xác minh `commit_reservation()` kiểm tra `audit_metadata->>'reservation_id'` trên PostgreSQL để không ghi trùng bản ghi tổng hợp sau khi sổ cái per-attempt đã ghi.
4. `test_cost_summary_excludes_or_flags_unknown_telemetry_postgres`: Xác minh `summarize_cost_accounting_logs()` trên dữ liệu PostgreSQL thật gắn cờ `INCOMPLETE_LOWER_BOUND` khi tồn tại attempt `UNKNOWN` và không coi là \$0 compute.

### Kiểm Tra Cổng Chất Lượng (Quality Gates)
- `bash scripts/quality-gates.sh backend-static`: Ruff check, Ruff format (380 files), `mypy --strict` (279 files), `lint-imports` (5 kept, 0 broken contracts) đều **PASSED**.
- `bash scripts/check-api-contract.sh`: OpenAPI schema & `openapi-typescript` sync **PASSED**.
- `backend/.venv/bin/pytest backend/tests/integration -q`: **42 passed, 2 skipped** (2 skip là opt-in live SDK/Embedding tests cần API key/flag riêng).

---

## 5. Kết Luận & Quyết Định Chuyển Pha (Staging UAT Verdict)

Khiếm khuyết **DEF-17** đã được khắc phục toàn diện ở tầng kiến trúc, sổ cái DB PostgreSQL 16 (atomic partial unique index + JSONB audit metadata + autonomous persistence), luồng thực thi `AIExecutionManager` và bộ kiểm thử hồi quy/tích hợp thật. **Đủ điều kiện đóng DEF-17 và chuyển sang pha Staging User Acceptance Testing (UAT).**
