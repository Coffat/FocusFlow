from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
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


async def _seed_billing_user() -> UUID:
    user_id = uuid7()
    now = datetime.now(UTC)
    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"billing_{user_id.hex}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="Billing Learner",
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
        await session.commit()
    return user_id


async def _cleanup_billing_user(user_id: UUID) -> None:
    async with async_session_factory() as session:
        # payment_transactions.user_id is ON DELETE RESTRICT -> delete transactions first
        await session.execute(
            delete(PaymentTransactionORM).where(PaymentTransactionORM.user_id == user_id)
        )
        await session.execute(delete(UserORM).where(UserORM.id == user_id))
        await session.commit()


def _sign_body(raw_body: bytes, timestamp: str, webhook_secret: str) -> str:
    signed_payload = f"{timestamp}.".encode() + raw_body
    return hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_billing_checkout_reuse_hmac_webhook_idempotency_and_prod_guard() -> None:
    user_id = await _seed_billing_user()
    token = JwtTokenProvider.create_access_token(
        user_id=user_id,
        email=f"billing_{user_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    headers = {"Authorization": f"Bearer {token}"}

    dev_mock_settings = Settings(
        _env_file=None,
        environment="test",
        debug=True,
        billing_release_mode="PAID_ENABLED",
        payment_provider="local_mock",
        secret_key="test_jwt_secret_key_64_chars_long_1234567890abcdef1234567890abcd",
        payment_webhook_secret="test_dedicated_billing_webhook_secret_64_chars_0987654321fedcba",
    )
    prod_mock_settings = Settings(
        _env_file=None,
        environment="production",
        debug=False,
        billing_release_mode="PAID_ENABLED",
        payment_provider="local_mock",
        secret_key="prod_non_default_secret_key_64_chars_long_1234567890abcdef123456",
        payment_webhook_secret="prod_dedicated_billing_webhook_secret_64_chars_0987654321fedcba",
        calendar_provider="local_mock",
    )

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Production guard: local_mock in production MUST fail closed (503 checkout, 403 mock-confirm)
            with (
                patch(
                    "src.account.presentation.deps.get_settings", return_value=prod_mock_settings
                ),
                patch(
                    "src.account.presentation.billing_router.get_settings",
                    return_value=prod_mock_settings,
                ),
            ):
                prod_checkout = await client.post(
                    "/api/v1/account/billing/checkout",
                    json={"plan_code": "PREMIUM_MONTHLY"},
                    headers=headers,
                )
                assert prod_checkout.status_code == 503

                prod_confirm = await client.post(
                    f"/api/v1/account/billing/mock-confirm/{uuid7()}",
                    headers=headers,
                )
                assert prod_confirm.status_code == 403

            # 2. Dev/test local_mock checkout -> creates PENDING and reuses within 15m TTL
            with (
                patch("src.account.presentation.deps.get_settings", return_value=dev_mock_settings),
                patch(
                    "src.account.presentation.billing_router.get_settings",
                    return_value=dev_mock_settings,
                ),
            ):
                c1 = await client.post(
                    "/api/v1/account/billing/checkout",
                    json={"plan_code": "PREMIUM_MONTHLY"},
                    headers=headers,
                )
                assert c1.status_code == 200
                c1_data = c1.json()
                assert c1_data["status"] == "PENDING"
                assert c1_data["amount_vnd"] == 99000
                assert c1_data["provider"] == "MOCK"
                assert c1_data["is_mock_provider"] is True
                txn_id = c1_data["transaction_id"]
                assert c1_data["checkout_url"] == f"http://localhost:3000/pricing?mock_tx={txn_id}"

                # Second checkout for same plan within 15m TTL reuses the same PENDING txn
                c2 = await client.post(
                    "/api/v1/account/billing/checkout",
                    json={"plan_code": "PREMIUM_MONTHLY"},
                    headers=headers,
                )
                assert c2.status_code == 200
                assert c2.json()["transaction_id"] == txn_id

                # Transactions list shows 1 PENDING transaction
                txns_resp = await client.get(
                    "/api/v1/account/billing/transactions", headers=headers
                )
                assert txns_resp.status_code == 200
                txns = txns_resp.json()
                assert len(txns) == 1
                assert txns[0]["id"] == txn_id
                assert txns[0]["status"] == "PENDING"

                # 3. Webhook missing/invalid HMAC signature -> 401
                now_ts = str(int(datetime.now(UTC).timestamp()))
                webhook_payload = json.dumps(
                    {
                        "event_type": "payment.succeeded",
                        "transaction_id": txn_id,
                        "transaction_ref": c1_data["transaction_ref"],
                        "status": "PAID",
                        "amount_vnd": 99000,
                        "currency": "VND",
                        "user_id": str(user_id),
                    }
                ).encode("utf-8")

                no_sig = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=webhook_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": now_ts,
                    },
                )
                assert no_sig.status_code == 401

                bad_sig = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=webhook_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": now_ts,
                        "X-Webhook-Signature": "deadbeef" * 8,
                    },
                )
                assert bad_sig.status_code == 401

                # 4. Valid HMAC webhook -> PAID + User.tier=PREMIUM + AIQuota.monthly_limit=300
                valid_sig = _sign_body(
                    webhook_payload, now_ts, dev_mock_settings.payment_webhook_secret
                )
                ok_webhook = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=webhook_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": now_ts,
                        "X-Webhook-Signature": valid_sig,
                    },
                )
                assert ok_webhook.status_code == 200
                ok_data = ok_webhook.json()
                assert ok_data["status"] == "PAID"
                assert ok_data["transaction_id"] == txn_id
                assert ok_data["already_processed"] is False

                async with async_session_factory() as session:
                    user_row = (
                        await session.execute(select(UserORM).where(UserORM.id == user_id))
                    ).scalar_one()
                    quota_row = (
                        await session.execute(
                            select(AIQuotaORM).where(AIQuotaORM.user_id == user_id)
                        )
                    ).scalar_one()
                    txn_row = (
                        await session.execute(
                            select(PaymentTransactionORM).where(
                                PaymentTransactionORM.id == UUID(txn_id)
                            )
                        )
                    ).scalar_one()
                    assert user_row.tier == "PREMIUM"
                    assert quota_row.monthly_limit == 300
                    assert txn_row.status == "PAID"
                    assert txn_row.paid_at is not None
                    assert txn_row.webhook_signature_verified is True

                # 5. Replayed webhook -> idempotent 200 with already_processed=True
                replay_webhook = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=webhook_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": now_ts,
                        "X-Webhook-Signature": valid_sig,
                    },
                )
                assert replay_webhook.status_code == 200
                assert replay_webhook.json()["already_processed"] is True
                assert replay_webhook.json()["status"] == "PAID"

                # 6. Yearly checkout + mock-confirm works in dev/test
                yearly = await client.post(
                    "/api/v1/account/billing/checkout",
                    json={"plan_code": "PREMIUM_YEARLY"},
                    headers=headers,
                )
                assert yearly.status_code == 200
                yearly_id = yearly.json()["transaction_id"]
                assert yearly.json()["amount_vnd"] == 990000

                confirm_resp = await client.post(
                    f"/api/v1/account/billing/mock-confirm/{yearly_id}",
                    headers=headers,
                )
                assert confirm_resp.status_code == 200
                assert confirm_resp.json()["status"] == "PAID"
                assert confirm_resp.json()["already_processed"] is False
    finally:
        await _cleanup_billing_user(user_id)


