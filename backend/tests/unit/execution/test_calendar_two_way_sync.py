import hashlib
import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from uuid6 import uuid7

from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.application.use_cases.calendar.process_google_calendar_webhook_use_case import (
    ProcessGoogleCalendarWebhookUseCase,
)
from src.account.application.use_cases.calendar.reconcile_calendar_connections_use_case import (
    ReconcileCalendarConnectionsUseCase,
)
from src.account.application.use_cases.calendar.renew_expiring_calendar_webhooks_use_case import (
    RenewExpiringCalendarWebhooksUseCase,
)
from src.account.application.use_cases.calendar.sync_schedule_blocks_use_case import (
    SyncScheduleBlocksToGoogleUseCase,
)
from src.account.domain.models.calendar_connection import CalendarConnection
from src.account.domain.ports.calendar_provider_port import (
    CalendarEventDTO,
    get_deterministic_event_id,
)
from src.account.infrastructure.adapters.mock_calendar_adapter import (
    MockCalendarAdapter,
)
from src.account.presentation.webhook_router import handle_google_calendar_webhook
from src.planning.public_api import (
    ScheduleBlockSyncDTO,
    ScheduleBlockSyncPort,
)
from src.shared_kernel.config import Settings
from src.shared_kernel.domain.base import utc_now
from src.shared_kernel.infrastructure.security.encryption import (
    encrypt_token,
    generate_fernet_key,
)


# --- In-Memory Implementations for Testing ---
class InMemoryCalendarConnectionRepository(CalendarConnectionRepositoryPort):
    def __init__(self) -> None:
        self.connections: dict[UUID, CalendarConnection] = {}

    async def get_by_user_id_and_provider(
        self, user_id: UUID, provider: str = "GOOGLE"
    ) -> CalendarConnection | None:
        for conn in self.connections.values():
            if conn.user_id == user_id and conn.provider == provider:
                return conn
        return None

    async def get_by_user_id(self, user_id: UUID) -> list[CalendarConnection]:
        return [c for c in self.connections.values() if c.user_id == user_id]

    async def get_by_channel_id(self, channel_id: str) -> CalendarConnection | None:
        for conn in self.connections.values():
            if conn.channel_id == channel_id:
                return conn
        return None

    async def get_expiring_active_connections(
        self, expiration_before: datetime
    ) -> list[CalendarConnection]:
        res: list[CalendarConnection] = []
        for conn in self.connections.values():
            if (
                conn.sync_status == "ACTIVE"
                and conn.channel_expiration is not None
                and conn.channel_expiration <= expiration_before
            ):
                res.append(conn)
        return res

    async def get_active_connections(self) -> list[CalendarConnection]:
        return [c for c in self.connections.values() if c.sync_status == "ACTIVE"]

    async def save(self, connection: CalendarConnection) -> CalendarConnection:
        self.connections[connection.id] = connection
        return connection

    async def delete(self, connection_id: UUID) -> bool:
        if connection_id in self.connections:
            del self.connections[connection_id]
            return True
        return False


class InMemoryScheduleBlockSyncPort(ScheduleBlockSyncPort):
    def __init__(self, blocks: list[ScheduleBlockSyncDTO] | None = None) -> None:
        self.blocks: dict[UUID, ScheduleBlockSyncDTO] = {b.id: b for b in (blocks or [])}

    async def get_blocks_for_schedule(
        self,
        official_schedule_id: UUID,
        sync_status_in: Sequence[str] | None = None,
    ) -> list[ScheduleBlockSyncDTO]:
        res = [b for b in self.blocks.values() if b.official_schedule_id == official_schedule_id]
        if sync_status_in:
            res = [b for b in res if b.sync_status in sync_status_in]
        return res

    async def get_block_by_id(self, block_id: UUID) -> ScheduleBlockSyncDTO | None:
        return self.blocks.get(block_id)

    async def get_block_by_external_event_id(
        self, external_event_id: str
    ) -> ScheduleBlockSyncDTO | None:
        for b in self.blocks.values():
            if b.external_calendar_event_id == external_event_id:
                return b
        return None

    async def update_block_sync_info(
        self,
        block_id: UUID,
        *,
        external_calendar_event_id: str | None = None,
        etag: str | None = None,
        sync_status: str | None = None,
        last_synced_at: datetime | None = None,
    ) -> None:
        if block_id in self.blocks:
            old = self.blocks[block_id]
            self.blocks[block_id] = ScheduleBlockSyncDTO(
                id=old.id,
                roadmap_id=old.roadmap_id,
                official_schedule_id=old.official_schedule_id,
                task_id=old.task_id,
                sequence_in_task=old.sequence_in_task,
                block_type=old.block_type,
                block_date=old.block_date,
                start_time=old.start_time,
                end_time=old.end_time,
                scheduled_duration_minutes=old.scheduled_duration_minutes,
                is_protected=old.is_protected,
                status=old.status,
                external_calendar_event_id=(
                    external_calendar_event_id
                    if external_calendar_event_id is not None
                    else old.external_calendar_event_id
                ),
                etag=etag if etag is not None else old.etag,
                sync_status=sync_status if sync_status is not None else old.sync_status,
                last_synced_at=last_synced_at if last_synced_at is not None else old.last_synced_at,
                placement_rationale=old.placement_rationale,
            )


