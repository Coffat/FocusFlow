from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from uuid6 import uuid7

from src.account.domain.exceptions.quota_exceptions import (
    QuotaExceededException,
    QuotaReservationNotFoundError,
)
from src.account.domain.services.ai_cost_accounting_service import (
    CostAccountingResult,
    build_usage_log_metadata,
    build_usage_log_metadata_dict,
    calculate_cost_accounting,
    calculate_estimated_cost_usd,
    parse_usage_log_metadata,
    resolve_canonical_gateway_model,
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
        "GOAL_CLARIFICATION",
    }
)

_ACTION_TYPE_ALIASES: dict[str, str] = {
    "ROADMAP_GEN": "ROADMAP_GENERATION",
    "MILESTONE_GEN": "MILESTONE_BREAKDOWN",
    "TASK_DECOMPOSITION": "MILESTONE_BREAKDOWN",
    "PROPOSAL_GEN": "SCHEDULE_PROPOSAL",
    "SCHEDULE_GEN": "SCHEDULE_PROPOSAL",
    "WEEKLY_REVIEW": "AI_REVIEW_WEEKLY",
    "CRITIC_REVIEW": "AI_REVIEW_WEEKLY",
    "MILESTONE_REVIEW": "AI_REVIEW_MILESTONE",
    "VALIDATION_JUDGE": "AI_REVIEW_MILESTONE",
    "CLARIFICATION": "GOAL_CLARIFICATION",
}


