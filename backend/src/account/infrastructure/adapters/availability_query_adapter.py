from datetime import UTC, datetime, time
from uuid import UUID

from src.account.application.ports.availability_repository_port import (
    AvailabilityRepositoryPort,
)
from src.account.domain.exceptions.availability import (
    ConcurrentAvailabilityModifiedException,
)
from src.account.domain.models.availability import (
    AvailabilityMode,
    AvailabilityProfile,
    ProposedTaskSlot,
    parse_time_str,
)
from src.account.domain.services.hybrid_availability_rule_engine import (
    HybridAvailabilityRuleEngine,
)
from src.account.public_api import (
    AvailabilityGateResultDTO,
    AvailabilityQueryPort,
    AvailabilitySnapshotDTO,
    ProposedTaskBlockDTO,
)


class SqlAlchemyAvailabilityQueryAdapter(AvailabilityQueryPort):
    """Implementation of AvailabilityQueryPort exposed to Planning and Evaluation contexts."""

    def __init__(self, repository: AvailabilityRepositoryPort) -> None:
        self._repository = repository

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None:
        profile = await self._repository.get_by_user_id(user_id)
        is_persisted = profile is not None
        if profile is None:
            profile = AvailabilityProfile.create_default(user_id)

        daily_caps = [
            profile.get_daily_ceiling(day_name)
            for day_name, d in profile.weekly_schedule.days.items()
            if d.enabled
        ]
        daily_cap_minutes = max(daily_caps) if daily_caps else 0
        weekly_capacity_minutes = int(
            profile.weekly_schedule.calculate_total_weekly_hours(profile.mode) * 60
        )
        daily_quota_minutes = {
            day_name: int(round(d.quota_hours * 60)) if d.enabled else 0
            for day_name, d in profile.weekly_schedule.days.items()
        }
        disabled_weekdays = tuple(
            day_name for day_name, d in profile.weekly_schedule.days.items() if not d.enabled
        )
        availability_slots = tuple(
            {
                "day_of_week": day_name,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "end_day_offset": slot.end_day_offset,
                "is_active": d.enabled,
            }
            for day_name, d in profile.weekly_schedule.days.items()
            for slot in d.time_slots
        )

        return AvailabilitySnapshotDTO(
            user_id=profile.user_id,
            mode=profile.mode.value,
            daily_cap_minutes=daily_cap_minutes,
            weekly_capacity_minutes=weekly_capacity_minutes,
            updated_at=profile.updated_at.isoformat() if is_persisted else None,
            daily_quota_minutes=daily_quota_minutes,
            availability_slots=availability_slots,
            disabled_weekdays=disabled_weekdays,
        )

    async def validate_schedule_proposal(
        self,
        user_id: UUID,
        proposed_tasks: list[ProposedTaskBlockDTO],
        occupied_tasks: list[ProposedTaskBlockDTO] | None = None,
        expected_updated_at: str | None = None,
    ) -> AvailabilityGateResultDTO:
        profile = await self._repository.get_by_user_id(user_id)
        is_persisted = profile is not None
        if profile is None:
            profile = AvailabilityProfile.create_default(user_id)

        actual_updated_at = profile.updated_at.isoformat() if is_persisted else None

        # Optimistic locking check against concurrent modifications
        if expected_updated_at is not None and is_persisted:
            if expected_updated_at == "":
                raise ConcurrentAvailabilityModifiedException(
                    details={"expected": expected_updated_at, "actual": actual_updated_at}
                )
            try:
                expected_dt = datetime.fromisoformat(
                    expected_updated_at.replace("Z", "+00:00")
                ).astimezone(UTC)
            except ValueError as exc:
                raise ConcurrentAvailabilityModifiedException(
                    details={"expected": expected_updated_at, "actual": actual_updated_at}
                ) from exc

            actual_dt = profile.updated_at.astimezone(UTC)
            if abs((expected_dt - actual_dt).total_seconds()) > 0.001:
                raise ConcurrentAvailabilityModifiedException(
                    details={"expected": expected_updated_at, "actual": actual_updated_at}
                )

        occupied_by_day: dict[str, list[tuple[time, time, int]]] = {}
        for occ in occupied_tasks or []:
            d_key = occ.day_of_week.lower()
            s_t = parse_time_str(occ.start_time)
            e_t = parse_time_str(occ.end_time)
            occupied_by_day.setdefault(d_key, []).append((s_t, e_t, occ.end_day_offset))

        proposed_by_day: dict[str, list[ProposedTaskSlot]] = {}
        for task in proposed_tasks:
            d_key = task.day_of_week.lower()
            s_t = parse_time_str(task.start_time)
            e_t = parse_time_str(task.end_time)
            slot = ProposedTaskSlot(
                task_id=task.task_id,
                title=task.title,
                day_of_week=d_key,
                start_time=s_t,
                end_time=e_t,
                end_day_offset=task.end_day_offset,
                duration_minutes=task.duration_minutes,
            )
            proposed_by_day.setdefault(d_key, []).append(slot)

        has_soft_overflow = False
        max_overflow = 0
        all_reasons: list[str] = []

        for d_key, tasks in proposed_by_day.items():
            day_occupied = occupied_by_day.get(d_key, [])
            if profile.mode == AvailabilityMode.MODE_A:
                occupied_minutes = sum(
                    max(
                        0,
                        (e_t.hour * 60 + e_t.minute + offset * 1440) - (s_t.hour * 60 + s_t.minute),
                    )
                    for s_t, e_t, offset in day_occupied
                )
                total_task_minutes = sum(t.duration_minutes for t in tasks) + occupied_minutes
                res = HybridAvailabilityRuleEngine.validate_daily_ceiling(
                    profile, d_key, total_task_minutes
                )

                window_violations: list[str] = []
                day_schedule = profile.weekly_schedule.days.get(d_key)
                if day_schedule is not None and day_schedule.enabled:
                    win_s_t = parse_time_str(day_schedule.allowed_window.start)
                    win_e_t = parse_time_str(day_schedule.allowed_window.end)
                    win_s = win_s_t.hour * 60 + win_s_t.minute
                    win_e = win_e_t.hour * 60 + win_e_t.minute
                    for t in tasks:
                        t_s, t_e = t.minute_range()
                        if t_s < win_s or t_e > win_e:
                            window_violations.append(
                                f"Nhiệm vụ '{t.title}' [{t.start_time.strftime('%H:%M')}-{t.end_time.strftime('%H:%M')}] "
                                f"nằm ngoài khung giờ cho phép ({day_schedule.allowed_window.start}-{day_schedule.allowed_window.end}) vào {d_key}."
                            )

                if not res.is_valid or window_violations:
                    all_reasons.extend(res.violation_reasons)
                    all_reasons.extend(window_violations)
                    return AvailabilityGateResultDTO(
                        is_valid=False,
                        has_soft_overflow=False,
                        overflow_minutes=res.overflow_minutes,
                        violation_reasons=tuple(all_reasons),
                        availability_updated_at=actual_updated_at,
                    )
            else:
                res = HybridAvailabilityRuleEngine.validate_proposal_against_slots(
                    profile, d_key, tasks, day_occupied
                )
                if not res.is_valid:
                    return AvailabilityGateResultDTO(
                        is_valid=False,
                        has_soft_overflow=False,
                        overflow_minutes=res.overflow_minutes,
                        violation_reasons=res.violation_reasons,
                        availability_updated_at=actual_updated_at,
                    )

            if res.has_soft_overflow:
                has_soft_overflow = True
                max_overflow = max(max_overflow, res.overflow_minutes)

        return AvailabilityGateResultDTO(
            is_valid=True,
            has_soft_overflow=has_soft_overflow,
            overflow_minutes=max_overflow,
            violation_reasons=(),
            availability_updated_at=actual_updated_at,
        )
