import asyncio
import logging
import random
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar
from uuid import UUID

from src.shared_kernel.application.llm_port import (
    AIErrorCategory,
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
    SchemaMismatchError,
    classify_ai_error,
    format_concise_schema_errors,
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
    repair_attempts: int = 0
    error_category: AIErrorCategory | None = None

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
    "404",
    "not_found",
    "422",
    "permission_denied",
    "permission denied",
)


def _is_http_500_stream_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code is None and isinstance(getattr(exc, "code", None), int):
        status_code = getattr(exc, "code", None)
    text = str(exc)
    text_lower = text.lower()
    return (
        status_code == 500
        or "500" in text
        or "stream interrupted" in text_lower
        or "INTERNAL" in text
    )


def default_ai_retry_predicate(exc: Exception) -> bool:
    """Retry only transient TIMEOUT and transient GATEWAY_ERROR (never SCHEMA_MISMATCH/QUOTA/VALIDATION_GATE/4xx)."""
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

    category = classify_ai_error(exc)
    if category not in (AIErrorCategory.TIMEOUT, AIErrorCategory.GATEWAY_ERROR):
        return False

    if category is AIErrorCategory.TIMEOUT:
        return True

    status_code = getattr(exc, "status_code", None)
    if status_code is None and isinstance(getattr(exc, "code", None), int):
        status_code = getattr(exc, "code", None)
    if isinstance(status_code, int):
        if status_code in _NON_RETRYABLE_STATUS_CODES:
            return False
        if status_code in _RETRYABLE_STATUS_CODES:
            return True

    text = str(exc).lower()
    if any(marker in text for marker in _NON_RETRYABLE_MARKERS):
        return False

    return True


def _extract_raw_gen(
    raw_gen: Any,
    default_model_name: str,
    provider: LLMProviderPort,
) -> tuple[Any, int, int, int, str, int]:
    if isinstance(raw_gen, LLMGenerationResult):
        p_tok = int(raw_gen.prompt_tokens or 0)
        t_tok = int(raw_gen.thinking_tokens or 0)
        c_tok = max(int(raw_gen.output_tokens or 0), t_tok)
        return (
            raw_gen.payload,
            p_tok,
            c_tok,
            t_tok,
            raw_gen.model_id or default_model_name,
            int(raw_gen.repair_attempts or 0),
        )
    payload, p_tok, c_tok = raw_gen
    t_tok = int(getattr(raw_gen, "thinking_tokens", 0) or 0)
    resolved_model = str(
        getattr(provider, "last_model_used", None)
        or getattr(provider, "model_used", None)
        or default_model_name
    )
    return (
        payload,
        int(p_tok or 0),
        max(int(c_tok or 0), t_tok),
        t_tok,
        resolved_model,
        0,
    )