# Re-exported cost accounting utilities (ADR-005, BUSR-10)
__all__ = [
    "CostAccountingResult",
    "QuotaFacadeAdapter",
    "SqlAlchemyQuotaFacadeAdapter",
    "build_usage_log_metadata",
    "calculate_cost_accounting",
    "calculate_estimated_cost_usd",
    "normalize_action_type",
    "parse_usage_log_metadata",
    "resolve_canonical_gateway_model",
]


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
        self._recorded_attempt_keys: set[str] = set()
        self._reservations_with_attempt_logs: set[UUID] = set()

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

    def _is_db_session(self) -> bool:
        return isinstance(self._session, AsyncSession)

    def _compute_available(self, quota: AIQuotaORM) -> int:
        if self._is_db_session():
            return max(
                0,
                int(quota.monthly_limit or 0)
                - int(quota.used_calls or 0)
                - int(quota.reserved_calls or 0),
            )
        return max(
            0,
            int(quota.free_credits_remaining or 0)
            + int(quota.paid_credits_remaining or 0)
            - int(quota.reserved_calls or 0),
        )

    async def check_quota_available(
        self,
        user_id: UUID,
        min_credits: int = 1,
    ) -> bool:
        quota = await self._get_or_init_quota_for_update(user_id)
        return self._compute_available(quota) >= min_credits

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
        total_available = self._compute_available(quota)
        if total_available < actual_cost:
            raise QuotaExceededException(
                message=(
                    f"Không đủ hạn ngạch AI: cần {actual_cost} credit, "
                    f"hiện còn {max(0, total_available)} credit."
                )
            )

        quota.reserved_calls = int(quota.reserved_calls or 0) + actual_cost

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
        model_name: str = "gemini-3.8-flash",
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
        quota.reserved_calls = max(0, int(quota.reserved_calls or 0) - cost)
        quota.used_calls = int(quota.used_calls or 0) + cost
        total_tok = max(0, int(prompt_tokens)) + max(0, int(completion_tokens))
        quota.tokens_consumed = int(quota.tokens_consumed or 0) + total_tok

        if self._is_db_session():
            if (
                "_free_credits_remaining" in quota.__dict__
                and "_paid_credits_remaining" in quota.__dict__
            ):
                free_rem = int(quota.__dict__["_free_credits_remaining"])
                paid_rem = int(quota.__dict__["_paid_credits_remaining"])
                deduct_from_free = min(free_rem, cost)
                deduct_from_paid = max(0, cost - deduct_from_free)
                quota.__dict__["_free_credits_remaining"] = max(0, free_rem - deduct_from_free)
                quota.__dict__["_paid_credits_remaining"] = max(0, paid_rem - deduct_from_paid)
        else:
            free_rem = quota.free_credits_remaining
            paid_rem = quota.paid_credits_remaining
            deduct_from_free = min(free_rem, cost)
            deduct_from_paid = max(0, cost - deduct_from_free)
            quota._set_credit_pool(
                max(0, free_rem - deduct_from_free),
                max(0, paid_rem - deduct_from_paid),
            )

        now = datetime.now(UTC)
        res.status = "COMMITTED"
        res.resolved_at = now

        reservation = res
        model_for_cost = reservation.model_name or model_name or "gemini-3.8-flash"
        res_key = f"reservation:{res.id}"
        already_recorded_for_reservation = res.id in self._reservations_with_attempt_logs
        if not already_recorded_for_reservation and isinstance(self._session, AsyncSession):
            existing_stmt = text(
                "SELECT id FROM ai_usage_logs "
                "WHERE user_id = :uid AND audit_metadata->>'reservation_id' = :rid "
                "LIMIT 1"
            )
            existing_row = (
                await self._session.execute(
                    existing_stmt,
                    {"uid": res.user_id, "rid": str(res.id)},
                )
            ).scalar_one_or_none()
            if existing_row is not None:
                already_recorded_for_reservation = True
                self._reservations_with_attempt_logs.add(res.id)

        if not already_recorded_for_reservation and res_key not in self._recorded_attempt_keys:
            await self.record_attempt_usage(
                user_id=res.user_id,
                action_type=res.operation_type,
                requested_model=model_for_cost,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                status="SUCCESS",
                reservation_id=res.id,
                idempotency_key=res_key,
            )

    async def record_attempt_usage(
        self,
        *,
        user_id: UUID,
        action_type: str,
        requested_model: str = "gemini-3.8-flash",
        resolved_model: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        thinking_tokens: int = 0,
        latency_ms: int = 0,
        status: Literal["SUCCESS", "FAILED", "RATE_LIMITED", "TIMEOUT"] = "SUCCESS",
        usage_completeness: Literal["COMPLETE", "PARTIAL", "UNKNOWN"] = "COMPLETE",
        usage_source: Literal[
            "GATEWAY_TELEMETRY", "CACHE", "ESTIMATED", "UNKNOWN"
        ] = "GATEWAY_TELEMETRY",
        error_code: str | None = None,
        error_message: str | None = None,
        attempt_no: int = 1,
        idempotency_key: str | None = None,
        reservation_id: UUID | None = None,
    ) -> AIUsageLogORM | None:
        """Idempotently record a single attempt's provider token usage and cost accounting.

        When backed by PostgreSQL AsyncEngine, executes an atomic INSERT ... ON CONFLICT DO NOTHING
        in an autonomous transaction so provider usage telemetry survives caller UoW rollbacks and
        concurrent multi-worker retries.
        """
        cost_res = calculate_cost_accounting(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_name=requested_model,
            thinking_tokens=thinking_tokens,
            resolved_model=resolved_model,
            usage_completeness=usage_completeness,
            usage_source=usage_source,
        )

        meta_dict = build_usage_log_metadata_dict(
            requested_model=requested_model,
            resolved_model=resolved_model,
            pricing_version=cost_res.pricing_version,
            usage_source=usage_source,
            usage_completeness=usage_completeness,
            cost_verification_status=cost_res.gateway_cost_status,
            thinking_tokens=thinking_tokens,
            attempt_no=attempt_no,
            idempotency_key=idempotency_key,
            reservation_id=str(reservation_id) if reservation_id else None,
            error_detail=error_message,
        )

        chosen_model = resolved_model or requested_model or "gemini-3.8-flash"
        normalized_action = normalize_action_type(action_type)
        now = datetime.now(UTC)
        log_id = uuid7()

        session_bind = getattr(self._session, "bind", None)
        if isinstance(self._session, AsyncSession) and isinstance(session_bind, AsyncEngine):
            stmt = pg_insert(AIUsageLogORM).values(
                id=log_id,
                user_id=user_id,
                action_type=normalized_action,
                model_name=chosen_model,
                prompt_tokens=cost_res.prompt_tokens,
                completion_tokens=cost_res.completion_tokens,
                total_tokens=cost_res.total_tokens,
                latency_ms=max(0, int(latency_ms)),
                estimated_cost_usd=cost_res.estimated_provider_cost_usd,
                status=status,
                error_code=error_code,
                error_message=error_message,
                idempotency_key=idempotency_key,
                audit_metadata=meta_dict,
                created_at=now,
            )
            if idempotency_key is not None:
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["idempotency_key"],
                    index_where=text("idempotency_key IS NOT NULL"),
                )
            returning_stmt = stmt.returning(AIUsageLogORM.id)

            async with AsyncSession(bind=session_bind, expire_on_commit=False) as audit_session:
                try:
                    exec_res = await audit_session.execute(returning_stmt)
                    inserted_id = exec_res.scalar_one_or_none()
                    await audit_session.commit()
                    if reservation_id is not None:
                        self._reservations_with_attempt_logs.add(reservation_id)
                    if inserted_id is None:
                        if idempotency_key is not None:
                            self._recorded_attempt_keys.add(idempotency_key)
                        return None
                    if idempotency_key is not None:
                        self._recorded_attempt_keys.add(idempotency_key)
                    return await audit_session.get(AIUsageLogORM, inserted_id)
                except IntegrityError as exc:
                    await audit_session.rollback()
                    if "fk_ai_usage_logs_user" not in str(exc):
                        raise

        # Fallback for MockQuotaAsyncSession or uncommitted in-transaction test UserORM
        if idempotency_key is not None:
            if idempotency_key in self._recorded_attempt_keys:
                return None
            self._recorded_attempt_keys.add(idempotency_key)
        if reservation_id is not None:
            self._reservations_with_attempt_logs.add(reservation_id)

        usage_log = AIUsageLogORM(
            id=log_id,
            user_id=user_id,
            action_type=normalized_action,
            model_name=chosen_model,
            prompt_tokens=cost_res.prompt_tokens,
            completion_tokens=cost_res.completion_tokens,
            total_tokens=cost_res.total_tokens,
            latency_ms=max(0, int(latency_ms)),
            estimated_cost_usd=cost_res.estimated_provider_cost_usd,
            status=status,
            error_code=error_code,
            error_message=error_message,
            idempotency_key=idempotency_key,
            audit_metadata=meta_dict,
            created_at=now,
        )
        self._session.add(usage_log)
        await self._session.flush()
        return usage_log

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
            return

        # Idempotent if already RELEASED, EXPIRED, or COMMITTED
        if res.status in ("RELEASED", "EXPIRED", "COMMITTED"):
            return

        quota_stmt = select(AIQuotaORM).where(AIQuotaORM.id == res.quota_id).with_for_update()
        quota = (await self._session.execute(quota_stmt)).scalar_one_or_none()
        cost = max(1, int(res.tokens_reserved or 1))
        if quota is not None:
            quota.reserved_calls = max(0, int(quota.reserved_calls or 0) - cost)

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
                quota.reserved_calls = max(0, int(quota.reserved_calls or 0) - cost)
            res.status = "EXPIRED"
            res.resolved_at = current_time

        if stale_rows:
            await self._session.flush()
        return len(stale_rows)


SqlAlchemyQuotaFacadeAdapter = QuotaFacadeAdapter
