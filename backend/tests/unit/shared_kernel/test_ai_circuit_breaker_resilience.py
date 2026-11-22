from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
import redis.asyncio as redis
from fastapi import FastAPI
from pydantic import BaseModel, ValidationError

from src.evaluation.presentation.deps import get_evaluation_llm_provider
from src.main import create_app
from src.planning.presentation.deps import get_llm_provider
from src.shared_kernel.application.harness.execution_manager import (
    AIExecutionManager,
    default_ai_retry_predicate,
)
from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
    SchemaMismatchError,
)
from src.shared_kernel.config import Settings, get_settings
from src.shared_kernel.infrastructure.external_ai.circuit_breaker import (
    _LUA_RECORD_FAILURE,
    AIServiceUnavailableError,
    CircuitBreakingLLMProvider,
    CircuitState,
    InMemoryCircuitStateStore,
    RedisCircuitStateStore,
    reset_shared_circuit_breakers,
    wrap_with_circuit_breaker,
)


class _DummyOutput(BaseModel):
    answer: str


class _ScriptedProvider:
    supports_native_structured_output = True

    def __init__(self, outcomes: list[Any], *, gate: asyncio.Event | None = None) -> None:
        self._outcomes = list(outcomes)
        self._gate = gate
        self.calls = 0

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
        del system_prompt, user_prompt, response_schema, tools, tool_executor
        del max_tool_calls, thinking_level, timeout_seconds, tool_call_timeout_seconds
        self.calls += 1
        if self._gate is not None:
            await self._gate.wait()
        outcome = self._outcomes.pop(0) if self._outcomes else {"answer": "ok"}
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome, 10, 5

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        del system_prompt, user_prompt
        yield '{"answer": "ok"}'


class _RecordingQuota:
    def __init__(self) -> None:
        self.reserved: list[UUID] = []
        self.committed: list[UUID] = []
        self.released: list[tuple[UUID, str]] = []

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GENERATION",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        del user_id, operation_type, cost, ttl_seconds
        rid = uuid4()
        self.reserved.append(rid)
        return rid

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "",
    ) -> None:
        del prompt_tokens, completion_tokens, model_name
        self.committed.append(reservation_id)

    async def release_reservation(
        self,
        reservation_id: UUID,
        reason: str = "RELEASED",
    ) -> None:
        self.released.append((reservation_id, reason))

    async def record_attempt_usage(self, **kwargs: Any) -> None:
        del kwargs


