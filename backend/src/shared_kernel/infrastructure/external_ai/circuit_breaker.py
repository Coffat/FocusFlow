import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable, Sequence
from enum import StrEnum
from typing import Any, Literal, Protocol, cast

import redis.asyncio as redis
import structlog
from pydantic import ValidationError

from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
    SchemaMismatchError,
)
from src.shared_kernel.config import get_settings

_logger = structlog.get_logger(__name__)

_DEFAULT_UNAVAILABLE_MESSAGE = (
    "Dịch vụ AI đang tạm bảo trì. Vui lòng thử lại hoặc lập kế hoạch thủ công."
)

# Atomic failure counter: INCR + EXPIRE on first hit + TTL < 0 self-heal.
_LUA_RECORD_FAILURE = """
local count = redis.call("INCR", KEYS[1])
if count == 1 then
    redis.call("EXPIRE", KEYS[1], tonumber(ARGV[1]))
else
    local ttl = redis.call("TTL", KEYS[1])
    if ttl < 0 then
        redis.call("EXPIRE", KEYS[1], tonumber(ARGV[1]))
    end
end
return count
"""

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
_RETRYABLE_MARKERS = (
    "408",
    "429",
    "rate limit",
    "resource_exhausted",
    "500",
    "502",
    "503",
    "504",
    "timeout",
    "timed out",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "connection",
    "stream interrupted",
    "high demand",
    "overloaded",
)
_RETRYABLE_EXCEPTION_TYPES = frozenset(
    {
        "RateLimitError",
        "ServiceUnavailableError",
        "InternalServerError",
        "BadGatewayError",
        "GatewayTimeoutError",
        "APIConnectionError",
        "APITimeoutError",
        "ConnectError",
        "ReadTimeout",
        "ConnectTimeout",
        "RemoteProtocolError",
    }
)


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class AIServiceUnavailableError(RuntimeError):
    code = "AI_SERVICE_UNAVAILABLE"


CallPermission = Literal["CLOSED", "HALF_OPEN_PROBE", "OPEN"]


class CircuitStateStore(Protocol):
    async def is_open(self) -> bool: ...

    async def try_half_open_probe(self) -> bool: ...

    async def record_failure(self) -> int: ...

    async def open(self) -> None: ...

    async def reset(self) -> None: ...


