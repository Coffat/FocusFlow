from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.account.domain.exceptions.quota_exceptions import (
    QuotaExceededException,
    QuotaReservationNotFoundError,
)
from src.account.infrastructure.orm.user_orm import (
    AIQuotaORM,
    AIQuotaReservationORM,
    AIUsageLogORM,
)
from src.account.public_api import QuotaFacadePort

_VALID_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "ROADMAP_GENERATION",
        "SCHEDULE_PROPOSAL",
        "AI_REVIEW_WEEKLY",
        "AI_REVIEW_MILESTONE",
        "MILESTONE_BREAKDOWN",
        "CHAT_ASSISTANT",
    }
)

_ACTION_TYPE_ALIASES: dict[str, str] = {
    "ROADMAP_GEN": "ROADMAP_GENERATION",
    "MILESTONE_GEN": "MILESTONE_BREAKDOWN",
    "PROPOSAL_GEN": "SCHEDULE_PROPOSAL",
    "SCHEDULE_GEN": "SCHEDULE_PROPOSAL",
    "WEEKLY_REVIEW": "AI_REVIEW_WEEKLY",
    "MILESTONE_REVIEW": "AI_REVIEW_MILESTONE",
}


def normalize_action_type(operation_type: str) -> str:
    """Normalize operation_type string into valid ai_usage_logs.action_type value."""
    upper = (operation_type or "ROADMAP_GENERATION").strip().upper()
    if upper in _VALID_ACTION_TYPES:
        return upper
    return _ACTION_TYPE_ALIASES.get(upper, "ROADMAP_GENERATION")


