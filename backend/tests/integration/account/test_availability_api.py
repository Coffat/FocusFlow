from collections.abc import AsyncGenerator, Generator
from datetime import time
from typing import Self
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from uuid6 import uuid7

from src.account.application.dtos.availability import (
    AllowedWindowDTO,
    DayScheduleDTO,
    TimeSlotDTO,
    UpdateAvailabilityRequestDTO,
    WeeklyScheduleDTO,
)
from src.account.application.ports.availability_repository_port import (
    AvailabilityRepositoryPort,
)
from src.account.application.use_cases.availability.get_availability_use_case import (
    GetAvailabilityUseCase,
)
from src.account.application.use_cases.availability.update_availability_use_case import (
    UpdateAvailabilityUseCase,
)
from src.account.domain.events.availability_events import AvailabilityUpdatedEvent
from src.account.domain.exceptions.availability import (
    ConcurrentAvailabilityModifiedException,
)
from src.account.domain.models.availability import (
    AvailabilityMode,
    AvailabilityProfile,
    CalendarIntegrationMode,
)
from src.account.infrastructure.adapters.availability_query_adapter import (
    SqlAlchemyAvailabilityQueryAdapter,
)
from src.account.infrastructure.orm.availability_orm import (
    AvailabilityORM,
    AvailabilitySlotORM,
)
from src.account.infrastructure.orm.user_orm import UserORM
from src.account.infrastructure.repositories.availability_repository import (
    SqlAlchemyAvailabilityRepository,
)
from src.account.presentation.deps import (
    get_account_uow,
    get_availability_repository,
    get_current_learner_id,
    get_get_availability_use_case,
    get_update_availability_use_case,
)
from src.account.public_api import ProposedTaskBlockDTO
from src.main import app
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import AggregateRoot
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import (
    SqlAlchemyUnitOfWork,
)
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM


class InMemoryAvailabilityRepository(AvailabilityRepositoryPort):
    """In-memory test double for repository simulating 3NF persistence."""

    def __init__(self) -> None:
        self.profiles: dict[UUID, AvailabilityProfile] = {}

    async def get_by_user_id(self, user_id: UUID) -> AvailabilityProfile | None:
        return self.profiles.get(user_id)

    async def save(self, profile: AvailabilityProfile) -> AvailabilityProfile:
        self.profiles[profile.user_id] = profile
        return profile


class InMemoryUnitOfWork(AsyncUnitOfWork):
    """In-memory test double for Unit of Work capturing outbox events."""

    def __init__(self) -> None:
        self.collected_events: list[AvailabilityUpdatedEvent] = []
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if exc_type is not None:
            self.rolled_back = True

    def collect_events_from(self, aggregate: AggregateRoot) -> None:
        events = aggregate.pull_domain_events()
        for ev in events:
            if isinstance(ev, AvailabilityUpdatedEvent):
                self.collected_events.append(ev)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def _create_sample_weekly_dto(mode: str = "MODE_A") -> WeeklyScheduleDTO:
    """Helper to build a valid WeeklyScheduleDTO."""
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    days: dict[str, DayScheduleDTO] = {}
    for d in day_names:
        is_weekend = d in ("saturday", "sunday")
        days[d] = DayScheduleDTO(
            enabled=True,
            quota_hours=3.0 if is_weekend else 2.0,
            time_slots=[
                TimeSlotDTO(start="14:00", end="17:00")
                if is_weekend
                else TimeSlotDTO(start="19:30", end="21:30")
            ],
            allowed_window=AllowedWindowDTO(start="07:00", end="23:00"),
            preferred_period="AFTERNOON" if is_weekend else "EVENING",
            min_session_minutes=30,
        )
    return WeeklyScheduleDTO(**days)


@pytest.fixture
def test_setup() -> Generator[
    tuple[InMemoryAvailabilityRepository, InMemoryUnitOfWork, UUID], None, None
]:
    repo = InMemoryAvailabilityRepository()
    uow = InMemoryUnitOfWork()
    user_id = uuid7()

    app.dependency_overrides[get_current_learner_id] = lambda: user_id
    app.dependency_overrides[get_availability_repository] = lambda: repo
    app.dependency_overrides[get_account_uow] = lambda: uow
    app.dependency_overrides[get_get_availability_use_case] = lambda: GetAvailabilityUseCase(repo)
    app.dependency_overrides[get_update_availability_use_case] = lambda: UpdateAvailabilityUseCase(
        repo, uow
    )

    try:
        yield repo, uow, user_id
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# API INTEGRATION TESTS: GET /me & PUT /me
# =============================================================================


