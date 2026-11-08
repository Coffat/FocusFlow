# AGENTS.md — FocusFlow

Hướng dẫn cho AI agent làm việc trong repo này. Đọc hết file trước khi sửa code. Chi tiết kỹ thuật nằm trong hai skill (mục 2); file này là bản tóm tắt luôn-bật.

## 1. Dự án

FocusFlow là hệ thống quản lý và điều phối học tập cá nhân hóa thông minh tích hợp AI (**FocusFlow Learning Intelligence Harness — An adaptive AI-powered learning management system**), vận hành theo chu trình 6 bước (*Understand → Plan → Schedule → Adapt → Learn → Improve*) thống nhất với mô hình SRL 3 pha của Zimmerman (*Forethought → Performance → Self-Reflection*).

| Phần | Công nghệ |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async (asyncpg), Alembic, Taskiq + Redis Streams, PostgreSQL 16 (pgvector) |
| Frontend | Angular 21+ (standalone, zoneless, OnPush, Signals), Tailwind CSS v4, PrimeNG v21, Lucide, openapi-typescript |
| Kiến trúc | Context-First Modular Monolith + Hexagonal + Shared AI Harness Runtime. 4 Bounded Context: `account`, `planning`, `execution`, `evaluation`, cùng `shared_kernel`. 35 bảng (12 `account`, 10 `planning`, 5 `execution`, 4 `evaluation`, 4 `shared_kernel`) |
| Hạ tầng | Docker Compose 4 container: postgres, redis, backend (gộp Uvicorn API, Taskiq worker, Taskiq scheduler qua Supervisord), frontend |
| Test | pytest + pytest-asyncio, Vitest, Playwright |

Cấu trúc repo (khớp theo thực tế nếu khác):
```
backend/    src/{shared_kernel,account,planning,execution,evaluation}  tests/  alembic/
frontend/   src/app/{core,shared,features/<9 slice>}
docs/       requirements/ (SRS)  adr/  database/ (schema.sql)  uml/
```

## 2. Skill — đọc trước khi làm

Trước mọi tác vụ, nạp skill tương ứng và làm theo:

- Việc backend (API, use case, domain, repository, Taskiq, migration, AI/quota, auth/bảo mật): skill `focusflow-backend`.
- Việc frontend (component, store, route, form, SSE, timer, UI, test FE): skill `focusflow-frontend`.
- Việc chạm cả hai (thêm tính năng đầu-cuối): nạp cả hai, làm backend trước, regenerate type FE sau.

Nếu skill chưa được cài, đọc trực tiếp `focusflow-*/SKILL.md` và các file `references/` (vị trí do nhóm đặt, ví dụ `.agents/skills/`).

## 3. Nguồn chân lý và cách xử lý mâu thuẫn

1. Yêu cầu nghiệp vụ, hành vi quan sát được, state machine, số Use Case: **SRS v1.3** (`docs/srs/srs-v1.3.md`, `UC-01..UC-28`).
2. Cách làm kỹ thuật (thư viện, kiến trúc, hạ tầng): **ADR-001..010**.
3. Hai nguồn lệch nhau: xem `references/spec-conflicts.md` trong skill, áp dụng cách giải quyết đã ghi, và **nói rõ với người dùng** bạn đã chọn gì, vì sao, tài liệu nào cần cập nhật. Không im lặng chọn.
4. Chỗ SRS/ADR chưa quy định: đề xuất tối thiểu hợp lý, đánh dấu `TODO(spec)`, hỏi người dùng nếu liên quan tiền, quota, xóa dữ liệu hoặc quyền truy cập.

## 4. Luật không được vi phạm (tóm tắt)

**Backend**
- Không import chéo giữa 4 context (trừ `public_api` và `shared_kernel`). Cần dữ liệu context khác thì qua Query Port; cần phản ứng thì qua Outbox event.
- Thứ tự phụ thuộc: `presentation → infrastructure → application → domain`. `domain` thuần Python, không I/O, không `datetime.now()`. `application` không import FastAPI/SQLAlchemy/Taskiq.
- `Depends`/`TaskiqDepends` chỉ ở `presentation/deps.py`. Router và Taskiq task gọi cùng một use case.
- Giao dịch qua `AsyncUnitOfWork`. Repository chỉ `add/flush`, không `commit`. Event liên context ghi `outbox_events` cùng giao dịch. Consumer idempotent qua `processed_events`.
- Không `relationship()` hoặc JOIN giữa bảng của hai context. Mọi tài nguyên phải kiểm `user_id` (IDOR); không thuộc user thì trả 404.
- Mọi lệnh gọi LLM đi qua **Shared AI Harness Runtime** (`LLMProviderPort`, Context Builder, Prompt Registry, Tool/Skill Layer, Guardrail & Verification Layer, Memory Extraction, Observability & Eval) và nằm trong vòng đời quota RESERVE → COMMIT/RELEASE/EXPIRE.
- Phân tách rạch ròi **AI Reasoning vs. Deterministic Scheduling Engine** và **3 thực thể cốt lõi**: (1) **Roadmap** (học gì, thứ tự nào — `estimated_effort`), (2) **Schedule** (học khi nào — `schedule_blocks` với `scheduled_duration`, thay đổi giờ rảnh chỉ chạy lại Schedule Optimization mà không tạo lại Roadmap), (3) **Learner Model** (học như thế nào — `learner_profiles`, `learner_memory_items`, `learner_concept_masteries` lưu giữ xuyên suốt nhiều Roadmap). Ràng buộc cứng kiểm bằng code tất định, không bằng LLM.
- Tài liệu RAG (`knowledge_sources`, `knowledge_chunks`) bắt buộc đóng gói trong thẻ `<untrusted_knowledge_context>` và kiểm tra SSRF khi nạp URL.
- AI chỉ tạo `ScheduleProposal(DRAFT)`. Chỉ hành động Apply của người học mới ghi `OfficialSchedule`.
- Task quá hạn không bị tự dời `scheduled_date`; chỉ gắn cờ và gửi email. Domino Shift không tăng `reschedule_count`.
- Bảo mật: cookie JWT HttpOnly, `PyJWT` + `pwdlib[argon2]`, WebCal token chỉ lưu sha256, OAuth token mã hóa Fernet, webhook `HMAC-SHA256` + khóa lũy đẳng. Không log secret/token/PII.
- Đổi schema bằng Alembic. Không sửa tay `docs/database/schema.sql`.

