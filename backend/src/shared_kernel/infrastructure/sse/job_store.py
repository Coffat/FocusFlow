import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis

from src.planning.application.ports.sse_job_port import (
    SseEventRecord,
    SseJobNotFoundError,
    SseJobPort,
    SseJobRecord,
)
from src.shared_kernel.config import get_settings


class InMemorySseJobStore(SseJobPort):
    """In-memory 2-Stage SSE Job Store supporting 24h Idempotency-Key & Last-Event-ID replay (ADR-005)."""

    def __init__(self) -> None:
        self._jobs: dict[UUID, SseJobRecord] = {}
        self._idempotency_map: dict[tuple[UUID, str, str], tuple[UUID, datetime]] = {}
        self._condition_map: dict[UUID, asyncio.Condition] = {}

    def clear(self) -> None:
        self._jobs.clear()
        self._idempotency_map.clear()
        self._condition_map.clear()

    def _get_condition(self, job_id: UUID) -> asyncio.Condition:
        cond = self._condition_map.get(job_id)
        if cond is None:
            cond = asyncio.Condition()
            self._condition_map[job_id] = cond
        return cond

    async def get_by_idempotency_key(
        self,
        *,
        user_id: UUID,
        operation: str,
        idempotency_key: str,
    ) -> SseJobRecord | None:
        cleaned_key = (idempotency_key or "").strip()
        if not cleaned_key:
            return None

        composite = (user_id, operation.strip().upper(), cleaned_key)
        entry = self._idempotency_map.get(composite)
        if entry is None:
            return None

        job_id, expires_at = entry
        now = datetime.now(UTC)
        if now >= expires_at:
            self._idempotency_map.pop(composite, None)
            return None

        job = self._jobs.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        return job

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
    ) -> SseJobRecord:
        now = datetime.now(UTC)
        record = SseJobRecord(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap_id,
            reservation_id=reservation_id,
            job_type=job_type,
            status="RESERVED",
            created_at=now,
            updated_at=now,
            events=[],
        )
        self._jobs[job_id] = record
        if idempotency_key and idempotency_key.strip():
            composite = (user_id, operation.strip().upper(), idempotency_key.strip())
            self._idempotency_map[composite] = (
                job_id,
                now + timedelta(seconds=max(1, ttl_seconds)),
            )
        return record

    async def get_job_for_user(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
    ) -> SseJobRecord:
        job = self._jobs.get(job_id)
        if job is None or job.user_id != user_id:
            raise SseJobNotFoundError()
        return job

    async def append_event(
        self,
        *,
        job_id: UUID,
        event: str,
        data: dict[str, Any],
        status: str | None = None,
    ) -> SseEventRecord:
        job = self._jobs.get(job_id)
        if job is None:
            raise SseJobNotFoundError()

        next_id = len(job.events) + 1
        enriched_data = dict(data)
        enriched_data.setdefault("id", next_id)
        enriched_data.setdefault("event", event)

        event_record = SseEventRecord(
            id=next_id,
            event=event,
            data=enriched_data,
        )
        job.events.append(event_record)
        if status is not None:
            job.status = status
        elif event == "completed":
            job.status = "COMPLETED"
        elif event == "failed":
            job.status = "FAILED"
        elif job.status == "RESERVED":
            job.status = "STREAMING"
        job.updated_at = datetime.now(UTC)

        cond = self._get_condition(job_id)
        async with cond:
            cond.notify_all()

        return event_record

    async def stream_events(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        last_event_id: int | None = None,
        timeout_seconds: float = 55.0,
    ) -> AsyncIterator[SseEventRecord]:
        job = await self.get_job_for_user(job_id=job_id, user_id=user_id)
        cursor = int(last_event_id) if last_event_id is not None else 0
        cond = self._get_condition(job_id)
        deadline = asyncio.get_running_loop().time() + timeout_seconds

        while True:
            pending = [ev for ev in job.events if ev.id > cursor]
            for ev in pending:
                cursor = ev.id
                yield ev
                if ev.event in ("completed", "failed") or ev.data.get("stage") in (
                    "COMPLETED",
                    "FAILED",
                ):
                    return

            if job.status in ("COMPLETED", "FAILED") and all(ev.id <= cursor for ev in job.events):
                return

            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return

            try:
                async with cond:
                    await asyncio.wait_for(cond.wait(), timeout=min(remaining, 1.0))
            except TimeoutError:
                if job.status in ("COMPLETED", "FAILED"):
                    continue