# ==============================================================================
# FIXTURES
# ==============================================================================
@pytest.fixture
def test_settings() -> Settings:
    key = generate_fernet_key()
    return Settings(
        calendar_encryption_key=key,
        calendar_webhook_base_url="https://api.focusflow.test",
    )


@pytest.fixture
def mock_calendar() -> MockCalendarAdapter:
    adapter = MockCalendarAdapter()
    adapter.reset()
    return adapter


@pytest.fixture
def conn_repo() -> InMemoryCalendarConnectionRepository:
    return InMemoryCalendarConnectionRepository()


# ==============================================================================
# 1. OUTBOUND SYNC TESTS (Deterministic ID & 409 Conflict Recovery)
# ==============================================================================
@pytest.mark.asyncio
async def test_deterministic_event_id_format() -> None:
    block_id = uuid7()
    event_id = get_deterministic_event_id(block_id)

    # Must start with "ff" followed by 32 hex chars = 34 chars total
    assert event_id.startswith("ff")
    assert len(event_id) == 34
    # Must strictly match Google Calendar event ID regex [a-v0-9]{5,1024}
    assert re.match(r"^[a-v0-9]{5,1024}$", event_id) is not None


@pytest.mark.asyncio
async def test_outbound_sync_creates_events_and_updates_blocks(
    conn_repo: InMemoryCalendarConnectionRepository,
    mock_calendar: MockCalendarAdapter,
    test_settings: Settings,
) -> None:
    user_id = uuid7()
    schedule_id = uuid7()
    roadmap_id = uuid7()

    # Active connection with encrypted token
    encrypted = encrypt_token("mock_refresh_token", key=test_settings.calendar_encryption_key)
    conn = CalendarConnection(
        user_id=user_id,
        provider="GOOGLE",
        external_calendar_id="primary",
        oauth_refresh_token_encrypted=encrypted,
        sync_status="ACTIVE",
    )
    await conn_repo.save(conn)

    # 2 ScheduleBlocks
    start1 = datetime.now(UTC) + timedelta(days=1)
    end1 = start1 + timedelta(minutes=45)
    b1 = ScheduleBlockSyncDTO(
        id=uuid7(),
        roadmap_id=roadmap_id,
        official_schedule_id=schedule_id,
        task_id=uuid7(),
        sequence_in_task=1,
        block_type="STUDY",
        block_date=start1.date(),
        start_time=start1,
        end_time=end1,
        scheduled_duration_minutes=45,
        is_protected=False,
        status="PLANNED",
        external_calendar_event_id=None,
        etag=None,
        sync_status="PENDING_SYNC",
        last_synced_at=None,
        placement_rationale=None,
    )

    start2 = end1 + timedelta(minutes=15)
    end2 = start2 + timedelta(minutes=30)
    b2 = ScheduleBlockSyncDTO(
        id=uuid7(),
        roadmap_id=roadmap_id,
        official_schedule_id=schedule_id,
        task_id=uuid7(),
        sequence_in_task=2,
        block_type="REVISION",
        block_date=start2.date(),
        start_time=start2,
        end_time=end2,
        scheduled_duration_minutes=30,
        is_protected=False,
        status="PLANNED",
        external_calendar_event_id=None,
        etag=None,
        sync_status="PENDING_SYNC",
        last_synced_at=None,
        placement_rationale=None,
    )

    block_port = InMemoryScheduleBlockSyncPort([b1, b2])

    use_case = SyncScheduleBlocksToGoogleUseCase(
        repository=conn_repo,
        calendar_provider=mock_calendar,
        schedule_block_port=block_port,
        settings=test_settings,
    )

    result = await use_case.execute(schedule_id=schedule_id, user_id=user_id)
    assert result.total_blocks_scanned == 2
    assert result.synced_blocks_count == 2
    assert result.conflict_resolved_count == 0

    # Verify blocks updated
    updated_b1 = await block_port.get_block_by_id(b1.id)
    assert updated_b1 is not None
    assert updated_b1.sync_status == "SYNCED"
    assert updated_b1.external_calendar_event_id == get_deterministic_event_id(b1.id)
    assert updated_b1.etag is not None
    assert updated_b1.last_synced_at is not None


