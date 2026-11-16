import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from src.shared_kernel.application.harness.context_engine import ContextEngine
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.harness.models import (
    HarnessContext,
    PromptTemplate,
    ToolResultEnvelope,
    WorkflowRun,
    WorkflowStatus,
    WorkflowType,
)
from src.shared_kernel.application.harness.prompt_registry import PromptRegistry
from src.shared_kernel.application.harness.tool_registry import RegisteredTool, ToolRegistry
from src.shared_kernel.application.llm_port import LLMToolDeclarationDTO
from src.shared_kernel.infrastructure.external_ai.circuit_breaker import (
    AIServiceUnavailableError,
    CircuitBreakingLLMProvider,
    InMemoryCircuitStateStore,
)


class _Output(BaseModel):
    answer: str


class _Provider:
    def __init__(self, outcomes: list[Exception | dict[str, Any]]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    async def generate_structured(
        self, *args: object, **kwargs: object
    ) -> tuple[dict[str, Any], int, int]:
        del args, kwargs
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome, 10, 4

    async def stream_structured(self, **kwargs: object) -> AsyncIterator[str]:
        del kwargs
        yield "{}"


class _SlowProvider(_Provider):
    async def generate_structured(
        self, *args: object, **kwargs: object
    ) -> tuple[dict[str, Any], int, int]:
        del args, kwargs
        self.calls += 1
        await asyncio.sleep(0.05)
        return {"answer": "late"}, 10, 4


class _Quota:
    def __init__(self) -> None:
        self.reservation_id = uuid4()
        self.committed = 0
        self.released: list[str] = []

    async def reserve_quota(self, user_id: UUID, **kwargs: object) -> UUID:
        del user_id, kwargs
        return self.reservation_id

    async def commit_reservation(self, reservation_id: UUID, **kwargs: object) -> None:
        assert reservation_id == self.reservation_id
        self.committed += 1

    async def release_reservation(self, reservation_id: UUID, reason: str = "RELEASED") -> None:
        assert reservation_id == self.reservation_id
        self.released.append(reason)


def _prompt(version: str) -> PromptTemplate:
    values: dict[str, Any] = {
        "prompt_id": "planning.roadmap",
        "version": version,
        "workflow_type": "PLAN_CREATION",
        "skill_id": "roadmap",
        "system_template": "Return a roadmap",
        "output_schema": {"type": "object"},
    }
    return PromptTemplate(
        **values,
        checksum=PromptRegistry.checksum_for(**values),
    )


def test_prompt_registry_is_versioned_immutable_and_checksum_bound() -> None:
    registry = PromptRegistry([_prompt("1.2.0"), _prompt("1.10.0")])
    assert registry.latest("planning.roadmap").version == "1.10.0"
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_prompt("1.2.0"))
    invalid = _prompt("2.0.0")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        registry.register(replace(invalid, checksum="bad"))


def test_context_engine_rejects_raw_history_and_obeys_budget() -> None:
    engine = ContextEngine(total_token_budget=500)
    context = HarnessContext(learning={"summary": "x" * 10_000})
    result = engine.assemble(context)
    assert result.total_tokens <= 500
    assert result.truncated_layers
    with pytest.raises(ValueError, match="study_sessions"):
        engine.assemble(HarnessContext(learning={"study_sessions": []}))


@pytest.mark.asyncio
async def test_tool_registry_enforces_stage_and_standard_envelope() -> None:
    async def handler(arguments: dict[str, Any]) -> ToolResultEnvelope:
        return ToolResultEnvelope(status="success", summary="ok", data=arguments)

    declaration = LLMToolDeclarationDTO(
        name="availability.read",
        description="Read availability",
        parameters_schema={"type": "object"},
    )
    registry = ToolRegistry([RegisteredTool(declaration, frozenset({"SCHEDULE"}), handler)])
    result = await registry.dispatch(
        stage="SCHEDULE", tool_name=declaration.name, arguments={"x": 1}
    )
    assert set(result) == {"status", "summary", "data", "next_actions", "artifacts"}
    with pytest.raises(PermissionError):
        await registry.dispatch(stage="PLAN", tool_name=declaration.name, arguments={})


