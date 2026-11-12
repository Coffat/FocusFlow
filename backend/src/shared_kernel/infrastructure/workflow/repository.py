from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared_kernel.application.harness.models import (
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from src.shared_kernel.application.harness.workflow_port import WorkflowRepositoryPort

from .models import WorkflowRunORM, WorkflowStepExecutionORM


class SqlAlchemyWorkflowRepository(WorkflowRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_run(self, run: WorkflowRun) -> None:
        self._session.add(self._run_to_orm(run))
        await self._session.flush()

    async def get_run(self, run_id: UUID, *, user_id: UUID | None = None) -> WorkflowRun | None:
        stmt = select(WorkflowRunORM).where(WorkflowRunORM.id == run_id)
        if user_id is not None:
            stmt = stmt.where(WorkflowRunORM.user_id == user_id)
        row = await self._session.scalar(stmt)
        return self._run_to_domain(row) if row else None

    async def save_run(self, run: WorkflowRun) -> None:
        row = await self._session.get(WorkflowRunORM, run.id)
        if row is None:
            raise LookupError(f"Workflow run not found: {run.id}")
        row.current_step = run.current_step
        row.status = run.status.value
        row.context_snapshot = dict(run.context_snapshot)
        row.error_detail = run.error_detail
        row.paused_at = run.paused_at
        row.completed_at = run.completed_at
        await self._session.flush()

    async def add_step(self, step: WorkflowStepExecution) -> None:
        self._session.add(
            WorkflowStepExecutionORM(
                id=step.id,
                workflow_run_id=step.workflow_run_id,
                step_name=step.step_name,
                step_order=step.step_order,
                status=step.status.value,
                input_summary=dict(step.input_summary),
                output_payload=dict(step.output_payload),
                ai_usage_log_id=step.ai_usage_log_id,
                retry_count=step.retry_count,
                started_at=step.started_at,
                completed_at=step.completed_at,
            )
        )
        await self._session.flush()

    async def get_steps(self, run_id: UUID) -> list[WorkflowStepExecution]:
        rows = (
            await self._session.scalars(
                select(WorkflowStepExecutionORM)
                .where(WorkflowStepExecutionORM.workflow_run_id == run_id)
                .order_by(WorkflowStepExecutionORM.step_order)
            )
        ).all()
        return [self._step_to_domain(row) for row in rows]

    @staticmethod
    def _run_to_orm(run: WorkflowRun) -> WorkflowRunORM:
        return WorkflowRunORM(
            id=run.id,
            user_id=run.user_id,
            goal_id=run.goal_id,
            roadmap_id=run.roadmap_id,
            workflow_type=run.workflow_type.value,
            current_step=run.current_step,
            status=run.status.value,
            context_snapshot=dict(run.context_snapshot),
            error_detail=run.error_detail,
            started_at=run.started_at,
            paused_at=run.paused_at,
            completed_at=run.completed_at,
        )

    @staticmethod
    def _run_to_domain(row: WorkflowRunORM) -> WorkflowRun:
        return WorkflowRun(
            id=row.id,
            user_id=row.user_id,
            goal_id=row.goal_id,
            roadmap_id=row.roadmap_id,
            workflow_type=WorkflowType(row.workflow_type),
            current_step=row.current_step,
            status=WorkflowStatus(row.status),
            context_snapshot=dict(row.context_snapshot),
            error_detail=row.error_detail,
            started_at=row.started_at,
            paused_at=row.paused_at,
            completed_at=row.completed_at,
        )

    @staticmethod
    def _step_to_domain(row: WorkflowStepExecutionORM) -> WorkflowStepExecution:
        return WorkflowStepExecution(
            id=row.id,
            workflow_run_id=row.workflow_run_id,
            step_name=row.step_name,
            step_order=row.step_order,
            status=WorkflowStepStatus(row.status),
            input_summary=dict(row.input_summary),
            output_payload=dict(row.output_payload),
            ai_usage_log_id=row.ai_usage_log_id,
            retry_count=row.retry_count,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
