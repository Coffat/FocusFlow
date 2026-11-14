import asyncio
import inspect
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar
from uuid import UUID

from src.shared_kernel.application.llm_port import (
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from src.shared_kernel.domain.base import generate_uuid7

from .models import (
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from .output_engine import OutputEngine
from .workflow_port import WorkflowRepositoryPort

T = TypeVar("T")


class AIQuotaPort(Protocol):
    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GENERATION",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID: ...

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "",
    ) -> None: ...

    async def release_reservation(
        self,
        reservation_id: UUID,
        reason: str = "RELEASED",
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class AIExecutionResult:
    value: Any
    prompt_tokens: int
    completion_tokens: int
    attempts: int
    reservation_id: UUID


RetryPredicate = Callable[[Exception], bool]
SleepFn = Callable[[float], Awaitable[None]]


class AIExecutionManager:
    """Single quota-safe execution path for structured FocusFlow AI calls."""

    def __init__(
        self,
        *,
        provider: LLMProviderPort,
        quota: AIQuotaPort,
        timeout_seconds: float = 55.0,
        max_retries: int = 2,
        sleep: SleepFn = asyncio.sleep,
        retry_predicate: RetryPredicate | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
    ) -> None:
        self._provider = provider
        self._quota = quota
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._sleep = sleep
        self._retry_predicate = retry_predicate or (lambda _exc: True)
        self._workflow_repo = workflow_repo

    async def execute(
        self,
        *,
        user_id: UUID,
        operation_type: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T] | dict[str, Any] | None,
        model_name: str,
        tools: list[LLMToolDeclarationDTO] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 4,
        thinking_level: str | None = None,
        existing_reservation_id: UUID | None = None,
        commit_on_success: bool = True,
        release_on_failure: bool = True,
        workflow_type: WorkflowType | None = None,
        step_name: str | None = None,
        step_order: int = 1,
        goal_id: UUID | None = None,
        roadmap_id: UUID | None = None,
        context_snapshot: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> AIExecutionResult:
        if existing_reservation_id is not None:
            reservation_id = existing_reservation_id
        else:
            reservation_id = await self._quota.reserve_quota(
                user_id,
                operation_type=operation_type,
                ttl_seconds=max(120, int(self._timeout_seconds) + 30),
            )

        started_at = datetime.now(UTC)
        run: WorkflowRun | None = None
        if self._workflow_repo is not None and workflow_type is not None:
            run = WorkflowRun(
                id=generate_uuid7(),
                user_id=user_id,
                goal_id=goal_id,
                roadmap_id=roadmap_id,
                workflow_type=workflow_type,
                current_step=step_name or operation_type,
                status=WorkflowStatus.RUNNING,
                context_snapshot=dict(context_snapshot or {}),
                started_at=started_at,
            )

        sig_params = inspect.signature(self._provider.generate_structured).parameters
        supports_prompt = "prompt" in sig_params or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_params.values()
        )
        supports_tools = "tools" in sig_params or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_params.values()
        )
        supports_temperature = "temperature" in sig_params or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_params.values()
        )

        last_error: Exception | None = None
        attempts_done = 0
        try:
            for attempt in range(1, self._max_retries + 2):
                attempts_done = attempt
                try:
                    call_kwargs: dict[str, Any] = {
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "response_schema": response_schema,
                    }
                    if supports_prompt:
                        call_kwargs["prompt"] = user_prompt
                    if supports_temperature:
                        call_kwargs["temperature"] = temperature
                    if supports_tools and tools is not None:
                        call_kwargs["tools"] = tools
                        call_kwargs["tool_executor"] = tool_executor
                        call_kwargs["max_tool_calls"] = max_tool_calls
                        call_kwargs["thinking_level"] = thinking_level

                    payload, prompt_tokens, completion_tokens = await asyncio.wait_for(
                        self._provider.generate_structured(**call_kwargs),
                        timeout=self._timeout_seconds,
                    )
                    value = OutputEngine.validate(payload, response_schema)
                    if commit_on_success:
                        await self._quota.commit_reservation(
                            reservation_id,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            model_name=model_name,
                        )
                    if run is not None and self._workflow_repo is not None:
                        finished_at = datetime.now(UTC)
                        await self._workflow_repo.add_run(run.complete(now=finished_at))
                        await self._workflow_repo.add_step(
                            WorkflowStepExecution(
                                id=generate_uuid7(),
                                workflow_run_id=run.id,
                                step_name=step_name or operation_type,
                                step_order=max(1, step_order),
                                status=WorkflowStepStatus.COMPLETED,
                                input_summary={
                                    "operation_type": operation_type,
                                    "model_name": model_name,
                                    "prompt_tokens": int(prompt_tokens or 0),
                                },
                                output_payload={
                                    "completion_tokens": int(completion_tokens or 0),
                                    "attempts": attempt,
                                },
                                retry_count=max(0, attempt - 1),
                                started_at=started_at,
                                completed_at=finished_at,
                            )
                        )
                    return AIExecutionResult(
                        value=value,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        attempts=attempt,
                        reservation_id=reservation_id,
                    )
                except Exception as exc:
                    last_error = exc
                    if attempt > self._max_retries or not self._retry_predicate(exc):
                        break
                    backoff_cap = min(10.0, float(2**attempt))
                    await self._sleep(random.uniform(0.0, backoff_cap))
        except asyncio.CancelledError:
            if release_on_failure:
                await self._quota.release_reservation(reservation_id, reason="CANCELLED")
            if run is not None and self._workflow_repo is not None:
                await self._workflow_repo.add_run(
                    run.fail(now=datetime.now(UTC), error_detail="CANCELLED")
                )
            raise
        if release_on_failure:
            await self._quota.release_reservation(
                reservation_id,
                reason=type(last_error).__name__ if last_error else "AI_EXECUTION_FAILED",
            )
        if run is not None and self._workflow_repo is not None:
            finished_at = datetime.now(UTC)
            err_name = type(last_error).__name__ if last_error else "AI_EXECUTION_FAILED"
            await self._workflow_repo.add_run(run.fail(now=finished_at, error_detail=err_name))
            await self._workflow_repo.add_step(
                WorkflowStepExecution(
                    id=generate_uuid7(),
                    workflow_run_id=run.id,
                    step_name=step_name or operation_type,
                    step_order=max(1, step_order),
                    status=WorkflowStepStatus.FAILED,
                    input_summary={"operation_type": operation_type, "model_name": model_name},
                    output_payload={"error": str(last_error) if last_error else err_name},
                    retry_count=max(0, attempts_done - 1),
                    started_at=started_at,
                    completed_at=finished_at,
                )
            )
        if last_error is None:
            raise RuntimeError("AI execution failed without an exception")
        raise last_error