@pytest.mark.asyncio
async def test_execution_manager_retries_and_commits_exactly_once() -> None:
    quota = _Quota()
    provider = _Provider([TimeoutError(), {"answer": "ok"}])
    manager = AIExecutionManager(
        provider=provider,
        quota=quota,
        sleep=lambda _delay: asyncio.sleep(0),
    )
    result = await manager.execute(
        user_id=uuid4(),
        operation_type="PLAN_CREATION",
        system_prompt="system",
        user_prompt="user",
        response_schema=_Output,
        model_name="mock",
    )
    assert result.attempts == 2
    assert quota.committed == 1
    assert quota.released == []


@pytest.mark.asyncio
async def test_execution_manager_releases_on_terminal_failure() -> None:
    quota = _Quota()
    manager = AIExecutionManager(
        provider=_Provider([TimeoutError("timeout")]),
        quota=quota,
        max_retries=0,
    )
    with pytest.raises(TimeoutError):
        await manager.execute(
            user_id=uuid4(),
            operation_type="PLAN_CREATION",
            system_prompt="system",
            user_prompt="user",
            response_schema=_Output,
            model_name="mock",
        )
    assert quota.committed == 0
    assert quota.released == ["TimeoutError"]


@pytest.mark.asyncio
async def test_execution_manager_enforces_one_total_timeout_across_retries() -> None:
    quota = _Quota()
    provider = _SlowProvider([{"answer": "unused"}])
    manager = AIExecutionManager(
        provider=provider,
        quota=quota,
        timeout_seconds=0.02,
        max_retries=2,
        sleep=lambda _delay: asyncio.sleep(0),
    )

    with pytest.raises((TimeoutError, asyncio.TimeoutError)):
        await manager.execute(
            user_id=uuid4(),
            operation_type="GOAL_CLARIFICATION",
            system_prompt="system",
            user_prompt="user",
            response_schema=_Output,
            model_name="mock",
        )

    assert provider.calls == 1
    assert quota.committed == 0
    assert len(quota.released) == 1


@pytest.mark.asyncio
async def test_circuit_opens_then_allows_one_half_open_probe() -> None:
    state = InMemoryCircuitStateStore()
    provider = _Provider([RuntimeError("503"), {"answer": "recovered"}])
    circuit = CircuitBreakingLLMProvider(provider, state, failure_threshold=1)
    with pytest.raises(RuntimeError, match="503"):
        await circuit.generate_structured(response_schema=_Output)
    with pytest.raises(AIServiceUnavailableError):
        await circuit.generate_structured(response_schema=_Output)
    assert provider.calls == 1
    state.elapse_cooldown()
    payload, _, _ = await circuit.generate_structured(response_schema=_Output)
    assert payload == {"answer": "recovered"}
    assert state.opened is False


def test_workflow_pause_resume_is_explicit() -> None:
    now = datetime.now(UTC)
    run = WorkflowRun(
        id=uuid4(),
        user_id=uuid4(),
        workflow_type=WorkflowType.PLAN_CREATION,
        current_step="CLARIFY",
        status=WorkflowStatus.RUNNING,
        context_snapshot={},
        started_at=now,
    )
    paused = run.pause(now=now, waiting_step="WAITING_CLARIFICATION")
    resumed = paused.resume(next_step="MILESTONES", context_snapshot={"answers": 3})
    assert resumed.status is WorkflowStatus.RUNNING
    assert resumed.context_snapshot == {"answers": 3}


@pytest.mark.asyncio
async def test_execution_manager_post_llm_db_failure_does_not_retry_llm() -> None:
    """T0.3 / T1.2: Post-LLM workflow DB failure must NOT trigger a second LLM call."""
    from src.shared_kernel.application.harness.models import WorkflowStepExecution

    class _FailingWorkflowRepo:
        async def add_run(self, run: WorkflowRun) -> None:
            del run
            raise RuntimeError("Simulated DB connection drop after LLM succeeded")

        async def add_step(self, step: WorkflowStepExecution) -> None:
            del step

    quota = _Quota()
    provider = _Provider([{"answer": "ok"}, {"answer": "should_never_run"}])
    manager = AIExecutionManager(
        provider=provider,
        quota=quota,
        max_retries=2,
        workflow_repo=_FailingWorkflowRepo(),  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="Simulated DB connection drop"):
        await manager.execute(
            user_id=uuid4(),
            operation_type="PLAN_CREATION",
            system_prompt="sys",
            user_prompt="usr",
            response_schema=_Output,
            model_name="gemini-3.8-flash",
            workflow_type=WorkflowType.PLAN_CREATION,
            step_name="STEP_1",
        )

    assert provider.calls == 1
    assert quota.committed == 1
    assert quota.released == []


