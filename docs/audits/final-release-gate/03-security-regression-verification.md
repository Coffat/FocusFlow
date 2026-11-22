# 03 — Independent Security Regression Verification (Phase 4)

- **Execution Method**: Kiểm chứng độc lập hoàn toàn (không dựa vào unit test của implementer) bằng script `p3_independent_sec_gate.py` chạy trực tiếp trên Docker staging (`http://127.0.0.1:3000` + Mailpit `http://127.0.0.1:8025`) với 2 tài khoản độc lập mới đăng ký qua OTP (`p3_sec_a_1795343319@example.com`, `p3_sec_b_1795343319@example.com`).
- **Verdict**: **PASS — 13 / 13 SECURITY CONTROLS INDEPENDENTLY VERIFIED LIVE**

---

## Live 2-User Security Verification Matrix

| # | Security Control | Expected Behavior | Observed Live Evidence (`http://127.0.0.1:3000`) | Status |
|---|---|---|---|---|
| 01 | **Google SSO Token Validation (`AUD-CRIT-01`)** | Từ chối invalid `id_token` & `access_token` | `POST /auth/google` (invalid `id_token`) → `401`; (invalid `access_token`) → `401` | **PASS** |
| 02 | **Cookie CSRF & Refresh Cookie Path (`AUD-HIGH-01`)** | Thiếu/sai `Origin` → `403`; `Origin` hợp lệ → `200`; `refresh_token` `Path=/api/v1/auth` | Missing `Origin` → `403`, `Origin: https://evil.example` → `403`, `Origin: http://127.0.0.1:3000` → `200`, `Set-Cookie refresh_token` có `Path=/api/v1/auth` | **PASS** |
| 03 | **Refresh Token Rotation & Reuse Detection (`AUD-HIGH-02`)** | Replay token cũ thu hồi cả family; phiên độc lập không bị ảnh hưởng | `rt1` rotate → `200 (rt2)`; replay `rt1` → `401`; `rt2` (compromised family) → `401`; Session B độc lập `rt_b` → `200` | **PASS** |
| 04 | **Password Reset Session Revocation (`AUD-HIGH-03`)** | Reset mật khẩu thu hồi toàn bộ refresh token cũ | Hoàn tất OTP reset (`request-otp` → `verify-otp` → `confirm` `200`), replay refresh token cũ → `401`, đăng nhập mật khẩu mới → `200` | **PASS** |
| 05 | **OTP-Only Registration (`AUD-HIGH-04`)** | Chặn đăng ký trực tiếp không OTP ở staging/prod | `POST /api/v1/auth/register` → `403 REGISTRATION_OTP_REQUIRED` | **PASS** |
| 06 | **Cross-User IDOR & Admin RBAC (`AUD-HIGH-10`)** | User B không thể đọc/ghi tài nguyên User A (`404`); non-admin → `403` | `POST /sessions/notes` (`task_id` User A) → `404`, `PATCH /tasks/{id}` → `404`, `GET /roadmaps/{id}` → `404`, `GET /account/admin/status` → `403` | **PASS** |
| 07 | **DNS Rebinding / SSRF Intake (`AUD-CRIT-03`)** | Chặn loopback & cloud metadata | `http://127.0.0.1:6379/` → `422`; `http://169.254.169.254/latest/meta-data/` → `422` *(DNS rebinding IP-pinning được xác minh thêm bởi 43 deterministic unit tests)* | **PASS** |
| 08 | **RAG Magic-Byte Upload (`AUD-HIGH-06`)** | Chặn file giả mạo extension | Upload PNG bytes giả `fake.pdf` → `422` (`Tệp PDF không có chữ ký định dạng hợp lệ`) | **PASS** |
| 09 | **Evaluation AI Quota Enforcement (`AUD-CRIT-04`)** | Prove Mode trừ quota thật & ghi `ai_usage_logs` | `POST /evaluation/milestones/{id}/proofs/generate-jobs` → `202`; `GET /account/quota` tăng `used_calls: 0 → 1`, `remaining: 30 → 29`, `tokens_consumed: 931` | **PASS** |
| 10 | **Billing Webhook & Free Beta Gating (`AUD-CRIT-02`, `AUD-HIGH-11`)** | Fail-closed webhook, checkout & mock-confirm | `POST /billing/webhook` → `503`, `POST /billing/checkout` → `503`, `POST /billing/mock-confirm/{uuid}` → `403` | **PASS** |
| 11 | **WebCal Token Isolation** | Rotate tạo feed hợp lệ; revoke trả `404` | `rotate` → `200`, `GET /feeds/{token}.ics` → `200 (BEGIN:VCALENDAR)`, `DELETE /webcal` → `200`, fetch lại → `404` | **PASS** |
| 12 | **Account Export Data Isolation** | User A chỉ nhận dữ liệu của mình | `GET /account/export` → `200`, `contains_user_a=True`, `contains_user_b=False` | **PASS** |
| 13 | **Distributed Rate Limiting (`AUD-HIGH-05`)** | Chặn brute-force account `429` + `Retry-After`, không khóa tài khoản khác cùng IP | Login sai lần 1–10 → `401`, lần 11 → `429 (Retry-After=300)`; email khác cùng IP → `401` | **PASS** |

---

## Giới hạn kiểm chứng
- Google SSO **thật** (với Google OAuth consent screen & ID token ký thật từ Google) chưa chạy end-to-end với tài khoản Google production (đã kiểm chứng bằng negative live test + bộ unit tests `test_google_auth_security.py`).
- DNS rebinding thực tế trên mạng ngoài không thực hiện theo strict rule (đã kiểm chứng xác định bằng local DNS resolver fixtures trong `test_safe_url_fetcher_ssrf.py`).
