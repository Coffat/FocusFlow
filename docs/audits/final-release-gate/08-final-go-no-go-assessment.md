# 08 — Final GO / NO-GO Release Readiness Assessment (Phase 8)

- **Assessment Scope**: **FocusFlow Free Beta** (Single-VPS Docker Compose, `BILLING_RELEASE_MODE=FREE_BETA`)
- **Audit Baseline**: Independent Product Reality Audit (01–08) → P0A (09) → P0B (10) → P1A (11) → P1B (12) → P1C (13) → P2 (14) → P3 Final Release Gate (01–07).

---

## 1. Release Criteria Scorecard

| Release Gate Pillar | Status | Evidence Summary |
|---|---|---|
| **1. Source Integrity & Provenance** | **CONDITIONAL** | 0 secrets rò rỉ, 18/18 file lõi P0–P2 có mặt, **nhưng** working tree chưa commit & còn thư mục `artifacts/` cần dọn trước khi gắn tag release. |
| **2. Security & Cross-User Isolation** | **PASS** | **13/13** kiểm chứng bảo mật 2 người dùng PASS trực tiếp trên live staging (Google SSO, CSRF, RTR reuse + family revoke, Password Reset revoke, OTP-only reg, IDOR 404, SSRF 422, RAG magic-byte 422, Eval quota, Billing fail-closed, WebCal, Export isolation, Distributed rate limit). |
| **3. Functional Product Reality (A–H)** | **PASS (Free Beta)** | **1,061/1,061** backend tests, **666/666** frontend unit tests, **37/37** Playwright E2E PASS (`0 failed, 0 flaky`), `0 drift` OpenAPI & `schema.sql`, Gemini live Planning & Prove Mode grading verified. |
| **4. Performance & Reliability** | **PASS (Free Beta Cohort)** | 120 concurrent requests `0.00%` lỗi (`p95 ≤ 227.3ms`), PG16 `17 connections` (`0 idle in transaction`), restart recovery `11.045s`, Outbox rút sạch `PENDING → 0`, concurrent refresh race PASS. Còn 2 điểm lệch tầng timeout khuyến nghị chỉnh sớm. |
| **5. Disaster Recovery** | **PASS (Drill Verified)** | Clean-room PG16 backup (`182ms`) & restore (`359ms`, 37 tables, 26 triggers, `0015`) PASS; Redis AOF `everysec` khỏe. Cần thiết lập cron backup off-host & trần `maxmemory` trên VPS production. |
| **6. Production Manifests & Config** | **CONDITIONAL** | Đã có `docker-compose.prod.yml`, `supervisord.prod.conf`, `Dockerfile.prod`, `nginx.prod.conf`, `.env.prod.example` (`config --quiet` exit `0`). Chưa chạy `docker compose build`, live production SMTP & host TLS trên máy chủ thật. |
| **7. Monetization / Paid Mode** | **FEATURE GATED (`FREE_BETA`)** | Fail-closed cả FE & BE (`503`/`403`); **NO-GO cho `PAID_ENABLED`** cho đến khi tích hợp & sandbox-test live payment gateway. |

---

## 2. FINAL RELEASE DECISION

### **VERDICT: CONDITIONAL GO (FREE BETA ONLY — CONTROLLED COHORT)**

FocusFlow **ĐỦ ĐIỀU KIỆN kỹ thuật về mặt ứng dụng, bảo mật và độ tin cậy dữ liệu để phát hành `Free Beta` có kiểm soát** (khắc phục hoàn toàn 4/4 Critical, 10/11 High, 11/13 Medium, 5/6 Low và feature-gate trung thực `AUD-HIGH-11`), **VỚI ĐIỀU KIỆN BẮT BUỘC** hoàn thành 5 bước tiền-triển khai sau trước khi mở URL cho người dùng thật:

### Mandatory Pre-Launch Conditions (Phải hoàn thành trước khi mở Free Beta)
1. **Source Freeze & Clean Release Tag**: Dọn/loại trừ `artifacts/`, `docs_ute/`, `docs/experiments/scheduled_eval_7d/runs/` khỏi nhánh release, thực thi **Atomic Commit Plan** (8 commit) trong `01-release-source-integrity.md`, merge có review vào `main` và gắn tag `v0.9.0-beta.1`.
2. **Production Container Build & Smoke Test**: Chạy `docker compose -f docker-compose.prod.yml build`, điền `.env.prod` với secrets thật (64-hex `SECRET_KEY`, `FERNET_KEY`, `CALENDAR_ENCRYPTION_KEY`, `REDIS_PASSWORD`, HTTPS `FRONTEND_URL`/`BACKEND_CORS_ORIGINS`/`CSRF_TRUSTED_ORIGINS`, transactional SMTP thật thay Mailpit), chạy one-shot `migrate` profile, xác minh `/api/health` (`200`), đăng ký OTP thật qua SMTP và luồng AI Roadmap trên môi trường production trước khi mở cho người dùng.
3. **Operational Limits & Feature Gates**:
   - Giữ **`BILLING_RELEASE_MODE=FREE_BETA`** (tuyệt đối không bật `PAID_ENABLED`).
   - Giữ **GDPR Account Delete** ở trạng thái feature-gated.
   - Đặt giới hạn cohort Free Beta ban đầu (**≤ 50–100 người dùng hoạt động đồng thời** trên 1 VPS 1 API + 2 workers), bật giám sát `/api/health`, `pg_stat_activity`, Redis memory (đặt `--maxmemory`), Outbox `FAILED/PENDING` age và chi phí LLM hàng ngày.
4. **Automated Off-Host Backups**: Cài cron chạy `scripts/backup_postgres.sh` hàng ngày đẩy lên object storage mã hóa (S3/R2/GCS) với retention 14 ngày.
5. **Recommended Pre-Scale Quick Fixes (Sprint 0 / ngay sau pilot)**:
   - Thêm `HTTP_TIMEOUT_MS = 40_000` cho `submitMilestoneProof` (`35_000` cho `generateMilestoneProof`) và lệch tầng DB timeouts (`20s`/`23s`/`15s` < `30s` FE).
   - Bật `EMBEDDING_API_KEY` nếu muốn mở tính năng Knowledge RAG cho người dùng Free Beta (nếu chưa bật, thông báo rõ RAG chưa kích hoạt).

### Explicit NO-GO Scope
- **NO-GO** cho `PAID_ENABLED` / thu phí thật.
- **NO-GO** cho triển khai trực tiếp bằng `docker-compose.yml` (dev) hoặc `supervisord.conf` (có `--reload` và `mailpit`).
