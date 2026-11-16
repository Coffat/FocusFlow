import asyncio
import json
import logging
import random
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar
from uuid import UUID

from pydantic import ValidationError

from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from src.shared_kernel.domain.base import generate_uuid7

from .models import (
    PromptTemplate,
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from .output_engine import OutputEngine
from .prompt_registry import build_prompt_audit_metadata
from .workflow_port import WorkflowRepositoryPort

logger = logging.getLogger(__name__)

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


class _NoOpQuotaAdapter:
    """Internal no-op quota adapter when `manage_quota=False` for sub-steps."""

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "INTERNAL_STEP",
        cost: int = 0,
        ttl_seconds: int = 120,
    ) -> UUID:
        del user_id, operation_type, cost, ttl_seconds
        return generate_uuid7()

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "",
    ) -> None:
        del reservation_id, prompt_tokens, completion_tokens, model_name

    async def release_reservation(
        self,
        reservation_id: UUID,
        reason: str = "RELEASED",
    ) -> None:
        del reservation_id, reason


@dataclass(frozen=True, slots=True)
class AIExecutionResult:
    value: Any
    prompt_tokens: int
    completion_tokens: int
    attempts: int
    reservation_id: UUID
    thinking_tokens: int = 0
    model_id: str = ""

    @property
    def output_tokens(self) -> int:
        return self.completion_tokens


RetryPredicate = Callable[[Exception], bool]
SleepFn = Callable[[float], Awaitable[None]]

_NON_RETRYABLE_STATUS_CODES = frozenset({400, 401, 403, 404, 422})
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
_NON_RETRYABLE_MARKERS = (
    "400",
    "bad request",
    "401",
    "unauthorized",
    "invalid api key",
    "403",
    "forbidden",
    "permission_denied",
    "permission denied",
)
_RETRYABLE_MARKERS = (
    "429",
    "rate limit",
    "resource_exhausted",
    "500",
    "502",
    "503",
    "504",
    "unavailable",
    "overloaded",
    "high demand",
    "timeout",
    "timed out",
    "connection",
    "ai_schema_validation_error",
    "empty json response",
    "malformed_function_call",
)


def default_ai_retry_predicate(exc: Exception) -> bool:
    """Retry only transient provider/timeout errors and structured output/schema validation errors."""
    if isinstance(
        exc,
        (
            PermissionError,
            TypeError,
            KeyError,
            AttributeError,
            NotImplementedError,
        ),
    ):
        return False

    module_name = type(exc).__module__.lower()
    exc_type_name = type(exc).__name__.lower()
    if any(
        db_marker in module_name or db_marker in exc_type_name
        for db_marker in ("sqlalchemy", "asyncpg", "psycopg", "integrityerror", "operationalerror")
    ):
        return False

    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(status_code, int):
        if status_code in _NON_RETRYABLE_STATUS_CODES:
            return False
        if status_code in _RETRYABLE_STATUS_CODES:
            return True

    if isinstance(
        exc,
        (
            TimeoutError,
            asyncio.TimeoutError,
            ConnectionError,
            ValidationError,
            json.JSONDecodeError,
        ),
    ):
        return True

    text = str(exc).lower()
    if any(marker in text for marker in _NON_RETRYABLE_MARKERS):
        return False

    if isinstance(exc, ValueError):
        return any(
            marker in text
            for marker in (
                "json",
                "schema",
                "validation",
                "malformed_function_call",
                "empty response",
            )
        )

    return any(marker in text for marker in _RETRYABLE_MARKERS)


