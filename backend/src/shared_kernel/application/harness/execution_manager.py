import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar
from uuid import UUID

from src.shared_kernel.application.llm_port import (
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)

from .output_engine import OutputEngine

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
    ) -> None:
        self._provider = provider
        self._quota = quota
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._sleep = sleep
        self._retry_predicate = retry_predicate or (lambda _exc: True)

    async def execute(
        self,
        *,
        user_id: UUID,
        operation_type: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        model_name: str,
        tools: list[LLMToolDeclarationDTO] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 4,
        thinking_level: str | None = None,
    ) -> AIExecutionResult:
        reservation_id = await self._quota.reserve_quota(
            user_id,
            operation_type=operation_type,
            ttl_seconds=max(120, int(self._timeout_seconds) + 30),
        )
        last_error: Exception | None = None
        try:
            for attempt in range(1, self._max_retries + 2):
                try:
                    payload, prompt_tokens, completion_tokens = await asyncio.wait_for(
                        self._provider.generate_structured(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            response_schema=response_schema,
                            tools=tools,
                            tool_executor=tool_executor,
                            max_tool_calls=max_tool_calls,
                            thinking_level=thinking_level,
                        ),
                        timeout=self._timeout_seconds,
                    )
                    value = OutputEngine.validate(payload, response_schema)
                    await self._quota.commit_reservation(
                        reservation_id,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        model_name=model_name,
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
            await self._quota.release_reservation(reservation_id, reason="CANCELLED")
            raise
        await self._quota.release_reservation(
            reservation_id,
            reason=type(last_error).__name__ if last_error else "AI_EXECUTION_FAILED",
        )
        if last_error is None:
            raise RuntimeError("AI execution failed without an exception")
        raise last_error
