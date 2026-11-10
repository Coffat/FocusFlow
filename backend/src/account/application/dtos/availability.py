from pydantic import BaseModel, Field


class TimeSlotDTO(BaseModel):
    start: str
    end: str
    end_day_offset: int = 0


class AllowedWindowDTO(BaseModel):
    start: str = "07:00"
    end: str = "23:00"


class DayScheduleDTO(BaseModel):
    enabled: bool
    quota_hours: float
    time_slots: list[TimeSlotDTO] = Field(default_factory=list)
    allowed_window: AllowedWindowDTO = Field(default_factory=AllowedWindowDTO)
    preferred_period: str = "ANY"
    min_session_minutes: int = 30


class WeeklyScheduleDTO(BaseModel):
    monday: DayScheduleDTO
    tuesday: DayScheduleDTO
    wednesday: DayScheduleDTO
    thursday: DayScheduleDTO
    friday: DayScheduleDTO
    saturday: DayScheduleDTO
    sunday: DayScheduleDTO


class UpdateAvailabilityRequestDTO(BaseModel):
    mode: str = "MODE_A"
    calendar_integration_mode: str = "NONE"
    min_session_minutes: int = 30
    weekly_schedule: WeeklyScheduleDTO


class AvailabilityResponseDTO(BaseModel):
    id: str | None = None
    user_id: str
    mode: str
    calendar_integration_mode: str
    min_session_minutes: int
    weekly_schedule: WeeklyScheduleDTO
    total_weekly_hours: float
    updated_at: str
