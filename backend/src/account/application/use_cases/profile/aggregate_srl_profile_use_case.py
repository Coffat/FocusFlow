from datetime import UTC, datetime
from decimal import Decimal
from statistics import median
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.account.application.ports.learner_profile_repository_port import (
    LearnerProfileRecordDTO,
    LearnerProfileRepositoryPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.execution.public_api import ExecutionDashboardQueryPort
from src.shared_kernel.application.uow import AsyncUnitOfWork

COLD_START_MIN_SESSIONS = 3
_BUCKET_ORDER: tuple[str, ...] = ("MORNING", "AFTERNOON", "EVENING", "NIGHT")


def _resolve_timezone(tz_name: str | None) -> ZoneInfo:
    raw = (tz_name or "").strip()
    if not raw:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _hour_to_slot(hour: int) -> str:
    if 5 <= hour <= 11:
        return "MORNING"
    if 12 <= hour <= 17:
        return "AFTERNOON"
    if 18 <= hour <= 22:
        return "EVENING"
    return "NIGHT"


def _compute_peak_productivity_slots(
    start_datetimes_utc: tuple[datetime, ...],
    user_tz: ZoneInfo,
) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for dt in start_datetimes_utc:
        aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
        local_hour = aware.astimezone(user_tz).hour
        slot = _hour_to_slot(local_hour)
        counts[slot] = counts.get(slot, 0) + 1

    ranked = sorted(
        counts.items(),
        key=lambda item: (-item[1], _BUCKET_ORDER.index(item[0])),
    )
    return tuple(slot for slot, _ in ranked[:2])


class AggregateSrlProfileUseCase:
    """Aggregate real StudySession facts into `learner_profiles` (BE-MOCK-02)."""

    def __init__(
        self,
        *,
        user_repo: UserRepositoryPort,
        learner_profile_repo: LearnerProfileRepositoryPort,
        execution_dashboard_port: ExecutionDashboardQueryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._user_repo = user_repo
        self._learner_profile_repo = learner_profile_repo
        self._execution_dashboard_port = execution_dashboard_port
        self._uow = uow

    async def execute(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
    ) -> LearnerProfileRecordDTO:
        effective_now = now or datetime.now(UTC)
        user = await self._user_repo.find_by_id(user_id)
        user_tz = _resolve_timezone(getattr(user, "timezone", None) if user is not None else None)

        facts = await self._execution_dashboard_port.get_srl_session_facts(user_id)
        total_completed = max(0, int(facts.total_completed_sessions))
        is_cold_start = total_completed < COLD_START_MIN_SESSIONS

        clamped_rate = max(0.0, min(100.0, float(facts.weekly_completion_rate)))
        weekly_completion_rate = Decimal(f"{clamped_rate:.2f}")

        if is_cold_start:
            optimal_focus_duration_mins = 25
            estimation_bias_factor = Decimal("1.00")
            peak_productivity_slots: tuple[str, ...] = ()
        else:
            if facts.completed_durations_mins:
                med_duration = int(round(float(median(facts.completed_durations_mins))))
                optimal_focus_duration_mins = max(15, min(120, med_duration))
            else:
                optimal_focus_duration_mins = 25

            if len(facts.estimation_ratios) >= COLD_START_MIN_SESSIONS:
                mean_ratio = sum(facts.estimation_ratios) / len(facts.estimation_ratios)
                clamped_bias = max(0.50, min(2.00, mean_ratio))
                estimation_bias_factor = Decimal(f"{clamped_bias:.2f}")
            else:
                estimation_bias_factor = Decimal("1.00")

            peak_productivity_slots = _compute_peak_productivity_slots(
                facts.session_start_datetimes_utc,
                user_tz,
            )

        record = LearnerProfileRecordDTO(
            user_id=user_id,
            optimal_focus_duration_mins=optimal_focus_duration_mins,
            peak_productivity_slots=peak_productivity_slots,
            estimation_bias_factor=estimation_bias_factor,
            weekly_completion_rate=weekly_completion_rate,
            total_completed_sessions=total_completed,
            is_cold_start=is_cold_start,
            last_aggregated_at=effective_now,
        )

        async with self._uow:
            saved = await self._learner_profile_repo.upsert(record, now=effective_now)
            await self._uow.commit()

        return saved
