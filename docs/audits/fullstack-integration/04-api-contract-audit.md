# API Integration & Data Contract Audit — FocusFlow

> **Audit Target**: API Endpoints, OpenAPI 3.1 Contracts, Pydantic DTOs & TypeScript Schemas  
> **Auditor**: Principal Fullstack Engineer & Software Architecture Auditor  
> **Date**: 2026-11-20  
> **Scope**: `backend/src/*/presentation/`, `frontend/src/app/core/api/schema.d.ts`, `frontend/src/app/core/constants/api-endpoints.ts`  
> **Standards**: OpenAPI 3.1, Pydantic v2, ADR-004, ADR-008, `AGENTS.md` (0 schema drift)

---

## 1. Executive Summary & Verification Metrics

FocusFlow maintains strict API contract hygiene using automated type generation (`scripts/check-api-contract.sh`) that compiles backend FastAPI Pydantic v2 schemas directly into `frontend/src/app/core/api/schema.d.ts` using `openapi-typescript`.

Runtime contract verification confirmed:
- **0 Schema Drift**: The generated TypeScript types match FastAPI OpenAPI 3.1 output with 0 diffs.
- **89 Total HTTP Endpoints** audited across backend routers.
- However, serious specification drift, security violations, and exception handling defects were discovered:
  1. **Rule 4 & ADR-008 Violation (`FE-API-04` — CRITICAL)**: Bearer tokens are persisted to and read from `localStorage` in `AuthService` and `authInterceptor`, violating the HttpOnly cookie-only security mandate.
  2. **Inverted Error Handling / False Success (`FE-API-03` — HIGH)**: Roadmaps Hub optimistically updates roadmap status to `ACTIVE` and fires a success toast inside the HTTP `error` callback of `resumeRoadmap()`.
  3. **Path Mismatches in Frontend Constants (`FE-API-01`, `BE-API-01` — HIGH)**: `API_ENDPOINTS.SETTINGS.PROFILE` and `QUOTA` point to non-existent `/api/v1/users/*` paths, forcing frontend services to bypass the constant map and hardcode strings.
  4. **Ghost Endpoints (`FE-API-02`, `BE-API-02` — MEDIUM)**: Dead paths for `BILLING` and `ADMIN` are defined in frontend constants, but corresponding backend routers do not exist.
  5. **Unhandled 500 on Input Validation (`BE-API-03` — MEDIUM)**: File and URL knowledge ingestion routes fail to catch `ValueError`, returning HTTP 500 instead of 400.
  6. **Unbounded Collection Listing (`BE-API-04` — MEDIUM)**: Zero listing endpoints implement pagination (`limit`/`offset`).

---

## 2. API Contract & Integration Findings Catalog

| Finding ID | Severity | Category | Affected File & Lines | Description / Summary |
|---|---|---|---|---|
| **FE-API-04** | **CRITICAL** | Security / Constitution | `auth.service.ts#L62-L65`, `auth.interceptor.ts#L20-L25` | Bearer token saved in `localStorage`; `Authorization` header attached instead of pure HttpOnly cookies. |
| **FE-API-03** | **HIGH** | Error Handling / False State | `roadmaps-hub.component.ts#L299-L307` | In `error` callback of `resumeRoadmap()`, UI forcefully sets status to `ACTIVE` and shows success toast! |
| **FE-API-01** | **HIGH** | Contract Path Mismatch | `api-endpoints.ts#L133-L135` | `SETTINGS.PROFILE` (`/api/v1/users/profile`) and `QUOTA` (`/api/v1/users/quota`) diverge from backend `/account/*`. |
| **FE-API-02** | **MEDIUM** | Ghost Endpoints | `api-endpoints.ts#L137-L141` | `ADMIN` endpoints defined in frontend constants do not exist on backend. |
| **FE-API-05** | **MEDIUM** | Missing Checkout UI | `api-endpoints.ts#L9-L12`, `pricing.component.ts#L209` | Billing checkout constant exists, but `/pricing` redirects to `/settings` with no checkout flow. |
| **BE-API-01** | **MEDIUM** | Contract Drift | `backend/src/`, `frontend/.../api-endpoints.ts` | Discarded paths (`BILLING`, `ADMIN`, `/users/profile`, `/roadmaps/active`) clutter frontend contracts. |
| **BE-API-02** | **MEDIUM** | Missing Application Layer | `backend/src/account/infrastructure/orm/user_orm.py` | Tables `payment_transactions` and `webcal_tokens` exist in DB/ORM, but have no use cases or routers. |
| **BE-API-03** | **MEDIUM** | Exception Mapping | `backend/src/planning/presentation/routers.py#L464-L515`| Unhandled `ValueError` in file/URL knowledge routes crashes request with HTTP 500 instead of 400. |
| **BE-API-04** | **MEDIUM** | Scalability / Missing Pagination| `backend/src/*/presentation/routers.py` | Zero list endpoints (`/tasks`, `/roadmaps`, `/notes`, `/learner-memory`) implement pagination. |
| **BE-API-05** | **LOW** | REST Incompleteness | `backend/src/execution/presentation/routers.py` | Missing single task retrieval endpoint (`GET /api/v1/tasks/{task_id}`). |