@pytest.mark.asyncio
async def test_outbound_sync_409_conflict_recovery(
    conn_repo: InMemoryCalendarConnectionRepository,
    mock_calendar: MockCalendarAdapter,
    test_settings: Settings,
) -> None:
    user_id = uuid7()
    schedule_id = uuid7()
    roadmap_id = uuid7()

    encrypted = encrypt_token("mock_refresh_token", key=test_settings.calendar_encryption_key)
    conn = CalendarConnection(
        user_id=user_id,
        provider="GOOGLE",
        external_calendar_id="primary",
        oauth_refresh_token_encrypted=encrypted,
        sync_status="ACTIVE",
    )
    await conn_repo.save(conn)

    block_id = uuid7()
    det_id = get_deterministic_event_id(block_id)
    start_time = datetime.now(UTC) + timedelta(days=2)
    end_time = start_time + timedelta(minutes=60)

    # Pre-populate event in mock Google Calendar to induce 409 Conflict
    existing_event = CalendarEventDTO(
        id=det_id,
        title="Existing Pre-synced Event",
        start_time=start_time,
        end_time=end_time,
        block_id=block_id,
        etag='"etag_conflict_123"',
        extended_properties={"focusflow_block_id": str(block_id)},
    )
    mock_calendar._events["primary"][det_id] = existing_event

    b1 = ScheduleBlockSyncDTO(
        id=block_id,
        roadmap_id=roadmap_id,
        official_schedule_id=schedule_id,
        task_id=uuid7(),
        sequence_in_task=1,
        block_type="STUDY",
        block_date=start_time.date(),
        start_time=start_time,
        end_time=end_time,
        scheduled_duration_minutes=60,
        is_protected=False,
        status="PLANNED",
        external_calendar_event_id=None,
        etag=None,
        sync_status="PENDING_SYNC",
        last_synced_at=None,
        placement_rationale=None,
    )
    block_port = InMemoryScheduleBlockSyncPort([b1])

    use_case = SyncScheduleBlocksToGoogleUseCase(
        repository=conn_repo,
        calendar_provider=mock_calendar,
        schedule_block_port=block_port,
        settings=test_settings,
    )

    result = await use_case.execute(schedule_id=schedule_id, user_id=user_id)
    assert result.total_blocks_scanned == 1
    assert result.synced_blocks_count == 1
    assert result.conflict_resolved_count == 1

    # Verify block resolved 409 without creating duplicate
    updated_b = await block_port.get_block_by_id(block_id)
    assert updated_b is not None
    assert updated_b.sync_status == "SYNCED"
    assert updated_b.external_calendar_event_id == det_id
    assert updated_b.etag == '"etag_conflict_123"'