class RedisSseJobStore(SseJobPort):
    """Redis-backed 2-Stage SSE Job Store with automatic fallback to InMemorySseJobStore."""

    def __init__(
        self,
        redis_url: str | None = None,
        fallback_store: InMemorySseJobStore | None = None,
    ) -> None:
        settings = get_settings()
        self._redis_url = redis_url or settings.redis_url
        self._fallback = fallback_store or default_in_memory_sse_job_store
        self._client: aioredis.Redis | None = None

    def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    @staticmethod
    def _job_meta_key(job_id: UUID) -> str:
        return f"sse:job:{job_id}:meta"

    @staticmethod
    def _job_events_key(job_id: UUID) -> str:
        return f"sse:job:{job_id}:events"

    @staticmethod
    def _idem_key(user_id: UUID, operation: str, idempotency_key: str) -> str:
        return f"sse:idem:{user_id}:{operation.strip().upper()}:{idempotency_key.strip()}"

    async def get_by_idempotency_key(
        self,
        *,
        user_id: UUID,
        operation: str,
        idempotency_key: str,
    ) -> SseJobRecord | None:
        mem_hit = await self._fallback.get_by_idempotency_key(
            user_id=user_id,
            operation=operation,
            idempotency_key=idempotency_key,
        )
        if mem_hit is not None:
            return mem_hit

        cleaned_key = (idempotency_key or "").strip()
        if not cleaned_key:
            return None

        try:
            client = self._get_client()
            job_id_str = await client.get(self._idem_key(user_id, operation, cleaned_key))
            if not job_id_str:
                return None
            return await self.get_job_for_user(job_id=UUID(str(job_id_str)), user_id=user_id)
        except SseJobNotFoundError:
            return None
        except Exception:
            return None

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
    ) -> SseJobRecord:
        record = await self._fallback.create_job(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap_id,
            reservation_id=reservation_id,
            job_type=job_type,
            operation=operation,
            idempotency_key=idempotency_key,
            ttl_seconds=ttl_seconds,
        )
        try:
            client = self._get_client()
            meta = {
                "job_id": str(record.job_id),
                "user_id": str(record.user_id),
                "roadmap_id": str(record.roadmap_id),
                "reservation_id": str(record.reservation_id),
                "job_type": record.job_type,
                "status": record.status,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
            }
            await client.set(
                self._job_meta_key(job_id),
                json.dumps(meta),
                ex=max(1, ttl_seconds),
            )
            if idempotency_key and idempotency_key.strip():
                await client.set(
                    self._idem_key(user_id, operation, idempotency_key),
                    str(job_id),
                    ex=max(1, ttl_seconds),
                )
        except Exception:
            pass
        return record

    async def get_job_for_user(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
    ) -> SseJobRecord:
        try:
            return await self._fallback.get_job_for_user(job_id=job_id, user_id=user_id)
        except SseJobNotFoundError:
            pass

        try:
            client = self._get_client()
            raw_meta = await client.get(self._job_meta_key(job_id))
            if not raw_meta:
                raise SseJobNotFoundError()
            meta = json.loads(raw_meta)
            if UUID(meta["user_id"]) != user_id:
                raise SseJobNotFoundError()
            raw_events = await client.lrange(self._job_events_key(job_id), 0, -1)
            events = [
                SseEventRecord(
                    id=int(ev_dict["id"]),
                    event=str(ev_dict["event"]),
                    data=dict(ev_dict["data"]),
                )
                for ev_dict in (json.loads(item) for item in raw_events)
            ]
            return SseJobRecord(
                job_id=UUID(meta["job_id"]),
                user_id=UUID(meta["user_id"]),
                roadmap_id=UUID(meta["roadmap_id"]),
                reservation_id=UUID(meta["reservation_id"]),
                job_type=str(meta["job_type"]),
                status=str(meta["status"]),
                created_at=datetime.fromisoformat(meta["created_at"]),
                updated_at=datetime.fromisoformat(meta["updated_at"]),
                events=events,
            )
        except SseJobNotFoundError:
            raise
        except Exception as exc:
            raise SseJobNotFoundError() from exc

    async def append_event(
        self,
        *,
        job_id: UUID,
        event: str,
        data: dict[str, Any],
        status: str | None = None,
    ) -> SseEventRecord:
        ev = await self._fallback.append_event(
            job_id=job_id,
            event=event,
            data=data,
            status=status,
        )
        try:
            client = self._get_client()
            serialized = json.dumps({"id": ev.id, "event": ev.event, "data": ev.data})
            await client.rpush(self._job_events_key(job_id), serialized)
            await client.expire(self._job_events_key(job_id), 86400)
        except Exception:
            pass
        return ev

    async def stream_events(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        last_event_id: int | None = None,
        timeout_seconds: float = 55.0,
    ) -> AsyncIterator[SseEventRecord]:
        async for ev in self._fallback.stream_events(
            job_id=job_id,
            user_id=user_id,
            last_event_id=last_event_id,
            timeout_seconds=timeout_seconds,
        ):
            yield ev


default_in_memory_sse_job_store = InMemorySseJobStore()
