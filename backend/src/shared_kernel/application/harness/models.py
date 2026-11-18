from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class FrozenSchemaList(list[Any]):
    """Immutable list used inside frozen PromptTemplate JSON schemas."""

    def _immutable(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("PromptTemplate.output_schema is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    append = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    clear = _immutable
    sort = _immutable
    reverse = _immutable


class FrozenSchemaDict(dict[str, Any]):
    """Immutable dict used for `PromptTemplate.output_schema` while remaining JSON-serializable."""

    def _immutable(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("PromptTemplate.output_schema is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    pop = _immutable
    popitem = _immutable
    clear = _immutable
    update = _immutable
    setdefault = _immutable


def freeze_schema_value(value: Any) -> Any:
    """Deep-copy and freeze nested dicts/lists for immutable schema storage."""
    if isinstance(value, dict):
        return FrozenSchemaDict({str(k): freeze_schema_value(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return FrozenSchemaList(freeze_schema_value(item) for item in value)
    return copy.deepcopy(value)


class ContextLayer(StrEnum):
    SYSTEM = "SYSTEM"
    WORKFLOW = "WORKFLOW"
    USER = "USER"
    LEARNING = "LEARNING"
    RUNTIME = "RUNTIME"


@dataclass(frozen=True, slots=True)
class HarnessContext:
    system: dict[str, Any] = field(default_factory=dict)
    workflow: dict[str, Any] = field(default_factory=dict)
    user: dict[str, Any] = field(default_factory=dict)
    learning: dict[str, Any] = field(default_factory=dict)
    runtime: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    prompt_id: str
    version: str
    workflow_type: str
    skill_id: str
    system_template: str
    output_schema: dict[str, Any]
    checksum: str
    schema_checksum: str = ""
    thinking_level: str | None = None

    def __post_init__(self) -> None:
        frozen_schema = freeze_schema_value(self.output_schema)
        object.__setattr__(self, "output_schema", frozen_schema)
        if not self.schema_checksum:
            canonical_schema = json.dumps(
                frozen_schema,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            object.__setattr__(
                self,
                "schema_checksum",
                hashlib.sha256(canonical_schema.encode()).hexdigest(),
            )

    @property
    def prompt_ref(self) -> str:
        return f"{self.prompt_id}@{self.version}"


@dataclass(frozen=True, slots=True)
class ToolResultEnvelope:
    status: str
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    next_actions: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "data": self.data,
            "next_actions": list(self.next_actions),
            "artifacts": list(self.artifacts),
        }


class WorkflowType(StrEnum):
    PLAN_CREATION = "PLAN_CREATION"
    SCHEDULE_GENERATION = "SCHEDULE_GENERATION"
    OVERDUE_RECOVERY = "OVERDUE_RECOVERY"
    WEEKLY_REVIEW = "WEEKLY_REVIEW"
    CONTINUOUS_LEARNING = "CONTINUOUS_LEARNING"


class WorkflowStatus(StrEnum):
    RUNNING = "RUNNING"
    PAUSED_WAITING_USER = "PAUSED_WAITING_USER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowStepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_USER = "WAITING_USER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class WorkflowRun:
    id: UUID
    user_id: UUID
    workflow_type: WorkflowType
    current_step: str
    status: WorkflowStatus
    context_snapshot: dict[str, Any]
    started_at: datetime
    goal_id: UUID | None = None
    roadmap_id: UUID | None = None
    error_detail: str | None = None
    paused_at: datetime | None = None
    completed_at: datetime | None = None

    def pause(self, *, now: datetime, waiting_step: str) -> WorkflowRun:
        if self.status is not WorkflowStatus.RUNNING:
            raise ValueError("Only a running workflow can be paused")
        return replace(
            self,
            status=WorkflowStatus.PAUSED_WAITING_USER,
            current_step=waiting_step,
            paused_at=now,
        )

    def resume(self, *, next_step: str, context_snapshot: dict[str, Any]) -> WorkflowRun:
        if self.status is not WorkflowStatus.PAUSED_WAITING_USER:
            raise ValueError("Only a paused workflow can be resumed")
        return replace(
            self,
            status=WorkflowStatus.RUNNING,
            current_step=next_step,
            context_snapshot=dict(context_snapshot),
            paused_at=None,
        )

    def complete(self, *, now: datetime) -> WorkflowRun:
        if self.status is not WorkflowStatus.RUNNING:
            raise ValueError("Only a running workflow can complete")
        return replace(self, status=WorkflowStatus.COMPLETED, completed_at=now)

    def fail(self, *, now: datetime, error_detail: str) -> WorkflowRun:
        if self.status not in (WorkflowStatus.RUNNING, WorkflowStatus.PAUSED_WAITING_USER):
            raise ValueError("Terminal workflow cannot fail again")
        return replace(
            self,
            status=WorkflowStatus.FAILED,
            error_detail=error_detail,
            completed_at=now,
        )


@dataclass(frozen=True, slots=True)
class WorkflowStepExecution:
    id: UUID
    workflow_run_id: UUID
    step_name: str
    step_order: int
    status: WorkflowStepStatus
    input_summary: dict[str, Any]
    output_payload: dict[str, Any]
    retry_count: int
    started_at: datetime
    ai_usage_log_id: UUID | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.step_order < 1:
            raise ValueError("step_order must be >= 1")
        if self.retry_count < 0:
            raise ValueError("retry_count must be >= 0")
