# 02 — End-to-End Product Validation (Workflows A–H)

- **Environment Tested**: Live Docker Compose stack (`http://127.0.0.1:3000` → `focusflow-backend:8000`, `focusflow-postgres` PG16, `focusflow-redis` Redis 7, `focusflow-mailpit` :8025, AI Gateway `http://host.docker.internal:8045` với `LLM_PROVIDER=gemini`, `ENVIRONMENT=staging`, `PAYMENT_PROVIDER=mock`, `CALENDAR_PROVIDER=google`).
- **Isolated Audit Accounts**: `qa_user_a_1795255590@example.com` (`bbdff9e1-9e71-4fc9-a24f-0a5e7cabb53d`) và `qa_user_b_1795255732@example.com`.
- **Automated Suites Executed Independently**:
  - Backend unit + AI evals + evaluation + root: **713 passed, 1 skipped, 0 failed**.
  - Backend integration (real PG16 + Redis 7): **75 passed, 0 failed, 2 deselected** (opt-in live tests).
  - Frontend Vitest unit: **649 passed (85/85 files)**.
  - Frontend Playwright E2E against live Docker (`http://127.0.0.1:3000`): **35 passed, 2 failed (94.6%)**.

---

## 1. Workflow-by-Workflow Live Validation Matrix

