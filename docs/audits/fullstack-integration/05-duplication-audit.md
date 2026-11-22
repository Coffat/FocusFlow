# Code Duplication & Reusability Audit — FocusFlow

> **Audit Target**: FocusFlow Fullstack Codebase  
> **Auditor**: Principal Fullstack Engineer & Software Architecture Auditor  
> **Date**: 2026-11-20  
> **Scope**: Frontend (`frontend/src/app`), Backend (`backend/src/`), Taskiq Workers  
> **Standards**: DRY (Don't Repeat Yourself), Modular Monolith Reusability, Hexagonal Port & Adapter Patterns

---

## 1. Executive Summary

This audit targeted redundant, orphaned, and duplicated code across the frontend and backend. While the core domain logic in backend bounded contexts is well-structured, several structural and functional duplications have emerged:

1. **Orphaned Parallel Implementations in Frontend**: Multiple legacy files from earlier development iterations exist alongside modern replacements (e.g. two auth interceptors, two auth guards, two login pages, two dashboards, and two footers).
2. **Duplicated Server State & HTTP Requests (`FE-DUP-07`)**: Four separate services maintain four duplicate `roadmaps` signal arrays and duplicate `loadRoadmaps()` API calls.
3. **Duplicate Broker Task Registrations (`BE-DUP-01`)**: Identical Taskiq background tasks are registered twice on the message broker under identical names in different contexts, creating non-deterministic job routing.
4. **Repeated Business Logic**: Date manipulation arithmetic, interval collision checks, and task rescheduling logic are repeated in multiple locations.

---

## 2. Duplication Catalog & Consolidation Matrix

| Finding ID | Severity | Category | Duplicated Implementations | Canonical Target | Action & Recommendation |
|---|---|---|---|---|---|
| **FE-DUP-01** | **MEDIUM** | Frontend / Interceptor | `app/interceptors/auth.interceptor.ts` vs `core/interceptors/auth.interceptor.ts` | `core/interceptors/auth.interceptor.ts` | **Delete** legacy outer interceptor. |
| **FE-DUP-02** | **HIGH** | Frontend / Route Guard | `app/guards/auth.guard.ts` (checks localStorage) vs `core/guards/auth.guard.ts` (checks session) | `core/guards/auth.guard.ts` | **Switch import** in `app.routes.ts` and **delete** legacy guard. |
| **FE-DUP-03** | **LOW** | Frontend / Layout Components | `shared/components/footer` & `header` vs `layout/main-layout/app-footer` & `app-navbar` | `layout/main-layout/*` | **Delete** orphaned shared header and footer. |
| **FE-DUP-04** | **MEDIUM** | Frontend / Auth Pages | `features/auth/components/login-page.component.ts` & `auth.routes.ts` vs `features/auth/sign-in/*` | `features/auth/sign-in/*` | **Delete** orphaned login page and unused auth routes. |
| **FE-DUP-05** | **LOW** | Frontend / Dashboard View | `dashboard-page.component.ts` (129 lines) vs `dashboard.component.ts` | `dashboard.component.ts` | **Delete** orphaned dashboard-page component. |
| **FE-DUP-06** | **LOW** | Frontend / Re-export Facades | 3 single-line re-export files in `features/roadmaps/` | Direct canonical file imports | **Delete** 3 re-export facades; update direct imports. |
| **FE-DUP-07** | **MEDIUM** | Frontend / Repeated API Call | `loadRoadmaps()` in `RoadmapService`, `TaskService`, `ScheduleService`, `AnalyticsService` | `core/stores/roadmap.store.ts` | **Centralize** in a single reactive roadmap store. |
| **FE-DUP-08** | **MEDIUM** | Frontend / Repeated Mutation | `rescheduleTask()` in `TaskService#L244` vs `ScheduleService#L218` | `TaskService.rescheduleTask()` | **Delegate** `ScheduleService` call to `TaskService`. |
| **FE-DUP-09** | **LOW** | Frontend / Utility Math | Monday date calculation in `schedule.service.ts`, `analytics.service.ts`, `workspace-session.service.ts` | `core/utils/date.util.ts` | **Extract** into shared date utility. |
| **BE-DUP-01** | **MEDIUM** | Backend / Taskiq Task Registration | `sync_schedule_blocks_to_google` & `sweep_overdue_tasks_and_anti_loop` registered in 2 contexts each | Designate 1 owner context per task | **Consolidate** tasks to Account and Execution respectively. |
| **BE-DUP-02** | **LOW** | Backend / Collision Detection | Time interval overlap logic (`s1 < e2 and s2 < e1`) in `hybrid_availability_rule_engine.py` & `spatio_temporal_engine.py` | `shared_kernel/domain/value_objects/time_interval.py` | **Extract** shared `Interval.overlaps_with()` value object. |

---

## 3. Detailed Duplication Analyses & Migration Plans

### [FE-DUP-01 & FE-DUP-02] Duplicate Auth Interceptors and Guards
- **Severity**: **HIGH** (Due to guard security bypass in FE-DUP-02)
- **Problem Analysis**:
  - `frontend/src/app/interceptors/auth.interceptor.ts` (28 lines) is an outdated functional interceptor that is NOT registered in `app.config.ts`. The real interceptor is `frontend/src/app/core/interceptors/auth.interceptor.ts` (91 lines).
  - Conversely, `app.routes.ts` imports the **legacy** guard `frontend/src/app/guards/auth.guard.ts` (which checks `localStorage.getItem('access_token')`) while the modern `frontend/src/app/core/guards/auth.guard.ts` (which checks `authService.checkSession()` with HttpOnly cookies) sits completely unused.
- **Consumer Impact**: Switching to the core guard enforces proper server-side session validation.
- **Migration Plan**:
  1. In `frontend/src/app/app.routes.ts`:
     Change: `import { authGuard } from './guards/auth.guard';`
     To: `import { authGuard } from './core/guards/auth.guard';`
  2. Delete `frontend/src/app/guards/auth.guard.ts` and `frontend/src/app/guards/auth.guard.spec.ts`.
  3. Delete `frontend/src/app/interceptors/auth.interceptor.ts` and `frontend/src/app/interceptors/auth.interceptor.spec.ts`.
  4. Run `pnpm exec ng test --watch=false` to verify zero broken imports.

---

### [FE-DUP-03, FE-DUP-04, FE-DUP-05] Orphaned Components & Dead Routes
- **Severity**: **MEDIUM**
- **Problem Analysis**:
  - `LoginPageComponent` (`frontend/src/app/features/auth/components/login-page.component.ts`) with selector `app-login-page` was created alongside `frontend/src/app/features/auth/auth.routes.ts`. However, `app.routes.ts` routes `/sign-in` directly to `SignInComponent` (`features/auth/sign-in/sign-in.component.ts`). The login page and route file are completely orphaned dead code.
  - `DashboardPageComponent` (`frontend/src/app/features/dashboard/components/dashboard-page.component.ts`, 129 lines) sits inside `components/` while the active dashboard is `frontend/src/app/features/dashboard/dashboard.component.ts`.
  - `frontend/src/app/shared/components/footer` and `header` are never imported by any layout.
- **Migration Plan**:
  1. Delete `frontend/src/app/features/auth/components/login-page.component.ts` and spec.
  2. Delete `frontend/src/app/features/auth/auth.routes.ts`.
  3. Delete `frontend/src/app/features/dashboard/components/dashboard-page.component.ts` and spec.
  4. Delete `frontend/src/app/shared/components/footer/` and `frontend/src/app/shared/components/header/`.

---

### [FE-DUP-07] Quadruple Repeated Roadmap Loading Logic
- **Severity**: **MEDIUM**
- **Problem Analysis**:
  Four separate services each implement their own `roadmaps = signal<RoadmapResponse[]>([])` and `loadRoadmaps()` HTTP call:
  ```typescript
  // In RoadmapService, TaskService, ScheduleService, AnalyticsService:
  loadRoadmaps(): void {
    this.http.get<RoadmapResponse[]>('/api/v1/roadmaps').subscribe({
      next: (data) => this.roadmaps.set(data),
      error: (err) => console.error(err)
    });
  }
  ```
  This creates 4 duplicate network requests on page switches, 4 disconnected signals in memory, and causes the stale status bugs identified in `FE-SYNC-01`.
- **Target Implementation**:
  Create `frontend/src/app/core/stores/roadmap.store.ts`:
  ```typescript
  @Injectable({ providedIn: 'root' })
  export class RoadmapStore {
    private readonly http = inject(HttpClient);
    readonly roadmaps = signal<readonly RoadmapResponse[]>([]);
    readonly activeRoadmap = computed(() => this.roadmaps().find(r => r.status === 'ACTIVE'));

    loadRoadmaps(force = false): void {
      if (this.roadmaps().length > 0 && !force) return;
      this.http.get<RoadmapResponse[]>('/api/v1/roadmaps').subscribe({
        next: (res) => this.roadmaps.set(res)
      });
    }

    invalidate(): void {
      this.loadRoadmaps(true);
    }
  }
  ```
- **Migration Plan**: Inject `RoadmapStore` into `TaskService`, `ScheduleService`, and `AnalyticsService`, removing their private signals.

---

### [BE-DUP-01] Duplicate Background Task Registrations on Taskiq Broker
- **Severity**: **MEDIUM**
- **Problem Analysis**:
  Two critical Taskiq background tasks are decorated with `@broker.task` in two separate files each:
  1. `sync_schedule_blocks_to_google`:
     - Registered in `backend/src/execution/presentation/tasks.py:437`
     - Registered in `backend/src/account/presentation/tasks.py:43`
  2. `sweep_overdue_tasks_and_anti_loop`:
     - Registered in `backend/src/execution/presentation/tasks.py:162`
     - Registered in `backend/src/evaluation/presentation/tasks.py:10`
- **Impact**:
  Taskiq registers tasks in a global dictionary keyed by task function name (`broker.tasks["sync_schedule_blocks_to_google"]`). Having duplicate definitions causes the second import to silently overwrite the first. When the worker or scheduler dispatches the task, which implementation executes depends entirely on Python module import order.
- **Migration Plan**:
  1. Consolidate `sync_schedule_blocks_to_google` into `account/presentation/tasks.py` (since Google Calendar OAuth credentials belong to the Account context). Remove the registration from `execution/presentation/tasks.py`.
  2. Consolidate `sweep_overdue_tasks_and_anti_loop` into `execution/presentation/tasks.py` (since Tasks belong to Execution). Remove the registration from `evaluation/presentation/tasks.py`.
  3. Validate task registration keys via `python -c "from src.shared_kernel.infrastructure.workers.broker import broker; print(broker.tasks.keys())"`.
