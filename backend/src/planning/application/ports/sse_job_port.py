from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.planning.domain.exceptions.planning_exceptions import PlanningDomainError


class SseJobNotFoundError(PlanningDomainError):
    """Raised when an SSE job does not exist or does not belong to the requesting user (IDOR 404)."""

    def __init__(self, message: str = "Không tìm thấy tiến trình sinh lộ trình AI.") -> None:
        super().__init__(message=message, code="SSE_JOB_NOT_FOUND")


@dataclass(frozen=True, slots=True)
class SseEventRecord:
    """Single Server-Sent Event item with monotonic integer ID for Last-Event-ID replay (ADR-005)."""

    id: int
    event: str  # "stage" | "chunk" | "validation_retry" | "completed" | "failed"
    data: dict[str, Any] = field(default_factory=dict)

    def format_sse(self) -> str:
        """Render standard SSE wire format (`id:`, `event:`, `data:`)."""
        import json

        payload_str = json.dumps(self.data, ensure_ascii=False)
        return f"id: {self.id}\nevent: {self.event}\ndata: {payload_str}\n\n"


@dataclass(slots=True)
class SseJobRecord:
    """Metadata and event history of a 2-Stage SSE AI generation job."""

    job_id: UUID
    user_id: UUID
    roadmap_id: UUID
    reservation_id: UUID
    job_type: str  # "MILESTONE_GEN" | "SCHEDULE_PROPOSAL_GEN"
    status: str  # "RESERVED" | "STREAMING" | "COMPLETED" | "FAILED"
    created_at: datetime
    updated_at: datetime
    events: list[SseEventRecord] = field(default_factory=list)


class SseJobPort(Protocol):
    """Application port for 2-Stage SSE Job Store & Event Streamer (ADR-005)."""

    async def get_by_idempotency_key(
        self,
        *,
        user_id: UUID,
        operation: str,
        idempotency_key: str,
    ) -> SseJobRecord | None: ...

    async def create_job(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        roadmap_id: UUID,
        reservation_id: UUID,
        job_type: str,
        operation: str,
        idempotency_key: str | None = None,
        ttl_seconds: int = 86400,
    ) -> SseJobRecord: ...

    async def get_job_for_user(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
    ) -> SseJobRecord: ...

    async def append_event(
        self,
        *,
        job_id: UUID,
        event: str,
        data: dict[str, Any],
        status: str | None = None,
    ) -> SseEventRecord: ...

    def stream_events(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        last_event_id: int | None = None,
        timeout_seconds: float = 55.0,
    ) -> AsyncIterator[SseEventRecord]: ...