| Workflow | Classification | Live API / DB / Outbox Evidence | Playwright E2E Evidence | Gaps / Issues Observed |
|---|---|---|---|---|
| **A. Onboarding** (Register → OTP → Login → Profile → Availability) | **E2E VERIFIED (LIVE)** | `request-otp` (200, 70ms) → Mailpit OTP → `verify-otp` (201, 16ms) → `me` (200) → `PATCH /account/profile` (200) → `PUT /availabilities/me` (200). Outbox `AvailabilityUpdatedEvent` = `PUBLISHED`, `processed_events` đã chạy consumer. | `auth.spec.ts` (**8/8 PASS**), `availability.spec.ts` (**2/2 PASS**) | Direct `/api/v1/auth/register` không OTP vẫn mở ở staging (`AUD-HIGH-04`); `access_token` trả trong JSON body (`AUD-MED-03`). |
| **B. AI Roadmap Generation** (Goal → Clarify → Milestones → Approve → Proposal → Apply) | **E2E VERIFIED (LIVE GEMINI)** | `POST /roadmaps` (201) → `clarify-questions` (200, **8.8s**, 3 câu tiếng Việt sát domain PG16) → `clarify-skip` (200) → `milestones/generate-jobs` (202) → SSE stream (**21.3s**, 4 events, 4 milestones chất lượng tốt) → `approve` (200) → `proposals/generate-jobs` (202) → SSE stream (**31.8s**, 9 events, lưu `DRAFT`) → `apply` (200, chuyển `APPLIED`, tạo **13 tasks** & **21 schedule_blocks**). Quota `used_calls=3`, `tokens_consumed=63800`. | `fit_capacity_scope_approval.spec.ts` (1/1 PASS), `roadmap-dashboard-sync.spec.ts` (5/5 PASS), `p2a-data-consistency.spec.ts` (10/10 PASS); `e2e_full_workflow.spec.ts` **FAIL** Test 1 do Clarification vào Vòng 2 | Không khôi phục SSE `job_id` khi F5 trình duyệt (`AUD-MED-07`); legacy E2E spec lỗi thời (`AUD-MED-13`). **Tuân thủ SRS**: AI chỉ tạo `DRAFT`, chỉ `Apply` mới ghi `OfficialSchedule`. |
| **C. Study Execution** (Dashboard → Today → Start → Heartbeat → Complete → Finalize → Takeaway) | **E2E VERIFIED (LIVE)** | `today-focus` (200) → `start` (201, STANDARD 25m) → `heartbeat` (200, `actual_minutes=10` + scratchpad) → `tasks/{id}/complete` (200) → `finalize` (200, takeaway). Outbox `StudySessionCompletedEvent` = `PUBLISHED`. | `p2b1-study-data-integrity.spec.ts` (**1/1 PASS**) | Timer dựa trên mốc thời gian (không đếm tick), không còn `localStorage` Pomodoro counter. |
| **D. Feedback & Adaptation** (Missed Task → Overdue → Proposal → Apply → Domino Shift) | **CODE + INTEGRATION VERIFIED (CRON NOT LIVE-WAITED)** | `sweep_overdue_tasks_and_anti_loop` (`execution/presentation/tasks.py:165-333`) đã xác minh mã nguồn & test: **không tự dời `scheduled_date`** (dòng 202), gắn cờ STALLED khi `reschedule_count >= 3`. `shift_incomplete_tasks_for_domino()` (`schedule_sync_adapter.py:306-313`) **không tăng `reschedule_count`**. | Đã kiểm chứng qua backend unit/integration; chưa chờ cron 00:05 ICT live trên staging | Tuân thủ đúng ràng buộc bất biến SRS về Overdue & Domino Shift. |
| **E. Learning Evaluation** (Milestone → Prove Mode → Challenge → Submit → AI Eval → Profile) | **PARTIAL / DEFECTIVE LIVE** | `proofs/generate-jobs` (202, **5.4s** blocking đồng bộ, trả 3 câu hỏi tiếng Việt PG16 `status=READY`) → `submit` (200, **7.5s**, trả `status=NEEDS_REVIEW, score=0` với fallback message). | `p2b2a-functional-completeness.spec.ts` (**3/3 PASS** với mock) | **CRITICAL**: Bypass hoàn toàn AI Quota (`used_calls` giữ nguyên `3`, `ai_usage_logs` giữ nguyên `11` — `AUD-CRIT-04`). Grader live rơi vào fallback `NEEDS_REVIEW` (`AUD-MED-12`). |
| **F. Analytics & Personalization** (Sessions → Outbox → SRL → Profile → Analytics → Dashboard) | **E2E VERIFIED (LIVE)** | Sau Workflow C: `outbox_events` = 4 (`PUBLISHED`), `processed_events` = 7 (gồm `aggregate_learner_srl_profile` & worker). `GET /analytics/summary` (200: `total_focused_hours=0.42`, `task_completion_rate=7.7`, `plan_adherence_rate=100.0`); `GET /evaluation/dashboard-summary` (200: `monthly_hours=0.4`, `streak_days=1`). | `p2a-data-consistency.spec.ts` (**10/10 PASS**) | Weekly Review LLM call cũng bypass quota (`AUD-CRIT-04`). |
| **G. Calendar & Notifications** (Availability → Google Calendar / WebCal → Notifications) | **E2E VERIFIED (WEBCAL + NOTIF); GOOGLE OAUTH NOT LIVE-TESTED** | `webcal/rotate` (200) → `GET /feeds/{token}.ics` (200, 6622 bytes, 21 `VEVENT`) → `DELETE /webcal` (200) → fetch lại trả **404**. `GET /account/notifications` (200, có bản ghi `SESSION_COMPLETED` bền vững sau refresh). | `p2b2a` & `p2b2b` (**7/7 PASS**) | Google OAuth live cần tài khoản Google thật & HTTPS webhook (`calendar_webhook_https_ready=false`); `CALENDAR_PROVIDER=local_mock` bị từ chối (`AUD-MED-11`). |
| **H. Account & Billing** (Settings → Profile → Export → Password → Logout/Login → Billing) | **ACCOUNT VERIFIED; BILLING UNAVAILABLE IN PROD** | `GET /account/export` (200, 12 khóa GDPR hợp lệ). `POST /account/billing/checkout` trả **503** trong `staging` (fail-closed vì không có live gateway). | `p2b2b-functional-integration.spec.ts` (**4/4 PASS**) | **Không có cổng thanh toán thật** (`AUD-HIGH-11`). `LocalMockPaymentAdapter` tạo URL `/billing/mock-checkout` không tồn tại trên FE. Xóa tài khoản GDPR bị gate (`AUD-LOW-06`). |

---

## 2. External Provider & Feature Availability Matrix

