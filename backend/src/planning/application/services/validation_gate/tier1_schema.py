"""Tier 1 Syntactic, Schema & Bound Validation Gate (ADR-009 / T7.3)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any
from uuid import UUID

from src.planning.application.services.learning_quality import validate_adaptive_milestones
from src.planning.domain.services.spatio_temporal_engine import NonSplittableTaskClassifier
from src.planning.domain.services.validation_types import (
    AI_BLOCK_MAX_MINUTES,
    AI_BLOCK_MIN_MINUTES,
    MANUAL_BLOCK_MAX_MINUTES,
    MANUAL_BLOCK_MIN_MINUTES,
    MAX_DAILY_PLANNED_MINUTES,
    ConstraintViolationDTO,
    parse_iso_date,
    parse_iso_datetime,
)


def _safe_minutes(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def validate_ai_milestones_tier1(
    milestones_data: Sequence[dict[str, Any]],
) -> list[ConstraintViolationDTO]:
    """Validate adaptive Milestone structure and pedagogical minimum fields."""
    return validate_adaptive_milestones(milestones_data)


def run_tier1_gate(
    proposal_data: dict[str, Any],
    *,
    valid_milestone_ids: set[UUID | str] | None = None,
    is_ai_generated: bool = True,
    allow_unscheduled_tasks: bool = False,
) -> list[ConstraintViolationDTO]:
    """Execute Tier 1 Syntactic & Bound checks on a ScheduleProposal payload."""
    violations: list[ConstraintViolationDTO] = []

    if "milestones" in proposal_data and isinstance(proposal_data["milestones"], list):
        if is_ai_generated and len(proposal_data["milestones"]) > 0:
            violations.extend(validate_ai_milestones_tier1(proposal_data["milestones"]))

    raw_tasks = proposal_data.get("tasks")
    if not isinstance(raw_tasks, list) or len(raw_tasks) == 0:
        violations.append(
            ConstraintViolationDTO(
                task_index=None,
                field="tasks",
                rule_code="EMPTY_PROPOSAL_TASKS",
                expected_bound="At least 1 study task",
                actual_value="0 tasks",
                suggested_fix="Cung cấp danh sách ít nhất 1 nhiệm vụ học tập trong trường 'tasks'.",
            )
        )
        return violations

    min_bound = AI_BLOCK_MIN_MINUTES if is_ai_generated else MANUAL_BLOCK_MIN_MINUTES
    max_bound = AI_BLOCK_MAX_MINUTES if is_ai_generated else MANUAL_BLOCK_MAX_MINUTES
    duration_rule_code = (
        "AI_TASK_DURATION_OUT_OF_BOUNDS"
        if is_ai_generated
        else "MANUAL_TASK_DURATION_OUT_OF_BOUNDS"
    )

    normalized_valid_mids: set[str] | None = (
        {str(mid) for mid in valid_milestone_ids} if valid_milestone_ids is not None else None
    )

    minutes_by_date: dict[date, list[tuple[int, int]]] = {}
    raw_blocks = proposal_data.get("schedule_blocks")
    has_blocks = isinstance(raw_blocks, list)

    capacity_overflow = proposal_data.get("_capacity_overflow")
    emitted_capacity_violation = False

    for idx, task in enumerate(raw_tasks):
        if not isinstance(task, dict):
            violations.append(
                ConstraintViolationDTO(
                    task_index=idx,
                    field="tasks",
                    rule_code="INVALID_TASK_OBJECT",
                    expected_bound="JSON object",
                    actual_value=type(task).__name__,
                    suggested_fix="Mỗi phần tử trong 'tasks' phải là một đối tượng JSON.",
                )
            )
            continue

        title = str(task.get("title", "")).strip()
        if not title:
            violations.append(
                ConstraintViolationDTO(
                    task_index=idx,
                    field="title",
                    rule_code="EMPTY_TASK_TITLE",
                    expected_bound="Non-empty title",
                    actual_value="''",
                    suggested_fix=f"Đặt tiêu đề rõ ràng cho nhiệm vụ #{idx}.",
                )
            )

        est_raw = task.get("estimated_minutes")
        try:
            est_mins = int(est_raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            est_mins = -1

        if not (min_bound <= est_mins <= max_bound):
            violations.append(
                ConstraintViolationDTO(
                    task_index=idx,
                    field="estimated_minutes",
                    rule_code=duration_rule_code,
                    expected_bound=f"[{min_bound}, {max_bound}] phút",
                    actual_value=f"{est_mins} phút",
                    suggested_fix=(
                        f"Điều chỉnh thời lượng nhiệm vụ #{idx} ('{title}') nằm trong khoảng "
                        f"[{min_bound}, {max_bound}] phút."
                    ),
                )
            )

        milestone_id = task.get("milestone_id")
        if normalized_valid_mids is not None:
            if milestone_id is None or str(milestone_id) not in normalized_valid_mids:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="milestone_id",
                        rule_code="INVALID_MILESTONE_REFERENCE",
                        expected_bound=(
                            "Một trong các milestone_id hợp lệ của lộ trình: "
                            f"{sorted(normalized_valid_mids)}"
                        ),
                        actual_value=str(milestone_id),
                        suggested_fix="Gán đúng milestone_id thuộc danh sách cột mốc đã phê duyệt của lộ trình.",
                    )
                )

        resources = task.get("learning_resources")
        if resources is not None:
            if not isinstance(resources, list):
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="learning_resources",
                        rule_code="INVALID_TASK_RESOURCE",
                        expected_bound="List of resource objects",
                        actual_value=type(resources).__name__,
                        suggested_fix="Trường 'learning_resources' phải là một danh sách các đối tượng tài nguyên học tập.",
                    )
                )
            else:
                for r_idx, res in enumerate(resources):
                    if not isinstance(res, dict) or not str(res.get("title", "")).strip():
                        violations.append(
                            ConstraintViolationDTO(
                                task_index=idx,
                                field=f"learning_resources[{r_idx}]",
                                rule_code="INVALID_TASK_RESOURCE",
                                expected_bound="Resource object with non-empty 'title'",
                                actual_value=str(res),
                                suggested_fix=f"Cung cấp đầy đủ 'title' cho tài nguyên #{r_idx} của nhiệm vụ #{idx}.",
                            )
                        )

        sched_date = parse_iso_date(task.get("scheduled_date"))
        if sched_date is None:
            if allow_unscheduled_tasks:
                continue
            task_diag = task.get("unscheduled_diagnostic")
            if (
                isinstance(task_diag, dict)
                and task_diag.get("reason_code") == "TASK_EXCEEDS_CONTINUOUS_SLOT"
            ):
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="estimated_minutes",
                        rule_code="TASK_EXCEEDS_CONTINUOUS_SLOT",
                        expected_bound=f"<= {task_diag.get('max_contiguous_window_minutes', 0)} phút liên tục",
                        actual_value=f"{est_mins} phút (nhiệm vụ không thể tách)",
                        suggested_fix=(
                            f"Mở rộng khung giờ rảnh liên tục lên >= {est_mins} phút hoặc "
                            "chuyển sang ngày có khung giờ dài hơn."
                        ),
                    )
                )
                emitted_capacity_violation = True
            elif isinstance(capacity_overflow, dict) and not emitted_capacity_violation:
                avail_m = int(capacity_overflow.get("available_minutes", 0) or 0)
                req_m = int(capacity_overflow.get("required_minutes", 0) or 0)
                t_date = str(capacity_overflow.get("target_date", "N/A"))
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="estimated_minutes",
                        rule_code="CAPACITY_EXCEEDED_BEFORE_TARGET_DATE",
                        expected_bound=f"Tổng thời lượng <= {avail_m} phút rảnh trước {t_date}",
                        actual_value=f"Yêu cầu {req_m} phút (dư {max(0, req_m - avail_m)} phút)",
                        suggested_fix=(
                            f"Gộp hoặc rút gọn các nhiệm vụ trong biên [{min_bound}, {max_bound}] phút "
                            f"để tổng nỗ lực không vượt quá {avail_m} phút khả dụng trước {t_date}."
                        ),
                    )
                )
                emitted_capacity_violation = True
            elif not isinstance(capacity_overflow, dict):
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="scheduled_date",
                        rule_code="INVALID_SCHEDULED_DATE",
                        expected_bound="YYYY-MM-DD",
                        actual_value=str(task.get("scheduled_date")),
                        suggested_fix="Cung cấp ngày học hợp lệ theo định dạng YYYY-MM-DD.",
                    )
                )
        elif est_mins > 0 and not has_blocks:
            minutes_by_date.setdefault(sched_date, []).append((idx, est_mins))

    if isinstance(raw_blocks, list):
        _validate_schedule_blocks(
            raw_blocks=raw_blocks,
            raw_tasks=raw_tasks,
            allow_unscheduled_tasks=allow_unscheduled_tasks,
            minutes_by_date=minutes_by_date,
            violations=violations,
        )

    for sched_date, day_entries in minutes_by_date.items():
        daily_total = sum(m for _, m in day_entries)
        if daily_total > MAX_DAILY_PLANNED_MINUTES:
            last_idx = day_entries[-1][0]
            violations.append(
                ConstraintViolationDTO(
                    task_index=last_idx,
                    field="estimated_minutes",
                    rule_code="DAILY_MAX_720M_EXCEEDED",
                    expected_bound=f"<= {MAX_DAILY_PLANNED_MINUTES} phút/ngày",
                    actual_value=f"{daily_total} phút vào ngày {sched_date.isoformat()}",
                    suggested_fix=(
                        f"Tổng thời lượng trong ngày {sched_date.isoformat()} vượt trần tuyệt đối "
                        f"{MAX_DAILY_PLANNED_MINUTES} phút. Hãy phân bổ bớt sang các ngày khác."
                    ),
                )
            )

    return violations


def _validate_schedule_blocks(
    *,
    raw_blocks: list[Any],
    raw_tasks: list[Any],
    allow_unscheduled_tasks: bool,
    minutes_by_date: dict[date, list[tuple[int, int]]],
    violations: list[ConstraintViolationDTO],
) -> None:
    task_efforts = {
        str(task.get("task_id") or task.get("id")): _safe_minutes(task.get("estimated_minutes"))
        for task in raw_tasks
        if isinstance(task, dict)
    }
    scheduled_task_ids = {
        str(task.get("task_id") or task.get("id"))
        for task in raw_tasks
        if isinstance(task, dict) and parse_iso_date(task.get("scheduled_date")) is not None
    }
    allocated_efforts: dict[str, int] = {}
    block_intervals: list[tuple[int, datetime, datetime]] = []
    block_bounds: dict[str, tuple[datetime, datetime]] = {}
    block_sequences: set[tuple[str, int]] = set()
    block_dates_by_task: dict[str, set[date]] = {}
    block_count_by_task: dict[str, int] = {}

    for idx, block in enumerate(raw_blocks):
        if not isinstance(block, dict):
            violations.append(
                ConstraintViolationDTO(
                    task_index=idx,
                    field="schedule_blocks",
                    rule_code="INVALID_SCHEDULE_BLOCK",
                    expected_bound="Schedule block object",
                    actual_value=type(block).__name__,
                    suggested_fix="Mỗi phần tử trong 'schedule_blocks' phải là một đối tượng JSON.",
                )
            )
            continue
        task_id = str(block.get("task_id"))
        block_date = parse_iso_date(block.get("block_date"))
        start = parse_iso_datetime(block.get("scheduled_start"))
        end = parse_iso_datetime(block.get("scheduled_end"))
        duration = _safe_minutes(block.get("scheduled_duration_minutes"))
        sequence = _safe_minutes(block.get("sequence_in_task"))
        if (
            task_id not in task_efforts
            or block_date is None
            or start is None
            or end is None
            or block_date != start.date()
            or duration < 10
            or duration > 240
            or int((end - start).total_seconds() // 60) != duration
            or sequence < 1
            or (task_id, sequence) in block_sequences
        ):
            violations.append(
                ConstraintViolationDTO(
                    task_index=idx,
                    field="schedule_blocks",
                    rule_code="INVALID_SCHEDULE_BLOCK",
                    expected_bound="Task hợp lệ, thời gian tăng và phiên 10..240 phút",
                    actual_value=str(block),
                    suggested_fix="Xếp lại các phiên học theo thời gian rảnh.",
                )
            )
            continue
        block_sequences.add((task_id, sequence))
        block_intervals.append((idx, start, end))
        block_dates_by_task.setdefault(task_id, set()).add(block_date)
        block_count_by_task[task_id] = block_count_by_task.get(task_id, 0) + 1
        first, last = block_bounds.get(task_id, (start, end))
        block_bounds[task_id] = min(first, start), max(last, end)
        allocated_efforts[task_id] = allocated_efforts.get(task_id, 0) + duration
        minutes_by_date.setdefault(block_date, []).append((idx, duration))

    block_intervals.sort(key=lambda item: item[1])
    for previous, current in zip(block_intervals, block_intervals[1:], strict=False):
        if current[1] < previous[2]:
            violations.append(
                ConstraintViolationDTO(
                    task_index=current[0],
                    field="schedule_blocks",
                    rule_code="SCHEDULE_BLOCK_OVERLAP",
                    expected_bound="Các phiên học không trùng giờ",
                    actual_value=f"{current[1].isoformat()} < {previous[2].isoformat()}",
                    suggested_fix="Dời phiên học sang khung giờ còn trống.",
                )
            )

    for task_id, effort in task_efforts.items():
        if allow_unscheduled_tasks and task_id not in scheduled_task_ids:
            if allocated_efforts.get(task_id, 0) != 0:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=None,
                        field="schedule_blocks",
                        rule_code="SCHEDULE_BLOCK_EFFORT_MISMATCH",
                        expected_bound=f"0 phút cho task chưa xếp lịch {task_id}",
                        actual_value=f"{allocated_efforts.get(task_id, 0)} phút",
                        suggested_fix="Gỡ các phiên học chưa hoàn chỉnh của task chưa xếp được lịch.",
                    )
                )
            continue
        if allocated_efforts.get(task_id, 0) != effort:
            violations.append(
                ConstraintViolationDTO(
                    task_index=None,
                    field="schedule_blocks",
                    rule_code="SCHEDULE_BLOCK_EFFORT_MISMATCH",
                    expected_bound=f"{effort} phút cho task {task_id}",
                    actual_value=f"{allocated_efforts.get(task_id, 0)} phút",
                    suggested_fix="Phân bổ đủ nỗ lực ước tính của nhiệm vụ.",
                )
            )

    for idx, task in enumerate(raw_tasks):
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or task.get("id"))
        is_ns, _ = NonSplittableTaskClassifier.classify(task)
        if is_ns:
            distinct_dates = block_dates_by_task.get(task_id, set())
            if len(distinct_dates) > 1:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="schedule_blocks",
                        rule_code="NON_SPLITTABLE_TASK_SPLIT_ACROSS_DAYS",
                        expected_bound="1 phiên học liên tục trên 1 ngày cho nhiệm vụ không thể tách",
                        actual_value=f"Bị tách qua {len(distinct_dates)} ngày ({sorted(d.isoformat() for d in distinct_dates)})",
                        suggested_fix="Xếp toàn bộ nhiệm vụ thi thử / kiểm thử tải này vào 1 khung giờ liên tục duy nhất.",
                    )
                )
            elif block_count_by_task.get(task_id, 0) > 1:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="schedule_blocks",
                        rule_code="NON_SPLITTABLE_TASK_SPLIT",
                        expected_bound="1 phiên học liên tục duy nhất cho nhiệm vụ không thể tách",
                        actual_value=f"Bị tách thành {block_count_by_task.get(task_id, 0)} phiên",
                        suggested_fix="Gộp thành 1 khối liên tục duy nhất cho nhiệm vụ không thể tách.",
                    )
                )
        bounds = block_bounds.get(task_id)
        if bounds is None:
            continue
        if (
            parse_iso_datetime(task.get("scheduled_start")) != bounds[0]
            or parse_iso_datetime(task.get("scheduled_end")) != bounds[1]
        ):
            violations.append(
                ConstraintViolationDTO(
                    task_index=None,
                    field="schedule_blocks",
                    rule_code="SCHEDULE_BLOCK_TIME_MISMATCH",
                    expected_bound="Giờ bắt đầu/kết thúc nhiệm vụ khớp các phiên học",
                    actual_value=task_id,
                    suggested_fix="Cập nhật thời gian nhiệm vụ theo phiên đầu và phiên cuối.",
                )
            )
