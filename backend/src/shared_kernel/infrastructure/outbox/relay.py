from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.infrastructure.outbox.repository import SqlAlchemyOutboxRepository
from src.shared_kernel.infrastructure.worker.broker import broker

logger = logging.getLogger("focusflow.shared_kernel.outbox.relay")

OutboxEventHandler = Callable[[UUID, dict[str, Any]], Awaitable[None]]

OUTBOX_META_KEY = "_outbox_meta"
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_BACKOFF_SECONDS = 5.0
DEFAULT_MAX_BACKOFF_SECONDS = 300.0
MAX_ERROR_LENGTH = 500

_CREDENTIAL_URL_RE = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://)([^/\s:@]+):([^/\s@]+)@")
_CONTROL_CHARS_RE = re.compile(r"[\r\n\t]+")

_OUTBOX_HANDLERS: dict[str, list[tuple[str, OutboxEventHandler]]] = {}


@dataclass
class _RelayCounters:
    published_count: int = 0
    retry_attempts: int = 0
    unknown_handler_events: int = 0
    dispatch_failures: int = 0


_RELAY_COUNTERS = _RelayCounters()


@dataclass(frozen=True, slots=True)
class OutboxMetricsSnapshot:
    """Observability snapshot combining PostgreSQL outbox queue state and relay counters."""

    pending_count: int
    failed_count: int
    oldest_pending_age_seconds: float | None
    retry_attempts: int
    unknown_handler_events: int
    dispatch_failures: int
    published_count: int


def register_outbox_handler(
    event_type: str,
    handler_name: str,
    handler: OutboxEventHandler,
) -> None:
    """Register an idempotent outbox handler for an event type without cross-context imports."""
    handlers = _OUTBOX_HANDLERS.setdefault(event_type, [])
    for idx, (existing_name, _) in enumerate(handlers):
        if existing_name == handler_name:
            handlers[idx] = (handler_name, handler)
            return
    handlers.append((handler_name, handler))


def get_registered_outbox_handlers() -> dict[str, list[tuple[str, OutboxEventHandler]]]:
    """Return a shallow snapshot of registered outbox handlers."""
    return {event_type: list(handlers) for event_type, handlers in _OUTBOX_HANDLERS.items()}


def clear_outbox_handlers() -> None:
    """Clear all registered outbox handlers (for test isolation)."""
    _OUTBOX_HANDLERS.clear()


def reset_outbox_relay_metrics() -> None:
    """Reset in-process cumulative relay counters (for test isolation)."""
    _RELAY_COUNTERS.published_count = 0
    _RELAY_COUNTERS.retry_attempts = 0
    _RELAY_COUNTERS.unknown_handler_events = 0
    _RELAY_COUNTERS.dispatch_failures = 0


def compute_retry_backoff_seconds(
    retry_count: int,
    *,
    base_backoff_seconds: float = DEFAULT_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: float = DEFAULT_MAX_BACKOFF_SECONDS,
) -> float:
    """Compute bounded exponential backoff delay in seconds for a retry attempt."""
    if base_backoff_seconds <= 0.0 or retry_count <= 0:
        return 0.0
    delay: float = base_backoff_seconds * (2.0 ** (retry_count - 1))
    return min(delay, max(base_backoff_seconds, max_backoff_seconds))


def _normalize_utc(dt: datetime | None) -> datetime:
    current = dt or datetime.now(UTC)
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def _sanitize_error(error: BaseException | str) -> str:
    raw = f"{type(error).__name__}: {error}" if isinstance(error, BaseException) else str(error)
    redacted = _CREDENTIAL_URL_RE.sub(r"\1***:***@", raw)
    normalized = _CONTROL_CHARS_RE.sub(" ", redacted).strip()
    if len(normalized) > MAX_ERROR_LENGTH:
        return f"{normalized[: MAX_ERROR_LENGTH - 3]}..."
    return normalized


def _extract_clean_payload(raw_payload: Any) -> dict[str, Any]:
    if not isinstance(raw_payload, dict):
        return {}
    return {k: v for k, v in raw_payload.items() if k != OUTBOX_META_KEY}


def _parse_next_retry_at(raw_payload: Any) -> datetime | None:
    if not isinstance(raw_payload, dict):
        return None
    meta = raw_payload.get(OUTBOX_META_KEY)
    if not isinstance(meta, dict):
        return None
    raw_ts = meta.get("next_retry_at")
    if not isinstance(raw_ts, str) or not raw_ts:
        return None
    try:
        parsed = datetime.fromisoformat(raw_ts)
    except ValueError:
        return None
    return _normalize_utc(parsed)


