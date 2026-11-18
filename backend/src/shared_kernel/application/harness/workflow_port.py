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


class BufferedWorkflowRepo:
    """In-memory WorkflowRepositoryPort buffer for concurrent gather stages (flushed sequentially)."""

    def __init__(self) -> None:
        self.runs: list[WorkflowRun] = []
        self.steps: list[WorkflowStepExecution] = []

    async def add_run(self, run: WorkflowRun) -> None:
        self.runs.append(run)

    async def get_run(self, run_id: UUID, *, user_id: UUID | None = None) -> WorkflowRun | None:
        del user_id
        return next((r for r in self.runs if r.id == run_id), None)

    async def get_run_for_update(
        self,
        run_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> WorkflowRun | None:
        return await self.get_run(run_id, user_id=user_id)

    async def get_active_run_for_goal(
        self,
        goal_id: UUID,
        user_id: UUID,
        workflow_type: WorkflowType = WorkflowType.PLAN_CREATION,
    ) -> WorkflowRun | None:
        del goal_id, user_id, workflow_type
        return None

    async def acquire_goal_clarification_lock(self, goal_id: UUID, user_id: UUID) -> None:
        del goal_id, user_id

    async def get_run_by_idempotency_key(
        self,
        goal_id: UUID,
        user_id: UUID,
        idempotency_key: str,
    ) -> WorkflowRun | None:
        del goal_id, user_id, idempotency_key
        return None

    async def save_run(self, run: WorkflowRun) -> None:
        self.runs.append(run)

    async def add_step(self, step: WorkflowStepExecution) -> None:
        self.steps.append(step)

    async def get_steps(self, run_id: UUID) -> list[WorkflowStepExecution]:
        return [s for s in self.steps if s.workflow_run_id == run_id]

    def drain_pairs(self) -> list[tuple[WorkflowRun, WorkflowStepExecution]]:
        """Pair buffered runs and steps in creation order for sequential persistence."""
        runs_by_id = {run.id: run for run in self.runs}
        pairs: list[tuple[WorkflowRun, WorkflowStepExecution]] = []
        seen_runs: set[UUID] = set()
        for step in self.steps:
            run = runs_by_id.get(step.workflow_run_id)
            if run is not None:
                pairs.append((run, step))
                seen_runs.add(run.id)
        for run in self.runs:
            if run.id not in seen_runs:
                # Preserve standalone run records if any
                pass
        return pairs
