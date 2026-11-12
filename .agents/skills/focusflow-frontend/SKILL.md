---
name: focusflow-frontend
description: Quy tắc kiến trúc và quy trình làm việc cho frontend FocusFlow (Angular 21+ standalone, zoneless, OnPush, Signals, Tailwind CSS v4, PrimeNG v21, Lucide, openapi-typescript, Vitest, Playwright). Dùng skill này BẤT CỨ KHI NÀO người dùng viết, sửa, review, debug hoặc thiết kế giao diện/code frontend của FocusFlow - component, feature slice, signal store, route/guard, form, bảng, dialog, Pomodoro/Study Workspace, heartbeat, luồng AI streaming SSE (EventSource), lịch học, dashboard Needs Attention, analytics, billing QR, admin portal, a11y, responsive, test Vitest/Playwright - kể cả khi họ chỉ nói "làm màn hình...", "thêm trang...", "sửa UI", "thêm component", "gọi API", "hiển thị lỗi".
---

# FocusFlow Frontend — hướng dẫn cho AI agent (vai trò: Senior Frontend Engineer)

SPA Angular 21+ hướng tới 28 use case theo SRS v1.3 của FocusFlow (Learner + Administrator). Các điểm khó đã được chốt trong ADR: bộ đếm Pomodoro cập nhật mỗi giây (zoneless để không quét lại cây), luồng AI SSE 2 chặng với Human-in-the-Loop, lịch/analytics giàu dữ liệu, và Lighthouse Accessibility ≥ 90. Skill này giúp bạn làm đúng ngay lần đầu và nhất quán với backend.

## 0. Quy trình bắt buộc cho mọi tác vụ

1. **Xác định feature slice** (mục 2) và use case SRS v1.3 liên quan. Màn hình mới ⇒ đọc `references/feature-slices.md` để biết hành vi, trạng thái, mã lỗi cần xử lý.
2. **Kiểm tra hợp đồng API**: kiểu dữ liệu lấy từ `src/app/core/api/schema.d.ts` (sinh từ OpenAPI). Chưa có endpoint/field? Dừng và báo cho người dùng/backend — **không tự viết interface tay** cho dữ liệu API.
3. **Đọc component/store lân cận** để khớp pattern có sẵn trước khi viết mới.
4. **Viết**: store/service (signals) → component trình bày (dumb) → container (smart) → route. Mỗi trạng thái UI (loading, empty, error, success, disabled, offline) đều phải có thiết kế.
5. **Tự kiểm**: build production, lint, unit test, và (nếu đụng luồng chính) Playwright. Kiểm a11y bàn phím + responsive 375px/1024px. Không báo "xong" khi chưa chạy; nếu không chạy được, nói rõ.
6. **Báo cáo ngắn**: file đã đổi, giả định, điểm cần backend/người dùng xác nhận.

Khi SRS và ADR lệch nhau (đặc biệt số UC, AI Reschedule, thời lượng task AI) → xem `references/spec-conflicts.md`, áp dụng cách giải quyết ghi ở đó và **nói với người dùng**.

## 1. Luật bất khả xâm phạm

**Angular**
- 100% standalone component, `changeDetection: ChangeDetectionStrategy.OnPush`, không `zone.js` (dùng `provideZonelessChangeDetection()`), không `NgModule` mới.
- Control flow mới: `@if`, `@for` (luôn có `track`), `@switch`, `@defer`. Cấm `*ngIf/*ngFor`.
- Signal API: `input()`, `input.required()`, `output()`, `model()`, `viewChild()`, `computed()`, `effect()` (chỉ cho side-effect đồng bộ ra ngoài như logging/DOM — **không** để đồng bộ state này sang state kia, dùng `computed`/`linkedSignal`), `inject()` thay constructor injection.
- Không dùng `setTimeout`/`setInterval`/Promise để "kích hoạt render" — zoneless chỉ render khi signal đổi, `markForCheck` hoặc event của template. Mọi state hiển thị phải là signal.
- Subscription RxJS: `toSignal()` hoặc `takeUntilDestroyed()`; không `subscribe` trần không dọn.
- Lazy load mọi feature qua `loadComponent`/`loadChildren`; guard/resolver/interceptor dạng **hàm** (`CanActivateFn`, `HttpInterceptorFn`).