@pytest.mark.asyncio
async def test_execution_manager_cancellation_uses_shield_and_preserves_original_error() -> None:
    """T0.3 / T1.2: CancelledError triggers shielded quota release; cleanup errors preserve root exception."""
    release_finished = False

    class _SlowReleaseQuota(_Quota):
        async def release_reservation(self, reservation_id: UUID, reason: str = "RELEASED") -> None:
            nonlocal release_finished
            await asyncio.sleep(0.02)
            release_finished = True
            await super().release_reservation(reservation_id, reason=reason)

    class _HangingProvider:
        async def generate_structured(self, **kwargs: object) -> tuple[dict[str, Any], int, int]:
            del kwargs
            await asyncio.sleep(10)
            return {"answer": "never"}, 1, 1

        async def stream_structured(self, **kwargs: object) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    quota = _SlowReleaseQuota()
    manager = AIExecutionManager(provider=_HangingProvider(), quota=quota, timeout_seconds=5.0)
    task = asyncio.create_task(
        manager.execute(
            user_id=uuid4(),
            operation_type="GOAL_CLARIFICATION",
            system_prompt="sys",
            user_prompt="usr",
            response_schema=_Output,
            model_name="gemini-3.8-flash",
        )
    )
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert release_finished is True
    assert quota.released == ["CANCELLED"]

    # Cleanup failure must NOT mask the original non-retryable provider error.
    class _BrokenCleanupQuota(_Quota):
        async def release_reservation(self, reservation_id: UUID, reason: str = "RELEASED") -> None:
            del reservation_id, reason
            raise OSError("Redis down during release")

    broken_mgr = AIExecutionManager(
        provider=_Provider([PermissionError("403 Forbidden")]),
        quota=_BrokenCleanupQuota(),
        max_retries=2,
    )
    with pytest.raises(PermissionError, match="403 Forbidden"):
        await broken_mgr.execute(
            user_id=uuid4(),
            operation_type="PLAN_CREATION",
            system_prompt="sys",
            user_prompt="usr",
            response_schema=_Output,
            model_name="gemini-3.8-flash",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [
        RuntimeError("400 Bad Request: invalid schema"),
        RuntimeError("401 Unauthorized: invalid api key"),
        RuntimeError("403 Forbidden: permission denied"),
        PermissionError("denied"),
        TypeError("wrong argument type"),
        ValueError("Unsupported domain argument"),
    ],
)
async def test_execution_manager_does_not_retry_non_retryable_errors(exc: Exception) -> None:
    """T0.3 / T1.2: Non-retryable client/programming errors run strictly 1 attempt."""
    quota = _Quota()
    provider = _Provider([exc, {"answer": "unused"}])
    manager = AIExecutionManager(
        provider=provider,
        quota=quota,
        max_retries=2,
        sleep=lambda _delay: asyncio.sleep(0),
    )

    with pytest.raises(type(exc)):
        await manager.execute(
            user_id=uuid4(),
            operation_type="PLAN_CREATION",
            system_prompt="sys",
            user_prompt="usr",
            response_schema=_Output,
            model_name="gemini-3.8-flash",
        )

    assert provider.calls == 1
    assert quota.committed == 0
    assert len(quota.released) == 1


