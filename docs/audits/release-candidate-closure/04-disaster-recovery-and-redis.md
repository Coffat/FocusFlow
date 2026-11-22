# 04 — Disaster Recovery & Redis Persistence Verification (Phase 4)

- **Scripts**: `scripts/backup_postgres.sh`, `scripts/restore_postgres.sh` (committed in `1e72ef4`)
- **Drill Scope**: Isolated temp databases `focusflow_rc_dr_src` → `focusflow_rc_dr_dst` trong `focusflow-postgres` (0 tác động đến `focusflow_db`).
- **Verdict**: **PASS (MULTI-MB DR DRILL & REDIS AOF/MAXMEMORY VERIFIED; OFF-HOST CRON IS PRE-LAUNCH OPS TASK)**

---

## 1. Realistic Multi-MB PostgreSQL Drill (19,300 Rows / 24 MB)
- **Dataset**: `200` users, `200` ai_quotas, `400` goals, `400` roadmaps, `400` official_schedules, `1,200` milestones, `6,000` tasks, `6,000` schedule_blocks, `2,000` study_sessions, `2,000` notifications, `500` outbox_events (**19,300** rows, **24 MB** source DB).
- **Backup**: `scripts/backup_postgres.sh` → **`247 ms`**, dump `-Fc` **1,219,371 bytes (1.2 MB)** + SHA-256 verified (exit `0`).
- **Restore**: `scripts/restore_postgres.sh --confirm-target` → **`458 ms`** raw RTO, **25 MB** restored DB (exit `0`).
- **Integrity**: **19,300 / 19,300 rows (100% match)**, **59 / 59 FK constraints**, **37 tables**, **26 `BEFORE UPDATE` triggers**, `plpgsql:1.0, vector:0.8.7`, post-restore `alembic current` = `0015_add_notifications_table (head)` và `alembic upgrade head` exit `0`.

## 2. Redis Recovery & Persistence
- **Verified in `focusflow-rc` prod container**: `appendonly=yes`, `appendfsync=everysec`, `maxmemory=536870912` (512 MiB), `maxmemory-policy=noeviction`, `--requirepass` bật.
- **Failure Semantics**: AI Quotas (`SELECT ... FOR UPDATE`) & Outbox (`outbox_events`/`processed_events`) nằm 100% ở PostgreSQL → không mất dữ liệu hay bypass quota khi mất Redis; mất volume Redis chỉ khiến phiên đăng nhập reset an toàn (buộc đăng nhập lại).
- **Measured vs Target RPO/RTO**: Đo thực tế raw restore **458ms** (24 MB); mục tiêu vận hành Free Beta: PG **RPO 24h / RTO < 5 phút** (cài cron `backup_postgres.sh` đẩy off-host S3/R2 mã hóa trên VPS thật), Redis **RPO ≤ 1s (volume intact) / RTO < 1 phút**.
