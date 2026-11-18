import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from uuid6 import uuid7

from src.account.domain.services.ai_cost_accounting_service import ONE_MILLION_TOKENS
from src.account.infrastructure.adapters.quota_facade_adapter import (
    CostAccountingResult,
    QuotaFacadeAdapter,
    calculate_cost_accounting,
    calculate_estimated_cost_usd,
    resolve_canonical_gateway_model,
)
from src.account.infrastructure.orm.user_orm import (
    AIQuotaORM,
    AIQuotaReservationORM,
    AIUsageLogORM,
    UserORM,
)
from src.shared_kernel.infrastructure.database.session import async_session_factory


class MockDbQueryResult:
    def __init__(self, item: Any) -> None:
        self._item = item

    def scalar_one_or_none(self) -> Any | None:
        return self._item

    def scalar_one(self) -> Any:
        return self._item


class MockQuotaAsyncSession:
    def __init__(self, reservation: AIQuotaReservationORM, quota: AIQuotaORM) -> None:
        self.reservation = reservation
        self.quota = quota
        self.added: list[Any] = []

    def add(self, item: Any) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        pass

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> MockDbQueryResult:
        stmt_str = str(stmt).upper()
        if "AI_QUOTA_RESERVATIONS" in stmt_str:
            return MockDbQueryResult(self.reservation)
        if "AI_QUOTAS" in stmt_str:
            return MockDbQueryResult(self.quota)
        return MockDbQueryResult(None)


def test_resolve_canonical_gateway_model_mappings() -> None:
    """Verify suffix stripping and canonical normalization for Gemini models."""
    # Suffixes -low, -medium, -high
    assert resolve_canonical_gateway_model("gemini-3.8-flash-low") == "gemini-3.8-flash"
    assert resolve_canonical_gateway_model("gemini-3.8-flash-medium") == "gemini-3.8-flash"
    assert resolve_canonical_gateway_model("gemini-3.8-flash-high") == "gemini-3.8-flash"

    # Other suffixes: -thinking, -preview, -latest
    assert resolve_canonical_gateway_model("gemini-3.8-flash-thinking") == "gemini-3.8-flash"
    assert resolve_canonical_gateway_model("gemini-3.8-flash-preview") == "gemini-3.8-flash"
    assert resolve_canonical_gateway_model("gemini-3.8-flash-latest") == "gemini-3.8-flash"

    # Multi-suffix chaining and case-insensitivity
    assert resolve_canonical_gateway_model("gemini-3.8-flash-thinking-high") == "gemini-3.8-flash"
    assert resolve_canonical_gateway_model("GEMINI-3.8-FLASH-LOW") == "gemini-3.8-flash"
    assert resolve_canonical_gateway_model("models/gemini-3.8-flash-high") == "gemini-3.8-flash"

    # Defaults on empty / None
    assert resolve_canonical_gateway_model(None) == "gemini-3.8-flash"
    assert resolve_canonical_gateway_model("") == "gemini-3.8-flash"
    assert resolve_canonical_gateway_model("   ") == "gemini-3.8-flash"

    # Legacy models preserve base name
    assert resolve_canonical_gateway_model("gemini-2.5-flash-latest") == "gemini-2.5-flash"
    assert resolve_canonical_gateway_model("gemini-1.5-flash-preview") == "gemini-1.5-flash"


def test_calculate_estimated_cost_usd_gemini_3_8_flash_standard_pricing() -> None:
    """Verify Gemini 3.8 Flash Standard pricing schedule ($0.75 / 1M prompt, $3.75 / 1M output)."""
    # 1. Zero tokens -> $0.00
    assert calculate_estimated_cost_usd(0, 0) == Decimal("0")
    assert calculate_estimated_cost_usd(0, 0, "gemini-3.8-flash") == Decimal("0")

    # 2. 1,000,000 prompt tokens = $0.75
    cost_prompt = calculate_estimated_cost_usd(1_000_000, 0, "gemini-3.8-flash")
    assert cost_prompt == Decimal("0.75")

    # 3. 1,000,000 completion tokens = $3.75
    cost_comp = calculate_estimated_cost_usd(0, 1_000_000, "gemini-3.8-flash")
    assert cost_comp == Decimal("3.75")

    # 4. Realistic request: 1,000 prompt + 1,000 completion tokens = $0.004500
    # (1000 * 0.75 + 1000 * 3.75) / 1000000 = (750 + 3750) / 1000000 = 0.004500
    cost_1k = calculate_estimated_cost_usd(1000, 1000, "gemini-3.8-flash")
    assert cost_1k == Decimal("0.004500")

    # 5. Negative tokens clamp to 0
    assert calculate_estimated_cost_usd(-50, -100, "gemini-3.8-flash") == Decimal("0")

    # 6. Suffixed model variants compute the same standard rate
    assert calculate_estimated_cost_usd(1000, 1000, "gemini-3.8-flash-low") == Decimal("0.004500")
    assert calculate_estimated_cost_usd(1000, 1000, "gemini-3.8-flash-medium") == Decimal(
        "0.004500"
    )
    assert calculate_estimated_cost_usd(1000, 1000, "gemini-3.8-flash-high") == Decimal("0.004500")