---

## 3. Detailed Structured Audit Findings

### [FE-API-04] Direct Violation of Rule 4: JWT Saved in LocalStorage
- **Severity**: **CRITICAL**
- **Category**: Security / Architecture Rule Violation
- **Affected Pages/Modules**: `AuthService`, `authInterceptor`, `authGuard`
- **File Path + Line Numbers**:
  - [frontend/src/app/core/services/auth.service.ts#L62-L65](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/services/auth.service.ts#L62-L65)
  - [frontend/src/app/core/interceptors/auth.interceptor.ts#L20-L25](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/interceptors/auth.interceptor.ts#L20-L25)
  - [frontend/src/app/guards/auth.guard.ts#L9](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/guards/auth.guard.ts#L9)
- **Expected Behavior**: `AGENTS.md` Rule 4 states: *"Không lưu token trong JS/localStorage; withCredentials cho HttpClient và EventSource."* ADR-008 explicitly mandates SameSite HttpOnly cookies for JWT authentication to eliminate XSS token theft.
- **Actual Behavior**:
  - `AuthService.setUser()` explicitly writes:
    ```typescript
    if (accessToken) {
      localStorage.setItem('access_token', accessToken);
    }
    ```
  - `authInterceptor` reads `localStorage` and injects `Authorization: Bearer <token>`:
    ```typescript
    const token = localStorage.getItem('access_token') || '';
    if (token.length > 0 && isApiRequest) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    ```
  - `auth.guard.ts` validates route access using `localStorage.getItem('access_token')`.
- **Root Cause**: Mixed legacy implementation retained during transition to HttpOnly cookies.
- **Evidence**: `auth.service.ts` line 64, `auth.interceptor.ts` lines 20-25, `auth.guard.ts` line 9.
- **Impact**: Security vulnerability (XSS can extract the bearer token from localStorage) and direct violation of the project constitution.
- **Recommended Fix**: Remove all `localStorage.setItem('access_token')` and `localStorage.getItem('access_token')` calls. Rely exclusively on `withCredentials: true` with HttpOnly cookies.
- **Validation Steps**: Inspect `localStorage` after login; verify no tokens are stored in browser storage.
- **Confidence Level**: 100%

---

### [FE-API-03] Optimistic Update Showing Success Despite API Failure
- **Severity**: **HIGH**
- **Category**: Error Handling / False Success State
- **Affected Pages/Modules**: `/roadmaps` (RoadmapsHubComponent)
- **File Path + Line Numbers**: [frontend/src/app/features/roadmaps/components/roadmaps-hub/roadmaps-hub.component.ts#L299-L307](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/roadmaps/components/roadmaps-hub/roadmaps-hub.component.ts#L299-L307)
- **Expected Behavior**: When resuming a roadmap fails with an HTTP error, the UI must roll back the status to PAUSED and show an error notification explaining why the resume failed.
- **Actual Behavior**: In `RoadmapsHubComponent.executeResume`:
  ```typescript
  this.roadmapService.resumeRoadmap(id).subscribe({
    next: () => { /* show success */ },
    error: () => {
      this.roadmapService.roadmaps.update(list =>
        list.map(r => (r.id === id ? { ...r, status: 'ACTIVE' } : r))
      );
      this.messageService?.add({
        severity: 'success',
        summary: 'Đã kích hoạt',
        detail: 'Lộ trình đã hoạt động trở lại.',
      });
    }
  });
  ```
  In the `error` callback, the component forcefully sets the status to `'ACTIVE'` and displays a success toast!
- **Root Cause**: Copy-paste error from the `next` block into the `error` block.
- **Evidence**: `roadmaps-hub.component.ts` lines 299-307.
- **Impact**: Critical usability flaw. When an API call fails (e.g. database error, concurrent modification, network disconnect), the UI tells the user that the roadmap is active, masking failures.
- **Recommended Fix**: Replace the `error` block with proper error handling:
  ```typescript
  error: (err) => {
    this.messageService?.add({
      severity: 'error',
      summary: 'Lỗi kích hoạt',
      detail: parseHttpErrorMessage(err, 'Không thể kích hoạt lộ trình.'),
    });
  }
  ```
- **Validation Steps**: Trigger `resumeRoadmap` with backend disconnected; verify error toast is displayed and status remains PAUSED.
- **Confidence Level**: 100%

---

### [FE-API-01] Endpoint Path Mismatches in `API_ENDPOINTS` Constant
- **Severity**: **HIGH**
- **Category**: Contract Mismatch / Dead Constant
- **Affected Pages/Modules**: `core/constants/api-endpoints.ts`, `settings.service.ts`, `profile.service.ts`
- **File Path + Line Numbers**:
  - [frontend/src/app/core/constants/api-endpoints.ts#L133-L135](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/constants/api-endpoints.ts#L133-L135)
  - [frontend/src/app/core/api/schema.d.ts#L22-L46](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/api/schema.d.ts#L22-L46)
- **Expected Behavior**: `API_ENDPOINTS.SETTINGS.PROFILE` and `API_ENDPOINTS.SETTINGS.QUOTA` should match the OpenAPI backend specification paths `/api/v1/account/profile` and `/api/v1/account/quota`.
- **Actual Behavior**: `api-endpoints.ts` specifies:
  ```typescript
  SETTINGS: {
    PROFILE: '/api/v1/users/profile', // Backend is /api/v1/account/profile!
    AVAILABILITY: '/api/v1/availabilities/me',
    QUOTA: '/api/v1/users/quota',     // Backend is /api/v1/account/quota!
  }
  ```
  Because of this mismatch, developers of `ProfileService` and `SettingsService` bypassed `API_ENDPOINTS` and hardcoded string literals `'/api/v1/account/profile'` and `'/api/v1/account/quota'` inside their service files.
- **Root Cause**: Specification drift between early design (`/users/*`) and Hexagonal Bounded Context nomenclature (`/account/*`).
- **Evidence**: `api-endpoints.ts` line 133; `schema.d.ts` lines 22 & 46.
- **Impact**: Any service attempting to use `API_ENDPOINTS.SETTINGS.PROFILE` or `QUOTA` receives a 404 Not Found error.
- **Recommended Fix**: Align `API_ENDPOINTS.SETTINGS` with OpenAPI paths:
  ```typescript
  PROFILE: '/api/v1/account/profile',
  QUOTA: '/api/v1/account/quota',
  ```
- **Validation Steps**: Grep for `/users/profile` and replace with `API_ENDPOINTS.SETTINGS.PROFILE`; verify request succeeds.
- **Confidence Level**: 100%

---

### [BE-API-03] Unhandled ValueError in Knowledge Upload Routers Causes HTTP 500
- **Severity**: **MEDIUM**
- **Category**: Exception Mapping / API Robustness
- **Affected Pages/Modules**: `planning/presentation/routers.py` (`upload_knowledge_source_file`, `add_knowledge_source_url`)
- **File Path + Line Numbers**: [backend/src/planning/presentation/routers.py#L464-L515](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/presentation/routers.py#L464-L515)
- **Expected Behavior**: Uploading an unsupported file format or invalid/SSRF-flagged URL should return `HTTP 400 Bad Request` or `HTTP 422 Unprocessable Content` with a clear Vietnamese validation message.
- **Actual Behavior**: Both route handlers only catch `LookupError`. When `use_case.create_file` or `create_url` raises `ValueError` (or `UnsafeUrlError`), the exception bubbles up unhandled, causing FastAPI to return `HTTP 500 Internal Server Error`.
- **Root Cause**: Missing `except (ValueError, UnsafeUrlError) as exc:` in presentation handlers.
- **Evidence**:
  ```python
  # routers.py:483-488
  try:
      source = await use_case.create_file(...)
  except LookupError as exc:
      raise HTTPException(status_code=404, detail="Goal not found") from exc
  # ValueError is unhandled!
  ```
- **Impact**: Client mistakes cause 500 errors in monitoring logs, degrading API reliability metrics.
- **Recommended Fix**: Add `except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc))`.
- **Validation Steps**: Send POST to `/api/v1/planning/goals/{id}/knowledge-sources/files` with an `.exe` file; verify response status is 400 instead of 500.
- **Confidence Level**: 100%

---

### [BE-API-04] Lack of Pagination Across All Collection Endpoints
- **Severity**: **MEDIUM**
- **Category**: API Scalability & Query Performance
- **Affected Pages/Modules**: `execution`, `planning`, `account` list endpoints
- **File Path + Line Numbers**:
  - [backend/src/execution/presentation/routers.py#L210-L230](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/presentation/routers.py#L210-L230) (`GET /api/v1/tasks`)
  - [backend/src/planning/presentation/routers.py#L760-L775](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/presentation/routers.py#L760-L775) (`GET /api/v1/roadmaps`)
  - [backend/src/execution/presentation/routers.py#L575-L590](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/presentation/routers.py#L575-L590) (`GET /api/v1/sessions/notes`)
  - [backend/src/account/presentation/routers.py#L135-L145](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/presentation/routers.py#L135-L145) (`GET /api/v1/account/learner-memory`)
- **Expected Behavior**: Collection listing endpoints should support pagination (`limit`, `offset` / `cursor`) to protect against unbounded database queries and high memory consumption.
- **Actual Behavior**: No listing endpoints accept pagination parameters. Queries fetch all matching rows unconditionally (`SELECT * FROM tasks WHERE roadmap_id IN (...)`).
- **Root Cause**: Early implementation assumed small initial datasets per student.
- **Evidence**: Grep for `limit`/`offset` query parameters across presentation routers returned 0 matches.
- **Impact**: Potential performance degradation, memory bloat, and API response timeouts for accounts with hundreds of tasks or notes.
- **Recommended Fix**: Add `limit: int = Query(50, le=100)` and `offset: int = Query(0, ge=0)` to listing endpoints.
- **Validation Steps**: Seed 1,000 tasks and query `GET /api/v1/tasks`; observe entire 1,000-item array returned.
- **Confidence Level**: 95%
