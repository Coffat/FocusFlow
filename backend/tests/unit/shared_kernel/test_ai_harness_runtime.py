import asyncio
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
