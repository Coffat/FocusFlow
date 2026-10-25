---
name: frontend-feature
description: Step-by-step guide to create Angular 21+ Zoneless components, pages, and Signal services. Use when building new UI features, standalone components, 2-Stage SSE streams, or integrating with Tailwind CSS v4 and PrimeNG v21.
---

# Frontend Feature Implementation (Angular 21+ Zoneless + Signals + PrimeNG v21)

Creates an Angular 21+ feature slice under `frontend/src/app/features/` following FocusFlow v2.0 conventions.

## Pre-flight

1. Identify the Use Case (`UC-01`..`UC-19`) and target feature slice under `frontend/src/app/features/`:
   - `auth`, `dashboard`, `roadmaps`, `workspace`, `schedule`, `tasks`, `analytics`, `settings`, or `admin` (`UC-18`, `UC-19`).
2. Check if the backend API endpoint exists and types are synced in `frontend/src/app/core/api/schema.d.ts`. If not -> apply skill `api-contract` first.

## Implementation Order

### 1. Models & OpenAPI Types (`core/api/schema.d.ts` or `features/{slice}/models/`)

- Prefer generated OpenAPI types from `frontend/src/app/core/api/schema.d.ts` (`npm run gen:api-types`).
- Add view-specific TypeScript interfaces in `features/{slice}/models/{slice}.model.ts`.

### 2. Feature Store / Service (`features/{slice}/services/` or `core/services/`)

- Create service with `@Injectable({ providedIn: 'root' })` and `inject(HttpClient)`.
- Manage reactive state with **Angular Signals** (`signal()`, `computed()`, `linkedSignal()`, `rxResource()`).
- For AI streaming endpoints (`UC-06`, `UC-08`, `UC-15`, `UC-16`), use `AiSseService` (`core/services/ai-sse.service.ts`) implementing the **Uniform 2-Stage SSE pattern (`ADR-005`)**:
  1. `POST` to reserve ACID AI Quota and obtain `jobId` + `streamUrl`.
  2. Connect `EventSource` wrapped in RxJS `Observable` -> `toSignal()` with `takeUntilDestroyed()`.

### 3. Standalone Component (`features/{slice}/components/`)

- Use `standalone: true` and `changeDetection: ChangeDetectionStrategy.OnPush` (compatible with `provideZonelessChangeDetection()` in `app.config.ts`).
- Use modern Angular control flow (`@for (...; track ...)`, `@if`, `@switch`) — never `*ngFor` or `*ngIf`.
- Use Signal inputs/outputs (`input()`, `output()`) and `inject()`.

### 4. Styling (Tailwind CSS v4 + PrimeNG v21 + Lucide Icons)

- Style layouts with **Tailwind CSS v4** utility classes and **PrimeNG v21** components (`@primeuix/themes`).
- Always reference semantic CSS variables (`var(--primary)`, `var(--background)`, `var(--muted-foreground)`) — never hardcode hex colors.

### 5. Routing (`features/{slice}/{slice}.routes.ts` & `app.routes.ts`)

- Export `{SLICE}_ROUTES: Routes` using lazy `loadComponent`.
- Register top-level slice path in `frontend/src/app/app.routes.ts` with `authGuard` / RBAC role guard where required.

### 6. Verification

- Run `cd frontend && npm run build` (or `vitest run` / `playwright test`).
