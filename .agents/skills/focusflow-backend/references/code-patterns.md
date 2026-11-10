# Mẫu code chuẩn (Backend)

Mục lục: 1. Aggregate · 2. Port & Use case · 3. Repository & UoW · 4. Router · 5. Composition Root · 6. Outbox & consumer · 7. Taskiq task/sweeper · 8. Lỗi → HTTP

Các đoạn dưới là **mẫu hình**; hãy khớp tên/đường dẫn với repo thực tế.

## 1. Aggregate giàu hành vi

```python
# domain/task.py — thuần Python
@dataclass
class Task:
    id: UUID; roadmap_id: UUID; user_id: UUID
    status: TaskStatus; scheduled_date: date | None
    reschedule_count: int = 0
    completed_at: datetime | None = None
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    @property
    def is_stalled(self) -> bool:            # cờ suy diễn, không lưu
        return self.reschedule_count >= 3

    def is_overdue(self, today: date) -> bool:   # today tính theo timezone người học (truyền từ ngoài)
        return (self.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
                and self.scheduled_date is not None and self.scheduled_date < today)

    def complete(self, now: datetime) -> None:
        if self.status is TaskStatus.CANCELLED:
            raise DomainError("TASK_CANCELLED")
        self.status, self.completed_at, self.reschedule_count = TaskStatus.COMPLETED, now, 0

    def reschedule_due_to_overdue(self, new_date: date) -> None:
        if self.is_stalled:
            raise DomainError("TASK_STALLED")      # buộc người học can thiệp (UC-21 tiền điều kiện)
        self.scheduled_date = new_date
        self.reschedule_count += 1
```
Quy tắc: hành vi đổi trạng thái nằm trong aggregate; không có setter công khai bypass bất biến. Domain event thêm vào `_events`; UoW thu thập.

## 2. Port & Use case

```python
# application/ports/task_repository.py
class TaskRepository(Protocol):
    async def get(self, task_id: UUID) -> Task | None: ...
    async def save(self, task: Task) -> None: ...

# application/use_cases/complete_task.py
class CompleteTaskUseCase:
    def __init__(self, uow: AsyncUnitOfWork, clock: Clock) -> None:
        self._uow, self._clock = uow, clock

    async def execute(self, cmd: CompleteTaskCommand) -> TaskDTO:
        async with self._uow:
            task = await self._uow.tasks.get(cmd.task_id)
            if task is None or task.user_id != cmd.actor_id:      # IDOR: 404, không lộ tồn tại
                raise NotFoundError("TASK_NOT_FOUND")
            task.complete(self._clock.now())
            await self._uow.tasks.save(task)
            self._uow.collect_domain_events(task)
            await self._uow.commit()
            return TaskDTO.from_entity(task)
```
- Command (đổi trạng thái) ⇒ trong UoW + commit. Query ⇒ không cần commit, ưu tiên query service đọc thẳng (read model/DTO), vẫn kiểm sở hữu.
- Use case nhận `actor_id`/`role` trong command (đã xác thực ở presentation), không đọc request.
- Use case không biết HTTP, Redis, SQLAlchemy.

## 3. Repository & UoW

```python
class SqlAlchemyTaskRepository:
    def __init__(self, session: AsyncSession) -> None: self._s = session
    async def get(self, task_id):
        row = await self._s.get(TaskORM, task_id)
        return _to_domain(row) if row else None
    async def save(self, task):
        row = await self._s.get(TaskORM, task.id) or TaskORM(id=task.id)
        _apply(row, task); self._s.add(row); await self._s.flush()   # KHÔNG commit
```
`SqlAlchemyUnitOfWork.__aenter__` mở session; `commit()` = lấy event từ aggregate đã collect → với event liên context ghi `OutboxEventORM` → `session.commit()` (1 giao dịch). `__aexit__` rollback nếu có exception hoặc chưa commit. Khóa hàng: `select(...).with_for_update()` (hoặc `.with_for_update(skip_locked=True)` cho sweeper) nằm trong repository, expose qua method tên rõ nghĩa (`get_for_update`).

## 4. Router (presentation) — mỏng

```python
@router.post("/tasks/{task_id}/complete", response_model=TaskOut)
async def complete_task(task_id: UUID,
                        user: AuthUser = Depends(current_user),
                        uc: CompleteTaskUseCase = Depends(get_complete_task_uc)):
    dto = await uc.execute(CompleteTaskCommand(task_id=task_id, actor_id=user.id))
    return TaskOut.model_validate(dto)
```
- Schema Pydantic v2 request/response ở `schemas.py`; đặt `operation_id` ổn định và `response_model` đầy đủ (frontend sinh type từ OpenAPI).
- Prefix `/api/v1`. Lệnh tạo tài nguyên/AI: nhận `Idempotency-Key`.
- Phân trang danh sách: `limit/offset` hoặc cursor, trả `{items, total|next_cursor}`.
- Không logic nghiệp vụ trong router; không truy vấn DB trong router.

