from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from src.planning.domain.services.validation_types import (
    MAX_DAILY_PLANNED_MINUTES,
    SOFT_OVERFLOW_MAX_MINUTES,
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    ConstraintViolationDTO,
    SoftOverflowWarningDTO,
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

        # Group proposed tasks by scheduled_date
        tasks_by_date: dict[date, list[tuple[int, dict[str, object]]]] = {}
        for idx, raw_task in enumerate(tasks):
            sched_date = parse_iso_date(raw_task.get("scheduled_date"))
            if sched_date is None:
                continue
            tasks_by_date.setdefault(sched_date, []).append((idx, raw_task))

        # Group existing active roadmap tasks by scheduled_date
        existing_minutes_by_date: dict[date, int] = {}
        existing_edf_by_date: dict[date, list[tuple[str, int, date | None]]] = {}
        for ext in existing_tasks:
            status = str(getattr(ext, "status", "TODO")).upper()
            if status in ("CANCELLED", "COMPLETED"):
                continue
            ext_date = parse_iso_date(getattr(ext, "scheduled_date", None))
            if ext_date is None:
                continue
            ext_mins = int(getattr(ext, "estimated_minutes", 0) or 0)
            ext_title = str(getattr(ext, "title", "Existing Task"))
            ext_target = parse_iso_date(getattr(ext, "roadmap_target_date", None))
            existing_minutes_by_date[ext_date] = (
                existing_minutes_by_date.get(ext_date, 0) + ext_mins
            )
            existing_edf_by_date.setdefault(ext_date, []).append((ext_title, ext_mins, ext_target))

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
            start_t = parse_hhmm_or_time(
                raw_task.get("scheduled_start") or raw_task.get("start_time")
            )
            end_t = parse_hhmm_or_time(raw_task.get("scheduled_end") or raw_task.get("end_time"))

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

        # Group existing active tasks by scheduled_date for cross-roadmap overlap check (OS-04)
        existing_by_date: dict[date, list[tuple[str, int, int, date | None]]] = {}
        for ext in existing_tasks:
            status = str(getattr(ext, "status", "TODO")).upper()
            if status in ("CANCELLED", "COMPLETED"):
                continue
            ext_date = parse_iso_date(getattr(ext, "scheduled_date", None))
            ext_start_dt = parse_iso_datetime(getattr(ext, "scheduled_start", None))
            ext_end_dt = parse_iso_datetime(getattr(ext, "scheduled_end", None))
            ext_start_t = parse_hhmm_or_time(getattr(ext, "scheduled_start", None))
            ext_end_t = parse_hhmm_or_time(getattr(ext, "scheduled_end", None))
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
            existing_by_date.setdefault(ext_date, []).append(
                (ext_title, ext_range[0], ext_range[1], ext_target)
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

            # 1. Check self-overlap within proposed tasks on the same date
            for i in range(len(sorted_entries) - 1):
                idx1, task1, _, s1, e1, _ = sorted_entries[i]
                idx2, task2, _, s2, e2, _ = sorted_entries[i + 1]
                if s1 < e2 and s2 < e1:
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=idx2,
                            field="scheduled_start",
                            rule_code="TASK_TIME_OVERLAP",
                            expected_bound=f"Không chồng lấn với nhiệm vụ #{idx1} ('{task1.get('title')}')",
                            actual_value=f"Nhiệm vụ #{idx1} và #{idx2} ('{task2.get('title')}') trùng giờ trong ngày {sched_date.isoformat()}",
                            suggested_fix="Dời khung giờ bắt đầu của nhiệm vụ sau thời điểm kết thúc của nhiệm vụ trước.",
                        )
                    )

            # 2. Check Cross-Roadmap EDF overlap against existing active tasks
            day_existing = existing_by_date.get(sched_date, [])
            for idx, raw_task, _, t_s, t_e, _ in sorted_entries:
                for ext_title, occ_s, occ_e, ext_target in day_existing:
                    if t_s < occ_e and occ_s < t_e:
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
    ) -> list[dict[str, Any]]:
        """Deterministically allocate unscheduled atomic tasks into learner availability slots.

        - Preserves any task that already has a valid `scheduled_date`.
        - Topologically sorts unscheduled tasks by `dependencies` (`predecessor_id -> successor_id`),
          `milestone_order_map`, and `task_order` / original list index.
        - Respects `disabled_weekdays`, `existing_tasks` (EDF), Mode A (`QUOTA`) and Mode B (`FIXED_SLOTS`),
          and ensures `predecessor.end <= successor.start`.
        """
        _ = target_date
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

        # 1. Seed existing committed tasks
        for ex in existing_tasks or ():
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
                ex_start = parse_iso_datetime(getattr(ex, "planned_start_at", None))
                ex_end = parse_iso_datetime(getattr(ex, "planned_end_at", None))

            if ex_date is not None and ex_mins > 0:
                daily_used_minutes[ex_date] = daily_used_minutes.get(ex_date, 0) + ex_mins
                if ex_start is not None and ex_end is not None:
                    s_m = ex_start.hour * 60 + ex_start.minute
                    e_m = s_m + max(ex_mins, int((ex_end - ex_start).total_seconds() // 60))
                    daily_intervals.setdefault(ex_date, []).append((s_m, e_m))

        # 2. Seed already-scheduled tasks in cloned_tasks
        id_to_idx: dict[str, int] = {}
        for idx, t in enumerate(cloned_tasks):
            tid = str(t.get("task_id") or t.get("id") or f"idx-{idx}")
            id_to_idx[tid] = idx
            s_date = parse_iso_date(t.get("scheduled_date"))
            if s_date is not None:
                dur = max(1, _to_int(t.get("estimated_minutes"), 60))
                daily_used_minutes[s_date] = daily_used_minutes.get(s_date, 0) + dur
                st_dt = parse_iso_datetime(t.get("scheduled_start"))
                en_dt = parse_iso_datetime(t.get("scheduled_end"))
                if st_dt is not None and en_dt is not None:
                    s_m = st_dt.hour * 60 + st_dt.minute
                    e_m = s_m + max(dur, int((en_dt - st_dt).total_seconds() // 60))
                else:
                    s_m = 19 * 60
                    e_m = s_m + dur
                daily_intervals.setdefault(s_date, []).append((s_m, e_m))
                task_end_anchor[tid] = (s_date, e_m)

        # 3. Build topological order for unscheduled tasks
        ms_order: dict[str, int] = dict(milestone_order_map or {})
        for idx, t in enumerate(cloned_tasks):
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

        # 4. Allocate each unscheduled task
        for idx in ordered_unscheduled:
            t_item = cloned_tasks[idx]
            tid = str(t_item.get("task_id") or t_item.get("id") or f"idx-{idx}")
            duration = max(30, min(120, _to_int(t_item.get("estimated_minutes"), 60)))
            t_item["estimated_minutes"] = duration

            min_date = start_date
            min_minute_on_min_date = 0
            for p_idx in preds_by_idx.get(idx, []):
                p_tid = str(
                    cloned_tasks[p_idx].get("task_id")
                    or cloned_tasks[p_idx].get("id")
                    or f"idx-{p_idx}"
                )
                anchor = task_end_anchor.get(p_tid)
                if anchor is not None:
                    p_date, p_end_min = anchor
                    if p_date > min_date:
                        min_date = p_date
                        min_minute_on_min_date = p_end_min
                    elif p_date == min_date:
                        min_minute_on_min_date = max(min_minute_on_min_date, p_end_min)

            allocated = False
            for day_step in range(366):
                cand_date = min_date + timedelta(days=day_step)
                wname = weekday_names[cand_date.weekday()]
                if wname in disabled_days:
                    continue

                used_today = daily_used_minutes.get(cand_date, 0)
                earliest_min = min_minute_on_min_date if day_step == 0 else 0

                if mode_upper == "FIXED_SLOTS":
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

                t_item["scheduled_date"] = cand_date.isoformat()
                t_item["scheduled_start"] = f"{cand_date.isoformat()}T{sh:02d}:{sm:02d}:00+00:00"
                t_item["scheduled_end"] = f"{end_date.isoformat()}T{eh:02d}:{em:02d}:00+00:00"

                daily_used_minutes[cand_date] = used_today + duration
                daily_intervals.setdefault(cand_date, []).append((win_s, win_e))
                task_end_anchor[tid] = (
                    end_date,
                    win_e % 1440 if end_day_offset > 0 else win_e,
                )
                allocated = True
                break

            if not allocated:
                fallback_date = min_date
                t_item["scheduled_date"] = fallback_date.isoformat()
                t_item["scheduled_start"] = f"{fallback_date.isoformat()}T19:00:00+00:00"
                end_m = 19 * 60 + duration
                t_item["scheduled_end"] = (
                    f"{fallback_date.isoformat()}T{(end_m // 60) % 24:02d}:{end_m % 60:02d}:00+00:00"
                )

        return cloned_tasks