**Frontend**
- Standalone + OnPush + zoneless; control flow `@if/@for(track)/@switch/@defer`; state bằng signals (không NgRx).
- Kiểu API chỉ lấy từ `schema.d.ts` (openapi-typescript); không viết tay interface cho dữ liệu API. Không `any`.
- Không lưu token trong JS/localStorage; `withCredentials` cho HttpClient và `EventSource`.
- Component phức tạp dùng PrimeNG; bố cục dùng Tailwind; màu qua biến ngữ nghĩa; hỗ trợ dark mode.
- A11y (Lighthouse ≥ 90) và responsive 375–1024px là yêu cầu, không phải bổ sung.
- UI không auto-apply bản nháp AI, không tự dời lịch quá hạn; cảnh báo Soft Overflow phải được xác nhận.
- Timer tính từ mốc thời gian, không đếm tick; EventSource và interval phải đóng khi destroy.

## 5. Quy trình làm việc

1. Hiểu yêu cầu, xác định context/slice và UC liên quan. Mơ hồ ở điểm rủi ro cao thì hỏi một câu ngắn; còn lại nêu giả định rồi làm.
2. Đọc code lân cận, bắt chước pattern sẵn có. Không phát minh pattern mới khi đã có.
3. Làm thay đổi nhỏ, tập trung. Không refactor lan man ngoài phạm vi yêu cầu; nếu thấy vấn đề ngoài phạm vi, ghi chú lại thay vì sửa.
4. Viết test cùng lúc với code (domain trước). Bug mới thì viết test tái hiện trước khi sửa.
5. Chạy cổng chất lượng (mục 6). Không báo "xong" khi chưa chạy; nếu không chạy được, nói rõ phần nào chưa kiểm chứng.
6. Báo cáo ngắn: file đã đổi, quyết định đáng chú ý, giả định, việc cần người dùng xác nhận.

## 6. Lệnh kiểm tra

Backend (`backend/`):
```bash
ruff check . && ruff format --check .
mypy --strict src
lint-imports            # phải 0 broken contracts
pytest -q
alembic upgrade head    # khi đổi schema; rồi diff với docs/database/schema.sql
```

Frontend (`frontend/`):
```bash
npm run api:gen         # khi backend đổi OpenAPI
npx ng lint
npx vitest run
npx ng build --configuration production
npx playwright test     # khi đụng luồng chính
```

Chạy toàn hệ thống: `docker compose up --build`. Chế độ offline/demo dùng `LLM_PROVIDER=mock`, `PAYMENT_PROVIDER=local_mock`, `CALENDAR_PROVIDER=local_mock`.

## 7. Definition of Done

- Đúng SRS (BUSR/FR/state machine) và không phá luật mục 4.
- Có test phù hợp và đang xanh; CI gate (ruff, mypy, import-linter, build FE) sạch.
- Không có secret, token hoặc PII trong code, log hoặc prompt gửi LLM.
- Nếu thêm tích hợp ngoài thì có adapter mock tương ứng.
- Nếu đổi API: OpenAPI cập nhật, FE regenerate type, báo breaking change cho người dùng.
- Nếu đổi schema: migration có upgrade/downgrade, schema diff xanh.
- Mọi trạng thái UI (loading/empty/error/offline) có xử lý; a11y và responsive đã kiểm.

## 8. Những việc không làm khi chưa được phép

- Thêm thư viện lớn hoặc đổi công nghệ đã chốt trong ADR.
- Thêm bảng mới hoặc đổi số lượng 35 bảng (12 `account`, 10 `planning`, 5 `execution`, 4 `evaluation`, 4 `shared_kernel`).
- Sửa nội dung ADR/SRS (chỉ đề xuất thay đổi).
- Xóa dữ liệu, `git push --force`, đổi cấu hình CI/CD, hoặc chạm vào file `.env` thật.
- Gọi LLM thật hoặc cổng thanh toán thật trong test/CI.
- Bỏ qua hoặc "tắt" lint/import-linter/mypy để cho qua; hãy sửa thiết kế.

## 9. Cách giao tiếp

- Trả lời bằng tiếng Việt, ngắn gọn, đi thẳng vào kết quả. Giữ nguyên thuật ngữ kỹ thuật tiếng Anh.
- Nói rõ cái gì đã làm, cái gì chưa chắc, cái gì cần xác nhận. Không nói quá về mức độ kiểm chứng.
- Khi phát hiện mâu thuẫn tài liệu hoặc rủi ro nghiệp vụ, báo ngay thay vì tự xử lý âm thầm.
- Văn bản giao diện người dùng viết bằng tiếng Việt, dùng đúng thuật ngữ trong SRS.