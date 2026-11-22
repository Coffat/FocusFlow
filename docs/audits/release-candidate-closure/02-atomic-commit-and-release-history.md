# 02 — Atomic Commit & Release History (Phase 1)

- **Branch**: `release/free-beta-rc`
- **Ancestry from `main` (`345a55d`)**: 6 prior commits (`8999e2a..347066b`) + **9 verified atomic commits** (`fd77d22..78ced25`) + Commit #10 (bộ báo cáo RC Closure này).
- **Verdict**: **PASS**

---

## Atomic Commit Ledger (`347066b..78ced25`)

| # | Commit SHA | Files | Message |
|---:|---|---:|---|
| 1 | `fd77d22` | 147 | `feat(baseline): land P2A-P2B2B notifications, webcal, admin guard, prove mode UI and migrations 0014-0015` |
| 2 | `57a0769` | 21 | `fix(security): P0A remediation — Google SSO, billing webhook, DNS rebinding SSRF, eval quota, sticky note IDOR, password reset, OTP-only register` |
| 3 | `90ee297` | 17 | `fix(auth): P0B remediation — CSRF middleware, atomic RTR reuse detection, distributed Redis rate limiting and OTP E2E helpers` |
| 4 | `335dac4` | 14 | `fix(reliability): P1A remediation — RAG magic-byte/zip-bomb security, transactional outbox hardening and Playwright E2E stabilization` |
| 5 | `6a53cef` | 30 | `fix(reliability): P1B remediation — AI circuit breaker, PostgreSQL pooling/timeouts, Prove Mode grading correctness and 1-wave decomposition` |
| 6 | `2a03bea` | 20 | `feat(billing): P1C remediation — FREE_BETA vs PAID_ENABLED release gating, server-side billing config and SRS quota 300 alignment` |
| 7 | `af127cd` | 38 | `refactor(architecture): P2 remediation — cross-context query ports, backend/frontend hygiene, pagination and canonical schema.sql sync` |
| 8 | `1e72ef4` | 15 | `chore(release): P3 production compose/nginx/supervisord manifests, PostgreSQL DR scripts and final release gate reports` |
| 9 | `78ced25` | 1 | `test(reliability): align db timeout default assertions with tightened 15s/23s/20s config` |
| 10 | *(next)* | 9 | `docs(release): finalize RC Closure verification reports and main PR readiness` |

- Không giả lập timestamp, không rewrite lịch sử đã publish, không commit secrets hay 141 file ngoài phạm vi.
