---
name: focusflow-backend
description: Quy tắc kiến trúc và quy trình làm việc cho backend FocusFlow (Python 3.12, FastAPI, SQLAlchemy 2.0 async, Taskiq, Redis Streams, PostgreSQL 16, Context-First Modular Monolith + Hexagonal). Dùng skill này BẤT CỨ KHI NÀO người dùng viết, sửa, review, debug hoặc thiết kế code/test/migration phía backend của FocusFlow - use case, aggregate, repository, router FastAPI, Taskiq task/sweeper, outbox event, quota AI, cổng kiểm duyệt 3 tầng, LLMProviderPort, auth/JWT, webhook thanh toán, WebCal, Alembic, import-linter - kể cả khi họ không nhắc tên skill hay chỉ nói "thêm API", "thêm endpoint", "thêm task nền", "sửa bug backend", "viết use case", "thêm bảng".
---

# FocusFlow Backend — hướng dẫn cho AI agent (vai trò: Senior Backend Engineer)

FocusFlow: hệ thống lập kế hoạch & thực thi lộ trình tự học thích ứng tích hợp AI (mô hình SRL của Zimmerman: Forethought → Performance → Self-Reflection). Backend là **Context-First Modular Monolith + Hexagonal**, 4 Bounded Context + `shared_kernel`. SRS v1.3 xác định đích 35 bảng; Alembic hiện có 28 bảng, nên luôn kiểm migration trước khi dùng bảng mới.

Skill này tồn tại vì dự án có nhiều ràng buộc kiến trúc được *máy kiểm tra* (import-linter, mypy --strict, CI diff schema). Code "chạy được nhưng sai ranh giới" sẽ làm hỏng CI và mất điểm thiết kế. Hãy đọc kỹ phần "Luật bất khả xâm phạm" trước khi viết bất cứ dòng code nào.

## 0. Quy trình bắt buộc cho mọi tác vụ

1. **Xác định Bounded Context sở hữu** thay đổi (bảng nào thuộc context nào: xem `references/data-model.md`). Một thay đổi chạm 2 context ⇒ dùng `public_api.py` (đọc) hoặc Outbox event (ghi/phản ứng). Không có đường thứ ba.
2. **Tra yêu cầu** trong `references/domain-rules.md` (BUSR, state machine, OS-01..08, ngưỡng số). Nếu yêu cầu mâu thuẫn giữa SRS và ADR → xem `references/spec-conflicts.md`, **áp dụng cách giải quyết đã ghi, và nói rõ với người dùng** bạn đã chọn theo hướng nào. Không tự chế thêm quy tắc nghiệp vụ.
3. **Đọc code hiện có** của context đó (cấu trúc thư mục, pattern đang dùng) trước khi viết; bắt chước pattern sẵn có thay vì phát minh pattern mới.
4. **Viết theo thứ tự từ trong ra ngoài**: domain (thuần Python) → application (use case + ports) → infrastructure (ORM, repo, adapter) → presentation (router, schema, deps). Test domain trước.
5. **Chạy cổng chất lượng** (mục 6) và sửa đến khi xanh. Không báo "xong" khi chưa chạy hoặc không thể chạy — nếu không chạy được, nói rõ phần nào chưa kiểm chứng.
6. **Báo cáo ngắn**: file đã đổi, quyết định đáng chú ý, giả định, việc người dùng cần xác nhận.

Khi yêu cầu mơ hồ ở điểm có thể gây sai nghiệp vụ nghiêm trọng (tiền, quota, xóa dữ liệu, quyền truy cập) → hỏi 1 câu ngắn. Còn lại: nêu giả định và làm.

## 1. Bản đồ kiến trúc (tóm tắt)

```
backend/src/
  shared_kernel/   # UoW, outbox, LLMProviderPort, config, logging, worker
  account/         # auth, profile, availability, quota, billing, learner model
  planning/        # goal, roadmap, RAG, schedule proposal, official schedule
  execution/       # task, DAG, study session, calendar sync
  evaluation/      # proof, review, adaptation, schedule change log
  <context>/{domain,application,infrastructure,presentation}/ + public_api.py
```
Phụ thuộc một chiều: `presentation → infrastructure → application → domain`. Chi tiết, cấu hình import-linter, cây thư mục: `references/architecture-and-layout.md`.