def test_cost_accounting_separation_and_unverified_gateway() -> None:
    """Verify provider cost accounting vs unverified gateway status."""
    cost_res = calculate_cost_accounting(
        prompt_tokens=1000,
        completion_tokens=1000,
        model_name="gemini-3.8-flash-high",
    )

    assert isinstance(cost_res, CostAccountingResult)
    assert cost_res.model_name == "gemini-3.8-flash-high"
    assert cost_res.canonical_model == "gemini-3.8-flash"
    assert cost_res.pricing_version == "2026-Q1-STANDARD"
    assert cost_res.prompt_tokens == 1000
    assert cost_res.completion_tokens == 1000
    assert cost_res.total_tokens == 2000
    assert cost_res.estimated_provider_cost_usd == Decimal("0.004500")

    # Verify Gateway Pricing Separation
    assert cost_res.actual_gateway_cost_usd is None
    assert cost_res.gateway_cost_status == "UNVERIFIED"
    assert len(cost_res.verification_notes) > 0


def test_legacy_schedule_fallback() -> None:
    """Verify legacy schedule fallback when as_of_date or model is legacy."""
    # 1. Fallback when model is legacy (gemini-2.5-flash)
    cost_legacy_model = calculate_cost_accounting(
        prompt_tokens=1000,
        completion_tokens=1000,
        model_name="gemini-2.5-flash",
    )
    assert cost_legacy_model.pricing_version == "2025-LEGACY"
    assert cost_legacy_model.canonical_model == "gemini-2.5-flash"
    # Legacy pricing: (1000 * 0.075 + 1000 * 0.300) / 1000000 = 0.000375
    assert cost_legacy_model.estimated_provider_cost_usd == Decimal("0.000375")

    # 2. Fallback when model is legacy (gemini-1.5-flash)
    cost_1_5 = calculate_cost_accounting(
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        model_name="gemini-1.5-flash",
    )
    assert cost_1_5.pricing_version == "2025-LEGACY"
    assert cost_1_5.estimated_provider_cost_usd == Decimal("0.375")

    # 3. Fallback when as_of_date <= 2025-12-31 even if model is gemini-3.8-flash
    past_date = date(2025, 11, 15)
    cost_past = calculate_cost_accounting(
        prompt_tokens=1000,
        completion_tokens=1000,
        model_name="gemini-3.8-flash",
        as_of_date=past_date,
    )
    assert cost_past.pricing_version == "2025-LEGACY"
    assert cost_past.effective_date == past_date
    assert cost_past.estimated_provider_cost_usd == Decimal("0.000375")