# ==============================================================================
# 2. WEBHOOK ROUTER 3-HEADER VERIFICATION TESTS
# ==============================================================================
@pytest.mark.asyncio
async def test_webhook_router_header_verification(
    conn_repo: InMemoryCalendarConnectionRepository,
) -> None:
    channel_id = "chan_valid_123"
    resource_id = "res_valid_456"
    secret_token = "secret_channel_token_999"
    token_hash = hashlib.sha256(secret_token.encode("utf-8")).hexdigest()

    conn = CalendarConnection(
        user_id=uuid7(),
        channel_id=channel_id,
        resource_id=resource_id,
        channel_token_hash=token_hash,
        sync_status="ACTIVE",
    )
    await conn_repo.save(conn)

    # 1. Valid 3 headers -> 200 OK / accepted
    resp = await handle_google_calendar_webhook(
        x_goog_channel_id=channel_id,
        x_goog_resource_id=resource_id,
        x_goog_channel_token=secret_token,
        x_goog_resource_state="exists",
        repository=conn_repo,
    )
    assert resp["status"] == "accepted"
    assert resp["channel_id"] == channel_id

    # 2. Channel sync ping -> 200 OK channel verified
    sync_resp = await handle_google_calendar_webhook(
        x_goog_channel_id=channel_id,
        x_goog_resource_id=resource_id,
        x_goog_channel_token=secret_token,
        x_goog_resource_state="sync",
        repository=conn_repo,
    )
    assert sync_resp["status"] == "ok"

    # 3. Missing header -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        await handle_google_calendar_webhook(
            x_goog_channel_id=None,
            x_goog_resource_id=resource_id,
            x_goog_channel_token=secret_token,
            repository=conn_repo,
        )
    assert exc_info.value.status_code == 403

    # 4. Unknown channel ID -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        await handle_google_calendar_webhook(
            x_goog_channel_id="chan_unknown",
            x_goog_resource_id=resource_id,
            x_goog_channel_token=secret_token,
            repository=conn_repo,
        )
    assert exc_info.value.status_code == 403

    # 5. Resource ID mismatch -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        await handle_google_calendar_webhook(
            x_goog_channel_id=channel_id,
            x_goog_resource_id="wrong_res_id",
            x_goog_channel_token=secret_token,
            repository=conn_repo,
        )
    assert exc_info.value.status_code == 403

    # 6. Invalid token hash -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        await handle_google_calendar_webhook(
            x_goog_channel_id=channel_id,
            x_goog_resource_id=resource_id,
            x_goog_channel_token="wrong_token_tampered",
            repository=conn_repo,
        )
    assert exc_info.value.status_code == 403


# ==============================================================================
# 3. INBOUND SYNC: CONTENT & VERSION ECHO CHECK
# ==============================================================================
@pytest.mark.asyncio
async def test_inbound_sync_echo_check_and_strict_review(
    conn_repo: InMemoryCalendarConnectionRepository,
    mock_calendar: MockCalendarAdapter,
    test_settings: Settings,
) -> None:
    channel_id = "chan_echo_test"
    resource_id = "res_echo_test"
    encrypted = encrypt_token("mock_refresh_token", key=test_settings.calendar_encryption_key)
    conn = CalendarConnection(
        user_id=uuid7(),
        channel_id=channel_id,
        resource_id=resource_id,
        oauth_refresh_token_encrypted=encrypted,
        external_calendar_id="primary",
        sync_status="ACTIVE",
    )
    await conn_repo.save(conn)

    start_time = datetime.now(UTC) + timedelta(days=3)
    end_time = start_time + timedelta(minutes=45)

    block_id_echo = uuid7()
    block_id_edited = uuid7()

    det_id_echo = get_deterministic_event_id(block_id_echo)
    det_id_edited = get_deterministic_event_id(block_id_edited)

    # 1. Echo Event: start_time and end_time identical to DB block
    ev_echo = CalendarEventDTO(
        id=det_id_echo,
        title="Echo Session",
        start_time=start_time,
        end_time=end_time,
        block_id=block_id_echo,
        etag='"etag_echo_v2"',
    )
    mock_calendar._events["primary"][det_id_echo] = ev_echo

    # 2. User Edited Event: user pushed start_time 1 hour later on Google!
    ev_edited = CalendarEventDTO(
        id=det_id_edited,
        title="User Edited Session",
        start_time=start_time + timedelta(hours=1),
        end_time=end_time + timedelta(hours=1),
        block_id=block_id_edited,
        etag='"etag_user_edit_v2"',
    )
    mock_calendar._events["primary"][det_id_edited] = ev_edited

    b_echo = ScheduleBlockSyncDTO(
        id=block_id_echo,
        roadmap_id=uuid7(),
        official_schedule_id=uuid7(),
        task_id=uuid7(),
        sequence_in_task=1,
        block_type="STUDY",
        block_date=start_time.date(),
        start_time=start_time,
        end_time=end_time,
        scheduled_duration_minutes=45,
        is_protected=False,
        status="PLANNED",
        external_calendar_event_id=det_id_echo,
        etag='"etag_echo_v1"',
        sync_status="SYNCED",
        last_synced_at=utc_now(),
        placement_rationale=None,
    )

    b_edited = ScheduleBlockSyncDTO(
        id=block_id_edited,
        roadmap_id=uuid7(),
        official_schedule_id=uuid7(),
        task_id=uuid7(),
        sequence_in_task=2,
        block_type="STUDY",
        block_date=start_time.date(),
        start_time=start_time,
        end_time=end_time,
        scheduled_duration_minutes=45,
        is_protected=False,
        status="PLANNED",
        external_calendar_event_id=det_id_edited,
        etag='"etag_user_edit_v1"',
        sync_status="SYNCED",
        last_synced_at=utc_now(),
        placement_rationale=None,
    )

    block_port = InMemoryScheduleBlockSyncPort([b_echo, b_edited])

    use_case = ProcessGoogleCalendarWebhookUseCase(
        repository=conn_repo,
        calendar_provider=mock_calendar,
        schedule_block_port=block_port,
        settings=test_settings,
    )

    result = await use_case.execute(channel_id=channel_id)
    assert result.total_events_received == 2
    assert result.echo_ignored_count == 1
    assert result.pending_review_count == 1

    # Check b_echo: ETag updated to v2, sync_status remained SYNCED
    updated_echo = await block_port.get_block_by_id(block_id_echo)
    assert updated_echo is not None
    assert updated_echo.etag == '"etag_echo_v2"'
    assert updated_echo.sync_status == "SYNCED"

    # Check b_edited: ETag updated, sync_status marked PENDING_REVIEW!
    updated_edited = await block_port.get_block_by_id(block_id_edited)
    assert updated_edited is not None
    assert updated_edited.etag == '"etag_user_edit_v2"'
    assert updated_edited.sync_status == "PENDING_REVIEW"


