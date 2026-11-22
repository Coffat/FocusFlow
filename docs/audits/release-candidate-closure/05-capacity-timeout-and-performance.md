# 05 — Capacity, Timeout Alignment & Performance Verification (Phase 5)

- **Target**: Live Docker staging (`http://127.0.0.1:3000`, 1 Uvicorn + 2 Taskiq workers + PG16 + Redis 7) + timeout fixes committed in `1e72ef4` & `78ced25`.
- **Verdict**: **PASS FOR FREE BETA (≤ 50 SUSTAINED CONCURRENT DB-ACTIVE CLIENTS; 100-CLIENT BURST 0.00% ERRORS; TIMEOUTS ALIGNED)**

---

## 1. Timeout Alignment (Closed in `release/free-beta-rc`)
- **Prove Mode FE vs BE**: `ProveModeService` truyền tường minh `HTTP_TIMEOUT_MS = 35_000` (`generateProof`, BE `20s`) và `40_000` (`submitProof`, BE `25s`) — xóa hoàn toàn rủi ro abort sớm ở `30s` `timeoutInterceptor`.
- **DB vs FE**: Lệch tầng DB timeouts trong `config.py` xuống `db_pool_timeout = 15.0s`, `db_statement_timeout_ms = 20000`, `db_command_timeout = 23.0s` (tất cả nhỏ hơn chặt `30.0s` FE default; `test_ai_circuit_breaker_resilience.py` & `test_db_pool_reliability.py` PASS).
- **SSE Chain**: BE hard cap `55s` < FE `EventSource` watchdog `90s` < Nginx `proxy_read_timeout 120s` (`proxy_buffering off`).
- **Connection Budget**: 1 Uvicorn (`≤20`) + 2 Taskiq workers (`≤40`) = **60 / 97** available PG16 connections (37 slot dự phòng).

## 2. Graduated Load Verification (`20 → 50 → 100` Concurrent Clients — 1,700 Requests)

| Tier | Concurrent | Reqs | Duration | Throughput | p50 (ms) | p95 (ms) | p99 (ms) | Error Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Tier 1 (20×10)** | 20 | 200 | 1.050s | **190.56 req/s** | 94.36 | **210.85** | 256.23 | **0.00%** |
| **Tier 2 (50×10)** | 50 | 500 | 2.682s | **186.43 req/s** | 262.55 | **501.40** | 622.37 | **0.00%** |
| **Tier 3 (100×10)** | 100 | 1,000 | 5.209s | **191.97 req/s** | 510.38 | **1,028.39** | 1,593.71 | **0.00%** |

- **Telemetry**: Backend RAM ổn định `503→516 MiB`, Redis `25.35M` / `14` clients, PG peak `idle in transaction = 20` (đúng trần pool 20) rồi xả sạch về **`0`** sau mỗi tier, Outbox rút sạch `10→0`.
- **Giới hạn trung thực**: Đã xác minh API đồng thời 20/50/100; tải đồng thời nhiều AI job live LLM không chạy stress test do giới hạn chi phí API (**NOT VERIFIED**). Khuyến nghị vận hành 1 VPS ở mức **≤ 50 người dùng DB-active đồng thời**.