@pytest.mark.asyncio
async def test_commit_reservation_assigns_calculated_cost_to_usage_log() -> None:
    """Verify commit_reservation computes and logs Gemini 3.8 Flash cost correctly."""
    user_id = uuid7()
    quota_id = uuid7()
    res_id = uuid7()

    quota = AIQuotaORM(
        id=quota_id,
        user_id=user_id,
        free_credits_remaining=3,
        paid_credits_remaining=0,
        reserved_calls=1,
        used_calls=0,
        tokens_consumed=0,
    )
    reservation = AIQuotaReservationORM(
        id=res_id,
        quota_id=quota_id,
        user_id=user_id,
        operation_type="ROADMAP_GEN",
        status="RESERVED",
        tokens_reserved=1,
    )

    mock_session = MockQuotaAsyncSession(reservation=reservation, quota=quota)
    adapter = QuotaFacadeAdapter(session=mock_session)  # type: ignore[arg-type]

    prompt_tokens = 2500
    completion_tokens = 750
    # Gemini 3.8 Flash Standard:
    # (2500 * 0.75 + 750 * 3.75) / 1,000,000 = (1875 + 2812.5) / 1,000,000 = 4687.5 / 1,000,000 = 0.0046875
    expected_cost = (
        Decimal(prompt_tokens) * Decimal("0.75") + Decimal(completion_tokens) * Decimal("3.75")
    ) / ONE_MILLION_TOKENS

    await adapter.commit_reservation(
        reservation_id=res_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model_name="gemini-3.8-flash-medium",
    )

    usage_logs = [item for item in mock_session.added if isinstance(item, AIUsageLogORM)]
    assert len(usage_logs) == 1
    log = usage_logs[0]
    assert log.prompt_tokens == prompt_tokens
    assert log.completion_tokens == completion_tokens
    assert log.total_tokens == prompt_tokens + completion_tokens
    assert log.estimated_cost_usd == expected_cost
    assert log.estimated_cost_usd == Decimal("0.0046875")
    assert log.model_name == "gemini-3.8-flash-medium"
    assert reservation.status == "COMMITTED"


@pytest.mark.asyncio
async def test_commit_reservation_uses_reservation_model_name_property() -> None:
    """Verify reservation.model_name is used when attached directly to reservation."""
    user_id = uuid7()
    quota_id = uuid7()
    res_id = uuid7()

    quota = AIQuotaORM(
        id=quota_id,
        user_id=user_id,
        free_credits_remaining=3,
        paid_credits_remaining=0,
        reserved_calls=1,
        used_calls=0,
        tokens_consumed=0,
    )
    reservation = AIQuotaReservationORM(
        id=res_id,
        quota_id=quota_id,
        user_id=user_id,
        operation_type="ROADMAP_GEN",
        status="RESERVED",
        tokens_reserved=1,
    )
    reservation.model_name = "gemini-3.8-flash-high"

    mock_session = MockQuotaAsyncSession(reservation=reservation, quota=quota)
    adapter = QuotaFacadeAdapter(session=mock_session)  # type: ignore[arg-type]

    await adapter.commit_reservation(
        reservation_id=res_id,
        prompt_tokens=1000,
        completion_tokens=1000,
        model_name="ignored-fallback-model",
    )

    usage_logs = [item for item in mock_session.added if isinstance(item, AIUsageLogORM)]
    assert len(usage_logs) == 1
    log = usage_logs[0]
    assert log.model_name == "gemini-3.8-flash-high"
    assert log.estimated_cost_usd == Decimal("0.004500")


@pytest.mark.asyncio
async def test_commit_reservation_cost_with_database_session() -> None:
    """Verify DB session integration recording in AIUsageLogORM."""
    user_id = uuid7()
    unique_email = f"cost_test_{uuid.uuid4().hex}@focusflow.vn"
    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=unique_email,
                password_hash="argon2id$mockhash",
                full_name="Cost Test Learner",
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier="FREE",
                is_locked=False,
            )
        )
        await session.commit()

    async with async_session_factory() as session:
        facade = QuotaFacadeAdapter(session=session)
        res_id = await facade.reserve_quota(user_id=user_id, operation_type="SCHEDULE_PROPOSAL")
        await session.commit()

        # Commit reservation with Gemini 3.8 Flash
        await facade.commit_reservation(
            reservation_id=res_id,
            prompt_tokens=4000,
            completion_tokens=1500,
            model_name="gemini-3.8-flash",
        )
        await session.commit()

        # Query written AIUsageLogORM
        stmt = (
            select(AIUsageLogORM)
            .where(AIUsageLogORM.user_id == user_id)
            .order_by(AIUsageLogORM.created_at.desc())
        )
        log = (await session.execute(stmt)).scalars().first()
        assert log is not None
        assert log.prompt_tokens == 4000
        assert log.completion_tokens == 1500
        assert log.total_tokens == 5500
        assert log.model_name == "gemini-3.8-flash"
        # Expected: (4000 * 0.75 + 1500 * 3.75) / 1000000 = (3000 + 5625) / 1000000 = 0.008625 USD
        assert log.estimated_cost_usd == Decimal("0.008625")