**Lưu ý đánh số UC**: SRS v1.3 dùng UC-01..UC-28. ADR và skill cũ còn dùng 19/25 UC; tra tên UC trong SRS trước khi ghi số. Xem `references/spec-conflicts.md`.

## 2. Luật bất khả xâm phạm (vi phạm = CI đỏ hoặc bug nghiệp vụ)

**Ranh giới**
- Không import chéo giữa `account | planning | execution | evaluation`, trừ `src.<ctx>.public_api` và `shared_kernel`. Cần đọc dữ liệu context khác → gọi Query Port trong `public_api.py` của context đó, nhận DTO bất biến.
- `domain/` chỉ Python thuần: cấm `fastapi, sqlalchemy, taskiq, redis, litellm, pydantic` (nếu repo cho phép pydantic trong domain thì theo repo; mặc định là cấm), cấm I/O, cấm `datetime.now()` trực tiếp — nhận `Clock`/tham số thời gian.
- `application/` không import `fastapi`, `starlette`, `sqlalchemy`, `taskiq`. Chỉ phụ thuộc `Protocol`/ABC và DTO thuần.
- `Depends`/`TaskiqDepends` chỉ xuất hiện trong `presentation/deps.py` (Composition Root). Router và Taskiq task đều gọi **cùng một Use Case** qua factory trong deps.
- Cấm `relationship()` hoặc SQL `JOIN` giữa bảng của 2 context. FK vật lý vẫn giữ ở DDL.

**Giao dịch & sự kiện**
- Command use case chạy trong `async with self.uow:` và kết thúc bằng `await self.uow.commit()`. Repository chỉ `add()/flush()`, **không bao giờ `commit()`**.
- Sự kiện liên context ⇒ aggregate phát domain event → `uow.collect_domain_events(agg)` → UoW ghi `outbox_events` **cùng giao dịch** với dữ liệu nghiệp vụ. Không publish thẳng vào Redis từ use case (dual-write).
- Consumer cross-context phải idempotent: kiểm `event_id` trong `processed_events` trước khi xử lý.
- Sự kiện nội bộ một context dùng `InProcessEventBus`, trong cùng UoW.

**Dữ liệu**
- PK là UUIDv7 sinh ở domain (`uuid6.uuid7()`), không để DB sinh.
- Mọi bảng chỉ được **ghi** bởi context sở hữu. Cột `user_id`/`roadmap_id` trên bảng downstream là *tenant correlation id* để kiểm IDOR O(1) — giữ nguyên, và use case **phải** kiểm `resource.user_id == current_user.id` (NFR-SEC-004) trước khi thao tác.
- Đổi schema ⇒ Alembic migration (async). Không sửa tay `docs/database/schema.sql`; nó được dump lại bằng `scripts/dump_schema.sh` và CI diff với kết quả `alembic upgrade head`.
- `session_tasks.task_id` là `ON DELETE RESTRICT`: không hard-delete Task có lịch sử phiên; chuyển `CANCELLED`.

**AI**
- Mọi lệnh gọi LLM đi qua `LLMProviderPort` (không import SDK nhà cung cấp trong application/domain). Mọi lần gọi **phải** nằm trong vòng đời quota 2 pha `RESERVE → COMMIT | RELEASE/EXPIRE`.
- Output LLM luôn qua Pydantic v2 structured output; văn bản người dùng nhập đưa vào prompt phải bọc `<user_input>…</user_input>` (loại thẻ đóng giả mạo) và qua `PromptSanitizer` (bỏ email, họ tên, thanh toán, mật khẩu).
- AI **không bao giờ** ghi trực tiếp `OfficialSchedule`/đổi trạng thái lộ trình (BUSR-02, BUSR-12). AI chỉ tạo `ScheduleProposal(DRAFT)`; chỉ hành động `Apply` của người học (kèm validate tất định lần cuối) mới ghi vào Official Schedule.
- Kiểm tra ràng buộc cứng (Mode A/B, DAG, overlap) bằng code tất định, không bao giờ bằng LLM.

