# Mẫu code Angular 21+ (FocusFlow)

Mục lục: 1. Bootstrap · 2. Store bằng signals · 3. Gọi API typed · 4. Interceptors · 5. SSE → Signal (luồng AI) · 6. Timer Pomodoro/Stopwatch · 7. Heartbeat · 8. Optimistic update · 9. Form · 10. Route & guard · 11. Component trình bày vs container

Các đoạn dưới là **mẫu hình**. Luôn khớp với code đang có trong repo; nếu API Angular đã đổi ở phiên bản bạn thấy trong `package.json`, theo tài liệu chính thức của phiên bản đó (đặc biệt `rxResource`/`httpResource`, forms signal — vẫn đang phát triển).

## 1. Bootstrap

```ts
// app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding(), withViewTransitions()),
    provideHttpClient(withInterceptors([credentialsInterceptor, correlationInterceptor, authRefreshInterceptor, errorInterceptor])),
    provideAnimationsAsync(),
    providePrimeNG({ theme: { preset: FocusFlowPreset, options: { darkModeSelector: '.app-dark', cssLayer: { name: 'primeng', order: 'theme, base, primeng' } } } }),
  ],
};
```
Không import `zone.js` ở `polyfills`/`angular.json`. (Theo ADR-003; nếu test tooling cần, dùng setup zoneless của Vitest/Angular testing.)

## 2. Store bằng signals

```ts
@Injectable({ providedIn: 'root' })   // hoặc providedIn route/feature nếu state chỉ sống trong slice
export class TaskStore {
  private readonly api = inject(TaskApi);
  private readonly _tasks = signal<TaskDto[]>([]);
  private readonly _status = signal<'idle' | 'loading' | 'error'>('idle');
  private readonly _error = signal<ApiError | null>(null);

  readonly tasks = this._tasks.asReadonly();
  readonly status = this._status.asReadonly();
  readonly error = this._error.asReadonly();
  readonly overdue = computed(() => this._tasks().filter(t => t.is_overdue && t.status !== 'COMPLETED'));
  readonly stalled = computed(() => this._tasks().filter(t => t.reschedule_count >= 3));

  async load(roadmapId: string) {
    this._status.set('loading'); this._error.set(null);
    try { this._tasks.set(await firstValueFrom(this.api.list(roadmapId))); this._status.set('idle'); }
    catch (e) { this._error.set(toApiError(e)); this._status.set('error'); }
  }
}
```
Dữ liệu server theo tham số (id route…) → ưu tiên `rxResource`/`httpResource` hoặc `linkedSignal`:
```ts
readonly roadmapId = input.required<string>();
readonly tasks = rxResource({ params: () => ({ id: this.roadmapId() }), stream: ({ params }) => this.api.list(params.id) });
// template: @if (tasks.isLoading()) {...} @else if (tasks.error()) {...} @else { tasks.value() }
```
`linkedSignal` cho state phụ thuộc nguồn nhưng cho phép ghi đè cục bộ (vd lựa chọn mặc định đổi khi danh sách đổi).

## 3. Gọi API typed

```ts
import type { paths, components } from '@/app/core/api/schema';
type Task = components['schemas']['TaskOut'];
type CompleteResp = paths['/api/v1/tasks/{task_id}/complete']['post']['responses']['200']['content']['application/json'];

@Injectable({ providedIn: 'root' })
export class TaskApi {
  private readonly http = inject(HttpClient);
  complete(id: string) { return this.http.post<CompleteResp>(`/api/v1/tasks/${id}/complete`, {}); }
}
```
Không `any`. Tên `TaskDto` có thể là alias của `components['schemas'][...]`; **đừng** định nghĩa lại field.

## 4. Interceptors (hàm)

- `credentialsInterceptor`: `req.clone({ withCredentials: true })` cho mọi request tới `/api`.
- `correlationInterceptor`: gắn `X-Correlation-Id` (uuid) để đối chiếu log backend.
- `authRefreshInterceptor`: khi 401 (trừ chính `/auth/refresh`, `/auth/login`) → chạy **một** refresh dùng chung (`shareReplay`/subject), các request khác chờ rồi thử lại; refresh lỗi ⇒ `sessionStore.clear()` + điều hướng `/login` kèm `returnUrl`.
- `errorInterceptor`: chuyển `HttpErrorResponse` thành `ApiError {code, message, details, correlationId, status}`; không toast ở đây (để nơi gọi quyết định), trừ lỗi toàn cục (mất mạng, 5xx).

