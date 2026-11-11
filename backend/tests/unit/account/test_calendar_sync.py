import base64
import json
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.account.application.dtos.calendar import (
    CalendarOAuthCallbackRequestDTO,
    InitiateCalendarAuthRequestDTO,
)
from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.application.use_cases.calendar import (
    DisconnectGoogleCalendarUseCase,
    GetCalendarConnectionStatusUseCase,
    HandleGoogleCalendarOAuthCallbackUseCase,
    InitiateGoogleCalendarAuthUseCase,
)
from src.account.domain.models.calendar_connection import CalendarConnection
from src.account.domain.ports.calendar_provider_port import (
    CalendarConflictError,
    CalendarEventDTO,
    CalendarPreconditionFailedError,
    CalendarRateLimitError,
)
from src.account.infrastructure.adapters.mock_calendar_adapter import (
    MockCalendarAdapter,
    get_deterministic_event_id,
)
from src.shared_kernel.config import Settings
from src.shared_kernel.infrastructure.security.encryption import (
    decrypt_token,
    encrypt_token,
    ensure_calendar_encryption_key_valid,
    generate_fernet_key,
    validate_fernet_key,
)


# --- In-Memory Repository for Unit Testing ---
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


# ==============================================================================
# 1. FERNET ENCRYPTION & KEY VALIDATION TESTS
# ==============================================================================
def test_validate_fernet_key_valid_and_invalid() -> None:
    # 1. Valid generated key
    valid_key = generate_fernet_key()
    assert validate_fernet_key(valid_key) is True

    # 2. Invalid keys
    assert validate_fernet_key("") is False
    assert validate_fernet_key("not-base64-at-all!") is False
    # 16-byte base64 (too short for 32-byte Fernet key)
    short_b64 = base64.urlsafe_b64encode(b"0123456789abcdef").decode("utf-8")
    assert validate_fernet_key(short_b64) is False
    # 64-byte base64 (too long)
    long_b64 = base64.urlsafe_b64encode(b"a" * 64).decode("utf-8")
    assert validate_fernet_key(long_b64) is False


def test_encrypt_and_decrypt_token_roundtrip() -> None:
    key = generate_fernet_key()
    original_secret = "google_refresh_token_xyz_123456789"

    ciphertext = encrypt_token(original_secret, key=key)
    assert ciphertext != original_secret

    decrypted = decrypt_token(ciphertext, key=key)
    assert decrypted == original_secret

    # Decrypt with wrong key raises ValueError
    wrong_key = generate_fernet_key()
    with pytest.raises(ValueError, match="Ciphertext decryption failed"):
        decrypt_token(ciphertext, key=wrong_key)

    # Decrypt tampered ciphertext raises ValueError
    with pytest.raises(ValueError, match="Ciphertext decryption failed"):
        decrypt_token(ciphertext[:-5] + "AAAAA", key=key)


def test_fail_fast_calendar_encryption_key_validation() -> None:
    # When provider is 'google' and key is missing -> raises ValueError
    settings_invalid = Settings(
        calendar_provider="google",
        calendar_encryption_key="",
    )
    with pytest.raises(ValueError, match="CALENDAR_ENCRYPTION_KEY must be a valid 32-byte"):
        ensure_calendar_encryption_key_valid(settings_invalid)

    # When provider is 'google' and key is invalid base64
    settings_bad_key = Settings(
        calendar_provider="google",
        calendar_encryption_key="invalid_non_base64_string",
    )
    with pytest.raises(ValueError, match="CALENDAR_ENCRYPTION_KEY must be a valid 32-byte"):
        ensure_calendar_encryption_key_valid(settings_bad_key)

    # When provider is 'mock' -> does not raise even if key is empty
    settings_mock = Settings(
        calendar_provider="mock",
        calendar_encryption_key="",
    )
    ensure_calendar_encryption_key_valid(settings_mock)

    # When provider is 'google' and key is valid Fernet key -> does not raise
    valid_key = generate_fernet_key()
    settings_valid_google = Settings(
        calendar_provider="google",
        calendar_encryption_key=valid_key,
    )
    ensure_calendar_encryption_key_valid(settings_valid_google)


