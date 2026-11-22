# Mock Data, Fake Implementation & Placeholder Audit — FocusFlow

> **Audit Target**: FocusFlow Fullstack Codebase  
> **Auditor**: Principal Fullstack Engineer & Software Architecture Auditor  
> **Date**: 2026-11-20  
> **Scope**: Frontend (`frontend/src/app`), Backend (`backend/src/`), Database Adapters  
> **Standards**: SRS v1.3, ADR-001..ADR-010, `AGENTS.md` (Zero ungrounded mocks in production)

---

## 1. Executive Summary & Classification Methodology

A comprehensive line-by-line inspection was conducted across all frontend components and backend services to detect fake data, hardcoded numbers, silent error fallbacks, dead buttons, client-side fake CRUD, and background task stubs.

Every identified finding is classified into one of four objective tiers:

1. **Category 1: Valid Mock for Test / Dev**: Explicit mock fixtures in `tests/`, `tests/ai_evals/`, or isolated mock adapters (`MockLiteLLMAdapter`, `MockEmbeddingAdapter`, `MockCalendarAdapter`) enabled ONLY via environment flags (`LLM_PROVIDER=mock`, `CALENDAR_PROVIDER=local_mock`).
2. **Category 2: Valid Static Content**: Immutable configuration constants, navigation labels, i18n copy, UI typography presets, or architectural default limits.
3. **Category 3: Invalid Mock in Production**: Hardcoded numbers, fake objects, or stubbed methods active in production code paths that masquerade as real backend data.
4. **Category 4: Mock Fallback Hiding API Integration Errors**: Catch blocks that silently swallow HTTP or database exceptions and inject synthetic data, deceiving users and masking infrastructure failures.

---

## 2. Mock & Fake Implementation Catalog

| Finding ID | Severity | Classification Tier | Affected File & Lines | Description / Summary |
|---|---|---|---|---|
| **FE-MOCK-01** | **HIGH** | Tier 4 (Silent Fallback) | `frontend/.../settings.service.ts#L64-L74` | Quota API failure silently injects fake mock quota (10 limit, 2 used, 3450 tokens). |
| **FE-MOCK-02** | **HIGH** | Tier 3 (Fake Implementation) | `frontend/.../settings-page.component.ts#L941-L942`, `settings.service.ts#L94-L99` | Static WebCal token initialized; reset generates fake URL via `Math.random().toString(36)`. |
| **FE-MOCK-03** | **MEDIUM** | Tier 3 (Fake Implementation) | `frontend/.../settings-page.component.ts#L1200-L1218` | GDPR data export dumps client-side memory JSON, ignoring all backend study history. |
| **FE-MOCK-04** | **HIGH** | Tier 3 (Dead Action) | `frontend/.../settings-page.component.ts#L1277-L1304` | GDPR Account Deletion confirmation is a no-op that fires a UI toast without any backend request. |
| **FE-MOCK-05** | **MEDIUM** | Tier 3 (Hardcoded Data) | `frontend/.../profile.service.ts#L28-L32` | Zimmerman SRL metrics (45m, 1.05x bias, Sequential Deep Work) hardcoded in static signal. |
| **FE-MOCK-06** | **HIGH** | Tier 3 (UI-Only Stub) | `frontend/.../admin-dashboard-page.component.ts#L117-L134` | Admin dashboard has hardcoded 0s for AI telemetry, empty users array, local memory quota button. |
| **FE-MOCK-07** | **LOW** | Tier 3 (Placeholder Defaults) | `frontend/.../adaptation-modal-dialog.component.ts#L29-L33` | Hardcoded default inputs displayed on Dashboard when dialog opens un-bound. |
| **FE-MOCK-08** | **MEDIUM** | Tier 3 (Dead Button) | `frontend/.../app-navbar.component.html#L65-L71` | Navbar notification bell has no `(click)` binding, no notification store, and no alerts API. |
| **FE-MOCK-09** | **MEDIUM** | Tier 3 (LocalStorage CRUD) | `frontend/.../workspace-session.service.ts#L930-L983` | Daily Pomodoro count increments and reads `focusflow_pomodoros_today_v1` in `localStorage`. |
| **BE-MOCK-01** | **HIGH** | Tier 3 (Stub Implementation) | `backend/src/account/presentation/tasks.py#L10-L13` | Sweeper `sweep_expired_ai_quota_reservations` returns `0` without calling adapter method. |
| **BE-MOCK-02** | **MEDIUM** | Tier 3 (Stub Implementation) | `backend/src/account/presentation/tasks.py#L16-L19` | Taskiq consumer `aggregate_learner_srl_profile` returns `None` without recalculating metrics. |
| **BE-MOCK-03** | **MEDIUM** | Tier 3 (Stub Implementation) | `backend/src/execution/presentation/tasks.py#L431-L434` | Taskiq task `sync_external_google_calendar` is a dead stub returning `None`. |
| **BE-INT-02** | **HIGH** | Tier 3 (Stubbed Relay) | `backend/src/shared_kernel/infrastructure/outbox/relay.py#L10-L29` | Outbox relay marks `PENDING` events `PUBLISHED` without dispatching them to workers. |

