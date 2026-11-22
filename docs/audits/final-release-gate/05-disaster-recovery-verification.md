# 05 — Database & Redis Disaster Recovery Verification (Phase 3)

- **Scripts Created**: `scripts/backup_postgres.sh`, `scripts/restore_postgres.sh` (executable, `bash -n` verified, hỗ trợ Docker mode & direct `DATABASE_URL` mode, kiểm tra SHA-256 bắt buộc, chặn ghi đè khi thiếu `--confirm-target`).
- **Verdict**: **PASS (CLEAN-ROOM BACKUP/RESTORE DRILL VERIFIED; OFF-HOST SCHEDULED CRON & REDIS `maxmemory` CAP REQUIRED BEFORE PROD)**

---

## 1. Clean-Room PostgreSQL Backup & Restore Drill

Thực hiện trên 2 database tạm hoàn toàn cô lập (`focusflow_dr_source` → `focusflow_dr_restored`) trong `focusflow-postgres` (0 tác động đến `focusflow_db`):

| Check / Metric | Measured Evidence | Status |
|---|---|---|
| Clean baseline migration (`alembic upgrade head`) | `0001_account_avail` → `0015_add_notifications_table` | **PASS** |
| Synthetic round-trip row (`users`) | `11111111-2222-3333-4444-555555555555` (`dr-drill@focusflow.local`) | **PASS** |
| Backup duration (`scripts/backup_postgres.sh`) | **182 ms** (`pg_dump -Fc --no-owner --no-privileges`) | **PASS** |
| Dump size & SHA-256 checksum | **150,395 bytes (148 KB)**, SHA-256 verified | **PASS** |
| Overwrite safety guard (thiếu `--confirm-target`) | Từ chối với exit code `1` trước khi chạm DB | **PASS** |
| Restore duration / Raw RTO (`scripts/restore_postgres.sh`) | **359 ms** (`pg_restore --exit-on-error`) | **PASS** |
| Restored tables / triggers / version / extensions | **37** tables (36 app + `alembic_version`), **26** `BEFORE UPDATE` triggers, `0015_add_notifications_table`, `plpgsql:1.0, vector:0.8.7` | **PASS** |
| Synthetic user row integrity & temp cleanup | Bản ghi khớp 100%; cả 2 temp DB & file dump tạm đã xóa sạch | **PASS** |

---

## 2. Redis Persistence & Recovery Behavior (`focusflow-redis`)

- **Cấu hình thực tế**: `appendonly=yes`, `appendfsync=everysec`, `save="3600 1 300 100 60 10000"`, `aof_last_write_status=ok`, `aof_last_bgrewrite_status=ok`, `aof_current_size=13.78MB`, `used_memory_human=25.42M`, `maxmemory=0` (**khuyến nghị production đặt trần `maxmemory` tường minh**, vd `512mb`, kèm giám sát bộ nhớ).
- **Ảnh hưởng khi Redis restart / mất toàn bộ volume**:
  - **Sessions / Refresh Tokens**: Còn nguyên sau restart nhờ AOF (≤ 1s). Nếu mất toàn bộ volume, người dùng bị đăng xuất an toàn (phải đăng nhập lại, không hạ cấp bảo mật).
  - **Distributed Rate Limiting**: Bộ đếm cửa sổ reset về 0 nếu mất volume; khi Redis tạm ngắt, endpoint rủi ro cao (OTP/login-account/password-reset) fail-closed `503`.
  - **Outbox & Taskiq**: Nguồn chân lý là PostgreSQL `outbox_events` + `processed_events`; ngay cả khi mất Redis Streams, Outbox relay tự đọc lại từ Postgres với at-least-once + consumer idempotency.
  - **SSE & Checkpoints**: Stream đang mở bị ngắt (client thử lại); kết quả AI đã commit nằm bền vững trong PostgreSQL.
  - **AI Quotas**: **100% PostgreSQL (`SELECT ... FOR UPDATE`)** — mất Redis không bao giờ làm sai lệch hay bypass quota.

---

## 3. Realistic RPO / RTO Targets (Single-VPS Free Beta)

| Component | Target RPO | Target RTO | Verified vs Unverified |
|---|---|---|---|
| **PostgreSQL (Daily `pg_dump -Fc` to off-host S3/R2)** | **24 giờ** *(giảm xuống ≤ 5 phút khi nâng lên WAL/PITR)* | **< 5 phút** *(đã đo raw restore = **359ms** trên schema sạch; phần còn lại là tải dump & kiểm tra health)* | Raw restore **VERIFIED**; off-host cron & tải từ S3/R2 **NOT VERIFIED** (cần thiết lập trên VPS production). |
| **Redis (`AOF everysec`)** | **≤ 1 giây** (khi còn volume) / chấp nhận mất tạm thời | **< 1 phút** | AOF config **VERIFIED**; không cần backup riêng vì PG là System of Record. |
