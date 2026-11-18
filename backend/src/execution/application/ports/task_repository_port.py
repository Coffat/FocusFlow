from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.execution.domain.models.task import Task, TaskDependency


class TaskRepositoryPort(Protocol):
    """Repository port for Execution Task & TaskDependency persistence."""

    async def get_by_id(self, task_id: UUID) -> Task | None: ...

    async def get_by_id_for_update(self, task_id: UUID) -> Task | None: ...

    async def list_by_ids(self, task_ids: Sequence[UUID]) -> list[Task]: ...

    async def list_by_roadmap_ids(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        status: str | None = None,
    ) -> list[Task]: ...

    async def list_backlog_by_roadmap_ids(
        self,
        roadmap_ids: Sequence[UUID],
    ) -> list[Task]: ...

    async def list_dependencies_by_roadmap_ids(
        self,
        roadmap_ids: Sequence[UUID],
    ) -> list[TaskDependency]: ...

    async def get_dependency(
        self,
        predecessor_id: UUID,
        successor_id: UUID,
    ) -> TaskDependency | None: ...

    async def save(self, task: Task) -> Task: ...

    async def add_dependency(self, dependency: TaskDependency) -> TaskDependency: ...

    async def delete_dependency(
        self,
        predecessor_id: UUID,
        successor_id: UUID,
    ) -> bool: ...

    async def count_incomplete_non_cancelled_in_roadmap(
        self,
        roadmap_id: UUID,
    ) -> int: ...

    async def count_completed_in_roadmap(
        self,
        roadmap_id: UUID,
    ) -> int: ...