class InMemoryCircuitStateStore(CircuitStateStore):
    """In-memory circuit state store used in tests and as automatic Redis outage fallback."""

    def __init__(
        self,
        *,
        window_seconds: int = 60,
        open_seconds: int = 60,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.opened = False
        self.cooldown_active = False
        self.failures = 0
        self.probe_claimed = False
        self._window_seconds = max(1, int(window_seconds))
        self._open_seconds = max(1, int(open_seconds))
        self._clock = clock or time.monotonic
        self._window_started_at: float | None = None
        self._cooldown_until: float | None = None
        self._probe_expires_at: float | None = None
        self._lock = asyncio.Lock()

    def current_state(self) -> CircuitState:
        if not self.opened:
            return CircuitState.CLOSED
        if self.cooldown_active:
            if self._cooldown_until is not None and self._clock() >= self._cooldown_until:
                return CircuitState.HALF_OPEN
            return CircuitState.OPEN
        return CircuitState.HALF_OPEN

    async def acquire_permission(self) -> CallPermission:
        async with self._lock:
            if not self.opened:
                return "CLOSED"
            now = self._clock()
            if self.cooldown_active:
                if self._cooldown_until is not None and now >= self._cooldown_until:
                    self.cooldown_active = False
                    self._cooldown_until = None
                else:
                    return "OPEN"
            if self.probe_claimed and (
                self._probe_expires_at is None or now < self._probe_expires_at
            ):
                return "OPEN"
            self.probe_claimed = True
            self._probe_expires_at = now + self._open_seconds
            return "HALF_OPEN_PROBE"

    async def is_open(self) -> bool:
        return (await self.acquire_permission()) == "OPEN"

    async def try_half_open_probe(self) -> bool:
        async with self._lock:
            now = self._clock()
            if self.probe_claimed and (
                self._probe_expires_at is None or now < self._probe_expires_at
            ):
                return False
            self.probe_claimed = True
            self._probe_expires_at = now + self._open_seconds
            return True

    async def release_probe(self) -> None:
        async with self._lock:
            self.probe_claimed = False
            self._probe_expires_at = None

    async def record_failure(self) -> int:
        async with self._lock:
            now = self._clock()
            if (
                self._window_started_at is None
                or (now - self._window_started_at) >= self._window_seconds
            ):
                self.failures = 0
                self._window_started_at = now
            self.failures += 1
            return self.failures

    async def open(self) -> None:
        async with self._lock:
            self.opened = True
            self.cooldown_active = True
            self._cooldown_until = self._clock() + self._open_seconds
            self.probe_claimed = False
            self._probe_expires_at = None

    def elapse_cooldown(self) -> None:
        self.cooldown_active = False
        self._cooldown_until = None

    async def reset(self) -> None:
        async with self._lock:
            self.opened = False
            self.cooldown_active = False
            self.failures = 0
            self.probe_claimed = False
            self._window_started_at = None
            self._cooldown_until = None
            self._probe_expires_at = None


class RedisCircuitStateStore(CircuitStateStore):
    """Redis-backed distributed circuit state store with automatic in-memory fallback."""

    def __init__(
        self,
        client: redis.Redis,
        *,
        namespace: str = "focusflow:ai:circuit",
        window_seconds: int = 60,
        open_seconds: int = 60,
        fallback: InMemoryCircuitStateStore | None = None,
    ) -> None:
        self._client = client
        self._namespace = namespace
        self._failures_key = f"{namespace}:failures"
        self._state_key = f"{namespace}:state"
        self._cooldown_key = f"{namespace}:cooldown"
        self._probe_key = f"{namespace}:probe"
        self._window_seconds = max(1, int(window_seconds))
        self._open_seconds = max(1, int(open_seconds))
        self._fallback = fallback or InMemoryCircuitStateStore(
            window_seconds=self._window_seconds,
            open_seconds=self._open_seconds,
        )
        self.redis_fallback_count: int = 0

    def _handle_redis_error(self, operation: str, exc: Exception) -> None:
        self.redis_fallback_count += 1
        _logger.warning(
            "ai_circuit_breaker_redis_fallback",
            operation=operation,
            namespace=self._namespace,
            error_type=type(exc).__name__,
            error=str(exc),
            redis_fallback_count=self.redis_fallback_count,
        )

    async def acquire_permission(self) -> CallPermission:
        try:
            if not await self._client.exists(self._state_key):
                return "CLOSED"
            if await self._client.exists(self._cooldown_key):
                return "OPEN"
            claimed = bool(
                await self._client.set(self._probe_key, "1", ex=self._open_seconds, nx=True)
            )
            return "HALF_OPEN_PROBE" if claimed else "OPEN"
        except (redis.RedisError, OSError, TimeoutError) as exc:
            self._handle_redis_error("acquire_permission", exc)
            return await self._fallback.acquire_permission()

    async def is_open(self) -> bool:
        return (await self.acquire_permission()) == "OPEN"

    async def try_half_open_probe(self) -> bool:
        try:
            return bool(
                await self._client.set(self._probe_key, "1", ex=self._open_seconds, nx=True)
            )
        except (redis.RedisError, OSError, TimeoutError) as exc:
            self._handle_redis_error("try_half_open_probe", exc)
            return await self._fallback.try_half_open_probe()

    async def release_probe(self) -> None:
        try:
            await self._client.delete(self._probe_key)
        except (redis.RedisError, OSError, TimeoutError) as exc:
            self._handle_redis_error("release_probe", exc)
            await self._fallback.release_probe()

    async def record_failure(self) -> int:
        try:
            raw = await self._client.eval(
                _LUA_RECORD_FAILURE,
                1,
                self._failures_key,
                self._window_seconds,
            )
            return int(raw)
        except (redis.RedisError, OSError, TimeoutError) as exc:
            self._handle_redis_error("record_failure", exc)
            return await self._fallback.record_failure()

    async def open(self) -> None:
        try:
            await self._client.set(self._state_key, CircuitState.OPEN.value)
            await self._client.set(self._cooldown_key, "1", ex=self._open_seconds)
            await self._client.delete(self._probe_key)
        except (redis.RedisError, OSError, TimeoutError) as exc:
            self._handle_redis_error("open", exc)
            await self._fallback.open()

    async def reset(self) -> None:
        try:
            await self._client.delete(
                self._failures_key,
                self._state_key,
                self._cooldown_key,
                self._probe_key,
            )
        except (redis.RedisError, OSError, TimeoutError) as exc:
            self._handle_redis_error("reset", exc)
        await self._fallback.reset()


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
        self._rejected_calls: int = 0
        self._recorded_failures: int = 0
        self._opened_count: int = 0
        self._half_open_probes: int = 0
        self._recovery_count: int = 0

    @staticmethod
    def _default_retryable(exc: Exception) -> bool:
        if isinstance(
            exc,
            (
                AIServiceUnavailableError,
                ValidationError,
                SchemaMismatchError,
                json.JSONDecodeError,
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                PermissionError,
            ),
        ):
            return False

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

        if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError, OSError)):
            return True

        if type(exc).__name__ in _RETRYABLE_EXCEPTION_TYPES:
            return True

        return any(marker in text for marker in _RETRYABLE_MARKERS)

    def get_telemetry(self) -> dict[str, int]:
        return {
            "rejected_calls": self._rejected_calls,
            "recorded_failures": self._recorded_failures,
            "opened_count": self._opened_count,
            "half_open_probes": self._half_open_probes,
            "recovery_count": self._recovery_count,
            "redis_fallback_count": int(getattr(self._state, "redis_fallback_count", 0)),
        }

    async def _before_call(self) -> bool:
        acquire_fn = getattr(self._state, "acquire_permission", None)
        if callable(acquire_fn):
            permission = cast(CallPermission, await acquire_fn())
            if permission == "OPEN":
                self._rejected_calls += 1
                raise AIServiceUnavailableError(_DEFAULT_UNAVAILABLE_MESSAGE)
            if permission == "HALF_OPEN_PROBE":
                self._half_open_probes += 1
                return True
            return False

        if await self._state.is_open():
            self._rejected_calls += 1
            raise AIServiceUnavailableError(_DEFAULT_UNAVAILABLE_MESSAGE)
        return False

    async def _release_probe_if_needed(self, *, is_half_open_probe: bool) -> None:
        if not is_half_open_probe:
            return
        release_fn = getattr(self._state, "release_probe", None)
        if callable(release_fn):
            await release_fn()

    async def _record_failure(self, exc: Exception, *, is_half_open_probe: bool = False) -> None:
        if not self._retryable(exc):
            await self._release_probe_if_needed(is_half_open_probe=is_half_open_probe)
            return
        self._recorded_failures += 1
        if is_half_open_probe:
            await self._state.open()
            self._opened_count += 1
            return
        failures = await self._state.record_failure()
        if failures >= self._failure_threshold:
            await self._state.open()
            self._opened_count += 1

    async def _record_success(self, *, is_half_open_probe: bool = False) -> None:
        await self._state.reset()
        if is_half_open_probe:
            self._recovery_count += 1

    @property
    def supports_native_structured_output(self) -> bool:
        return bool(getattr(self._provider, "supports_native_structured_output", True))

    @property
    def model_identifier(self) -> str:
        return str(getattr(self._provider, "model_identifier", "gemini-3.8-flash"))

    def resolve_model_for_thinking_level(self, thinking_level: str | None) -> str:
        fn = getattr(self._provider, "resolve_model_for_thinking_level", None)
        if callable(fn):
            return str(fn(thinking_level))
        return self.model_identifier

    @property
    def model_used(self) -> str:
        return str(getattr(self._provider, "model_used", "gemini-3.8-flash"))

    @property
    def last_model_used(self) -> str:
        return str(getattr(self._provider, "last_model_used", self.model_used))

    @property
    def degraded_model_used(self) -> bool:
        return bool(getattr(self._provider, "degraded_model_used", False))

    @property
    def last_degraded_model_used(self) -> bool:
        return bool(getattr(self._provider, "last_degraded_model_used", False))

    async def generate_structured(
        self,
        *,
        system_prompt: str = "",
        user_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> tuple[dict[str, Any], int, int] | LLMGenerationResult:
        is_half_open_probe = await self._before_call()
        try:
            result = await self._provider.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
                timeout_seconds=timeout_seconds,
                tool_call_timeout_seconds=tool_call_timeout_seconds,
            )
        except asyncio.CancelledError:
            await self._release_probe_if_needed(is_half_open_probe=is_half_open_probe)
            raise
        except Exception as exc:
            await self._record_failure(exc, is_half_open_probe=is_half_open_probe)
            raise
        await self._record_success(is_half_open_probe=is_half_open_probe)
        return result

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        is_half_open_probe = await self._before_call()
        try:
            async for chunk in self._provider.stream_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            ):
                yield chunk
        except asyncio.CancelledError:
            await self._release_probe_if_needed(is_half_open_probe=is_half_open_probe)
            raise
        except Exception as exc:
            await self._record_failure(exc, is_half_open_probe=is_half_open_probe)
            raise
        await self._record_success(is_half_open_probe=is_half_open_probe)


