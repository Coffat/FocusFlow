# 13 — P1C Billing Readiness, Release Feature Gating & Final P1 Closure Report (FocusFlow)

- **Branch**: `fix/p1c-billing-release-gating` (tạo từ `fix/p1b-ai-db-reliability`, bảo toàn toàn bộ P0A + P0B + P1A + P1B)
- **Scope**: Phase 0 (P1B Follow-up), Phase 1–4 (`AUD-HIGH-11` Billing Domain Audit, `FREE_BETA` vs `PAID_ENABLED` Release Modes, Honest Feature Gating & Payment Security Regression), Phase 5 (Full P1 End-to-End Regression). Không mở rộng sang P2 và **không tự tuyên bố GO-LIVE**.

---

## 1. P1B Follow-up Verification Results (Phase 0)

| Area | Verification Result | Minimal Fix Applied (if any) |
|---|---|---|
| **Database Connection Budget** | **PASS (topology hiện tại)** — `supervisord.conf` chạy 1 Uvicorn API + 2 Taskiq workers (active worst-case `60/97` available PG16 connections; gồm scheduler + 3 reserved = `83/100`). Nếu scale Uvicorn lên `>= 4` workers cần hạ `DB_POOL_SIZE` hoặc đặt PgBouncer. | Đóng read DB transaction (`await self._uow.rollback()`) trước pipeline LLM 55s trong `ExecuteScheduleProposalGenerationUseCase` (xác minh 0 uncommitted write trước bước decompose). *(Ghi nhận `GenerateClarificationQuestionsUseCase` giữ lock theo thiết kế khóa goal — đề xuất tách ở P2 nếu cần tải cao.)* |
| **Prove Mode Semantics** | **PASS** — `is_verified` (AI chấm thành công) tách biệt rõ với `status == "PASSED"` (`>= 70`); `upsert_memory_and_mastery_feedback` ánh xạ điểm thấp/0 về `NEEDS_REINFORCEMENT` (`< 0.5`), không bao giờ gán nhầm `MASTERED`; `ProveModeDialogComponent` hiển thị tách bạch. | Không cần sửa (đã đạt). |
| **AI Job Recovery (`resumable`)** | **1 DEFECT FIXED** — Khi Redis lỗi, `RedisMilestoneCheckpointStore` fallback sang `_memory_fallback` (bị hủy cuối job) nhưng SSE `failed` vẫn phát `resumable=True`. | Thêm thuộc tính `is_durable: bool` trên `MilestoneCheckpointStorePort` / `RedisMilestoneCheckpointStore` (chỉ `True` khi lưu/đọc bền vững từ Redis); gate `resumable` trên `is_durable` (4 regression tests mới PASS). |

---

## 2. Billing Domain State-Machine Review (Phase 1)

- **ORM & DB Check Constraints (`user_orm.py:471-515`)**:
  - `chk_payment_transactions_status`: `PENDING`, `PAID`, `FAILED`, `CANCELLED`, `REFUNDED` (lệch nhẹ SRS v1.3 dùng `EXPIRED` thay `REFUNDED`, chưa có cột `expires_at` — hiện tính động `created_at + 15m`).
  - `chk_payment_transactions_provider`: `PAYOS`, `VNPAY`, `MOCK` (chưa cho phép `SEPAY`).
- **Đã đồng bộ trong P1C**:
  - `PREMIUM_MONTHLY_AI_QUOTA`: nâng từ `100` → **`300`** lượt/tháng khớp SRS `OS-02` & `FR-QUOTA-002` (`billing.py`, `user_repository.py`, `user_repository_port.py`).
  - Giá gói từ 1 nguồn chân lý server (`BILLING_PLANS`): `PREMIUM_MONTHLY = 99.000đ`, `PREMIUM_YEARLY = 990.000đ`, `max_active_roadmaps = 15` (xóa hoàn toàn lệch giá `199k` vs `99k` và hứa hẹn "Không giới hạn" trên FE).
  - Sửa `LocalMockPaymentAdapter.checkout_url` từ route chết `/billing/mock-checkout` → `{frontend_base}/pricing?mock_tx={transaction_id}`.
  - Sửa kiểu trả về `BillingService.confirmMockCheckout()` từ `PaymentTransactionDTO` → `BillingWebhookResponseDTO`.