**Bảo mật**
- Cookie JWT (`HttpOnly; Secure; SameSite=Lax`), access 15 phút, refresh 7 ngày xoay vòng trên Redis (reuse ⇒ thu hồi cả family). Không dùng localStorage, `python-jose`, `passlib`.
- Mật khẩu: `pwdlib[argon2]`. WebCal token: `secrets.token_hex(32)`, chỉ lưu `sha256`. OAuth token Google: mã hóa Fernet/AES-GCM bằng `CALENDAR_ENCRYPTION_KEY`. Webhook thanh toán: `HMAC-SHA256` + `hmac.compare_digest` + khóa lũy đẳng `transaction_ref`.
- Không log password/token/signature/cookie/URL webcal (processor `sanitize_sensitive_data_processor`). Không hard-code secret.
- Route `/api/v1/admin/*` bắt buộc `require_role(ADMIN)` ở presentation **và** kiểm quyền trong use case.

## 3. Quyết định kỹ thuật cần nhớ nhanh

| Chủ đề | Quyết định |
|---|---|
| Async | Mọi thứ `async def`; Taskiq worker dùng chung engine/pool với API, không `asyncio.run`, không `NullPool`. CPU nặng → `asyncio.to_thread()`. |
| Task nền | Taskiq + `RedisStreamBroker` (XREADGROUP/XACK), Redis `--appendonly yes`. `scheduler` **replicas: 1**, `worker` scale N. Payload task chỉ chứa ID nguyên thủy/ISO time. Sweeper dùng `SELECT … FOR UPDATE SKIP LOCKED`. Gọi dịch vụ ngoài: timeout + `SimpleRetryMiddleware` (backoff lũy thừa + jitter). |
| Streaming AI | 2 chặng: `POST` (kèm `Idempotency-Key`, reserve quota) → `202 {job_id}` trong <150ms; `GET .../jobs/{job_id}/stream` SSE với sự kiện `stage, chunk, validation_retry, completed, failed`. Hard timeout LLM 55s (NFR-PERF-001). TTFT mục tiêu ≤ 2.5s. |
| Quota | `SELECT … FOR UPDATE` trên `ai_quotas`; bất biến `used + reserved <= max`; reservation TTL 120s; sweeper 60s. Free 30 lượt/tháng, Premium 300; reset ngày 01. |
| Validation gate | Tier1 Pydantic (block AI 30..120 phút theo SRS v1.3 — xem conflict), Tier2 tất định (`HybridAvailabilityRuleEngine`, `DagCycleValidator`, fail-closed), Tier3 Pedagogical Judge (advisory, timeout ≤5s, fail-open). Retry có cấu trúc tối đa 2 vòng với `ConstraintViolationDTO`; hết retry ⇒ RELEASE quota, không lưu DRAFT. |
| Offline defense | `LLM_PROVIDER=mock`, `PAYMENT_PROVIDER=local_mock`, `CALENDAR_PROVIDER=local_mock` chọn adapter ở composition root. Mọi tích hợp ngoài **phải** có adapter mock tương ứng. |
| Quan sát | `structlog` JSON + `correlation_id` (middleware ASGI, truyền qua Taskiq headers). |

## 4. Khi thêm… (đi thẳng tới tài liệu cần đọc)

- **Endpoint/Use case mới** → `references/code-patterns.md` §Use case, §Router; rồi `references/testing.md`.
- **Task nền / sweeper / consumer sự kiện** → `references/code-patterns.md` §Taskiq, §Outbox; luật lũy đẳng ở mục 2.
- **Gọi LLM / luồng SSE / quota** → `references/ai-and-quota.md`.
- **Bảng/cột/migration** → `references/data-model.md`.
- **Auth, webhook, WebCal, OAuth, log** → `references/security.md`.
- **Quy tắc nghiệp vụ, trạng thái, ngưỡng số** → `references/domain-rules.md`.
- **Thấy SRS/ADR nói khác nhau** → `references/spec-conflicts.md`.

