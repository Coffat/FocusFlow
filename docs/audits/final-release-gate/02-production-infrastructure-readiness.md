# 02 — Production Infrastructure & Configuration Readiness (Phases 1 & 2)

- **Target Topology**: Single-VPS Docker Compose (1 API + 2 Taskiq workers + 1 single-replica scheduler + PostgreSQL 16 + Redis 7 + Nginx SPA) phía sau host-level TLS reverse proxy (Caddy/Nginx).
- **Verdict**: **CONFIG READY (COMPOSE SYNTAX VERIFIED; PROD IMAGE BUILD & LIVE PROD SMTP/TLS NOT VERIFIED ON PROD HOST)**

---

## 1. Production Manifests Created (Standalone, Không Chạm File Dev)

| File | Purpose & Verified Production Controls | Validation Status |
|---|---|---|
| `docker-compose.prod.yml` | Topology độc lập không có `mailpit`, không có `--reload`, không có bind mount `./backend:/app` hay `./frontend:/app`; mạng nội bộ `focusflow-internal` (không mở public port 5432/6379/8000); `json-file` log rotation (`20m × 5`); CPU/RAM limits; `restart: unless-stopped`; `migrate` service chạy 1 lần qua `--profile migrate`; Redis `--appendonly yes --requirepass`; `BILLING_RELEASE_MODE=FREE_BETA`. | **PASS** (`docker compose -f docker-compose.prod.yml --env-file .env.prod.example config --quiet` exit `0`, kể cả `--profile migrate`) |
| `backend/supervisord.prod.conf` | Uvicorn không `--reload`, `--proxy-headers`, `--forwarded-allow-ips` giới hạn dải private/loopback, `--timeout-graceful-shutdown 25`, `stopsignal=TERM` (`stopwaitsecs=30`), `taskiq worker --workers 2`, `taskiq scheduler` (`numprocs=1`), toàn bộ log đẩy ra `stdout/stderr`. | **VERIFIED** (cấu trúc & tham chiếu từ `docker-compose.prod.yml`) |
| `frontend/Dockerfile.prod` | Multi-stage build: `node:22-alpine` (`pnpm@10.33.0`, `--frozen-lockfile`, `ng build --configuration production`) → `nginx:1.27-alpine` copy `/app/dist/focusflow-frontend/browser` (đã xác minh khớp `frontend/angular.json:24`), chạy non-root `USER nginx` port `8080` có `HEALTHCHECK`. | **PATH VERIFIED / DOCKER BUILD NOT EXECUTED** |
| `frontend/nginx.prod.conf` | SPA `try_files`, `gzip`, `client_max_body_size 25m` (khớp 20MB RAG upload), cache bất biến cho asset có hash, `no-cache` cho `index.html`, security headers (`nosniff`, `DENY`, `strict-origin-when-cross-origin`), `/api/` proxy với `proxy_buffering off`, `proxy_read_timeout 120s`, `proxy_connect_timeout 10s`, bảo toàn `X-Forwarded-Proto`. | **VERIFIED** |
| `.env.prod.example` | Template biến môi trường production đầy đủ, **0 secrets thật** (chỉ chứa placeholder an toàn). | **VERIFIED** |

---

## 2. Secrets, HTTPS & Startup Fail-Closed Verification (Phase 2)

| Configuration Item | Code Fail-Closed Behavior | Production Prerequisite | Status |
|---|---|---|---|
| `SECRET_KEY` | `config.py` chặn startup nếu rỗng hoặc dùng default ở `production` | Sinh 64-hex random (`openssl rand -hex 32`) | **VERIFIED (Code)** |
| `FERNET_KEY` & `CALENDAR_ENCRYPTION_KEY` | `config.py` (`AUD-LOW-01`) fail-closed ở `production` nếu `calendar_provider=google` thiếu/sai khóa Fernet | Sinh khóa Fernet hợp lệ riêng | **VERIFIED (Code)** |
| `DEBUG` & `ENVIRONMENT` | `config.py` chặn `DEBUG=true` ở `staging`/`production` | Đặt `ENVIRONMENT=production`, `DEBUG=false` | **VERIFIED (Code)** |
| `FRONTEND_URL`, `BACKEND_CORS_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | `config.py` từ chối wildcard `*`; `CSRFProtectionMiddleware` chỉ tin allowlist server | Khai báo chính xác HTTPS origin (vd `https://app.focusflow.vn`) | **VERIFIED (Code + Live)** |
| Trusted Reverse Proxies | `rate_limiter.py` chỉ đọc `X-Forwarded-For` khi peer thuộc `RATE_LIMIT_TRUSTED_PROXIES`; `supervisord.prod.conf` giới hạn `--forwarded-allow-ips` | Khớp CIDR Docker network / host reverse proxy | **VERIFIED (Code)** |
| Cookie Security | `HttpOnly; Secure; SameSite=Lax`; `refresh_token` `Path=/api/v1/auth` | Chấm dứt TLS ở host proxy (Caddy/Nginx) | **VERIFIED (Live Staging)** |
| Redis Auth & Persistence | `docker-compose.prod.yml` bật `--requirepass ${REDIS_PASSWORD}` & `--appendonly yes` | Bổ sung `--maxmemory 512mb` (hoặc phù hợp VPS) | **CONFIGURED** |
| `BILLING_RELEASE_MODE=FREE_BETA` | Fail-closed `503`/`403`; không cho kích hoạt mock payment ngoài dev/test | Giữ `FREE_BETA` khi launch | **VERIFIED (Live Staging)** |
| Production SMTP & AI Keys | Code hỗ trợ SMTP thật & Gemini/Embedding keys | **NOT VERIFIED LIVE**: chưa chạy gửi OTP qua SMTP production thật và chưa bật `EMBEDDING_API_KEY` | **PREREQUISITE BEFORE LAUNCH** |

---

## 3. Scaling Roadmap (Ghi nhận không overengineer)

- **Free Beta (Single VPS)**: 1 container `backend` (1 Uvicorn + 2 Taskiq workers = max 60/97 PG16 connections), 1 `frontend` Nginx, 1 `postgres`, 1 `redis`.
- **Khi vượt 1 VPS**: Tách `postgres` sang Managed PostgreSQL + PgBouncer, chạy `migrate` thành pre-deploy CI/CD job, tách `api` (scale N) khỏi `worker` (scale M) và giữ `scheduler` = 1 replica duy nhất.