_shared_redis_clients: dict[str, redis.Redis] = {}
_shared_circuit_states: dict[tuple[str, str], RedisCircuitStateStore] = {}


def _get_shared_redis_client(redis_url: str) -> redis.Redis:
    client = _shared_redis_clients.get(redis_url)
    if client is None:
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        _shared_redis_clients[redis_url] = client
    return client


def reset_shared_circuit_breakers() -> None:
    """Clear shared circuit breaker state/client caches (intended for tests)."""
    _shared_circuit_states.clear()
    _shared_redis_clients.clear()


def wrap_with_circuit_breaker(
    provider: LLMProviderPort,
    *,
    provider_name: str = "litellm",
) -> LLMProviderPort:
    """Wrap an LLMProviderPort with the canonical shared circuit breaker."""
    if isinstance(provider, CircuitBreakingLLMProvider):
        return provider

    settings = get_settings()
    normalized_name = (provider_name or "litellm").strip().lower() or "litellm"
    cache_key = (settings.redis_url, normalized_name)
    state = _shared_circuit_states.get(cache_key)
    if state is None:
        client = _get_shared_redis_client(settings.redis_url)
        state = RedisCircuitStateStore(
            client,
            namespace=f"focusflow:ai:circuit:{normalized_name}",
            window_seconds=settings.ai_circuit_window_seconds,
            open_seconds=settings.ai_circuit_open_seconds,
        )
        _shared_circuit_states[cache_key] = state

    return CircuitBreakingLLMProvider(
        provider,
        state,
        failure_threshold=settings.ai_circuit_failure_threshold,
    )
