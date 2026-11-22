# 07 — Release Blockers & Residual Risk Acceptance (Phase 7)

---

## 1. Merge Blockers into `main`: **0 OPEN (ALL CLOSED)**
- `RC-BLK-01` (`frontend/Dockerfile.prod` Nginx duplicate `pid` crash-loop): **CLOSED & VERIFIED** in clean worktree (`1e72ef4`, 4/4 containers healthy on `:18080`).
- `RC-BLK-02` (Uncommitted working tree / source freeze): **CLOSED & VERIFIED** (`release/free-beta-rc` has 9 clean atomic commits `fd77d22..78ced25` + Commit #10 RC docs; 141 excluded/unclear files cleanly left outside stage).
- Timeout alignments (`ProveModeService` `35s`/`40s` + DB `15s`/`23s`/`20s`) & Redis `maxmemory=512mb`: **CLOSED & VERIFIED**.

## 2. Production Deployment Blockers (Pre-Launch Ops — NOT Merge Blockers)
1. **Production Host Secrets & TLS**: Điền `.env.prod` thật (64-hex `SECRET_KEY`, `FERNET_KEY`, `CALENDAR_ENCRYPTION_KEY`, `REDIS_PASSWORD`, HTTPS `FRONTEND_URL`/`BACKEND_CORS_ORIGINS`/`CSRF_TRUSTED_ORIGINS`) và đặt Caddy/Nginx TLS reverse proxy phía trước `:8080`.
2. **Production Transactional SMTP**: Cấu hình & smoke-test gửi OTP thật qua SMTP (không dùng Mailpit).
3. **Off-Host Automated Backup Cron**: Cài cron chạy `scripts/backup_postgres.sh` hàng ngày đẩy lên object storage mã hóa (S3/R2/GCS) với retention 14 ngày.
4. **Monitoring & Alerts**: Bật uptime probe `/api/health`, cảnh báo disk/RAM/Redis memory/Outbox age/LLM spend.

## 3. Accepted Deferred Findings (Free Beta Only)
- **`AUD-MED-03`** (`access_token` trong JSON body — FE dùng HttpOnly cookie): Accepted for Free Beta; gỡ trong PR breaking-change ≤ 30 ngày.
- **`AUD-MED-11`** (Offline mock adapters & non-Gemini tool parity): Accepted for Free Beta (production dùng Gemini + Google Calendar).
- **`AUD-LOW-04`** (Stateless access token 15m window sau logout): Accepted for Free Beta (refresh family thu hồi nguyên tử); thêm `token_version`/JTI trước Paid Tier.
- **`AUD-HIGH-11`** (Live payment gateway): **FEATURE-GATED (`FREE_BETA`)** — **NO-GO cho `PAID_ENABLED`** cho đến khi tích hợp & sandbox-test cổng thanh toán thật.
