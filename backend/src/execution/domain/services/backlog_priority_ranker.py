from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from src.execution.domain.models.task import Task, TaskDependency, TaskStatus


@dataclass(frozen=True, slots=True)
class RankedBacklogTask:
    task: Task
    priority_rank: int
    out_degree: int
    milestone_sequence: int


class BacklogPriorityRanker:
    """Deterministic 4-tier Backlog Recovery Queue ranker (SRS FR-TASK-002).

    Sort key:
    1. `out_degree` DESC — tasks unblocking more downstream non-cancelled tasks come first.
    2. `milestone_sequence` ASC — earlier milestone tasks come first.
    3. `reschedule_count` DESC — repeatedly postponed tasks are rescued first.
    4. `estimated_minutes` ASC — shorter quick-win tasks break ties.
    """

    @classmethod
    def rank(
        cls,
        backlog_tasks: Sequence[Task],
        *,
        dependencies: Sequence[TaskDependency] = (),
        milestone_sequences: Mapping[UUID, int] | None = None,
        active_task_statuses: Mapping[UUID, TaskStatus] | None = None,
    ) -> list[RankedBacklogTask]:
        seq_map = milestone_sequences or {}
        status_map = active_task_statuses or {t.id: t.status for t in backlog_tasks}

        out_degree_map: dict[UUID, int] = {}
        seen_edges: set[tuple[UUID, UUID]] = set()
        for dep in dependencies:
            pair = (dep.predecessor_id, dep.successor_id)
            if pair in seen_edges:
                continue
            seen_edges.add(pair)
            succ_status = status_map.get(dep.successor_id)
            if succ_status == TaskStatus.CANCELLED:
                continue
            out_degree_map[dep.predecessor_id] = out_degree_map.get(dep.predecessor_id, 0) + 1

        def sort_key(task: Task) -> tuple[int, int, int, int, str]:
            out_deg = out_degree_map.get(task.id, 0)
            ms_seq = seq_map.get(task.milestone_id, 999_999)
            return (
                -out_deg,
                ms_seq,
                -int(task.reschedule_count),
                int(task.estimated_minutes),
                str(task.id),
            )

        ordered = sorted(backlog_tasks, key=sort_key)
        return [
            RankedBacklogTask(
                task=task,
                priority_rank=idx + 1,
                out_degree=out_degree_map.get(task.id, 0),
                milestone_sequence=seq_map.get(task.milestone_id, 999_999),
            )
            for idx, task in enumerate(ordered)
        ]