**State**
- Mỗi feature có `@Injectable` store dùng `signal/computed/linkedSignal/rxResource|httpResource`. **Không NgRx.** Không `BehaviorSubject` cho state mới.
- State chỉ có một nguồn; dẫn xuất bằng `computed`. Không lưu bản sao dữ liệu server trong nhiều nơi.
- Chỉ đọc state ra ngoài dưới dạng `Signal` (`asReadonly()`), thay đổi qua method của store.

**API & type**
- Mọi kiểu request/response lấy từ `schema.d.ts` sinh bởi `openapi-typescript` (script `npm run api:gen`). Đổi backend ⇒ regenerate ⇒ sửa lỗi biên dịch; đó là cơ chế phát hiện lệch hợp đồng.
- Gọi API chỉ qua service trong `core/api` hoặc `features/<slice>/data/`; component **không** dùng `HttpClient` trực tiếp.
- Xác thực bằng **cookie HttpOnly** (`withCredentials: true` qua interceptor). **Cấm** lưu token ở `localStorage/sessionStorage`; cấm tự đọc/gắn JWT trong JS.
- Lỗi API có dạng `{code, message, details, correlation_id}`: UI map theo `code` (xem `feature-slices.md` §Mã lỗi), hiển thị `correlation_id` ở chi tiết lỗi kỹ thuật để hỗ trợ debug.

**UI**
- Thành phần phức tạp lấy từ **PrimeNG v21** (Table, Dialog, Drawer, Select, DatePicker, Timeline, ProgressBar, Toast, ConfirmPopup, Stepper, Chart...). Đừng tự chế lại. Bố cục/khoảng cách/typography/vi tương tác dùng **Tailwind v4**. Icon: **`lucide-angular`**.
- Màu qua biến ngữ nghĩa (`var(--p-primary-color)`, `--p-surface-*`); hỗ trợ light/dark; không hard-code hex trong component.
- A11y là yêu cầu (NFR-UX-002: Lighthouse ≥ 90 ở Onboarding, Study Workspace, Calendar, Analytics): `aria-label` cho nút chỉ có icon, tương phản đủ, điều hướng bàn phím, focus nhìn thấy được, `aria-live` cho toast/timer/tiến trình AI, không dùng màu là tín hiệu duy nhất.
- Responsive (NFR-UX-001): không vỡ layout/overflow ngang từ 375px đến ≥1024px. Thiết kế mobile-first.
- Phản hồi thao tác cơ bản (tick task, start/stop timer, đổi tab) ≤ 500ms: dùng optimistic update có rollback khi lỗi.

**Nghiệp vụ trên UI** (không tự suy diễn khác SRS)
- AI chỉ tạo **bản nháp** (`DRAFT`). UI luôn có bước xem/diff/chỉnh sửa và nút **Apply** tường minh trước khi lịch chính thức đổi (BUSR-02). Không có auto-apply.
- Soft Overflow (≤30 phút, task cuối ngày Mode B) phải hiện cảnh báo trực quan + yêu cầu xác nhận trước Apply (BUSR-04).
- Quá hạn **không** tự dời lịch; hiển thị ở khu "Needs Attention" kèm nút "Dời lịch hợp lý bằng AI" theo từng lộ trình (BUSR-06).
- `STALLED` (`reschedule_count >= 3`) ⇒ khóa dời tự động, mở dialog can thiệp 3 lựa chọn (Re-commit / AI Micro-Stepping / Backlog–Cancel).
- Cờ `OVERDUE`, `BLOCKED`, `STALLED` là **suy diễn** từ dữ liệu API (hoặc cờ do API trả); đừng coi là trạng thái lưu.
- Lộ trình `COMPLETED/ARCHIVED` chỉ đọc. Phiên học đã kết thúc không mở lại.
- Không bao giờ hiển thị/ghi log token, URL WebCal đầy đủ ngoài khoảnh khắc "hiện một lần" khi tạo/reset (kèm nút sao chép).

