"""Security regression tests for Billing Webhook Remediation (AUD-CRIT-02).

Covers:
1. Dedicated `payment_webhook_secret` (JWT `secret_key` rejected; unconfigured secret fails closed -> 503).
2. Strict business event, status (`PAID` only), amount, currency, transaction_ref, and ownership validation.
3. Timestamp freshness (`X-Webhook-Timestamp` within ±300s, Unix epoch & ISO8601) and signature binding.
4. Idempotency & concurrency under row-level locking (`SELECT ... FOR UPDATE`) — no double credit.
5. Mock vs. live boundary — `staging` and `production` cannot use `mock-confirm` or `local_mock` checkout.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete, select
from uuid6 import uuid7

from src.account.infrastructure.orm.user_orm import (
    AIQuotaORM,
    PaymentTransactionORM,
    UserORM,
)
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.main import app
from src.shared_kernel.config import Settings
from src.shared_kernel.infrastructure.database.session import async_session_factory

_JWT_SECRET = "jwt_signing_secret_must_never_verify_webhooks_1234567890abcdef12"
_WEBHOOK_SECRET = "dedicated_payment_webhook_hmac_secret_9876543210fedcba9876543210"


def _dev_settings(*, webhook_secret: str = _WEBHOOK_SECRET) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        debug=True,
        billing_release_mode="PAID_ENABLED",
        payment_provider="local_mock",
        secret_key=_JWT_SECRET,
        payment_webhook_secret=webhook_secret,
    )


def _sign_webhook(raw_body: bytes, timestamp: str, secret: str) -> str:
    signed_payload = f"{timestamp}.".encode() + raw_body
    return hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()


async def _seed_user_with_pending_txn(
    amount_vnd: int = 99_000,
) -> tuple[UUID, UUID, str]:
    user_id = uuid7()
    txn_id = uuid7()
    txn_ref = f"FF-PM-{txn_id.hex[:16].upper()}"
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"sec_billing_{user_id.hex}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="Security Billing Learner",
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier="FREE",
                is_locked=False,
            )
        )
        await session.flush()
        session.add(
            AIQuotaORM(
                id=uuid7(),
                user_id=user_id,
                monthly_limit=30,
                used_calls=0,
                reserved_calls=0,
                tokens_consumed=0,
                cycle_start=now,
                cycle_end=now + timedelta(days=30),
            )
        )
        session.add(
            PaymentTransactionORM(
                id=txn_id,
                user_id=user_id,
                transaction_ref=txn_ref,
                gateway_provider="MOCK",
                amount_vnd=amount_vnd,
                currency="VND",
                status="PENDING",
                qr_code_url="https://example.local/qr.png",
                webhook_signature_verified=False,
                paid_at=None,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    return user_id, txn_id, txn_ref


async def _cleanup_user(user_id: UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(
            delete(PaymentTransactionORM).where(PaymentTransactionORM.user_id == user_id)
        )
        await session.execute(delete(UserORM).where(UserORM.id == user_id))
        await session.commit()


async def _assert_unsettled(user_id: UUID, txn_id: UUID) -> None:
    async with async_session_factory() as session:
        user_row = (
            await session.execute(select(UserORM).where(UserORM.id == user_id))
        ).scalar_one()
        quota_row = (
            await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
        ).scalar_one()
        txn_row = (
            await session.execute(
                select(PaymentTransactionORM).where(PaymentTransactionORM.id == txn_id)
            )
        ).scalar_one()
        assert user_row.tier == "FREE"
        assert quota_row.monthly_limit == 30
        assert txn_row.status == "PENDING"
        assert txn_row.paid_at is None


def _build_valid_payload(
    *,
    txn_id: UUID,
    txn_ref: str,
    user_id: UUID,
    amount_vnd: int = 99_000,
    currency: str = "VND",
    status: str = "PAID",
    event_type: str = "payment.succeeded",
) -> dict[str, Any]:
    return {
        "event_id": f"evt_{uuid7().hex[:12]}",
        "event_type": event_type,
        "transaction_id": str(txn_id),
        "transaction_ref": txn_ref,
        "status": status,
        "amount_vnd": amount_vnd,
        "currency": currency,
        "user_id": str(user_id),
    }


@pytest.mark.asyncio
async def test_webhook_rejects_unconfigured_secret_and_jwt_secret_reuse() -> None:
    """Unconfigured payment_webhook_secret fails closed (503); JWT secret_key is rejected (401)."""
    user_id, txn_id, txn_ref = await _seed_user_with_pending_txn()
    try:
        payload_bytes = json.dumps(
            _build_valid_payload(txn_id=txn_id, txn_ref=txn_ref, user_id=user_id)
        ).encode("utf-8")
        ts = str(int(datetime.now(UTC).timestamp()))

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Empty payment_webhook_secret -> fail closed with 503
            empty_secret_settings = _dev_settings(webhook_secret="")
            with patch(
                "src.account.presentation.billing_router.get_settings",
                return_value=empty_secret_settings,
            ):
                resp = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": ts,
                        "X-Webhook-Signature": _sign_webhook(payload_bytes, ts, _JWT_SECRET),
                    },
                )
                assert resp.status_code == 503

            # 2. Signed with JWT secret_key instead of payment_webhook_secret -> 401
            configured_settings = _dev_settings(webhook_secret=_WEBHOOK_SECRET)
            with patch(
                "src.account.presentation.billing_router.get_settings",
                return_value=configured_settings,
            ):
                jwt_signed_resp = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": ts,
                        "X-Webhook-Signature": _sign_webhook(payload_bytes, ts, _JWT_SECRET),
                    },
                )
                assert jwt_signed_resp.status_code == 401

                # 3. Legacy signature without timestamp binding -> 401
                legacy_sig = hmac.new(
                    _WEBHOOK_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256
                ).hexdigest()
                legacy_resp = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": ts,
                        "X-Webhook-Signature": legacy_sig,
                    },
                )
                assert legacy_resp.status_code == 401

        await _assert_unsettled(user_id, txn_id)
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_status", ["FAILED", "PENDING", "CANCELLED", "REFUNDED", "UNKNOWN"])
async def test_webhook_rejects_non_paid_statuses_without_settling(bad_status: str) -> None:
    """Validly signed webhooks with non-PAID status MUST be rejected without upgrading user."""
    user_id, txn_id, txn_ref = await _seed_user_with_pending_txn()
    try:
        payload_bytes = json.dumps(
            _build_valid_payload(txn_id=txn_id, txn_ref=txn_ref, user_id=user_id, status=bad_status)
        ).encode("utf-8")
        ts = str(int(datetime.now(UTC).timestamp()))
        sig = _sign_webhook(payload_bytes, ts, _WEBHOOK_SECRET)

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch(
                "src.account.presentation.billing_router.get_settings",
                return_value=_dev_settings(),
            ):
                resp = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": ts,
                        "X-Webhook-Signature": sig,
                    },
                )
                assert resp.status_code == 422

        await _assert_unsettled(user_id, txn_id)
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_webhook_rejects_event_amount_currency_and_ownership_mismatches() -> None:
    """Reject unsupported event_type, underpaid/overpaid/missing amount, currency, ref, and user_id."""
    user_id, txn_id, txn_ref = await _seed_user_with_pending_txn(amount_vnd=99_000)
    other_user_id = uuid7()
    try:
        ts = str(int(datetime.now(UTC).timestamp()))
        base = _build_valid_payload(txn_id=txn_id, txn_ref=txn_ref, user_id=user_id)

        invalid_cases: list[tuple[dict[str, Any], int]] = [
            ({**base, "event_type": "payment.failed"}, 422),
            ({**base, "event_type": "payment.refunded"}, 422),
            ({**base, "amount_vnd": 1_000}, 422),  # underpaid
            ({**base, "amount_vnd": 990_000}, 422),  # overpaid
            ({**base, "amount_vnd": 0}, 422),  # zero
            ({k: v for k, v in base.items() if k != "amount_vnd"}, 400),  # missing amount
            ({**base, "currency": "USD"}, 422),  # wrong currency
            ({k: v for k, v in base.items() if k != "currency"}, 400),  # missing currency
            ({**base, "user_id": str(other_user_id)}, 422),  # ownership mismatch
            ({**base, "transaction_ref": "FF-PM-WRONGREF000000"}, 422),  # ref mismatch
        ]

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch(
                "src.account.presentation.billing_router.get_settings",
                return_value=_dev_settings(),
            ):
                for case_payload, expected_status in invalid_cases:
                    raw = json.dumps(case_payload).encode("utf-8")
                    sig = _sign_webhook(raw, ts, _WEBHOOK_SECRET)
                    resp = await client.post(
                        "/api/v1/account/billing/webhook",
                        content=raw,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Timestamp": ts,
                            "X-Webhook-Signature": sig,
                        },
                    )
                    assert resp.status_code == expected_status, (
                        f"Expected {expected_status} for {case_payload}, got {resp.status_code}: {resp.text}"
                    )

        await _assert_unsettled(user_id, txn_id)
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_webhook_timestamp_freshness_and_replay_tampering_protection() -> None:
    """Reject missing, malformed, stale (>300s), future (>300s), and timestamp-swapped replays."""
    user_id, txn_id, txn_ref = await _seed_user_with_pending_txn()
    try:
        raw = json.dumps(
            _build_valid_payload(txn_id=txn_id, txn_ref=txn_ref, user_id=user_id)
        ).encode("utf-8")
        now = datetime.now(UTC)
        stale_ts = str(int((now - timedelta(seconds=301)).timestamp()))
        future_ts = str(int((now + timedelta(seconds=301)).timestamp()))
        fresh_ts = str(int(now.timestamp()))
        naive_iso = now.replace(tzinfo=None).isoformat()

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch(
                "src.account.presentation.billing_router.get_settings",
                return_value=_dev_settings(),
            ):
                # Missing timestamp
                r_missing = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=raw,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": _sign_webhook(raw, fresh_ts, _WEBHOOK_SECRET),
                    },
                )
                assert r_missing.status_code == 401

                # Stale timestamp (> 5 minutes old)
                r_stale = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=raw,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": stale_ts,
                        "X-Webhook-Signature": _sign_webhook(raw, stale_ts, _WEBHOOK_SECRET),
                    },
                )
                assert r_stale.status_code == 401

                # Future timestamp (> 5 minutes ahead)
                r_future = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=raw,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": future_ts,
                        "X-Webhook-Signature": _sign_webhook(raw, future_ts, _WEBHOOK_SECRET),
                    },
                )
                assert r_future.status_code == 401

                # Naive ISO timestamp without timezone
                r_naive = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=raw,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": naive_iso,
                        "X-Webhook-Signature": _sign_webhook(raw, naive_iso, _WEBHOOK_SECRET),
                    },
                )
                assert r_naive.status_code == 401

                # Timestamp-swap replay attack: signature computed for stale_ts, sent with fresh_ts
                r_swap = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=raw,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": fresh_ts,
                        "X-Webhook-Signature": _sign_webhook(raw, stale_ts, _WEBHOOK_SECRET),
                    },
                )
                assert r_swap.status_code == 401

                await _assert_unsettled(user_id, txn_id)

                # Valid ISO8601 UTC timestamp + sha256= prefix succeeds cleanly
                iso_ts = now.isoformat().replace("+00:00", "Z")
                iso_sig = f"sha256={_sign_webhook(raw, iso_ts, _WEBHOOK_SECRET)}"
                r_ok = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=raw,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": iso_ts,
                        "X-Webhook-Signature": iso_sig,
                    },
                )
                assert r_ok.status_code == 200
                assert r_ok.json()["status"] == "PAID"
                assert r_ok.json()["already_processed"] is False
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_concurrent_webhook_deliveries_settle_exactly_once() -> None:
    """Concurrent valid webhook deliveries for the same transaction settle once without double credit."""
    user_id, txn_id, txn_ref = await _seed_user_with_pending_txn()
    try:
        raw = json.dumps(
            _build_valid_payload(txn_id=txn_id, txn_ref=txn_ref, user_id=user_id)
        ).encode("utf-8")
        ts = str(int(datetime.now(UTC).timestamp()))
        sig = _sign_webhook(raw, ts, _WEBHOOK_SECRET)
        req_headers = {
            "Content-Type": "application/json",
            "X-Webhook-Timestamp": ts,
            "X-Webhook-Signature": sig,
        }

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch(
                "src.account.presentation.billing_router.get_settings",
                return_value=_dev_settings(),
            ):
                responses = await asyncio.gather(
                    *[
                        client.post(
                            "/api/v1/account/billing/webhook",
                            content=raw,
                            headers=req_headers,
                        )
                        for _ in range(5)
                    ]
                )

        assert all(r.status_code == 200 for r in responses)
        bodies = [r.json() for r in responses]
        newly_processed = [b for b in bodies if b["already_processed"] is False]
        already_processed = [b for b in bodies if b["already_processed"] is True]
        assert len(newly_processed) == 1
        assert len(already_processed) == 4

        async with async_session_factory() as session:
            user_row = (
                await session.execute(select(UserORM).where(UserORM.id == user_id))
            ).scalar_one()
            quota_row = (
                await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
            ).scalar_one()
            txn_row = (
                await session.execute(
                    select(PaymentTransactionORM).where(PaymentTransactionORM.id == txn_id)
                )
            ).scalar_one()
            assert user_row.tier == "PREMIUM"
            assert quota_row.monthly_limit == 300
            assert txn_row.status == "PAID"
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("env_name", ["staging", "production"])
async def test_mock_confirm_and_mock_checkout_forbidden_in_staging_and_production(
    env_name: str,
) -> None:
    """Mock payment adapter and mock-confirm endpoint MUST fail closed in staging and production."""
    user_id, txn_id, _ = await _seed_user_with_pending_txn()
    token = JwtTokenProvider.create_access_token(
        user_id=user_id,
        email=f"sec_billing_{user_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    auth_headers = {"Authorization": f"Bearer {token}"}
    restricted_settings = Settings(
        _env_file=None,
        environment=env_name,
        debug=False,
        billing_release_mode="PAID_ENABLED",
        payment_provider="local_mock",
        secret_key=_JWT_SECRET,
        payment_webhook_secret=_WEBHOOK_SECRET,
        calendar_provider="local_mock",
    )

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with (
                patch(
                    "src.account.presentation.deps.get_settings",
                    return_value=restricted_settings,
                ),
                patch(
                    "src.account.presentation.billing_router.get_settings",
                    return_value=restricted_settings,
                ),
            ):
                config_resp = await client.get("/api/v1/account/billing/config")
                assert config_resp.status_code == 200
                config_data = config_resp.json()
                assert config_data["release_mode"] == "PAID_ENABLED"
                assert config_data["checkout_enabled"] is False
                assert config_data["mock_confirm_enabled"] is False
                assert config_data["provider"] == "none"

                checkout_resp = await client.post(
                    "/api/v1/account/billing/checkout",
                    json={"plan_code": "PREMIUM_MONTHLY"},
                    headers=auth_headers,
                )
                assert checkout_resp.status_code == 503
                assert "mock" in checkout_resp.json()["detail"].lower()

                confirm_resp = await client.post(
                    f"/api/v1/account/billing/mock-confirm/{txn_id}",
                    headers=auth_headers,
                )
                assert confirm_resp.status_code == 403
                assert "local_mock" in confirm_resp.json()["detail"].lower()

        await _assert_unsettled(user_id, txn_id)
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("env_name", ["staging", "production"])
@pytest.mark.parametrize("provider_name", ["sepay", "payos", "vnpay"])
async def test_paid_enabled_with_unimplemented_live_providers_fails_closed(
    env_name: str,
    provider_name: str,
) -> None:
    """PAID_ENABLED with unimplemented live providers MUST fail closed in staging/production."""
    user_id, txn_id, _ = await _seed_user_with_pending_txn()
    token = JwtTokenProvider.create_access_token(
        user_id=user_id,
        email=f"sec_billing_{user_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    auth_headers = {"Authorization": f"Bearer {token}"}
    unconfigured_live_settings = Settings(
        _env_file=None,
        environment=env_name,
        debug=False,
        billing_release_mode="PAID_ENABLED",
        payment_provider=provider_name,
        secret_key=_JWT_SECRET,
        payment_webhook_secret=_WEBHOOK_SECRET,
        calendar_provider="local_mock",
    )

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with (
                patch(
                    "src.account.presentation.deps.get_settings",
                    return_value=unconfigured_live_settings,
                ),
                patch(
                    "src.account.presentation.billing_router.get_settings",
                    return_value=unconfigured_live_settings,
                ),
            ):
                config_resp = await client.get("/api/v1/account/billing/config")
                assert config_resp.status_code == 200
                config_data = config_resp.json()
                assert config_data["release_mode"] == "PAID_ENABLED"
                assert config_data["checkout_enabled"] is False
                assert config_data["mock_confirm_enabled"] is False
                assert config_data["provider"] == "none"

                checkout_resp = await client.post(
                    "/api/v1/account/billing/checkout",
                    json={"plan_code": "PREMIUM_MONTHLY"},
                    headers=auth_headers,
                )
                assert checkout_resp.status_code == 503

                confirm_resp = await client.post(
                    f"/api/v1/account/billing/mock-confirm/{txn_id}",
                    headers=auth_headers,
                )
                assert confirm_resp.status_code == 403

        await _assert_unsettled(user_id, txn_id)
    finally:
        await _cleanup_user(user_id)
