import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.planning.domain.exceptions.planning_exceptions import (
    IdempotencyInProgressError,
    PlanningDomainError,
)
from src.shared_kernel.domain.exceptions import DomainError

# Keep the transport alive beyond the Shared AI Harness hard timeout (110s),
# leaving enough time to persist and deliver the terminal failure event.
DEFAULT_SSE_STREAM_TIMEOUT_SECONDS = 210.0

DEFAULT_SSE_TIMEOUT_MESSAGE = (
    "Quá thời gian xử lý AI. Vui lòng thử lại hoặc tiếp tục từ checkpoint."
)
DEFAULT_SSE_FALLBACK_MESSAGE = "Đã xảy ra lỗi trong quá trình xử lý AI. Vui lòng thử lại."


def sanitize_sse_error_details(
    exc: BaseException,
    *,
    default_code: str = "AI_GENERATION_FAILED",
    default_message: str = DEFAULT_SSE_FALLBACK_MESSAGE,
) -> tuple[str, str]:
    """Return stable, sanitized `(error_code, error_message)` for SSE `failed` payloads."""
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return ("AI_GATEWAY_TIMEOUT", DEFAULT_SSE_TIMEOUT_MESSAGE)
    if isinstance(exc, DomainError):
        code = str(getattr(exc, "code", "") or default_code).strip() or default_code
        message = str(getattr(exc, "message", "") or "").strip() or default_message
        return (code, message)
    return (default_code, default_message)


class SseJobNotFoundError(PlanningDomainError):
    """Raised when an SSE job does not exist or does not belong to the requesting user (IDOR 404)."""

    def __init__(self, message: str = "Không tìm thấy tiến trình sinh lộ trình AI.") -> None:
        super().__init__(message=message, code="SSE_JOB_NOT_FOUND")


@dataclass(frozen=True, slots=True)
class IdempotencySlotClaim:
    """Result of an atomic idempotency slot claim (`SET NX EX` or in-memory lock)."""

    acquired: bool
    token: str | None = None
    existing_job: "SseJobRecord | None" = None
    in_progress: bool = False


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

    async def claim_idempotency_slot(
        self,
        *,
        user_id: UUID,
        operation: str,
        idempotency_key: str,
        pending_ttl_seconds: int = 30,
    ) -> IdempotencySlotClaim: ...

    async def finalize_idempotency_slot(
        self,
        *,
        user_id: UUID,
        operation: str,
        idempotency_key: str,
        token: str,
        job_id: UUID,
        ttl_seconds: int = 86400,
    ) -> bool: ...

    async def release_idempotency_slot(
        self,
        *,
        user_id: UUID,
        operation: str,
        idempotency_key: str,
        token: str,
    ) -> bool: ...

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
        register_idempotency: bool = True,
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
        timeout_seconds: float = DEFAULT_SSE_STREAM_TIMEOUT_SECONDS,
    ) -> AsyncIterator[SseEventRecord]: ...


async def claim_idempotency_slot_with_wait(
    sse_store: SseJobPort,
    *,
    user_id: UUID,
    operation: str,
    idempotency_key: str,
    max_wait_seconds: float = 2.0,
    pending_ttl_seconds: int = 30,
) -> tuple[IdempotencySlotClaim, SseJobRecord | None]:
    """Claim an idempotency slot or wait briefly for an in-flight winner to commit."""
    cleaned_key = idempotency_key.strip()
    claim = await sse_store.claim_idempotency_slot(
        user_id=user_id,
        operation=operation,
        idempotency_key=cleaned_key,
        pending_ttl_seconds=pending_ttl_seconds,
    )
    if claim.acquired:
        return (claim, None)
    if claim.existing_job is not None:
        existing = await sse_store.get_job_for_user(
            job_id=claim.existing_job.job_id,
            user_id=user_id,
        )
        return (claim, existing)

    deadline = asyncio.get_running_loop().time() + max(0.05, float(max_wait_seconds))
    delay = 0.02
    while claim.in_progress:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise IdempotencyInProgressError()
        await asyncio.sleep(min(delay, remaining))
        delay = min(0.2, delay * 2.0)
        claim = await sse_store.claim_idempotency_slot(
            user_id=user_id,
            operation=operation,
            idempotency_key=cleaned_key,
            pending_ttl_seconds=pending_ttl_seconds,
        )
        if claim.acquired:
            return (claim, None)
        if claim.existing_job is not None:
            existing = await sse_store.get_job_for_user(
                job_id=claim.existing_job.job_id,
                user_id=user_id,
            )
            return (claim, existing)

    raise IdempotencyInProgressError()
