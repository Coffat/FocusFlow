from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog

from src.account.public_api import (
    AvailabilityQueryPort,
    AvailabilitySnapshotDTO,
    CalendarBusyIntervalDTO,
    CalendarConnectionQueryPort,
)
from src.execution.public_api import (
    ExecutionScheduleSyncPort,
    ExistingScheduledTaskDTO,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    normalize_weekday_name,
    parse_hhmm_or_time,
    parse_iso_date,
    parse_iso_datetime,
)

logger = structlog.get_logger(__name__)

WEEKDAY_NAMES: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _minutes_to_hhmm(minutes: int) -> str:
    clamped = max(0, min(1439, minutes))
    return f"{clamped // 60:02d}:{clamped % 60:02d}"


def _parse_window_minutes(hhmm: str, default_minutes: int) -> int:
    if str(hhmm or "").strip() == "24:00":
        return 1440
    parsed = parse_hhmm_or_time(hhmm)
    if parsed is None:
        return default_minutes
    return parsed.hour * 60 + parsed.minute


def subtract_intervals_and_filter_fragments(
    base_intervals: Sequence[tuple[int, int]],
    busy_intervals: Sequence[tuple[int, int]],
    min_session_minutes: int = 30,
) -> list[tuple[int, int]]:
    """Subtract `busy_intervals` from `base_intervals` and discard fragments < `min_session_minutes`."""
    remaining: list[tuple[int, int]] = [(s, e) for s, e in base_intervals if e > s]
    for b_start, b_end in sorted(busy_intervals, key=lambda item: (item[0], item[1])):
        if b_end <= b_start:
            continue
        next_remaining: list[tuple[int, int]] = []
        for r_start, r_end in remaining:
            if b_end <= r_start or b_start >= r_end:
                next_remaining.append((r_start, r_end))
                continue
            if b_start > r_start:
                next_remaining.append((r_start, b_start))
            if b_end < r_end:
                next_remaining.append((b_end, r_end))
        remaining = next_remaining

    min_dur = max(1, int(min_session_minutes))
    return [(s, e) for s, e in remaining if (e - s) >= min_dur]


@dataclass(frozen=True, slots=True)
class EffectiveAvailabilityResultDTO:
    """Unified output of GetEffectiveAvailabilityUseCase (Phase B.1 — AC-02, AC-03, AC-04)."""

    availability_config: AvailabilityConfigurationDTO
    blocked_intervals: tuple[dict[str, Any], ...] = ()
    source_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    effective_existing_tasks: tuple[Any, ...] = ()