class QuotaFacadeAdapter(QuotaFacadePort):
    """SQLAlchemy 2-Phase ACID AI Quota Reservation Adapter (ADR-005, BUSR-10).

    Never calls session.commit(); transactions are managed by AsyncUnitOfWork or caller.
    """

    def __init__(self, session: AsyncSession, default_free_credits: int = 3) -> None:
        self._session = session
        self._default_free_credits = default_free_credits

    async def _get_or_init_quota_for_update(self, user_id: UUID) -> AIQuotaORM:
        stmt = select(AIQuotaORM).where(AIQuotaORM.user_id == user_id).with_for_update()
        result = await self._session.execute(stmt)
        quota = result.scalar_one_or_none()
        if quota is None:
            now = datetime.now(UTC)
            quota = AIQuotaORM(
                id=uuid7(),
                user_id=user_id,
                free_credits_remaining=self._default_free_credits,
                paid_credits_remaining=0,
                used_calls=0,
                reserved_calls=0,
                tokens_consumed=0,
                cycle_start=now,
                cycle_end=now + timedelta(days=30),
            )
            self._session.add(quota)
            await self._session.flush()
        return quota

    async def check_quota_available(
        self,
        user_id: UUID,
        min_credits: int = 1,
    ) -> bool:
        quota = await self._get_or_init_quota_for_update(user_id)
        total_available = int(quota.free_credits_remaining or 0) + int(
            quota.paid_credits_remaining or 0
        )
        return total_available >= min_credits

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str | int = "ROADMAP_GEN",
        cost: int | str = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        # Support both (user_id, operation_type, cost) and (user_id, cost, operation_type)
        if isinstance(operation_type, int) and isinstance(cost, str):
            actual_cost = int(operation_type)
            actual_op = str(cost)
        else:
            actual_op = str(operation_type)
            actual_cost = int(cost)

        if actual_cost <= 0:
            actual_cost = 1

        quota = await self._get_or_init_quota_for_update(user_id)
        total_available = quota.free_credits_remaining + quota.paid_credits_remaining
        if total_available < actual_cost:
            raise QuotaExceededException(
                message=(
                    f"Không đủ hạn ngạch AI: cần {actual_cost} credit, "
                    f"hiện còn {total_available} credit."
                )
            )

        # Hold credits during reservation phase while preserving DB invariant
        # used_calls + reserved_calls <= monthly_limit
        quota.reserved_calls = (quota.reserved_calls or 0) + actual_cost
        used = int(quota.used_calls or 0)
        if used + quota.reserved_calls > quota.monthly_limit:
            quota.monthly_limit = used + quota.reserved_calls

        now = datetime.now(UTC)
        reservation = AIQuotaReservationORM(
            id=uuid7(),
            quota_id=quota.id,
            user_id=user_id,
            operation_type=actual_op,
            status="RESERVED",
            tokens_reserved=actual_cost,
            expires_at=now + timedelta(seconds=ttl_seconds),
            created_at=now,
            resolved_at=None,
        )
        self._session.add(reservation)
        await self._session.flush()
        return reservation.id

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        stmt = (
            select(AIQuotaReservationORM)
            .where(AIQuotaReservationORM.id == reservation_id)
            .with_for_update()
        )
        res = (await self._session.execute(stmt)).scalar_one_or_none()
        if res is None:
            raise QuotaReservationNotFoundError(f"Không tìm thấy reservation_id={reservation_id}.")

        # Idempotent if already COMMITTED
        if res.status == "COMMITTED":
            return

        if res.status in ("RELEASED", "EXPIRED"):
            return

        quota_stmt = select(AIQuotaORM).where(AIQuotaORM.id == res.quota_id).with_for_update()
        quota = (await self._session.execute(quota_stmt)).scalar_one_or_none()
        if quota is None:
            quota = await self._get_or_init_quota_for_update(res.user_id)

        cost = max(1, int(res.tokens_reserved or 1))
        free_rem = quota.free_credits_remaining
        paid_rem = quota.paid_credits_remaining

        # Deduct from free_credits_remaining first, then paid_credits_remaining (BUSR-10)
        deduct_from_free = min(free_rem, cost)
        deduct_from_paid = max(0, cost - deduct_from_free)
        new_free = max(0, free_rem - deduct_from_free)
        new_paid = max(0, paid_rem - deduct_from_paid)

        quota.reserved_calls = max(0, int(quota.reserved_calls or 0) - cost)
        quota.used_calls = int(quota.used_calls or 0) + cost
        total_tok = max(0, int(prompt_tokens)) + max(0, int(completion_tokens))
        quota.tokens_consumed = int(quota.tokens_consumed or 0) + total_tok
        quota._set_credit_pool(new_free, new_paid)

        now = datetime.now(UTC)
        res.status = "COMMITTED"
        res.resolved_at = now

        usage_log = AIUsageLogORM(
            id=uuid7(),
            user_id=res.user_id,
            action_type=normalize_action_type(res.operation_type),
            model_name=model_name or "gemini-2.5-flash",
            prompt_tokens=max(0, int(prompt_tokens)),
            completion_tokens=max(0, int(completion_tokens)),
            total_tokens=total_tok,
            latency_ms=0,
            status="SUCCESS",
            created_at=now,
        )
        self._session.add(usage_log)
        await self._session.flush()

    async def release_reservation(
        self,
        reservation_id: UUID,
        reason: str = "RELEASED",
    ) -> None:
        _ = reason
        stmt = (
            select(AIQuotaReservationORM)
            .where(AIQuotaReservationORM.id == reservation_id)
            .with_for_update()
        )
        res = (await self._session.execute(stmt)).scalar_one_or_none()
        if res is None:
            raise QuotaReservationNotFoundError(f"Không tìm thấy reservation_id={reservation_id}.")

        # Idempotent if already RELEASED or EXPIRED
        if res.status in ("RELEASED", "EXPIRED"):
            return

        if res.status == "COMMITTED":
            return

        quota_stmt = select(AIQuotaORM).where(AIQuotaORM.id == res.quota_id).with_for_update()
        quota = (await self._session.execute(quota_stmt)).scalar_one_or_none()
        cost = max(1, int(res.tokens_reserved or 1))
        if quota is not None:
            free_rem = quota.free_credits_remaining
            paid_rem = quota.paid_credits_remaining
            quota.reserved_calls = max(0, int(quota.reserved_calls or 0) - cost)
            quota._set_credit_pool(free_rem, paid_rem)

        res.status = "RELEASED"
        res.resolved_at = datetime.now(UTC)
        await self._session.flush()

    async def expire_stale_reservations(self, now: datetime | None = None) -> int:
        """Sweeper helper: mark expired RESERVED rows as EXPIRED with SKIP LOCKED."""
        current_time = now or datetime.now(UTC)
        stmt = (
            select(AIQuotaReservationORM)
            .where(
                AIQuotaReservationORM.status == "RESERVED",
                AIQuotaReservationORM.expires_at <= current_time,
            )
            .with_for_update(skip_locked=True)
        )
        stale_rows = list((await self._session.execute(stmt)).scalars().all())
        for res in stale_rows:
            quota_stmt = select(AIQuotaORM).where(AIQuotaORM.id == res.quota_id).with_for_update()
            quota = (await self._session.execute(quota_stmt)).scalar_one_or_none()
            cost = max(1, int(res.tokens_reserved or 1))
            if quota is not None:
                free_rem = quota.free_credits_remaining
                paid_rem = quota.paid_credits_remaining
                quota.reserved_calls = max(0, int(quota.reserved_calls or 0) - cost)
                quota._set_credit_pool(free_rem, paid_rem)
            res.status = "EXPIRED"
            res.resolved_at = current_time

        if stale_rows:
            await self._session.flush()
        return len(stale_rows)


SqlAlchemyQuotaFacadeAdapter = QuotaFacadeAdapter
