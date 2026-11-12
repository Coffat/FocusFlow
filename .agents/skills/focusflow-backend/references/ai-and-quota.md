# AI: LLMProviderPort, SSE 2 chặng, Quota 2 pha, Cổng kiểm duyệt 3 tầng

Mục lục: 1. Port & adapter · 2. Quota 2 pha · 3. SSE 2 chặng · 4. Cổng 3 tầng · 5. AI Reschedule · 6. Chịu lỗi (timeout, retry, circuit breaker) · 7. Privacy · 8. Eval harness

## 1. LLMProviderPort

`shared_kernel/application`:
- `stream_structured_output(prompt, response_schema, ...) -> AsyncIterator[StreamChunk]` (luồng SSE).
- `generate_structured_output(prompt, response_schema, ...) -> T` (worker: AI Review, Pedagogical Judge, micro-stepping).

Adapter: `LiteLLMAdapter`/`OpenAICompatibleAdapter` (Gemini, OpenAI, Anthropic, Groq, Ollama/vLLM), `MockLLMAdapter` (kịch bản xác định, chunk với độ trễ 1–2s giả lập, dùng cho pytest/CI/offline defense). Env: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`. Không để tên nhà cung cấp rò vào application/domain. Mọi tính năng AI mới phải chạy được với `MockLLMAdapter`.

Circuit breaker (NFR-AI-002): ≥3 lỗi 5xx/429/timeout liên tiếp trong 60s ⇒ `OPEN`, trả ngay lỗi bảo trì kèm gợi ý lập kế hoạch thủ công. ADR chưa mô tả cách cài; cách làm hợp lý: decorator `CircuitBreakingLLMProvider` bọc port, trạng thái trong Redis (key có TTL) để chia sẻ giữa các worker/replica. Nêu rõ đây là quyết định bổ sung khi triển khai.

## 2. Quota 2 pha (account) — bất biến `used_calls + reserved_calls <= max_calls`

1. **RESERVE** (trước khi gọi LLM, trong 1 giao dịch): `SELECT … FROM ai_quotas WHERE user_id=:uid FOR UPDATE`; nếu `used+reserved < max` ⇒ `reserved += 1`, insert `ai_quota_reservations(status='RESERVED', expires_at=now()+120s)`; ngược lại `QUOTA_EXHAUSTED` (không gọi LLM).
2. **COMMIT** (cùng giao dịch lưu kết quả thành công): `reserved -= 1; used += 1; tokens_consumed += n`; reservation → `COMMITTED`; ghi `ai_usage_logs` (model, prompt/completion tokens, latency_ms, status).
3. **RELEASE** (LLM lỗi, hết 2 retry, timeout 55s, người dùng hủy/ngắt SSE): `reserved -= 1`; reservation → `RELEASED`; ghi `ai_usage_logs` với lỗi. **EXPIRE**: `QuotaSweeperTask` mỗi 60s quét `RESERVED` có `expires_at < now()` (`FOR UPDATE SKIP LOCKED`) → `EXPIRED` và hoàn `reserved`.

Quy tắc: RELEASE/COMMIT lũy đẳng theo `reservation_id` (không giảm hai lần). Mọi nhánh `except`/`finally` của luồng AI phải đảm bảo reservation được đóng. TTL 120s > hard timeout 55s + retry; nếu thay đổi timeout, kiểm TTL. Nâng cấp Premium: `max_calls` 30 → 300. Reset ngày 01 hằng tháng (`used_calls = 0`; không xóa reservation đang `RESERVED`).

Test bắt buộc: 10 request song song khi còn 1 lượt ⇒ đúng 1 thành công, 9 nhận 429/`QUOTA_EXHAUSTED`.

## 3. SSE 2 chặng (áp dụng cho UC-07 milestone và UC-08 schedule proposal, và UC-23)

- **Chặng 1** `POST /api/v1/.../generate` (header `Idempotency-Key`): xác thực → kiểm sở hữu → reserve quota → tạo job → `202 {"job_id": "..."}` trong <150ms. Cùng `Idempotency-Key` ⇒ trả lại cùng `job_id`, không reserve lần hai.
- **Chặng 2** `GET /api/v1/.../jobs/{job_id}/stream` (`text/event-stream`, xác thực bằng cookie, `Cache-Control: no-cache`, `X-Accel-Buffering: no`): sự kiện `stage`, `chunk`, `validation_retry`, `completed`, `failed`. `EventSource` tự reconnect ⇒ kết nối lại **không** được tái kích hoạt LLM hay trừ quota (job idempotent; hỗ trợ `Last-Event-ID` hoặc phát lại trạng thái hiện tại của job).
- Job state lưu bền (DB hoặc Redis có TTL); worker/handler sinh nội dung, endpoint SSE chỉ đọc/stream trạng thái. Không giữ quota reservation phụ thuộc vào sự sống của kết nối SSE (đứt SSE ≠ hủy job; job vẫn kết thúc, hoặc reservation hết TTL và bị sweeper thu).
- Human-in-the-loop 2 cấp: sau Cấp 1 (Milestones) **dừng** chờ người học sửa/Approve; chỉ Approve mới kích hoạt Cấp 2 (Tasks + Schedule Proposal `DRAFT`).

## 4. Cổng kiểm duyệt 3 tầng — `ProposalValidationGateOrchestrator` (application của planning)

Luồng: LLM → Tier1 → Tier2 → Tier3 → lưu `ScheduleProposal(DRAFT)` + COMMIT quota. Vi phạm Tier1/Tier2 ⇒ retry có cấu trúc (tối đa 2 lần, backoff OS-08: 2s/4s, trần 10s, full jitter) bằng prompt chứa `ConstraintViolationDTO` (mã lỗi, ngày, phút vượt, cặp task tạo chu trình). Hết retry ⇒ hủy, RELEASE quota, `AI_SCHEMA_VALIDATION_ERROR`, **không lưu bản nháp vi phạm**. Phát SSE `validation_retry` mỗi lần retry.

- **Tier 1** (Pydantic v2, fail-closed): cấu trúc JSON, độ dài, ISO 8601, `milestone_id` hợp lệ, khối liên tục do AI sinh trong dải cho phép (xem `spec-conflicts.md` — mục Thời lượng — hiện ADR-009 `[15,120]`, SRS v1.3 `30–120`).
- **Tier 2** (tất định, fail-closed): `HybridAvailabilityRuleEngine` — Mode A: tổng phút/ngày ≤ `max_daily_minutes` (dải cấu hình 30 phút–14h/ngày, OS-06); Mode B: mỗi task nằm trong `TimeSlot` thực (đã trừ khoảng bận Google Calendar & lịch các roadmap khác), Soft Overflow ≤ 30 phút **chỉ cho task cuối ngày** và cần cảnh báo + xác nhận khi Apply, cấm overlap tuyệt đối, hỗ trợ khe vắt nửa đêm. `DagCycleValidator` — Kahn/DFS, 0 chu trình, tiền đề xếp trước hậu kế. Xung đột slot giữa nhiều roadmap: EDF theo `target_date` (OS-04).
- **Tier 3** (Pedagogical Judge, advisory, timeout ≤5s, **fail-open**): chỉ gắn `advisory_warnings` vào DRAFT khi timeout/lỗi/cảnh báo nhẹ; "vi phạm nặng khi còn lượt retry" mới kích hoạt retry.

**Apply** (UC-08/09/13/20/21 `<<include>>` UC-12): khi người học bấm Apply, chạy lại Tier 2 tất định lần cuối (trạng thái có thể đã đổi), rồi ghi `OfficialSchedule` theo OS-03 (Merge/Future Shift: giữ nguyên task/phiên `COMPLETED` quá khứ, thay các task chưa hoàn thành), ghi `schedule_change_logs`, phát `OfficialScheduleAppliedEvent`. Roadmap `INITIALIZED → ACTIVE` chỉ khi chưa vượt trần lộ trình ACTIVE của gói (Free 3 / Premium 15).

## 5. AI Reschedule quá hạn (UC-23) — **có mâu thuẫn SRS/ADR**

Đọc `spec-conflicts.md` — mục AI overdue recovery trước khi cài. Mặc định áp dụng SRS v1.3 (mới hơn, và do BUSR-02): tạo `ScheduleProposal(DRAFT)` cho **một** roadmap, đi qua cổng 3 tầng, người học Apply, và `reschedule_count` chỉ tăng khi Apply. Phạm vi: chỉ task chưa hoàn thành của roadmap đó, trừ khung giờ đã bị roadmap khác/lịch ngoài chiếm; tuyệt đối không chạm roadmap/task khác. Tiền điều kiện: có task OVERDUE, `reschedule_count < 3`, còn quota. Consume quota như mọi lệnh AI.

## 6. Chịu lỗi

- Hard timeout 55s cho sinh lộ trình/lịch (NFR-PERF-001, tổng hiển thị ≤60s).
- 429/503/timeout: retry tối đa 2 lần, Exponential Backoff + Full Jitter (2s, 4s, trần 10s — OS-08); thất bại ⇒ RELEASE quota; UI nhận lỗi có cấu trúc kèm lựa chọn "Thử lại" / "Lập kế hoạch thủ công".
- Lỗi/timeout không bao giờ được trừ quota người học (BUSR-10).

## 7. Privacy khi gọi LLM

`PromptSanitizer` trước `LLMProviderPort`: bỏ email, họ tên, thông tin thanh toán, mật khẩu, ghi chú bảo mật. Văn bản tự do bọc `<user_input>…</user_input>` và loại/mã hóa mọi thẻ đóng giả mạo (`</user_input>` do người dùng gõ). Chỉ gửi dữ liệu cần thiết (mục tiêu, năng lực, tóm tắt Key Takeaways). Có unit test: payload gửi LLM không chứa field nhạy cảm; prompt-injection bị cô lập.

AI Review (UC-19): chỉ nhận xét định tính dựa trên số liệu đã tính tất định (UC-18); **không** sửa lịch/lộ trình (BUSR-12); không bịa số liệu — số liệu đi vào prompt là số đã tính, kết quả kiểm bằng schema.

## 8. Eval harness (`tests/ai_evals/`)

JSONL ≥100 kịch bản gồm ca biên: quỹ giờ cực hẹp, Mode B vắt nửa đêm, DAG nhiều nhánh, β_bias cao. Chạy qua `LLMProviderPort` trên nhiều model. Metric: Raw Pass@1, Post-Retry Recovery Rate, và **0 vi phạm lọt Tier 2** (`Zero Hallucinated Overbooking`). Thêm ca regression cho mỗi lỗi AI mới phát hiện.