@pytest.mark.asyncio
async def test_execution_manager_tracks_thinking_tokens_and_idempotent_commit_release() -> None:
    """T1.1 / T1.2: Billable output tokens + thinking_tokens tracked; repeated commit/release ignored."""
    from src.shared_kernel.application.llm_port import LLMGenerationResult

    class _RichProvider:
        async def generate_structured(self, **kwargs: object) -> LLMGenerationResult:
            del kwargs
            return LLMGenerationResult(
                payload={"answer": "verified"},
                prompt_tokens=100,
                output_tokens=70,  # e.g., 45 candidates + 25 thoughts
                thinking_tokens=25,
                model_id="gemini-3.8-flash-actual",
            )

        async def stream_structured(self, **kwargs: object) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    quota = _Quota()
    manager = AIExecutionManager(provider=_RichProvider(), quota=quota, max_retries=0)
    res = await manager.execute(
        user_id=uuid4(),
        operation_type="TASK_DECOMPOSITION",
        system_prompt="sys",
        user_prompt="usr",
        response_schema=_Output,
        model_name="gemini-3.8-flash",
    )
    assert res.prompt_tokens == 100
    assert res.output_tokens == 70
    assert res.thinking_tokens == 25
    assert res.model_id == "gemini-3.8-flash-actual"
    assert quota.committed == 1


@pytest.mark.asyncio
async def test_tool_registry_dispatch_validation_timeout_error_truncation_and_redaction() -> None:
    """T3.2: ToolRegistry enforces JSON Schema args, timeout, error envelope, payload limits, and redaction."""
    handler_calls = 0

    async def _search_handler(args: dict[str, Any]) -> ToolResultEnvelope:
        nonlocal handler_calls
        handler_calls += 1
        return ToolResultEnvelope(
            status="OK",
            summary="found",
            data={
                "items": [{"idx": i, "text": "x" * 80} for i in range(50)],
                "query": args["query"],
            },
        )

    async def _slow_handler(args: dict[str, Any]) -> ToolResultEnvelope:
        del args
        await asyncio.sleep(0.1)
        return ToolResultEnvelope(status="OK", summary="late", data={})

    async def _boom_handler(args: dict[str, Any]) -> ToolResultEnvelope:
        del args
        raise RuntimeError("boom token=secret-value")

    registry = ToolRegistry(max_items=5, max_output_bytes=1200)
    registry.register(
        RegisteredTool(
            declaration=LLMToolDeclarationDTO(
                name="search_docs",
                description="Search docs",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "minLength": 2},
                        "limit": {"type": "integer"},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            ),
            allowed_stages=frozenset({"TASK_DECOMPOSITION"}),
            handler=_search_handler,
        )
    )
    registry.register(
        RegisteredTool(
            declaration=LLMToolDeclarationDTO(
                name="slow_tool",
                description="Slow",
                parameters_schema={"type": "object", "properties": {}},
            ),
            allowed_stages=frozenset({"TASK_DECOMPOSITION"}),
            handler=_slow_handler,
            timeout_seconds=0.01,
        )
    )
    registry.register(
        RegisteredTool(
            declaration=LLMToolDeclarationDTO(
                name="boom_tool",
                description="Boom",
                parameters_schema={"type": "object", "properties": {}},
            ),
            allowed_stages=frozenset({"TASK_DECOMPOSITION"}),
            handler=_boom_handler,
        )
    )

    # 1. Invalid args never invoke handler & return error envelope
    bad_env = await registry.dispatch(
        stage="TASK_DECOMPOSITION",
        tool_name="search_docs",
        arguments={"query": "", "extra": 1, "api_key": "sk-secret-123"},
    )
    assert bad_env["status"] == "error"
    assert handler_calls == 0
    assert "sk-secret-123" not in json.dumps(registry.audit_log[-1].sanitized_arguments)

    # 2. Valid args truncate items & bytes safely
    ok_env = await registry.dispatch(
        stage="TASK_DECOMPOSITION",
        tool_name="search_docs",
        arguments={"query": "fastapi", "limit": 10},
    )
    assert ok_env["status"] == "success"
    assert ok_env["data"]["truncated"] is True
    assert registry.audit_log[-1].truncated is True

    # 3. Tool timeout -> error envelope
    timeout_env = await registry.dispatch(
        stage="TASK_DECOMPOSITION",
        tool_name="slow_tool",
        arguments={},
    )
    assert timeout_env["status"] == "error"
    assert timeout_env["data"]["error_code"] == "TOOL_TIMEOUT"

    # 4. Tool exception -> error envelope
    boom_env = await registry.dispatch(
        stage="TASK_DECOMPOSITION",
        tool_name="boom_tool",
        arguments={},
    )
    assert boom_env["status"] == "error"
    assert boom_env["data"]["error_code"] == "TOOL_EXECUTION_ERROR"
