import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from src.planning.domain.services.validation_types import (
    AI_BLOCK_MAX_MINUTES,
    AI_BLOCK_MIN_MINUTES,
    MANUAL_BLOCK_MAX_MINUTES,
    MAX_DAILY_PLANNED_MINUTES,
    SOFT_OVERFLOW_MAX_MINUTES,
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    ConstraintViolationDTO,
    FeasibilityVerdict,
    NecessaryConditionCheckResult,
    NonSplittableSource,
    ScheduleAllocationResult,
    SoftOverflowWarningDTO,
    UnscheduledTaskDiagnosticDTO,
    normalize_weekday_name,
    parse_hhmm_or_time,
    parse_iso_date,
    parse_iso_datetime,
)


def _to_int(val: object, default: int = 0) -> int:
    if val is None:
        return default
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, (int, float)):
        return int(val)
    try:
        return int(str(val).strip())
    except ValueError:
        return default


def _in_user_timezone(value: datetime | None, timezone: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=ZoneInfo(timezone))
    return value.astimezone(ZoneInfo(timezone))


def _slot_minute_range(slot: AvailabilitySlotDTO) -> tuple[int, int]:
    s_t = parse_hhmm_or_time(slot.start_time)
    e_t = parse_hhmm_or_time(slot.end_time)
    if s_t is None or e_t is None:
        return 0, 0
    s_m = s_t.hour * 60 + s_t.minute
    e_m = e_t.hour * 60 + e_t.minute
    # Support cross-midnight slots (e.g. 23:00-01:00) via end_day_offset=1 or end_time <= start_time
    offset = 1 if (slot.end_day_offset == 1 or e_m <= s_m) else 0
    return s_m, e_m + offset * 1440


def _task_minute_range_on_base_date(
    base_date: date,
    start_dt: datetime | None,
    end_dt: datetime | None,
    start_t: time | None,
    end_t: time | None,
) -> tuple[int, int] | None:
    if start_dt is not None and end_dt is not None:
        s_day_diff = (start_dt.date() - base_date).days
        e_day_diff = (end_dt.date() - base_date).days
        s_m = s_day_diff * 1440 + start_dt.hour * 60 + start_dt.minute
        e_m = e_day_diff * 1440 + end_dt.hour * 60 + end_dt.minute
        if e_m <= s_m:
            e_m += 1440
        return s_m, e_m

    if start_t is not None and end_t is not None:
        s_m = start_t.hour * 60 + start_t.minute
        e_m = end_t.hour * 60 + end_t.minute
        if e_m <= s_m:
            e_m += 1440
        return s_m, e_m

    return None


def _record_occupied_interval(
    intervals_map: dict[date, list[tuple[int, int]]],
    used_map: dict[date, int],
    base_date: date,
    start_min: int,
    end_min: int,
) -> None:
    """Record `[start_min, end_min)` relative to `base_date`, splitting cross-midnight into `d+1`."""
    if end_min <= start_min:
        return
    cur_s = start_min
    while cur_s < end_min:
        day_offset = cur_s // 1440
        day_date = base_date + timedelta(days=day_offset)
        local_s = cur_s - day_offset * 1440
        local_e = min(1440, end_min - day_offset * 1440)
        if local_e > local_s:
            intervals_map.setdefault(day_date, []).append((local_s, local_e))
            used_map[day_date] = used_map.get(day_date, 0) + (local_e - local_s)
        cur_s = (day_offset + 1) * 1440


class NonSplittableTaskClassifier:
    """Deterministic classifier for tasks requiring a single contiguous study block."""

    _NON_SPLITTABLE_PATTERN: re.Pattern[str] = re.compile(
        r"(?:"
        r"\bmock\s+tests?\b"
        r"|\bmock\s+exams?\b"
        r"|\btimed\s+exams?\b"
        r"|\bpractice\s+exams?\b"
        r"|\bfull\s+tests?\b"
        r"|\bfinal\s+exams?\b"
        r"|\btimed\s+simulations?\b"
        r"|\bload\s+tests?(?:ing)?\b"
        r"|\bstress\s+tests?(?:ing)?\b"
        r"|\bbenchmark\s+(?:test|exam|evaluation|assessment)s?\b"
        r"|bài\s+thi\s+thử"
        r"|thi\s+thử"
        r"|đề\s+thi\s+đầy\s+đủ"
        r"|kiểm\s+thử\s+(?:chịu\s+)?tải"
        r"|tải\s+cao"
        r"|đối\s+chuẩn"
        r"|đánh\s+giá\s+tổng\s+hợp"
        r"|kiểm\s+tra\s+cuối"
        r"|mô\s+phỏng\s+phòng\s+thi"
        r"|điều\s+kiện\s+phòng\s+thi"
        r")",
        re.IGNORECASE,
    )

    _RETROSPECTIVE_OR_SETUP_RE: re.Pattern[str] = re.compile(
        r"(?:"
        r"phân\s+tích\s+kết\s+quả\s+(?:của\s+)?(?:(?:cả\s+hai|các)\s+)?(?:bài\s+)?(?:thi\s+thử|mock\s+(?:test|exam)s?)"
        r"|(?:review|analyze|summarise|summarize)\s+(?:the\s+)?(?:results?\s+of\s+)?(?:mock\s+(?:test|exam)s?|practice\s+exams?)"
        r")",
        re.IGNORECASE,
    )

    @classmethod
    def classify(cls, task: Mapping[str, Any]) -> tuple[bool, NonSplittableSource]:
        """Return `(is_non_splittable, provenance_source)` for a task payload."""
        explicit = task.get("is_non_splittable")
        if explicit is not None:
            return bool(explicit), "EXPLICIT_DTO"
        title = str(task.get("title") or "").strip()
        if title and cls._NON_SPLITTABLE_PATTERN.search(title):
            return True, "DETERMINISTIC_RULE"
        task_type = str(task.get("task_type") or "").strip().upper()
        if task_type in ("THEORY", "REVIEW"):
            return False, "DEFAULT_SPLITTABLE"
        secondary_text = " ".join(
            part
            for field in ("description", "completion_criteria", "learning_objective")
            if (part := str(task.get(field) or "").strip())
        )
        if secondary_text:
            cleaned_secondary = cls._RETROSPECTIVE_OR_SETUP_RE.sub(" ", secondary_text)
            if cls._NON_SPLITTABLE_PATTERN.search(cleaned_secondary):
                return True, "DETERMINISTIC_RULE"
        return False, "DEFAULT_SPLITTABLE"

    @classmethod
    def is_non_splittable(cls, task: Mapping[str, Any]) -> bool:
        """Return whether a task must be scheduled as a single contiguous block."""
        flagged, _ = cls.classify(task)
        return flagged


def _subtract_intervals(
    base_intervals: Sequence[tuple[int, int]],
    occupied: Sequence[tuple[int, int]],
    *,
    earliest_min: int = 0,
) -> list[tuple[int, int]]:
    """Subtract sorted occupied intervals and an earliest-minute bound from base intervals."""
    if not base_intervals:
        return []
    sorted_occ = sorted(
        ((s, e) for s, e in occupied if e > s),
        key=lambda iv: (iv[0], iv[1]),
    )
    free: list[tuple[int, int]] = []
    for base_s, base_e in base_intervals:
        cur_s = max(base_s, earliest_min)
        if cur_s >= base_e:
            continue
        for occ_s, occ_e in sorted_occ:
            if occ_e <= cur_s:
                continue
            if occ_s >= base_e:
                break
            if occ_s > cur_s:
                free.append((cur_s, occ_s))
            cur_s = max(cur_s, occ_e)
            if cur_s >= base_e:
                break
        if cur_s < base_e:
            free.append((cur_s, base_e))
    return free


def _choose_slot_chunk(
    *,
    rem_effort: int,
    window_width: int,
    preferred_session_minutes: int,
    allow_slot_sliver: bool = False,
    max_chunk: int | None = None,
) -> int | None:
    """Choose a slot-aware chunk size avoiding <30m task blocks and <30m stranded slot tails."""
    if rem_effort <= 0 or window_width <= 0:
        return None
    chunk_ceiling = (
        AI_BLOCK_MAX_MINUTES if max_chunk is None else min(AI_BLOCK_MAX_MINUTES, int(max_chunk))
    )

    def _valid_slot_tail(chunk: int) -> bool:
        tail = window_width - chunk
        return tail == 0 or tail >= AI_BLOCK_MIN_MINUTES

    if rem_effort < AI_BLOCK_MIN_MINUTES:
        if max_chunk is not None and rem_effort > int(max_chunk):
            return None
        if window_width >= rem_effort and (allow_slot_sliver or _valid_slot_tail(rem_effort)):
            return rem_effort
        return None

    # Whole-fit preference: place entire task remainder in 1 block when it fits (<= chunk_ceiling)
    # and does not strand a <30m physical slot tail (unless allow_slot_sliver is enabled).
    if (
        rem_effort <= chunk_ceiling
        and window_width >= rem_effort
        and (allow_slot_sliver or _valid_slot_tail(rem_effort))
    ):
        return rem_effort

    if window_width < AI_BLOCK_MIN_MINUTES or chunk_ceiling < AI_BLOCK_MIN_MINUTES:
        return None

    pref_bound = max(AI_BLOCK_MIN_MINUTES, min(chunk_ceiling, int(preferred_session_minutes)))
    pref_cap = min(window_width, pref_bound, chunk_ceiling, rem_effort)
    hard_cap = min(window_width, chunk_ceiling, rem_effort)

    def _valid_task_rem(chunk: int) -> bool:
        rem = rem_effort - chunk
        return rem == 0 or rem >= AI_BLOCK_MIN_MINUTES

    # 1. Respect preferred_session_minutes while leaving no <30m task remainder or slot tail.
    for chunk in range(pref_cap, AI_BLOCK_MIN_MINUTES - 1, -1):
        if _valid_task_rem(chunk) and _valid_slot_tail(chunk):
            return chunk

    # 2. Expand up to min(window_width, chunk_ceiling) if needed to keep both remainders >= 30m or 0.
    for chunk in range(hard_cap, pref_cap, -1):
        if _valid_task_rem(chunk) and _valid_slot_tail(chunk):
            return chunk

    # 3. Last resort (fallback pass only): preserve >=30m task remainder even if slot tail <30m.
    if allow_slot_sliver:
        for chunk in range(pref_cap, AI_BLOCK_MIN_MINUTES - 1, -1):
            if _valid_task_rem(chunk):
                return chunk
        for chunk in range(hard_cap, pref_cap, -1):
            if _valid_task_rem(chunk):
                return chunk

    return None