# ==============================================================================
# 4. EVENT DELETION MATRIX TESTS (100% Preservation of Completed Tasks)
# ==============================================================================
@pytest.mark.asyncio
async def test_event_deletion_matrix_preserves_completed_and_missed_blocks(
    conn_repo: InMemoryCalendarConnectionRepository,
    mock_calendar: MockCalendarAdapter,
    test_settings: Settings,
) -> None:
    channel_id = "chan_deletion_matrix"
    encrypted = encrypt_token("mock_refresh_token", key=test_settings.calendar_encryption_key)
    conn = CalendarConnection(
        user_id=uuid7(),
        channel_id=channel_id,
        resource_id="res_del",
        oauth_refresh_token_encrypted=encrypted,
        external_calendar_id="primary",
        sync_status="ACTIVE",
    )
    await conn_repo.save(conn)

    start_time = datetime.now(UTC) - timedelta(days=1)
    end_time = start_time + timedelta(minutes=45)

    block_completed = uuid7()
    block_missed = uuid7()
    block_planned = uuid7()

    det_completed = get_deterministic_event_id(block_completed)
    det_missed = get_deterministic_event_id(block_missed)
    det_planned = get_deterministic_event_id(block_planned)

    # 3 Cancelled / Deleted events from Google Calendar
    mock_calendar._events["primary"][det_completed] = CalendarEventDTO(
        id=det_completed,
        title="Completed",
        start_time=start_time,
        end_time=end_time,
        block_id=block_completed,
        status="cancelled",
    )
    mock_calendar._events["primary"][det_missed] = CalendarEventDTO(
        id=det_missed,
        title="Missed",
        start_time=start_time,
        end_time=end_time,
        block_id=block_missed,
        status="cancelled",
    )
    mock_calendar._events["primary"][det_planned] = CalendarEventDTO(
        id=det_planned,
        title="Planned",
        start_time=start_time,
        end_time=end_time,
        block_id=block_planned,
        status="cancelled",
    )

    b_comp = ScheduleBlockSyncDTO(
        id=block_completed,
        roadmap_id=uuid7(),
        official_schedule_id=uuid7(),
        task_id=uuid7(),
        sequence_in_task=1,
        block_type="STUDY",
        block_date=start_time.date(),
        start_time=start_time,
        end_time=end_time,
        scheduled_duration_minutes=45,
        is_protected=False,
        status="COMPLETED",  # COMPLETED!
        external_calendar_event_id=det_completed,
        etag='"etag_comp"',
        sync_status="SYNCED",
        last_synced_at=utc_now(),
        placement_rationale=None,
    )
    b_missed = ScheduleBlockSyncDTO(
        id=block_missed,
        roadmap_id=uuid7(),
        official_schedule_id=uuid7(),
        task_id=uuid7(),
        sequence_in_task=2,
        block_type="STUDY",
        block_date=start_time.date(),
        start_time=start_time,
        end_time=end_time,
        scheduled_duration_minutes=45,
        is_protected=False,
        status="MISSED",  # MISSED!
        external_calendar_event_id=det_missed,
        etag='"etag_missed"',
        sync_status="SYNCED",
        last_synced_at=utc_now(),
        placement_rationale=None,
    )
    b_planned = ScheduleBlockSyncDTO(
        id=block_planned,
        roadmap_id=uuid7(),
        official_schedule_id=uuid7(),
        task_id=uuid7(),
        sequence_in_task=3,
        block_type="STUDY",
        block_date=start_time.date(),
        start_time=start_time,
        end_time=end_time,
        scheduled_duration_minutes=45,
        is_protected=False,
        status="PLANNED",
        external_calendar_event_id=det_planned,
        etag='"etag_plan"',
        sync_status="SYNCED",
        last_synced_at=utc_now(),
        placement_rationale=None,
    )

    block_port = InMemoryScheduleBlockSyncPort([b_comp, b_missed, b_planned])

    use_case = ProcessGoogleCalendarWebhookUseCase(
        repository=conn_repo,
        calendar_provider=mock_calendar,
        schedule_block_port=block_port,
        settings=test_settings,
    )

    result = await use_case.execute(channel_id=channel_id)
    assert result.total_events_received == 3
    assert result.deleted_blocks_count == 3

    # COMPLETED block must remain COMPLETED with sync_status EXTERNAL_DELETED (100% progress preservation)
    res_comp = await block_port.get_block_by_id(block_completed)
    assert res_comp is not None
    assert res_comp.status == "COMPLETED"
    assert res_comp.sync_status == "EXTERNAL_DELETED"

    # MISSED block must remain MISSED with sync_status EXTERNAL_DELETED
    res_missed = await block_port.get_block_by_id(block_missed)
    assert res_missed is not None
    assert res_missed.status == "MISSED"
    assert res_missed.sync_status == "EXTERNAL_DELETED"

    # PLANNED block marked EXTERNAL_DELETED without deleting block
    res_planned = await block_port.get_block_by_id(block_planned)
    assert res_planned is not None
    assert res_planned.status == "PLANNED"
    assert res_planned.sync_status == "EXTERNAL_DELETED"


