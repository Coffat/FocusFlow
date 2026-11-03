from collections.abc import Sequence
from datetime import time

from src.account.domain.models.availability import (
    AvailabilityMode,
    AvailabilityProfile,
    AvailabilityValidationResult,
    ProposedTaskSlot,
    TimeSlot,
)


def _to_minute_range(t_start: time, t_end: time, end_day_offset: int = 0) -> tuple[int, int]:
    start_m = t_start.hour * 60 + t_start.minute
    end_m = t_end.hour * 60 + t_end.minute + (end_day_offset * 1440)
    return start_m, end_m


def _minutes_to_slot(start_m: int, end_m: int) -> TimeSlot:
    start_time = time(hour=(start_m % 1440) // 60, minute=start_m % 60)
    end_offset = (end_m // 1440) - (start_m // 1440)
    end_time = time(hour=(end_m % 1440) // 60, minute=end_m % 60)
    return TimeSlot(
        start_time=start_time,
        end_time=end_time,
        end_day_offset=end_offset,
    )


def _merge_contiguous_slot_ranges(slots: Sequence[TimeSlot]) -> list[tuple[int, int]]:
    if not slots:
        return []
    sorted_ranges = sorted((s.minute_range() for s in slots), key=lambda r: r[0])
    merged: list[tuple[int, int]] = [sorted_ranges[0]]
    for cur_s, cur_e in sorted_ranges[1:]:
        prev_s, prev_e = merged[-1]
        if cur_s <= prev_e:
            merged[-1] = (prev_s, max(prev_e, cur_e))
        else:
            merged.append((cur_s, cur_e))
    return merged


class HybridAvailabilityRuleEngine:
    """Pure domain service enforcing Hybrid Availability rules (Mode A & Mode B)."""

    @staticmethod
    def validate_daily_ceiling(
        profile: AvailabilityProfile,
        day_of_week: str,
        total_minutes: int,
    ) -> AvailabilityValidationResult:
        """Validate daily ceiling for Mode A (Hard Ceiling Gate)."""
        day_name = day_of_week.lower()
        day_schedule = profile.weekly_schedule.days.get(day_name)

        if not day_schedule or not day_schedule.enabled:
            if total_minutes > 0:
                return AvailabilityValidationResult(
                    is_valid=False,
                    overflow_minutes=total_minutes,
                    violation_reasons=(
                        f"Ngày {day_name} đã tắt hoặc không có lịch học nhưng có nhiệm vụ {total_minutes} phút.",
                    ),
                )
            return AvailabilityValidationResult(is_valid=True)

        ceiling_minutes = int(day_schedule.quota_hours * 60)
        if total_minutes > ceiling_minutes:
            overflow = total_minutes - ceiling_minutes
            return AvailabilityValidationResult(
                is_valid=False,
                overflow_minutes=overflow,
                violation_reasons=(
                    f"Tổng thời gian nhiệm vụ ({total_minutes}m) vượt quá trần cho phép ({ceiling_minutes}m) vào {day_name}.",
                ),
            )

        return AvailabilityValidationResult(is_valid=True, overflow_minutes=0)

    @staticmethod
    def subtract_intervals(
        base_slots: Sequence[TimeSlot],
        occupied: Sequence[tuple[time, time, int] | tuple[time, time]],
    ) -> list[TimeSlot]:
        """Interval subtraction algorithm (O(N log N + N*M)) discarding pieces < 30m."""
        normalized_occupied: list[tuple[int, int]] = []
        for occ in occupied:
            if len(occ) == 3:
                s_t, e_t, offset = occ
            else:
                s_t, e_t = occ
                offset = 0
            normalized_occupied.append(_to_minute_range(s_t, e_t, offset))

        sorted_occupied = sorted(normalized_occupied, key=lambda x: x[0])
        current_segments = [slot.minute_range() for slot in base_slots]

        for occ_start, occ_end in sorted_occupied:
            next_segments: list[tuple[int, int]] = []
            for seg_start, seg_end in current_segments:
                if seg_end <= occ_start or seg_start >= occ_end:
                    next_segments.append((seg_start, seg_end))
                else:
                    if seg_start < occ_start and (occ_start - seg_start) >= 30:
                        next_segments.append((seg_start, occ_start))
                    if seg_end > occ_end and (seg_end - occ_end) >= 30:
                        next_segments.append((occ_end, seg_end))
            current_segments = next_segments

        return [_minutes_to_slot(s, e) for s, e in current_segments]

    @classmethod
    def calculate_remaining_capacity(
        cls,
        profile: AvailabilityProfile,
        day_of_week: str,
        occupied_intervals: Sequence[tuple[time, time, int] | tuple[time, time]] = (),
        allocated_minutes: int = 0,
    ) -> int | list[TimeSlot]:
        """Calculate remaining learning capacity for cross-roadmap or calendar sync."""
        day_name = day_of_week.lower()
        day_schedule = profile.weekly_schedule.days.get(day_name)

        if profile.mode == AvailabilityMode.MODE_A:
            if not day_schedule or not day_schedule.enabled:
                return 0
            ceiling = int(day_schedule.quota_hours * 60)
            return max(0, ceiling - allocated_minutes)

        if not day_schedule or not day_schedule.enabled:
            return []
        return cls.subtract_intervals(day_schedule.time_slots, occupied_intervals)

    @staticmethod
    def validate_proposal_against_slots(
        profile: AvailabilityProfile,
        day_of_week: str,
        proposed_tasks: Sequence[ProposedTaskSlot],
        occupied_intervals: Sequence[tuple[time, time, int] | tuple[time, time]] = (),
    ) -> AvailabilityValidationResult:
        """Validate proposed tasks against Mode B slots with Soft Overflow (<= 30m)."""
        day_name = day_of_week.lower()
        day_schedule = profile.weekly_schedule.days.get(day_name)

        if not day_schedule or not day_schedule.enabled:
            if proposed_tasks:
                total_duration = sum(t.duration_minutes for t in proposed_tasks)
                return AvailabilityValidationResult(
                    is_valid=False,
                    overflow_minutes=total_duration,
                    violation_reasons=(
                        f"Ngày {day_name} đã tắt nhưng có {len(proposed_tasks)} đề xuất nhiệm vụ.",
                    ),
                )
            return AvailabilityValidationResult(is_valid=True)

        # 1. Check if proposed tasks self-overlap
        sorted_tasks = sorted(proposed_tasks, key=lambda t: t.minute_range()[0])
        for i in range(len(sorted_tasks) - 1):
            s1, e1 = sorted_tasks[i].minute_range()
            s2, e2 = sorted_tasks[i + 1].minute_range()
            if s1 < e2 and s2 < e1:
                return AvailabilityValidationResult(
                    is_valid=False,
                    violation_reasons=(
                        f"Các nhiệm vụ đề xuất tự chồng lấn nhau: '{sorted_tasks[i].title}' và '{sorted_tasks[i + 1].title}'.",
                    ),
                )

        # 2. Check collision with occupied intervals
        normalized_occupied: list[tuple[int, int]] = []
        for occ in occupied_intervals:
            if len(occ) == 3:
                s_t, e_t, offset = occ
            else:
                s_t, e_t = occ
                offset = 0
            normalized_occupied.append(_to_minute_range(s_t, e_t, offset))

        for task in proposed_tasks:
            t_s, t_e = task.minute_range()
            for occ_s, occ_e in normalized_occupied:
                if t_s < occ_e and occ_s < t_e:
                    return AvailabilityValidationResult(
                        is_valid=False,
                        violation_reasons=(
                            f"Nhiệm vụ '{task.title}' [{task.start_time.strftime('%H:%M')}-{task.end_time.strftime('%H:%M')}] va chạm với khoảng bận.",
                        ),
                    )

        # 3. Check each task against merged contiguous day.time_slots
        total_overflow_minutes = 0
        merged_ranges = _merge_contiguous_slot_ranges(day_schedule.time_slots)

        for task in proposed_tasks:
            t_s, t_e = task.minute_range()
            matched = False
            task_overflow = 0

            for s_s, s_e in merged_ranges:
                # Exact fit: task lies fully within merged slot
                if s_s <= t_s and t_e <= s_e:
                    matched = True
                    break
                # Soft Overflow: starts within slot, overflows end by <= 30m
                if s_s <= t_s < s_e and t_e > s_e:
                    overflow = t_e - s_e
                    if 0 < overflow <= 30:
                        # Ensure no collision with another slot
                        has_other_slot_collision = any(
                            other_s < t_e for other_s, _ in merged_ranges if other_s >= s_e
                        )
                        if not has_other_slot_collision:
                            matched = True
                            task_overflow = overflow
                            break

            if not matched:
                # Check if it was hard block (> 30m overflow)
                for s_s, s_e in merged_ranges:
                    if s_s <= t_s < s_e and t_e > s_e:
                        overflow = t_e - s_e
                        if overflow > 30:
                            return AvailabilityValidationResult(
                                is_valid=False,
                                overflow_minutes=overflow,
                                violation_reasons=(
                                    f"Nhiệm vụ '{task.title}' tràn {overflow} phút ngoài khung rảnh (vượt quá dung sai 30 phút).",
                                ),
                            )
                return AvailabilityValidationResult(
                    is_valid=False,
                    violation_reasons=(
                        f"Nhiệm vụ '{task.title}' [{task.start_time.strftime('%H:%M')}-{task.end_time.strftime('%H:%M')}] nằm ngoài khung giờ rảnh.",
                    ),
                )

            total_overflow_minutes += task_overflow
            if total_overflow_minutes > 30:
                return AvailabilityValidationResult(
                    is_valid=False,
                    overflow_minutes=total_overflow_minutes,
                    violation_reasons=(
                        f"Tổng thời gian tràn trong ngày {day_name} ({total_overflow_minutes} phút) vượt quá giới hạn tối đa 30 phút.",
                    ),
                )

        return AvailabilityValidationResult(
            is_valid=True,
            has_soft_overflow=(total_overflow_minutes > 0),
            overflow_minutes=total_overflow_minutes,
        )