## 5. SSE 2 chặng → Signal

```ts
export type AiEvent =
  | { type: 'stage'; data: { name: string } }
  | { type: 'chunk'; data: { text: string } }
  | { type: 'validation_retry'; data: { attempt: number; reason: string } }
  | { type: 'completed'; data: { result_id: string } }
  | { type: 'failed'; data: { code: string; message: string } };

function sse$(url: string): Observable<AiEvent> {
  return new Observable(sub => {
    const es = new EventSource(url, { withCredentials: true });
    for (const t of ['stage', 'chunk', 'validation_retry', 'completed', 'failed'] as const) {
      es.addEventListener(t, (ev) => {
        sub.next({ type: t, data: JSON.parse((ev as MessageEvent).data) } as AiEvent);
        if (t === 'completed' || t === 'failed') { es.close(); sub.complete(); }   // dừng, tránh EventSource tự reconnect
      });
    }
    es.onerror = () => { if (es.readyState === EventSource.CLOSED) sub.error(new Error('SSE_CLOSED')); /* CONNECTING = đang tự reconnect: giữ nguyên */ };
    return () => es.close();                        // teardown khi unsubscribe/destroy
  });
}

@Injectable()
export class AiJobStore {
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);
  readonly text = signal(''); readonly stage = signal<string | null>(null);
  readonly retries = signal(0); readonly state = signal<'idle'|'starting'|'streaming'|'done'|'failed'>('idle');
  readonly error = signal<ApiError | null>(null);
  private key = crypto.randomUUID();                // 1 key cho 1 "ý định" bấm; tạo mới khi người dùng thật sự muốn sinh lại

  start(path: string, body: unknown) {
    if (this.state() === 'starting' || this.state() === 'streaming') return;   // chống bấm đúp
    this.state.set('starting'); this.text.set(''); this.error.set(null);
    this.http.post<{ job_id: string }>(path, body, { headers: { 'Idempotency-Key': this.key } }).pipe(
      switchMap(({ job_id }) => { this.state.set('streaming'); return sse$(`${path}/jobs/${job_id}/stream`); }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: ev => { switch (ev.type) {
        case 'stage': this.stage.set(ev.data.name); break;
        case 'chunk': this.text.update(t => t + ev.data.text); break;
        case 'validation_retry': this.retries.set(ev.data.attempt); break;
        case 'completed': this.state.set('done'); break;
        case 'failed': this.state.set('failed'); this.error.set({ code: ev.data.code, message: ev.data.message } as ApiError); break; } },
      error: e => { this.state.set('failed'); this.error.set(toApiError(e)); },
    });
  }
  regenerate() { this.key = crypto.randomUUID(); /* rồi gọi start lại */ }
}
```
Yêu cầu UI cho luồng AI: hiển thị `stage` + tiến trình; khi `validation_retry` hiện "AI đang tự hiệu chỉnh (lần n/2)" (minh bạch, đúng ADR-009); `aria-live="polite"` cho vùng trạng thái; nút Hủy/Thử lại/Lập kế hoạch thủ công khi `failed`; token đầu tiên hiện ≤2.5s (đừng buffer chunk). Khi `completed` → tải bản nháp bằng API thường (nguồn chân lý), không dựng lịch từ chuỗi chunk.
Sau Cấp 1 (Milestones) **dừng**; chỉ khi người học bấm "Approve Milestones" mới gọi Cấp 2.

## 6. Timer Pomodoro/Stopwatch (zoneless, chính xác khi tab nền)

```ts
@Injectable()
export class SessionTimerStore {
  private readonly nowMs = toSignal(timer(0, 1000).pipe(map(() => Date.now())), { initialValue: Date.now() });
  readonly startedAtMs = signal<number | null>(null);
  readonly pausedMs = signal(0);
  readonly mode = signal<'pomodoro' | 'stopwatch'>('pomodoro');
  readonly targetMs = signal(25 * 60_000);             // D_opt lấy từ Learner Profile (mặc định 25)
  readonly elapsedMs = computed(() => this.startedAtMs() === null ? 0 : this.nowMs() - this.startedAtMs()! - this.pausedMs());
  readonly remainingMs = computed(() => Math.max(0, this.targetMs() - this.elapsedMs()));
  readonly label = computed(() => formatMmSs(this.mode() === 'pomodoro' ? this.remainingMs() : this.elapsedMs()));
}
```
Tính từ mốc thời gian (không đếm tick) ⇒ đúng khi tab bị throttle. Chỉ text node bind `label()` cập nhật mỗi giây. `aria-live="off"` cho đồng hồ (tránh đọc mỗi giây), nhưng thông báo mốc (hết giờ) dùng `aria-live="assertive"`/toast. Nguồn chân lý số phút thực học là server (heartbeat ghi `actual_minutes`); timer client chỉ để hiển thị.

