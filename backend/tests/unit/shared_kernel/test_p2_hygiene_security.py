"""Unit tests for P2 Backend Security & Reliability Hygiene (AUD-MED-01..08, AUD-LOW-01..03)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

import src.main as main_mod
from src.account.application.dtos.auth import RequestPasswordResetOtpCommand
from src.account.application.dtos.calendar import CalendarOAuthCallbackRequestDTO
from src.account.application.use_cases.auth.password_reset_otp_use_case import (
    RequestPasswordResetOtpUseCase,
)
from src.account.application.use_cases.calendar.handle_google_calendar_oauth_callback_use_case import (
    HandleGoogleCalendarOAuthCallbackUseCase,
)
from src.account.domain.exceptions.auth_exceptions import RateLimitError
from src.account.domain.models.calendar_connection import CalendarConnection
from src.account.domain.ports.calendar_provider_port import (
    CalendarAuthError,
    CalendarProviderError,
)
from src.account.domain.services.oauth_state import create_signed_oauth_state
from src.account.infrastructure.caching.otp_repository import OtpRepository
from src.account.infrastructure.email.email_service import EmailService, mask_email
from src.account.presentation.calendar_router import handle_google_calendar_callback_get
from src.account.presentation.webhook_router import handle_google_calendar_webhook
from src.shared_kernel.config import Settings
from src.shared_kernel.infrastructure.security.encryption import generate_fernet_key
from src.shared_kernel.infrastructure.sse.job_store import (
    InMemorySseJobStore,
    RedisSseJobStore,
)
from src.shared_kernel.logging import redact_pii_processor

# ---------------------------------------------------------------------------
# AUD-MED-01: Password Reset Account Enumeration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aud_med_01_password_reset_identical_message_and_uniform_cooldown() -> None:
    """Existing and non-existing emails get identical message and identical 60s cooldown."""
    expected_msg = (
        "Nếu email tồn tại trong hệ thống, mã xác thực OTP đã được gửi đến hòm thư của bạn."
    )
    cooldowns: dict[str, int] = {}

    class StubOtpRepo:
        def generate_otp(self) -> str:
            return "123456"

        def hash_otp(self, otp_code: str) -> str:
            return otp_code

        async def get_cooldown_remaining(self, purpose: str, identifier: str) -> int | None:
            return cooldowns.get(f"{purpose}:{identifier}")

        async def set_cooldown(self, purpose: str, identifier: str) -> None:
            cooldowns[f"{purpose}:{identifier}"] = 60

        async def get_raw_session(self, purpose: str, identifier: str) -> dict[str, Any] | None:
            return None

        async def save_otp(
            self,
            purpose: str,
            identifier: str,
            otp_code: str,
            payload: dict[str, Any] | None = None,
        ) -> None:
            del otp_code, payload
            cooldowns[f"{purpose}:{identifier}"] = 60

        async def verify_and_consume_otp(
            self, purpose: str, identifier: str, user_otp: str
        ) -> tuple[bool, str, dict[str, Any]]:
            return False, "", {}

        async def save_reset_token(self, token: str, email: str, ttl_seconds: int = 600) -> None:
            return None

        async def consume_reset_token(self, token: str) -> str | None:
            return None

    existing_user = SimpleNamespace(id=uuid4(), email="exists@example.com")
    user_repo = AsyncMock()
    user_repo.find_by_email.side_effect = lambda email: (
        existing_user if email == "exists@example.com" else None
    )
    email_service = AsyncMock()
    otp_repo = StubOtpRepo()

    uc = RequestPasswordResetOtpUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
        email_service=email_service,
    )

    msg_existing = await uc.execute(RequestPasswordResetOtpCommand(email="exists@example.com"))
    msg_missing = await uc.execute(RequestPasswordResetOtpCommand(email="missing@example.com"))

    assert msg_existing == expected_msg
    assert msg_missing == expected_msg
    # Email only sent for existing account
    email_service.send_otp_email.assert_awaited_once_with(
        "exists@example.com", "123456", "reset_password"
    )

    # Second call for BOTH existing and non-existing raises RateLimitError BEFORE user lookup
    user_repo.find_by_email.reset_mock()
    with pytest.raises(RateLimitError):
        await uc.execute(RequestPasswordResetOtpCommand(email="exists@example.com"))
    with pytest.raises(RateLimitError):
        await uc.execute(RequestPasswordResetOtpCommand(email="missing@example.com"))
    user_repo.find_by_email.assert_not_awaited()


# ---------------------------------------------------------------------------
# AUD-MED-02: Atomic OTP Verification (Lua) & Reset Token Consumption (GETDEL)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aud_med_02_consume_reset_token_uses_atomic_getdel() -> None:
    """consume_reset_token must use atomic GETDEL instead of non-atomic GET+DELETE."""
    fake_redis = AsyncMock()
    fake_redis.getdel.return_value = "learner@example.com"

    with patch(
        "src.account.infrastructure.caching.otp_repository.get_redis_client",
        return_value=fake_redis,
    ):
        result = await OtpRepository.consume_reset_token("tok_123")

    assert result == "learner@example.com"
    fake_redis.getdel.assert_awaited_once_with("password_reset_token:tok_123")
    fake_redis.get.assert_not_awaited()
    fake_redis.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_aud_med_02_verify_and_consume_otp_uses_atomic_lua_script() -> None:
    """verify_and_consume_otp executes a single atomic Lua eval without separate GET/SET/DEL."""
    stored_payload = {"full_name": "Test User"}
    stored_raw = json.dumps(
        {
            "otp_hash": OtpRepository.hash_otp("654321"),
            "attempts": 0,
            "payload": stored_payload,
        }
    )

    fake_redis = AsyncMock()
    fake_redis.eval.side_effect = [
        ["INVALID", "2", ""],
        ["OK", "0", stored_raw],
        ["EXPIRED", "0", ""],
        ["MAX_ATTEMPTS", "0", ""],
    ]

    with patch(
        "src.account.infrastructure.caching.otp_repository.get_redis_client",
        return_value=fake_redis,
    ):
        ok1, msg1, payload1 = await OtpRepository.verify_and_consume_otp(
            "register", "User@Example.com", "000000"
        )
        ok2, msg2, payload2 = await OtpRepository.verify_and_consume_otp(
            "register", "User@Example.com", "654321"
        )
        ok3, msg3, payload3 = await OtpRepository.verify_and_consume_otp(
            "register", "User@Example.com", "654321"
        )
        ok4, msg4, payload4 = await OtpRepository.verify_and_consume_otp(
            "register", "User@Example.com", "111111"
        )

    assert (ok1, payload1) == (False, {})
    assert "còn 2 lần thử" in msg1

    assert (ok2, msg2, payload2) == (True, "Xác thực thành công.", stored_payload)
    assert (ok3, payload3) == (False, {})
    assert "hết hạn" in msg3

    assert (ok4, payload4) == (False, {})
    assert "quá số lần" in msg4

    assert fake_redis.eval.await_count == 4
    fake_redis.get.assert_not_awaited()
    fake_redis.set.assert_not_awaited()
    fake_redis.delete.assert_not_awaited()


# ---------------------------------------------------------------------------
# AUD-MED-04: /api/health Hardening & Real DB/Redis Checks
# ---------------------------------------------------------------------------


def test_aud_med_04_health_returns_503_when_redis_fails_and_hides_internals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_mod, "check_database_health", AsyncMock(return_value=True))
    monkeypatch.setattr(main_mod, "check_redis_health", AsyncMock(return_value=False))
    probe_spy = AsyncMock()
    monkeypatch.setattr(main_mod, "probe_cobhub_capabilities", probe_spy)

    client = TestClient(main_mod.create_app())
    resp = client.get("/api/health?probe_ai=true")
    assert resp.status_code == 503
    assert resp.json() == {
        "status": "degraded",
        "database": "ok",
        "redis": "error",
    }
    probe_spy.assert_not_awaited()


# ---------------------------------------------------------------------------
# AUD-MED-05: Google Calendar Webhook Fail-Closed on Null Token Hash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aud_med_05_webhook_fails_closed_when_channel_token_hash_is_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.account.presentation.webhook_router.enforce_rate_limit",
        AsyncMock(return_value=None),
    )
    conn = CalendarConnection(
        user_id=uuid4(),
        provider="GOOGLE",
        external_calendar_id="primary",
        oauth_refresh_token_encrypted="enc",
        sync_status="ACTIVE",
        channel_id="chan-null-token",
        resource_id="res-123",
        channel_token_hash=None,
    )
    repo = AsyncMock()
    repo.get_by_channel_id.return_value = conn
    req = Request({"type": "http", "method": "POST", "headers": []})

    with pytest.raises(HTTPException) as exc_info:
        await handle_google_calendar_webhook(
            request=req,
            x_goog_channel_id="chan-null-token",
            x_goog_resource_id="res-123",
            x_goog_channel_token="any-token",
            x_goog_resource_state="exists",
            repository=repo,
        )

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# AUD-MED-06: Recursive PII/Secret Redaction & Email Masking
# ---------------------------------------------------------------------------


def test_aud_med_06_recursive_pii_redaction_nested_dicts_and_lists() -> None:
    event: dict[str, Any] = {
        "event": "auth_debug",
        "email": "top@example.com",
        "nested": {
            "to_email": "nested@example.com",
            "otp_code": "123456",
            "headers": {
                "Authorization": "Bearer secret-jwt",
                "Cookie": "access_token=abc",
            },
            "secrets": [
                {"fernet_key": "k1", "calendar_encryption_key": "k2"},
                {"google_client_secret": "gsec", "payment_webhook_secret": "psec"},
                {"safe_field": "visible"},
            ],
        },
        "safe_top": "ok",
    }

    redacted = redact_pii_processor(None, "info", event)

    assert redacted["email"] == "[REDACTED]"
    assert redacted["safe_top"] == "ok"
    assert redacted["nested"]["to_email"] == "[REDACTED]"
    assert redacted["nested"]["otp_code"] == "[REDACTED]"
    assert redacted["nested"]["headers"]["Authorization"] == "[REDACTED]"
    assert redacted["nested"]["headers"]["Cookie"] == "[REDACTED]"
    assert redacted["nested"]["secrets"][0]["fernet_key"] == "[REDACTED]"
    assert redacted["nested"]["secrets"][0]["calendar_encryption_key"] == "[REDACTED]"
    assert redacted["nested"]["secrets"][1]["google_client_secret"] == "[REDACTED]"
    assert redacted["nested"]["secrets"][1]["payment_webhook_secret"] == "[REDACTED]"
    assert redacted["nested"]["secrets"][2]["safe_field"] == "visible"


@pytest.mark.asyncio
async def test_aud_med_06_email_service_masks_recipient_email_in_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert mask_email("learner@example.com") == "l***@example.com"
    assert mask_email("a@b.vn") == "a***@b.vn"
    assert mask_email("invalid-email") == "***"

    fake_settings = SimpleNamespace(
        email_backend="smtp",
        environment="production",
        email_from="FocusFlow <no-reply@focusflow.local>",
        email_host="smtp.example.com",
        email_port=587,
        email_user="mailer",
        email_pass="secret",
        otp_ttl_seconds=300,
        otp_max_attempts=3,
    )
    raw_email = "sensitive.student@university.edu"

    with (
        caplog.at_level(logging.INFO, logger="focusflow.email"),
        patch(
            "src.account.infrastructure.email.email_service.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "src.account.infrastructure.email.email_service.aiosmtplib.send",
            new=AsyncMock(return_value=({}, "250 OK")),
        ),
    ):
        await EmailService.send_otp_email(raw_email, "999888", "register")
        await EmailService.send_overdue_alert_email(raw_email, ["Task 1"], 2)

    assert raw_email not in caplog.text
    assert "s***@university.edu" in caplog.text

    caplog.clear()
    with (
        caplog.at_level(logging.ERROR, logger="focusflow.email"),
        patch(
            "src.account.infrastructure.email.email_service.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "src.account.infrastructure.email.email_service.aiosmtplib.send",
            new=AsyncMock(side_effect=RuntimeError("SMTP timeout")),
        ),
        pytest.raises(RuntimeError),
    ):
        await EmailService.send_otp_email(raw_email, "999888", "reset_password")

    assert raw_email not in caplog.text
    assert "s***@university.edu" in caplog.text


# ---------------------------------------------------------------------------
# AUD-MED-08: SSE Job Store Memory Leak Prevention & TTL Eviction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aud_med_08_redis_store_does_not_mirror_to_fallback_when_healthy() -> None:
    """Healthy Redis writes must NOT populate InMemorySseJobStore; only failures fall back."""
    fallback = InMemorySseJobStore()
    store = RedisSseJobStore(redis_url="redis://localhost:6379/0", fallback_store=fallback)

    healthy_client = AsyncMock()
    healthy_client.set.return_value = True
    store._client = healthy_client

    job_id = uuid4()
    user_id = uuid4()
    await store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=uuid4(),
        reservation_id=uuid4(),
        job_type="PLAN",
        operation="GENERATE",
        idempotency_key="idem-healthy",
    )

    assert job_id not in fallback._jobs
    assert len(fallback._idempotency_map) == 0
    assert healthy_client.set.await_count == 2

    # Now simulate Redis failure -> MUST fall back to in-memory store
    failing_client = AsyncMock()
    failing_client.set.side_effect = ConnectionError("Redis down")
    store._client = failing_client
    store._redis_retry_after = 0.0

    fallback_job_id = uuid4()
    await store.create_job(
        job_id=fallback_job_id,
        user_id=user_id,
        roadmap_id=uuid4(),
        reservation_id=uuid4(),
        job_type="PLAN",
        operation="GENERATE",
        idempotency_key="idem-fallback",
    )
    assert fallback_job_id in fallback._jobs


@pytest.mark.asyncio
async def test_aud_med_08_in_memory_store_evicts_expired_jobs_conditions_and_idempotency() -> None:
    store = InMemorySseJobStore(eviction_interval_seconds=0.0)
    job_id = uuid4()
    user_id = uuid4()

    await store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=uuid4(),
        reservation_id=uuid4(),
        job_type="PLAN",
        operation="GENERATE",
        idempotency_key="idem-expire",
        ttl_seconds=10,
    )
    store._get_condition(job_id)
    assert job_id in store._jobs
    assert job_id in store._condition_map
    assert len(store._idempotency_map) == 1

    future = datetime.now(UTC) + timedelta(seconds=20)
    evicted = store.evict_expired(now=future, force=True)
    assert evicted >= 2
    assert job_id not in store._jobs
    assert job_id not in store._condition_map
    assert len(store._idempotency_map) == 0


# ---------------------------------------------------------------------------
# AUD-LOW-01: Config Validation for Calendar Encryption Key
# ---------------------------------------------------------------------------


def test_aud_low_01_invalid_fernet_key_rejected_in_production() -> None:
    with pytest.raises(ValueError, match="CALENDAR_ENCRYPTION_KEY"):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            secret_key="prod-secret-key-not-default",
            calendar_provider="google",
            calendar_encryption_key="not-a-valid-fernet-key",
        )


# ---------------------------------------------------------------------------
# AUD-LOW-02: Calendar OAuth GET Callback Does Not Leak Raw Exception Text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc", "expected_code"),
    [
        (CalendarAuthError("SECRET_INTERNAL_TOKEN=xyz leaked"), "oauth_auth_failed"),
        (CalendarProviderError("Raw Google upstream 500 trace"), "calendar_provider_error"),
        (RuntimeError("Database password=supersecret"), "calendar_connection_failed"),
    ],
)
async def test_aud_low_02_calendar_callback_get_uses_generic_error_code(
    exc: Exception,
    expected_code: str,
) -> None:
    use_case = AsyncMock()
    use_case.execute.side_effect = exc
    req = Request({"type": "http", "method": "GET", "headers": []})

    response = await handle_google_calendar_callback_get(
        request=req,
        code="auth-code",
        state="invalid-state",
        user_id=uuid4(),
        use_case=use_case,
    )

    assert response.status_code == 302
    location = response.headers["location"]
    assert f"calendar_connected=error&error_detail={expected_code}" in location
    assert "SECRET_INTERNAL_TOKEN" not in location
    assert "supersecret" not in location
    assert "Raw Google upstream" not in location


# ---------------------------------------------------------------------------
# AUD-LOW-03: OAuth Callback Use Case Closes Ephemeral httpx.AsyncClient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aud_low_03_oauth_callback_closes_ephemeral_httpx_client() -> None:
    settings = Settings(
        _env_file=None,
        calendar_provider="google",
        google_client_id="cid",
        google_client_secret="csec",
        calendar_encryption_key=generate_fernet_key(),
        google_redirect_uri="http://localhost:8000/callback",
        secret_key="test-secret-key-for-oauth-state-hmac-32bytes",
    )
    user_id = uuid4()
    nonce = "nonce-close-test"
    signed_state = create_signed_oauth_state(
        user_id=user_id,
        sync_type="one_way",
        redirect_uri=settings.google_redirect_uri,
        return_to="/settings",
        nonce=nonce,
        secret_key=settings.secret_key,
        now=datetime.now(UTC),
    )

    state_store = AsyncMock()
    state_store.consume_nonce.return_value = user_id

    repo = AsyncMock()
    repo.get_by_user_id_and_provider.return_value = None
    repo.save.side_effect = lambda conn: conn

    provider = AsyncMock()

    entered = False
    exited = False

    class TrackingAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs

        async def __aenter__(self) -> TrackingAsyncClient:
            nonlocal entered
            entered = True
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            nonlocal exited
            exited = True

        async def post(self, url: str, data: dict[str, Any]) -> MagicMock:
            del url, data
            resp = MagicMock(spec=httpx.Response)
            resp.is_error = False
            resp.json.return_value = {
                "access_token": "ya29.test",
                "refresh_token": "refresh_tok_123",
            }
            return resp

    use_case = HandleGoogleCalendarOAuthCallbackUseCase(
        repository=repo,
        calendar_provider=provider,
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
        http_client=None,
    )

    with patch(
        "src.account.application.use_cases.calendar."
        "handle_google_calendar_oauth_callback_use_case.httpx.AsyncClient",
        TrackingAsyncClient,
    ):
        result = await use_case.execute(
            user_id=user_id,
            request=CalendarOAuthCallbackRequestDTO(code="code123", state=signed_state),
        )

    assert result.connected is True
    assert entered is True
    assert exited is True
