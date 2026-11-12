from collections.abc import Mapping, Sequence
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.execution.infrastructure.orm.task_orm import TaskDependencyORM, TaskORM
from src.execution.public_api import (
    ExecutionScheduleSyncPort,
    ExistingScheduledTaskDTO,
    ProposedDependencySyncItemDTO,
    ProposedTaskSyncItemDTO,
    ScheduleSyncResultDTO,
)


class ExecutionScheduleSyncAdapter(ExecutionScheduleSyncPort):
    """SQLAlchemy adapter for ExecutionScheduleSyncPort (OS-03 Merge / Future Shift & OS-04 EDF).

    Strictly obeys hexagonal & modular monolith rules:
    - Never imports from `src.planning.*` (except `public_api` if needed).
    - Never performs SQL JOIN across bounded context tables.
    - Never calls `session.commit()` (only `add`, `delete`, `flush`).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        """Return non-cancelled scheduled tasks belonging to the given roadmap IDs."""
        if not roadmap_ids:
            return []

        stmt = (
            select(TaskORM)
            .where(
                TaskORM.roadmap_id.in_(list(roadmap_ids)),
                TaskORM.status.in_(("TODO", "IN_PROGRESS", "COMPLETED")),
            )
            .order_by(TaskORM.scheduled_date.asc().nulls_last(), TaskORM.created_at.asc())
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        target_map = roadmap_target_dates or {}
        return [
            ExistingScheduledTaskDTO(
                task_id=row.id,
                roadmap_id=row.roadmap_id,
                milestone_id=row.milestone_id,
                title=row.title,
                estimated_minutes=row.estimated_minutes,
                scheduled_date=row.scheduled_date,
                scheduled_start=row.scheduled_start,
                scheduled_end=row.scheduled_end,
                status=row.status,
                roadmap_target_date=target_map.get(row.roadmap_id),
            )
            for row in rows
        ]

    async def get_active_roadmaps_tasks(
        self,
        user_id: UUID,
        exclude_roadmap_id: UUID | None = None,
        *,
        active_roadmap_ids: Sequence[UUID] | None = None,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        """Return scheduled tasks for a user's active roadmaps without cross-context ORM JOINs."""
        _ = user_id
        if active_roadmap_ids is None:
            return []
        filtered_ids = [
            rid
            for rid in active_roadmap_ids
            if exclude_roadmap_id is None or rid != exclude_roadmap_id
        ]
        return await self.get_tasks_for_roadmaps(
            filtered_ids,
            roadmap_target_dates=roadmap_target_dates,
        )

    async def sync_official_schedule_tasks(
        self,
        *,
        roadmap_id: UUID,
        official_schedule_id: UUID,
        proposed_tasks: Sequence[ProposedTaskSyncItemDTO],
        proposed_dependencies: Sequence[ProposedDependencySyncItemDTO],
        now: datetime,
        protected_task_ids: Sequence[UUID] = (),
    ) -> ScheduleSyncResultDTO:
        """Apply OS-03 Merge / Future Shift:
        - Preserves any existing tasks for `roadmap_id` with `status == 'COMPLETED'`.
        - For non-completed tasks:
          * If referenced by `session_tasks` (`ON DELETE RESTRICT`), transitions them to `CANCELLED`
            with `scheduled_date=None`, `scheduled_start=None`, `scheduled_end=None`.
          * Otherwise deletes them and replaces with the newly applied tasks and dependencies.
        """
        existing_stmt = select(TaskORM).where(TaskORM.roadmap_id == roadmap_id)
        existing_tasks = list((await self._session.execute(existing_stmt)).scalars().all())

        completed_tasks: dict[UUID, TaskORM] = {}
        protected_tasks: dict[UUID, TaskORM] = {}
        non_completed_tasks: list[TaskORM] = []
        protected_ids = set(protected_task_ids)

        for task in existing_tasks:
            if task.status == "COMPLETED":
                completed_tasks[task.id] = task
            elif task.id in protected_ids:
                protected_tasks[task.id] = task
            else:
                non_completed_tasks.append(task)

        # Remove existing dependencies for this roadmap before rebuilding
        await self._session.execute(
            delete(TaskDependencyORM).where(TaskDependencyORM.roadmap_id == roadmap_id)
        )

        # Find which non-completed tasks have session history (`session_tasks.task_id` ON DELETE RESTRICT)
        non_completed_ids = [t.id for t in non_completed_tasks if t.status != "CANCELLED"]
        tasks_with_sessions: set[UUID] = set()
        if non_completed_ids:
            res = await self._session.execute(
                text("SELECT DISTINCT task_id FROM session_tasks WHERE task_id = ANY(:task_ids)"),
                {"task_ids": non_completed_ids},
            )
            tasks_with_sessions = {row[0] for row in res.fetchall()}

        replaced_count = 0
        shifted_minutes = 0
        deletable_ids: list[UUID] = []

        for old_task in non_completed_tasks:
            if old_task.status != "CANCELLED":
                replaced_count += 1
                shifted_minutes += int(old_task.estimated_minutes or 0)

            if old_task.id in tasks_with_sessions:
                old_task.status = "CANCELLED"
                old_task.scheduled_date = None
                old_task.scheduled_start = None
                old_task.scheduled_end = None
                old_task.official_schedule_id = None
                old_task.updated_at = now
            else:
                deletable_ids.append(old_task.id)

        if deletable_ids:
            await self._session.execute(delete(TaskORM).where(TaskORM.id.in_(deletable_ids)))
        await self._session.flush()

        # Keep completed tasks linked to the current official_schedule_id
        for comp_task in (*completed_tasks.values(), *protected_tasks.values()):
            comp_task.official_schedule_id = official_schedule_id
            comp_task.updated_at = now

        # Insert new tasks (skipping any task_id that is already COMPLETED)
        valid_task_ids: set[UUID] = set(completed_tasks) | set(protected_tasks)
        inserted_count = 0
        inserted_minutes = 0

        for item in proposed_tasks:
            if item.task_id in completed_tasks or item.task_id in protected_tasks:
                continue
            new_id = item.task_id
            if new_id in tasks_with_sessions:
                new_id = uuid7()

            new_task = TaskORM(
                id=new_id,
                roadmap_id=roadmap_id,
                milestone_id=item.milestone_id,
                official_schedule_id=official_schedule_id,
                title=item.title,
                description=item.description,
                estimated_minutes=item.estimated_minutes,
                scheduled_date=item.scheduled_date,
                scheduled_start=item.scheduled_start,
                scheduled_end=item.scheduled_end,
                status="TODO",
                completed_at=None,
                reschedule_count=0,
                created_at=now,
                updated_at=now,
            )
            self._session.add(new_task)
            valid_task_ids.add(new_id)
            inserted_count += 1
            inserted_minutes += int(item.estimated_minutes)

        await self._session.flush()

        # Insert dependencies between valid existing/new tasks
        seen_pairs: set[tuple[UUID, UUID]] = set()
        for dep in proposed_dependencies:
            if dep.predecessor_id == dep.successor_id:
                continue
            if dep.predecessor_id not in valid_task_ids or dep.successor_id not in valid_task_ids:
                continue
            pair = (dep.predecessor_id, dep.successor_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            dep_orm = TaskDependencyORM(
                id=uuid7(),
                predecessor_id=dep.predecessor_id,
                successor_id=dep.successor_id,
                roadmap_id=roadmap_id,
                is_mandatory=dep.is_mandatory,
                created_at=now,
            )
            self._session.add(dep_orm)

        await self._session.flush()

        preserved_minutes = sum(
            int(task.estimated_minutes or 0)
            for task in (*completed_tasks.values(), *protected_tasks.values())
        )
        total_active_sessions = len(completed_tasks) + len(protected_tasks) + inserted_count
        total_planned_minutes = preserved_minutes + inserted_minutes
        affected_tasks_count = replaced_count + inserted_count
        total_shifted_minutes = shifted_minutes if replaced_count > 0 else inserted_minutes

        return ScheduleSyncResultDTO(
            roadmap_id=roadmap_id,
            official_schedule_id=official_schedule_id,
            preserved_completed_tasks_count=len(completed_tasks),
            replaced_tasks_count=replaced_count,
            inserted_tasks_count=inserted_count,
            affected_tasks_count=affected_tasks_count,
            total_shifted_minutes=total_shifted_minutes,
            total_active_sessions=total_active_sessions,
            total_planned_minutes=total_planned_minutes,
        )


SqlAlchemyExecutionScheduleSyncAdapter = ExecutionScheduleSyncAdapter