## 7. Heartbeat 60s

```ts
// trong WorkspacePage / SessionStore, chỉ chạy khi phiên IN_PROGRESS
timer(60_000, 60_000).pipe(
  switchMap(() => this.api.heartbeat(sessionId).pipe(catchError(() => of(null)))),   // lỗi mạng: bỏ qua, thử lần sau
  takeUntilDestroyed(this.destroyRef),
).subscribe(r => this.online.set(r !== null));
fromEvent(document, 'visibilitychange').pipe(filter(() => !document.hidden), takeUntilDestroyed()).subscribe(() => this.sendHeartbeatNow());
```
Quy tắc: `online=false` thì hiện banner "Mất kết nối — tiến độ sẽ được chốt tại lần đồng bộ gần nhất"; backend chốt sau 5 phút im lặng (OS-07). Khi quay lại và phiên đã bị chốt (API trả trạng thái khác `IN_PROGRESS`), hiển thị tóm tắt phiên (task xong giữ nguyên, task dở về Backlog) thay vì tiếp tục timer. Khi người dùng "Kết thúc"/"Dừng sớm": gọi API, dừng heartbeat, hiển thị tóm tắt.

## 8. Optimistic update (tick task, ≤500ms)

```ts
async toggleComplete(task: TaskDto) {
  const snapshot = this._tasks();
  this._tasks.update(l => l.map(t => t.id === task.id ? { ...t, status: task.status === 'COMPLETED' ? 'TODO' : 'COMPLETED' } : t));
  try { const fresh = await firstValueFrom(this.api.toggle(task.id)); this._tasks.update(l => l.map(t => t.id === fresh.id ? fresh : t)); }
  catch (e) { this._tasks.set(snapshot); this.toast.error(toApiError(e)); }
}
```
Sau khi server trả về, **thay bằng dữ liệu server** (progress, `reschedule_count`, `completed_at` do server tính).

## 9. Form

- Reactive Forms có kiểu (`FormGroup<{...}>`, `nonNullable`). Validator phản chiếu luật backend để phản hồi sớm: Mode A `0.5–14` giờ/ngày; Mode B `start < end` hoặc có `end_day_offset` khi vắt nửa đêm, không overlap giữa các slot cùng ngày; thời lượng task thủ công `15–240` phút; mật khẩu theo chính sách backend.
- Lỗi từ server (`422` + `details`) gắn lại vào control/field tương ứng hoặc banner; không nuốt lỗi.
- Nút submit: disable khi `pending`, hiển thị loading, chống submit đúp.
- Văn bản tự do người học nhập (mục tiêu, ghi chú) không thay đổi nội dung ở client; việc cô lập prompt-injection là việc của backend, nhưng **không** render HTML thô: dùng pipe markdown an toàn (sanitize) cho Scratchpad/Key Takeaways.

## 10. Route & guard

```ts
export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/pages/login.page') },
  { path: '', canActivate: [authGuard], component: ShellComponent, children: [
      { path: 'dashboard', loadChildren: () => import('./features/dashboard/dashboard.routes') },
      { path: 'planning',  loadChildren: () => import('./features/planning/planning.routes') },
      /* workspace, calendar, tasks, analytics, settings */
      { path: 'admin', canActivate: [roleGuard('ADMIN')], loadChildren: () => import('./features/admin/admin.routes') },
  ]},
];
```
`authGuard` kiểm bằng `GET /me` (cookie) chứ không đọc token. Guard chỉ cải thiện UX; backend vẫn là nơi cưỡng chế. Có `returnUrl`. Trang 403/404 riêng.

## 11. Trình bày vs container

- `ui/` (presentational): chỉ `input()/output()/model()`, không inject store/HTTP, dễ test bằng Vitest, dễ tái dùng.
- `pages/` (container): inject store, truyền signal xuống, xử lý output. Giữ template mỏng.
- `@defer (on viewport)` cho khối nặng (chart, calendar thấp ưu tiên); luôn có `@placeholder`/`@loading` có kích thước ổn định tránh layout shift.