## 2. 9 Feature slice (`src/app/features/`)

| Slice | Nội dung | UC (SRS v1.3) |
|---|---|---|
| `auth/` | đăng ký, đăng nhập, quên mật khẩu, onboarding | 01, 02 |
| `dashboard/` | Today Focus, tiến độ hôm nay, **Needs Attention**, quota AI | 13, 23, 25 (hiển thị) |
| `planning/` | goal → AI milestone (SSE) → duyệt → AI schedule proposal (SSE) → diff → Apply; tạo thủ công; danh mục/lưu trữ lộ trình | 07, 08, 09, 10 |
| `workspace/` | Phiên học, MVS, Key Takeaways, heartbeat và khôi phục phiên | 14, 15, 16 |
| `calendar/` | lịch chính thức, dời thủ công, Google Calendar và WebCal/.ics | 13, 17, 18 |
| `tasks/` | danh sách task, backlog, DAG, can thiệp `STALLED` | 11, 23, 24 |
| `analytics/` | thống kê, Prove Mode, Weekly Review, Pause/Resume | 19, 20, 21, 22 |
| `settings/` | hồ sơ, múi giờ, lịch rảnh Mode A/B, Learner Profile (reset), nâng cấp Premium, thanh toán QR | 03, 04 (+05 kết quả) |
| `admin/` | người dùng & hạn ngạch, đối soát, giám sát | 26, 27, 28 |

Cấu trúc một slice:
```
features/<slice>/
  <slice>.routes.ts           # lazy routes + guards
  data/                       # api service (typed) + store (signals)
  ui/                         # presentational components (input/output, OnPush)
  pages/                      # container components (nối store ↔ ui)
  *.spec.ts                   # Vitest, cạnh file
src/app/core/                 # api (schema.d.ts, client, error mapper), auth (session store, guards), interceptors, layout
src/app/shared/               # ui dùng chung (kỳ vọng nhỏ), pipes, utils (date/timezone), directives
```
Slice **không import chéo nội bộ** của slice khác; dùng chung qua `core/` hoặc `shared/`. Component trình bày không biết store/HTTP.

## 3. Đi thẳng tới tài liệu cần đọc

- Mẫu code Angular (store, SSE → signal, timer, heartbeat, form, guard, interceptor, optimistic update): `references/angular-patterns.md`
- Hành vi từng màn hình, mã lỗi → UI, trạng thái, mapping UC: `references/feature-slices.md`
- Hệ thống thiết kế PrimeNG v21 + Tailwind v4 + dark mode + a11y + responsive: `references/ui-system.md`
- Chiến lược test Vitest + Playwright + Lighthouse: `references/testing.md`
- Mâu thuẫn SRS/ADR: `references/spec-conflicts.md`

## 4. Quyết định kỹ thuật cần nhớ

| Chủ đề | Quyết định |
|---|---|
| Framework | Angular 21+, standalone, zoneless, OnPush, signals; Reactive Forms cho form phức tạp (validator đồng bộ với quy tắc backend, nhưng backend vẫn là chốt chặn cuối). |
| Style | Tailwind CSS v4 + PrimeNG v21 (Styled mode, semantic CSS variables), Lucide icons, light/dark. |
| Auth | Cookie JWT HttpOnly; interceptor xử lý 401 → một lần refresh (hàng đợi các request đang chờ) → thử lại; refresh fail ⇒ về `/login`. Admin routes qua `roleGuard('ADMIN')` (chỉ là UX; backend mới là bảo mật). |
| SSE AI | `POST` (kèm `Idempotency-Key` uuid mỗi lần bấm) → `202 {job_id}` → `EventSource(.../jobs/{id}/stream, {withCredentials: true})`; sự kiện `stage/chunk/validation_retry/completed/failed`; đóng EventSource khi `completed/failed/destroy`. Kết nối lại không tạo job mới. |
| Heartbeat | `POST /api/v1/sessions/{id}/heartbeat` mỗi 60s khi phiên `IN_PROGRESS` (kể cả tab nền: dùng timestamp, không dựa số tick `setInterval` vì tab nền bị throttle); lỗi mạng ⇒ thử lại, hiển thị trạng thái offline; backend tự chốt sau 5 phút. |
| Thời gian | Server trả ISO/UTC; hiển thị theo `User.timezone` (IANA). "Ngày" học (`scheduled_date`) là ngày theo múi giờ người học — không cộng trừ ngày bằng UTC. |
| Test | Vitest (unit: store, component, pipe), Playwright (E2E luồng chính, chạy được với backend `LLM_PROVIDER=mock`). |
| Build | `ng build --configuration production` sạch lỗi/cảnh báo; bundle SPA tĩnh phục vụ qua Nginx (proxy `/api`, `proxy_buffering off` cho SSE). |

