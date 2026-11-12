import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any, Protocol

import redis.asyncio as redis

from src.shared_kernel.application.llm_port import (
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)


class AIServiceUnavailableError(RuntimeError):
    code = "AI_SERVICE_UNAVAILABLE"


class CircuitStateStore(Protocol):
    async def is_open(self) -> bool: ...

    async def try_half_open_probe(self) -> bool: ...

    async def record_failure(self) -> int: ...

    async def open(self) -> None: ...

    async def reset(self) -> None: ...


class RedisCircuitStateStore(CircuitStateStore):
    def __init__(
        self,
        client: redis.Redis,
        *,
        namespace: str = "focusflow:ai:circuit",
        window_seconds: int = 60,
        open_seconds: int = 60,
    ) -> None:
        self._client = client
        self._failures_key = f"{namespace}:failures"
        self._state_key = f"{namespace}:state"
        self._cooldown_key = f"{namespace}:cooldown"
        self._probe_key = f"{namespace}:probe"
        self._window_seconds = window_seconds
        self._open_seconds = open_seconds

    async def is_open(self) -> bool:
        if not await self._client.exists(self._state_key):
            return False
        if await self._client.exists(self._cooldown_key):
            return True
        return not await self.try_half_open_probe()

    async def try_half_open_probe(self) -> bool:
        return bool(await self._client.set(self._probe_key, "1", ex=self._open_seconds, nx=True))

    async def record_failure(self) -> int:
        count = int(await self._client.incr(self._failures_key))
        if count == 1:
            await self._client.expire(self._failures_key, self._window_seconds)
        return count

    async def open(self) -> None:
        await self._client.set(self._state_key, "OPEN")
        await self._client.set(self._cooldown_key, "1", ex=self._open_seconds)
        await self._client.delete(self._probe_key)

    async def reset(self) -> None:
        await self._client.delete(
            self._failures_key,
            self._state_key,
            self._cooldown_key,
            self._probe_key,
        )


class InMemoryCircuitStateStore(CircuitStateStore):
    """Deterministic test store; production uses RedisCircuitStateStore."""

    def __init__(self) -> None:
        self.opened = False
        self.cooldown_active = False
        self.failures = 0
        self.probe_claimed = False

    async def is_open(self) -> bool:
        if not self.opened:
            return False
        if self.cooldown_active:
            return True
        return not await self.try_half_open_probe()

    async def try_half_open_probe(self) -> bool:
        if self.probe_claimed:
            return False
        self.probe_claimed = True
        return True

    async def record_failure(self) -> int:
        self.failures += 1
        return self.failures

    async def open(self) -> None:
        self.opened = True
        self.cooldown_active = True
        self.probe_claimed = False

    def elapse_cooldown(self) -> None:
        self.cooldown_active = False

    async def reset(self) -> None:
        self.opened = False
        self.cooldown_active = False
        self.failures = 0
        self.probe_claimed = False


RetryablePredicate = Callable[[Exception], bool]


class CircuitBreakingLLMProvider(LLMProviderPort):
    def __init__(
        self,
        provider: LLMProviderPort,
        state: CircuitStateStore,
        *,
        failure_threshold: int = 3,
        retryable: RetryablePredicate | None = None,
    ) -> None:
        self._provider = provider
        self._state = state
        self._failure_threshold = max(1, failure_threshold)
        self._retryable = retryable or self._default_retryable

    @staticmethod
    def _default_retryable(exc: Exception) -> bool:
        text = str(exc).lower()
        return isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or any(
            marker in text for marker in ("429", "rate limit", "500", "502", "503", "504")
        )

    async def _before_call(self) -> None:
        if await self._state.is_open():
            raise AIServiceUnavailableError(
                "Dịch vụ AI đang tạm bảo trì. Vui lòng thử lại hoặc lập kế hoạch thủ công."
            )

    async def _record_failure(self, exc: Exception) -> None:
        if not self._retryable(exc):
            return
        failures = await self._state.record_failure()
        if failures >= self._failure_threshold:
            await self._state.open()

    async def generate_structured(
        self,
        prompt: str | None = None,
        system_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        *,
        user_prompt: str | None = None,
        temperature: float = 0.2,
        tools: list[LLMToolDeclarationDTO] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 4,
        thinking_level: str | None = None,
    ) -> tuple[dict[str, Any], int, int]:
        await self._before_call()
        try:
            result = await self._provider.generate_structured(
                prompt=prompt,
                system_prompt=system_prompt,
                response_schema=response_schema,
                user_prompt=user_prompt,
                temperature=temperature,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
            )
        except Exception as exc:
            await self._record_failure(exc)
            raise
        await self._state.reset()
        return result

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        await self._before_call()
        try:
            async for chunk in self._provider.stream_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            ):
                yield chunk
        except Exception as exc:
            await self._record_failure(exc)
            raise
        await self._state.reset()