# ==============================================================================
# 5. 410 GONE FULL SYNC RECONCILIATION TESTS
# ==============================================================================
@pytest.mark.asyncio
async def test_inbound_sync_410_gone_triggers_full_sync_without_deleting_blocks(
    conn_repo: InMemoryCalendarConnectionRepository,
    mock_calendar: MockCalendarAdapter,
    test_settings: Settings,
) -> None:
    channel_id = "chan_410_test"
    encrypted = encrypt_token("mock_refresh_token", key=test_settings.calendar_encryption_key)
    conn = CalendarConnection(
        user_id=uuid7(),
        channel_id=channel_id,
        resource_id="res_410",
        oauth_refresh_token_encrypted=encrypted,
        external_calendar_id="primary",
        sync_status="ACTIVE",
        sync_token="stale_sync_token_expired",
    )
    await conn_repo.save(conn)

    # Inject 410 fault into mock adapter
    mock_calendar.inject_fault_410 = True

    block_id = uuid7()
    det_id = get_deterministic_event_id(block_id)
    start_time = datetime.now(UTC) + timedelta(days=5)
    end_time = start_time + timedelta(minutes=45)

    b = ScheduleBlockSyncDTO(
        id=block_id,
        roadmap_id=uuid7(),
        official_schedule_id=uuid7(),
        task_id=uuid7(),
        sequence_in_task=1,
        block_type="STUDY",
        block_date=start_time.date(),
        start_time=start_time,
        end_time=end_time,
        scheduled_duration_minutes=45,
        is_protected=False,
        status="PLANNED",
        external_calendar_event_id=det_id,
        etag='"etag_v1"',
        sync_status="SYNCED",
        last_synced_at=utc_now(),
        placement_rationale=None,
    )
    block_port = InMemoryScheduleBlockSyncPort([b])

    use_case = ProcessGoogleCalendarWebhookUseCase(
        repository=conn_repo,
        calendar_provider=mock_calendar,
        schedule_block_port=block_port,
        settings=test_settings,
    )

    result = await use_case.execute(channel_id=channel_id)
    assert result.full_reconciliation_triggered is True

    # Internal block is preserved, NOT deleted!
    preserved_block = await block_port.get_block_by_id(block_id)
    assert preserved_block is not None