---

## 3. Detailed Structured Audit Findings

### [FE-MOCK-01] Silent AI Quota Fallback with Hardcoded Mock Numbers
- **Severity**: **HIGH**
- **Category**: Mock Fallback Hiding API Errors (Tier 4)
- **Affected Pages/Modules**: `/settings` (SettingsPageComponent, SettingsService)
- **File Path + Line Numbers**: [frontend/src/app/features/settings/services/settings.service.ts#L64-L74](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/settings/services/settings.service.ts#L64-L74)
- **Expected Behavior**: When the quota endpoint `/api/v1/account/quota` fails or is unreachable, the error should be surfaced to the user or an error state recorded, clearly indicating that quota telemetry is currently unavailable.
- **Actual Behavior**: The catch block silently swallows the HTTP error and populates the store with fabricated numbers:
  ```typescript
  // Fallback with realistic initial mock if quota endpoint is unreachable
  this.quota.set({
    monthly_limit: 10,
    used_calls: 2,
    reserved_calls: 0,
    remaining_calls: 8,
    tokens_consumed: 3450,
    cycle_start: new Date(Date.now() - 7 * 86400000).toISOString(),
    cycle_end: new Date(Date.now() + 23 * 86400000).toISOString(),
  });
  ```
- **Root Cause / Hypothesis**: Prototype mock left in place as a catch fallback during early development.
- **Evidence**: `settings.service.ts` lines 64-74.
- **Impact**: Masking backend network or database failures; learners believe they have 8 calls and 3450 tokens remaining even if their session is expired.
- **Recommended Fix**: Remove the fallback mock object. Expose an `errorState` signal in `SettingsService` and display an inline retry banner in `SettingsPageComponent`.
- **Validation Steps**: Disconnect backend; navigate to `/settings`; verify that an error message is displayed rather than "8 lượt còn lại".
- **Confidence Level**: 100%

---

### [FE-MOCK-02] Fake WebCal URL Generation & Hardcoded Static Secret
- **Severity**: **HIGH**
- **Category**: Fake Implementation / Stub (Tier 3)
- **Affected Pages/Modules**: `/settings` (Calendar Tab)
- **File Path + Line Numbers**:
  - [frontend/src/app/features/settings/services/settings.service.ts#L94-L99](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/settings/services/settings.service.ts#L94-L99)
  - [frontend/src/app/features/settings/components/settings-page.component.ts#L941-L942](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/settings/components/settings-page.component.ts#L941-L942)
- **Expected Behavior**: WebCal feed URL and token should be loaded from the backend (table `webcal_tokens`), where the token is hashed via SHA-256 (ADR-008). Regenerating the token should invoke a backend POST endpoint.
- **Actual Behavior**:
  - `SettingsPageComponent` initializes `webcalUrl` with a hardcoded static string:
    ```typescript
    readonly webcalUrl = signal<string>(
      'webcal://focusflow.app/api/v1/calendar/feed.ics?token=ff_live_sec_789123'
    );
    ```
  - When the user clicks "Tạo lại liên kết WebCal", `settingsService.resetWebCalToken()` returns a completely fake URL constructed with `Math.random()`:
    ```typescript
    return {
      webcal_url: 'webcal://focusflow.app/api/v1/calendar/feed.ics?token=ff_live_' + Math.random().toString(36).substring(2, 12),
    };
    ```
- **Root Cause / Hypothesis**: Frontend UI was built before backend WebCal use cases were exposed.
- **Evidence**: `settings.service.ts` lines 94-99, `settings-page.component.ts` lines 941-942.
- **Impact**: Any learner copying this link into Apple Calendar, Google Calendar, or Outlook receives a broken URL with a non-existent token.
- **Recommended Fix**: Implement backend WebCal endpoints (`GET /api/v1/account/calendar/webcal`, `POST /api/v1/account/calendar/webcal/reset`) and connect `SettingsService` to them.
- **Validation Steps**: Click "Tạo lại liên kết" in Settings; verify network tab issues an authenticated POST request and receives a valid token signed by backend.
- **Confidence Level**: 100%

---

### [FE-MOCK-03] Fake GDPR Data Export Masquerading as Complete Archive
- **Severity**: **MEDIUM**
- **Category**: Fake Implementation (Tier 3)
- **Affected Pages/Modules**: `/settings` (Security & Privacy Tab)
- **File Path + Line Numbers**: [frontend/src/app/features/settings/components/settings-page.component.ts#L1200-L1218](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/settings/components/settings-page.component.ts#L1200-L1218)
- **Expected Behavior**: According to GDPR Article 20 and SRS requirements, data export should request an aggregated archive from the backend containing user roadmaps, milestones, tasks, Pomodoro sessions, key takeaways, and learner memory.
- **Actual Behavior**: The "Tải xuống dữ liệu (JSON)" button executes an entirely client-side script that bundles only the in-memory user profile and UI preferences:
  ```typescript
  const data = {
    user: this.authService.currentUser(),
    preferences: this.preferences(),
    exported_at: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  ```
- **Root Cause / Hypothesis**: Frontend stub created to satisfy visual design without an export API endpoint on backend.
- **Evidence**: `settings-page.component.ts` lines 1200-1218.
- **Impact**: False compliance claim. Users exporting their data do not receive any of their study logs, roadmaps, or learning progress.
- **Recommended Fix**: Call backend export endpoint or clearly label the button as "Xuất cấu hình giao diện" until a comprehensive GDPR export endpoint is implemented.
- **Validation Steps**: Click "Tải xuống dữ liệu (JSON)"; examine the downloaded file to verify comprehensive entity data.
- **Confidence Level**: 100%

---

### [FE-MOCK-04] Fake GDPR Account Deletion (Dead Action)
- **Severity**: **HIGH**
- **Category**: Dead Action / Unimplemented Security Feature (Tier 3)
- **Affected Pages/Modules**: `/settings` (Security & Privacy Tab)
- **File Path + Line Numbers**: [frontend/src/app/features/settings/components/settings-page.component.ts#L1277-L1304](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/settings/components/settings-page.component.ts#L1277-L1304)
- **Expected Behavior**: Confirming "Xóa tài khoản vĩnh viễn" (GDPR Article 17) should trigger a DELETE request to the backend, invalidate session cookies, and redirect to the landing page.
- **Actual Behavior**: Confirming the deletion modal only fires a PrimeNG toast message:
  ```typescript
  accept: () => {
    this.messageService?.add({
      severity: 'warn',
      summary: 'Đang gửi yêu cầu',
      detail: 'Yêu cầu xóa tài khoản đã được chuyển đến bộ phận bảo mật GDPR.',
      life: 5000,
    });
  }
  ```
  No HTTP request is made. The account remains active, session remains valid, and the user stays logged in.
- **Root Cause / Hypothesis**: Placeholder UI stub.
- **Evidence**: `settings-page.component.ts` lines 1277-1304.
- **Impact**: Severe compliance violation. Users believe their account has been scheduled for deletion, but zero action occurs.
- **Recommended Fix**: Implement backend DELETE endpoint (`DELETE /api/v1/account`) and call it from `SettingsService.deleteAccount()`, followed by `authService.signOut()` and navigation to `/`.
- **Validation Steps**: Click "Xóa tài khoản vĩnh viễn"; verify DELETE request is sent and user is signed out immediately.
- **Confidence Level**: 100%

---

### [FE-MOCK-05] Hardcoded Zimmerman SRL Metrics in Profile Service
- **Severity**: **MEDIUM**
- **Category**: Hardcoded Mock Data (Tier 3)
- **Affected Pages/Modules**: `/profile` (ProfilePageComponent, ProfileService)
- **File Path + Line Numbers**:
  - [frontend/src/app/features/profile/services/profile.service.ts#L28-L32](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/profile/services/profile.service.ts#L28-L32)
  - [frontend/src/app/features/profile/components/profile-page.component.ts#L325-L368](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/profile/components/profile-page.component.ts#L325-L368)
- **Expected Behavior**: Zimmerman SRL (Self-Regulated Learning) metrics—optimal session duration, completion rate bias, and dominant learning style—should be computed dynamically from the user's completed study sessions (evaluation context or learner profile).
- **Actual Behavior**: `ProfileService` initializes `srlMetrics` with static mock values that never change:
  ```typescript
  readonly srlMetrics = signal<SrlMetrics>({
    optSessionMinutes: 45,
    completionRateBias: 1.05,
    learningStyle: 'Tuần tự & Tập trung sâu (Sequential Deep Work)',
  });
  ```
- **Root Cause / Hypothesis**: Prototype values left hardcoded.
- **Evidence**: `profile.service.ts` lines 28-32, `profile-page.component.ts` lines 325-368.
- **Impact**: All users see identical metrics (45 minutes, 1.05x, Sequential Deep Work) regardless of their actual study behavior.
- **Recommended Fix**: Derive SRL metrics from `AnalyticsService.summary()` or load them from `/api/v1/account/learner-memory` / `/api/v1/evaluation/dashboard-summary`.
- **Validation Steps**: Complete multiple 25-minute Pomodoro sessions; verify optimal session length reflects actual user data.
- **Confidence Level**: 100%

---

### [FE-MOCK-06] Admin Dashboard 100% Disconnected UI Stub
- **Severity**: **HIGH**
- **Category**: UI-Only Stub / Missing Backend Connection (Tier 3)
- **Affected Pages/Modules**: `/admin` (AdminDashboardPageComponent)
- **File Path + Line Numbers**: [frontend/src/app/features/admin/components/admin-dashboard-page.component.ts#L117-L134](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/admin/components/admin-dashboard-page.component.ts#L117-L134)
- **Expected Behavior**: The admin portal (UC-18, UC-19) should display real AI telemetry (requests 24h, 3-tier pass rate, TTFT latency, tokens) and permit viewing and adjusting user quota.
- **Actual Behavior**: The component contains zero injected services and zero HTTP calls:
  ```typescript
  readonly aiMetrics = signal<AISystemMetricSummary>({
    totalRequests24h: 0,
    tier123PassRate: 0,
    avgLatencyMs: 0,
    totalTokensConsumed: 0
  });
  readonly users = signal<readonly AdminUserQuotaRow[]>([]);
  grantBonusQuota(userId: string): void {
    this.users.update(rows => rows.map(row => row.id === userId ? { ...row, remainingCredits: row.remainingCredits + 5 } : row));
  }
  ```
  The "+5 AI Quota" button only mutates an in-memory array that is initially empty anyway.
- **Root Cause / Hypothesis**: Skeleton component created for route testing without backend admin endpoints.
- **Evidence**: `admin-dashboard-page.component.ts` lines 117-134; OpenAPI `schema.d.ts` contains 0 admin endpoints.
- **Impact**: The `/admin` route is completely unusable in production.
- **Recommended Fix**: Either implement backend admin API endpoints or gate this route behind a "Coming Soon" guard and remove it from production navigation.
- **Validation Steps**: Open `/admin`; check that live telemetry is populated via real monitoring endpoint.
- **Confidence Level**: 100%

---

### [FE-MOCK-08] Dead Notification Bell in App Navbar
- **Severity**: **MEDIUM**
- **Category**: Dead Button / Unimplemented UI Element (Tier 3)
- **Affected Pages/Modules**: Main Layout (`app-navbar.component.html`)
- **File Path + Line Numbers**: [frontend/src/app/layout/main-layout/app-navbar/app-navbar.component.html#L65-L71](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/layout/main-layout/app-navbar/app-navbar.component.html#L65-L71)
- **Expected Behavior**: Clicking the notification bell should toggle a notification popover/drawer displaying system events, overdue task alerts, and Domino shift recommendations.
- **Actual Behavior**: The bell `<button>` has no `(click)` binding, no event handler, no notification badge, and no notification service. Clicking it does nothing.
- **Root Cause / Hypothesis**: Decorative icon placed in navbar markup without implementation.
- **Evidence**: `app-navbar.component.html` lines 65-71.
- **Impact**: Users attempting to view alerts find a non-responsive button.
- **Recommended Fix**: Implement `NotificationService` and bind `(click)="toggleNotifications()"` with a dropdown panel.
- **Validation Steps**: Click notification bell in navbar; verify notification panel opens.
- **Confidence Level**: 100%

---

### [FE-MOCK-09] Daily Pomodoro Count Relying on LocalStorage
- **Severity**: **MEDIUM**
- **Category**: LocalStorage as Backend Substitute (Tier 3)
- **Affected Pages/Modules**: `/workspace` (WorkspaceSessionService)
- **File Path + Line Numbers**: [frontend/src/app/core/services/workspace-session.service.ts#L930-L983](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/services/workspace-session.service.ts#L930-L983)
- **Expected Behavior**: Daily completed Pomodoro counts should be tracked reliably by the backend execution context (e.g. `today_focus.pomodoros_completed_today`) and synchronized across devices.
- **Actual Behavior**: The service increments and reads `focusflow_pomodoros_today_v1` in `localStorage`:
  ```typescript
  localStorage.setItem('focusflow_pomodoros_today_v1', JSON.stringify({ date: today, count: nextCount }));
  ```
  If a learner uses another browser or clears site data, the count is lost or desynchronized from the server's session record.
- **Root Cause / Hypothesis**: Client-side quick-counter added to supplement backend polling.
- **Evidence**: `workspace-session.service.ts` lines 930-983.
- **Impact**: Inconsistent Pomodoro statistics between multiple devices or after clearing browser cache.
- **Recommended Fix**: Rely primarily on `todayFocus().pomodoros_completed_today` from GET `/api/v1/sessions/today-focus`, and re-fetch `loadTodayFocus()` upon session finalization.
- **Validation Steps**: Complete a Pomodoro session in an incognito window; verify server count increments and is reflected across sessions.
- **Confidence Level**: 95%

---

### [BE-MOCK-01] Stubbed Taskiq Sweeper Fails to Expire AI Quota Reservations
- **Severity**: **HIGH**
- **Category**: Stub Implementation / Production Placeholder (Tier 3)
- **Affected Pages/Modules**: `account/presentation/tasks.py` (`sweep_expired_ai_quota_reservations`)
- **File Path + Line Numbers**: [backend/src/account/presentation/tasks.py#L10-L13](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/presentation/tasks.py#L10-L13)
- **Expected Behavior**: Taskiq cron task `sweep_expired_ai_quota_reservations` running every minute should query `ai_quota_reservations` where `expires_at <= now` and status is `RESERVED`, refund the reserved credits, and transition them to `EXPIRED`.
- **Actual Behavior**: The function body consists entirely of `return 0`:
  ```python
  @broker.task(schedule=[{"cron": "* * * * *"}])
  async def sweep_expired_ai_quota_reservations() -> int:
      """Sweep RESERVED AI quota locks older than expires_at and refund credits (ADR-003)."""
      return 0
  ```
- **Root Cause / Hypothesis**: Taskiq task was registered as a stub, even though `QuotaFacadeAdapter.expire_stale_reservations` is already implemented.
- **Evidence**: `account/presentation/tasks.py` lines 10-13.
- **Impact**: If an AI generation job crashes, times out, or disconnects without release, reserved AI quota calls remain permanently locked in `RESERVED` status, preventing students from using their allocated quota.
- **Recommended Fix**: Connect `sweep_expired_ai_quota_reservations` to `QuotaFacadeAdapter.expire_stale_reservations(now)`.
- **Validation Steps**: Insert a reservation with `expires_at = now - 5min`, execute task, verify status transitions to `EXPIRED` and return value is > 0.
- **Confidence Level**: 100%

---

### [BE-MOCK-02] Stubbed Taskiq Consumer for Learner SRL Profile Aggregation
- **Severity**: **MEDIUM**
- **Category**: Stub Implementation / Production Placeholder (Tier 3)
- **Affected Pages/Modules**: `account/presentation/tasks.py` (`aggregate_learner_srl_profile`)
- **File Path + Line Numbers**: [backend/src/account/presentation/tasks.py#L16-L19](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/presentation/tasks.py#L16-L19)
- **Expected Behavior**: `aggregate_learner_srl_profile` should recalculate learner SRL profile metrics (e.g. self-reflection habits, study consistency, preferred study time) upon `StudySessionCompletedEvent`.
- **Actual Behavior**: The function body is a dummy stub containing only `return None`:
  ```python
  @broker.task
  async def aggregate_learner_srl_profile(user_id: str) -> None:
      """Recalculate LearnerProfile SRL metrics upon StudySessionCompletedEvent."""
      return None
  ```
- **Root Cause / Hypothesis**: Skeleton handler created for event integration that was never implemented.
- **Evidence**: `account/presentation/tasks.py` lines 16-19.
- **Impact**: `learner_profiles` table metrics remain static and un-updated across study sessions.
- **Recommended Fix**: Implement SRL calculation service and connect to event subscriber.
- **Validation Steps**: Execute task with valid `user_id` and check that `learner_profiles` metrics are recalculated.
- **Confidence Level**: 100%

---

### [BE-INT-02] Broken Transactional Outbox Relay Fails to Dispatch Events
- **Severity**: **HIGH**
- **Category**: Broken Transactional Outbox / Stubbed Relay (Tier 3)
- **Affected Pages/Modules**: `shared_kernel/infrastructure/outbox/relay.py`, `execution/presentation/tasks.py`
- **File Path + Line Numbers**: [backend/src/shared_kernel/infrastructure/outbox/relay.py#L10-L29](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/outbox/relay.py#L10-L29)
- **Expected Behavior**: The outbox relay task (`relay_pending_outbox_events`) should read `PENDING` outbox events and publish them to message brokers (Redis Streams) or dispatch corresponding Taskiq worker tasks before updating status to `PUBLISHED`.
- **Actual Behavior**: `relay_pending_outbox_events` queries `PENDING` events and executes `event.status = "PUBLISHED"` directly in the database without publishing to any stream or notifying any consumer:
  ```python
  for event in events:
      event.status = "PUBLISHED"
      event.published_at = now
  if events:
      await session.commit()
  return len(events)
  ```
- **Root Cause / Hypothesis**: Stub implementation created during initial scaffolding; Redis Streams publishing was omitted.
- **Evidence**: `relay.py` lines 24-28.
- **Impact**: Events like `OverdueTaskAlertEvent` are marked `PUBLISHED`, but no worker ever reads them, meaning overdue alert emails are NEVER sent to learners.
- **Recommended Fix**: Integrate Redis Streams producer into `relay_pending_outbox_events` or dispatch corresponding consumers for registered event types.
- **Validation Steps**: Insert an event with status `PENDING`, run `relay_pending_outbox_events`, observe that status changes to `PUBLISHED` and corresponding consumer is triggered.
- **Confidence Level**: 100%