class _FlakyRedisClient:
    """In-memory Redis test double supporting Lua eval and simulated disconnect/reconnect."""

    def __init__(self, *, fail_mode: Exception | None = None) -> None:
        self.fail_mode = fail_mode
        self.data: dict[str, Any] = {}
        self.ttls: dict[str, int] = {}
        self.eval_calls: list[tuple[str, int, tuple[Any, ...]]] = []

    def _maybe_fail(self) -> None:
        if self.fail_mode is not None:
            raise self.fail_mode

    async def exists(self, key: str) -> int:
        self._maybe_fail()
        return 1 if key in self.data else 0

    async def set(self, key: str, value: str, *, ex: int | None = None, nx: bool = False) -> bool:
        self._maybe_fail()
        if nx and key in self.data:
            return False
        self.data[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def delete(self, *keys: str) -> int:
        self._maybe_fail()
        deleted = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                deleted += 1
            self.ttls.pop(key, None)
        return deleted

    async def eval(self, script: str, numkeys: int, *keys_and_args: Any) -> int:
        self._maybe_fail()
        self.eval_calls.append((script, numkeys, keys_and_args))
        key = str(keys_and_args[0])
        window_seconds = int(keys_and_args[1])
        count = int(self.data.get(key, 0)) + 1
        self.data[key] = count
        if count == 1 or self.ttls.get(key, -1) < 0:
            self.ttls[key] = window_seconds
        return count


@pytest.mark.asyncio
async def test_circuit_closed_open_half_open_closed_recovery_and_telemetry() -> None:
    now = [100.0]
    state = InMemoryCircuitStateStore(
        window_seconds=60,
        open_seconds=30,
        clock=lambda: now[0],
    )
    provider = _ScriptedProvider(
        [
            RuntimeError("503 Service Unavailable"),
            RuntimeError("502 Bad Gateway"),
            {"answer": "recovered"},
            {"answer": "healthy-again"},
        ]
    )
    circuit = CircuitBreakingLLMProvider(provider, state, failure_threshold=2)

    assert state.current_state() is CircuitState.CLOSED

    with pytest.raises(RuntimeError, match="503"):
        await circuit.generate_structured(response_schema=_DummyOutput)
    assert state.current_state() is CircuitState.CLOSED

    with pytest.raises(RuntimeError, match="502"):
        await circuit.generate_structured(response_schema=_DummyOutput)
    assert state.current_state() is CircuitState.OPEN

    # Open state rejects fast without calling underlying provider
    with pytest.raises(AIServiceUnavailableError):
        await circuit.generate_structured(response_schema=_DummyOutput)
    assert provider.calls == 2

    # Advance clock past cooldown -> HALF_OPEN -> single probe succeeds -> CLOSED
    now[0] += 31.0
    assert state.current_state() is CircuitState.HALF_OPEN

    payload, _, _ = await circuit.generate_structured(response_schema=_DummyOutput)
    assert payload == {"answer": "recovered"}
    assert state.current_state() is CircuitState.CLOSED

    payload2, _, _ = await circuit.generate_structured(response_schema=_DummyOutput)
    assert payload2 == {"answer": "healthy-again"}

    telemetry = circuit.get_telemetry()
    assert telemetry == {
        "rejected_calls": 1,
        "recorded_failures": 2,
        "opened_count": 1,
        "half_open_probes": 1,
        "recovery_count": 1,
        "redis_fallback_count": 0,
    }


@pytest.mark.asyncio
async def test_half_open_concurrency_allows_single_probe_and_rejects_others() -> None:
    gate = asyncio.Event()
    state = InMemoryCircuitStateStore(window_seconds=60, open_seconds=60)
    provider = _ScriptedProvider([{"answer": "probe-ok"}], gate=gate)
    circuit = CircuitBreakingLLMProvider(provider, state, failure_threshold=1)

    await state.open()
    state.elapse_cooldown()

    probe_task = asyncio.create_task(circuit.generate_structured(response_schema=_DummyOutput))
    # Yield so probe_task acquires the single HALF_OPEN probe lock and blocks on gate
    await asyncio.sleep(0)

    # Concurrent callers while probe is in flight MUST be rejected immediately
    with pytest.raises(AIServiceUnavailableError):
        await circuit.generate_structured(response_schema=_DummyOutput)
    with pytest.raises(AIServiceUnavailableError):
        await circuit.generate_structured(response_schema=_DummyOutput)

    gate.set()
    payload, _, _ = await probe_task
    assert payload == {"answer": "probe-ok"}
    assert provider.calls == 1
    assert state.opened is False

    telemetry = circuit.get_telemetry()
    assert telemetry["half_open_probes"] == 1
    assert telemetry["rejected_calls"] == 2
    assert telemetry["recovery_count"] == 1


@pytest.mark.asyncio
async def test_half_open_failed_probe_reopens_circuit_immediately() -> None:
    state = InMemoryCircuitStateStore(window_seconds=60, open_seconds=60)
    provider = _ScriptedProvider([TimeoutError("gateway timeout")])
    circuit = CircuitBreakingLLMProvider(provider, state, failure_threshold=3)

    await state.open()
    state.elapse_cooldown()

    with pytest.raises(TimeoutError):
        await circuit.generate_structured(response_schema=_DummyOutput)

    assert state.opened is True
    assert state.cooldown_active is True
    with pytest.raises(AIServiceUnavailableError):
        await circuit.generate_structured(response_schema=_DummyOutput)

    telemetry = circuit.get_telemetry()
    assert telemetry["half_open_probes"] == 1
    assert telemetry["opened_count"] == 1
    assert telemetry["rejected_calls"] == 1
    assert telemetry["recovery_count"] == 0


@pytest.mark.asyncio
async def test_retryable_vs_non_retryable_errors_classification() -> None:
    # Build a real Pydantic ValidationError
    with pytest.raises(ValidationError) as exc_info:
        _DummyOutput.model_validate({})
    validation_err = exc_info.value

    class _StatusError(RuntimeError):
        def __init__(self, status_code: int, message: str) -> None:
            super().__init__(message)
            self.status_code = status_code

    non_retryable_errors: list[Exception] = [
        validation_err,
        SchemaMismatchError("bad schema"),
        _StatusError(400, "400 Bad Request"),
        _StatusError(401, "401 Unauthorized"),
        _StatusError(403, "403 Forbidden"),
        ValueError("invalid prompt"),
    ]
    state = InMemoryCircuitStateStore()
    provider = _ScriptedProvider(non_retryable_errors)
    circuit = CircuitBreakingLLMProvider(provider, state, failure_threshold=1)

    for expected_exc in non_retryable_errors:
        with pytest.raises(type(expected_exc)):
            await circuit.generate_structured(response_schema=_DummyOutput)

    assert state.opened is False
    assert state.failures == 0
    assert circuit.get_telemetry()["recorded_failures"] == 0

    # Transient provider failures MUST trip the circuit
    transient_errors: list[Exception] = [
        _StatusError(429, "429 Too Many Requests"),
        _StatusError(500, "500 Internal Server Error"),
        _StatusError(503, "503 Service Unavailable"),
        TimeoutError("upstream timed out"),
        ConnectionError("connection reset by peer"),
    ]
    for transient in transient_errors:
        t_state = InMemoryCircuitStateStore()
        t_provider = _ScriptedProvider([transient])
        t_circuit = CircuitBreakingLLMProvider(t_provider, t_state, failure_threshold=1)
        with pytest.raises(type(transient)):
            await t_circuit.generate_structured(response_schema=_DummyOutput)
        assert t_state.opened is True
        assert t_circuit.get_telemetry()["recorded_failures"] == 1
        assert t_circuit.get_telemetry()["opened_count"] == 1


@pytest.mark.asyncio
async def test_redis_disconnect_falls_back_to_in_memory_and_recovers_on_reconnect() -> None:
    fake_redis = _FlakyRedisClient(fail_mode=redis.ConnectionError("redis connection refused"))
    store = RedisCircuitStateStore(
        fake_redis,  # type: ignore[arg-type]
        namespace="focusflow:ai:circuit:test",
        window_seconds=60,
        open_seconds=60,
    )
    provider = _ScriptedProvider(
        [
            {"answer": "ok-during-redis-outage"},
            RuntimeError("503 upstream down"),
            {"answer": "ok-after-reconnect"},
        ]
    )
    circuit = CircuitBreakingLLMProvider(provider, store, failure_threshold=1)

    # 1. Redis is down: LLM call STILL succeeds (no crash!), fallback increments
    payload, _, _ = await circuit.generate_structured(response_schema=_DummyOutput)
    assert payload == {"answer": "ok-during-redis-outage"}
    assert store.redis_fallback_count >= 1

    # 2. Redis is still down: provider failure trips in-memory fallback circuit
    with pytest.raises(RuntimeError, match="503"):
        await circuit.generate_structured(response_schema=_DummyOutput)

    with pytest.raises(AIServiceUnavailableError):
        await circuit.generate_structured(response_schema=_DummyOutput)

    # 3. Redis reconnects: store resumes Redis operations cleanly and uses Lua script
    fake_redis.fail_mode = None
    payload2, _, _ = await circuit.generate_structured(response_schema=_DummyOutput)
    assert payload2 == {"answer": "ok-after-reconnect"}

    # Verify atomic Lua script execution on Redis failure recording
    count = await store.record_failure()
    assert count == 1
    assert len(fake_redis.eval_calls) == 1
    assert fake_redis.eval_calls[0][0] == _LUA_RECORD_FAILURE
    assert fake_redis.ttls["focusflow:ai:circuit:test:failures"] == 60
    assert circuit.get_telemetry()["redis_fallback_count"] == store.redis_fallback_count
    assert circuit.get_telemetry()["redis_fallback_count"] >= 4


@pytest.mark.asyncio
async def test_execution_manager_does_not_retry_circuit_open_error() -> None:
    assert default_ai_retry_predicate(AIServiceUnavailableError("open")) is False

    state = InMemoryCircuitStateStore()
    await state.open()
    provider = _ScriptedProvider([{"answer": "never-called"}])
    circuit = CircuitBreakingLLMProvider(provider, state, failure_threshold=1)
    quota = _RecordingQuota()

    sleep_calls: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    manager = AIExecutionManager(
        provider=circuit,
        quota=quota,
        timeout_seconds=10.0,
        max_retries=3,
        sleep=_fake_sleep,
    )

    with pytest.raises(AIServiceUnavailableError):
        await manager.execute(
            user_id=uuid4(),
            operation_type="GOAL_CLARIFICATION",
            system_prompt="sys",
            user_prompt="usr",
            response_schema=_DummyOutput,
            model_name="mock",
            thinking_level="LOW",
        )

    assert provider.calls == 0
    assert sleep_calls == []
    assert len(quota.reserved) == 1
    assert len(quota.committed) == 0
    assert len(quota.released) == 1
    assert circuit.get_telemetry()["rejected_calls"] == 1


@pytest.mark.asyncio
async def test_execution_manager_propagates_cancellation_during_retry_backoff() -> None:
    provider = _ScriptedProvider([TimeoutError("transient timeout"), {"answer": "too-late"}])
    quota = _RecordingQuota()
    entered_sleep = asyncio.Event()

    async def _cancellable_sleep(_delay: float) -> None:
        entered_sleep.set()
        await asyncio.sleep(60)

    manager = AIExecutionManager(
        provider=provider,
        quota=quota,
        timeout_seconds=10.0,
        max_retries=2,
        sleep=_cancellable_sleep,
    )

    task = asyncio.create_task(
        manager.execute(
            user_id=uuid4(),
            operation_type="GOAL_CLARIFICATION",
            system_prompt="sys",
            user_prompt="usr",
            response_schema=_DummyOutput,
            model_name="mock",
            thinking_level="LOW",
        )
    )
    await entered_sleep.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert provider.calls == 1
    assert len(quota.committed) == 0
    assert len(quota.released) == 1
    assert quota.released[0][1] == "CANCELLED"


def test_shared_circuit_breaker_wiring_and_config_defaults() -> None:
    reset_shared_circuit_breakers()
    get_settings.cache_clear()
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.ai_harness_v2_enabled is True
    assert settings.ai_circuit_breaker_enabled is True
    assert settings.ai_prove_question_timeout_seconds == 20.0
    assert settings.ai_prove_grader_timeout_seconds == 25.0
    assert settings.ai_proposal_finalize_reserve_seconds == 6.0
    assert settings.db_pool_size == 10
    assert settings.db_max_overflow == 10
    assert settings.db_pool_timeout == 30.0
    assert settings.db_pool_recycle == 1800
    assert settings.db_pool_pre_ping is True
    assert settings.db_connect_timeout == 10.0
    assert settings.db_command_timeout == 30.0
    assert settings.db_statement_timeout_ms == 30000
    assert settings.db_lock_timeout_ms == 10000

    planning_provider = get_llm_provider()
    evaluation_provider = get_evaluation_llm_provider()
    assert isinstance(planning_provider, CircuitBreakingLLMProvider)
    assert isinstance(evaluation_provider, CircuitBreakingLLMProvider)
    assert planning_provider._state is evaluation_provider._state
    assert wrap_with_circuit_breaker(planning_provider) is planning_provider


@pytest.mark.asyncio
async def test_fastapi_maps_ai_service_unavailable_to_503() -> None:
    app: FastAPI = create_app()

    @app.get("/_test/circuit-open")
    async def _raise_circuit_open() -> dict[str, str]:
        raise AIServiceUnavailableError("Circuit breaker is OPEN")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/_test/circuit-open")

    assert resp.status_code == 503
    assert resp.json() == {
        "code": "AI_SERVICE_UNAVAILABLE",
        "detail": "Circuit breaker is OPEN",
    }