class SpatioTemporalRuleEngine:
    """Pure Python Tier 2 deterministic validator for Mode A, Mode B, Soft Overflow, and EDF conflicts."""

    @staticmethod
    def is_higher_or_equal_edf_priority(
        existing_target_date: date | None,
        current_target_date: date | None,
        existing_roadmap_id: UUID | None = None,
        current_roadmap_id: UUID | None = None,
    ) -> bool:
        """OS-04 Earliest Deadline First (EDF):
        Other ACTIVE roadmaps occupy slots/quota if their target_date is earlier than or equal
        to the current roadmap's target_date (or if existing tasks are already committed in an
        active schedule, BUSR-05 states new schedules only place into remaining free space; when
        two active roadmaps contend, earlier target_date wins).
        """
        if existing_target_date is None and current_target_date is None:
            return True
        if existing_target_date is not None and current_target_date is None:
            return True
        if existing_target_date is None and current_target_date is not None:
            return True
        assert existing_target_date is not None and current_target_date is not None
        if existing_target_date < current_target_date:
            return True
        if existing_target_date == current_target_date:
            if existing_roadmap_id is not None and current_roadmap_id is not None:
                return str(existing_roadmap_id) <= str(current_roadmap_id)
            return True
        # Even when current roadmap has an earlier target_date, existing active roadmap tasks
        # already occupy physical time; however if the caller checks EDF priority, we still flag
        # cross-roadmap conflict so no overbooking occurs.
        return True

    @classmethod
    def validate_mode_a_quota(
        cls,
        *,
        tasks: Sequence[dict[str, object]],
        availability: AvailabilityConfigurationDTO,
        existing_tasks: Sequence[object] = (),
        current_roadmap_target_date: date | None = None,
    ) -> list[ConstraintViolationDTO]:
        violations: list[ConstraintViolationDTO] = []

        # Group proposed tasks by scheduled_date, and collect timed intervals for cross-midnight overlap checks
        tasks_by_date: dict[date, list[tuple[int, dict[str, object]]]] = {}
        timed_proposed: list[tuple[int, dict[str, object], date, int, int]] = []
        for idx, raw_task in enumerate(tasks):
            sched_date = parse_iso_date(raw_task.get("scheduled_date"))
            start_dt = _in_user_timezone(
                parse_iso_datetime(raw_task.get("scheduled_start")), availability.timezone
            )
            end_dt = _in_user_timezone(
                parse_iso_datetime(raw_task.get("scheduled_end")), availability.timezone
            )
            if sched_date is None and start_dt is not None:
                sched_date = start_dt.date()
            if sched_date is None:
                continue
            tasks_by_date.setdefault(sched_date, []).append((idx, raw_task))
            if start_dt is not None and end_dt is not None:
                m_range = _task_minute_range_on_base_date(
                    sched_date,
                    start_dt,
                    end_dt,
                    parse_hhmm_or_time(start_dt),
                    parse_hhmm_or_time(end_dt),
                )
                if m_range is not None and m_range[1] > m_range[0]:
                    base_ord = sched_date.toordinal() * 1440
                    timed_proposed.append(
                        (idx, raw_task, sched_date, base_ord + m_range[0], base_ord + m_range[1])
                    )

        # Group existing active roadmap tasks by scheduled_date & collect timed intervals
        existing_minutes_by_date: dict[date, int] = {}
        existing_edf_by_date: dict[date, list[tuple[str, int, date | None]]] = {}
        existing_timed: list[tuple[str, int, int, date | None]] = []
        for ext in existing_tasks:
            status = str(getattr(ext, "status", "TODO")).upper()
            if status in ("CANCELLED", "COMPLETED"):
                continue
            ext_date = parse_iso_date(getattr(ext, "scheduled_date", None))
            ext_start_dt = _in_user_timezone(
                parse_iso_datetime(
                    getattr(ext, "planned_start_at", None) or getattr(ext, "scheduled_start", None)
                ),
                availability.timezone,
            )
            ext_end_dt = _in_user_timezone(
                parse_iso_datetime(
                    getattr(ext, "planned_end_at", None) or getattr(ext, "scheduled_end", None)
                ),
                availability.timezone,
            )
            if ext_date is None and ext_start_dt is not None:
                ext_date = ext_start_dt.date()
            if ext_date is None:
                continue
            ext_mins = int(getattr(ext, "estimated_minutes", 0) or 0)
            ext_title = str(getattr(ext, "title", "Existing Task"))
            ext_target = parse_iso_date(getattr(ext, "roadmap_target_date", None))
            existing_minutes_by_date[ext_date] = (
                existing_minutes_by_date.get(ext_date, 0) + ext_mins
            )
            existing_edf_by_date.setdefault(ext_date, []).append((ext_title, ext_mins, ext_target))
            if ext_start_dt is not None and ext_end_dt is not None:
                ext_range = _task_minute_range_on_base_date(
                    ext_date,
                    ext_start_dt,
                    ext_end_dt,
                    parse_hhmm_or_time(ext_start_dt),
                    parse_hhmm_or_time(ext_end_dt),
                )
                if ext_range is not None and ext_range[1] > ext_range[0]:
                    ext_ord = ext_date.toordinal() * 1440
                    existing_timed.append(
                        (ext_title, ext_ord + ext_range[0], ext_ord + ext_range[1], ext_target)
                    )

        # Timed self-overlap & EDF slot overlap across date boundaries (including cross-midnight)
        if timed_proposed:
            sorted_timed = sorted(timed_proposed, key=lambda e: (e[3], e[4]))
            for i in range(len(sorted_timed) - 1):
                idx1, task1, _, abs_s1, abs_e1 = sorted_timed[i]
                idx2, task2, d2, abs_s2, abs_e2 = sorted_timed[i + 1]
                if abs_s1 < abs_e2 and abs_s2 < abs_e1:
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=idx2,
                            field="scheduled_start",
                            rule_code="TASK_TIME_OVERLAP",
                            expected_bound=f"Không chồng lấn với nhiệm vụ #{idx1} ('{task1.get('title')}')",
                            actual_value=(
                                f"Nhiệm vụ #{idx1} và #{idx2} ('{task2.get('title')}') "
                                f"trùng giờ vào ngày {d2.isoformat()}"
                            ),
                            suggested_fix="Dời khung giờ bắt đầu của nhiệm vụ sau thời điểm kết thúc của nhiệm vụ trước.",
                        )
                    )
            for idx, raw_task, d, abs_s, abs_e in sorted_timed:
                for ext_title, occ_s, occ_e, ext_target in existing_timed:
                    if abs_s < occ_e and occ_s < abs_e:
                        edf_info = (
                            f" (EDF ưu tiên lộ trình có target_date={ext_target.isoformat()})"
                            if ext_target is not None
                            and (
                                current_roadmap_target_date is None
                                or ext_target <= current_roadmap_target_date
                            )
                            else ""
                        )
                        violations.append(
                            ConstraintViolationDTO(
                                task_index=idx,
                                field="scheduled_start",
                                rule_code="CROSS_ROADMAP_EDF_SLOT_CONFLICT",
                                expected_bound=f"Không trùng khung giờ đã xếp của lộ trình ACTIVE khác ('{ext_title}'){edf_info}",
                                actual_value=f"Nhiệm vụ '{raw_task.get('title')}' trùng khung giờ với '{ext_title}' vào ngày {d.isoformat()}",
                                suggested_fix="Chọn khung giờ rảnh khác hoặc chuyển sang ngày khác chưa bị lộ trình ưu tiên EDF chiếm.",
                            )
                        )

        for sched_date, day_items in sorted(tasks_by_date.items(), key=lambda x: x[0]):
            weekday_name = normalize_weekday_name(sched_date)
            weekday_idx = sched_date.weekday()

            if weekday_name in {d.lower() for d in availability.disabled_weekdays}:
                first_idx = day_items[0][0]
                violations.append(
                    ConstraintViolationDTO(
                        task_index=first_idx,
                        field="scheduled_date",
                        rule_code="DAY_DISABLED",
                        expected_bound="0 minutes (weekday disabled)",
                        actual_value=f"{sched_date.isoformat()} ({weekday_name})",
                        suggested_fix=f"Dời các nhiệm vụ ngày {sched_date.isoformat()} sang ngày học đang bật.",
                    )
                )
                continue

            quota_mins: int | None = None
            if weekday_name in availability.daily_quota_minutes:
                quota_mins = int(availability.daily_quota_minutes[weekday_name])
            elif weekday_idx in availability.daily_quota_minutes:
                quota_mins = int(availability.daily_quota_minutes[weekday_idx])
            elif str(weekday_idx) in availability.daily_quota_minutes:
                quota_mins = int(availability.daily_quota_minutes[str(weekday_idx)])
            else:
                quota_mins = int(availability.default_daily_quota_minutes)

            proposed_sum = sum(_to_int(item.get("estimated_minutes", 0)) for _, item in day_items)
            occupied_sum = existing_minutes_by_date.get(sched_date, 0)
            total_sum = proposed_sum + occupied_sum

            if total_sum > quota_mins:
                last_idx = day_items[-1][0]
                overflow = total_sum - quota_mins
                if occupied_sum > 0:
                    edf_notes = ", ".join(
                        f"'{t}' ({m}p, EDF target={td.isoformat() if td else 'N/A'})"
                        for t, m, td in existing_edf_by_date.get(sched_date, [])
                    )
                    rule_code = (
                        "CROSS_ROADMAP_EDF_QUOTA_CONFLICT"
                        if any(
                            td is not None
                            and (
                                current_roadmap_target_date is None
                                or td <= current_roadmap_target_date
                            )
                            for _, _, td in existing_edf_by_date.get(sched_date, [])
                        )
                        else "MODE_A_DAILY_QUOTA_EXCEEDED"
                    )
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=last_idx,
                            field="estimated_minutes",
                            rule_code=rule_code,
                            expected_bound=f"<= {quota_mins} phút/ngày (còn trống {max(0, quota_mins - occupied_sum)} phút)",
                            actual_value=f"{total_sum} phút (đề xuất {proposed_sum}p + lộ trình khác {occupied_sum}p: {edf_notes})",
                            suggested_fix=(
                                f"Giảm ít nhất {overflow} phút trong ngày {sched_date.isoformat()} hoặc dời nhiệm vụ sang ngày khác."
                            ),
                        )
                    )
                else:
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=last_idx,
                            field="estimated_minutes",
                            rule_code="MODE_A_DAILY_QUOTA_EXCEEDED",
                            expected_bound=f"<= {quota_mins} phút/ngày ({weekday_name})",
                            actual_value=f"{total_sum} phút vào ngày {sched_date.isoformat()}",
                            suggested_fix=(
                                f"Giảm ít nhất {overflow} phút trong ngày {sched_date.isoformat()} hoặc chia nhiệm vụ sang ngày khác."
                            ),
                        )
                    )

        return violations

    @classmethod
    def validate_mode_b_slots(
        cls,
        *,
        tasks: Sequence[dict[str, object]],
        availability: AvailabilityConfigurationDTO,
        existing_tasks: Sequence[object] = (),
        current_roadmap_target_date: date | None = None,
    ) -> tuple[list[ConstraintViolationDTO], list[SoftOverflowWarningDTO]]:
        violations: list[ConstraintViolationDTO] = []
        warnings: list[SoftOverflowWarningDTO] = []

        # Map active slots by weekday name ("monday".."sunday")
        slots_by_weekday: dict[str, list[tuple[int, int]]] = {}
        for slot in availability.availability_slots:
            if not slot.is_active:
                continue
            wname = normalize_weekday_name(slot.day_of_week)
            s_m, e_m = _slot_minute_range(slot)
            if e_m > s_m:
                slots_by_weekday.setdefault(wname, []).append((s_m, e_m))

        # Merge contiguous slots per weekday
        for wname, raw_ranges in list(slots_by_weekday.items()):
            sorted_r = sorted(raw_ranges, key=lambda r: r[0])
            merged: list[tuple[int, int]] = [sorted_r[0]]
            for cur_s, cur_e in sorted_r[1:]:
                prev_s, prev_e = merged[-1]
                if cur_s <= prev_e:
                    merged[-1] = (prev_s, max(prev_e, cur_e))
                else:
                    merged.append((cur_s, cur_e))
            slots_by_weekday[wname] = merged

        # Parse proposed tasks and assign each to its logical anchor date
        # (including cross-midnight tasks that start late on date D and end early on D+1)
        parsed_task_entries: list[tuple[int, dict[str, object], date, int, int, int]] = []
        for idx, raw_task in enumerate(tasks):
            est_mins = _to_int(raw_task.get("estimated_minutes", 0))
            sched_date = parse_iso_date(raw_task.get("scheduled_date"))
            start_dt = parse_iso_datetime(raw_task.get("scheduled_start"))
            end_dt = parse_iso_datetime(raw_task.get("scheduled_end"))
            start_dt = _in_user_timezone(start_dt, availability.timezone)
            end_dt = _in_user_timezone(end_dt, availability.timezone)
            start_t = parse_hhmm_or_time(start_dt or raw_task.get("start_time"))
            end_t = parse_hhmm_or_time(end_dt or raw_task.get("end_time"))

            if sched_date is None and start_dt is not None:
                sched_date = start_dt.date()

            if (
                sched_date is None
                or (start_dt is None and start_t is None)
                or (end_dt is None and end_t is None)
            ):
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="scheduled_start",
                        rule_code="MODE_B_MISSING_TIME_BOUNDS",
                        expected_bound="scheduled_date, scheduled_start, and scheduled_end required in Mode B",
                        actual_value=f"date={sched_date}, start={raw_task.get('scheduled_start')}, end={raw_task.get('scheduled_end')}",
                        suggested_fix="Cung cấp đầy đủ scheduled_date, scheduled_start và scheduled_end cho từng nhiệm vụ trong Mode B.",
                    )
                )
                continue

            m_range = _task_minute_range_on_base_date(sched_date, start_dt, end_dt, start_t, end_t)
            if m_range is None:
                continue
            t_s, t_e = m_range
            actual_duration = t_e - t_s
            if actual_duration <= 0:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="scheduled_end",
                        rule_code="INVALID_TASK_TIME_ORDER",
                        expected_bound="scheduled_end > scheduled_start",
                        actual_value=f"{actual_duration} phút",
                        suggested_fix="Chỉnh lại giờ kết thúc lớn hơn giờ bắt đầu.",
                    )
                )
                continue

            if abs(actual_duration - est_mins) > 1:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="estimated_minutes",
                        rule_code="MODE_B_DURATION_MISMATCH",
                        expected_bound=f"estimated_minutes == (scheduled_end - scheduled_start) ({actual_duration} phút)",
                        actual_value=f"estimated_minutes={est_mins} phút nhưng khoảng giờ là {actual_duration} phút",
                        suggested_fix=f"Đồng bộ estimated_minutes={actual_duration} hoặc điều chỉnh scheduled_end khớp với {est_mins} phút.",
                    )
                )

            parsed_task_entries.append((idx, raw_task, sched_date, t_s, t_e, est_mins))

        # Group proposed tasks by scheduled_date
        by_date: dict[date, list[tuple[int, dict[str, object], date, int, int, int]]] = {}
        for entry in parsed_task_entries:
            by_date.setdefault(entry[2], []).append(entry)

        # Group existing active tasks globally by absolute minute intervals for cross-midnight overlap checks (OS-04)
        existing_abs_entries: list[tuple[str, int, int, date | None]] = []
        for ext in existing_tasks:
            status = str(getattr(ext, "status", "TODO")).upper()
            if status in ("CANCELLED", "COMPLETED"):
                continue
            ext_date = parse_iso_date(getattr(ext, "scheduled_date", None))
            ext_start_dt = parse_iso_datetime(
                getattr(ext, "planned_start_at", None) or getattr(ext, "scheduled_start", None)
            )
            ext_end_dt = parse_iso_datetime(
                getattr(ext, "planned_end_at", None) or getattr(ext, "scheduled_end", None)
            )
            ext_start_dt = _in_user_timezone(ext_start_dt, availability.timezone)
            ext_end_dt = _in_user_timezone(ext_end_dt, availability.timezone)
            ext_start_t = parse_hhmm_or_time(ext_start_dt)
            ext_end_t = parse_hhmm_or_time(ext_end_dt)
            if ext_date is None and ext_start_dt is not None:
                ext_date = ext_start_dt.date()
            if ext_date is None:
                continue
            ext_range = _task_minute_range_on_base_date(
                ext_date, ext_start_dt, ext_end_dt, ext_start_t, ext_end_t
            )
            if ext_range is None:
                continue
            ext_title = str(getattr(ext, "title", "Existing Task"))
            ext_target = parse_iso_date(getattr(ext, "roadmap_target_date", None))
            ext_ord = ext_date.toordinal() * 1440
            existing_abs_entries.append(
                (ext_title, ext_ord + ext_range[0], ext_ord + ext_range[1], ext_target)
            )

        # 1. Global self-overlap check across date boundaries (including cross-midnight)
        global_sorted_entries = sorted(
            parsed_task_entries,
            key=lambda e: (e[2].toordinal() * 1440 + e[3], e[2].toordinal() * 1440 + e[4]),
        )
        for i in range(len(global_sorted_entries) - 1):
            idx1, task1, d1, s1, e1, _ = global_sorted_entries[i]
            idx2, task2, d2, s2, e2, _ = global_sorted_entries[i + 1]
            abs_s1 = d1.toordinal() * 1440 + s1
            abs_e1 = d1.toordinal() * 1440 + e1
            abs_s2 = d2.toordinal() * 1440 + s2
            abs_e2 = d2.toordinal() * 1440 + e2
            if abs_s1 < abs_e2 and abs_s2 < abs_e1:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx2,
                        field="scheduled_start",
                        rule_code="TASK_TIME_OVERLAP",
                        expected_bound=f"Không chồng lấn với nhiệm vụ #{idx1} ('{task1.get('title')}')",
                        actual_value=f"Nhiệm vụ #{idx1} và #{idx2} ('{task2.get('title')}') trùng giờ trong ngày {d2.isoformat()}",
                        suggested_fix="Dời khung giờ bắt đầu của nhiệm vụ sau thời điểm kết thúc của nhiệm vụ trước.",
                    )
                )

        # 2. Global Cross-Roadmap EDF overlap check across date boundaries (including cross-midnight)
        for idx, raw_task, sched_date, t_s, t_e, _ in global_sorted_entries:
            abs_s = sched_date.toordinal() * 1440 + t_s
            abs_e = sched_date.toordinal() * 1440 + t_e
            for ext_title, occ_s, occ_e, ext_target in existing_abs_entries:
                if abs_s < occ_e and occ_s < abs_e:
                    edf_info = (
                        f" (EDF ưu tiên lộ trình có target_date={ext_target.isoformat()})"
                        if ext_target is not None
                        and (
                            current_roadmap_target_date is None
                            or ext_target <= current_roadmap_target_date
                        )
                        else ""
                    )
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=idx,
                            field="scheduled_start",
                            rule_code="CROSS_ROADMAP_EDF_SLOT_CONFLICT",
                            expected_bound=f"Không trùng khung giờ đã xếp của lộ trình ACTIVE khác ('{ext_title}'){edf_info}",
                            actual_value=f"Nhiệm vụ '{raw_task.get('title')}' trùng khung giờ với '{ext_title}' vào ngày {sched_date.isoformat()}",
                            suggested_fix="Chọn khung giờ rảnh khác trong ngày hoặc chuyển sang ngày khác chưa bị lộ trình ưu tiên EDF chiếm.",
                        )
                    )

        for sched_date, entries in sorted(by_date.items(), key=lambda x: x[0]):
            sorted_entries = sorted(entries, key=lambda e: (e[3], e[4]))
            weekday_name = normalize_weekday_name(sched_date)
            day_slots = slots_by_weekday.get(weekday_name, [])

            # Also check if a task starting early in the morning (e.g. 00:15) belongs to previous day's cross-midnight slot
            prev_date = sched_date - timedelta(days=1)
            prev_weekday = normalize_weekday_name(prev_date)
            prev_day_cross_slots = [
                (s_m - 1440, e_m - 1440)
                for s_m, e_m in slots_by_weekday.get(prev_weekday, [])
                if e_m > 1440
            ]
            effective_slots = sorted([*prev_day_cross_slots, *day_slots], key=lambda r: r[0])

            # 3. Check each task against availability slots & Soft Overflow rule (BUSR-04)
            if not effective_slots:
                for idx, raw_task, _, _, _, _ in sorted_entries:
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=idx,
                            field="scheduled_date",
                            rule_code="NO_AVAILABILITY_SLOT_FOR_DAY",
                            expected_bound=f"Ngày có khung giờ rảnh (Mode B) — {weekday_name} không có slot",
                            actual_value=f"{sched_date.isoformat()} ({weekday_name})",
                            suggested_fix=f"Dời nhiệm vụ '{raw_task.get('title')}' sang ngày có cấu hình khung giờ rảnh.",
                        )
                    )
                continue

            last_entry_idx_on_day = sorted_entries[-1][0]
            for pos, (idx, raw_task, _, t_s, t_e, _) in enumerate(sorted_entries):
                is_last_task_of_day = (
                    pos == (len(sorted_entries) - 1) or idx == last_entry_idx_on_day
                )
                title_str = str(raw_task.get("title", f"Task #{idx}"))

                matched_exact = False
                matched_soft_overflow = 0
                hard_overflow_amount = 0

                for slot_s, slot_e in effective_slots:
                    if slot_s <= t_s and t_e <= slot_e:
                        matched_exact = True
                        break
                    if slot_s <= t_s < slot_e and t_e > slot_e:
                        overflow = t_e - slot_e
                        # Check if it collides with another proposed task after it
                        overlaps_next_task = any(
                            other_s < t_e
                            for other_idx, _, _, other_s, _, _ in sorted_entries
                            if other_idx != idx and other_s >= t_s
                        )
                        if (
                            0 < overflow <= SOFT_OVERFLOW_MAX_MINUTES
                            and is_last_task_of_day
                            and not overlaps_next_task
                        ):
                            matched_soft_overflow = overflow
                            break
                        hard_overflow_amount = max(hard_overflow_amount, overflow)

                if matched_exact:
                    continue

                if matched_soft_overflow > 0:
                    warnings.append(
                        SoftOverflowWarningDTO(
                            task_index=idx,
                            task_title=title_str,
                            scheduled_date=sched_date,
                            overflow_minutes=matched_soft_overflow,
                            message=(
                                f"Nhiệm vụ cuối ngày '{title_str}' ({sched_date.isoformat()}) "
                                f"tràn {matched_soft_overflow} phút sau mốc kết thúc khung giờ rảnh (<= 30 phút). "
                                "Cần xác nhận Soft Overflow trước khi Apply."
                            ),
                        )
                    )
                    continue

                slot_bounds_str = ", ".join(
                    f"{(s // 60) % 24:02d}:{s % 60:02d}-{(e // 60) % 24:02d}:{e % 60:02d}"
                    + (" (+1d)" if e >= 1440 else "")
                    for s, e in effective_slots
                )
                if hard_overflow_amount > SOFT_OVERFLOW_MAX_MINUTES:
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=idx,
                            field="scheduled_end",
                            rule_code="OVERFLOW_EXCEEDS_30M",
                            expected_bound=(
                                f"Tràn tối đa {SOFT_OVERFLOW_MAX_MINUTES} phút ở nhiệm vụ cuối ngày "
                                f"(khung rảnh: {slot_bounds_str})"
                            ),
                            actual_value=f"Tràn {hard_overflow_amount} phút vào ngày {sched_date.isoformat()}",
                            suggested_fix=(
                                f"Rút ngắn thời lượng nhiệm vụ '{title_str}' ít nhất "
                                f"{hard_overflow_amount - SOFT_OVERFLOW_MAX_MINUTES} phút hoặc chia nhỏ nhiệm vụ."
                            ),
                        )
                    )
                else:
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=idx,
                            field="scheduled_start",
                            rule_code="OUTSIDE_AVAILABILITY_SLOT",
                            expected_bound=f"Nằm gọn trong khung giờ rảnh Mode B ({slot_bounds_str})",
                            actual_value=(
                                f"Nhiệm vụ '{title_str}' [{(t_s // 60) % 24:02d}:{t_s % 60:02d}-"
                                f"{(t_e // 60) % 24:02d}:{t_e % 60:02d}] nằm ngoài slot"
                            ),
                            suggested_fix=f"Đặt giờ học của '{title_str}' nằm trong khung [{slot_bounds_str}].",
                        )
                    )

        return violations, warnings

    @staticmethod
    def _coalesce_adjacent_blocks(blocks: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge back-to-back same-day blocks of the same task up to 120m and renumber 1..m."""
        if not blocks:
            return []

        grouped: dict[str, list[dict[str, Any]]] = {}
        task_order: list[str] = []
        for raw_blk in blocks:
            blk = dict(raw_blk)
            tid = str(blk.get("task_id") or "")
            if tid not in grouped:
                grouped[tid] = []
                task_order.append(tid)
            grouped[tid].append(blk)

        coalesced_all: list[dict[str, Any]] = []
        for tid in task_order:
            raw_t_blocks = grouped[tid]
            if any(
                bool(blk.get("is_protected")) or bool(blk.get("_preserve_verbatim"))
                for blk in raw_t_blocks
            ):
                preserved = sorted(
                    (dict(blk) for blk in raw_t_blocks),
                    key=lambda b: (
                        _to_int(b.get("sequence_in_task"), 0),
                        str(b.get("block_date") or ""),
                        str(b.get("scheduled_start") or ""),
                    ),
                )
                coalesced_all.extend(preserved)
                continue
            t_blocks = sorted(
                raw_t_blocks,
                key=lambda b: (
                    str(b.get("block_date") or ""),
                    str(b.get("scheduled_start") or ""),
                    _to_int(b.get("sequence_in_task"), 0),
                ),
            )
            merged: list[dict[str, Any]] = []
            for blk in t_blocks:
                if not merged:
                    merged.append(dict(blk))
                    continue
                prev = merged[-1]
                prev_end = parse_iso_datetime(prev.get("scheduled_end"))
                curr_start = parse_iso_datetime(blk.get("scheduled_start"))
                prev_dur = _to_int(prev.get("scheduled_duration_minutes"), 0)
                curr_dur = _to_int(blk.get("scheduled_duration_minutes"), 0)
                if (
                    str(prev.get("block_date") or "") == str(blk.get("block_date") or "")
                    and prev_end is not None
                    and curr_start is not None
                    and prev_end == curr_start
                    and prev_dur + curr_dur <= AI_BLOCK_MAX_MINUTES
                ):
                    prev["scheduled_end"] = blk["scheduled_end"]
                    prev["scheduled_duration_minutes"] = prev_dur + curr_dur
                else:
                    merged.append(dict(blk))
            for seq, blk in enumerate(merged, start=1):
                blk["sequence_in_task"] = seq
            coalesced_all.extend(merged)
        return coalesced_all

    @staticmethod
    def _extract_pinned_blocks_and_anchor(
        task: Mapping[str, Any],
        *,
        tid: str,
        effort: int,
        tz_name: str,
    ) -> tuple[list[tuple[date, int, int, int]], list[dict[str, Any]], tuple[date, int]]:
        """Extract per-day `(block_date, start_min, end_min, dur)`, block dicts, and end anchor."""
        user_tz = ZoneInfo(tz_name)
        raw_pinned = task.get("pinned_schedule_blocks")
        day_entries: list[tuple[date, int, int, int]] = []
        block_dicts: list[dict[str, Any]] = []
        end_anchor_date: date | None = None
        end_anchor_min = 0

        if isinstance(raw_pinned, Sequence) and not isinstance(raw_pinned, (str, bytes)):
            valid_pinned = [b for b in raw_pinned if isinstance(b, Mapping)]
            if valid_pinned:
                valid_pinned.sort(
                    key=lambda b: (
                        _to_int(b.get("sequence_in_task"), 0),
                        str(b.get("block_date") or ""),
                        str(b.get("scheduled_start") or ""),
                    )
                )
                for seq_idx, blk in enumerate(valid_pinned, start=1):
                    b_start = _in_user_timezone(
                        parse_iso_datetime(blk.get("scheduled_start")), tz_name
                    )
                    b_end = _in_user_timezone(parse_iso_datetime(blk.get("scheduled_end")), tz_name)
                    b_date = parse_iso_date(blk.get("block_date"))
                    if b_date is None and b_start is not None:
                        b_date = b_start.date()
                    if b_date is None:
                        continue
                    b_dur = _to_int(blk.get("scheduled_duration_minutes"), 0)
                    if b_start is not None and b_end is not None:
                        s_m = b_start.hour * 60 + b_start.minute
                        span_mins = max(1, int((b_end - b_start).total_seconds() // 60))
                        if b_dur <= 0:
                            b_dur = span_mins
                        e_m = s_m + max(b_dur, span_mins)
                        b_end_date = b_end.date()
                        b_end_min = b_end.hour * 60 + b_end.minute
                        start_iso = b_start.isoformat()
                        end_iso = b_end.isoformat()
                    else:
                        b_dur = max(1, b_dur or effort)
                        s_m = 19 * 60
                        e_m = s_m + b_dur
                        b_end_date = b_date + timedelta(days=e_m // 1440)
                        b_end_min = e_m % 1440 if e_m >= 1440 else e_m
                        start_iso = datetime.combine(
                            b_date, time(19, 0), tzinfo=user_tz
                        ).isoformat()
                        end_iso = datetime.combine(
                            b_end_date, time((e_m % 1440) // 60, e_m % 60), tzinfo=user_tz
                        ).isoformat()
                    day_entries.append((b_date, s_m, e_m, max(1, b_dur)))
                    blk_copy: dict[str, Any] = {
                        "task_id": tid,
                        "sequence_in_task": _to_int(blk.get("sequence_in_task"), seq_idx),
                        "block_date": b_date.isoformat(),
                        "scheduled_start": start_iso,
                        "scheduled_end": end_iso,
                        "scheduled_duration_minutes": max(1, b_dur),
                        "_preserve_verbatim": True,
                    }
                    if blk.get("is_protected") is not None:
                        blk_copy["is_protected"] = bool(blk.get("is_protected"))
                    block_dicts.append(blk_copy)
                    if end_anchor_date is None or (b_end_date, b_end_min) > (
                        end_anchor_date,
                        end_anchor_min,
                    ):
                        end_anchor_date = b_end_date
                        end_anchor_min = b_end_min
                if day_entries and end_anchor_date is not None:
                    return day_entries, block_dicts, (end_anchor_date, end_anchor_min)

        s_date = parse_iso_date(task.get("scheduled_date"))
        assert s_date is not None
        dur = max(1, effort)
        st_dt = _in_user_timezone(parse_iso_datetime(task.get("scheduled_start")), tz_name)
        en_dt = _in_user_timezone(parse_iso_datetime(task.get("scheduled_end")), tz_name)
        if st_dt is not None and en_dt is not None:
            s_m = st_dt.hour * 60 + st_dt.minute
            span_mins = max(dur, int((en_dt - st_dt).total_seconds() // 60))
            e_m = s_m + span_mins
            end_d = en_dt.date()
            end_m = en_dt.hour * 60 + en_dt.minute
            start_iso = st_dt.isoformat()
            end_iso = en_dt.isoformat()
        else:
            s_m = 19 * 60
            e_m = s_m + dur
            end_d = s_date + timedelta(days=e_m // 1440)
            end_m = e_m % 1440 if e_m >= 1440 else e_m
            start_iso = datetime.combine(s_date, time(19, 0), tzinfo=user_tz).isoformat()
            end_iso = datetime.combine(
                end_d, time((e_m % 1440) // 60, e_m % 60), tzinfo=user_tz
            ).isoformat()

        day_entries.append((s_date, s_m, e_m, dur))
        block_dicts.append(
            {
                "task_id": tid,
                "sequence_in_task": 1,
                "block_date": s_date.isoformat(),
                "scheduled_start": start_iso,
                "scheduled_end": end_iso,
                "scheduled_duration_minutes": dur,
            }
        )
        return day_entries, block_dicts, (end_d, end_m)

    @staticmethod
    def _finalize_allocation_output(
        tasks: Sequence[dict[str, Any]],
        blocks: Sequence[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        clean_tasks = [{k: v for k, v in t.items() if k != "pinned_schedule_blocks"} for t in tasks]
        clean_blocks = [{k: v for k, v in b.items() if not k.startswith("_")} for b in blocks]
        return clean_tasks, clean_blocks

    @classmethod
    def _build_calendar_context(
        cls,
        availability: AvailabilityConfigurationDTO,
        *,
        existing_tasks: Sequence[Any] | None = None,
        daily_workload_cap_minutes: int | None = None,
    ) -> dict[str, Any]:
        weekday_names = (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
        disabled_days: set[str] = set()
        for raw_d in availability.disabled_weekdays:
            norm_d = normalize_weekday_name(raw_d)
            if norm_d:
                disabled_days.add(norm_d)

        quota_by_day: dict[str, int] = {}
        for k, v in availability.daily_quota_minutes.items():
            norm_k = normalize_weekday_name(k)
            if norm_k:
                quota_by_day[norm_k] = int(v)

        slots_by_day: dict[str, list[tuple[int, int]]] = {}
        for raw_slot in availability.availability_slots:
            if isinstance(raw_slot, AvailabilitySlotDTO):
                if not raw_slot.is_active:
                    continue
                s_day = normalize_weekday_name(raw_slot.day_of_week)
                s_start = parse_hhmm_or_time(raw_slot.start_time)
                s_end = parse_hhmm_or_time(raw_slot.end_time)
                end_offset = int(raw_slot.end_day_offset or 0)
            elif isinstance(raw_slot, dict):
                if raw_slot.get("is_active", True) is False:
                    continue
                s_day = normalize_weekday_name(raw_slot.get("day_of_week"))
                s_start = parse_hhmm_or_time(raw_slot.get("start_time"))
                s_end = parse_hhmm_or_time(raw_slot.get("end_time"))
                end_offset = _to_int(raw_slot.get("end_day_offset"), 0)
            else:
                continue
            if not s_day or s_start is None or s_end is None:
                continue
            start_min = s_start.hour * 60 + s_start.minute
            end_min = s_end.hour * 60 + s_end.minute
            if end_offset == 1 or end_min <= start_min:
                end_min += 1440
            slots_by_day.setdefault(s_day, []).append((start_min, end_min))

        for d_key, raw_intervals in list(slots_by_day.items()):
            sorted_iv = sorted(raw_intervals, key=lambda x: (x[0], x[1]))
            merged: list[tuple[int, int]] = []
            for iv_s, iv_e in sorted_iv:
                if merged and iv_s <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], iv_e))
                else:
                    merged.append((iv_s, iv_e))
            slots_by_day[d_key] = merged

        existing_used: dict[date, int] = {}
        existing_intervals: dict[date, list[tuple[int, int]]] = {}
        for ex in existing_tasks or ():
            status = (
                str(ex.get("status", "TODO"))
                if isinstance(ex, dict)
                else str(getattr(ex, "status", "TODO"))
            ).upper()
            if status in ("CANCELLED", "COMPLETED"):
                continue
            if isinstance(ex, dict):
                ex_date = parse_iso_date(ex.get("scheduled_date"))
                ex_mins = _to_int(ex.get("estimated_minutes"), 0)
                ex_start = parse_iso_datetime(
                    ex.get("planned_start_at") or ex.get("scheduled_start")
                )
                ex_end = parse_iso_datetime(ex.get("planned_end_at") or ex.get("scheduled_end"))
            else:
                ex_date = parse_iso_date(getattr(ex, "scheduled_date", None))
                ex_mins = _to_int(getattr(ex, "estimated_minutes", 0), 0)
                ex_start = parse_iso_datetime(
                    getattr(ex, "planned_start_at", None) or getattr(ex, "scheduled_start", None)
                )
                ex_end = parse_iso_datetime(
                    getattr(ex, "planned_end_at", None) or getattr(ex, "scheduled_end", None)
                )

            ex_start = _in_user_timezone(ex_start, availability.timezone)
            ex_end = _in_user_timezone(ex_end, availability.timezone)

            if ex_start is not None and ex_end is not None:
                base_d = ex_start.date()
                s_m = ex_start.hour * 60 + ex_start.minute
                span_m = int((ex_end - ex_start).total_seconds() // 60)
                e_m = s_m + max(ex_mins, span_m)
                if e_m > s_m:
                    _record_occupied_interval(
                        existing_intervals,
                        existing_used,
                        base_d,
                        s_m,
                        e_m,
                    )
            elif ex_date is not None and ex_mins > 0:
                existing_used[ex_date] = existing_used.get(ex_date, 0) + ex_mins

        mode_upper = (availability.mode or "QUOTA").strip().upper()
        cap_ceiling = (
            min(MAX_DAILY_PLANNED_MINUTES, max(10, int(daily_workload_cap_minutes)))
            if daily_workload_cap_minutes is not None
            else MAX_DAILY_PLANNED_MINUTES
        )
        return {
            "weekday_names": weekday_names,
            "disabled_days": disabled_days,
            "quota_by_day": quota_by_day,
            "slots_by_day": slots_by_day,
            "existing_used": existing_used,
            "existing_intervals": existing_intervals,
            "mode_b": mode_upper in ("FIXED_SLOTS", "MODE_B", "SLOTS"),
            "cap_ceiling": cap_ceiling,
            "default_quota": int(availability.default_daily_quota_minutes),
            "timezone": availability.timezone,
        }

    @staticmethod
    def _day_free_windows(
        ctx: dict[str, Any],
        cand_date: date,
        *,
        earliest_min: int,
        used_today: int,
        occupied: Sequence[tuple[int, int]],
        next_day_occupied: Sequence[tuple[int, int]] = (),
    ) -> tuple[list[tuple[int, int]], int, int]:
        """Return `(free_intervals, rem_day_cap, raw_day_cap)` for `cand_date`."""
        wname = ctx["weekday_names"][cand_date.weekday()]
        if wname in ctx["disabled_days"]:
            return [], 0, 0

        cap_ceiling: int = ctx["cap_ceiling"]
        if ctx["mode_b"]:
            day_slots: list[tuple[int, int]] = list(ctx["slots_by_day"].get(wname, []))
            prev_wname = ctx["weekday_names"][(cand_date - timedelta(days=1)).weekday()]
            if prev_wname not in ctx["disabled_days"]:
                prev_cross = [
                    (max(0, s_m - 1440), e_m - 1440)
                    for s_m, e_m in ctx["slots_by_day"].get(prev_wname, [])
                    if e_m > 1440
                ]
                if prev_cross:
                    day_slots.extend(prev_cross)
            if not day_slots:
                return [], 0, 0
            day_slots.sort(key=lambda r: (r[0], r[1]))
            merged_slots: list[tuple[int, int]] = [day_slots[0]]
            for cur_s, cur_e in day_slots[1:]:
                prev_s, prev_e = merged_slots[-1]
                if cur_s <= prev_e:
                    merged_slots[-1] = (prev_s, max(prev_e, cur_e))
                else:
                    merged_slots.append((cur_s, cur_e))
            raw_day_cap = min(cap_ceiling, sum(max(0, e - s) for s, e in merged_slots))
            rem_day_cap = max(0, raw_day_cap - used_today)
            if rem_day_cap <= 0:
                return [], 0, raw_day_cap
            combined_occ = list(occupied)
            if next_day_occupied and any(e > 1440 for _, e in merged_slots):
                combined_occ.extend((s + 1440, e + 1440) for s, e in next_day_occupied if s < 1440)
            free = [
                (s, e)
                for s, e in _subtract_intervals(
                    merged_slots, combined_occ, earliest_min=earliest_min
                )
                if s < 1440
            ]
            return free, rem_day_cap, raw_day_cap

        day_quota: int = min(
            cap_ceiling,
            ctx["quota_by_day"].get(wname, ctx["default_quota"]),
        )
        if day_quota <= 0:
            return [], 0, 0
        rem_day_cap = max(0, day_quota - used_today)
        if rem_day_cap <= 0:
            return [], 0, day_quota

        # Mode A prefers evening study (19:00-24:00) and falls back to daytime (09:00-19:00).
        evening_free = _subtract_intervals(
            [(19 * 60, 24 * 60)],
            occupied,
            earliest_min=earliest_min,
        )
        daytime_free = _subtract_intervals(
            [(9 * 60, 19 * 60)],
            occupied,
            earliest_min=earliest_min,
        )
        late_free = _subtract_intervals(
            [(0, 9 * 60)],
            occupied,
            earliest_min=earliest_min,
        )
        combined = [*evening_free, *daytime_free, *late_free]
        return combined, rem_day_cap, day_quota

    @staticmethod
    def _build_dag_graph(
        tasks: Sequence[dict[str, Any]],
        dependencies: Sequence[dict[str, Any]] | None,
    ) -> tuple[
        dict[str, int],
        dict[int, list[int]],
        dict[int, list[int]],
        bool,
    ]:
        id_to_idx: dict[str, int] = {}
        for idx, t in enumerate(tasks):
            tid = str(t.get("task_id") or t.get("id") or f"idx-{idx}")
            id_to_idx[tid] = idx

        preds: dict[int, list[int]] = {i: [] for i in range(len(tasks))}
        succs: dict[int, list[int]] = {i: [] for i in range(len(tasks))}
        seen_edges: set[tuple[int, int]] = set()
        has_self_loop = False

        for dep in dependencies or ():
            if not isinstance(dep, dict):
                continue
            if dep.get("is_mandatory", True) is False:
                continue
            p_id = str(dep.get("predecessor_id") or "")
            s_id = str(dep.get("successor_id") or "")
            p_idx = id_to_idx.get(p_id)
            s_idx = id_to_idx.get(s_id)
            if p_idx is None or s_idx is None:
                continue
            if p_idx == s_idx:
                has_self_loop = True
                continue
            if (p_idx, s_idx) not in seen_edges:
                seen_edges.add((p_idx, s_idx))
                preds[s_idx].append(p_idx)
                succs[p_idx].append(s_idx)

        in_deg = {i: len(preds[i]) for i in range(len(tasks))}
        queue = [i for i, d in in_deg.items() if d == 0]
        visited = 0
        while queue:
            cur = queue.pop(0)
            visited += 1
            for nxt in succs[cur]:
                in_deg[nxt] -= 1
                if in_deg[nxt] == 0:
                    queue.append(nxt)
        is_acyclic = (not has_self_loop) and (visited == len(tasks))
        return id_to_idx, preds, succs, is_acyclic

    @classmethod
    def verify_necessary_conditions(
        cls,
        tasks: Sequence[dict[str, Any]],
        availability: AvailabilityConfigurationDTO,
        *,
        start_date: date,
        target_date: date | None = None,
        dependencies: Sequence[dict[str, Any]] | None = None,
        existing_tasks: Sequence[Any] | None = None,
        daily_workload_cap_minutes: int | None = None,
        effective_efforts: Sequence[int] | None = None,
        classifications: Sequence[tuple[bool, NonSplittableSource]] | None = None,
    ) -> NecessaryConditionCheckResult:
        """Verify mathematical necessary conditions NC-1 (capacity), NC-2 (contiguous slot), and NC-3 (DAG critical path)."""
        ctx = cls._build_calendar_context(
            availability,
            existing_tasks=existing_tasks,
            daily_workload_cap_minutes=daily_workload_cap_minutes,
        )
        end_date = target_date if target_date is not None else (start_date + timedelta(days=365))
        if end_date < start_date:
            horizon_days: list[date] = []
        else:
            span = min(366, (end_date - start_date).days + 1)
            horizon_days = [start_date + timedelta(days=offset) for offset in range(span)]

        efforts = (
            list(effective_efforts)
            if effective_efforts is not None
            else [_to_int(t.get("estimated_minutes"), 0) for t in tasks]
        )
        cls_list = (
            list(classifications)
            if classifications is not None
            else [NonSplittableTaskClassifier.classify(t) for t in tasks]
        )

        # Seed already-scheduled tasks within `tasks` as occupied intervals
        seeded_used: dict[date, int] = dict(ctx["existing_used"])
        seeded_intervals: dict[date, list[tuple[int, int]]] = {
            d: list(ivs) for d, ivs in ctx["existing_intervals"].items()
        }
        already_scheduled_anchor: dict[int, tuple[date, int]] = {}
        unscheduled_indices: list[int] = []
        for idx, t in enumerate(tasks):
            s_date = parse_iso_date(t.get("scheduled_date"))
            if s_date is not None:
                tid = str(t.get("task_id") or t.get("id") or f"task_{idx}")
                day_entries, _, anchor = cls._extract_pinned_blocks_and_anchor(
                    t, tid=tid, effort=efforts[idx], tz_name=ctx["timezone"]
                )
                for b_date, s_m, e_m, dur in day_entries:
                    if e_m > s_m:
                        _record_occupied_interval(seeded_intervals, seeded_used, b_date, s_m, e_m)
                    else:
                        seeded_used[b_date] = seeded_used.get(b_date, 0) + dur
                already_scheduled_anchor[idx] = anchor
            elif efforts[idx] > 0:
                unscheduled_indices.append(idx)

        positive_efforts = [efforts[i] for i in unscheduled_indices if efforts[i] > 0]
        small_efforts = [e for e in positive_efforts if e < AI_BLOCK_MIN_MINUTES]
        large_efforts = [e for e in positive_efforts if e >= AI_BLOCK_MIN_MINUTES]
        small_total = sum(small_efforts)
        large_total = sum(large_efforts)
        small_min = min(small_efforts) if small_efforts else AI_BLOCK_MIN_MINUTES

        # Per-day packable capacity, raw capacity without existing, and max contiguous free window
        day_free_map: dict[date, list[tuple[int, int]]] = {}
        day_packable_map: dict[date, int] = {}
        day_packable_30_map: dict[date, int] = {}
        day_small_bonus_map: dict[date, int] = {}
        day_max_win_map: dict[date, int] = {}
        raw_cap_without_existing = 0
        last_horizon_day = horizon_days[-1] if horizon_days else None

        for d in horizon_days:
            free_ivs, rem_cap, raw_cap = cls._day_free_windows(
                ctx,
                d,
                earliest_min=0,
                used_today=seeded_used.get(d, 0),
                occupied=seeded_intervals.get(d, ()),
                next_day_occupied=seeded_intervals.get(d + timedelta(days=1), ()),
            )
            usable_30 = [(s, e) for s, e in free_ivs if (e - s) >= AI_BLOCK_MIN_MINUTES]
            usable_small_only = (
                [(s, e) for s, e in free_ivs if small_min <= (e - s) < AI_BLOCK_MIN_MINUTES]
                if small_efforts
                else []
            )
            usable_all = [*usable_30, *usable_small_only]
            day_free_map[d] = usable_30 if large_efforts else usable_all

            # Avoid double-counting cross-midnight tails when d+1 is also in horizon_days
            if d != last_horizon_day:
                phys_30 = sum(min(1440, e) - s for s, e in usable_30 if s < 1440)
                phys_small = sum(min(1440, e) - s for s, e in usable_small_only if s < 1440)
            else:
                phys_30 = sum(e - s for s, e in usable_30)
                phys_small = sum(e - s for s, e in usable_small_only)

            cap_30 = min(rem_cap, phys_30)
            cap_all = min(rem_cap, phys_30 + phys_small)
            day_packable_30_map[d] = cap_30
            day_small_bonus_map[d] = max(0, cap_all - cap_30)
            day_packable_map[d] = cap_30
            day_max_win_map[d] = min(
                rem_cap,
                max((e - s for s, e in usable_30), default=0)
                if large_efforts
                else max((e - s for s, e in usable_all), default=0),
            )
            if ctx["mode_b"] and d != last_horizon_day:
                # Count physical minutes on d without double-counting carryover already counted on d+1
                wname_d = ctx["weekday_names"][d.weekday()]
                if wname_d not in ctx["disabled_days"]:
                    prev_wname_d = ctx["weekday_names"][(d - timedelta(days=1)).weekday()]
                    prev_c = (
                        sum(
                            e_m - max(1440, s_m)
                            for s_m, e_m in ctx["slots_by_day"].get(prev_wname_d, [])
                            if e_m > 1440
                        )
                        if prev_wname_d not in ctx["disabled_days"]
                        else 0
                    )
                    own_phys = sum(
                        min(1440, e_m) - s_m
                        for s_m, e_m in ctx["slots_by_day"].get(wname_d, [])
                        if s_m < 1440
                    )
                    raw_cap_without_existing += min(ctx["cap_ceiling"], own_phys + prev_c)
            else:
                raw_cap_without_existing += raw_cap

        total_required = sum(efforts[i] for i in unscheduled_indices)
        total_packable_30 = sum(day_packable_30_map.values())
        total_small_bonus = min(small_total, sum(day_small_bonus_map.values()))
        total_packable = total_packable_30 + total_small_bonus
        global_max_win = max(day_max_win_map.values(), default=0)

        nc1_passed = (large_total <= total_packable_30) and (total_required <= total_packable)
        nc1_code = (
            "CALENDAR_CONFLICT_SATURATION"
            if (not nc1_passed and total_required <= raw_cap_without_existing)
            else "TOTAL_EFFORT_EXCEEDS_HARD_CAPACITY"
        )

        _, preds, succs, is_acyclic = cls._build_dag_graph(tasks, dependencies)

        # Compute ancestor sets for NC-2 earliest date lower bound and NC-3 cones
        ancestors_map: dict[int, set[int]] = {}
        descendants_map: dict[int, set[int]] = {}
        if is_acyclic:
            for i in range(len(tasks)):
                seen_anc: set[int] = set()
                stack = list(preds[i])
                while stack:
                    cur = stack.pop()
                    if cur not in seen_anc:
                        seen_anc.add(cur)
                        stack.extend(preds[cur])
                ancestors_map[i] = seen_anc

                seen_desc: set[int] = set()
                d_stack = list(succs[i])
                while d_stack:
                    cur = d_stack.pop()
                    if cur not in seen_desc:
                        seen_desc.add(cur)
                        d_stack.extend(succs[cur])
                descendants_map[i] = seen_desc

        # NC-2: each non-splittable task (and any task >=30m needing >=min_unit) must fit in some contiguous window >= its effort
        nc2_failed_tasks: dict[int, UnscheduledTaskDiagnosticDTO] = {}
        for i in unscheduled_indices:
            eff = efforts[i]
            is_ns, src = cls_list[i]
            if not is_ns:
                continue
            # Determine earliest date lower bound from already-scheduled ancestors
            earliest_d = start_date
            if is_acyclic:
                for anc in ancestors_map.get(i, ()):
                    if anc in already_scheduled_anchor:
                        anc_d, _ = already_scheduled_anchor[anc]
                        if anc_d > earliest_d:
                            earliest_d = anc_d
            max_win_after = max(
                (w for d, w in day_max_win_map.items() if d >= earliest_d),
                default=0,
            )
            if eff > max_win_after:
                tid = str(tasks[i].get("task_id") or tasks[i].get("id") or f"task_{i}")
                title = str(tasks[i].get("title") or tid)
                nc2_failed_tasks[i] = UnscheduledTaskDiagnosticDTO(
                    task_id=tid,
                    title=title,
                    estimated_minutes=eff,
                    is_non_splittable=is_ns,
                    non_splittable_source=src,
                    verdict="EXPLICIT_UNSCHEDULABLE",
                    reason_code="TASK_EXCEEDS_CONTINUOUS_SLOT",
                    message=(
                        f"Nhiệm vụ không thể tách '{title}' ({eff} phút) vượt quá khung giờ liên tục lớn nhất "
                        f"({max_win_after} phút)."
                    ),
                    earliest_feasible_date=earliest_d,
                    max_contiguous_window_minutes=max_win_after,
                    required_minutes=eff,
                )

        # NC-3: DAG Critical Path & Scheduled-Anchor Forward-Cone Lower Bound
        nc3_failed_tasks: dict[int, UnscheduledTaskDiagnosticDTO] = {}
        if is_acyclic and horizon_days:
            # 3a. Forward cone from already-scheduled tasks
            for s_idx, (s_date, s_end_min) in already_scheduled_anchor.items():
                unsched_desc = [
                    d_i for d_i in descendants_map.get(s_idx, ()) if d_i in unscheduled_indices
                ]
                if not unsched_desc:
                    continue
                cone_req = sum(efforts[d_i] for d_i in unsched_desc)
                desc_small_effs = [
                    efforts[d_i] for d_i in unsched_desc if 0 < efforts[d_i] < AI_BLOCK_MIN_MINUTES
                ]
                desc_small_total = sum(desc_small_effs)
                desc_small_min = min(desc_small_effs) if desc_small_effs else AI_BLOCK_MIN_MINUTES
                # Packable capacity on or after (s_date, s_end_min)
                cone_cap_30 = 0
                cone_small_bonus = 0
                for d in horizon_days:
                    if d < s_date:
                        continue
                    if d == s_date:
                        free_ivs, rem_cap, _ = cls._day_free_windows(
                            ctx,
                            d,
                            earliest_min=s_end_min,
                            used_today=seeded_used.get(d, 0),
                            occupied=seeded_intervals.get(d, ()),
                            next_day_occupied=seeded_intervals.get(d + timedelta(days=1), ()),
                        )
                        u30 = sum(
                            (min(1440, e) - s if d != last_horizon_day else e - s)
                            for s, e in free_ivs
                            if (e - s) >= AI_BLOCK_MIN_MINUTES
                            and (d == last_horizon_day or s < 1440)
                        )
                        usmall = (
                            sum(
                                (min(1440, e) - s if d != last_horizon_day else e - s)
                                for s, e in free_ivs
                                if desc_small_min <= (e - s) < AI_BLOCK_MIN_MINUTES
                                and (d == last_horizon_day or s < 1440)
                            )
                            if desc_small_effs
                            else 0
                        )
                        c30 = min(rem_cap, u30)
                        call = min(rem_cap, u30 + usmall)
                        cone_cap_30 += c30
                        cone_small_bonus += max(0, call - c30)
                    else:
                        cone_cap_30 += day_packable_30_map.get(d, 0)
                        cone_small_bonus += day_small_bonus_map.get(d, 0)
                cone_cap = cone_cap_30 + min(desc_small_total, cone_small_bonus)
                if cone_req > cone_cap:
                    for d_i in unsched_desc:
                        tid = str(
                            tasks[d_i].get("task_id") or tasks[d_i].get("id") or f"task_{d_i}"
                        )
                        is_ns, src = cls_list[d_i]
                        nc3_failed_tasks[d_i] = UnscheduledTaskDiagnosticDTO(
                            task_id=tid,
                            title=str(tasks[d_i].get("title") or tid),
                            estimated_minutes=efforts[d_i],
                            is_non_splittable=is_ns,
                            non_splittable_source=src,
                            verdict="EXPLICIT_UNSCHEDULABLE",
                            reason_code="CRITICAL_PATH_EXCEEDS_WINDOW",
                            message=(
                                f"Chuỗi phụ thuộc sau nhiệm vụ đã xếp lịch đòi hỏi {cone_req} phút "
                                f"nhưng chỉ còn {cone_cap} phút khả dụng tới hạn."
                            ),
                            earliest_feasible_date=s_date,
                            max_contiguous_window_minutes=global_max_win,
                            required_minutes=cone_req,
                        )

            # 3b. Earliest completion time of longest dependency chains alone in the horizon
            topo_order: list[int] = []
            in_deg = {i: len(preds[i]) for i in range(len(tasks))}
            q = [i for i, d in in_deg.items() if d == 0]
            while q:
                cur = q.pop(0)
                topo_order.append(cur)
                for nxt in succs[cur]:
                    in_deg[nxt] -= 1
                    if in_deg[nxt] == 0:
                        q.append(nxt)

            # Earliest (day_idx, minute) after finishing node `i` + chain daily minutes consumed
            earliest_finish: dict[int, tuple[int, int] | None] = {}
            chain_day_used: dict[int, dict[int, int]] = {}
            day_to_idx = {d: pos for pos, d in enumerate(horizon_days)}

            def _advance_single_task(
                task_idx: int,
                start_pos: int,
                start_min: int,
                base_chain_used: dict[int, int],
            ) -> tuple[tuple[int, int] | None, dict[int, int]]:
                eff = efforts[task_idx]
                cur_used = dict(base_chain_used)
                if eff <= 0:
                    return (start_pos, start_min), cur_used
                is_ns, _ = cls_list[task_idx]
                task_min_unit = min(AI_BLOCK_MIN_MINUTES, eff)
                rem = eff
                for pos in range(start_pos, len(horizon_days)):
                    d = horizon_days[pos]
                    e_min = start_min if pos == start_pos else 0
                    free_ivs, rem_cap, _ = cls._day_free_windows(
                        ctx,
                        d,
                        earliest_min=e_min,
                        used_today=seeded_used.get(d, 0) + cur_used.get(pos, 0),
                        occupied=seeded_intervals.get(d, ()),
                        next_day_occupied=seeded_intervals.get(d + timedelta(days=1), ()),
                    )
                    if rem_cap <= 0:
                        continue
                    day_budget = rem_cap
                    for iv_s, iv_e in free_ivs:
                        w = min(iv_e - iv_s, day_budget)
                        if is_ns:
                            if w >= rem:
                                end_m = iv_s + rem
                                day_part = min(1440, end_m) - iv_s
                                cur_used[pos] = cur_used.get(pos, 0) + day_part
                                if end_m > 1440:
                                    cur_used[pos + 1] = cur_used.get(pos + 1, 0) + (end_m - 1440)
                                    return (pos + 1, end_m - 1440), cur_used
                                return (pos, end_m), cur_used
                        else:
                            if w >= task_min_unit:
                                take = min(w, rem)
                                rem -= take
                                day_budget -= take
                                end_m = iv_s + take
                                day_part = min(1440, end_m) - iv_s
                                cur_used[pos] = cur_used.get(pos, 0) + day_part
                                if end_m > 1440:
                                    cur_used[pos + 1] = cur_used.get(pos + 1, 0) + (end_m - 1440)
                                if rem == 0:
                                    if end_m > 1440:
                                        return (pos + 1, end_m - 1440), cur_used
                                    return (pos, end_m), cur_used
                                if day_budget <= 0:
                                    break
                return None, cur_used

            for idx in topo_order:
                if idx in already_scheduled_anchor:
                    anc_d, anc_m = already_scheduled_anchor[idx]
                    chain_day_used[idx] = {}
                    if anc_d < horizon_days[0]:
                        earliest_finish[idx] = (0, 0)
                    else:
                        pos = day_to_idx.get(anc_d, len(horizon_days))
                        earliest_finish[idx] = (pos, anc_m)
                    continue
                cur_pos, cur_min = 0, 0
                best_pred_used: dict[int, int] = {}
                pred_impossible = False
                for p_idx in preds[idx]:
                    pf = earliest_finish.get(p_idx)
                    if pf is None:
                        pred_impossible = True
                        break
                    p_used = chain_day_used.get(p_idx, {})
                    if pf[0] > cur_pos or (pf[0] == cur_pos and pf[1] > cur_min):
                        cur_pos, cur_min = pf
                        best_pred_used = p_used
                    elif pf == (cur_pos, cur_min) and p_used.get(cur_pos, 0) > best_pred_used.get(
                        cur_pos, 0
                    ):
                        best_pred_used = p_used
                if pred_impossible:
                    earliest_finish[idx] = None
                    chain_day_used[idx] = {}
                    continue
                finish, new_chain_used = _advance_single_task(idx, cur_pos, cur_min, best_pred_used)
                earliest_finish[idx] = finish
                chain_day_used[idx] = new_chain_used
                if (
                    finish is None
                    and preds[idx]
                    and idx not in nc2_failed_tasks
                    and idx not in nc3_failed_tasks
                ):
                    tid = str(tasks[idx].get("task_id") or tasks[idx].get("id") or f"task_{idx}")
                    is_ns, src = cls_list[idx]
                    nc3_failed_tasks[idx] = UnscheduledTaskDiagnosticDTO(
                        task_id=tid,
                        title=str(tasks[idx].get("title") or tid),
                        estimated_minutes=efforts[idx],
                        is_non_splittable=is_ns,
                        non_splittable_source=src,
                        verdict="EXPLICIT_UNSCHEDULABLE",
                        reason_code="CRITICAL_PATH_EXCEEDS_WINDOW",
                        message=(
                            f"Đường găng phụ thuộc dẫn tới '{tasks[idx].get('title') or tid}' vượt quá "
                            "khung thời gian khả dụng đến ngày mục tiêu."
                        ),
                        earliest_feasible_date=None,
                        max_contiguous_window_minutes=global_max_win,
                        required_minutes=efforts[idx],
                    )
        elif not horizon_days and unscheduled_indices:
            # Horizon is empty: NC-1 already fails unless required == 0
            pass

        nc2_passed = len(nc2_failed_tasks) == 0
        nc3_passed = len(nc3_failed_tasks) == 0

        violations: list[ConstraintViolationDTO] = []
        if not nc1_passed:
            violations.append(
                ConstraintViolationDTO(
                    task_index=None,
                    field="estimated_minutes",
                    rule_code=nc1_code,
                    expected_bound=f"<= {total_packable} phút khả dụng",
                    actual_value=f"{total_required} phút",
                    suggested_fix="Gia hạn ngày mục tiêu, tăng thời lượng rảnh hoặc giảm phạm vi lộ trình.",
                )
            )
        for idx, diag in nc2_failed_tasks.items():
            violations.append(
                ConstraintViolationDTO(
                    task_index=idx,
                    field="estimated_minutes",
                    rule_code="TASK_EXCEEDS_CONTINUOUS_SLOT",
                    expected_bound=f"<= {diag.max_contiguous_window_minutes} phút liên tục",
                    actual_value=f"{diag.estimated_minutes} phút",
                    suggested_fix=(
                        f"Mở rộng khung giờ rảnh liên tục lên >= {diag.estimated_minutes} phút cho '{diag.title}'."
                    ),
                )
            )
        for idx, diag in nc3_failed_tasks.items():
            violations.append(
                ConstraintViolationDTO(
                    task_index=idx,
                    field="dependencies",
                    rule_code="CRITICAL_PATH_EXCEEDS_WINDOW",
                    expected_bound="Đường găng DAG hoàn tất trước ngày mục tiêu",
                    actual_value=diag.message,
                    suggested_fix="Gia hạn ngày mục tiêu hoặc giảm bớt phụ thuộc tuần tự trên đường găng.",
                )
            )

        verdict: FeasibilityVerdict = (
            "VERIFIED_FEASIBLE"
            if (nc1_passed and nc2_passed and nc3_passed)
            else "EXPLICIT_UNSCHEDULABLE"
        )
        combined_diags = list({**nc2_failed_tasks, **nc3_failed_tasks}.values())
        return NecessaryConditionCheckResult(
            verdict=verdict,
            nc1_passed=nc1_passed,
            nc2_passed=nc2_passed,
            nc3_passed=nc3_passed,
            total_required_minutes=total_required,
            total_hard_packable_minutes=total_packable,
            raw_capacity_without_existing_minutes=raw_cap_without_existing,
            max_contiguous_window_minutes=global_max_win,
            violations=tuple(violations),
            unscheduled_diagnostics=tuple(combined_diags),
        )

    @classmethod
    def _run_phase1_session_pass(
        cls,
        tasks: Sequence[dict[str, Any]],
        ctx: dict[str, Any],
        *,
        start_date: date,
        target_date: date | None,
        dependencies: Sequence[dict[str, Any]] | None,
        milestone_order_map: dict[str, int] | None,
        preferred_session_minutes: int,
        effective_efforts: Sequence[int],
        classifications: Sequence[tuple[bool, NonSplittableSource]],
        priority_mode: str = "TOPOLOGICAL_DEFAULT",
        allow_slot_sliver: bool = False,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[int]]:
        """Execute a single deterministic Phase 1 pass placing whole/slot-aligned blocks."""
        cloned_tasks = [dict(t) for t in tasks]
        for idx, t in enumerate(cloned_tasks):
            is_ns, src = classifications[idx]
            t["is_non_splittable"] = is_ns
            t["non_splittable_source"] = src

        daily_used: dict[date, int] = dict(ctx["existing_used"])
        daily_intervals: dict[date, list[tuple[int, int]]] = {
            d: list(ivs) for d, ivs in ctx["existing_intervals"].items()
        }
        task_end_anchor: dict[str, tuple[date, int]] = {}
        user_tz = ZoneInfo(ctx["timezone"])

        id_to_idx, preds_by_idx, succs_by_idx, is_acyclic = cls._build_dag_graph(
            cloned_tasks, dependencies
        )

        unscheduled_indices: list[int] = []
        blocks: list[dict[str, Any]] = []
        for idx, t in enumerate(cloned_tasks):
            tid = str(t.get("task_id") or t.get("id") or f"task_{idx}")
            s_date = parse_iso_date(t.get("scheduled_date"))
            if s_date is not None:
                day_entries, pinned_blocks, pinned_anchor = cls._extract_pinned_blocks_and_anchor(
                    t, tid=tid, effort=effective_efforts[idx], tz_name=ctx["timezone"]
                )
                for b_date, s_m, e_m, dur in day_entries:
                    if e_m > s_m:
                        _record_occupied_interval(daily_intervals, daily_used, b_date, s_m, e_m)
                    else:
                        daily_used[b_date] = daily_used.get(b_date, 0) + dur
                task_end_anchor[tid] = pinned_anchor
                blocks.extend(pinned_blocks)
            else:
                unscheduled_indices.append(idx)

        ms_order: dict[str, int] = dict(milestone_order_map or {})
        for t in cloned_tasks:
            mid = str(t.get("milestone_id") or "")
            if mid and mid not in ms_order:
                ms_order[mid] = len(ms_order) + 1

        # Downstream critical path effort for repair ordering
        downstream_cp: dict[int, int] = {i: effective_efforts[i] for i in range(len(cloned_tasks))}
        if is_acyclic:
            in_deg = {i: len(preds_by_idx[i]) for i in range(len(cloned_tasks))}
            q = [i for i, d in in_deg.items() if d == 0]
            topo: list[int] = []
            while q:
                cur = q.pop(0)
                topo.append(cur)
                for nxt in succs_by_idx[cur]:
                    in_deg[nxt] -= 1
                    if in_deg[nxt] == 0:
                        q.append(nxt)
            for node in reversed(topo):
                best_succ = max((downstream_cp[s] for s in succs_by_idx[node]), default=0)
                downstream_cp[node] = effective_efforts[node] + best_succ

        def _sort_key(i: int) -> tuple[Any, ...]:
            t_item = cloned_tasks[i]
            mid = str(t_item.get("milestone_id") or "")
            m_seq = ms_order.get(mid, 999)
            t_ord = _to_int(t_item.get("task_order"), i)
            is_ns = 1 if classifications[i][0] else 0
            eff = effective_efforts[i]
            if priority_mode == "CRITICAL_PATH_FIRST":
                return (-downstream_cp.get(i, eff), -is_ns, -eff, m_seq, t_ord, i)
            if priority_mode == "LARGEST_NON_SPLITTABLE_FIRST":
                return (-is_ns, -eff, -downstream_cp.get(i, eff), m_seq, t_ord, i)
            return (m_seq, t_ord, i)

        unsched_set = set(unscheduled_indices)
        in_degree: dict[int, int] = {
            i: sum(1 for p in preds_by_idx[i] if p in unsched_set) for i in unscheduled_indices
        }
        ready = sorted([i for i, deg in in_degree.items() if deg == 0], key=_sort_key)
        ordered_unscheduled: list[int] = []
        while ready:
            curr = ready.pop(0)
            ordered_unscheduled.append(curr)
            for nxt in succs_by_idx.get(curr, []):
                if nxt in in_degree:
                    in_degree[nxt] -= 1
                    if in_degree[nxt] == 0:
                        ready.append(nxt)
                        ready.sort(key=_sort_key)

        if len(ordered_unscheduled) < len(unscheduled_indices):
            remaining = [i for i in unscheduled_indices if i not in ordered_unscheduled]
            remaining.sort(key=_sort_key)
            ordered_unscheduled.extend(remaining)

        end_date = target_date if target_date is not None else (start_date + timedelta(days=365))
        max_days = max(0, (end_date - start_date).days + 1)
        unplaced_indices: list[int] = []

        for idx in ordered_unscheduled:
            t_item = cloned_tasks[idx]
            tid = str(t_item.get("task_id") or t_item.get("id") or f"task_{idx}")
            effort = effective_efforts[idx]
            is_ns, _ = classifications[idx]
            if effort > 0 and effective_efforts[idx] != _to_int(t_item.get("estimated_minutes"), 0):
                t_item["estimated_minutes"] = effort

            if effort <= 0:
                t_item["scheduled_date"] = None
                t_item["scheduled_start"] = None
                t_item["scheduled_end"] = None
                continue

            min_date = start_date
            min_minute_on_min_date = 0
            has_unplaced_predecessor = False
            for p_idx in preds_by_idx.get(idx, []):
                p_tid = str(
                    cloned_tasks[p_idx].get("task_id")
                    or cloned_tasks[p_idx].get("id")
                    or f"task_{p_idx}"
                )
                anchor = task_end_anchor.get(p_tid)
                if anchor is None:
                    has_unplaced_predecessor = True
                    break
                p_date, p_end_min = anchor
                if p_date > min_date:
                    min_date = p_date
                    min_minute_on_min_date = p_end_min
                elif p_date == min_date:
                    min_minute_on_min_date = max(min_minute_on_min_date, p_end_min)

            if has_unplaced_predecessor or min_date > end_date:
                t_item["scheduled_date"] = None
                t_item["scheduled_start"] = None
                t_item["scheduled_end"] = None
                unplaced_indices.append(idx)
                continue

            rem_effort = effort
            tentative_blocks: list[dict[str, Any]] = []
            tentative_used_map: dict[date, int] = {}
            tentative_intervals_map: dict[date, list[tuple[int, int]]] = {}

            day_span = min(max_days, (end_date - min_date).days + 1)
            for day_step in range(day_span):
                if rem_effort <= 0:
                    break
                cand_date = min_date + timedelta(days=day_step)
                earliest_min = min_minute_on_min_date if day_step == 0 else 0

                # Apply tentative updates on same day while placing multiple chunks
                while rem_effort > 0:
                    used_today = daily_used.get(cand_date, 0) + tentative_used_map.get(cand_date, 0)
                    occ_today = [
                        *daily_intervals.get(cand_date, ()),
                        *tentative_intervals_map.get(cand_date, ()),
                    ]
                    next_d = cand_date + timedelta(days=1)
                    occ_next = [
                        *daily_intervals.get(next_d, ()),
                        *tentative_intervals_map.get(next_d, ()),
                    ]
                    free_ivs, rem_day_cap, _ = cls._day_free_windows(
                        ctx,
                        cand_date,
                        earliest_min=earliest_min,
                        used_today=used_today,
                        occupied=occ_today,
                        next_day_occupied=occ_next,
                    )
                    if not free_ivs or rem_day_cap <= 0:
                        break

                    placed_in_day = False
                    for iv_s, iv_e in free_ivs:
                        w = min(iv_e - iv_s, rem_day_cap)
                        if w <= 0:
                            continue
                        if is_ns:
                            if w < rem_effort:
                                continue
                            chunk = rem_effort
                        else:
                            chunk_opt = _choose_slot_chunk(
                                rem_effort=rem_effort,
                                window_width=w,
                                preferred_session_minutes=preferred_session_minutes,
                                allow_slot_sliver=allow_slot_sliver,
                            )
                            if chunk_opt is None:
                                continue
                            chunk = chunk_opt

                        win_s = iv_s
                        win_e = iv_s + chunk
                        sh, sm = (win_s // 60) % 24, win_s % 60
                        end_day_offset = win_e // 1440
                        b_end_date = cand_date + timedelta(days=end_day_offset)
                        eh, em = (win_e % 1440) // 60, win_e % 60
                        local_start = datetime.combine(cand_date, time(sh, sm), tzinfo=user_tz)
                        local_end = datetime.combine(b_end_date, time(eh, em), tzinfo=user_tz)

                        tentative_blocks.append(
                            {
                                "task_id": tid,
                                "sequence_in_task": len(tentative_blocks) + 1,
                                "block_date": cand_date.isoformat(),
                                "scheduled_start": local_start.isoformat(),
                                "scheduled_end": local_end.isoformat(),
                                "scheduled_duration_minutes": chunk,
                                "_end_date": b_end_date,
                                "_end_min": win_e % 1440 if end_day_offset > 0 else win_e,
                            }
                        )
                        _record_occupied_interval(
                            tentative_intervals_map,
                            tentative_used_map,
                            cand_date,
                            win_s,
                            win_e,
                        )
                        rem_effort -= chunk
                        placed_in_day = True
                        break

                    if not placed_in_day:
                        break

            if rem_effort == 0 and tentative_blocks:
                # Commit blocks and coalesce any adjacent same-day blocks chronologically
                for d_u, mins in tentative_used_map.items():
                    daily_used[d_u] = daily_used.get(d_u, 0) + mins
                for d_i, ivs in tentative_intervals_map.items():
                    daily_intervals.setdefault(d_i, []).extend(ivs)
                ordered_tentative = sorted(
                    tentative_blocks,
                    key=lambda b: (
                        str(b.get("block_date") or ""),
                        str(b.get("scheduled_start") or ""),
                        b["_end_date"],
                        b["_end_min"],
                    ),
                )
                last_end_date, last_end_min = max(
                    (blk["_end_date"], blk["_end_min"]) for blk in ordered_tentative
                )
                clean_task_blocks = [
                    {k: v for k, v in blk.items() if not k.startswith("_")}
                    for blk in ordered_tentative
                ]
                coalesced_task_blocks = cls._coalesce_adjacent_blocks(clean_task_blocks)
                blocks.extend(coalesced_task_blocks)
                t_item["scheduled_date"] = coalesced_task_blocks[0]["block_date"]
                t_item["scheduled_start"] = coalesced_task_blocks[0]["scheduled_start"]
                t_item["scheduled_end"] = coalesced_task_blocks[-1]["scheduled_end"]
                task_end_anchor[tid] = (last_end_date, last_end_min)
            else:
                # Roll back partial blocks — never leave partial orphan blocks or mutate effort
                t_item["scheduled_date"] = None
                t_item["scheduled_start"] = None
                t_item["scheduled_end"] = None
                unplaced_indices.append(idx)

        return cloned_tasks, cls._coalesce_adjacent_blocks(blocks), unplaced_indices

    @staticmethod
    def _count_cross_day_splits(blocks: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
        """Return `(tasks_split_across_days_count, total_extra_day_spans)`."""
        dates_by_task: dict[str, set[str]] = {}
        for b in blocks:
            tid = str(b.get("task_id") or "")
            bdate = str(b.get("block_date") or "")[:10]
            if tid and bdate:
                dates_by_task.setdefault(tid, set()).add(bdate)
        split_tasks = sum(1 for ds in dates_by_task.values() if len(ds) > 1)
        extra_spans = sum(max(0, len(ds) - 1) for ds in dates_by_task.values())
        return split_tasks, extra_spans

    @staticmethod
    def _max_consecutive_study_days(blocks: Sequence[Mapping[str, Any]]) -> int:
        """Return the longest consecutive calendar-day run present in `blocks`."""
        unique_dates = sorted(
            {d for b in blocks if (d := parse_iso_date(b.get("block_date"))) is not None}
        )
        if not unique_dates:
            return 0
        max_streak = 1
        cur_streak = 1
        for prev_d, cur_d in zip(unique_dates, unique_dates[1:], strict=False):
            if (cur_d - prev_d).days == 1:
                cur_streak += 1
                if cur_streak > max_streak:
                    max_streak = cur_streak
            else:
                cur_streak = 1
        return max_streak

    @staticmethod
    def _count_adjacent_same_day_splits(blocks: Sequence[Mapping[str, Any]]) -> int:
        """Count adjacent same-day blocks of the same task whose merged duration <= 120m."""
        by_task_day: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for b in blocks:
            tid = str(b.get("task_id") or "")
            bdate = str(b.get("block_date") or "")[:10]
            if tid and bdate:
                by_task_day.setdefault((tid, bdate), []).append(b)
        count = 0
        for day_blocks in by_task_day.values():
            if len(day_blocks) <= 1:
                continue
            sorted_b = sorted(day_blocks, key=lambda x: str(x.get("scheduled_start") or ""))
            for cur, nxt in zip(sorted_b, sorted_b[1:], strict=False):
                cur_dur = _to_int(cur.get("scheduled_duration_minutes"), 0)
                nxt_dur = _to_int(nxt.get("scheduled_duration_minutes"), 0)
                if (
                    cur.get("scheduled_end") == nxt.get("scheduled_start")
                    and cur_dur + nxt_dur <= AI_BLOCK_MAX_MINUTES
                ):
                    count += 1
        return count

    @staticmethod
    def _select_phase2_study_days(
        avail_days: Sequence[date],
        *,
        day_max_win: Mapping[date, int],
        pinned_dates: set[date],
        use_end_buffer: bool,
        end_buffer_ratio: float,
        use_recovery_days: bool,
        max_streak: int,
    ) -> tuple[list[date], set[date], set[date]]:
        """Select `(study_days, buffer_days, recovery_days)` honoring end-buffer and streak cap."""
        if not avail_days:
            return [], set(), set()

        if use_end_buffer and end_buffer_ratio > 0.0 and len(avail_days) >= 4:
            n_buf = max(1, int(round(len(avail_days) * end_buffer_ratio)))
            n_buf = min(n_buf, len(avail_days) - 1)
            buffer_days = set(avail_days[-n_buf:])
            candidate_days = [d for d in avail_days if d not in buffer_days]
        else:
            buffer_days = set()
            candidate_days = list(avail_days)

        if not use_recovery_days or max_streak < 1:
            return candidate_days, buffer_days, set()

        candidate_set = set(candidate_days)
        active_timeline = sorted(candidate_set | (pinned_dates - buffer_days))
        streak: list[date] = []
        recovery_days: set[date] = set()

        for d in active_timeline:
            if not streak or (d - streak[-1]).days > 1:
                streak = [d]
                continue
            if len(streak) < max_streak:
                streak.append(d)
                continue
            # Adding `d` would exceed `max_streak` consecutive calendar days.
            window = [*streak, d]
            rest_candidates = [
                pos
                for pos, cand_day in enumerate(window)
                if (cand_day not in pinned_dates) and (cand_day in candidate_set)
            ]
            if rest_candidates:
                # Pick lowest-capacity day in the 6-day window; tie-break by latest position.
                best_pos = min(
                    rest_candidates,
                    key=lambda pos: (day_max_win.get(window[pos], 0), -pos),
                )
                recovery_days.add(window[best_pos])
                streak = window[best_pos + 1 :]
            else:
                streak.append(d)

        study_days = [d for d in candidate_days if d not in recovery_days]
        return study_days, buffer_days, recovery_days

    @classmethod
    def _run_phase2_soft_pass(
        cls,
        tasks: Sequence[dict[str, Any]],
        ctx: dict[str, Any],
        *,
        study_days: Sequence[date],
        dependencies: Sequence[dict[str, Any]] | None,
        milestone_order_map: dict[str, int] | None,
        preferred_session_minutes: int,
        effective_efforts: Sequence[int],
        classifications: Sequence[tuple[bool, NonSplittableSource]],
        use_daily_soft_cap: bool,
        use_even_spread: bool,
        avoid_partial_day_split: bool = False,
        priority_mode: str = "TOPOLOGICAL_DEFAULT",
        allow_slot_sliver: bool = False,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[int]]:
        """Execute a day-by-day topological Phase 2 soft pacing pass over `study_days`."""
        cloned_tasks = [dict(t) for t in tasks]
        for idx, t in enumerate(cloned_tasks):
            is_ns, src = classifications[idx]
            t["is_non_splittable"] = is_ns
            t["non_splittable_source"] = src

        daily_used: dict[date, int] = dict(ctx["existing_used"])
        daily_intervals: dict[date, list[tuple[int, int]]] = {
            d: list(ivs) for d, ivs in ctx["existing_intervals"].items()
        }
        task_end_anchor: dict[str, tuple[date, int]] = {}
        user_tz = ZoneInfo(ctx["timezone"])

        _, preds_by_idx, succs_by_idx, is_acyclic = cls._build_dag_graph(cloned_tasks, dependencies)

        unscheduled_indices: list[int] = []
        blocks: list[dict[str, Any]] = []
        for idx, t in enumerate(cloned_tasks):
            tid = str(t.get("task_id") or t.get("id") or f"task_{idx}")
            s_date = parse_iso_date(t.get("scheduled_date"))
            if s_date is not None:
                day_entries, pinned_blocks, pinned_anchor = cls._extract_pinned_blocks_and_anchor(
                    t, tid=tid, effort=effective_efforts[idx], tz_name=ctx["timezone"]
                )
                for b_date, s_m, e_m, dur in day_entries:
                    if e_m > s_m:
                        _record_occupied_interval(daily_intervals, daily_used, b_date, s_m, e_m)
                    else:
                        daily_used[b_date] = daily_used.get(b_date, 0) + dur
                task_end_anchor[tid] = pinned_anchor
                blocks.extend(pinned_blocks)
            elif effective_efforts[idx] > 0:
                unscheduled_indices.append(idx)
            else:
                t["scheduled_date"] = None
                t["scheduled_start"] = None
                t["scheduled_end"] = None

        if not unscheduled_indices:
            return cloned_tasks, cls._coalesce_adjacent_blocks(blocks), []
        if not study_days:
            for idx in unscheduled_indices:
                cloned_tasks[idx]["scheduled_date"] = None
                cloned_tasks[idx]["scheduled_start"] = None
                cloned_tasks[idx]["scheduled_end"] = None
            return cloned_tasks, [], unscheduled_indices

        ms_order: dict[str, int] = dict(milestone_order_map or {})
        for t in cloned_tasks:
            mid = str(t.get("milestone_id") or "")
            if mid and mid not in ms_order:
                ms_order[mid] = len(ms_order) + 1

        downstream_cp: dict[int, int] = {i: effective_efforts[i] for i in range(len(cloned_tasks))}
        if is_acyclic:
            in_deg = {i: len(preds_by_idx[i]) for i in range(len(cloned_tasks))}
            q = [i for i, d in in_deg.items() if d == 0]
            topo: list[int] = []
            while q:
                cur = q.pop(0)
                topo.append(cur)
                for nxt in succs_by_idx[cur]:
                    in_deg[nxt] -= 1
                    if in_deg[nxt] == 0:
                        q.append(nxt)
            for node in reversed(topo):
                best_succ = max((downstream_cp[s] for s in succs_by_idx[node]), default=0)
                downstream_cp[node] = effective_efforts[node] + best_succ

        def _sort_key(i: int) -> tuple[Any, ...]:
            t_item = cloned_tasks[i]
            mid = str(t_item.get("milestone_id") or "")
            m_seq = ms_order.get(mid, 999)
            t_ord = _to_int(t_item.get("task_order"), i)
            is_ns = 1 if classifications[i][0] else 0
            eff = effective_efforts[i]
            if priority_mode == "CRITICAL_PATH_FIRST":
                return (-downstream_cp.get(i, eff), -is_ns, -eff, m_seq, t_ord, i)
            if priority_mode == "LARGEST_NON_SPLITTABLE_FIRST":
                return (-is_ns, -eff, -downstream_cp.get(i, eff), m_seq, t_ord, i)
            return (m_seq, t_ord, i)

        unsched_set = set(unscheduled_indices)
        in_degree: dict[int, int] = {
            i: sum(1 for p in preds_by_idx[i] if p in unsched_set) for i in unscheduled_indices
        }
        ready = sorted([i for i, deg in in_degree.items() if deg == 0], key=_sort_key)

        rem_effort_map: dict[int, int] = {i: effective_efforts[i] for i in unscheduled_indices}
        tentative_blocks_map: dict[int, list[dict[str, Any]]] = {i: [] for i in unscheduled_indices}
        for idx in unscheduled_indices:
            if effective_efforts[idx] != _to_int(cloned_tasks[idx].get("estimated_minutes"), 0):
                cloned_tasks[idx]["estimated_minutes"] = effective_efforts[idx]

        total_movable = sum(effective_efforts[i] for i in unscheduled_indices)
        placed_movable = 0
        completed_count = 0
        active_partial_idx: int | None = None

        # Precompute hard capacity and max window per study day for safe pace gating
        positive_effs = [effective_efforts[i] for i in unscheduled_indices]
        small_effs = [e for e in positive_effs if e < AI_BLOCK_MIN_MINUTES]
        large_effs = [e for e in positive_effs if e >= AI_BLOCK_MIN_MINUTES]
        small_total = sum(small_effs)
        small_min = min(small_effs) if small_effs else AI_BLOCK_MIN_MINUTES
        num_days = len(study_days)
        day_caps: list[int] = []
        day_small_bonuses: list[int] = []
        day_max_wins: list[int] = []
        for d in study_days:
            free_ivs, rem_cap, _ = cls._day_free_windows(
                ctx,
                d,
                earliest_min=0,
                used_today=daily_used.get(d, 0),
                occupied=daily_intervals.get(d, ()),
                next_day_occupied=daily_intervals.get(d + timedelta(days=1), ()),
            )
            usable_30 = [(s, e) for s, e in free_ivs if (e - s) >= AI_BLOCK_MIN_MINUTES]
            usable_small = (
                [(s, e) for s, e in free_ivs if small_min <= (e - s) < AI_BLOCK_MIN_MINUTES]
                if small_effs
                else []
            )
            sum_30 = sum(e - s for s, e in usable_30)
            sum_small = sum(e - s for s, e in usable_small)
            cap_30 = min(rem_cap, sum_30)
            cap_all = min(rem_cap, sum_30 + sum_small)
            day_caps.append(cap_30)
            day_small_bonuses.append(max(0, cap_all - cap_30))
            day_max_wins.append(
                min(
                    rem_cap,
                    max((e - s for s, e in usable_30), default=0)
                    if large_effs
                    else max((e - s for s, e in [*usable_30, *usable_small]), default=0),
                )
            )

        suffix_cap = [0] * (num_days + 1)
        suffix_small_bonus = [0] * (num_days + 1)
        suffix_max_win = [0] * (num_days + 1)
        for j in range(num_days - 1, -1, -1):
            suffix_cap[j] = suffix_cap[j + 1] + day_caps[j]
            suffix_small_bonus[j] = suffix_small_bonus[j + 1] + day_small_bonuses[j]
            suffix_max_win[j] = max(suffix_max_win[j + 1], day_max_wins[j])

        for j, cand_date in enumerate(study_days):
            if placed_movable >= total_movable:
                break

            if use_even_spread and active_partial_idx is None:
                rem_movable = total_movable - placed_movable
                rem_tasks = len(unscheduled_indices) - completed_count
                rem_future_days = num_days - j - 1
                target_cum = (total_movable * (j + 1)) / num_days
                future_cap = suffix_cap[j + 1] + min(small_total, suffix_small_bonus[j + 1])
                future_max_win = suffix_max_win[j + 1]
                needs_todays_big_window = any(
                    classifications[r_idx][0]
                    and rem_effort_map[r_idx] > future_max_win
                    and rem_effort_map[r_idx] <= day_max_wins[j]
                    for r_idx in ready
                )
                if (
                    placed_movable >= target_cum
                    and future_cap >= rem_movable
                    and rem_tasks <= rem_future_days
                    and not needs_todays_big_window
                ):
                    continue

            _, rem_day_hard_cap_init, _ = cls._day_free_windows(
                ctx,
                cand_date,
                earliest_min=0,
                used_today=daily_used.get(cand_date, 0),
                occupied=daily_intervals.get(cand_date, ()),
                next_day_occupied=daily_intervals.get(cand_date + timedelta(days=1), ()),
            )
            if rem_day_hard_cap_init <= 0:
                continue

            if use_daily_soft_cap:
                rem_study_days = num_days - j
                rem_movable = total_movable - placed_movable
                raw_avg = (rem_movable + rem_study_days - 1) // rem_study_days
                paced_cap = ((raw_avg + 29) // 30) * 30
                pref_bound = max(AI_BLOCK_MIN_MINUTES, int(preferred_session_minutes))
                day_soft_cap = min(rem_day_hard_cap_init, max(pref_bound, paced_cap))
            else:
                day_soft_cap = rem_day_hard_cap_init

            used_by_us_today = 0

            while placed_movable < total_movable:
                free_ivs, rem_day_hard_cap, _ = cls._day_free_windows(
                    ctx,
                    cand_date,
                    earliest_min=0,
                    used_today=daily_used.get(cand_date, 0),
                    occupied=daily_intervals.get(cand_date, ()),
                    next_day_occupied=daily_intervals.get(cand_date + timedelta(days=1), ()),
                )
                if not free_ivs or rem_day_hard_cap <= 0:
                    break

                candidates = [active_partial_idx] if active_partial_idx is not None else list(ready)
                placed_step = False

                for cand_idx in candidates:
                    rem_eff = rem_effort_map[cand_idx]
                    if rem_eff <= 0:
                        continue
                    is_ns = classifications[cand_idx][0]

                    min_minute_on_min_date = 0
                    pred_not_ready = False
                    for p_idx in preds_by_idx.get(cand_idx, ()):
                        p_tid = str(
                            cloned_tasks[p_idx].get("task_id")
                            or cloned_tasks[p_idx].get("id")
                            or f"task_{p_idx}"
                        )
                        anchor = task_end_anchor.get(p_tid)
                        if anchor is None:
                            pred_not_ready = True
                            break
                        p_date, p_end_min = anchor
                        if p_date > cand_date:
                            pred_not_ready = True
                            break
                        if p_date == cand_date:
                            min_minute_on_min_date = max(min_minute_on_min_date, p_end_min)
                    if pred_not_ready:
                        continue

                    for iv_s, iv_e in free_ivs:
                        eff_s = max(iv_s, min_minute_on_min_date)
                        w = min(iv_e - eff_s, rem_day_hard_cap)
                        if w <= 0:
                            continue

                        chunk: int | None = None
                        if is_ns:
                            if w >= rem_eff and (
                                not use_daily_soft_cap
                                or used_by_us_today == 0
                                or used_by_us_today + rem_eff <= day_soft_cap
                            ):
                                chunk = rem_eff
                        elif use_daily_soft_cap:
                            if used_by_us_today == 0:
                                if (
                                    rem_eff <= AI_BLOCK_MAX_MINUTES
                                    and w >= rem_eff
                                    and (
                                        allow_slot_sliver
                                        or (w - rem_eff == 0 or w - rem_eff >= AI_BLOCK_MIN_MINUTES)
                                    )
                                ):
                                    # Whole-fit anti-split exception: never split a single whole task
                                    # unless doing so strands a <30m physical slot sliver.
                                    chunk = rem_eff
                                else:
                                    chunk = _choose_slot_chunk(
                                        rem_effort=rem_eff,
                                        window_width=w,
                                        preferred_session_minutes=preferred_session_minutes,
                                        allow_slot_sliver=allow_slot_sliver,
                                        max_chunk=min(
                                            AI_BLOCK_MAX_MINUTES,
                                            max(AI_BLOCK_MIN_MINUTES, day_soft_cap),
                                        ),
                                    )
                            else:
                                rem_soft_today = day_soft_cap - used_by_us_today
                                if rem_soft_today > 0:
                                    if (
                                        rem_eff <= rem_soft_today
                                        and rem_eff <= AI_BLOCK_MAX_MINUTES
                                        and w >= rem_eff
                                        and (
                                            allow_slot_sliver
                                            or (
                                                w - rem_eff == 0
                                                or w - rem_eff >= AI_BLOCK_MIN_MINUTES
                                            )
                                        )
                                    ):
                                        chunk = rem_eff
                                    elif (
                                        not avoid_partial_day_split
                                        or rem_eff > AI_BLOCK_MAX_MINUTES
                                    ) and (
                                        rem_soft_today >= AI_BLOCK_MIN_MINUTES
                                        or (
                                            rem_eff < AI_BLOCK_MIN_MINUTES
                                            and rem_eff <= rem_soft_today
                                        )
                                    ):
                                        chunk = _choose_slot_chunk(
                                            rem_effort=rem_eff,
                                            window_width=w,
                                            preferred_session_minutes=preferred_session_minutes,
                                            allow_slot_sliver=allow_slot_sliver,
                                            max_chunk=min(AI_BLOCK_MAX_MINUTES, rem_soft_today),
                                        )
                        elif avoid_partial_day_split and used_by_us_today > 0 and w < rem_eff:
                            chunk = None
                        else:
                            chunk = _choose_slot_chunk(
                                rem_effort=rem_eff,
                                window_width=w,
                                preferred_session_minutes=preferred_session_minutes,
                                allow_slot_sliver=allow_slot_sliver,
                            )

                        if chunk is None or chunk <= 0:
                            continue

                        win_s = eff_s
                        win_e = eff_s + chunk
                        sh, sm = (win_s // 60) % 24, win_s % 60
                        end_day_offset = win_e // 1440
                        b_end_date = cand_date + timedelta(days=end_day_offset)
                        eh, em = (win_e % 1440) // 60, win_e % 60
                        local_start = datetime.combine(cand_date, time(sh, sm), tzinfo=user_tz)
                        local_end = datetime.combine(b_end_date, time(eh, em), tzinfo=user_tz)
                        tid = str(
                            cloned_tasks[cand_idx].get("task_id")
                            or cloned_tasks[cand_idx].get("id")
                            or f"task_{cand_idx}"
                        )
                        tentative_blocks_map[cand_idx].append(
                            {
                                "task_id": tid,
                                "sequence_in_task": len(tentative_blocks_map[cand_idx]) + 1,
                                "block_date": cand_date.isoformat(),
                                "scheduled_start": local_start.isoformat(),
                                "scheduled_end": local_end.isoformat(),
                                "scheduled_duration_minutes": chunk,
                                "_end_date": b_end_date,
                                "_end_min": win_e % 1440 if end_day_offset > 0 else win_e,
                            }
                        )
                        _record_occupied_interval(
                            daily_intervals, daily_used, cand_date, win_s, win_e
                        )
                        used_by_us_today += chunk
                        rem_effort_map[cand_idx] -= chunk
                        placed_movable += chunk

                        if rem_effort_map[cand_idx] == 0:
                            ordered_t_blks = sorted(
                                tentative_blocks_map[cand_idx],
                                key=lambda b: (
                                    str(b.get("block_date") or ""),
                                    str(b.get("scheduled_start") or ""),
                                    b["_end_date"],
                                    b["_end_min"],
                                ),
                            )
                            last_end_date, last_end_min = max(
                                (blk["_end_date"], blk["_end_min"]) for blk in ordered_t_blks
                            )
                            clean_task_blocks = [
                                {k: v for k, v in blk.items() if not k.startswith("_")}
                                for blk in ordered_t_blks
                            ]
                            coalesced_task_blocks = cls._coalesce_adjacent_blocks(clean_task_blocks)
                            blocks.extend(coalesced_task_blocks)
                            cloned_tasks[cand_idx]["scheduled_date"] = coalesced_task_blocks[0][
                                "block_date"
                            ]
                            cloned_tasks[cand_idx]["scheduled_start"] = coalesced_task_blocks[0][
                                "scheduled_start"
                            ]
                            cloned_tasks[cand_idx]["scheduled_end"] = coalesced_task_blocks[-1][
                                "scheduled_end"
                            ]
                            task_end_anchor[tid] = (last_end_date, last_end_min)
                            completed_count += 1
                            if active_partial_idx == cand_idx:
                                active_partial_idx = None
                            if cand_idx in ready:
                                ready.remove(cand_idx)
                            for nxt in succs_by_idx.get(cand_idx, ()):
                                if nxt in in_degree:
                                    in_degree[nxt] -= 1
                                    if in_degree[nxt] == 0 and nxt not in ready:
                                        ready.append(nxt)
                            ready.sort(key=_sort_key)
                        else:
                            active_partial_idx = cand_idx
                            if cand_idx in ready:
                                ready.remove(cand_idx)

                        placed_step = True
                        break

                    if placed_step:
                        break

                if not placed_step:
                    break

        unplaced = [i for i in unscheduled_indices if rem_effort_map[i] > 0]
        if unplaced:
            for idx in unplaced:
                cloned_tasks[idx]["scheduled_date"] = None
                cloned_tasks[idx]["scheduled_start"] = None
                cloned_tasks[idx]["scheduled_end"] = None
            return cloned_tasks, [], unplaced

        return cloned_tasks, cls._coalesce_adjacent_blocks(blocks), []

    @classmethod
    def _validate_phase2_candidate(
        cls,
        *,
        cand_tasks: Sequence[dict[str, Any]],
        cand_blocks: Sequence[dict[str, Any]],
        availability: AvailabilityConfigurationDTO,
        start_date: date,
        target_date: date | None,
        dependencies: Sequence[dict[str, Any]] | None,
        existing_tasks: Sequence[Any] | None,
        effective_efforts: Sequence[int],
        classifications: Sequence[tuple[bool, NonSplittableSource]],
        hard_split_tasks: int,
        hard_extra_spans: int,
        max_allowed_streak: int | None = None,
        buffer_days: set[date] | None = None,
        movable_task_ids: set[str] | None = None,
        daily_workload_cap_minutes: int | None = None,
    ) -> list[str]:
        """Strictly re-validate a Phase 2 soft candidate against all hard scheduling invariants."""
        errors: list[str] = []

        if len(cand_tasks) != len(effective_efforts):
            errors.append("TASK_COUNT_MISMATCH")
            return errors

        # 1. Task effort conservation, placement completeness, and horizon bounds
        expected_effort_by_id: dict[str, int] = {}
        is_ns_by_id: dict[str, bool] = {}
        task_by_id: dict[str, dict[str, Any]] = {}
        for idx, t in enumerate(cand_tasks):
            tid = str(t.get("task_id") or t.get("id") or f"task_{idx}")
            eff = effective_efforts[idx]
            if _to_int(t.get("estimated_minutes"), 0) != eff:
                errors.append(f"EFFORT_MUTATION:{tid}")
            if eff <= 0:
                continue
            expected_effort_by_id[tid] = eff
            is_ns_by_id[tid] = classifications[idx][0]
            task_by_id[tid] = t
            s_date = parse_iso_date(t.get("scheduled_date"))
            s_start = parse_iso_datetime(t.get("scheduled_start"))
            s_end = parse_iso_datetime(t.get("scheduled_end"))
            if s_date is None or s_start is None or s_end is None:
                errors.append(f"UNPLACED_TASK:{tid}")
                continue
            if target_date is not None and s_date > target_date:
                errors.append(f"PAST_TARGET_DATE:{tid}")
            if (movable_task_ids is None or tid in movable_task_ids) and s_date < start_date:
                errors.append(f"BEFORE_START_DATE:{tid}")

        # 2. Schedule block structural integrity, <30m sliver guard, overlap, and 720m daily cap
        allocated_by_id: dict[str, int] = {}
        blocks_by_id: dict[str, list[dict[str, Any]]] = {}
        block_dates_by_id: dict[str, set[date]] = {}
        block_sequences: set[tuple[str, int]] = set()
        block_intervals: list[tuple[datetime, datetime]] = []
        minutes_by_date: dict[date, int] = {}

        for b in cand_blocks:
            tid = str(b.get("task_id") or "")
            if tid not in expected_effort_by_id:
                errors.append(f"ORPHAN_BLOCK:{tid}")
                continue
            b_date = parse_iso_date(b.get("block_date"))
            b_start = parse_iso_datetime(b.get("scheduled_start"))
            b_end = parse_iso_datetime(b.get("scheduled_end"))
            dur = _to_int(b.get("scheduled_duration_minutes"), 0)
            seq = _to_int(b.get("sequence_in_task"), 0)
            eff = expected_effort_by_id[tid]
            is_ns = is_ns_by_id[tid]
            is_pinned = movable_task_ids is not None and tid not in movable_task_ids
            min_block_allowed = (
                10
                if is_pinned
                else (
                    min(AI_BLOCK_MIN_MINUTES, eff)
                    if eff < AI_BLOCK_MIN_MINUTES
                    else AI_BLOCK_MIN_MINUTES
                )
            )
            max_block_allowed = (
                max(MANUAL_BLOCK_MAX_MINUTES, eff) if (is_ns or is_pinned) else AI_BLOCK_MAX_MINUTES
            )
            if (
                b_date is None
                or b_start is None
                or b_end is None
                or b_date != b_start.date()
                or dur < max(10, min_block_allowed)
                or dur > max_block_allowed
                or int((b_end - b_start).total_seconds() // 60) != dur
                or seq < 1
                or (tid, seq) in block_sequences
            ):
                errors.append(f"INVALID_BLOCK:{tid}:{seq}")
                continue
            if target_date is not None and b_date > target_date:
                errors.append(f"BLOCK_PAST_TARGET_DATE:{tid}")
            if (
                buffer_days
                and b_date in buffer_days
                and (movable_task_ids is None or tid in movable_task_ids)
            ):
                errors.append(f"BLOCK_IN_END_BUFFER:{tid}:{b_date.isoformat()}")
            block_sequences.add((tid, seq))
            allocated_by_id[tid] = allocated_by_id.get(tid, 0) + dur
            blocks_by_id.setdefault(tid, []).append(b)
            block_dates_by_id.setdefault(tid, set()).add(b_date)
            block_intervals.append((b_start, b_end))
            minutes_by_date[b_date] = minutes_by_date.get(b_date, 0) + dur

        for tid, eff in expected_effort_by_id.items():
            if allocated_by_id.get(tid, 0) != eff:
                errors.append(f"BLOCK_EFFORT_MISMATCH:{tid}")
            if is_ns_by_id[tid] and (movable_task_ids is None or tid in movable_task_ids):
                if (
                    len(blocks_by_id.get(tid, ())) != 1
                    or len(block_dates_by_id.get(tid, set())) != 1
                ):
                    errors.append(f"NON_SPLITTABLE_SPLIT:{tid}")

        block_intervals.sort(key=lambda iv: (iv[0], iv[1]))
        for prev_iv, curr_iv in zip(block_intervals, block_intervals[1:], strict=False):
            if curr_iv[0] < prev_iv[1]:
                errors.append("SCHEDULE_BLOCK_OVERLAP")
                break

        existing_minutes_by_date: dict[date, int] = {}
        if existing_tasks:
            dummy_intervals: dict[date, list[tuple[int, int]]] = {}
            for ext in existing_tasks:
                status = (
                    str(ext.get("status", "TODO"))
                    if isinstance(ext, dict)
                    else str(getattr(ext, "status", "TODO"))
                ).upper()
                if status in ("CANCELLED", "COMPLETED"):
                    continue
                if isinstance(ext, dict):
                    ex_date = parse_iso_date(ext.get("scheduled_date"))
                    ex_mins = _to_int(ext.get("estimated_minutes"), 0)
                    ex_start = parse_iso_datetime(
                        ext.get("planned_start_at") or ext.get("scheduled_start")
                    )
                    ex_end = parse_iso_datetime(
                        ext.get("planned_end_at") or ext.get("scheduled_end")
                    )
                else:
                    ex_date = parse_iso_date(getattr(ext, "scheduled_date", None))
                    ex_mins = _to_int(getattr(ext, "estimated_minutes", 0), 0)
                    ex_start = parse_iso_datetime(
                        getattr(ext, "planned_start_at", None)
                        or getattr(ext, "scheduled_start", None)
                    )
                    ex_end = parse_iso_datetime(
                        getattr(ext, "planned_end_at", None) or getattr(ext, "scheduled_end", None)
                    )
                ex_start = _in_user_timezone(ex_start, availability.timezone)
                ex_end = _in_user_timezone(ex_end, availability.timezone)
                if ex_start is not None and ex_end is not None:
                    s_m = ex_start.hour * 60 + ex_start.minute
                    span_m = int((ex_end - ex_start).total_seconds() // 60)
                    e_m = s_m + max(ex_mins, span_m)
                    if e_m > s_m:
                        _record_occupied_interval(
                            dummy_intervals,
                            existing_minutes_by_date,
                            ex_start.date(),
                            s_m,
                            e_m,
                        )
                elif ex_date is not None and ex_mins > 0:
                    existing_minutes_by_date[ex_date] = (
                        existing_minutes_by_date.get(ex_date, 0) + ex_mins
                    )

        cap_ceiling = (
            min(MAX_DAILY_PLANNED_MINUTES, max(10, int(daily_workload_cap_minutes)))
            if daily_workload_cap_minutes is not None
            else None
        )
        for d, mins in minutes_by_date.items():
            if mins > MAX_DAILY_PLANNED_MINUTES:
                errors.append(f"DAILY_MAX_720M_EXCEEDED:{d.isoformat()}")
            if cap_ceiling is not None and mins + existing_minutes_by_date.get(d, 0) > cap_ceiling:
                errors.append(f"DAILY_WORKLOAD_CAP_EXCEEDED:{d.isoformat()}")

        # 3. Mode A / Mode B / disabled weekdays / existing_tasks EDF checks
        block_items: list[dict[str, object]] = [
            {
                "task_id": b.get("task_id"),
                "estimated_minutes": b.get("scheduled_duration_minutes"),
                "scheduled_date": b.get("block_date"),
                "scheduled_start": b.get("scheduled_start"),
                "scheduled_end": b.get("scheduled_end"),
            }
            for b in cand_blocks
        ]
        mode_upper = (availability.mode or "MODE_A").strip().upper()
        if mode_upper in ("MODE_B", "FIXED_SLOTS", "SLOTS"):
            b_violations, b_warnings = cls.validate_mode_b_slots(
                tasks=block_items,
                availability=availability,
                existing_tasks=existing_tasks or (),
                current_roadmap_target_date=target_date,
            )
            for v in b_violations:
                errors.append(f"MODE_B:{v.rule_code}")
            if b_warnings:
                errors.append("MODE_B_SOFT_OVERFLOW")
        else:
            a_violations = cls.validate_mode_a_quota(
                tasks=block_items,
                availability=availability,
                existing_tasks=existing_tasks or (),
                current_roadmap_target_date=target_date,
            )
            for v in a_violations:
                errors.append(f"MODE_A:{v.rule_code}")

        # 4. Mandatory DAG prerequisite order (pred.end <= succ.start)
        for dep in dependencies or ():
            if not isinstance(dep, dict) or dep.get("is_mandatory", True) is False:
                continue
            p_id = str(dep.get("predecessor_id") or "")
            s_id = str(dep.get("successor_id") or "")
            p_task = task_by_id.get(p_id)
            s_task = task_by_id.get(s_id)
            if p_task is None or s_task is None:
                continue
            p_end = parse_iso_datetime(p_task.get("scheduled_end"))
            s_start = parse_iso_datetime(s_task.get("scheduled_start"))
            if p_end is None or s_start is None or p_end > s_start:
                errors.append(f"DAG_ORDER_VIOLATION:{p_id}->{s_id}")

        # 5. No extra cross-day or adjacent same-day splits introduced by pacing
        soft_split_tasks, soft_extra_spans = cls._count_cross_day_splits(cand_blocks)
        if soft_split_tasks > hard_split_tasks or soft_extra_spans > hard_extra_spans:
            errors.append("EXTRA_CROSS_DAY_SPLITS")
        if cls._count_adjacent_same_day_splits(cand_blocks) > 0:
            errors.append("ADJACENT_SAME_DAY_SPLITS")

        # 6. Recovery-day streak verification when tier enforces streak cap
        if (
            max_allowed_streak is not None
            and cls._max_consecutive_study_days(cand_blocks) > max_allowed_streak
        ):
            errors.append("STREAK_EXCEEDS_MAX")

        return errors

    @classmethod
    def _optimize_schedule_phase2(
        cls,
        *,
        tasks: Sequence[dict[str, Any]],
        hard_tasks: list[dict[str, Any]],
        hard_blocks: list[dict[str, Any]],
        availability: AvailabilityConfigurationDTO,
        ctx: dict[str, Any],
        start_date: date,
        target_date: date | None,
        dependencies: Sequence[dict[str, Any]] | None,
        existing_tasks: Sequence[Any] | None,
        milestone_order_map: dict[str, int] | None,
        preferred_session_minutes: int,
        effective_efforts: Sequence[int],
        classifications: Sequence[tuple[bool, NonSplittableSource]],
        nc_result: NecessaryConditionCheckResult,
        soft_pacing_v2_enabled: bool,
        end_buffer_ratio: float,
        max_consecutive_study_days: int,
        daily_workload_cap_minutes: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Phase 2 Soft Optimization with progressive relaxation and atomic fallback to S_hard."""
        if not soft_pacing_v2_enabled or not hard_blocks:
            return hard_tasks, hard_blocks

        if nc_result.verdict != "VERIFIED_FEASIBLE":
            return hard_tasks, hard_blocks

        movable_indices = [
            idx
            for idx, t in enumerate(tasks)
            if parse_iso_date(t.get("scheduled_date")) is None and effective_efforts[idx] > 0
        ]
        if not movable_indices:
            return hard_tasks, hard_blocks

        movable_task_ids = {
            str(tasks[idx].get("task_id") or tasks[idx].get("id") or f"task_{idx}")
            for idx in movable_indices
        }
        hard_split_tasks, hard_extra_spans = cls._count_cross_day_splits(hard_blocks)
        max_streak_cfg = max(1, int(max_consecutive_study_days))

        if target_date is None or target_date < start_date:
            # Without an explicit deadline, preserve S_hard unless study streak exceeds cap.
            if cls._max_consecutive_study_days(hard_blocks) <= max_streak_cfg:
                return hard_tasks, hard_blocks
            horizon_end = max(
                (d for b in hard_blocks if (d := parse_iso_date(b.get("block_date"))) is not None),
                default=start_date,
            ) + timedelta(days=max(14, len(movable_indices)))
            eff_end_buffer = 0.0
            allow_pacing = False
        else:
            horizon_end = target_date
            eff_end_buffer = max(0.0, min(0.45, float(end_buffer_ratio)))
            allow_pacing = True

        span = min(366, max(0, (horizon_end - start_date).days + 1))
        if span <= 0:
            return hard_tasks, hard_blocks

        positive_efforts = [effective_efforts[i] for i in movable_indices]
        small_efforts = [e for e in positive_efforts if e < AI_BLOCK_MIN_MINUTES]
        large_efforts = [e for e in positive_efforts if e >= AI_BLOCK_MIN_MINUTES]
        small_total = sum(small_efforts)
        small_min = min(small_efforts) if small_efforts else AI_BLOCK_MIN_MINUTES
        min_unit = AI_BLOCK_MIN_MINUTES if large_efforts else small_min
        total_movable_effort = sum(positive_efforts)

        pinned_used: dict[date, int] = dict(ctx["existing_used"])
        pinned_intervals: dict[date, list[tuple[int, int]]] = {
            d: list(ivs) for d, ivs in ctx["existing_intervals"].items()
        }
        pinned_dates: set[date] = set()
        for idx, t in enumerate(tasks):
            p_date = parse_iso_date(t.get("scheduled_date"))
            if p_date is None:
                continue
            tid = str(t.get("task_id") or t.get("id") or f"task_{idx}")
            day_entries, _, _ = cls._extract_pinned_blocks_and_anchor(
                t, tid=tid, effort=effective_efforts[idx], tz_name=ctx["timezone"]
            )
            for b_date, s_m, e_m, dur in day_entries:
                pinned_dates.add(b_date)
                if e_m > s_m:
                    _record_occupied_interval(pinned_intervals, pinned_used, b_date, s_m, e_m)
                else:
                    pinned_used[b_date] = pinned_used.get(b_date, 0) + dur

        avail_days: list[date] = []
        day_packable_cap: dict[date, int] = {}
        day_small_bonus: dict[date, int] = {}
        day_max_win: dict[date, int] = {}
        for offset in range(span):
            d = start_date + timedelta(days=offset)
            free_ivs, rem_cap, _ = cls._day_free_windows(
                ctx,
                d,
                earliest_min=0,
                used_today=pinned_used.get(d, 0),
                occupied=pinned_intervals.get(d, ()),
                next_day_occupied=pinned_intervals.get(d + timedelta(days=1), ()),
            )
            usable_30 = [(s, e) for s, e in free_ivs if (e - s) >= AI_BLOCK_MIN_MINUTES]
            usable_small = (
                [(s, e) for s, e in free_ivs if small_min <= (e - s) < AI_BLOCK_MIN_MINUTES]
                if small_efforts
                else []
            )
            sum_30 = sum(e - s for s, e in usable_30)
            sum_small = sum(e - s for s, e in usable_small)
            cap_30 = min(rem_cap, sum_30)
            cap_all = min(rem_cap, sum_30 + sum_small)
            if (cap_30 if large_efforts else cap_all) >= min_unit:
                avail_days.append(d)
                day_packable_cap[d] = cap_30
                day_small_bonus[d] = max(0, cap_all - cap_30)
                day_max_win[d] = min(
                    rem_cap,
                    max((e - s for s, e in usable_30), default=0)
                    if large_efforts
                    else max((e - s for s, e in [*usable_30, *usable_small]), default=0),
                )

        total_packable = sum(day_packable_cap.values()) + min(
            small_total, sum(day_small_bonus.values())
        )
        if total_packable <= total_movable_effort:
            # No slack at all -> return S_hard directly.
            return hard_tasks, hard_blocks

        # Progressive relaxation tiers (strict priority order -> atomic fallback to S_hard)
        # Tuple: (use_soft_cap, use_spread, use_end_buffer, use_recovery, streak_cap, avoid_partial_split)
        tiers: list[tuple[bool, bool, bool, bool, int, bool]] = []
        if allow_pacing:
            # Tier 1: Full soft targets (pacing + end_buffer + recovery_days)
            tiers.append((True, True, True, True, max_streak_cfg, True))
            tiers.append((True, False, True, True, max_streak_cfg, True))
            # Tier 2: Relax daily_soft_cap (keep recovery_days + end_buffer)
            tiers.append((False, False, True, True, max_streak_cfg, True))
            tiers.append((False, False, True, True, max_streak_cfg, False))
            # Tier 3: Relax end_buffer too (keep recovery_days; retry pacing first, then cap-free)
            tiers.append((True, True, False, True, max_streak_cfg, True))
            tiers.append((True, False, False, True, max_streak_cfg, True))
            tiers.append((False, False, False, True, max_streak_cfg, True))
            tiers.append((False, False, False, True, max_streak_cfg, False))
            if max_streak_cfg < 6:
                tiers.append((False, False, False, True, 6, True))
                tiers.append((False, False, False, True, 6, False))
        else:
            tiers.append((False, False, False, True, max_streak_cfg, True))
            tiers.append((False, False, False, True, max_streak_cfg, False))

        for use_soft_cap, use_spread, use_buf, use_rec, streak_cap, avoid_partial in tiers:
            study_days, buffer_days, _ = cls._select_phase2_study_days(
                avail_days,
                day_max_win=day_max_win,
                pinned_dates=pinned_dates,
                use_end_buffer=use_buf,
                end_buffer_ratio=eff_end_buffer,
                use_recovery_days=use_rec,
                max_streak=streak_cap,
            )
            if sum(day_packable_cap.get(d, 0) for d in study_days) < total_movable_effort:
                continue

            for prio_mode, allow_sliver in (
                ("TOPOLOGICAL_DEFAULT", False),
                ("CRITICAL_PATH_FIRST", False),
                ("LARGEST_NON_SPLITTABLE_FIRST", False),
                ("CRITICAL_PATH_FIRST", True),
            ):
                cand_tasks, cand_blocks, cand_unplaced = cls._run_phase2_soft_pass(
                    tasks,
                    ctx,
                    study_days=study_days,
                    dependencies=dependencies,
                    milestone_order_map=milestone_order_map,
                    preferred_session_minutes=preferred_session_minutes,
                    effective_efforts=effective_efforts,
                    classifications=classifications,
                    use_daily_soft_cap=use_soft_cap,
                    use_even_spread=use_spread,
                    avoid_partial_day_split=avoid_partial,
                    priority_mode=prio_mode,
                    allow_slot_sliver=allow_sliver,
                )
                if cand_unplaced:
                    continue

                validation_errors = cls._validate_phase2_candidate(
                    cand_tasks=cand_tasks,
                    cand_blocks=cand_blocks,
                    availability=availability,
                    start_date=start_date,
                    target_date=target_date,
                    dependencies=dependencies,
                    existing_tasks=existing_tasks,
                    effective_efforts=effective_efforts,
                    classifications=classifications,
                    hard_split_tasks=hard_split_tasks,
                    hard_extra_spans=hard_extra_spans,
                    max_allowed_streak=streak_cap if use_rec else None,
                    buffer_days=buffer_days if use_buf else None,
                    movable_task_ids=movable_task_ids,
                    daily_workload_cap_minutes=daily_workload_cap_minutes,
                )
                if not validation_errors:
                    return cand_tasks, cand_blocks

        # Tier 4: Atomic fallback to verified Phase 1 schedule S_hard
        return hard_tasks, hard_blocks

    @classmethod
    def allocate_task_sessions_with_diagnostics(
        cls,
        tasks: Sequence[dict[str, Any]],
        availability: AvailabilityConfigurationDTO,
        *,
        start_date: date,
        target_date: date | None = None,
        dependencies: Sequence[dict[str, Any]] | None = None,
        existing_tasks: Sequence[Any] | None = None,
        milestone_order_map: dict[str, int] | None = None,
        preferred_session_minutes: int = 60,
        estimation_bias_beta: float = 1.0,
        peak_productivity_slots: Sequence[str] = (),
        daily_workload_cap_minutes: int | None = None,
        buffer_minutes_per_week: int = 0,
        include_weekly_buffers: bool = False,
        soft_pacing_v2_enabled: bool = True,
        end_buffer_ratio: float = 0.12,
        max_consecutive_study_days: int = 5,
    ) -> ScheduleAllocationResult:
        """Phase 1 Hard-Constraint Slot-Aware Solver + Phase 2 Soft Pacing with atomic fallback."""
        _ = (peak_productivity_slots, buffer_minutes_per_week, include_weekly_buffers)
        classifications = [NonSplittableTaskClassifier.classify(t) for t in tasks]
        clamped_beta = max(0.7, min(1.8, float(estimation_bias_beta)))
        effective_efforts: list[int] = []
        for t in tasks:
            raw_effort = _to_int(t.get("estimated_minutes"), 0)
            if (
                AI_BLOCK_MIN_MINUTES <= raw_effort <= AI_BLOCK_MAX_MINUTES
                and abs(clamped_beta - 1.0) > 1e-6
            ):
                eff = max(
                    AI_BLOCK_MIN_MINUTES,
                    min(AI_BLOCK_MAX_MINUTES, int(round(raw_effort * clamped_beta))),
                )
            else:
                eff = raw_effort
            effective_efforts.append(eff)

        ctx = cls._build_calendar_context(
            availability,
            existing_tasks=existing_tasks,
            daily_workload_cap_minutes=daily_workload_cap_minutes,
        )

        best_tasks, best_blocks, best_unplaced = cls._run_phase1_session_pass(
            tasks,
            ctx,
            start_date=start_date,
            target_date=target_date,
            dependencies=dependencies,
            milestone_order_map=milestone_order_map,
            preferred_session_minutes=preferred_session_minutes,
            effective_efforts=effective_efforts,
            classifications=classifications,
            priority_mode="TOPOLOGICAL_DEFAULT",
            allow_slot_sliver=False,
        )
        repairs_attempted = 0

        if not best_unplaced:
            nc_ok = cls.verify_necessary_conditions(
                tasks,
                availability,
                start_date=start_date,
                target_date=target_date,
                dependencies=dependencies,
                existing_tasks=existing_tasks,
                daily_workload_cap_minutes=daily_workload_cap_minutes,
                effective_efforts=effective_efforts,
                classifications=classifications,
            )
            final_tasks, final_blocks = cls._optimize_schedule_phase2(
                tasks=tasks,
                hard_tasks=best_tasks,
                hard_blocks=best_blocks,
                availability=availability,
                ctx=ctx,
                start_date=start_date,
                target_date=target_date,
                dependencies=dependencies,
                existing_tasks=existing_tasks,
                milestone_order_map=milestone_order_map,
                preferred_session_minutes=preferred_session_minutes,
                effective_efforts=effective_efforts,
                classifications=classifications,
                nc_result=nc_ok,
                soft_pacing_v2_enabled=soft_pacing_v2_enabled,
                end_buffer_ratio=end_buffer_ratio,
                max_consecutive_study_days=max_consecutive_study_days,
                daily_workload_cap_minutes=daily_workload_cap_minutes,
            )
            clean_tasks, clean_blocks = cls._finalize_allocation_output(final_tasks, final_blocks)
            return ScheduleAllocationResult(
                tasks=clean_tasks,
                schedule_blocks=clean_blocks,
                feasibility_verdict="VERIFIED_FEASIBLE",
                necessary_conditions=nc_ok,
                unscheduled_diagnostics=(),
                repairs_attempted=0,
            )

        nc_result = cls.verify_necessary_conditions(
            tasks,
            availability,
            start_date=start_date,
            target_date=target_date,
            dependencies=dependencies,
            existing_tasks=existing_tasks,
            daily_workload_cap_minutes=daily_workload_cap_minutes,
            effective_efforts=effective_efforts,
            classifications=classifications,
        )

        # Bounded critical-path repair pass whenever NC-1..3 hold (or to maximize placement)
        repair_strategies: tuple[tuple[str, bool], ...] = (
            ("CRITICAL_PATH_FIRST", False),
            ("LARGEST_NON_SPLITTABLE_FIRST", False),
            ("CRITICAL_PATH_FIRST", True),
        )
        if nc_result.verdict == "VERIFIED_FEASIBLE":
            for strat_name, allow_sliver in repair_strategies:
                repairs_attempted += 1
                cand_tasks, cand_blocks, cand_unplaced = cls._run_phase1_session_pass(
                    tasks,
                    ctx,
                    start_date=start_date,
                    target_date=target_date,
                    dependencies=dependencies,
                    milestone_order_map=milestone_order_map,
                    preferred_session_minutes=preferred_session_minutes,
                    effective_efforts=effective_efforts,
                    classifications=classifications,
                    priority_mode=strat_name,
                    allow_slot_sliver=allow_sliver,
                )
                if len(cand_unplaced) < len(best_unplaced):
                    best_tasks, best_blocks, best_unplaced = cand_tasks, cand_blocks, cand_unplaced
                if not best_unplaced:
                    final_tasks, final_blocks = cls._optimize_schedule_phase2(
                        tasks=tasks,
                        hard_tasks=best_tasks,
                        hard_blocks=best_blocks,
                        availability=availability,
                        ctx=ctx,
                        start_date=start_date,
                        target_date=target_date,
                        dependencies=dependencies,
                        existing_tasks=existing_tasks,
                        milestone_order_map=milestone_order_map,
                        preferred_session_minutes=preferred_session_minutes,
                        effective_efforts=effective_efforts,
                        classifications=classifications,
                        nc_result=nc_result,
                        soft_pacing_v2_enabled=soft_pacing_v2_enabled,
                        end_buffer_ratio=end_buffer_ratio,
                        max_consecutive_study_days=max_consecutive_study_days,
                        daily_workload_cap_minutes=daily_workload_cap_minutes,
                    )
                    clean_tasks, clean_blocks = cls._finalize_allocation_output(
                        final_tasks, final_blocks
                    )
                    return ScheduleAllocationResult(
                        tasks=clean_tasks,
                        schedule_blocks=clean_blocks,
                        feasibility_verdict="VERIFIED_FEASIBLE",
                        necessary_conditions=nc_result,
                        unscheduled_diagnostics=(),
                        repairs_attempted=repairs_attempted,
                    )

        # Still unplaced tasks: distinguish EXPLICIT_UNSCHEDULABLE (NC failed) vs HEURISTIC_ALLOCATION_INCOMPLETE
        nc_diag_by_task_id = {d.task_id: d for d in nc_result.unscheduled_diagnostics}
        verdict: FeasibilityVerdict = (
            "EXPLICIT_UNSCHEDULABLE"
            if nc_result.verdict == "EXPLICIT_UNSCHEDULABLE"
            else "HEURISTIC_ALLOCATION_INCOMPLETE"
        )
        _, preds_by_idx, _, _ = cls._build_dag_graph(best_tasks, dependencies)
        unplaced_set = set(best_unplaced)
        final_diags: list[UnscheduledTaskDiagnosticDTO] = []
        for idx in best_unplaced:
            t_item = best_tasks[idx]
            tid = str(t_item.get("task_id") or t_item.get("id") or f"task_{idx}")
            title = str(t_item.get("title") or tid)
            eff = effective_efforts[idx]
            is_ns, src = classifications[idx]
            if tid in nc_diag_by_task_id:
                diag = nc_diag_by_task_id[tid]
            elif verdict == "EXPLICIT_UNSCHEDULABLE":
                has_unplaced_pred = any(p_i in unplaced_set for p_i in preds_by_idx.get(idx, ()))
                if not nc_result.nc1_passed:
                    r_code = (
                        "CALENDAR_CONFLICT_SATURATION"
                        if nc_result.total_required_minutes
                        <= nc_result.raw_capacity_without_existing_minutes
                        else "TOTAL_EFFORT_EXCEEDS_HARD_CAPACITY"
                    )
                    msg = (
                        f"DEADLINE_CAPACITY_EXCEEDED: Không đủ thời gian rảnh trước ngày mục tiêu "
                        f"({r_code}: cần {nc_result.total_required_minutes}p, khả dụng {nc_result.total_hard_packable_minutes}p)."
                    )
                elif not nc_result.nc3_passed:
                    r_code = "CRITICAL_PATH_EXCEEDS_WINDOW"
                    msg = (
                        "DEADLINE_CAPACITY_EXCEEDED: Đường găng phụ thuộc vượt quá khung thời gian khả dụng "
                        "(CRITICAL_PATH_EXCEEDS_WINDOW)."
                    )
                elif has_unplaced_pred:
                    r_code = "BLOCKED_BY_UNSCHEDULABLE_PREDECESSOR"
                    msg = (
                        f"BLOCKED_BY_UNSCHEDULABLE_PREDECESSOR: Nhiệm vụ '{title}' ({eff}p) bị chặn "
                        "vì nhiệm vụ tiền đề không thể xếp lịch trong giới hạn hiện tại."
                    )
                else:
                    r_code = "TASK_EXCEEDS_CONTINUOUS_SLOT"
                    msg = f"TASK_EXCEEDS_CONTINUOUS_SLOT: Không có khung giờ liên tục đủ lớn cho '{title}' ({eff}p)."
                diag = UnscheduledTaskDiagnosticDTO(
                    task_id=tid,
                    title=title,
                    estimated_minutes=eff,
                    is_non_splittable=is_ns,
                    non_splittable_source=src,
                    verdict="EXPLICIT_UNSCHEDULABLE",
                    reason_code=r_code,
                    message=msg,
                    max_contiguous_window_minutes=nc_result.max_contiguous_window_minutes,
                    required_minutes=eff,
                )
            else:
                diag = UnscheduledTaskDiagnosticDTO(
                    task_id=tid,
                    title=title,
                    estimated_minutes=eff,
                    is_non_splittable=is_ns,
                    non_splittable_source=src,
                    verdict="HEURISTIC_ALLOCATION_INCOMPLETE",
                    reason_code="HEURISTIC_ALLOCATION_INCOMPLETE",
                    message=(
                        f"HEURISTIC_ALLOCATION_INCOMPLETE: Quỹ giờ tổng đạt điều kiện cần nhưng "
                        f"bộ xếp lịch chưa thể đóng gói '{title}' ({eff}p) vào các ô trống rời rạc."
                    ),
                    max_contiguous_window_minutes=nc_result.max_contiguous_window_minutes,
                    required_minutes=eff,
                )
            final_diags.append(diag)
            t_item["unscheduled_diagnostic"] = diag.to_dict()
            if diag.reason_code in (
                "TOTAL_EFFORT_EXCEEDS_HARD_CAPACITY",
                "CRITICAL_PATH_EXCEEDS_WINDOW",
            ):
                if nc_result.total_hard_packable_minutes <= 0:
                    t_item["unscheduled_reason"] = (
                        f"NO_AVAILABILITY_CONFIGURED: Chưa có khung giờ rảnh khả dụng ({diag.reason_code})"
                    )
                else:
                    t_item["unscheduled_reason"] = (
                        f"DEADLINE_CAPACITY_EXCEEDED: Không đủ thời gian rảnh trước ngày mục tiêu ({diag.reason_code})"
                    )
            else:
                t_item["unscheduled_reason"] = diag.message

        clean_tasks, clean_blocks = cls._finalize_allocation_output(best_tasks, best_blocks)
        return ScheduleAllocationResult(
            tasks=clean_tasks,
            schedule_blocks=clean_blocks,
            feasibility_verdict=verdict,
            necessary_conditions=nc_result,
            unscheduled_diagnostics=tuple(final_diags),
            repairs_attempted=repairs_attempted,
        )

    @classmethod
    def allocate_tasks_to_availability(
        cls,
        tasks: Sequence[dict[str, Any]],
        availability: AvailabilityConfigurationDTO,
        *,
        start_date: date,
        target_date: date | None = None,
        dependencies: Sequence[dict[str, Any]] | None = None,
        existing_tasks: Sequence[Any] | None = None,
        milestone_order_map: dict[str, int] | None = None,
        daily_workload_cap_minutes: int | None = None,
        hard_solver_v2_enabled: bool = True,
    ) -> list[dict[str, Any]]:
        """Deterministically allocate unscheduled atomic tasks into learner availability slots.

        - Preserves any task that already has a valid `scheduled_date`.
        - Topologically sorts unscheduled tasks by `dependencies` (`predecessor_id -> successor_id`),
          `milestone_order_map`, and `task_order` / original list index.
        - Respects `disabled_weekdays`, `existing_tasks` (EDF), Mode A (`QUOTA`) and Mode B (`FIXED_SLOTS`),
          and ensures `predecessor.end <= successor.start`.
        """
        if not tasks:
            return []

        cloned_tasks: list[dict[str, Any]] = [dict(t) for t in tasks]
        unscheduled_indices = [
            idx
            for idx, t in enumerate(cloned_tasks)
            if parse_iso_date(t.get("scheduled_date")) is None
        ]
        if not unscheduled_indices:
            return cloned_tasks

        if not hard_solver_v2_enabled:
            return cls._allocate_tasks_to_availability_legacy(
                cloned_tasks,
                availability,
                start_date=start_date,
                target_date=target_date,
                dependencies=dependencies,
                existing_tasks=existing_tasks,
                milestone_order_map=milestone_order_map,
            )

        classifications = [NonSplittableTaskClassifier.classify(t) for t in cloned_tasks]
        efforts = [_to_int(t.get("estimated_minutes"), 0) for t in cloned_tasks]
        ctx = cls._build_calendar_context(
            availability,
            existing_tasks=existing_tasks,
            daily_workload_cap_minutes=daily_workload_cap_minutes,
        )

        # Atomic single-block placement (each task placed in a single contiguous interval)
        atomic_classifications: list[tuple[bool, NonSplittableSource]] = [
            (True, src) for _, src in classifications
        ]
        best_tasks, _, best_unplaced = cls._run_phase1_session_pass(
            cloned_tasks,
            ctx,
            start_date=start_date,
            target_date=target_date,
            dependencies=dependencies,
            milestone_order_map=milestone_order_map,
            preferred_session_minutes=AI_BLOCK_MAX_MINUTES,
            effective_efforts=efforts,
            classifications=atomic_classifications,
            priority_mode="TOPOLOGICAL_DEFAULT",
            allow_slot_sliver=False,
        )
        if best_unplaced:
            nc_result = cls.verify_necessary_conditions(
                cloned_tasks,
                availability,
                start_date=start_date,
                target_date=target_date,
                dependencies=dependencies,
                existing_tasks=existing_tasks,
                daily_workload_cap_minutes=daily_workload_cap_minutes,
                effective_efforts=efforts,
                classifications=classifications,
            )
            if nc_result.verdict == "VERIFIED_FEASIBLE":
                for strat_name in ("CRITICAL_PATH_FIRST", "LARGEST_NON_SPLITTABLE_FIRST"):
                    cand_tasks, _, cand_unplaced = cls._run_phase1_session_pass(
                        cloned_tasks,
                        ctx,
                        start_date=start_date,
                        target_date=target_date,
                        dependencies=dependencies,
                        milestone_order_map=milestone_order_map,
                        preferred_session_minutes=AI_BLOCK_MAX_MINUTES,
                        effective_efforts=efforts,
                        classifications=atomic_classifications,
                        priority_mode=strat_name,
                        allow_slot_sliver=False,
                    )
                    if len(cand_unplaced) < len(best_unplaced):
                        best_tasks, best_unplaced = cand_tasks, cand_unplaced
                    if not best_unplaced:
                        break

        for idx, t in enumerate(best_tasks):
            is_ns, src = classifications[idx]
            t["is_non_splittable"] = is_ns
            t["non_splittable_source"] = src
        return best_tasks

    @classmethod
    def _allocate_tasks_to_availability_legacy(
        cls,
        cloned_tasks: list[dict[str, Any]],
        availability: AvailabilityConfigurationDTO,
        *,
        start_date: date,
        target_date: date | None = None,
        dependencies: Sequence[dict[str, Any]] | None = None,
        existing_tasks: Sequence[Any] | None = None,
        milestone_order_map: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        unscheduled_indices = [
            idx
            for idx, t in enumerate(cloned_tasks)
            if parse_iso_date(t.get("scheduled_date")) is None
        ]
        if not unscheduled_indices:
            return cloned_tasks

        weekday_names = (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
        disabled_days: set[str] = set()
        for raw_d in availability.disabled_weekdays:
            norm_d = normalize_weekday_name(raw_d)
            if norm_d:
                disabled_days.add(norm_d)

        quota_by_day: dict[str, int] = {}
        for k, v in availability.daily_quota_minutes.items():
            norm_k = normalize_weekday_name(k)
            if norm_k:
                quota_by_day[norm_k] = int(v)

        slots_by_day: dict[str, list[tuple[int, int]]] = {}
        for raw_slot in availability.availability_slots:
            if isinstance(raw_slot, AvailabilitySlotDTO):
                s_day = normalize_weekday_name(raw_slot.day_of_week)
                s_start = parse_hhmm_or_time(raw_slot.start_time)
                s_end = parse_hhmm_or_time(raw_slot.end_time)
            elif isinstance(raw_slot, dict):
                s_day = normalize_weekday_name(raw_slot.get("day_of_week"))
                s_start = parse_hhmm_or_time(raw_slot.get("start_time"))
                s_end = parse_hhmm_or_time(raw_slot.get("end_time"))
            else:
                continue
            if not s_day or s_start is None or s_end is None:
                continue
            start_min = s_start.hour * 60 + s_start.minute
            end_min = s_end.hour * 60 + s_end.minute
            if end_min <= start_min:
                end_min += 1440
            slots_by_day.setdefault(s_day, []).append((start_min, end_min))

        for d_key, raw_intervals in list(slots_by_day.items()):
            sorted_iv = sorted(raw_intervals, key=lambda x: (x[0], x[1]))
            merged: list[tuple[int, int]] = []
            for iv_s, iv_e in sorted_iv:
                if merged and iv_s <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], iv_e))
                else:
                    merged.append((iv_s, iv_e))
            slots_by_day[d_key] = merged

        daily_used_minutes: dict[date, int] = {}
        daily_intervals: dict[date, list[tuple[int, int]]] = {}
        task_end_anchor: dict[str, tuple[date, int]] = {}

        for ex in existing_tasks or ():
            status = (
                str(ex.get("status", "TODO"))
                if isinstance(ex, dict)
                else str(getattr(ex, "status", "TODO"))
            ).upper()
            if status in ("CANCELLED", "COMPLETED"):
                continue
            if isinstance(ex, dict):
                ex_date = parse_iso_date(ex.get("scheduled_date"))
                ex_mins = _to_int(ex.get("estimated_minutes"), 0)
                ex_start = parse_iso_datetime(
                    ex.get("planned_start_at") or ex.get("scheduled_start")
                )
                ex_end = parse_iso_datetime(ex.get("planned_end_at") or ex.get("scheduled_end"))
            else:
                ex_date = parse_iso_date(getattr(ex, "scheduled_date", None))
                ex_mins = _to_int(getattr(ex, "estimated_minutes", 0), 0)
                ex_start = parse_iso_datetime(
                    getattr(ex, "planned_start_at", None) or getattr(ex, "scheduled_start", None)
                )
                ex_end = parse_iso_datetime(
                    getattr(ex, "planned_end_at", None) or getattr(ex, "scheduled_end", None)
                )

            ex_start = _in_user_timezone(ex_start, availability.timezone)
            ex_end = _in_user_timezone(ex_end, availability.timezone)

            if ex_start is not None and ex_end is not None:
                s_m = ex_start.hour * 60 + ex_start.minute
                e_m = s_m + max(ex_mins, int((ex_end - ex_start).total_seconds() // 60))
                _record_occupied_interval(
                    daily_intervals,
                    daily_used_minutes,
                    ex_start.date(),
                    s_m,
                    e_m,
                )
            elif ex_date is not None and ex_mins > 0:
                daily_used_minutes[ex_date] = daily_used_minutes.get(ex_date, 0) + ex_mins

        id_to_idx: dict[str, int] = {}
        for idx, t in enumerate(cloned_tasks):
            tid = str(t.get("task_id") or t.get("id") or f"idx-{idx}")
            id_to_idx[tid] = idx
            s_date = parse_iso_date(t.get("scheduled_date"))
            if s_date is not None:
                dur = max(1, _to_int(t.get("estimated_minutes"), 60))
                st_dt = _in_user_timezone(
                    parse_iso_datetime(t.get("scheduled_start")), availability.timezone
                )
                en_dt = _in_user_timezone(
                    parse_iso_datetime(t.get("scheduled_end")), availability.timezone
                )
                if st_dt is not None and en_dt is not None:
                    base_d = st_dt.date()
                    s_m = st_dt.hour * 60 + st_dt.minute
                    e_m = s_m + max(dur, int((en_dt - st_dt).total_seconds() // 60))
                else:
                    base_d = s_date
                    s_m = 19 * 60
                    e_m = s_m + dur
                _record_occupied_interval(daily_intervals, daily_used_minutes, base_d, s_m, e_m)
                end_d = base_d + timedelta(days=e_m // 1440)
                end_m = e_m % 1440 if e_m >= 1440 else e_m
                task_end_anchor[tid] = (end_d, end_m)

        ms_order: dict[str, int] = dict(milestone_order_map or {})
        for t in cloned_tasks:
            mid = str(t.get("milestone_id") or "")
            if mid and mid not in ms_order:
                ms_order[mid] = len(ms_order) + 1

        preds_by_idx: dict[int, list[int]] = {i: [] for i in range(len(cloned_tasks))}
        succs_by_idx: dict[int, list[int]] = {i: [] for i in range(len(cloned_tasks))}
        in_degree: dict[int, int] = {i: 0 for i in unscheduled_indices}

        for dep in dependencies or ():
            if not isinstance(dep, dict):
                continue
            p_id = str(dep.get("predecessor_id") or "")
            s_id = str(dep.get("successor_id") or "")
            p_idx = id_to_idx.get(p_id)
            s_idx = id_to_idx.get(s_id)
            if p_idx is not None and s_idx is not None and p_idx != s_idx:
                preds_by_idx[s_idx].append(p_idx)
                succs_by_idx[p_idx].append(s_idx)
                if p_idx in in_degree and s_idx in in_degree:
                    in_degree[s_idx] += 1

        def _sort_key(i: int) -> tuple[int, int, int]:
            t_item = cloned_tasks[i]
            mid = str(t_item.get("milestone_id") or "")
            m_seq = ms_order.get(mid, 999)
            t_ord = _to_int(t_item.get("task_order"), i)
            return (m_seq, t_ord, i)

        ready = sorted([i for i, deg in in_degree.items() if deg == 0], key=_sort_key)
        ordered_unscheduled: list[int] = []
        while ready:
            curr = ready.pop(0)
            ordered_unscheduled.append(curr)
            for nxt in succs_by_idx.get(curr, []):
                if nxt in in_degree:
                    in_degree[nxt] -= 1
                    if in_degree[nxt] == 0:
                        ready.append(nxt)
                        ready.sort(key=_sort_key)

        if len(ordered_unscheduled) < len(unscheduled_indices):
            remaining = [i for i in unscheduled_indices if i not in ordered_unscheduled]
            remaining.sort(key=_sort_key)
            ordered_unscheduled.extend(remaining)

        mode_upper = (availability.mode or "QUOTA").upper()

        for idx in ordered_unscheduled:
            t_item = cloned_tasks[idx]
            tid = str(t_item.get("task_id") or t_item.get("id") or f"idx-{idx}")
            duration = _to_int(t_item.get("estimated_minutes"), 0)
            if duration <= 0:
                t_item["scheduled_date"] = None
                continue

            min_date = start_date
            min_minute_on_min_date = 0
            has_unplaced_predecessor = False
            for p_idx in preds_by_idx.get(idx, []):
                p_tid = str(
                    cloned_tasks[p_idx].get("task_id")
                    or cloned_tasks[p_idx].get("id")
                    or f"idx-{p_idx}"
                )
                anchor = task_end_anchor.get(p_tid)
                if anchor is None:
                    has_unplaced_predecessor = True
                    break
                p_date, p_end_min = anchor
                if p_date > min_date:
                    min_date = p_date
                    min_minute_on_min_date = p_end_min
                elif p_date == min_date:
                    min_minute_on_min_date = max(min_minute_on_min_date, p_end_min)

            if has_unplaced_predecessor:
                t_item["scheduled_date"] = None
                t_item["scheduled_start"] = None
                t_item["scheduled_end"] = None
                continue

            allocated = False
            for day_step in range(366):
                cand_date = min_date + timedelta(days=day_step)
                if target_date is not None and cand_date > target_date:
                    break
                wname = weekday_names[cand_date.weekday()]
                if wname in disabled_days:
                    continue

                used_today = daily_used_minutes.get(cand_date, 0)
                earliest_min = min_minute_on_min_date if day_step == 0 else 0

                if mode_upper in ("FIXED_SLOTS", "MODE_B", "SLOTS"):
                    day_slots = slots_by_day.get(wname, [])
                    if not day_slots:
                        continue
                    slot_capacity = min(
                        MAX_DAILY_PLANNED_MINUTES,
                        sum(max(0, e - s) for s, e in day_slots),
                    )
                    if used_today + duration > slot_capacity:
                        continue

                    occupied = sorted(
                        daily_intervals.get(cand_date, []), key=lambda x: (x[0], x[1])
                    )
                    chosen_window: tuple[int, int] | None = None
                    for sl_s, sl_e in day_slots:
                        cand_s = max(sl_s, earliest_min)
                        for occ_s, occ_e in occupied:
                            if cand_s + duration <= occ_s:
                                break
                            if cand_s < occ_e:
                                cand_s = max(cand_s, occ_e)
                        if cand_s + duration <= sl_e:
                            chosen_window = (cand_s, cand_s + duration)
                            break

                    if chosen_window is None:
                        continue

                    win_s, win_e = chosen_window
                else:
                    day_quota = min(
                        MAX_DAILY_PLANNED_MINUTES,
                        quota_by_day.get(wname, availability.default_daily_quota_minutes),
                    )
                    if day_quota <= 0 or used_today + duration > day_quota:
                        continue

                    occupied = sorted(
                        daily_intervals.get(cand_date, []), key=lambda x: (x[0], x[1])
                    )
                    default_start = 9 * 60 if occupied else 19 * 60
                    cand_s = max(default_start, earliest_min)
                    for occ_s, occ_e in occupied:
                        if cand_s + duration <= occ_s:
                            break
                        if cand_s < occ_e:
                            cand_s = max(cand_s, occ_e)
                    if cand_s + duration > 1440:
                        continue
                    win_s, win_e = cand_s, cand_s + duration

                sh, sm = (win_s // 60) % 24, win_s % 60
                end_day_offset = win_e // 1440
                end_date = cand_date + timedelta(days=end_day_offset)
                eh, em = (win_e % 1440) // 60, win_e % 60
                user_tz = ZoneInfo(availability.timezone)
                local_start = datetime.combine(cand_date, time(sh, sm), tzinfo=user_tz)
                local_end = datetime.combine(end_date, time(eh, em), tzinfo=user_tz)

                t_item["scheduled_date"] = cand_date.isoformat()
                t_item["scheduled_start"] = local_start.isoformat()
                t_item["scheduled_end"] = local_end.isoformat()

                _record_occupied_interval(
                    daily_intervals,
                    daily_used_minutes,
                    cand_date,
                    win_s,
                    win_e,
                )
                task_end_anchor[tid] = (
                    end_date,
                    win_e % 1440 if end_day_offset > 0 else win_e,
                )
                allocated = True
                break

            if not allocated:
                t_item["scheduled_date"] = None
                t_item["scheduled_start"] = None
                t_item["scheduled_end"] = None

        return cloned_tasks

    @classmethod
    def calculate_available_capacity_minutes(
        cls,
        availability: AvailabilityConfigurationDTO,
        *,
        start_date: date,
        target_date: date | None,
        existing_tasks: Sequence[Any] | None = None,
        daily_workload_cap_minutes: int | None = None,
    ) -> int:
        """Compute total net free study minutes from `start_date` through `target_date`."""
        end_date = target_date if target_date is not None else (start_date + timedelta(days=29))
        if end_date < start_date:
            return 0
        span_days = min(366, (end_date - start_date).days + 1)

        disabled_days = {
            norm
            for raw_d in availability.disabled_weekdays
            if (norm := normalize_weekday_name(raw_d))
        }
        quota_by_day = {
            norm: int(val)
            for k, val in availability.daily_quota_minutes.items()
            if (norm := normalize_weekday_name(k))
        }
        slots_by_day: dict[str, int] = {}
        for slot in availability.availability_slots:
            if isinstance(slot, AvailabilitySlotDTO):
                if not slot.is_active:
                    continue
                s_day = normalize_weekday_name(slot.day_of_week)
                s_start, s_end = _slot_minute_range(slot)
                dur = max(0, s_end - s_start)
            elif isinstance(slot, dict):
                if slot.get("is_active", True) is False:
                    continue
                s_day = normalize_weekday_name(slot.get("day_of_week"))
                st = parse_hhmm_or_time(slot.get("start_time"))
                en = parse_hhmm_or_time(slot.get("end_time"))
                if st is None or en is None:
                    continue
                s_m = st.hour * 60 + st.minute
                e_m = en.hour * 60 + en.minute
                if e_m <= s_m:
                    e_m += 1440
                dur = max(0, e_m - s_m)
            else:
                continue
            if s_day:
                slots_by_day[s_day] = slots_by_day.get(s_day, 0) + dur

        used_by_date: dict[date, int] = {}
        for ext in existing_tasks or ():
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
            ext_mins = (
                _to_int(ext.get("estimated_minutes"), 0)
                if isinstance(ext, dict)
                else _to_int(getattr(ext, "estimated_minutes", 0), 0)
            )
            if ext_date is not None and ext_mins > 0:
                used_by_date[ext_date] = used_by_date.get(ext_date, 0) + ext_mins

        weekday_names = (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
        mode_upper = (availability.mode or "MODE_A").strip().upper()
        cap_ceiling = (
            min(MAX_DAILY_PLANNED_MINUTES, max(10, int(daily_workload_cap_minutes)))
            if daily_workload_cap_minutes is not None
            else MAX_DAILY_PLANNED_MINUTES
        )

        total_free = 0
        for offset in range(span_days):
            day = start_date + timedelta(days=offset)
            wname = weekday_names[day.weekday()]
            if wname in disabled_days:
                continue
            if mode_upper in ("FIXED_SLOTS", "MODE_B", "SLOTS"):
                raw_cap = min(cap_ceiling, slots_by_day.get(wname, 0))
            else:
                raw_cap = min(
                    cap_ceiling,
                    quota_by_day.get(wname, availability.default_daily_quota_minutes),
                )
            total_free += max(0, raw_cap - used_by_date.get(day, 0))
        return total_free

    @classmethod
    def calculate_hard_packable_capacity(
        cls,
        availability: AvailabilityConfigurationDTO,
        *,
        start_date: date,
        target_date: date | None,
        existing_tasks: Sequence[Any] | None = None,
        daily_workload_cap_minutes: int | None = None,
        min_unit_minutes: int = AI_BLOCK_MIN_MINUTES,
    ) -> tuple[int, dict[date, int]]:
        """Compute 100% hard slot-packable minutes and per-day map in `[start_date, target_date]`."""
        ctx = cls._build_calendar_context(
            availability,
            existing_tasks=existing_tasks,
            daily_workload_cap_minutes=daily_workload_cap_minutes,
        )
        end_date = target_date if target_date is not None else (start_date + timedelta(days=29))
        if end_date < start_date:
            return 0, {}

        span_days = min(366, (end_date - start_date).days + 1)
        min_unit = max(1, int(min_unit_minutes))
        day_packable_map: dict[date, int] = {}
        last_offset = span_days - 1
        for offset in range(span_days):
            d = start_date + timedelta(days=offset)
            free_ivs, rem_cap, _ = cls._day_free_windows(
                ctx,
                d,
                earliest_min=0,
                used_today=ctx["existing_used"].get(d, 0),
                occupied=ctx["existing_intervals"].get(d, ()),
                next_day_occupied=ctx["existing_intervals"].get(d + timedelta(days=1), ()),
            )
            usable_ivs = [(s, e) for s, e in free_ivs if (e - s) >= min_unit]
            if offset < last_offset:
                sum_usable = sum(min(1440, e) - s for s, e in usable_ivs if s < 1440)
            else:
                sum_usable = sum(e - s for s, e in usable_ivs)
            day_packable_map[d] = min(rem_cap, sum_usable)

        return sum(day_packable_map.values()), day_packable_map

    @classmethod
    def allocate_task_sessions(
        cls,
        tasks: Sequence[dict[str, Any]],
        availability: AvailabilityConfigurationDTO,
        *,
        start_date: date,
        target_date: date | None = None,
        dependencies: Sequence[dict[str, Any]] | None = None,
        existing_tasks: Sequence[Any] | None = None,
        milestone_order_map: dict[str, int] | None = None,
        preferred_session_minutes: int = 60,
        estimation_bias_beta: float = 1.0,
        peak_productivity_slots: Sequence[str] = (),
        daily_workload_cap_minutes: int | None = None,
        buffer_minutes_per_week: int = 0,
        include_weekly_buffers: bool = False,
        hard_solver_v2_enabled: bool = True,
        soft_pacing_v2_enabled: bool = True,
        end_buffer_ratio: float = 0.12,
        max_consecutive_study_days: int = 5,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Place task effort in bounded sessions while retaining the task learning graph."""
        if hard_solver_v2_enabled:
            res = cls.allocate_task_sessions_with_diagnostics(
                tasks,
                availability,
                start_date=start_date,
                target_date=target_date,
                dependencies=dependencies,
                existing_tasks=existing_tasks,
                milestone_order_map=milestone_order_map,
                preferred_session_minutes=preferred_session_minutes,
                estimation_bias_beta=estimation_bias_beta,
                peak_productivity_slots=peak_productivity_slots,
                daily_workload_cap_minutes=daily_workload_cap_minutes,
                buffer_minutes_per_week=buffer_minutes_per_week,
                include_weekly_buffers=include_weekly_buffers,
                soft_pacing_v2_enabled=soft_pacing_v2_enabled,
                end_buffer_ratio=end_buffer_ratio,
                max_consecutive_study_days=max_consecutive_study_days,
            )
            return res.tasks, res.schedule_blocks

        _ = (
            peak_productivity_slots,
            daily_workload_cap_minutes,
            buffer_minutes_per_week,
            include_weekly_buffers,
        )
        mode_b = availability.mode.upper() in ("MODE_B", "FIXED_SLOTS", "SLOTS")
        if mode_b:
            slot_lengths = [
                end - start
                for slot in availability.availability_slots
                if isinstance(slot, AvailabilitySlotDTO)
                for start, end in [_slot_minute_range(slot)]
                if end > start and slot.is_active
            ]
            capacity = max(slot_lengths, default=0)
        else:
            quotas = {
                normalize_weekday_name(day): int(minutes)
                for day, minutes in availability.daily_quota_minutes.items()
            }
            capacity = max(
                (
                    quotas.get(day, availability.default_daily_quota_minutes)
                    for day in (
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    )
                    if day not in availability.disabled_weekdays
                ),
                default=0,
            )
        session_limit = min(max(10, preferred_session_minutes), 120, capacity)
        if session_limit < 10:
            return ([{**task, "scheduled_date": None} for task in tasks], [])

        clamped_beta = max(0.7, min(1.8, float(estimation_bias_beta)))
        expanded: list[dict[str, Any]] = []
        expanded_deps: list[dict[str, Any]] = []
        part_ids: dict[str, list[str]] = {}
        effective_efforts: dict[str, int] = {}
        for index, task in enumerate(tasks):
            task_id = str(task.get("task_id") or task.get("id") or f"task_{index}")
            raw_effort = _to_int(task.get("estimated_minutes"), 0)
            if (
                AI_BLOCK_MIN_MINUTES <= raw_effort <= AI_BLOCK_MAX_MINUTES
                and abs(clamped_beta - 1.0) > 1e-6
            ):
                effort = max(
                    AI_BLOCK_MIN_MINUTES,
                    min(AI_BLOCK_MAX_MINUTES, int(round(raw_effort * clamped_beta))),
                )
            else:
                effort = raw_effort
            effective_efforts[task_id] = effort
            if effort <= 0:
                count = 1
            else:
                count = (effort + session_limit - 1) // session_limit
            base, extra = divmod(effort, count)
            if base < 10:
                return ([{**item, "scheduled_date": None} for item in tasks], [])
            ids: list[str] = []
            for sequence in range(1, count + 1):
                part_id = f"{task_id}::session::{sequence}"
                ids.append(part_id)
                expanded.append(
                    {
                        "task_id": part_id,
                        "milestone_id": task.get("milestone_id"),
                        "task_order": index,
                        "estimated_minutes": base + (1 if sequence <= extra else 0),
                    }
                )
                if sequence > 1:
                    expanded_deps.append({"predecessor_id": ids[-2], "successor_id": part_id})
            part_ids[task_id] = ids

        for dependency in dependencies or ():
            predecessor = part_ids.get(str(dependency.get("predecessor_id")))
            successor = part_ids.get(str(dependency.get("successor_id")))
            if predecessor and successor:
                expanded_deps.append(
                    {"predecessor_id": predecessor[-1], "successor_id": successor[0]}
                )

        placed = cls.allocate_tasks_to_availability(
            expanded,
            availability,
            start_date=start_date,
            target_date=target_date,
            dependencies=expanded_deps,
            existing_tasks=existing_tasks,
            milestone_order_map=milestone_order_map,
            hard_solver_v2_enabled=False,
        )
        placed_by_id = {str(part["task_id"]): part for part in placed}
        scheduled_tasks: list[dict[str, Any]] = []
        blocks: list[dict[str, Any]] = []
        for index, task in enumerate(tasks):
            task_id = str(task.get("task_id") or task.get("id") or f"task_{index}")
            parts = [placed_by_id[part_id] for part_id in part_ids[task_id]]
            scheduled = dict(task)
            if effective_efforts.get(task_id, 0) > 0:
                scheduled["estimated_minutes"] = effective_efforts[task_id]
            if all(part.get("scheduled_start") and part.get("scheduled_end") for part in parts):
                scheduled["scheduled_date"] = parts[0]["scheduled_date"]
                scheduled["scheduled_start"] = parts[0]["scheduled_start"]
                scheduled["scheduled_end"] = parts[-1]["scheduled_end"]
                for sequence, part in enumerate(parts, start=1):
                    blocks.append(
                        {
                            "task_id": task_id,
                            "sequence_in_task": sequence,
                            "block_date": part["scheduled_date"],
                            "scheduled_start": part["scheduled_start"],
                            "scheduled_end": part["scheduled_end"],
                            "scheduled_duration_minutes": part["estimated_minutes"],
                        }
                    )
            else:
                scheduled["scheduled_date"] = None
                scheduled["scheduled_start"] = None
                scheduled["scheduled_end"] = None
            scheduled_tasks.append(scheduled)
        return scheduled_tasks, blocks
