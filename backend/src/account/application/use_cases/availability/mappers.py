from src.account.application.dtos.availability import (
    AllowedWindowDTO,
    AvailabilityResponseDTO,
    DayScheduleDTO,
    TimeSlotDTO,
    WeeklyScheduleDTO,
)
from src.account.domain.exceptions.availability import (
    InvalidAllowedWindowException,
    InvalidPreferredPeriodException,
    InvalidTimeSlotException,
)
from src.account.domain.models.availability import (
    AllowedWindow,
    AvailabilityMode,
    AvailabilityProfile,
    DaySchedule,
    PreferredPeriod,
    TimeSlot,
    WeeklySchedule,
)

DAY_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def to_weekly_schedule_dto(weekly: WeeklySchedule) -> WeeklyScheduleDTO:
    day_dtos: dict[str, DayScheduleDTO] = {}
    for day_name in DAY_KEYS:
        day = weekly.days.get(
            day_name,
            DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        )
        time_slot_dtos = [
            TimeSlotDTO(
                start=slot.start_time.strftime("%H:%M"),
                end=slot.end_time.strftime("%H:%M"),
                end_day_offset=slot.end_day_offset,
            )
            for slot in day.time_slots
        ]
        allowed_window_dto = AllowedWindowDTO(
            start=day.allowed_window.start,
            end=day.allowed_window.end,
        )
        day_dtos[day_name] = DayScheduleDTO(
            enabled=day.enabled,
            quota_hours=day.quota_hours,
            time_slots=time_slot_dtos,
            allowed_window=allowed_window_dto,
            preferred_period=day.preferred_period.value,
            min_session_minutes=day.min_session_minutes,
        )
    return WeeklyScheduleDTO(**day_dtos)


def to_availability_response_dto(
    profile: AvailabilityProfile, is_lazy_default: bool = False
) -> AvailabilityResponseDTO:
    weekly_dto = to_weekly_schedule_dto(profile.weekly_schedule)
    total_hours = profile.weekly_schedule.calculate_total_weekly_hours(profile.mode)
    return AvailabilityResponseDTO(
        id=None if is_lazy_default else str(profile.id),
        user_id=str(profile.user_id),
        mode=profile.mode.value,
        calendar_integration_mode=profile.calendar_integration_mode.value,
        min_session_minutes=profile.min_session_minutes,
        weekly_schedule=weekly_dto,
        total_weekly_hours=total_hours,
        updated_at=profile.updated_at.isoformat(),
    )


def from_weekly_schedule_dto(
    dto: WeeklyScheduleDTO,
    target_mode: AvailabilityMode = AvailabilityMode.MODE_A,
    existing_profile: AvailabilityProfile | None = None,
    default_min_session_minutes: int = 30,
) -> WeeklySchedule:
    days: dict[str, DaySchedule] = {}
    for day_name in DAY_KEYS:
        day_dto: DayScheduleDTO = getattr(dto, day_name)
        is_weekend = day_name in ("saturday", "sunday")
        existing_day = (
            existing_profile.weekly_schedule.days.get(day_name)
            if existing_profile is not None
            else None
        )

        try:
            preferred = PreferredPeriod(day_dto.preferred_period)
        except ValueError as exc:
            raise InvalidPreferredPeriodException(
                preferred_period=day_dto.preferred_period,
                day=day_name,
            ) from exc

        default_slots = (
            (TimeSlot.from_str("14:00", "17:00"),)
            if is_weekend
            else (TimeSlot.from_str("19:30", "21:30"),)
        )
        fallback_slots = (
            existing_day.time_slots
            if (existing_day is not None and len(existing_day.time_slots) > 0)
            else default_slots
        )

        default_quota = 3.0 if is_weekend else 2.0
        fallback_quota = (
            existing_day.quota_hours
            if (existing_day is not None and 0.5 <= existing_day.quota_hours <= 14.0)
            else default_quota
        )

        fallback_window = (
            existing_day.allowed_window
            if existing_day is not None
            else AllowedWindow(start="07:00", end="23:00")
        )

        # 1. Parse time_slots (strict only when day is enabled and target_mode == MODE_B)
        if day_dto.enabled and target_mode == AvailabilityMode.MODE_B:
            slots = tuple(
                TimeSlot.from_str(
                    start=s.start,
                    end=s.end,
                    end_day_offset=s.end_day_offset,
                    day=day_name,
                )
                for s in day_dto.time_slots
            )
        else:
            if not day_dto.time_slots:
                slots = fallback_slots
            else:
                parsed_slots: list[TimeSlot] = []
                for s in day_dto.time_slots:
                    try:
                        parsed_slots.append(
                            TimeSlot.from_str(
                                start=s.start,
                                end=s.end,
                                end_day_offset=s.end_day_offset,
                                day=day_name,
                            )
                        )
                    except InvalidTimeSlotException:
                        continue
                slots = tuple(parsed_slots) if parsed_slots else fallback_slots

        # 2. Parse quota_hours (strict only when day is enabled and target_mode == MODE_A)
        if day_dto.enabled and target_mode == AvailabilityMode.MODE_A:
            quota_hours = day_dto.quota_hours
        else:
            if 0.5 <= day_dto.quota_hours <= 14.0:
                quota_hours = day_dto.quota_hours
            else:
                quota_hours = fallback_quota

        # 3. Parse allowed_window (strict only when day is enabled and target_mode == MODE_A)
        if day_dto.enabled and target_mode == AvailabilityMode.MODE_A:
            window = AllowedWindow(
                start=day_dto.allowed_window.start,
                end=day_dto.allowed_window.end,
            )
        else:
            try:
                window = AllowedWindow(
                    start=day_dto.allowed_window.start,
                    end=day_dto.allowed_window.end,
                )
            except InvalidAllowedWindowException:
                window = fallback_window

        # 4. Parse min_session_minutes
        if day_dto.enabled and target_mode == AvailabilityMode.MODE_A:
            day_min_session = day_dto.min_session_minutes
        else:
            if 15 <= day_dto.min_session_minutes <= 120:
                day_min_session = day_dto.min_session_minutes
            elif existing_day is not None and 15 <= existing_day.min_session_minutes <= 120:
                day_min_session = existing_day.min_session_minutes
            else:
                day_min_session = default_min_session_minutes

        days[day_name] = DaySchedule(
            enabled=day_dto.enabled,
            quota_hours=quota_hours,
            time_slots=slots,
            allowed_window=window,
            preferred_period=preferred,
            min_session_minutes=day_min_session,
        )
    return WeeklySchedule(days=days)