def _is_retry_ready(event: OutboxEventORM, now: datetime) -> bool:
    next_retry_at = _parse_next_retry_at(event.payload)
    if next_retry_at is None:
        return True
    return next_retry_at <= now


def _build_payload_with_meta(
    clean_payload: dict[str, Any],
    *,
    failure_code: str,
    last_error: str,
    failed_at: datetime,
    next_retry_at: datetime | None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "failure_code": failure_code,
        "last_error": _sanitize_error(last_error),
        "last_failed_at": failed_at.isoformat(),
    }
    if next_retry_at is not None:
        meta["next_retry_at"] = next_retry_at.isoformat()
    return {**clean_payload, OUTBOX_META_KEY: meta}


def _apply_failure_transition(
    event: OutboxEventORM,
    *,
    max_retries: int,
    error: BaseException,
    base_backoff_seconds: float,
    max_backoff_seconds: float,
    now: datetime,
) -> tuple[str, int, datetime | None]:
    clean_payload = _extract_clean_payload(event.payload)
    new_retry_count = int(event.retry_count or 0) + 1
    exhausted = new_retry_count >= max_retries
    new_status = "FAILED" if exhausted else "PENDING"
    failure_code = "MAX_RETRIES_EXCEEDED" if exhausted else "DISPATCH_FAILED"

    next_retry_at: datetime | None = None
    if not exhausted:
        backoff_secs = compute_retry_backoff_seconds(
            new_retry_count,
            base_backoff_seconds=base_backoff_seconds,
            max_backoff_seconds=max_backoff_seconds,
        )
        if backoff_secs > 0.0:
            next_retry_at = now + timedelta(seconds=backoff_secs)

    event.published_at = None
    event.retry_count = new_retry_count
    event.status = new_status
    event.payload = _build_payload_with_meta(
        clean_payload,
        failure_code=failure_code,
        last_error=_sanitize_error(error),
        failed_at=now,
        next_retry_at=next_retry_at,
    )
    return new_status, new_retry_count, next_retry_at


async def _record_failure_in_fresh_session(
    session_maker: Any,
    *,
    event_id: UUID,
    max_retries: int,
    error: BaseException,
    base_backoff_seconds: float,
    max_backoff_seconds: float,
    now: datetime,
) -> tuple[str, int, datetime | None] | None:
    """Persist retry/failure state in a fresh clean transaction after a rollback/aborted TX."""
    async with session_maker() as recovery_session:
        try:
            stmt = (
                select(OutboxEventORM)
                .where(OutboxEventORM.id == event_id)
                .with_for_update(key_share=True)
            )
            event = (await recovery_session.execute(stmt)).scalar_one_or_none()
            if event is None or event.status != "PENDING":
                await recovery_session.rollback()
                return None

            new_status, new_retry_count, next_retry_at = _apply_failure_transition(
                event,
                max_retries=max_retries,
                error=error,
                base_backoff_seconds=base_backoff_seconds,
                max_backoff_seconds=max_backoff_seconds,
                now=now,
            )
            await recovery_session.commit()
            return new_status, new_retry_count, next_retry_at
        except Exception as recovery_exc:
            await recovery_session.rollback()
            logger.error(
                "Outbox failure recovery transaction failed: event_id=%s error=%s",
                event_id,
                _sanitize_error(recovery_exc),
            )
            return None