| Capability | Live Provider | Local Mock | Feature Gated / Unavailable | Evidence |
|---|---|---|---|---|
| **LLM Generation (Planning & Evaluation)** | **LIVE** (Gemini via Cobhub `host.docker.internal:8045`) | **NOT AVAILABLE** in prod runtime (`LiteLLMAdapter` rejects `mock`) | Direct Gemini API blocked without `LLM_BASE_URL` | `litellm_adapter.py:428-440` + live run |
| **RAG Embeddings** | Code supports Google AI Studio (`gemini-embedding-2`) | None | **UNAVAILABLE** in staging (`rag_embedding_configured: false`) | `GET /api/health` live |
| **Email / OTP** | SMTP (`mailpit` in staging) | SMTP sink (Mailpit) | Production SMTP untested | Live OTP verified via Mailpit :8025 |
| **Google Calendar Sync** | **CODE REAL** (`GoogleCalendarAdapter`) | **NOT AVAILABLE** (`deps.py` rejects `local_mock`) | Webhook HTTPS `false` in staging; live OAuth not executed | `account/presentation/deps.py:518-531` |
| **WebCal (`.ics`)** | **LIVE & VERIFIED** | N/A | None | Live 21-VEVENT `.ics` + revoke 404 |
| **Billing / Subscription** | **NOT IMPLEMENTED** (SePay/VNPay/MoMo/Stripe absent) | `LocalMockPaymentAdapter` (chỉ dev/test) | **HTTP 503** trong `staging`/`production` | Live `POST /billing/checkout` → `503` |
| **GDPR Account Delete** | **NOT IMPLEMENTED** | None | **FEATURE GATED** (UI disabled no-op) | `settings-page.component.ts:1533-1537` |

---

## 3. Playwright Live E2E Breakdown (35/37 Passed, 2 Failed)

Chạy từ `frontend/` với `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 BACKEND_API_URL=http://127.0.0.1:3000/api/v1 MAILPIT_API_URL=http://127.0.0.1:8025/api/v1`:

- **PASS 100% (34/34 tests)** trên toàn bộ 8 bộ spec mới: `auth.spec.ts` (8/8), `availability.spec.ts` (2/2), `fit_capacity_scope_approval.spec.ts` (1/1), `p2a-data-consistency.spec.ts` (10/10), `p2b1-study-data-integrity.spec.ts` (1/1), `p2b2a-functional-completeness.spec.ts` (3/3), `p2b2b-functional-integration.spec.ts` (4/4), `roadmap-dashboard-sync.spec.ts` (5/5).
- **FAIL (2 tests)** trên 2 spec kế thừa (`AUD-MED-13`):
  1. `frontend/e2e/e2e_full_workflow.spec.ts:14` (1/2 fail): Kỳ vọng nút `[data-testid="generate-milestones-ai-btn"]` xuất hiện ngay sau Vòng 1 Clarification, nhưng AI thực tế mở **Vòng 2 Clarification**; đồng thời hardcode `http://localhost:8000`.
  2. `frontend/e2e/signal_e2e_evidence.spec.ts:14` (0/1 fail, timeout 120s): Chờ selector cũ `.trailing-toggle-button` trên `/login` (đã đổi thành nút `"Ẩn/Hiện mật khẩu"`); hardcode `http://localhost:8000`.

---

## 4. PostgreSQL Persistence Verification (User A Live Run)

- `roadmaps`: 1 | `milestones`: 4 | `schedule_proposals`: 1 (`APPLIED`) | `schedule_blocks`: 21 | `tasks`: 13.
- `ai_quotas`: `used_calls=3`, `reserved_calls=0`, `monthly_limit=30`, `tokens_consumed=63800` (**không đổi sau Prove Mode**).
- `ai_quota_reservations`: 3 (`GOAL_CLARIFICATION`, `MILESTONE_GEN`, `SCHEDULE_PROPOSAL_GEN` — đều `COMMITTED`).
- `ai_usage_logs`: 11 rows (`total_tokens=63800` — **không tăng sau Prove Mode**).
- `outbox_events`: 4 (`AvailabilityUpdatedEvent`, `MilestoneApprovedEvent`, `OfficialScheduleAppliedEvent`, `StudySessionCompletedEvent` — tất cả `PUBLISHED`).
- `processed_events`: 7 handler rows đã xử lý idempotent thành công.