@pytest.mark.asyncio
async def test_get_availability_lazy_initialization(
    test_setup: tuple[InMemoryAvailabilityRepository, InMemoryUnitOfWork, UUID],
) -> None:
    """TC-API-01: GET /me returns lazy default template with id=None when user has no DB record."""
    repo, _, user_id = test_setup
    assert await repo.get_by_user_id(user_id) is None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/availabilities/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] is None
    assert data["user_id"] == str(user_id)
    assert data["mode"] == "MODE_A"
    assert data["calendar_integration_mode"] == "NONE"
    assert data["total_weekly_hours"] == 16.0
    assert data["weekly_schedule"]["monday"]["quota_hours"] == 2.0
    assert data["weekly_schedule"]["saturday"]["quota_hours"] == 3.0


@pytest.mark.asyncio
async def test_put_availability_persists_and_emits_outbox(
    test_setup: tuple[InMemoryAvailabilityRepository, InMemoryUnitOfWork, UUID],
) -> None:
    """TC-API-02: PUT /me saves schedule, generates ID, and emits AvailabilityUpdatedEvent."""
    repo, uow, user_id = test_setup
    weekly_dto = _create_sample_weekly_dto("MODE_A")
    req_payload = UpdateAvailabilityRequestDTO(
        mode="MODE_A",
        calendar_integration_mode="EXPORT_ICS",
        min_session_minutes=45,
        weekly_schedule=weekly_dto,
    ).model_dump()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/api/v1/availabilities/me", json=req_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["mode"] == "MODE_A"
    assert data["calendar_integration_mode"] == "EXPORT_ICS"
    assert data["min_session_minutes"] == 45
    assert data["total_weekly_hours"] == 16.0

    # Verify repository persistence
    saved_profile = await repo.get_by_user_id(user_id)
    assert saved_profile is not None
    assert saved_profile.mode == AvailabilityMode.MODE_A
    assert saved_profile.calendar_integration_mode == CalendarIntegrationMode.EXPORT_ICS

    # Verify Outbox event collection and UoW commit
    assert uow.committed is True
    assert len(uow.collected_events) == 1
    assert uow.collected_events[0].user_id == user_id
    assert uow.collected_events[0].availability_mode == "MODE_A"