# ==============================================================================
# 2. MOCK CALENDAR ADAPTER TESTS
# ==============================================================================
@pytest.mark.asyncio
async def test_deterministic_event_id() -> None:
    block_id = UUID("0193132e-5a12-7000-8000-000000000001")
    event_id = get_deterministic_event_id(block_id)

    # Must match Google Calendar ID format: ^[a-v0-9]{5,1024}$
    assert event_id == f"ff{block_id.hex}"
    assert re.match(r"^[a-v0-9]{5,1024}$", event_id) is not None


@pytest.mark.asyncio
async def test_mock_calendar_crud_and_precondition() -> None:
    adapter = MockCalendarAdapter()
    block_id = uuid4()
    start_time = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    end_time = datetime(2026, 11, 10, 10, 30, tzinfo=UTC)

    event = CalendarEventDTO(
        id=get_deterministic_event_id(block_id),
        title="Deep Work: Algorithms",
        start_time=start_time,
        end_time=end_time,
        block_id=block_id,
    )

    # 1. Create event
    created = await adapter.create_event("fake_token", "primary", event)
    assert created.id == get_deterministic_event_id(block_id)
    assert created.etag is not None

    # 2. Duplicate create raises 409 Conflict
    with pytest.raises(CalendarConflictError):
        await adapter.create_event("fake_token", "primary", event)

    # 3. Update event with correct ETag
    created.title = "Deep Work: Advanced Algorithms"
    updated = await adapter.update_event("fake_token", "primary", created)
    assert updated.title == "Deep Work: Advanced Algorithms"

    # 4. Update event with mismatched ETag raises 412
    created.etag = '"mismatched_etag"'
    with pytest.raises(CalendarPreconditionFailedError):
        await adapter.update_event("fake_token", "primary", created)

    # 5. Delete event
    deleted = await adapter.delete_event("fake_token", "primary", created.id, etag=updated.etag)
    assert deleted is True

    # 6. Delete again returns False (not found)
    assert (
        await adapter.delete_event("fake_token", "primary", created.id, etag=updated.etag) is False
    )


@pytest.mark.asyncio
async def test_mock_calendar_freebusy_query() -> None:
    adapter = MockCalendarAdapter()
    base_time = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)

    # Insert 3 events
    # Event 1: 09:00 - 10:00 (inside range)
    # Event 2: 11:00 - 12:00 (cancelled - should be ignored)
    # Event 3: 14:00 - 15:30 (inside range)
    await adapter.create_event(
        "tok",
        "primary",
        CalendarEventDTO(
            id="ev1",
            title="Meeting 1",
            start_time=base_time + timedelta(hours=1),
            end_time=base_time + timedelta(hours=2),
        ),
    )
    await adapter.create_event(
        "tok",
        "primary",
        CalendarEventDTO(
            id="ev2",
            title="Cancelled Meeting",
            start_time=base_time + timedelta(hours=3),
            end_time=base_time + timedelta(hours=4),
            status="cancelled",
        ),
    )
    await adapter.create_event(
        "tok",
        "primary",
        CalendarEventDTO(
            id="ev3",
            title="Meeting 3",
            start_time=base_time + timedelta(hours=6),
            end_time=base_time + timedelta(hours=7, minutes=30),
        ),
    )

    query_min = base_time
    query_max = base_time + timedelta(hours=8)
    intervals = await adapter.get_free_busy_intervals("tok", ["primary"], query_min, query_max)

    assert len(intervals) == 2
    assert intervals[0].start_time == base_time + timedelta(hours=1)
    assert intervals[0].end_time == base_time + timedelta(hours=2)
    assert intervals[1].start_time == base_time + timedelta(hours=6)
    assert intervals[1].end_time == base_time + timedelta(hours=7, minutes=30)


