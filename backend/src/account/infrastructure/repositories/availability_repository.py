from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.application.ports.availability_repository_port import (
    AvailabilityRepositoryPort,
)
from src.account.domain.models.availability import (
    AllowedWindow,
    AvailabilityMode,
    AvailabilityProfile,
    CalendarIntegrationMode,
    DaySchedule,
    PreferredPeriod,
    TimeSlot,
    WeeklySchedule,
    parse_time_str,
)
from src.account.infrastructure.orm.availability_orm import (
    AvailabilityORM,
    AvailabilitySlotORM,
)

DAY_TO_INT = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
INT_TO_DAY = {v: k for k, v in DAY_TO_INT.items()}


class SqlAlchemyAvailabilityRepository(AvailabilityRepositoryPort):
    """Data Mapper repository persisting AvailabilityProfile across 3NF tables without committing."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> AvailabilityProfile | None:
        stmt = select(AvailabilityORM).where(AvailabilityORM.user_id == user_id)
        result = await self.session.execute(stmt)
        avail_orm = result.scalar_one_or_none()
        if avail_orm is None:
            return None

        slots_stmt = (
            select(AvailabilitySlotORM)
            .where(AvailabilitySlotORM.availability_id == avail_orm.id)
            .order_by(AvailabilitySlotORM.day_of_week.asc(), AvailabilitySlotORM.start_time.asc())
        )
        slots_res = await self.session.execute(slots_stmt)
        all_slots = list(slots_res.scalars().all())

        days: dict[str, DaySchedule] = {}
        for day_num in range(7):
            day_name = INT_TO_DAY[day_num]
            quota_cfg: dict[str, Any] = avail_orm.daily_quotas.get(day_name, {})
            enabled = bool(quota_cfg.get("enabled", True))
            quota_hours = float(quota_cfg.get("quota_hours", 2.0))
            min_session = int(quota_cfg.get("min_session_minutes", avail_orm.min_session_minutes))
            preferred = PreferredPeriod(quota_cfg.get("preferred_period", "ANY"))

            allowed_slot_orm = next(
                (s for s in all_slots if s.day_of_week == day_num and s.slot_type == "ALLOWED"),
                None,
            )
            if allowed_slot_orm is not None:
                allowed_window = AllowedWindow(
                    start=allowed_slot_orm.start_time.strftime("%H:%M"),
                    end=allowed_slot_orm.end_time.strftime("%H:%M"),
                )
            else:
                window_cfg: dict[str, str] = quota_cfg.get("allowed_window", {})
                allowed_window = AllowedWindow(
                    start=window_cfg.get("start", "07:00"),
                    end=window_cfg.get("end", "23:00"),
                )

            day_fixed_slots = [
                TimeSlot(
                    start_time=s.start_time,
                    end_time=s.end_time,
                    end_day_offset=s.end_day_offset,
                )
                for s in all_slots
                if s.day_of_week == day_num and s.slot_type == "FIXED"
            ]

            days[day_name] = DaySchedule(
                enabled=enabled,
                quota_hours=quota_hours,
                time_slots=tuple(day_fixed_slots),
                allowed_window=allowed_window,
                preferred_period=preferred,
                min_session_minutes=min_session,
            )

        return AvailabilityProfile(
            id=avail_orm.id,
            user_id=avail_orm.user_id,
            mode=AvailabilityMode(avail_orm.mode),
            calendar_integration_mode=CalendarIntegrationMode(avail_orm.calendar_integration_mode),
            weekly_schedule=WeeklySchedule(days=days),
            min_session_minutes=avail_orm.min_session_minutes,
            created_at=avail_orm.created_at,
            updated_at=avail_orm.updated_at,
        )

    async def save(self, profile: AvailabilityProfile) -> AvailabilityProfile:
        stmt = select(AvailabilityORM).where(AvailabilityORM.user_id == profile.user_id)
        result = await self.session.execute(stmt)
        avail_orm = result.scalar_one_or_none()

        daily_quotas: dict[str, Any] = {}
        for day_name, day_schedule in profile.weekly_schedule.days.items():
            daily_quotas[day_name] = {
                "enabled": day_schedule.enabled,
                "quota_hours": day_schedule.quota_hours,
                "min_session_minutes": day_schedule.min_session_minutes,
                "preferred_period": day_schedule.preferred_period.value,
                "allowed_window": {
                    "start": day_schedule.allowed_window.start,
                    "end": day_schedule.allowed_window.end,
                },
            }

        if avail_orm is None:
            avail_orm = AvailabilityORM(
                id=profile.id,
                user_id=profile.user_id,
                mode=profile.mode.value,
                calendar_integration_mode=profile.calendar_integration_mode.value,
                daily_quotas=daily_quotas,
                min_session_minutes=profile.min_session_minutes,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
            self.session.add(avail_orm)
        else:
            avail_orm.mode = profile.mode.value
            avail_orm.calendar_integration_mode = profile.calendar_integration_mode.value
            avail_orm.daily_quotas = daily_quotas
            avail_orm.min_session_minutes = profile.min_session_minutes
            avail_orm.updated_at = profile.updated_at

        await self.session.flush()

        # Atomic replacement of availability_slots
        del_stmt = delete(AvailabilitySlotORM).where(
            AvailabilitySlotORM.availability_id == avail_orm.id
        )
        await self.session.execute(del_stmt)

        for day_name, day_schedule in profile.weekly_schedule.days.items():
            day_num = DAY_TO_INT[day_name]

            # 1. FIXED slots (Mode B)
            for slot in day_schedule.time_slots:
                slot_orm = AvailabilitySlotORM(
                    availability_id=avail_orm.id,
                    day_of_week=day_num,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    end_day_offset=slot.end_day_offset,
                    slot_type="FIXED",
                    is_active=day_schedule.enabled,
                    created_at=profile.created_at,
                    updated_at=profile.updated_at,
                )
                self.session.add(slot_orm)

            # 2. ALLOWED window (Mode A)
            s_t = parse_time_str(day_schedule.allowed_window.start)
            e_t = parse_time_str(day_schedule.allowed_window.end)
            allowed_orm = AvailabilitySlotORM(
                availability_id=avail_orm.id,
                day_of_week=day_num,
                start_time=s_t,
                end_time=e_t,
                end_day_offset=0,
                slot_type="ALLOWED",
                is_active=day_schedule.enabled,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
            self.session.add(allowed_orm)

        await self.session.flush()
        return profile