## 5. Phong cách code

- TypeScript `strict`; không `any` (dùng `unknown` + thu hẹp kiểu); không `!` non-null tràn lan.
- Component nhỏ, một trách nhiệm; template ngắn (logic đưa vào `computed`). Tên selector `ff-*`. Tên file theo quy ước Angular (`task-list.component.ts` hoặc theo repo hiện có — khớp repo).
- Ngôn ngữ UI: tiếng Việt (nhãn, thông báo, lỗi), dùng ngôn ngữ SRS (vd "Dời lịch hợp lý bằng AI", "Áp dụng", "Task Cần Chú Ý"). Chuẩn bị i18n nếu repo đã dùng; không trộn Anh–Việt tuỳ hứng.
- Văn bản lỗi thân thiện, nói rõ cách tiếp tục (nút Thử lại / Lập kế hoạch thủ công), không lộ chi tiết nội bộ.
- Không thêm thư viện mới khi PrimeNG/Tailwind/Angular đã đáp ứng; nếu cần, nêu lý do và kích thước bundle.
- Chỉ comment "vì sao" (kèm `BUSR-xx`/`ADR-00x` nếu hữu ích).

## 6. Cổng chất lượng (chạy trong `frontend/`)

```bash
npm run api:gen            # nếu backend đổi OpenAPI
pnpm exec ng lint
pnpm exec ng test --watch=false  # Angular TestBed; raw vitest run chưa khởi tạo môi trường Angular
npx ng build --configuration production
npx playwright test        # khi đụng luồng chính
```
Definition of Done: đủ mọi trạng thái UI; không lỗi type sau `api:gen`; a11y bàn phím + aria; responsive 375/768/1024; test cho store logic và component có hành vi; không `console.log`; không token/PII trong log; dark mode không vỡ màu; không memory leak (EventSource/interval đóng khi destroy).

## 7. Lỗi hay gặp (tự soát trước khi nộp)

- Còn `*ngIf`, thiếu `track` trong `@for`, thiếu OnPush, dùng biến thường thay vì signal ⇒ UI không cập nhật trong zoneless.
- Đồng hồ Pomodoro dựa vào đếm tick `setInterval` (lệch khi tab nền) thay vì `Date.now()`/`performance.now()` so với mốc bắt đầu.
- Lưu JWT/đọc cookie bằng JS; quên `withCredentials` cho `EventSource`.
- Tự viết interface cho response; hoặc sửa tay `schema.d.ts`.
- Mở EventSource nhưng không đóng ⇒ rò kết nối; hoặc bấm "Tạo lại" làm sinh hai job (thiếu khóa nút/`Idempotency-Key`).
- Auto-apply bản nháp AI; bỏ qua cảnh báo Soft Overflow; để "Needs Attention" tự dời lịch.
- Dùng màu để báo trạng thái mà không có icon/chữ; nút icon thiếu `aria-label`.
- Tính "quá hạn"/"hôm nay" bằng giờ trình duyệt thay vì múi giờ hồ sơ người học (hai nơi có thể lệch).
- Tin vào guard FE để bảo vệ admin (chỉ UX), hoặc ẩn nút mà không xử lý 403/404 từ server.
- Hiển thị URL WebCal/token ở nơi lưu lại được (log, URL query, localStorage).