@pytest.mark.asyncio
async def test_billing_config_public_endpoint_and_free_beta_gating() -> None:
    """GET /billing/config is public & server-owned; FREE_BETA fails closed across all environments."""
    user_id = await _seed_billing_user()
    token = JwtTokenProvider.create_access_token(
        user_id=user_id,
        email=f"billing_{user_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    auth_headers = {"Authorization": f"Bearer {token}"}

    free_beta_dev_settings = Settings(
        _env_file=None,
        environment="test",
        debug=True,
        billing_release_mode="FREE_BETA",
        payment_provider="local_mock",
        secret_key="test_jwt_secret_key_64_chars_long_1234567890abcdef1234567890abcd",
    )
    paid_mock_dev_settings = Settings(
        _env_file=None,
        environment="test",
        debug=True,
        billing_release_mode="PAID_ENABLED",
        payment_provider="local_mock",
        secret_key="test_jwt_secret_key_64_chars_long_1234567890abcdef1234567890abcd",
    )

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. FREE_BETA: public /config returns disabled checkout + authoritative plans
            with (
                patch(
                    "src.account.presentation.deps.get_settings",
                    return_value=free_beta_dev_settings,
                ),
                patch(
                    "src.account.presentation.billing_router.get_settings",
                    return_value=free_beta_dev_settings,
                ),
            ):
                # Unauthenticated call must succeed (public pricing page)
                cfg_resp = await client.get("/api/v1/account/billing/config")
                assert cfg_resp.status_code == 200
                cfg = cfg_resp.json()
                assert cfg["release_mode"] == "FREE_BETA"
                assert cfg["checkout_enabled"] is False
                assert cfg["mock_confirm_enabled"] is False
                assert cfg["provider"] == "none"
                assert "Free Beta" in cfg["status_message"]

                plans_by_code = {p["plan_code"]: p for p in cfg["plans"]}
                assert set(plans_by_code.keys()) == {"PREMIUM_MONTHLY", "PREMIUM_YEARLY"}
                assert plans_by_code["PREMIUM_MONTHLY"]["amount_vnd"] == 99_000
                assert plans_by_code["PREMIUM_MONTHLY"]["currency"] == "VND"
                assert plans_by_code["PREMIUM_MONTHLY"]["ai_monthly_limit"] == 300
                assert plans_by_code["PREMIUM_MONTHLY"]["max_active_roadmaps"] == 15
                assert plans_by_code["PREMIUM_YEARLY"]["amount_vnd"] == 990_000
                assert plans_by_code["PREMIUM_YEARLY"]["currency"] == "VND"
                assert plans_by_code["PREMIUM_YEARLY"]["ai_monthly_limit"] == 300
                assert plans_by_code["PREMIUM_YEARLY"]["max_active_roadmaps"] == 15

                # FREE_BETA enforces 503 on checkout and 403 on mock-confirm even in test env
                checkout_resp = await client.post(
                    "/api/v1/account/billing/checkout",
                    json={"plan_code": "PREMIUM_MONTHLY"},
                    headers=auth_headers,
                )
                assert checkout_resp.status_code == 503
                assert "BILLING_FREE_BETA_DISABLED" in checkout_resp.json()["detail"]

                confirm_resp = await client.post(
                    f"/api/v1/account/billing/mock-confirm/{uuid7()}",
                    headers=auth_headers,
                )
                assert confirm_resp.status_code == 403

            # 2. PAID_ENABLED + local_mock in isolated test env exposes mock capabilities
            with patch(
                "src.account.presentation.billing_router.get_settings",
                return_value=paid_mock_dev_settings,
            ):
                paid_cfg_resp = await client.get("/api/v1/account/billing/config")
                assert paid_cfg_resp.status_code == 200
                paid_cfg = paid_cfg_resp.json()
                assert paid_cfg["release_mode"] == "PAID_ENABLED"
                assert paid_cfg["checkout_enabled"] is True
                assert paid_cfg["mock_confirm_enabled"] is True
                assert paid_cfg["provider"] == "local_mock"
    finally:
        await _cleanup_billing_user(user_id)