- **Chưa triển khai cho Paid Mode (giữ fail-closed)**:
  - Live payment provider adapter (PayOS / VNPay / SePay), `EXPIRED` sweeper, `FAILED`/`CANCELLED` state transition, `subscription_expires_at` / gia hạn / hạ cấp EDF, và outbox event `UserUpgradedToPremiumEvent`.

---

## 3. Release Modes Configuration (`FREE_BETA` vs `PAID_ENABLED`)

Cấu hình qua `BILLING_RELEASE_MODE: Literal["FREE_BETA", "PAID_ENABLED"] = "FREE_BETA"` (`config.py`) và phát công khai qua `GET /api/v1/account/billing/config`:

| `billing_release_mode` | `environment` | `payment_provider` | `checkout_enabled` | `mock_confirm_enabled` | `provider` | `POST /checkout` | `POST /mock-confirm/{id}` |
|---|---|---|---|---|---|---|---|
| **`FREE_BETA`** *(mặc định)* | Mọi môi trường | Bất kỳ | `False` | `False` | `"none"` | `503` (`BILLING_FREE_BETA_DISABLED`) | `403` |
| **`PAID_ENABLED`** | `dev`/`test`/`local` | `local_mock` | `True` | `True` | `"local_mock"` | `200` (mock cô lập) | `200` (owner only) |
| **`PAID_ENABLED`** | `staging`/`production` | `local_mock` | `False` | `False` | `"none"` | `503` (`BILLING_MOCK_FORBIDDEN`) | `403` |
| **`PAID_ENABLED`** | Mọi môi trường | `sepay`/`payos`/`vnpay` (chưa cài adapter) | `False` | `False` | `"none"` | `503` (`BILLING_PROVIDER_UNCONFIGURED`) | `403` |
| **`PAID_ENABLED`** | Mọi môi trường | Live provider thiếu `PAYMENT_WEBHOOK_SECRET` | `False` | `False` | `"none"` | `503` (`BILLING_WEBHOOK_SECRET_MISSING`) | `403` |

---

## 4. Payment Provider Readiness Classification (Trung thực)

| Mức độ sẵn sàng | Trạng thái | Ghi chú |
|---|---|---|
| **Billing Domain Ready (Core + Webhook Security)** | **READY** | Server-side pricing, `SELECT ... FOR UPDATE`, dedicated `PAYMENT_WEBHOOK_SECRET`, `±300s` timestamp HMAC, `monthly_limit=300`. |
| **Mock Payment Test Ready** | **READY (Dev/Test Only)** | Chỉ hoạt động khi `ENVIRONMENT ∈ {dev,test,local}` + `BILLING_RELEASE_MODE=PAID_ENABLED` + `PAYMENT_PROVIDER=local_mock`. |
| **Free Beta Feature Gating** | **VERIFIED LIVE** | Backend fail-closed (`503`/`403`), `/pricing` hiển thị Free Beta banner & disable CTA, không có checkout giả. |
| **Live Provider Integrated** | **NOT IMPLEMENTED** | Chưa chốt & chưa viết adapter PayOS/VNPay/SePay. |
| **Live Provider Sandbox Verified** | **NOT VERIFIED** | Chưa có sandbox credentials & sandbox test. |
| **Production Payment Enabled** | **BLOCKED (FAIL-CLOSED)** | Bắt buộc fail-closed đến khi hoàn thiện live provider + sandbox + subscription lifecycle. |

---

## 5. Feature Gating Matrix (Current Staging / Free Beta)