@pytest.mark.asyncio
async def test_put_availability_rejects_invalid_quota_bounds(
    test_setup: tuple[InMemoryAvailabilityRepository, InMemoryUnitOfWork, UUID],
) -> None:
    """TC-API-03: PUT /me rejects daily quota violating OS-06 (< 0.5h or > 14.0h) with 422."""
    _, _, _ = test_setup
    weekly_dto = _create_sample_weekly_dto("MODE_A")
    # Set Monday quota to 0.2h (below 0.5h minimum)
    weekly_dict = weekly_dto.model_dump()
    weekly_dict["monday"]["quota_hours"] = 0.2

    req_payload = {
        "mode": "MODE_A",
        "calendar_integration_mode": "NONE",
        "min_session_minutes": 30,
        "weekly_schedule": weekly_dict,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/api/v1/availabilities/me", json=req_payload)

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "INVALID_QUOTA_BOUNDS"
    assert data["details"]["day"] == "monday"
    assert data["details"]["quota_hours"] == 0.2


@pytest.mark.asyncio
async def test_put_availability_rejects_overlapping_time_slots(
    test_setup: tuple[InMemoryAvailabilityRepository, InMemoryUnitOfWork, UUID],
) -> None:
    """TC-API-04: PUT /me in Mode B rejects overlapping time slots with 422."""
    _, _, _ = test_setup
    weekly_dto = _create_sample_weekly_dto("MODE_B")
    weekly_dict = weekly_dto.model_dump()
    # Wednesday has 2 overlapping slots: 08:00-10:00 and 09:30-11:00
    weekly_dict["wednesday"]["time_slots"] = [
        {"start": "08:00", "end": "10:00", "end_day_offset": 0},
        {"start": "09:30", "end": "11:00", "end_day_offset": 0},
    ]

    req_payload = {
        "mode": "MODE_B",
        "calendar_integration_mode": "NONE",
        "min_session_minutes": 30,
        "weekly_schedule": weekly_dict,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/api/v1/availabilities/me", json=req_payload)

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "OVERLAPPING_TIME_SLOTS"
    assert data["details"]["day"] == "wednesday"
    assert len(data["details"]["conflicting_slots"]) == 2


@pytest.mark.asyncio
async def test_put_availability_rejects_insufficient_weekly_hours(
    test_setup: tuple[InMemoryAvailabilityRepository, InMemoryUnitOfWork, UUID],
) -> None:
    """TC-API-05: PUT /me rejects total weekly hours < 1.0h with 422."""
    _, _, _ = test_setup
    weekly_dto = _create_sample_weekly_dto("MODE_A")
    weekly_dict = weekly_dto.model_dump()
    # Disable all days except monday with 0.5h -> total 0.5h < 1.0h
    for day in weekly_dict:
        weekly_dict[day]["enabled"] = False
    weekly_dict["monday"]["enabled"] = True
    weekly_dict["monday"]["quota_hours"] = 0.5

    req_payload = {
        "mode": "MODE_A",
        "calendar_integration_mode": "NONE",
        "min_session_minutes": 30,
        "weekly_schedule": weekly_dict,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/api/v1/availabilities/me", json=req_payload)

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "INSUFFICIENT_WEEKLY_AVAILABILITY"
    assert data["details"]["total_hours"] == 0.5


@pytest.mark.asyncio
async def test_mode_switching_state_retention(
    test_setup: tuple[InMemoryAvailabilityRepository, InMemoryUnitOfWork, UUID],
) -> None:
    """TC-API-06: Switching Mode A -> Mode B -> Mode A preserves slots and quotas without data loss."""
    repo, _, user_id = test_setup
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Save in Mode B with custom slots
        weekly_dto = _create_sample_weekly_dto("MODE_B")
        weekly_dict = weekly_dto.model_dump()
        weekly_dict["monday"]["time_slots"] = [
            {"start": "06:00", "end": "08:00", "end_day_offset": 0},
            {"start": "20:00", "end": "22:00", "end_day_offset": 0},
        ]
        weekly_dict["monday"]["quota_hours"] = 4.0

        res1 = await client.put(
            "/api/v1/availabilities/me",
            json={
                "mode": "MODE_B",
                "calendar_integration_mode": "NONE",
                "min_session_minutes": 30,
                "weekly_schedule": weekly_dict,
            },
        )
        assert res1.status_code == 200
        assert res1.json()["mode"] == "MODE_B"

        # Step 2: Switch to Mode A, keep weekly schedule payload intact
        weekly_dict["monday"]["quota_hours"] = 3.5
        res2 = await client.put(
            "/api/v1/availabilities/me",
            json={
                "mode": "MODE_A",
                "calendar_integration_mode": "NONE",
                "min_session_minutes": 30,
                "weekly_schedule": weekly_dict,
            },
        )
        assert res2.status_code == 200
        assert res2.json()["mode"] == "MODE_A"

        # Step 3: Verify the saved profile still contains Mode B's time_slots
        profile = await repo.get_by_user_id(user_id)
        assert profile is not None
        assert profile.mode == AvailabilityMode.MODE_A
        monday_slots = profile.weekly_schedule.days["monday"].time_slots
        assert len(monday_slots) == 2
        assert monday_slots[0].start_time == time(6, 0)
        assert monday_slots[1].start_time == time(20, 0)


# =============================================================================
# ADAPTER & QUERY PORT TESTS: AvailabilityQueryPort & Optimistic Locking
# =============================================================================


@pytest.mark.asyncio
async def test_availability_query_adapter_proposal_and_optimistic_locking() -> None:
    """TC-API-07: Query Adapter tests schedule proposal validation and detects concurrent updates (409)."""
    repo = InMemoryAvailabilityRepository()
    adapter = SqlAlchemyAvailabilityQueryAdapter(repository=repo)
    user_id = uuid7()

    profile = AvailabilityProfile.create_default(user_id)
    await repo.save(profile)

    # 1. Snapshot test
    snapshot = await adapter.get_active_availability(user_id)
    assert snapshot is not None
    assert snapshot.mode == "MODE_A"
    assert snapshot.weekly_capacity_minutes == 16 * 60

    # 2. Validate proposal under Mode A (within ceiling: monday 2h = 120m)
    task1 = ProposedTaskBlockDTO(
        task_id=uuid7(),
        title="Python Fundamentals",
        day_of_week="monday",
        start_time="19:30",
        end_time="21:00",
        duration_minutes=90,
    )
    result_valid = await adapter.validate_schedule_proposal(
        user_id=user_id,
        proposed_tasks=[task1],
        expected_updated_at=profile.updated_at.isoformat(),
    )
    assert result_valid.is_valid is True
    assert result_valid.has_soft_overflow is False

    # 3. Validate proposal exceeding Mode A ceiling (task duration 150m > 120m)
    task_exceed = ProposedTaskBlockDTO(
        task_id=uuid7(),
        title="Heavy Lab Session",
        day_of_week="monday",
        start_time="19:00",
        end_time="21:30",
        duration_minutes=150,
    )
    result_exceed = await adapter.validate_schedule_proposal(
        user_id=user_id,
        proposed_tasks=[task_exceed],
    )
    assert result_exceed.is_valid is False
    assert result_exceed.overflow_minutes == 30

    # 4. Optimistic locking: mismatch between expected_updated_at and actual
    with pytest.raises(ConcurrentAvailabilityModifiedException):
        await adapter.validate_schedule_proposal(
            user_id=user_id,
            proposed_tasks=[task1],
            expected_updated_at="2026-01-01T00:00:00+00:00",
        )


# =============================================================================
# REPOSITORY 3NF DATA MAPPER & UOW TESTS
# =============================================================================


class FakeAsyncSession:
    """Fake AsyncSession tracking add, flush, and execute calls."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = False
        self.committed = False
        self.rolled_back = False

    def add(self, entity: object) -> None:
        self.added.append(entity)

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def execute(self, stmt: object) -> object:
        class FakeResult:
            def scalar_one_or_none(self) -> None:
                return None

            def scalars(self) -> "FakeResult":
                return self

            def all(self) -> list[object]:
                return []

        return FakeResult()


@pytest.mark.asyncio
async def test_sqlalchemy_availability_repository_3nf_save() -> None:
    """TC-REPO-01: SqlAlchemyAvailabilityRepository maps profile to 3NF availabilities and availability_slots."""
    fake_session = FakeAsyncSession()
    repo = SqlAlchemyAvailabilityRepository(session=fake_session)  # type: ignore[arg-type]
    user_id = uuid7()
    profile = AvailabilityProfile.create_default(user_id)

    saved = await repo.save(profile)
    assert saved.user_id == user_id
    assert fake_session.flushed is True

    # Check that AvailabilityORM and AvailabilitySlotORM instances were added
    avail_orms = [e for e in fake_session.added if isinstance(e, AvailabilityORM)]
    slot_orms = [e for e in fake_session.added if isinstance(e, AvailabilitySlotORM)]

    assert len(avail_orms) == 1
    assert avail_orms[0].user_id == user_id
    assert avail_orms[0].mode == "MODE_A"

    # Default profile has 7 ALLOWED slots + 7 FIXED slots = 14 slot records in 3NF table
    assert len(slot_orms) == 14
    fixed_slots = [s for s in slot_orms if s.slot_type == "FIXED"]
    allowed_slots = [s for s in slot_orms if s.slot_type == "ALLOWED"]
    assert len(fixed_slots) == 7
    assert len(allowed_slots) == 7


@pytest.mark.asyncio
async def test_sqlalchemy_uow_collects_events_and_commits() -> None:
    """TC-UOW-01: SqlAlchemyUnitOfWork collects DomainEvents and flushes them to outbox_events."""
    fake_session = FakeAsyncSession()
    uow = SqlAlchemyUnitOfWork(session=fake_session)  # type: ignore[arg-type]

    user_id = uuid7()
    profile = AvailabilityProfile.create_default(user_id)
    # Trigger an event
    profile.update_schedule(
        new_schedule=profile.weekly_schedule,
        calendar_integration_mode=CalendarIntegrationMode.NONE,
        min_session_minutes=30,
    )

    uow.collect_events_from(profile)
    await uow.commit()

    assert fake_session.committed is True
    from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM

    outbox_entries = [e for e in fake_session.added if isinstance(e, OutboxEventORM)]
    assert len(outbox_entries) == 1
    assert outbox_entries[0].event_type == "AvailabilityUpdatedEvent"
    assert outbox_entries[0].aggregate_type == "AvailabilityProfile"
    assert outbox_entries[0].payload["user_id"] == str(user_id)
    assert outbox_entries[0].payload["availability_mode"] == "MODE_A"


# =============================================================================
# REAL POSTGRESQL 16 E2E INTEGRATION TESTS (E2E-INT-01 .. E2E-INT-06)
# =============================================================================


@pytest.fixture
async def pg_learner_user() -> AsyncGenerator[UUID, None]:
    """Create a real learner user in PostgreSQL 16 and wire get_current_learner_id."""
    user_id = uuid7()
    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"e2e_avail_{user_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="E2E Postgres Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        session.add(user)
        await session.commit()

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_learner_id] = lambda: user_id

    try:
        yield user_id
    finally:
        app.dependency_overrides.clear()
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_e2e_int_01_02_03_04_real_postgres_3nf_persistence_and_state_retention(
    pg_learner_user: UUID,
) -> None:
    """
    E2E-INT-01..04 on real PostgreSQL 16:
    - E2E-INT-01: GET /me lazy default returns id=None and writes 0 rows to `availabilities`.
    - E2E-INT-02: PUT /me Mode A writes `availabilities`, 3NF `availability_slots` (ALLOWED + FIXED), and `outbox_events`.
    - E2E-INT-03: PUT /me Mode B (including cross-midnight slot) then switch back to Mode A with `time_slots=[]` preserves 100% of Mode B slots in PostgreSQL.
    - E2E-INT-04: Disabling Monday (`enabled=False, quota_hours=0, time_slots=[]`) preserves Monday's quota and slots in PostgreSQL.
    """
    user_id = pg_learner_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # --- E2E-INT-01: Lazy GET ---
        res_get1 = await client.get("/api/v1/availabilities/me")
        assert res_get1.status_code == 200
        data_get1 = res_get1.json()
        assert data_get1["id"] is None
        assert data_get1["mode"] == "MODE_A"
        assert data_get1["total_weekly_hours"] == 16.0

        async with async_session_factory() as session:
            count_res = await session.execute(
                select(func.count())
                .select_from(AvailabilityORM)
                .where(AvailabilityORM.user_id == user_id)
            )
            assert count_res.scalar_one() == 0

        # --- E2E-INT-02: PUT Mode A (Mon-Fri 2.5h, allowed_window 06:30-22:30, Sat-Sun disabled) ---
        weekly_mode_a = _create_sample_weekly_dto("MODE_A").model_dump()
        for day_name in ("monday", "tuesday", "wednesday", "thursday", "friday"):
            weekly_mode_a[day_name]["enabled"] = True
            weekly_mode_a[day_name]["quota_hours"] = 2.5
            weekly_mode_a[day_name]["preferred_period"] = "EVENING"
            weekly_mode_a[day_name]["allowed_window"] = {"start": "06:30", "end": "22:30"}
            weekly_mode_a[day_name]["time_slots"] = []
        for day_name in ("saturday", "sunday"):
            weekly_mode_a[day_name]["enabled"] = False
            weekly_mode_a[day_name]["quota_hours"] = 0.0
            weekly_mode_a[day_name]["time_slots"] = []

        res_put_a = await client.put(
            "/api/v1/availabilities/me",
            json={
                "mode": "MODE_A",
                "calendar_integration_mode": "EXPORT_ICS",
                "min_session_minutes": 45,
                "weekly_schedule": weekly_mode_a,
            },
        )
        assert res_put_a.status_code == 200
        data_put_a = res_put_a.json()
        assert data_put_a["id"] is not None
        assert data_put_a["total_weekly_hours"] == 12.5
        avail_id = UUID(data_put_a["id"])

        async with async_session_factory() as session:
            avail_row = (
                await session.execute(
                    select(AvailabilityORM).where(AvailabilityORM.user_id == user_id)
                )
            ).scalar_one()
            assert avail_row.id == avail_id
            assert avail_row.mode == "MODE_A"
            assert avail_row.daily_quotas["monday"]["quota_hours"] == 2.5

            slot_rows = list(
                (
                    await session.execute(
                        select(AvailabilitySlotORM).where(
                            AvailabilitySlotORM.availability_id == avail_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            allowed_rows = [s for s in slot_rows if s.slot_type == "ALLOWED"]
            fixed_rows = [s for s in slot_rows if s.slot_type == "FIXED"]
            assert len(allowed_rows) == 7
            assert len(fixed_rows) == 7
            mon_allowed = next(s for s in allowed_rows if s.day_of_week == 0)
            assert mon_allowed.start_time == time(6, 30)
            assert mon_allowed.end_time == time(22, 30)

            outbox_rows = list(
                (
                    await session.execute(
                        select(OutboxEventORM).where(OutboxEventORM.aggregate_id == avail_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(outbox_rows) == 1
            assert outbox_rows[0].event_type == "AvailabilityUpdatedEvent"
            assert outbox_rows[0].status == "PENDING"
            assert outbox_rows[0].published_at is None

        # --- E2E-INT-03: Switch to Mode B (with cross-midnight Saturday slot), then back to Mode A with time_slots=[] ---
        weekly_mode_b = _create_sample_weekly_dto("MODE_B").model_dump()
        for d in weekly_mode_b.values():
            d["quota_hours"] = 0.0  # Simulate client sending 0 in Mode B
        weekly_mode_b["monday"]["enabled"] = True
        weekly_mode_b["monday"]["time_slots"] = [
            {"start": "19:00", "end": "20:30", "end_day_offset": 0},
            {"start": "21:00", "end": "22:30", "end_day_offset": 0},
        ]
        weekly_mode_b["saturday"]["enabled"] = True
        weekly_mode_b["saturday"]["time_slots"] = [
            {"start": "22:30", "end": "00:30", "end_day_offset": 1},
        ]

        res_put_b = await client.put(
            "/api/v1/availabilities/me",
            json={
                "mode": "MODE_B",
                "calendar_integration_mode": "EXPORT_ICS",
                "min_session_minutes": 45,
                "weekly_schedule": weekly_mode_b,
            },
        )
        assert res_put_b.status_code == 200
        data_put_b = res_put_b.json()
        assert data_put_b["mode"] == "MODE_B"
        # Monday quota_hours=2.5 from Mode A must be preserved even though Mode B request sent 0.0
        assert data_put_b["weekly_schedule"]["monday"]["quota_hours"] == 2.5

        # Now switch back to Mode A sending empty time_slots=[]
        weekly_back_to_a = data_put_b["weekly_schedule"]
        for d in weekly_back_to_a.values():
            d["time_slots"] = []
        res_back_a = await client.put(
            "/api/v1/availabilities/me",
            json={
                "mode": "MODE_A",
                "calendar_integration_mode": "EXPORT_ICS",
                "min_session_minutes": 45,
                "weekly_schedule": weekly_back_to_a,
            },
        )
        assert res_back_a.status_code == 200

        res_get_after_a = await client.get("/api/v1/availabilities/me")
        assert res_get_after_a.status_code == 200
        data_after_a = res_get_after_a.json()
        assert data_after_a["mode"] == "MODE_A"
        mon_slots = data_after_a["weekly_schedule"]["monday"]["time_slots"]
        assert len(mon_slots) == 2
        assert mon_slots[0] == {"start": "19:00", "end": "20:30", "end_day_offset": 0}
        assert mon_slots[1] == {"start": "21:00", "end": "22:30", "end_day_offset": 0}
        sat_slots = data_after_a["weekly_schedule"]["saturday"]["time_slots"]
        assert len(sat_slots) == 1
        assert sat_slots[0] == {"start": "22:30", "end": "00:30", "end_day_offset": 1}

        # --- E2E-INT-04: Disable Monday (enabled=False, quota_hours=0, time_slots=[]) and verify retention ---
        weekly_disable_mon = data_after_a["weekly_schedule"]
        weekly_disable_mon["monday"]["enabled"] = False
        weekly_disable_mon["monday"]["quota_hours"] = 0.0
        weekly_disable_mon["monday"]["time_slots"] = []

        res_disable_mon = await client.put(
            "/api/v1/availabilities/me",
            json={
                "mode": "MODE_A",
                "calendar_integration_mode": "EXPORT_ICS",
                "min_session_minutes": 45,
                "weekly_schedule": weekly_disable_mon,
            },
        )
        assert res_disable_mon.status_code == 200
        data_disabled = res_disable_mon.json()
        assert data_disabled["weekly_schedule"]["monday"]["enabled"] is False
        assert data_disabled["weekly_schedule"]["monday"]["quota_hours"] == 2.5
        assert len(data_disabled["weekly_schedule"]["monday"]["time_slots"]) == 2


@pytest.mark.asyncio
async def test_e2e_int_05_real_postgres_422_validation_and_rollback(
    pg_learner_user: UUID,
) -> None:
    """E2E-INT-05: All 5 categories of invalid payloads return HTTP 422 with exact error codes (never 500)."""
    transport = ASGITransport(app=app)
    base_weekly = _create_sample_weekly_dto("MODE_A").model_dump()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # (a) Mode A quota_hours < 0.5
        w_a = _create_sample_weekly_dto("MODE_A").model_dump()
        w_a["monday"]["quota_hours"] = 0.2
        r_a = await client.put(
            "/api/v1/availabilities/me",
            json={"mode": "MODE_A", "weekly_schedule": w_a},
        )
        assert r_a.status_code == 422
        assert r_a.json()["code"] == "INVALID_QUOTA_BOUNDS"

        # (b) Mode A quota_hours > 14.0
        w_b = _create_sample_weekly_dto("MODE_A").model_dump()
        w_b["monday"]["quota_hours"] = 15.0
        r_b = await client.put(
            "/api/v1/availabilities/me",
            json={"mode": "MODE_A", "weekly_schedule": w_b},
        )
        assert r_b.status_code == 422
        assert r_b.json()["code"] == "INVALID_QUOTA_BOUNDS"

        # (c) Mode B overlapping slots
        w_c = _create_sample_weekly_dto("MODE_B").model_dump()
        w_c["monday"]["time_slots"] = [
            {"start": "19:00", "end": "21:00", "end_day_offset": 0},
            {"start": "20:00", "end": "22:00", "end_day_offset": 0},
        ]
        r_c = await client.put(
            "/api/v1/availabilities/me",
            json={"mode": "MODE_B", "weekly_schedule": w_c},
        )
        assert r_c.status_code == 422
        assert r_c.json()["code"] == "OVERLAPPING_TIME_SLOTS"

        # (d) Total weekly hours < 1.0h
        w_d = _create_sample_weekly_dto("MODE_A").model_dump()
        for d in w_d.values():
            d["enabled"] = False
        w_d["monday"]["enabled"] = True
        w_d["monday"]["quota_hours"] = 0.5
        r_d = await client.put(
            "/api/v1/availabilities/me",
            json={"mode": "MODE_A", "weekly_schedule": w_d},
        )
        assert r_d.status_code == 422
        assert r_d.json()["code"] == "INSUFFICIENT_WEEKLY_AVAILABILITY"

        # (e1) Invalid mode enum -> 422 INVALID_AVAILABILITY_MODE
        r_e1 = await client.put(
            "/api/v1/availabilities/me",
            json={"mode": "INVALID_MODE", "weekly_schedule": base_weekly},
        )
        assert r_e1.status_code == 422
        assert r_e1.json()["code"] == "INVALID_AVAILABILITY_MODE"

        # (e2) Invalid min_session_minutes -> 422 INVALID_MIN_SESSION_MINUTES
        r_e2 = await client.put(
            "/api/v1/availabilities/me",
            json={"mode": "MODE_A", "min_session_minutes": 5, "weekly_schedule": base_weekly},
        )
        assert r_e2.status_code == 422
        assert r_e2.json()["code"] == "INVALID_MIN_SESSION_MINUTES"

        # (e3) Invalid preferred_period -> 422 INVALID_PREFERRED_PERIOD
        w_e3 = _create_sample_weekly_dto("MODE_A").model_dump()
        w_e3["monday"]["preferred_period"] = "LATE_NIGHT"
        r_e3 = await client.put(
            "/api/v1/availabilities/me",
            json={"mode": "MODE_A", "weekly_schedule": w_e3},
        )
        assert r_e3.status_code == 422
        assert r_e3.json()["code"] == "INVALID_PREFERRED_PERIOD"


@pytest.mark.asyncio
async def test_e2e_int_06_real_postgres_query_port_cross_context_validation(
    pg_learner_user: UUID,
) -> None:
    """
    E2E-INT-06 on real PostgreSQL 16:
    - Lazy default user: get_active_availability returns default snapshot, no false 409 on lazy expected_updated_at.
    - Mode A multi-roadmap ceiling (90m occupied + 90m proposed > 120m ceiling -> is_valid=False, overflow=60m).
    - Mode A allowed_window check.
    - Mode B soft overflow (15m overflow -> is_valid=True, has_soft_overflow=True, overflow=15m).
    - Optimistic locking: 'Z' vs '+00:00' format compatibility + 409 Conflict when updated_at changes.
    """
    user_id = pg_learner_user

    async with async_session_factory() as session:
        repo = SqlAlchemyAvailabilityRepository(session)
        adapter = SqlAlchemyAvailabilityQueryAdapter(repo)

        # 1. Lazy user (before saving to DB)
        snap_lazy = await adapter.get_active_availability(user_id)
        assert snap_lazy is not None
        assert snap_lazy.mode == "MODE_A"
        assert snap_lazy.updated_at is None

        task_90m = ProposedTaskBlockDTO(
            task_id=uuid7(),
            title="Roadmap 2 Task",
            day_of_week="monday",
            start_time="19:00",
            end_time="20:30",
            duration_minutes=90,
        )
        res_lazy = await adapter.validate_schedule_proposal(
            user_id=user_id,
            proposed_tasks=[task_90m],
            expected_updated_at="2026-10-28T00:00:00Z",
        )
        assert res_lazy.is_valid is True

        # 2. Save Mode A profile (Monday = 2.0h = 120m, allowed_window = 07:00-23:00)
        profile = AvailabilityProfile.create_default(user_id)
        await repo.save(profile)
        await session.commit()

        persisted = await repo.get_by_user_id(user_id)
        assert persisted is not None
        z_timestamp = persisted.updated_at.isoformat().replace("+00:00", "Z")

        # Multi-roadmap Mode A: 90m occupied + 90m proposed = 180m > 120m -> overflow = 60m
        occ_90m = ProposedTaskBlockDTO(
            task_id=uuid7(),
            title="Roadmap 1 Occupied Task",
            day_of_week="monday",
            start_time="08:00",
            end_time="09:30",
            duration_minutes=90,
        )
        res_multi = await adapter.validate_schedule_proposal(
            user_id=user_id,
            proposed_tasks=[task_90m],
            occupied_tasks=[occ_90m],
            expected_updated_at=z_timestamp,
        )
        assert res_multi.is_valid is False
        assert res_multi.overflow_minutes == 60

        # Mode A outside allowed_window (05:30-06:30 is outside 07:00-23:00)
        task_early = ProposedTaskBlockDTO(
            task_id=uuid7(),
            title="Too Early Task",
            day_of_week="monday",
            start_time="05:30",
            end_time="06:30",
            duration_minutes=60,
        )
        res_early = await adapter.validate_schedule_proposal(
            user_id=user_id,
            proposed_tasks=[task_early],
            expected_updated_at=z_timestamp,
        )
        assert res_early.is_valid is False
        assert any("khung giờ cho phép" in r for r in res_early.violation_reasons)

        # 3. Switch to Mode B (Monday slot 19:30-21:30) and test 15m Soft Overflow (19:30-21:45)
        persisted.update_schedule(
            new_schedule=persisted.weekly_schedule,
            new_mode=AvailabilityMode.MODE_B,
        )
        await repo.save(persisted)
        await session.commit()

        task_soft_overflow = ProposedTaskBlockDTO(
            task_id=uuid7(),
            title="Soft Overflow Task (+15m)",
            day_of_week="monday",
            start_time="19:30",
            end_time="21:45",
            duration_minutes=135,
        )
        res_soft = await adapter.validate_schedule_proposal(
            user_id=user_id,
            proposed_tasks=[task_soft_overflow],
        )
        assert res_soft.is_valid is True
        assert res_soft.has_soft_overflow is True
        assert res_soft.overflow_minutes == 15

        # 4. Optimistic locking: passing stale z_timestamp from before the Mode B update raises 409
        with pytest.raises(ConcurrentAvailabilityModifiedException):
            await adapter.validate_schedule_proposal(
                user_id=user_id,
                proposed_tasks=[task_soft_overflow],
                expected_updated_at=z_timestamp,
            )
