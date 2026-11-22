# 07 — Release Readiness Assessment (Phase 8)

---

## 1. Feature Readiness Classification

| Feature / Domain | Classification | Rationale & Evidence |
|---|---|---|
| **Onboarding & OTP Auth** | **PARTIAL** | Luồng OTP → Login → Profile → Availability chạy live mượt (`auth.spec.ts` 8/8 PASS), nhưng còn blockers bảo mật (`AUD-CRIT-01` Google SSO, `AUD-HIGH-01..05` CSRF/RTR/Password Reset/Direct Register/Rate Limit). |
| **AI Roadmap & Schedule Planning** | **FUNCTIONALLY COMPLETE BUT NOT PRODUCTION VERIFIED** | Chạy live end-to-end với Gemini thật (Clarify → Milestones SSE → Approve → Proposal DRAFT → Apply → 13 tasks, 21 blocks), tuân thủ SRS. Cần bật Circuit Breaker an toàn (`AUD-HIGH-08`), thêm SSE refresh recovery (`AUD-MED-07`) & bỏ khóa cứng Cobhub proxy (`AUD-MED-11`). |
| **Study Execution Workspace** | **PARTIAL** | Timer, heartbeat, complete, finalize, takeaway, Outbox chạy live tốt (`p2b1` PASS), nhưng có lỗ hổng cross-user IDOR tạo sticky note (`AUD-HIGH-10`) cần vá trước khi mở cho người dùng thực. |
| **Overdue Detection & Adaptation (Domino Shift)** | **FUNCTIONALLY COMPLETE BUT NOT PRODUCTION VERIFIED** | Đúng bất biến SRS qua mã nguồn & integration test; chưa chạy cron live 00:05 ICT trên staging. |
| **Prove Mode & Weekly Review (Evaluation)** | **PARTIAL** | UI và persistence đã nối, nhưng **bypass hoàn toàn AI quota** (`AUD-CRIT-04`) và live grader rơi vào fallback `NEEDS_REVIEW` (`AUD-MED-12`). |
| **Analytics, SRL Aggregation & Notifications** | **FUNCTIONALLY COMPLETE BUT NOT PRODUCTION VERIFIED** | Outbox → `processed_events` → SRL Profile → Dashboard/Analytics/Notifications hoạt động live. Cần vá Outbox relay silent drop & aborted session (`AUD-HIGH-07`) và `NullPool` (`AUD-HIGH-09`). |
| **RAG Knowledge Ingestion** | **PARTIAL / UNCONFIGURED** | Code pgvector + RRF + `<untrusted_knowledge_context>` tốt, nhưng staging chưa bật `EMBEDDING_API_KEY` và còn lỗ hổng DNS rebinding SSRF (`AUD-CRIT-03`) + upload chỉ kiểm đuôi file (`AUD-HIGH-06`). |
| **WebCal (`.ics`)** | **PRODUCTION READY (sau khi vá rate limit)** | Sinh `.ics` hợp lệ, SHA-256 hash, revoke trả 404, header bảo mật chuẩn. Chỉ cần thay dict rate-limit in-memory bằng Redis (`AUD-HIGH-05`). |
| **Google Calendar Sync** | **FUNCTIONALLY COMPLETE BUT NOT PRODUCTION VERIFIED** | Code OAuth + Fernet + webhook tốt, nhưng chưa kiểm chứng với tài khoản Google & HTTPS webhook thật (`calendar_webhook_https_ready=false`); cần vá `AUD-MED-05` & `AUD-LOW-02/03`. |
| **Billing & Subscription Checkout** | **NOT IMPLEMENTED (LIVE)** | Không có cổng thanh toán thật (`503` ở staging — `AUD-HIGH-11`); webhook có lỗ hổng nghiêm trọng (`AUD-CRIT-02`). |
| **GDPR Data Export** | **PRODUCTION READY (sau khi thêm rate limit)** | Xuất 12 khóa JSON chỉ thuộc user hiện tại (verified live); cần thêm rate limit (`AUD-HIGH-05`). |
| **GDPR Account Deletion** | **FEATURE GATED** | UI đã khóa trung thực; backend chưa triển khai `DELETE /api/v1/account`. |
| **Admin Portal** | **PRODUCTION READY (MVP baseline)** | `adminGuard` FE + `403` BE verified live. |

---

## 2. Multi-Dimensional Quality Assessment

