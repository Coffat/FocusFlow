from typing import Protocol
from uuid import UUID

from .models import WorkflowRun, WorkflowStepExecution, WorkflowType


class WorkflowRepositoryPort(Protocol):
    async def add_run(self, run: WorkflowRun) -> None: ...

    async def get_run(self, run_id: UUID, *, user_id: UUID | None = None) -> WorkflowRun | None: ...

    async def get_run_for_update(
        self,
        run_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> WorkflowRun | None: ...

    async def get_active_run_for_goal(
        self,
        goal_id: UUID,
        user_id: UUID,
        workflow_type: WorkflowType = WorkflowType.PLAN_CREATION,
    ) -> WorkflowRun | None: ...

    async def acquire_goal_clarification_lock(self, goal_id: UUID, user_id: UUID) -> None: ...

    async def get_run_by_idempotency_key(
        self,
        goal_id: UUID,
        user_id: UUID,
        idempotency_key: str,
    ) -> WorkflowRun | None: ...

    async def save_run(self, run: WorkflowRun) -> None: ...

    async def add_step(self, step: WorkflowStepExecution) -> None: ...

    async def get_steps(self, run_id: UUID) -> list[WorkflowStepExecution]: ...