## 5. Phong cách code

- Python 3.12: type hints đầy đủ (`mypy --strict`), `type` alias, `dataclass(frozen=True, slots=True)` cho Value Object/DTO nội bộ. Pydantic v2 chỉ ở presentation, cấu hình (`pydantic-settings`) và Tier 1.
- Aggregate Root giàu hành vi (không anemic): bất biến nằm trong method (`task.complete(now)`, `session.finish(...)`), ném `DomainError` có mã lỗi ổn định.
- Lỗi: domain/application ném exception riêng có `code` (vd `QUOTA_EXHAUSTED`, `VALIDATION_OVERLOAD`, `DEPENDENCY_CYCLE_DETECTED`, `AI_SCHEMA_VALIDATION_ERROR`, `AI_GATEWAY_TIMEOUT`, `AI_RATE_LIMIT_EXCEEDED`); presentation ánh xạ sang HTTP trong một exception handler duy nhất. Không `HTTPException` ngoài presentation.
- Thời gian: lưu UTC (`timestamptz`); "ngày" nghiệp vụ (`scheduled_date`, quá hạn) tính theo `User.timezone` (IANA).
- Tên: `snake_case`, use case là động từ (`ApplyScheduleProposalUseCase`), port kết thúc `Port`, adapter nêu công nghệ (`SqlAlchemyTaskRepository`).
- Không thêm thư viện mới nếu không cần; nếu cần, nêu lý do và kiểm tra tương thích Python 3.12.
- Không comment giải thích điều code đã nói rõ; comment chỉ cho "vì sao" (tham chiếu `BUSR-xx`, `OS-xx`, `ADR-00x` rất hữu ích).

## 6. Cổng chất lượng (chạy trong `backend/`)

```bash
ruff check . && ruff format --check .
mypy --strict src
lint-imports                       # phải "0 broken contracts"
pytest -q                          # unit domain trước, rồi integration; thêm AI eval offline
# Từ gốc repo: bash scripts/quality-gates.sh backend-static|backend-tests
alembic upgrade head               # nếu đụng schema; rồi diff với docs/database/schema.sql
```
Definition of Done cho một tính năng: domain test (kể cả ca biên) + use case test với fake port + (nếu có DB) integration test; kiểm IDOR; kiểm lũy đẳng nếu là consumer/webhook/sweeper; không log dữ liệu nhạy cảm; migration + schema diff xanh; có mock adapter nếu thêm tích hợp ngoài; cập nhật OpenAPI (frontend sinh type từ đó — đổi tên field là breaking change, báo người dùng).

## 7. Những lỗi hay gặp (hãy tự soát trước khi nộp)

- `session.commit()` trong repository; `HTTPException`/`Depends` lọt vào use case.
- Import `src.planning.domain...` từ `account` (dù "chỉ lấy một enum").
- Gọi LLM mà quên reserve quota, hoặc quên RELEASE ở nhánh lỗi/timeout/hủy SSE.
- Quên kiểm `user_id` ⇒ IDOR; trả 403 thay vì 404 làm lộ sự tồn tại tài nguyên của người khác (ưu tiên 404 cho tài nguyên không thuộc user).
- Task quá hạn bị tự động đổi `scheduled_date` (cấm; chỉ gắn cờ + email).
- Sweeper không `SKIP LOCKED`; consumer không ghi `processed_events`; task payload chứa ORM object.
- Hard-delete Task có session; tăng `reschedule_count` khi Domino Shift (cấm — Domino Shift không tăng).
- Dùng `datetime.utcnow()`/`now()` trong domain; so sánh ngày bằng UTC thay vì múi giờ người học.
- Cập nhật hồ sơ `learner_profiles` trực tiếp từ `execution` (phải qua `StudySessionCompletedEvent` → handler của `account`).
