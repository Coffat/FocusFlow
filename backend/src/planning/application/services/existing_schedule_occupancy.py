from collections.abc import Sequence

from src.execution.public_api import ExistingScheduledTaskDTO
from src.planning.domain.models.schedule_block import ScheduleBlock


def expand_existing_schedule_occupancy(
    tasks: Sequence[ExistingScheduledTaskDTO],
    blocks: Sequence[ScheduleBlock],
) -> list[ExistingScheduledTaskDTO]:
    """Use actual study sessions for capacity instead of a task's first scheduled date."""
    active_blocks = [block for block in blocks if block.status == "PLANNED"]
    block_task_ids = {block.task_id for block in blocks if block.task_id is not None}
    task_by_id = {task.task_id: task for task in tasks}
    occupied = [task for task in tasks if task.task_id not in block_task_ids]
    for block in active_blocks:
        task = task_by_id.get(block.task_id) if block.task_id is not None else None
        occupied.append(
            ExistingScheduledTaskDTO(
                task_id=block.task_id or block.id,
                roadmap_id=block.roadmap_id,
                milestone_id=task.milestone_id if task is not None else block.id,
                title=task.title if task is not None else "Phiên học đã lên lịch",
                estimated_minutes=block.scheduled_duration_minutes,
                scheduled_date=block.block_date,
                scheduled_start=block.start_time,
                scheduled_end=block.end_time,
                status=task.status if task is not None else "TODO",
                roadmap_target_date=task.roadmap_target_date if task is not None else None,
            )
        )
    return occupied