class AIExecutionManager:
    """Single quota-safe execution path for structured FocusFlow AI calls."""

    def __init__(
        self,
        *,
        provider: LLMProviderPort,
        quota: AIQuotaPort | None = None,
        timeout_seconds: float = 55.0,
        max_retries: int = 2,
        sleep: SleepFn = asyncio.sleep,
        retry_predicate: RetryPredicate | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
        manage_quota: bool = True,
    ) -> None:
        self._provider = provider
        self._quota: AIQuotaPort = quota if quota is not None else _NoOpQuotaAdapter()
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._sleep = sleep
        self._retry_predicate = retry_predicate or default_ai_retry_predicate
        self._workflow_repo = workflow_repo
        self._manage_quota = manage_quota and (quota is not None)

    async def execute(
        self,
        *,
        user_id: UUID,
        operation_type: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T] | dict[str, Any] | None,
        model_name: str = "gemini-3.8-flash",
        tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        existing_reservation_id: UUID | None = None,
        commit_on_success: bool = True,
        release_on_failure: bool = True,
        manage_quota: bool | None = None,
        workflow_type: WorkflowType | None = None,
        step_name: str | None = None,
        step_order: int = 1,
        goal_id: UUID | None = None,
        roadmap_id: UUID | None = None,
        context_snapshot: dict[str, Any] | None = None,
        prompt_template: PromptTemplate | None = None,
    ) -> AIExecutionResult:
        effective_manage_quota = self._manage_quota if manage_quota is None else manage_quota
        effective_commit = commit_on_success and effective_manage_quota
        effective_release = release_on_failure and effective_manage_quota

        if existing_reservation_id is not None:
            reservation_id = existing_reservation_id
        elif effective_manage_quota:
            reservation_id = await self._quota.reserve_quota(
                user_id,
                operation_type=operation_type,
                ttl_seconds=max(120, int(self._timeout_seconds) + 30),
            )
        else:
            reservation_id = generate_uuid7()

        prompt_audit = (
            build_prompt_audit_metadata(prompt_template) if prompt_template is not None else {}
        )
        merged_snapshot = {**dict(context_snapshot or {}), **prompt_audit}

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
                context_snapshot=merged_snapshot,
                started_at=started_at,
            )

        reservation_finalized = False

        async def _commit_once(
            *,
            p_tokens: int,
            c_tokens: int,
            actual_model: str,
        ) -> None:
            nonlocal reservation_finalized
            if reservation_finalized or not effective_commit:
                return
            reservation_finalized = True
            await self._quota.commit_reservation(
                reservation_id,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                model_name=actual_model,
            )

        async def _release_once(reason: str) -> None:
            nonlocal reservation_finalized
            if reservation_finalized or not effective_release:
                return
            reservation_finalized = True
            await self._quota.release_reservation(
                reservation_id,
                reason=reason,
            )

        async def _cleanup_on_cancel() -> None:
            await _release_once("CANCELLED")
            if run is not None and self._workflow_repo is not None:
                await self._workflow_repo.add_run(
                    run.fail(now=datetime.now(UTC), error_detail="CANCELLED")
                )

        async def _cleanup_on_failure(err: Exception | None, attempts_made: int) -> None:
            err_name = type(err).__name__ if err else "AI_EXECUTION_FAILED"
            await _release_once(err_name)
            if run is not None and self._workflow_repo is not None:
                finished_at = datetime.now(UTC)
                await self._workflow_repo.add_run(run.fail(now=finished_at, error_detail=err_name))
                await self._workflow_repo.add_step(
                    WorkflowStepExecution(
                        id=generate_uuid7(),
                        workflow_run_id=run.id,
                        step_name=step_name or operation_type,
                        step_order=max(1, step_order),
                        status=WorkflowStepStatus.FAILED,
                        input_summary={
                            "operation_type": operation_type,
                            "model_name": model_name,
                            **prompt_audit,
                        },
                        output_payload={"error": str(err) if err else err_name},
                        retry_count=max(0, attempts_made - 1),
                        started_at=started_at,
                        completed_at=finished_at,
                    )
                )

        last_error: Exception | None = None
        attempts_done = 0
        validated_value: Any = None
        prompt_tokens = 0
        completion_tokens = 0
        thinking_tokens = 0
        resolved_model_id = model_name
        succeeded = False

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout_seconds
        try:
            for attempt in range(1, self._max_retries + 2):
                attempts_done = attempt
                try:
                    remaining_seconds = deadline - loop.time()
                    if remaining_seconds <= 0:
                        raise TimeoutError("AI execution exceeded the total timeout budget")

                    call_kwargs: dict[str, Any] = {
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "response_schema": response_schema,
                    }
                    if tools is not None:
                        call_kwargs["tools"] = tools
                        call_kwargs["tool_executor"] = tool_executor
                        call_kwargs["max_tool_calls"] = max_tool_calls
                    if thinking_level is not None:
                        call_kwargs["thinking_level"] = thinking_level

                    raw_gen = await asyncio.wait_for(
                        self._provider.generate_structured(**call_kwargs),
                        timeout=remaining_seconds,
                    )
                    if isinstance(raw_gen, LLMGenerationResult):
                        payload = raw_gen.payload
                        prompt_tokens = int(raw_gen.prompt_tokens or 0)
                        completion_tokens = int(raw_gen.output_tokens or 0)
                        thinking_tokens = int(raw_gen.thinking_tokens or 0)
                        resolved_model_id = raw_gen.model_id or model_name
                    else:
                        payload, p_tok, c_tok = raw_gen
                        prompt_tokens = int(p_tok or 0)
                        completion_tokens = int(c_tok or 0)
                        thinking_tokens = int(getattr(raw_gen, "thinking_tokens", 0) or 0)
                        resolved_model_id = str(
                            getattr(self._provider, "last_model_used", None)
                            or getattr(self._provider, "model_used", None)
                            or model_name
                        )

                    validated_value = OutputEngine.validate(payload, response_schema)
                    succeeded = True
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt > self._max_retries or not self._retry_predicate(exc):
                        break
                    backoff_cap = min(10.0, float(2**attempt))
                    remaining_seconds = deadline - loop.time()
                    if remaining_seconds <= 0:
                        last_error = TimeoutError("AI execution exceeded the total timeout budget")
                        break
                    await self._sleep(min(random.uniform(0.0, backoff_cap), remaining_seconds))
        except asyncio.CancelledError:
            try:
                await asyncio.shield(_cleanup_on_cancel())
            except Exception as cleanup_exc:
                logger.warning(
                    "ai_execution_cancel_cleanup_failed for reservation %s: %s",
                    reservation_id,
                    cleanup_exc,
                )
            raise

        if not succeeded:
            try:
                await asyncio.shield(_cleanup_on_failure(last_error, attempts_done))
            except Exception as cleanup_exc:
                logger.warning(
                    "ai_execution_failure_cleanup_failed for reservation %s: %s",
                    reservation_id,
                    cleanup_exc,
                )
            if last_error is None:
                raise RuntimeError("AI execution failed without an exception")
            raise last_error

        # Post-LLM persistence effects run strictly outside the LLM retry loop (A1).
        await _commit_once(
            p_tokens=prompt_tokens,
            c_tokens=completion_tokens,
            actual_model=resolved_model_id,
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
                        "model_name": resolved_model_id,
                        "prompt_tokens": prompt_tokens,
                        **prompt_audit,
                    },
                    output_payload={
                        "completion_tokens": completion_tokens,
                        "thinking_tokens": thinking_tokens,
                        "attempts": attempts_done,
                    },
                    retry_count=max(0, attempts_done - 1),
                    started_at=started_at,
                    completed_at=finished_at,
                )
            )
        return AIExecutionResult(
            value=validated_value,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            attempts=attempts_done,
            reservation_id=reservation_id,
            thinking_tokens=thinking_tokens,
            model_id=resolved_model_id,
        )