| Dimension | Rating | Evidence Summary |
|---|---|---|
| **Functional Correctness** | **Good (Core) / Gaps in Billing & Prove Mode** | Workflows A, B, C, F, G-WebCal/Notif chạy live thành công; Prove Mode bypass quota & live grader fallback; Billing live chưa có. |
| **Data Integrity** | **Moderate-High** | 36 bảng ORM khớp Alembic 100%, Outbox idempotent hoạt động live, nhưng còn Sticky Note IDOR (`AUD-HIGH-10`) và Outbox silent drop (`AUD-HIGH-07`). |
| **Security** | **UNACCEPTABLE FOR PROD (4 Critical, 7 High)** | Google SSO confused deputy, Billing webhook + JWT key reuse, DNS rebinding SSRF, không CSRF, không rate limit, Password Reset không revoke session, Direct Register không OTP, Sticky Note IDOR. |
| **Reliability** | **Moderate-Low Under Load** | `NullPool` không timeout (`AUD-HIGH-09`), Circuit Breaker tắt/crash khi mất Redis (`AUD-HIGH-08`), Outbox retry vô hạn khi lỗi DB (`AUD-HIGH-07`), SSE memory leak (`AUD-MED-08`). |
| **AI Output Quality** | **Good (Planning) / Degraded (Prove Mode Grader)** | Planning tạo câu hỏi, milestone và lịch tiếng Việt sát thực tế với Gemini thật; Prove Mode grader live rơi fallback `NEEDS_REVIEW`. |
| **Usability** | **Good** | UI Angular 21 + PrimeNG sạch, 34/34 Playwright spec mới pass; thiếu SSE recovery khi F5 (`AUD-MED-07`). |
| **Observability** | **Moderate** | Có `WorkflowRun`/`WorkflowStepExecution` & `structlog`, nhưng `ai_usage_logs` thiếu Evaluation, `/api/health` không kiểm DB/Redis và lộ thông tin nội bộ (`AUD-MED-04`), PII redaction chưa phủ stdlib (`AUD-MED-06`). |
| **Deployment Readiness** | **Not Ready** | Chưa có live payment, chưa cấu hình production SMTP/HTTPS webhook/RAG embedding, `NullPool`, working tree còn rất nhiều thay đổi chưa commit. |
| **Documentation Consistency** | **Drifted** | `docs/database/schema.sql` (35 bảng) lệch Alembic (36 bảng); `AGENTS.md` quảng bá `LLM_PROVIDER=mock` & `CALENDAR_PROVIDER=local_mock` nhưng code từ chối; `01-system-inventory.md` ghi 89 endpoint thay vì 102. |

---

## 3. Final Release Verdict

### **VERDICT: NO-GO**

FocusFlow **CHƯA sẵn sàng phát hành MVP cho người dùng thực trên production** tại thời điểm kiểm toán này.

**Lý do cốt lõi (Non-Negotiable Blockers)**:
1. **4 lỗ hổng Critical** có thể khai thác trực tiếp: chiếm quyền tài khoản qua Google SSO (`AUD-CRIT-01`), giả mạo nâng cấp gói & lộ khóa JWT qua Billing Webhook (`AUD-CRIT-02`), vượt tường lửa SSRF qua DNS Rebinding (`AUD-CRIT-03`), và gọi AI miễn phí không giới hạn qua Evaluation Quota Bypass (`AUD-CRIT-04` — đã tái hiện live).
2. **Các lỗ hổng High đã tái hiện trực tiếp**: Cross-user Sticky Note IDOR (`AUD-HIGH-10`), Password Reset không thu hồi refresh token (`AUD-HIGH-03`), đăng ký không OTP mở ở staging (`AUD-HIGH-04`), thiếu hoàn toàn CSRF (`AUD-HIGH-01`) & rate limiting (`AUD-HIGH-05`), RTR thiếu reuse detection (`AUD-HIGH-02`), DB `NullPool` (`AUD-HIGH-09`), và Outbox relay silent drop (`AUD-HIGH-07`).

**Điều kiện để chuyển từ `NO-GO` → `CONDITIONAL GO` (MVP Beta / Free Tier)**:
- Xử lý dứt điểm toàn bộ **P0 Release Blockers** trong tài liệu `08-prioritized-remediation-backlog.md` (`AUD-CRIT-01..04`, `AUD-HIGH-01..10`).
- **Feature-gate chính thức** (hiển thị rõ "Sắp ra mắt" / chặn endpoint ở production) cho: (1) Billing/Premium Upgrade (cho đến khi tích hợp cổng thanh toán thật), (2) GDPR Account Delete, và (3) RAG URL/File upload (nếu chưa cấu hình `EMBEDDING_API_KEY`).
- Chạy lại toàn bộ Playwright E2E (đạt 37/37 PASS sau khi sửa 2 spec kế thừa) và kiểm chứng lại Prove Mode grader live.