async def collect_outbox_metrics(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> OutboxMetricsSnapshot:
    """Collect queue depth, oldest pending age, and relay execution counters."""
    current_time = _normalize_utc(now)

    pending_stmt = select(func.count(OutboxEventORM.id)).where(OutboxEventORM.status == "PENDING")
    failed_stmt = select(func.count(OutboxEventORM.id)).where(OutboxEventORM.status == "FAILED")
    oldest_stmt = select(func.min(OutboxEventORM.created_at)).where(
        OutboxEventORM.status == "PENDING"
    )

    pending_count = int((await session.execute(pending_stmt)).scalar_one() or 0)
    failed_count = int((await session.execute(failed_stmt)).scalar_one() or 0)
    oldest_created_at: datetime | None = (await session.execute(oldest_stmt)).scalar_one_or_none()

    oldest_pending_age_seconds: float | None = None
    if oldest_created_at is not None:
        oldest_utc = _normalize_utc(oldest_created_at)
        oldest_pending_age_seconds = max(0.0, (current_time - oldest_utc).total_seconds())

    return OutboxMetricsSnapshot(
        pending_count=pending_count,
        failed_count=failed_count,
        oldest_pending_age_seconds=oldest_pending_age_seconds,
        retry_attempts=_RELAY_COUNTERS.retry_attempts,
        unknown_handler_events=_RELAY_COUNTERS.unknown_handler_events,
        dispatch_failures=_RELAY_COUNTERS.dispatch_failures,
        published_count=_RELAY_COUNTERS.published_count,
    )


@broker.task(schedule=[{"cron": "* * * * *"}])
async def relay_pending_outbox_events(
    batch_size: int = 100,
    max_retries: int = DEFAULT_MAX_RETRIES,
    session_factory: Any = None,
    *,
    base_backoff_seconds: float = DEFAULT_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: float = DEFAULT_MAX_BACKOFF_SECONDS,
    now: datetime | None = None,
) -> int:
    """Poll PENDING outbox_events with FOR UPDATE SKIP LOCKED and commit per event.

    Each event is locked, dispatched, and committed in its own transaction so a DB
    commit failure on event N cannot roll back events 1..N-1 already published to
    the broker.

    Reliability guarantees:
    - **No silent drops**: events with no registered handler are NEVER marked ``PUBLISHED``;
      they are quarantined as ``FAILED`` with ``NO_HANDLER_REGISTERED`` metadata and logged.
    - **Bounded retries with exponential backoff**: transient failures increment ``retry_count``,
      record ``next_retry_at`` inside ``payload._outbox_meta``, and transition deterministically
      to terminal ``FAILED`` once ``retry_count >= max_retries``.
    - **Aborted-transaction resilience**: any ``SQLAlchemyError`` or commit failure triggers
      ``session.rollback()`` and persists the retry/failure state in a fresh clean session.
    - **Delivery guarantee (at-least-once)**: if an external broker publish succeeds inside a
      handler but the subsequent DB commit fails before ``status='PUBLISHED'`` is persisted,
      the event remains ``PENDING`` and will be redelivered; downstream consumers MUST
      therefore enforce consumer-side idempotency via ``processed_events``.
    """
    session_maker = session_factory or async_session_factory
    current_time = _normalize_utc(now)

    published_count = 0
    run_retry_attempts = 0
    run_unknown_handlers = 0
    run_dispatch_failures = 0
    run_backoff_skipped = 0
    processed_in_batch = 0

    attempted_ids: set[UUID] = set()
    max_scans = max(batch_size * 5, batch_size)

    for _ in range(max_scans):
        if processed_in_batch >= batch_size:
            break

        async with session_maker() as session:
            stmt = (
                select(OutboxEventORM)
                .where(OutboxEventORM.status == "PENDING")
                .order_by(OutboxEventORM.created_at.asc())
                .limit(1)
                # Use FOR NO KEY UPDATE SKIP LOCKED so concurrent relays skip locked rows
                # without blocking FOR KEY SHARE locks acquired by downstream consumers
                # inserting into processed_events (which references outbox_events.id).
                .with_for_update(skip_locked=True, key_share=True)
            )
            if attempted_ids:
                stmt = stmt.where(OutboxEventORM.id.not_in(attempted_ids))

            result = await session.execute(stmt)
            event = result.scalar_one_or_none()
            if event is None:
                break

            event_id = event.id
            event_type = event.event_type
            attempted_ids.add(event_id)

            if not _is_retry_ready(event, current_time):
                run_backoff_skipped += 1
                await session.rollback()
                continue

            processed_in_batch += 1
            clean_payload = _extract_clean_payload(event.payload)
            handlers = list(_OUTBOX_HANDLERS.get(event_type, []))

            if not handlers:
                error_msg = (
                    f"NO_HANDLER_REGISTERED: No outbox handler registered "
                    f"for event_type={event_type}"
                )
                event.status = "FAILED"
                event.published_at = None
                event.payload = _build_payload_with_meta(
                    clean_payload,
                    failure_code="NO_HANDLER_REGISTERED",
                    last_error=error_msg,
                    failed_at=current_time,
                    next_retry_at=None,
                )
                try:
                    await session.commit()
                    run_unknown_handlers += 1
                    _RELAY_COUNTERS.unknown_handler_events += 1
                    logger.warning(
                        "Outbox event quarantined (NO_HANDLER_REGISTERED): "
                        "event_id=%s event_type=%s status=FAILED",
                        event_id,
                        event_type,
                    )
                except Exception as commit_exc:
                    await session.rollback()
                    logger.error(
                        "Failed to quarantine unknown outbox event: event_id=%s error=%s",
                        event_id,
                        _sanitize_error(commit_exc),
                    )
                continue

            outbox_repo = SqlAlchemyOutboxRepository(session)
            dispatched_ok = False
            dispatch_exc: Exception | None = None

            try:
                for handler_name, handler in handlers:
                    if await outbox_repo.is_event_processed(event_id, handler_name):
                        continue
                    async with session.begin_nested():
                        await handler(event_id, dict(clean_payload))
                        await outbox_repo.mark_event_processed(event_id, handler_name)

                event.status = "PUBLISHED"
                event.published_at = current_time
                if isinstance(event.payload, dict) and OUTBOX_META_KEY in event.payload:
                    event.payload = clean_payload
                dispatched_ok = True
            except Exception as exc:
                dispatch_exc = exc

            if dispatched_ok:
                try:
                    await session.commit()
                    published_count += 1
                    _RELAY_COUNTERS.published_count += 1
                except Exception as commit_exc:
                    await session.rollback()
                    run_dispatch_failures += 1
                    _RELAY_COUNTERS.dispatch_failures += 1
                    recovered = await _record_failure_in_fresh_session(
                        session_maker,
                        event_id=event_id,
                        max_retries=max_retries,
                        error=commit_exc,
                        base_backoff_seconds=base_backoff_seconds,
                        max_backoff_seconds=max_backoff_seconds,
                        now=current_time,
                    )
                    if recovered is not None and recovered[0] == "PENDING":
                        run_retry_attempts += 1
                        _RELAY_COUNTERS.retry_attempts += 1
                    logger.error(
                        "Outbox event commit failed (at-least-once redelivery will occur): "
                        "event_id=%s event_type=%s error=%s",
                        event_id,
                        event_type,
                        _sanitize_error(commit_exc),
                    )
                continue

            assert dispatch_exc is not None
            run_dispatch_failures += 1
            _RELAY_COUNTERS.dispatch_failures += 1

            # If a SQLAlchemy/DB error occurred or the session is no longer active,
            # always roll back and persist retry/failure state in a fresh clean session.
            needs_fresh_session = isinstance(dispatch_exc, SQLAlchemyError) or (
                not session.is_active
            )

            recorded_status: str | None = None
            recorded_retry: int | None = None
            recorded_next_retry: datetime | None = None

            if not needs_fresh_session:
                new_status, new_retry_count, next_retry_at = _apply_failure_transition(
                    event,
                    max_retries=max_retries,
                    error=dispatch_exc,
                    base_backoff_seconds=base_backoff_seconds,
                    max_backoff_seconds=max_backoff_seconds,
                    now=current_time,
                )
                try:
                    await session.commit()
                    recorded_status = new_status
                    recorded_retry = new_retry_count
                    recorded_next_retry = next_retry_at
                except Exception:
                    await session.rollback()
                    needs_fresh_session = True
            else:
                await session.rollback()

            if needs_fresh_session:
                recovered = await _record_failure_in_fresh_session(
                    session_maker,
                    event_id=event_id,
                    max_retries=max_retries,
                    error=dispatch_exc,
                    base_backoff_seconds=base_backoff_seconds,
                    max_backoff_seconds=max_backoff_seconds,
                    now=current_time,
                )
                if recovered is not None:
                    recorded_status, recorded_retry, recorded_next_retry = recovered

            if recorded_status == "PENDING":
                run_retry_attempts += 1
                _RELAY_COUNTERS.retry_attempts += 1

            logger.error(
                "Outbox event dispatch failed: event_id=%s event_type=%s retry_count=%s "
                "status=%s next_retry_at=%s error=%s",
                event_id,
                event_type,
                recorded_retry,
                recorded_status,
                recorded_next_retry.isoformat() if recorded_next_retry else None,
                _sanitize_error(dispatch_exc),
            )

    if (
        published_count > 0
        or run_dispatch_failures > 0
        or run_unknown_handlers > 0
        or run_backoff_skipped > 0
    ):
        logger.info(
            "Outbox relay summary: published=%d dispatch_failures=%d retry_attempts=%d "
            "unknown_handler_events=%d backoff_skipped=%d",
            published_count,
            run_dispatch_failures,
            run_retry_attempts,
            run_unknown_handlers,
            run_backoff_skipped,
        )

    return published_count