class AIExecutionManager:
    """Single quota-safe execution path for structured FocusFlow AI calls."""

    def __init__(
        self,
        *,
        provider: LLMProviderPort,
        quota: AIQuotaPort | None = None,
        timeout_seconds: float = 55.0,
        tool_call_timeout_seconds: float | None = None,
        max_retries: int = 2,
        sleep: SleepFn = asyncio.sleep,
        retry_predicate: RetryPredicate | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
        manage_quota: bool = True,
    ) -> None:
        self._provider = provider
        self._quota: AIQuotaPort = quota if quota is not None else _NoOpQuotaAdapter()
        self._timeout_seconds = timeout_seconds
        self._tool_call_timeout_seconds = tool_call_timeout_seconds
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
        tool_call_timeout_seconds: float | None = None,
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
            t_tokens: int,
            actual_model: str,
        ) -> None:
            nonlocal reservation_finalized
            if reservation_finalized or not effective_commit:
                return
            reservation_finalized = True
            billable_completion_tokens = max(int(c_tokens or 0), int(t_tokens or 0))
            await self._quota.commit_reservation(
                reservation_id,
                prompt_tokens=p_tokens,
                completion_tokens=billable_completion_tokens,
                model_name=actual_model,
            )

        async def _release_once(reason: str) -> None:
            nonlocal reservation_finalized
            if reservation_finalized or not effective_release:
                return
            reservation_finalized = True
            try:
                await self._quota.release_reservation(
                    reservation_id,
                    reason=reason,
                )
            except Exception as rel_exc:
                if getattr(rel_exc, "code", None) == "QUOTA_RESERVATION_NOT_FOUND" or (
                    type(rel_exc).__name__ == "QuotaReservationNotFoundError"
                ):
                    logger.info(
                        "ai_execution_release_not_found",
                        extra={"reservation_id": str(reservation_id)},
                    )
                    return
                raise

        async def _cleanup_on_cancel() -> None:
            await _release_once("CANCELLED")
            if run is not None and self._workflow_repo is not None:
                await self._workflow_repo.add_run(
                    run.fail(now=datetime.now(UTC), error_detail="CANCELLED")
                )

        async def _cleanup_on_failure(
            err: Exception | None,
            attempts_made: int,
            category: AIErrorCategory,
            repairs_made: int,
            p_tokens: int,
            c_tokens: int,
            t_tokens: int,
        ) -> None:
            err_name = type(err).__name__ if err else "AI_EXECUTION_FAILED"
            logger.warning(
                "ai_execution_failed",
                extra={
                    "operation_type": operation_type,
                    "reservation_id": str(reservation_id),
                    "error_category": category.value,
                    "repair_attempts": repairs_made,
                    "attempts": attempts_made,
                    "error_type": err_name,
                    "prompt_tokens": p_tokens,
                    "output_tokens": c_tokens,
                    "completion_tokens": c_tokens,
                    "thinking_tokens": t_tokens,
                },
            )
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
                            "prompt_tokens": p_tokens,
                            **prompt_audit,
                        },
                        output_payload={
                            "error": str(err) if err else err_name,
                            "error_category": category.value,
                            "repair_attempts": repairs_made,
                            "prompt_tokens": p_tokens,
                            "output_tokens": c_tokens,
                            "completion_tokens": c_tokens,
                            "thinking_tokens": t_tokens,
                        },
                        retry_count=max(0, attempts_made - 1),
                        started_at=started_at,
                        completed_at=finished_at,
                    )
                )

        last_error: Exception | None = None
        last_error_category: AIErrorCategory | None = None
        attempts_done = 0
        repair_attempts_done = 0
        http500_retries_used = 0
        validated_value: Any = None
        prompt_tokens = 0
        completion_tokens = 0
        thinking_tokens = 0
        resolved_model_id = model_name
        succeeded = False
        is_tool_stage = bool(tools and tool_executor is not None and max_tool_calls > 0)

        effective_tool_call_timeout = (
            tool_call_timeout_seconds
            if tool_call_timeout_seconds is not None
            else self._tool_call_timeout_seconds
        )
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
                        "timeout_seconds": remaining_seconds,
                    }
                    if tools is not None:
                        call_kwargs["tools"] = tools
                        call_kwargs["tool_executor"] = tool_executor
                        call_kwargs["max_tool_calls"] = max_tool_calls
                        if effective_tool_call_timeout is not None:
                            call_kwargs["tool_call_timeout_seconds"] = min(
                                float(effective_tool_call_timeout), remaining_seconds
                            )
                    if thinking_level is not None:
                        call_kwargs["thinking_level"] = thinking_level

                    raw_gen = await asyncio.wait_for(
                        self._provider.generate_structured(**call_kwargs),
                        timeout=remaining_seconds,
                    )
                    payload, p_tok, c_tok, t_tok, m_id, adapter_repairs = _extract_raw_gen(
                        raw_gen, model_name, self._provider
                    )
                    prompt_tokens += p_tok
                    completion_tokens += c_tok
                    thinking_tokens += t_tok
                    resolved_model_id = m_id
                    repair_attempts_done = max(repair_attempts_done, adapter_repairs)

                    validated_value = OutputEngine.validate(payload, response_schema)
                    succeeded = True
                    last_error = None
                    last_error_category = None
                    break
                except Exception as exc:
                    exc_category = classify_ai_error(exc)
                    if getattr(exc, "already_repaired", False):
                        repair_attempts_done = max(repair_attempts_done, 1)
                    if isinstance(exc, SchemaMismatchError):
                        prompt_tokens += exc.prompt_tokens
                        t_tok_err = int(exc.thinking_tokens or 0)
                        completion_tokens += max(int(exc.output_tokens or 0), t_tok_err)
                        thinking_tokens += t_tok_err
                        if exc.model_id:
                            resolved_model_id = exc.model_id

                    already_repaired = (
                        bool(getattr(exc, "already_repaired", False)) or repair_attempts_done >= 1
                    )
                    remaining_seconds = deadline - loop.time()
                    if (
                        exc_category is AIErrorCategory.SCHEMA_MISMATCH
                        and not is_tool_stage
                        and not already_repaired
                        and remaining_seconds > 2.0
                    ):
                        concise_errors = format_concise_schema_errors(exc)
                        repair_user_prompt = (
                            f"{user_prompt}\n\n[SCHEMA_REPAIR_ERRORS]\n{concise_errors}\n"
                            "Hãy sửa lại JSON cho đúng hoàn toàn schema yêu cầu."
                        )
                        repair_kwargs: dict[str, Any] = {
                            "system_prompt": system_prompt,
                            "user_prompt": repair_user_prompt,
                            "response_schema": response_schema,
                            "timeout_seconds": remaining_seconds,
                        }
                        if thinking_level is not None:
                            repair_kwargs["thinking_level"] = thinking_level
                        repair_attempts_done = 1
                        try:
                            repair_raw = await asyncio.wait_for(
                                self._provider.generate_structured(**repair_kwargs),
                                timeout=remaining_seconds,
                            )
                            r_payload, r_p_tok, r_c_tok, r_t_tok, r_m_id, _ = _extract_raw_gen(
                                repair_raw, model_name, self._provider
                            )
                            prompt_tokens += r_p_tok
                            completion_tokens += r_c_tok
                            thinking_tokens += r_t_tok
                            resolved_model_id = r_m_id
                            validated_value = OutputEngine.validate(r_payload, response_schema)
                            succeeded = True
                            last_error = None
                            last_error_category = None
                            break
                        except Exception as repair_exc:
                            if isinstance(repair_exc, SchemaMismatchError):
                                prompt_tokens += repair_exc.prompt_tokens
                                r_t_tok_err = int(repair_exc.thinking_tokens or 0)
                                completion_tokens += max(
                                    int(repair_exc.output_tokens or 0), r_t_tok_err
                                )
                                thinking_tokens += r_t_tok_err
                                if repair_exc.model_id:
                                    resolved_model_id = repair_exc.model_id
                            last_error = repair_exc
                            last_error_category = classify_ai_error(repair_exc)
                            break

                    last_error = exc
                    last_error_category = exc_category
                    if attempt > self._max_retries or not self._retry_predicate(exc):
                        break
                    if _is_http_500_stream_error(exc):
                        if http500_retries_used >= 1:
                            break
                        http500_retries_used += 1
                    backoff_cap = min(10.0, float(2**attempt))
                    remaining_seconds = deadline - loop.time()
                    if remaining_seconds <= 0:
                        last_error = TimeoutError("AI execution exceeded the total timeout budget")
                        last_error_category = AIErrorCategory.TIMEOUT
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
            failure_category = last_error_category or (
                classify_ai_error(last_error) if last_error is not None else AIErrorCategory.OTHER
            )
            try:
                await asyncio.shield(
                    _cleanup_on_failure(
                        last_error,
                        attempts_done,
                        failure_category,
                        repair_attempts_done,
                        prompt_tokens,
                        max(completion_tokens, thinking_tokens),
                        thinking_tokens,
                    )
                )
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
        billable_completion_tokens = max(completion_tokens, thinking_tokens)
        await _commit_once(
            p_tokens=prompt_tokens,
            c_tokens=billable_completion_tokens,
            t_tokens=thinking_tokens,
            actual_model=resolved_model_id,
        )
        logger.info(
            "ai_execution_completed",
            extra={
                "operation_type": operation_type,
                "step_name": step_name or operation_type,
                "model_id": resolved_model_id,
                "actual_model_id": resolved_model_id,
                "prompt_tokens": prompt_tokens,
                "output_tokens": billable_completion_tokens,
                "completion_tokens": billable_completion_tokens,
                "thinking_tokens": thinking_tokens,
                "attempts": attempts_done,
                "repair_attempts": repair_attempts_done,
                "reservation_id": str(reservation_id),
            },
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
                        "model_id": resolved_model_id,
                        "actual_model_id": resolved_model_id,
                        "prompt_tokens": prompt_tokens,
                        "output_tokens": billable_completion_tokens,
                        "completion_tokens": billable_completion_tokens,
                        "thinking_tokens": thinking_tokens,
                        "attempts": attempts_done,
                        "repair_attempts": repair_attempts_done,
                    },
                    retry_count=max(0, attempts_done - 1),
                    started_at=started_at,
                    completed_at=finished_at,
                )
            )
        return AIExecutionResult(
            value=validated_value,
            prompt_tokens=prompt_tokens,
            completion_tokens=billable_completion_tokens,
            attempts=attempts_done,
            reservation_id=reservation_id,
            thinking_tokens=thinking_tokens,
            model_id=resolved_model_id,
            repair_attempts=repair_attempts_done,
            error_category=None,
        )
