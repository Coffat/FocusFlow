# 03 — Reproducible Production Build & Runtime Verification (Phases 2 & 3)

- **Clean Checkout Source**: `git worktree` độc lập tại commit `1e72ef4` (`0` file untracked, không phụ thuộc working tree gốc).
- **Stack**: `docker compose -p focusflow-rc -f docker-compose.prod.yml --env-file .../scratch/rc.env` (`FRONTEND_PORT=18080`, `ENVIRONMENT=production`, `DEBUG=false`, `BILLING_RELEASE_MODE=FREE_BETA`, `REDIS_MAXMEMORY=512mb`, synthetic secrets riêng, không có `mailpit`/`--reload`/source bind mounts).
- **Verdict**: **BUILD PASS | STARTUP PASS | HEALTH PASS | FUNCTIONAL SMOKE PASS** (`RC-BLK-01` ĐÃ ĐÓNG DỨT ĐIỂM)

---

## 1. Gate-by-Gate Runtime Evidence

| Gate | Command / Endpoint | Exit / HTTP | Observed Evidence | Status |
|---|---|---:|---|---|
| **Compose Config** | `docker compose -p focusflow-rc -f docker-compose.prod.yml ... config --quiet` | `0` | Hợp lệ hoàn toàn (cả `--profile migrate`) | **PASS** |
| **Multi-Stage Build** | `docker compose -p focusflow-rc -f docker-compose.prod.yml ... build` | `0` | Build `focusflow-rc-backend` & `focusflow-rc-frontend` từ clean worktree trong **37s** | **PASS** |
| **One-Shot Migration** | `... --profile migrate run --rm migrate` | `0` | Áp dụng `0001` → `0015_add_notifications_table`; `alembic_version` xác nhận `0015_add_notifications_table` | **PASS** |
| **4-Container Startup & Health** | `... up -d backend frontend` | `0` | **ALL 4 HEALTHY** sau **5s** (`postgres`, `redis`, `backend`, **`frontend`** — `frontend/Dockerfile.prod` đã sửa sạch lỗi duplicate `pid`) | **PASS** |
| **Nginx SPA & Headers** | `GET http://127.0.0.1:18080/health`, `/`, `/pricing` | `200` | `text/html`, `<app-root>`, `Cache-Control: no-cache, no-store, must-revalidate`, đủ `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` | **PASS** |
| **Proxied API Health** | `GET http://127.0.0.1:18080/api/health` | `200` | `{"status":"healthy","database":"ok","redis":"ok"}` (0 metadata rò rỉ) | **PASS** |
| **Free Beta Billing Gate** | `GET /api/v1/account/billing/config`, `POST /billing/webhook` | `200` / `503` | `release_mode: "FREE_BETA"`, `checkout_enabled: false`, `mock_confirm_enabled: false`, `ai_monthly_limit: 300`; webhook fail-closed `503` | **PASS** |
| **Prod Security Controls** | `POST /auth/register`, `/auth/google` (fake), 11x `/auth/login` | `403` / `401` / `429` | Direct register `403 REGISTRATION_OTP_REQUIRED`; fake Google token `401`; lần 11 login trả **`429`** + `retry-after: 300` (xác nhận Redis auth rate limiter hoạt động) | **PASS** |
| **Redis Prod Config** | `CONFIG GET appendonly maxmemory maxmemory-policy` | `0` | `appendonly=yes`, `maxmemory=536870912` (512 MiB), `maxmemory-policy=noeviction` | **PASS** |
| **Graceful Restart** | `docker compose restart backend` → `GET :18080/api/health` | `200` | Phục hồi hoàn toàn trong **`4.61s`** | **PASS** |
| **Cleanup** | `down -v --remove-orphans`, xóa `rc.env` & `rc-clean-worktree` | `0` | `0` container/worktree tạm còn lại; staging `:3000` nguyên vẹn | **PASS** |

## 2. Production External Services Marked `NOT VERIFIED`
- Host-level HTTPS / TLS termination trên domain thật.
- Production transactional SMTP (gửi OTP thật qua mạng ngoài).
- Google Calendar HTTPS push webhook & RAG `EMBEDDING_API_KEY`.