## 5. Composition Root

```python
# presentation/deps.py
async def get_uow(session_factory=Depends(get_session_factory)) -> AsyncUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)

def get_complete_task_uc(uow: AsyncUnitOfWork = Depends(get_uow),
                         clock: Clock = Depends(get_clock)) -> CompleteTaskUseCase:
    return CompleteTaskUseCase(uow, clock)

def get_llm(settings: Settings = Depends(get_settings)) -> LLMProviderPort:
    return build_llm_provider(settings)      # switch theo LLM_PROVIDER
```

## 6. Outbox & consumer lũy đẳng

Phát: aggregate thêm event → `uow.collect_domain_events` → commit ghi `outbox_events` (PENDING).

Relay (Taskiq, chạy định kỳ):
```python
@broker.task
async def outbox_relay(uow=TaskiqDepends(get_uow)) -> None:
    async with uow:
        rows = await uow.outbox.fetch_pending_for_update(limit=100)   # FOR UPDATE SKIP LOCKED
        for r in rows:
            await dispatch(r)           # kiq handler của context đích; payload = ID nguyên thủy
            r.mark_published()
        await uow.commit()
```
Consumer:
```python
@broker.task(retry_on_error=True, max_retries=5)
async def on_study_session_completed(event_id: str, session_id: str,
                                     uc=TaskiqDepends(get_update_profile_uc)) -> None:
    await uc.execute(UpdateProfileCommand(event_id=UUID(event_id), session_id=UUID(session_id)))
# trong use case: async with uow: if await uow.processed.exists(event_id): return
#                 ... xử lý ...; await uow.processed.add(event_id); await uow.commit()
```
At-least-once delivery ⇒ consumer **phải** an toàn khi nhận trùng. Việc ghi `processed_events` nằm trong cùng giao dịch với tác dụng phụ.

## 7. Taskiq task & sweeper

- Task là lớp vỏ mỏng: nhận ID/ISO string → gọi use case. Mọi logic ở use case để test không cần broker (dùng `InMemoryBroker` khi test task).
- Lịch (scheduler `replicas: 1`): khai báo `schedule=[{"cron": "..."}]` trên task hoặc `LabelScheduleSource`. Danh mục: outbox relay (vài giây–1 phút), abandoned-session sweeper (60s), quota reservation sweeper (60s), overdue scanner (xem dưới), learner-profile aggregator (theo event), calendar sync (theo event + định kỳ), reset quota (ngày 01 hàng tháng).
- Sweeper chuẩn:
```python
async with uow:
    sessions = await uow.sessions.lock_stale_in_progress(cutoff=now - timedelta(minutes=5), limit=200)  # FOR UPDATE SKIP LOCKED
    for s in sessions:
        s.auto_close(ended_at=s.last_heartbeat_at, planned_threshold=0.5)   # OS-01/OS-07
        uow.collect_domain_events(s)
    await uow.commit()
```
- Overdue scanner: xem `domain-rules.md` §Quá hạn (timezone theo người học; lũy đẳng theo `(user_id, local_date)`; chỉ gắn cờ + gửi email; không sửa `scheduled_date`).
- Gọi dịch vụ ngoài trong task: luôn đặt timeout; retry bằng middleware; lỗi vĩnh viễn thì ghi log có cấu trúc và dừng, không retry vô hạn.

## 8. Lỗi → HTTP (một nơi duy nhất)

| Exception / code | HTTP |
|---|---|
| `NotFoundError` (kể cả tài nguyên của người khác) | 404 |
| thiếu/không hợp lệ xác thực | 401 |
| sai role (`ADMIN` required) | 403 |
| `VALIDATION_OVERLOAD`, `DEPENDENCY_CYCLE_DETECTED`, `DomainError` quy tắc nghiệp vụ | 422 (kèm `code`, `details` có cấu trúc: ngày vi phạm, phút vượt, cặp task tạo chu trình) |
| `QUOTA_EXHAUSTED`, `AI_RATE_LIMIT_EXCEEDED` | 429 |
| xung đột trạng thái (đã `APPLIED`, đã có phiên `IN_PROGRESS`) | 409 |
| `AI_GATEWAY_TIMEOUT` | 504 |
| `AI_SCHEMA_VALIDATION_ERROR` / AI provider 503 | 502/503 |
Body lỗi thống nhất: `{ "code": "...", "message": "...", "details": {...}, "correlation_id": "..." }`. `message` không chứa dữ liệu nhạy cảm. Frontend map theo `code`, nên **đừng đổi code đã công bố**.
