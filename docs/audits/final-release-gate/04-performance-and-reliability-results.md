# 04 — Performance, Reliability & Timeout Consistency Results (Phase 5)

- **Target**: Live Docker staging (`http://127.0.0.1:3000`, 1 Uvicorn + 2 Taskiq workers + PG16 + Redis 7)
- **Workload Defined**: **120 authenticated HTTP requests** (20 concurrent × 6 endpoints) trên tài khoản thật có Roadmap/Tasks + 2x concurrent refresh token race + backend restart recovery measurement.
- **Verdict**: **PASS WITH 2 TIMEOUT-ALIGNMENT FOLLOW-UPS (NO BLOCKING LATENCY OR LEAK DEFECTS)**

---

## 1. Free Beta Workload Benchmark (`p3_perf_gate.py`)

Tổng thời gian thực thi burst 120 requests: **`967.74 ms`**, tỷ lệ lỗi tổng thể: **`0.00%`**.

| Endpoint | Requests | Min (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | Error Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| `GET /api/health` *(probes PG + Redis)* | 20 | 337.56 | **341.23** | **345.17** | **345.36** | 345.41 | 0.0% |
| `GET /api/v1/auth/me` | 20 | 35.05 | **51.55** | **56.12** | **56.33** | 56.39 | 0.0% |
| `GET /api/v1/account/profile` | 20 | 77.71 | **105.91** | **150.78** | **153.56** | 154.26 | 0.0% |
| `GET /api/v1/account/billing/config` | 20 | 18.38 | **21.16** | **21.42** | **21.47** | 21.49 | 0.0% |
| `GET /api/v1/evaluation/dashboard-summary` | 20 | 153.49 | **204.50** | **227.30** | **231.01** | 231.93 | 0.0% |
| `GET /api/v1/tasks` | 20 | 84.31 | **109.05** | **121.56** | **123.42** | 123.89 | 0.0% |

*(Lưu ý trung thực: Kết quả này chỉ chứng minh tải burst 20 đồng thời cho các API đọc/điều phối lõi trên 1 VPS. Chưa thực hiện soak test 100+ concurrent users hoặc tải đồng thời nhiều AI job kéo dài — khuyến nghị giới hạn cohort Free Beta ban đầu ≤ 50–100 người dùng hoạt động đồng thời và theo dõi metrics thực tế.)*

---

## 2. Concurrency, Resource Utilization & Restart Recovery

- **Concurrent Refresh Token Race (2 simultaneous `/auth/refresh` với cùng 1 token)**:
  - Worker 2: `200 OK` (`14.83ms`), Worker 1: `401` (`Refresh token reuse detected. Session family has been revoked.`).
  - Replay token cũ & token xoay vòng của Worker 2: cả hai đều trả `401` (**0 dual valid tokens tồn tại**).
- **PostgreSQL 16 (`pg_stat_activity`)**: `16 idle` + `1 active` = **17 connections** (nằm gọn trong trần 60/97), **`0 idle in transaction`**.
- **Outbox**: `2 PENDING` mới tạo trong benchmark → rút sạch về **`0 PENDING`** (`PUBLISHED: 3,526`) sau 1 tick scheduler.
- **Redis 7**: `24 connected_clients`, `25.44M` memory, `aof_enabled: 1`, `aof_last_bgrewrite_status: ok`.
- **Backend Restart Recovery**: `docker compose restart backend` → `GET /api/health` trả `200 {"status":"healthy","database":"ok","redis":"ok"}` sau **`11.045s`** (`1.59s` restart + `9.455s` startup/readiness).

---

## 3. Timeout Consistency Audit (2 Non-Critical Mismatches Identified)

| Layer | Configured Value | Alignment Assessment |
|---|---|---|
| Angular `timeoutInterceptor` | `30.0s` (`HTTP_TIMEOUT_MS` chưa được truyền ở service nào) | **MISMATCH #1 (MEDIUM-HIGH)** với Prove Mode Grader (`25.0s` LLM deadline + DB/quota overhead có thể vượt `30.0s` gây abort sớm ở FE trong khi BE vẫn chấm xong → người dùng thử lại bị `409`). |
| Angular SSE `ai-sse.service.ts` | `90.0s` inactivity watchdog (native `EventSource` không qua `timeoutInterceptor`) | **ALIGNED** (`90s > 55s` BE SSE hard timeout; keepalive mỗi `10s`). |
| Nginx Prod Proxy (`nginx.prod.conf`) | `proxy_read_timeout 120s`, `proxy_connect_timeout 10s`, `proxy_buffering off` | **ALIGNED** (`120s > 90s > 55s`). |
| Backend DB Timeouts (`config.py`) | `statement_timeout=30s`, `command_timeout=30s`, `pool_timeout=30s` | **MISMATCH #2 (MEDIUM)**: trùng khít `30.0s` với nhau và với Angular `30.0s` (nguy cơ race giữa asyncpg cancel và PG `QueryCanceledError`). |
| `docker-compose.yml` (dev) | `AI_PROPOSAL_FINALIZE_RESERVE_SECONDS=14` (ghi đè default `6.0` của `config.py`) | Đã khớp `6.0` trong `.env.prod.example`. |

**Khuyến nghị đưa vào backlog tiền-launch (không sửa trong audit phase)**:
1. Truyền `HTTP_TIMEOUT_MS = 40_000` cho `submitMilestoneProof` và `35_000` cho `generateMilestoneProof` trong `ProveModeService`.
2. Lệch tầng DB timeouts: `db_statement_timeout_ms=20000`, `db_command_timeout=23.0`, `db_pool_timeout=15.0` (đều nhỏ hơn `30.0s` FE).