| Feature | Release State | Backend Enforcement | Frontend UX |
|---|---|---|---|
| **Free Tier Core Learning (A–G)** | **ENABLED** | Full OTP auth, CSRF, RTR, Redis rate limit, AI quota 30/tháng | Đầy đủ |
| **Premium Checkout & Upgrade** | **FEATURE GATED (`FREE_BETA`)** | `POST /checkout` → `503`, `POST /mock-confirm` → `403`, `/billing/config` → `checkout_enabled: false` | `billing-free-beta-banner`, nút Premium disabled (`Sắp ra mắt (Free Beta)`), Settings toast đồng nhất |
| **GDPR Account Deletion** | **FEATURE GATED** | Endpoint chưa mở | Nút xóa tài khoản disabled trung thực |
| **RAG Embeddings** | **UNCONFIGURED IN STAGING** | Fail-closed nếu thiếu `EMBEDDING_API_KEY`; upload đã có magic-byte/zip-bomb/SSRF guard | Báo lỗi có kiểm soát |

---

## 6. Security Regression, Tests & Live Runtime Evidence (Phase 4 & 5)

- **Backend**: `ruff check` & `ruff format --check` (476 files) **PASS**, `mypy --strict src` (326 files) **PASS**, `lint-imports` (5/5 contracts) **PASS**, **901 passed, 1 skipped** (unit/eval), **145 passed, 2 deselected** (integration PG16 + Redis 7, gồm 24/24 billing & webhook security tests).
- **Contract**: `bash scripts/check-api-contract.sh` → **PASS (0 drift)** (`schema.d.ts` đồng bộ `BillingConfigResponseDTO`, `BillingPlanDTO`, `BillingWebhookResponseDTO`).
- **Frontend**: `ng lint` **PASS**, **656/656** Vitest **PASS**, `ng build --configuration production` **PASS**.
- **Live Docker Staging (`http://127.0.0.1:3000`)**:
  - `GET /api/v1/account/billing/config` → `200`: `{"release_mode": "FREE_BETA", "checkout_enabled": false, "mock_confirm_enabled": false, "provider": "none", "plans": [99000/300/15, 990000/300/15]}`.
  - **Full Playwright E2E (10 specs / 37 tests)**: **`37 passed, 0 failed, 0 skipped (4.6m)`** — Test #30 (`FE-API-05`) xác minh trực tiếp trên trình duyệt: banner Free Beta hiển thị, CTA Premium disabled (không mở modal giả), `POST /checkout` → `503 BILLING_FREE_BETA_DISABLED`, `POST /mock-confirm` → `403`, `/auth/me` giữ `tier === 'FREE'`.

---

## 7. Remaining Release Blockers, Final P1 Closure & P2 Recommendations

### Remaining Blockers Before Paid Launch (Không chặn Free Beta nội bộ)
- **Paid Mode**: Chưa có live payment provider adapter & sandbox verification, chưa có subscription expiry/downgrade & migration `EXPIRED`/`expires_at`.
- **Production Operations (P2 Hygiene trước Public Beta)**:
  - `AUD-MED-01` (Password reset response enumeration text), `AUD-MED-02` (Atomic OTP verification), `AUD-MED-03` (Bỏ `access_token` khỏi JSON body), `AUD-MED-04` (`/api/health` ping DB/Redis & khóa chi tiết nội bộ), `AUD-MED-05` (Fail-closed Calendar webhook khi thiếu hash), `AUD-MED-06` (PII redaction cho stdlib logger), `AUD-MED-07/08` (FE HTTP timeout/SSE F5 recovery & TTL eviction trên `InMemorySseJobStore`), `AUD-MED-09` (2 raw SQL cross-context sót), `AUD-MED-10` (Đồng bộ `docs/database/schema.sql` 36 bảng).

### Final P1 Closure Recommendation
- **Toàn bộ P0 (10/10) và P1 (6/6) đã hoàn tất và được kiểm chứng bằng unit, integration, và live Docker staging (37/37 E2E PASS).**
- **Khuyến nghị trạng thái phát hành**: Chuyển từ **`NO-GO`** sang **ứng viên `CONDITIONAL GO (Free Beta Only)`** — chỉ chính thức mở Free Beta sau khi rà soát/đóng các mục bảo mật & vận hành P2 thiết yếu (`AUD-MED-01..06`, `AUD-MED-10`) và cấu hình production SMTP/secrets. **Không bật `PAID_ENABLED`** cho đến khi tích hợp & sandbox-test cổng thanh toán thật.