@pytest.mark.asyncio
async def test_mock_calendar_pagination_loop() -> None:
    # Test pagination loop with page_size = 2
    adapter = MockCalendarAdapter(page_size=2)
    base_time = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)

    # Insert 5 events
    for i in range(5):
        await adapter.create_event(
            "tok",
            "primary",
            CalendarEventDTO(
                id=f"paged_ev_{i}",
                title=f"Event {i}",
                start_time=base_time + timedelta(hours=i),
                end_time=base_time + timedelta(hours=i, minutes=45),
            ),
        )

    # Page 1
    page1 = await adapter.list_events("tok", "primary")
    assert len(page1.events) == 2
    assert page1.next_page_token == "offset_2"
    assert page1.next_sync_token is None

    # Page 2
    page2 = await adapter.list_events("tok", "primary", page_token=page1.next_page_token)
    assert len(page2.events) == 2
    assert page2.next_page_token == "offset_4"
    assert page2.next_sync_token is None

    # Page 3 (Final page: 1 item remaining)
    page3 = await adapter.list_events("tok", "primary", page_token=page2.next_page_token)
    assert len(page3.events) == 1
    assert page3.next_page_token is None
    assert page3.next_sync_token is not None
    assert page3.next_sync_token.startswith("sync_token_5_")


@pytest.mark.asyncio
async def test_mock_calendar_fault_injections() -> None:
    adapter = MockCalendarAdapter()

    # Fault 429 Rate Limit
    adapter.inject_fault_429 = True
    with pytest.raises(CalendarRateLimitError):
        await adapter.create_secondary_calendar("tok")
    adapter.inject_fault_429 = False

    # Fault 410 Gone / Sync Token Expired
    adapter.inject_fault_410 = True
    result_410 = await adapter.list_events("tok", "primary", sync_token="expired_tok")
    assert result_410.sync_reset_needed is True
    assert len(result_410.events) == 0
    adapter.inject_fault_410 = False

    # Fault 409 Conflict
    adapter.inject_fault_409 = True
    with pytest.raises(CalendarConflictError):
        await adapter.create_event(
            "tok",
            "primary",
            CalendarEventDTO(
                id="ev",
                title="T",
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC) + timedelta(hours=1),
            ),
        )
    adapter.inject_fault_409 = False


# ==============================================================================
# 3. ACCOUNT CALENDAR USE CASES TESTS
# ==============================================================================
@pytest.mark.asyncio
async def test_initiate_google_calendar_auth_use_case() -> None:
    settings = Settings(
        google_client_id="test_client_id",
        google_redirect_uri="http://localhost:8000/callback",
    )
    use_case = InitiateGoogleCalendarAuthUseCase(settings=settings)
    user_id = uuid4()

    # 1. Inbound Freebusy flow
    resp_inbound = await use_case.execute(
        user_id, InitiateCalendarAuthRequestDTO(sync_type="inbound")
    )
    assert "test_client_id" in resp_inbound.authorization_url
    assert "calendar.calendarlist.readonly" in resp_inbound.authorization_url
    assert "calendar.app.created" not in resp_inbound.authorization_url

    # Verify state contains user_id and sync_type
    decoded_state = json.loads(
        base64.urlsafe_b64decode(resp_inbound.state.encode("utf-8")).decode("utf-8")
    )
    assert decoded_state["user_id"] == str(user_id)
    assert decoded_state["sync_type"] == "inbound"

    # 2. Two-way sync flow
    resp_two_way = await use_case.execute(
        user_id, InitiateCalendarAuthRequestDTO(sync_type="two_way")
    )
    assert "calendar.app.created" in resp_two_way.authorization_url


@pytest.mark.asyncio
async def test_handle_google_calendar_oauth_callback_use_case() -> None:
    key = generate_fernet_key()
    settings = Settings(
        calendar_provider="mock",
        calendar_encryption_key=key,
    )
    repo = InMemoryCalendarConnectionRepository()
    adapter = MockCalendarAdapter()
    use_case = HandleGoogleCalendarOAuthCallbackUseCase(
        repository=repo,
        calendar_provider=adapter,
        settings=settings,
    )

    user_id = uuid4()
    state_payload = {"user_id": str(user_id), "sync_type": "two_way"}
    state_str = base64.urlsafe_b64encode(json.dumps(state_payload).encode("utf-8")).decode("utf-8")

    request = CalendarOAuthCallbackRequestDTO(code="mock_auth_code", state=state_str)
    result = await use_case.execute(user_id, request)

    assert result.connected is True
    assert result.sync_status == "ACTIVE"
    assert result.external_calendar_id is not None
    assert result.external_calendar_id.startswith("ff_cal_")

    # Verify saved connection in repository
    saved_conn = await repo.get_by_user_id_and_provider(user_id, "GOOGLE")
    assert saved_conn is not None
    assert saved_conn.is_active is True
    # Verify token is encrypted and can be decrypted back
    decrypted_token = decrypt_token(saved_conn.oauth_refresh_token_encrypted, key=key)
    assert decrypted_token.startswith("mock_refresh_token_")


