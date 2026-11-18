from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.execution.application.ports.task_repository_port import TaskRepositoryPort
from src.execution.domain.models.task import Task, TaskDependency, TaskStatus
from src.execution.infrastructure.orm.task_orm import TaskDependencyORM, TaskORM


def _ensure_utc(dt: datetime) -> datetime:
    if dt == datetime.min:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class SqlAlchemyTaskRepository(TaskRepositoryPort):
    """SQLAlchemy repository for Execution Task & TaskDependency (add/flush only, never commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: TaskORM) -> Task:
        return Task(
            id=row.id,
            roadmap_id=row.roadmap_id,
            milestone_id=row.milestone_id,
            official_schedule_id=row.official_schedule_id,
            parent_task_id=row.parent_task_id,
            concept_id=row.concept_id,
            title=row.title,
            description=row.description,
            estimated_minutes=int(row.estimated_minutes),
            learning_resources=[
                dict(r) for r in (row.learning_resources_json or []) if isinstance(r, dict)
            ],
            scheduled_date=row.scheduled_date,
            scheduled_start=row.scheduled_start,
            scheduled_end=row.scheduled_end,
            status=TaskStatus(row.status),
            completed_at=row.completed_at,
            reschedule_count=int(row.reschedule_count),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _dep_to_domain(row: TaskDependencyORM) -> TaskDependency:
        return TaskDependency(
            id=row.id,
            predecessor_id=row.predecessor_id,
            successor_id=row.successor_id,
            roadmap_id=row.roadmap_id,
            is_mandatory=bool(row.is_mandatory),
            created_at=row.created_at,
        )

    async def get_by_id(self, task_id: UUID) -> Task | None:
        stmt = select(TaskORM).where(TaskORM.id == task_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def get_by_id_for_update(self, task_id: UUID) -> Task | None:
        stmt = (
            select(TaskORM)
            .where(TaskORM.id == task_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def list_by_ids(self, task_ids: Sequence[UUID]) -> list[Task]:
        if not task_ids:
            return []
        stmt = select(TaskORM).where(TaskORM.id.in_(list(task_ids)))
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [self._to_domain(r) for r in rows]

    async def list_by_roadmap_ids(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        status: str | None = None,
    ) -> list[Task]:
        if not roadmap_ids:
            return []
        stmt = select(TaskORM).where(TaskORM.roadmap_id.in_(list(roadmap_ids)))
        if status is not None:
            stmt = stmt.where(TaskORM.status == status.strip().upper())
        stmt = stmt.order_by(
            TaskORM.scheduled_date.asc().nulls_last(),
            TaskORM.scheduled_start.asc().nulls_last(),
            TaskORM.created_at.asc(),
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [self._to_domain(r) for r in rows]

    async def list_backlog_by_roadmap_ids(
        self,
        roadmap_ids: Sequence[UUID],
    ) -> list[Task]:
        if not roadmap_ids:
            return []
        stmt = (
            select(TaskORM)
            .where(
                TaskORM.roadmap_id.in_(list(roadmap_ids)),
                TaskORM.status == "TODO",
                TaskORM.scheduled_date.is_(None),
            )
            .order_by(TaskORM.created_at.asc())
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [self._to_domain(r) for r in rows]

    async def list_dependencies_by_roadmap_ids(
        self,
        roadmap_ids: Sequence[UUID],
    ) -> list[TaskDependency]:
        if not roadmap_ids:
            return []
        stmt = (
            select(TaskDependencyORM)
            .where(TaskDependencyORM.roadmap_id.in_(list(roadmap_ids)))
            .order_by(TaskDependencyORM.created_at.asc(), TaskDependencyORM.id.asc())
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [self._dep_to_domain(r) for r in rows]

    async def get_dependency(
        self,
        predecessor_id: UUID,
        successor_id: UUID,
    ) -> TaskDependency | None:
        stmt = select(TaskDependencyORM).where(
            TaskDependencyORM.predecessor_id == predecessor_id,
            TaskDependencyORM.successor_id == successor_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._dep_to_domain(row) if row is not None else None

    async def save(self, task: Task) -> Task:
        row = await self._session.get(TaskORM, task.id)
        now = _ensure_utc(task.updated_at)
        created = _ensure_utc(task.created_at)
        if row is None:
            row = TaskORM(
                id=task.id,
                roadmap_id=task.roadmap_id,
                milestone_id=task.milestone_id,
                official_schedule_id=task.official_schedule_id,
                parent_task_id=task.parent_task_id,
                concept_id=task.concept_id,
                title=task.title,
                description=task.description,
                estimated_minutes=task.estimated_minutes,
                learning_resources_json=list(task.learning_resources),
                scheduled_date=task.scheduled_date,
                scheduled_start=task.scheduled_start,
                scheduled_end=task.scheduled_end,
                status=task.status.value,
                completed_at=task.completed_at,
                reschedule_count=task.reschedule_count,
                created_at=created,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.official_schedule_id = task.official_schedule_id
            row.parent_task_id = task.parent_task_id
            row.concept_id = task.concept_id
            row.title = task.title
            row.description = task.description
            row.estimated_minutes = task.estimated_minutes
            row.learning_resources_json = list(task.learning_resources)
            row.scheduled_date = task.scheduled_date
            row.scheduled_start = task.scheduled_start
            row.scheduled_end = task.scheduled_end
            row.status = task.status.value
            row.completed_at = task.completed_at
            row.reschedule_count = task.reschedule_count
            row.updated_at = now
        await self._session.flush()
        return self._to_domain(row)

    async def add_dependency(self, dependency: TaskDependency) -> TaskDependency:
        row = TaskDependencyORM(
            id=dependency.id,
            predecessor_id=dependency.predecessor_id,
            successor_id=dependency.successor_id,
            roadmap_id=dependency.roadmap_id,
            is_mandatory=dependency.is_mandatory,
            created_at=_ensure_utc(dependency.created_at),
        )
        self._session.add(row)
        await self._session.flush()
        return self._dep_to_domain(row)

    async def delete_dependency(
        self,
        predecessor_id: UUID,
        successor_id: UUID,
    ) -> bool:
        stmt = delete(TaskDependencyORM).where(
            TaskDependencyORM.predecessor_id == predecessor_id,
            TaskDependencyORM.successor_id == successor_id,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        rowcount = int(getattr(result, "rowcount", 0) or 0)
        return rowcount > 0

    async def count_incomplete_non_cancelled_in_roadmap(
        self,
        roadmap_id: UUID,
    ) -> int:
        stmt = select(func.count(TaskORM.id)).where(
            TaskORM.roadmap_id == roadmap_id,
            TaskORM.status.in_(("TODO", "IN_PROGRESS")),
        )
        return int((await self._session.execute(stmt)).scalar() or 0)

    async def count_completed_in_roadmap(
        self,
        roadmap_id: UUID,
    ) -> int:
        stmt = select(func.count(TaskORM.id)).where(
            TaskORM.roadmap_id == roadmap_id,
            TaskORM.status == "COMPLETED",
        )
        return int((await self._session.execute(stmt)).scalar() or 0)