# ==============================================================================
# 6. SWEEPER TASKS TESTS (Renewal & Periodic Reconciliation)
# ==============================================================================
@pytest.mark.asyncio
async def test_renew_expiring_calendar_webhooks_sweeper(
    conn_repo: InMemoryCalendarConnectionRepository,
    mock_calendar: MockCalendarAdapter,
    test_settings: Settings,
) -> None:
    now = utc_now()
    encrypted = encrypt_token("mock_refresh_token", key=test_settings.calendar_encryption_key)

    # 1. Expiring connection: channel expires in 2 hours
    expiring_conn = CalendarConnection(
        id=uuid7(),
        user_id=uuid7(),
        channel_id="chan_expiring_soon",
        resource_id="res_expiring",
        channel_expiration=now + timedelta(hours=2),
        oauth_refresh_token_encrypted=encrypted,
        sync_status="ACTIVE",
    )
    await conn_repo.save(expiring_conn)

    # 2. Healthy connection: channel expires in 6 days
    healthy_conn = CalendarConnection(
        id=uuid7(),
        user_id=uuid7(),
        channel_id="chan_healthy",
        resource_id="res_healthy",
        channel_expiration=now + timedelta(days=6),
        oauth_refresh_token_encrypted=encrypted,
        sync_status="ACTIVE",
    )
    await conn_repo.save(healthy_conn)

    sweeper = RenewExpiringCalendarWebhooksUseCase(
        repository=conn_repo,
        calendar_provider=mock_calendar,
        settings=test_settings,
    )

    renewed_count = await sweeper.execute()
    assert renewed_count == 1

    # Check updated expiring connection
    updated = await conn_repo.get_by_user_id_and_provider(expiring_conn.user_id, "GOOGLE")
    assert updated is not None
    assert updated.channel_id != "chan_expiring_soon"
    assert updated.channel_expiration is not None
    assert updated.channel_expiration > now + timedelta(days=1)

    # Healthy connection was not touched
    untouched = await conn_repo.get_by_user_id_and_provider(healthy_conn.user_id, "GOOGLE")
    assert untouched is not None
    assert untouched.channel_id == "chan_healthy"


@pytest.mark.asyncio
async def test_reconcile_calendar_connections_sweeper(
    conn_repo: InMemoryCalendarConnectionRepository,
    mock_calendar: MockCalendarAdapter,
    test_settings: Settings,
) -> None:
    encrypted = encrypt_token("mock_refresh_token", key=test_settings.calendar_encryption_key)
    conn = CalendarConnection(
        id=uuid7(),
        user_id=uuid7(),
        channel_id="chan_reconcile",
        resource_id="res_reconcile",
        oauth_refresh_token_encrypted=encrypted,
        sync_status="ACTIVE",
    )
    await conn_repo.save(conn)

    block_port = InMemoryScheduleBlockSyncPort([])
    inbound_uc = ProcessGoogleCalendarWebhookUseCase(
        repository=conn_repo,
        calendar_provider=mock_calendar,
        schedule_block_port=block_port,
        settings=test_settings,
    )

    sweeper = ReconcileCalendarConnectionsUseCase(
        repository=conn_repo,
        process_webhook_use_case=inbound_uc,
    )

    reconciled_count = await sweeper.execute()
    assert reconciled_count == 1