@pytest.mark.asyncio
async def test_get_calendar_connection_status_and_disconnect() -> None:
    key = generate_fernet_key()
    settings = Settings(
        calendar_provider="mock",
        calendar_encryption_key=key,
    )
    repo = InMemoryCalendarConnectionRepository()
    adapter = MockCalendarAdapter()

    user_id = uuid4()
    status_uc = GetCalendarConnectionStatusUseCase(repository=repo)
    disconnect_uc = DisconnectGoogleCalendarUseCase(
        repository=repo, calendar_provider=adapter, settings=settings
    )

    # 1. Status when no connection exists
    status_before = await status_uc.execute(user_id)
    assert status_before.connected is False
    assert status_before.sync_status == "REVOKED"

    # 2. Add active connection with a watch channel
    encrypted_token = encrypt_token("mock_token", key=key)
    conn = CalendarConnection(
        user_id=user_id,
        provider="GOOGLE",
        external_calendar_id="ff_cal_123",
        oauth_refresh_token_encrypted=encrypted_token,
        sync_status="ACTIVE",
        channel_id="chan_abc",
        resource_id="res_abc",
    )
    await repo.save(conn)

    status_active = await status_uc.execute(user_id)
    assert status_active.connected is True
    assert status_active.sync_status == "ACTIVE"
    assert status_active.external_calendar_id == "ff_cal_123"

    # 3. Disconnect connection
    disconnect_res = await disconnect_uc.execute(user_id)
    assert disconnect_res.connected is False
    assert disconnect_res.sync_status == "REVOKED"

    saved_conn = await repo.get_by_user_id_and_provider(user_id, "GOOGLE")
    assert saved_conn is not None
    assert saved_conn.sync_status == "REVOKED"
    assert saved_conn.channel_id is None
    assert saved_conn.resource_id is None


# ==============================================================================
# 4. TASK DELETION & SYNC INVARIANT MATRIX (COMPLETED TASKS PRESERVATION)
# ==============================================================================
def reconcile_external_deletion_to_focusflow(
    current_block_status: str,
    external_event_status: str,  # "cancelled" or "deleted"
) -> str:
    """Core domain business invariant: If FocusFlow task is COMPLETED, external deletion

    or cancellation must NEVER downgrade or wipe the completed progress.
    """
    if current_block_status == "COMPLETED":
        # Immutable completion: preserve COMPLETED status
        return "COMPLETED"

    if external_event_status in ("cancelled", "deleted"):
        if current_block_status == "PLANNED":
            return "CANCELLED"
        if current_block_status == "MISSED":
            return "MISSED"

    return current_block_status


def test_completed_task_deletion_matrix_invariant() -> None:
    # 1. COMPLETED status MUST NEVER be downgraded to CANCELLED or PLANNED
    assert (
        reconcile_external_deletion_to_focusflow("COMPLETED", external_event_status="cancelled")
        == "COMPLETED"
    )
    assert (
        reconcile_external_deletion_to_focusflow("COMPLETED", external_event_status="deleted")
        == "COMPLETED"
    )

    # 2. PLANNED status gets updated to CANCELLED when deleted externally
    assert (
        reconcile_external_deletion_to_focusflow("PLANNED", external_event_status="cancelled")
        == "CANCELLED"
    )
    assert (
        reconcile_external_deletion_to_focusflow("PLANNED", external_event_status="deleted")
        == "CANCELLED"
    )

    # 3. MISSED status remains MISSED (preserves audit trail of missed study)
    assert (
        reconcile_external_deletion_to_focusflow("MISSED", external_event_status="cancelled")
        == "MISSED"
    )