class GetEffectiveAvailabilityUseCase:
    """Resolve effective study availability from Manual Hybrid config vs. Google Calendar FreeBusy.

    Business Rules (AC-02, AC-03, AC-04, AC-05):
    - Case 1 (Manual Hybrid): `calendar_integration_mode != "CONNECTED"` and no active Google sync.
      Uses learner's `MODE_A` or `MODE_B` configuration minus committed `existing_tasks`.
    - Case 2 (Google Calendar Sync): `calendar_integration_mode == "CONNECTED"` or active Google connection.
      Fetches Google Calendar FreeBusy intervals, takes `[allowed_window_start, allowed_window_end]`
      (default `07:00-23:00`) on enabled weekdays as base slots, subtracts `busy_intervals` and committed
      `existing_tasks`, removes fragments `< min_session_minutes` (default 30m), and switches allocation
      to `MODE_B` (`FIXED_SLOTS`). Degrades gracefully to configured availability with explicit
      `google_sync_status="FAILED_OR_EXPIRED"` warning if Google Calendar fails or token is expired.
    - Case 3 (Unconfigured): No persisted availability profile and no active Google Calendar connection.
      Marks `source_type="UNCONFIGURED"` with an explicit warning for the UI.
    """

    def __init__(
        self,
        availability_query_port: AvailabilityQueryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
        execution_sync_port: ExecutionScheduleSyncPort | None = None,
    ) -> None:
        self._availability_port = availability_query_port
        self._calendar_port = calendar_connection_query_port
        self._execution_sync_port = execution_sync_port

    @staticmethod
    def _build_config_from_snapshot(
        avail_snapshot: AvailabilitySnapshotDTO | None,
        timezone: str,
        fallback: AvailabilityConfigurationDTO | None = None,
    ) -> AvailabilityConfigurationDTO:
        if avail_snapshot is None:
            if fallback is not None:
                return fallback
            return AvailabilityConfigurationDTO(
                mode="MODE_A",
                default_daily_quota_minutes=120,
                daily_quota_minutes=dict.fromkeys(WEEKDAY_NAMES, 120),
                availability_slots=(),
                disabled_weekdays=frozenset(),
                timezone=timezone,
            )

        raw_mode = str(avail_snapshot.mode or "MODE_A").upper()
        norm_mode = "MODE_B" if "B" in raw_mode or "SLOT" in raw_mode else "MODE_A"
        slot_dtos: list[AvailabilitySlotDTO] = []
        for s in getattr(avail_snapshot, "availability_slots", ()):
            if isinstance(s, dict):
                slot_dtos.append(
                    AvailabilitySlotDTO(
                        day_of_week=str(s.get("day_of_week", "monday")),
                        start_time=str(s.get("start_time", "19:00")),
                        end_time=str(s.get("end_time", "21:00")),
                        end_day_offset=int(s.get("end_day_offset", 0) or 0),
                        is_active=bool(s.get("is_active", True)),
                    )
                )
            elif isinstance(s, AvailabilitySlotDTO):
                slot_dtos.append(s)

        daily_cap = max(30, int(avail_snapshot.daily_cap_minutes or 120))
        quota_map: dict[str | int, int] = dict(
            getattr(avail_snapshot, "daily_quota_minutes", {}) or {}
        )

        disabled_days = frozenset(
            str(d) for d in (getattr(avail_snapshot, "disabled_weekdays", ()) or ())
        )
        return AvailabilityConfigurationDTO(
            mode=norm_mode,
            default_daily_quota_minutes=daily_cap,
            daily_quota_minutes=quota_map,
            availability_slots=tuple(slot_dtos),
            disabled_weekdays=disabled_days,
            timezone=timezone,
        )

    async def execute(
        self,
        *,
        user_id: UUID,
        start_date: date,
        target_date: date | None = None,
        timezone: str = "Asia/Ho_Chi_Minh",
        existing_tasks: Sequence[Any] | None = None,
        exclude_roadmap_id: UUID | None = None,
        fallback_availability: AvailabilityConfigurationDTO | None = None,
    ) -> EffectiveAvailabilityResultDTO:
        warnings: list[str] = []
        avail_snapshot: AvailabilitySnapshotDTO | None = None
        if self._availability_port is not None:
            try:
                avail_snapshot = await self._availability_port.get_active_availability(user_id)
            except Exception as exc:
                logger.warning(
                    "effective_availability_snapshot_fetch_error",
                    user_id=str(user_id),
                    error=str(exc),
                )

        if existing_tasks is None:
            if self._execution_sync_port is not None:
                try:
                    existing_tasks = await self._execution_sync_port.get_active_roadmaps_tasks(
                        user_id=user_id,
                        exclude_roadmap_id=exclude_roadmap_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "effective_availability_existing_tasks_fetch_error",
                        user_id=str(user_id),
                        error=str(exc),
                    )
                    existing_tasks = ()
            else:
                existing_tasks = ()

        committed_tasks = list(existing_tasks)
        conn_snapshot = None
        if self._calendar_port is not None:
            try:
                conn_snapshot = await self._calendar_port.get_connection_snapshot(
                    user_id=user_id,
                    provider="GOOGLE",
                )
            except Exception as exc:
                logger.warning(
                    "effective_availability_calendar_snapshot_error",
                    user_id=str(user_id),
                    error=str(exc),
                )

        base_config = self._build_config_from_snapshot(
            avail_snapshot=avail_snapshot,
            timezone=timezone,
            fallback=fallback_availability,
        )

        is_persisted = (
            bool(getattr(avail_snapshot, "is_persisted", True))
            if avail_snapshot is not None
            else False
        )
        cal_integration_mode = (
            str(getattr(avail_snapshot, "calendar_integration_mode", "NONE") or "NONE").upper()
            if avail_snapshot is not None
            else "NONE"
        )
        has_conn_record = conn_snapshot is not None and (
            conn_snapshot.is_active
            or str(conn_snapshot.sync_status or "").upper()
            in ("FAILED", "REVOKED", "TOKEN_EXPIRED", "ERROR")
        )
        wants_google_sync = cal_integration_mode == "CONNECTED" or has_conn_record

        blocked_records: list[dict[str, Any]] = []
        user_tz = ZoneInfo(timezone)

        for ext in committed_tasks:
            status = (
                str(ext.get("status", "TODO"))
                if isinstance(ext, dict)
                else str(getattr(ext, "status", "TODO"))
            ).upper()
            if status in ("CANCELLED", "COMPLETED"):
                continue
            ext_date = (
                parse_iso_date(ext.get("scheduled_date"))
                if isinstance(ext, dict)
                else parse_iso_date(getattr(ext, "scheduled_date", None))
            )
            ext_start = (
                parse_iso_datetime(ext.get("scheduled_start") or ext.get("planned_start_at"))
                if isinstance(ext, dict)
                else parse_iso_datetime(
                    getattr(ext, "scheduled_start", None) or getattr(ext, "planned_start_at", None)
                )
            )
            ext_end = (
                parse_iso_datetime(ext.get("scheduled_end") or ext.get("planned_end_at"))
                if isinstance(ext, dict)
                else parse_iso_datetime(
                    getattr(ext, "scheduled_end", None) or getattr(ext, "planned_end_at", None)
                )
            )
            ext_mins = (
                int(ext.get("estimated_minutes", 0) or 0)
                if isinstance(ext, dict)
                else int(getattr(ext, "estimated_minutes", 0) or 0)
            )
            blocked_records.append(
                {
                    "source": "ACTIVE_ROADMAP_TASK",
                    "date": ext_date.isoformat() if ext_date else None,
                    "start_time": ext_start.isoformat() if ext_start else None,
                    "end_time": ext_end.isoformat() if ext_end else None,
                    "duration_minutes": ext_mins,
                }
            )

        # Case 3: Neither manual availability nor Google Calendar is configured
        if not is_persisted and not wants_google_sync and fallback_availability is None:
            warnings.append(
                "Chưa cấu hình khung giờ rảnh hoặc kết nối Google Calendar. Hệ thống tạm dùng khung giờ mặc định."
            )
            return EffectiveAvailabilityResultDTO(
                availability_config=base_config,
                blocked_intervals=tuple(blocked_records),
                source_metadata={
                    "source_type": "UNCONFIGURED",
                    "calendar_connected": False,
                    "sync_freshness": None,
                    "busy_intervals_count": 0,
                    "google_sync_status": "NOT_CONNECTED",
                    "calendar_integration_mode": cal_integration_mode,
                },
                warnings=tuple(warnings),
                effective_existing_tasks=tuple(committed_tasks),
            )

        # Case 1: Manual Hybrid Mode (MODE_A or MODE_B)
        if not wants_google_sync:
            return EffectiveAvailabilityResultDTO(
                availability_config=base_config,
                blocked_intervals=tuple(blocked_records),
                source_metadata={
                    "source_type": "MANUAL_HYBRID",
                    "calendar_connected": False,
                    "sync_freshness": None,
                    "busy_intervals_count": 0,
                    "google_sync_status": "NOT_CONNECTED",
                    "calendar_integration_mode": cal_integration_mode,
                },
                warnings=tuple(warnings),
                effective_existing_tasks=tuple(committed_tasks),
            )

        # Case 2: Google Calendar Sync
        end_date = target_date if target_date is not None else (start_date + timedelta(days=29))
        if end_date < start_date:
            end_date = start_date

        conn_status_upper = (
            str(conn_snapshot.sync_status or "").upper() if conn_snapshot is not None else "MISSING"
        )
        conn_unhealthy = (
            self._calendar_port is None
            or conn_snapshot is None
            or not conn_snapshot.is_active
            or conn_status_upper in ("FAILED", "REVOKED", "TOKEN_EXPIRED", "DISCONNECTED", "ERROR")
        )

        busy_dtos: list[CalendarBusyIntervalDTO] = []
        google_sync_failed = conn_unhealthy

        if not conn_unhealthy and self._calendar_port is not None:
            time_min = datetime.combine(start_date, time(0, 0), tzinfo=user_tz).astimezone(UTC)
            time_max = datetime.combine(
                end_date + timedelta(days=1), time(0, 0), tzinfo=user_tz
            ).astimezone(UTC)
            try:
                busy_dtos = await self._calendar_port.get_free_busy_intervals(
                    user_id=user_id,
                    time_min=time_min,
                    time_max=time_max,
                    provider="GOOGLE",
                )
            except Exception as exc:
                logger.warning(
                    "effective_availability_google_freebusy_failed",
                    user_id=str(user_id),
                    error=str(exc),
                )
                google_sync_failed = True

        if google_sync_failed:
            sync_warning = (
                "Không thể đồng bộ Google Calendar (kết nối gián đoạn hoặc token hết hạn). "
                "Hệ thống tự động sử dụng khung giờ rảnh dự phòng."
            )
            warnings.append(sync_warning)
            return EffectiveAvailabilityResultDTO(
                availability_config=base_config,
                blocked_intervals=tuple(blocked_records),
                source_metadata={
                    "source_type": "MANUAL_HYBRID",
                    "calendar_connected": False,
                    "sync_freshness": conn_snapshot.last_synced_at if conn_snapshot else None,
                    "busy_intervals_count": 0,
                    "google_sync_status": "FAILED_OR_EXPIRED",
                    "calendar_integration_mode": cal_integration_mode,
                },
                warnings=tuple(warnings),
                effective_existing_tasks=tuple(committed_tasks),
            )

        # Build Mode B Fixed Slots from allowed_window minus Google busy_intervals & existing_tasks
        win_start_str = (
            getattr(avail_snapshot, "allowed_window_start", "07:00")
            if avail_snapshot is not None
            else "07:00"
        ) or "07:00"
        win_end_str = (
            getattr(avail_snapshot, "allowed_window_end", "23:00")
            if avail_snapshot is not None
            else "23:00"
        ) or "23:00"
        min_session_minutes = (
            int(getattr(avail_snapshot, "min_session_minutes", 30) or 30)
            if avail_snapshot is not None
            else 30
        )

        win_start_min = _parse_window_minutes(win_start_str, 7 * 60)
        win_end_min = _parse_window_minutes(win_end_str, 23 * 60)
        if str(win_end_str).strip() in ("00:00", "24:00") and win_start_min > 0:
            win_end_min = 1440
        if win_end_min <= win_start_min:
            win_start_min, win_end_min = 7 * 60, 23 * 60

        disabled_days_set = {
            norm for d in base_config.disabled_weekdays if (norm := normalize_weekday_name(d))
        }

        # Map busy intervals by date and weekday in user's timezone
        busy_by_date: dict[date, list[tuple[int, int]]] = {}
        busy_by_weekday: dict[str, list[tuple[int, int]]] = {}
        synthetic_busy_tasks: list[ExistingScheduledTaskDTO] = []

        for b_idx, interval in enumerate(busy_dtos):
            b_start_local = (
                interval.start_time.astimezone(user_tz)
                if interval.start_time.tzinfo is not None
                else interval.start_time.replace(tzinfo=UTC).astimezone(user_tz)
            )
            b_end_local = (
                interval.end_time.astimezone(user_tz)
                if interval.end_time.tzinfo is not None
                else interval.end_time.replace(tzinfo=UTC).astimezone(user_tz)
            )
            if b_end_local <= b_start_local:
                continue

            blocked_records.append(
                {
                    "source": "GOOGLE_CALENDAR_BUSY",
                    "date": b_start_local.date().isoformat(),
                    "start_time": b_start_local.isoformat(),
                    "end_time": b_end_local.isoformat(),
                    "duration_minutes": int((b_end_local - b_start_local).total_seconds() // 60),
                }
            )

            cur_day = b_start_local.date()
            last_day = b_end_local.date()
            while cur_day <= last_day:
                day_start_dt = datetime.combine(cur_day, time(0, 0), tzinfo=user_tz)
                day_end_dt = day_start_dt + timedelta(days=1)
                seg_start = max(b_start_local, day_start_dt)
                seg_end = min(b_end_local, day_end_dt)
                if seg_end > seg_start:
                    s_min = seg_start.hour * 60 + seg_start.minute
                    e_min = 1440 if seg_end == day_end_dt else seg_end.hour * 60 + seg_end.minute
                    clipped_s = max(win_start_min, s_min)
                    clipped_e = min(win_end_min, e_min)
                    if clipped_e > clipped_s:
                        busy_by_date.setdefault(cur_day, []).append((clipped_s, clipped_e))
                        wname = WEEKDAY_NAMES[cur_day.weekday()]
                        busy_by_weekday.setdefault(wname, []).append((clipped_s, clipped_e))
                        synthetic_busy_tasks.append(
                            ExistingScheduledTaskDTO(
                                task_id=UUID(int=(b_idx + 1)),
                                roadmap_id=UUID(int=0),
                                milestone_id=UUID(int=0),
                                title="Google Calendar Busy",
                                scheduled_date=cur_day,
                                scheduled_start=datetime.combine(
                                    cur_day,
                                    time(clipped_s // 60, clipped_s % 60),
                                    tzinfo=user_tz,
                                ),
                                scheduled_end=datetime.combine(
                                    cur_day,
                                    time((clipped_e // 60) % 24, clipped_e % 60),
                                    tzinfo=user_tz,
                                )
                                if clipped_e < 1440
                                else day_end_dt,
                                estimated_minutes=clipped_e - clipped_s,
                                status="TODO",
                                roadmap_target_date=start_date,
                            )
                        )
                cur_day += timedelta(days=1)

        # Also collect existing committed tasks with explicit time windows per weekday
        # (handling overnight / cross-midnight tasks and 24:00 end times cleanly).
        committed_by_weekday: dict[str, list[tuple[int, int]]] = {}
        committed_covered_weekdays: dict[int, set[str]] = {}
        for ext_idx, ext in enumerate(committed_tasks):
            status = (
                str(ext.get("status", "TODO"))
                if isinstance(ext, dict)
                else str(getattr(ext, "status", "TODO"))
            ).upper()
            if status in ("CANCELLED", "COMPLETED"):
                continue
            ext_date = (
                parse_iso_date(ext.get("scheduled_date"))
                if isinstance(ext, dict)
                else parse_iso_date(getattr(ext, "scheduled_date", None))
            )
            ext_start = (
                parse_iso_datetime(ext.get("scheduled_start") or ext.get("planned_start_at"))
                if isinstance(ext, dict)
                else parse_iso_datetime(
                    getattr(ext, "scheduled_start", None) or getattr(ext, "planned_start_at", None)
                )
            )
            ext_end = (
                parse_iso_datetime(ext.get("scheduled_end") or ext.get("planned_end_at"))
                if isinstance(ext, dict)
                else parse_iso_datetime(
                    getattr(ext, "scheduled_end", None) or getattr(ext, "planned_end_at", None)
                )
            )
            if ext_date is not None and ext_start is not None and ext_end is not None:
                loc_s = (
                    ext_start.astimezone(user_tz)
                    if ext_start.tzinfo is not None
                    else ext_start.replace(tzinfo=user_tz)
                )
                loc_e = (
                    ext_end.astimezone(user_tz)
                    if ext_end.tzinfo is not None
                    else ext_end.replace(tzinfo=user_tz)
                )
                if loc_e <= loc_s:
                    loc_e = loc_e + timedelta(days=1)
                cur_day = loc_s.date()
                last_day = loc_e.date()
                covered_days: set[str] = set()
                while cur_day <= last_day:
                    day_start_dt = datetime.combine(cur_day, time(0, 0), tzinfo=user_tz)
                    day_end_dt = day_start_dt + timedelta(days=1)
                    seg_start = max(loc_s, day_start_dt)
                    seg_end = min(loc_e, day_end_dt)
                    if seg_end > seg_start:
                        s_min = seg_start.hour * 60 + seg_start.minute
                        e_min = (
                            1440 if seg_end == day_end_dt else seg_end.hour * 60 + seg_end.minute
                        )
                        if e_min > s_min:
                            wname = WEEKDAY_NAMES[cur_day.weekday()]
                            committed_by_weekday.setdefault(wname, []).append((s_min, e_min))
                            covered_days.add(wname)
                    cur_day += timedelta(days=1)
                if covered_days:
                    committed_covered_weekdays[ext_idx] = covered_days

        # Count how many times each weekday occurs in [start_date, end_date]
        span_days = min(366, (end_date - start_date).days + 1)
        dates_by_weekday: dict[str, list[date]] = {w: [] for w in WEEKDAY_NAMES}
        for offset in range(span_days):
            d = start_date + timedelta(days=offset)
            dates_by_weekday[WEEKDAY_NAMES[d.weekday()]].append(d)

        derived_slots: list[AvailabilitySlotDTO] = []
        derived_quotas: dict[str | int, int] = {}
        unplaced_date_specific_busy: list[ExistingScheduledTaskDTO] = []
        carved_weekdays: set[str] = set()

        for wname in WEEKDAY_NAMES:
            if wname in disabled_days_set:
                derived_quotas[wname] = 0
                continue

            occurrences = dates_by_weekday.get(wname, [])
            if len(occurrences) <= 1:
                # Single occurrence of this weekday in range (or 0): subtract all busy & committed
                # intervals on this weekday directly from the allowed window!
                day_busy = [
                    *busy_by_weekday.get(wname, []),
                    *committed_by_weekday.get(wname, []),
                ]
                free_ranges = subtract_intervals_and_filter_fragments(
                    base_intervals=[(win_start_min, win_end_min)],
                    busy_intervals=day_busy,
                    min_session_minutes=min_session_minutes,
                )
                carved_weekdays.add(wname)
            else:
                # Multi-week range: NEVER subtract date-specific Google busy events or committed
                # tasks from the recurring weekly AvailabilitySlotDTO; emit them per-date instead.
                free_ranges = [(win_start_min, win_end_min)]
                for task_busy in synthetic_busy_tasks:
                    if (
                        task_busy.scheduled_date is not None
                        and WEEKDAY_NAMES[task_busy.scheduled_date.weekday()] == wname
                    ):
                        unplaced_date_specific_busy.append(task_busy)

            total_day_mins = 0
            for f_start, f_end in free_ranges:
                total_day_mins += f_end - f_start
                end_offset = 1 if f_end >= 1440 else 0
                end_hhmm = _minutes_to_hhmm(f_end % 1440) if end_offset else _minutes_to_hhmm(f_end)
                derived_slots.append(
                    AvailabilitySlotDTO(
                        day_of_week=wname,
                        start_time=_minutes_to_hhmm(f_start),
                        end_time=end_hhmm,
                        end_day_offset=end_offset,
                        is_active=True,
                    )
                )
            derived_quotas[wname] = total_day_mins

        google_config = AvailabilityConfigurationDTO(
            mode="MODE_B",
            default_daily_quota_minutes=max(derived_quotas.values(), default=0),
            daily_quota_minutes=derived_quotas,
            availability_slots=tuple(derived_slots),
            disabled_weekdays=base_config.disabled_weekdays,
            timezone=timezone,
        )

        # Keep ALL committed_tasks unless every day spanned by that task was carved into `derived_slots`.
        filtered_existing: list[Any] = []
        for ext_idx, ext in enumerate(committed_tasks):
            covered_task_days = committed_covered_weekdays.get(ext_idx)
            if covered_task_days and covered_task_days.issubset(carved_weekdays):
                continue
            filtered_existing.append(ext)

        effective_tasks = [*filtered_existing, *unplaced_date_specific_busy]

        return EffectiveAvailabilityResultDTO(
            availability_config=google_config,
            blocked_intervals=tuple(blocked_records),
            source_metadata={
                "source_type": "GOOGLE_CALENDAR",
                "calendar_connected": True,
                "sync_freshness": (
                    conn_snapshot.last_synced_at
                    if conn_snapshot and conn_snapshot.last_synced_at
                    else datetime.now(UTC).isoformat()
                ),
                "busy_intervals_count": len(busy_dtos),
                "google_sync_status": "CONNECTED",
                "calendar_integration_mode": "CONNECTED",
            },
            warnings=tuple(warnings),
            effective_existing_tasks=tuple(effective_tasks),
        )
