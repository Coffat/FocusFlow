"""Port and adapters for milestone decomposition checkpoints (PR-E Durable Checkpoint & Resume)."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from src.planning.domain.models.milestone import Milestone
from src.shared_kernel.domain.base import generate_uuid7

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MilestoneDecompositionOutcome:
    """Single-milestone LLM decomposition output prior to global namespace reconciliation."""

    milestone: Milestone
    tasks: tuple[dict[str, Any], ...]
    dependencies: tuple[dict[str, Any], ...]
    prompt_tokens: int
    completion_tokens: int
    thinking_tokens: int
    attempts_used: int
    retry_history: tuple[dict[str, Any], ...] = ()
    from_checkpoint: bool = False

    @property
    def output_tokens(self) -> int:
        return self.completion_tokens


def serialize_outcome(outcome: MilestoneDecompositionOutcome) -> dict[str, Any]:
    """Serialize a MilestoneDecompositionOutcome into a JSON-compatible dictionary."""
    return {
        "milestone_id": str(outcome.milestone.id) if outcome.milestone is not None else None,
        "sequence_order": getattr(outcome.milestone, "sequence_order", 1)
        if outcome.milestone is not None
        else 1,
        "milestone_title": getattr(outcome.milestone, "title", "")
        if outcome.milestone is not None
        else "",
        "tasks": list(outcome.tasks),
        "dependencies": list(outcome.dependencies),
        "prompt_tokens": outcome.prompt_tokens,
        "completion_tokens": outcome.completion_tokens,
        "thinking_tokens": outcome.thinking_tokens,
        "attempts_used": outcome.attempts_used,
        "retry_history": list(outcome.retry_history),
        "from_checkpoint": True,
    }


def deserialize_outcome(
    data: dict[str, Any],
    milestone: Milestone | None = None,
) -> MilestoneDecompositionOutcome:
    """Deserialize a dictionary into a MilestoneDecompositionOutcome.

    When loaded from checkpoint, token usage fields are zeroed out for token accounting.
    """
    effective_m = milestone
    if effective_m is None:
        m_id = UUID(str(data["milestone_id"])) if data.get("milestone_id") else generate_uuid7()
        effective_m = Milestone(
            id=m_id,
            sequence_order=int(data.get("sequence_order", 1)),
            title=str(data.get("milestone_title") or f"Milestone #{data.get('sequence_order', 1)}"),
        )
    return MilestoneDecompositionOutcome(
        milestone=effective_m,
        tasks=tuple(data.get("tasks", ())),
        dependencies=tuple(data.get("dependencies", ())),
        prompt_tokens=0,
        completion_tokens=0,
        thinking_tokens=0,
        attempts_used=0,
        retry_history=(),
        from_checkpoint=True,
    )


def outcome_to_json(outcome: MilestoneDecompositionOutcome) -> str:
    """Serialize MilestoneDecompositionOutcome to canonical JSON string."""
    return json.dumps(serialize_outcome(outcome), ensure_ascii=False)


def outcome_from_json(
    json_str: str,
    milestone: Milestone | None = None,
) -> MilestoneDecompositionOutcome:
    """Deserialize JSON string into MilestoneDecompositionOutcome."""
    return deserialize_outcome(json.loads(json_str), milestone=milestone)


class MilestoneCheckpointStorePort(Protocol):
    """Port for persisting and retrieving milestone decomposition checkpoints."""

    async def get_checkpoint(self, key: str) -> dict[str, Any] | None:
        """Retrieve a cached checkpoint payload by its deterministic key, or None if not found."""
        ...

    async def set_checkpoint(
        self,
        key: str,
        payload: dict[str, Any] | MilestoneDecompositionOutcome,
    ) -> None:
        """Persist a checkpoint payload under the given deterministic key."""
        ...


class InMemoryMilestoneCheckpointStore:
    """Thread-safe / async-safe in-memory checkpoint store for tests and runtime caching."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def get_checkpoint(self, key: str) -> dict[str, Any] | None:
        payload = self._store.get(key)
        if payload is None:
            return None
        return dict(payload)

    async def set_checkpoint(
        self,
        key: str,
        payload: dict[str, Any] | MilestoneDecompositionOutcome,
    ) -> None:
        if isinstance(payload, MilestoneDecompositionOutcome):
            self._store[key] = serialize_outcome(payload)
        else:
            self._store[key] = dict(payload)

    async def get_outcome(
        self,
        key: str,
        milestone: Milestone | None = None,
    ) -> MilestoneDecompositionOutcome | None:
        data = await self.get_checkpoint(key)
        if data is None:
            return None
        return deserialize_outcome(data, milestone=milestone)

    async def set_outcome(
        self,
        key: str,
        outcome: MilestoneDecompositionOutcome,
    ) -> None:
        await self.set_checkpoint(key, outcome)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __bool__(self) -> bool:
        return True

    def __contains__(self, key: str) -> bool:
        return key in self._store


class RedisMilestoneCheckpointStore:
    """Redis-backed durable checkpoint store with automatic in-memory fallback.

    Persists milestone decomposition outcomes under deterministic SHA-256 keys.
    Key prefix: ff:checkpoint:milestone:{key}
    Default TTL: 86400s (24h).
    """

    serialize_outcome = staticmethod(serialize_outcome)
    deserialize_outcome = staticmethod(deserialize_outcome)
    outcome_to_json = staticmethod(outcome_to_json)
    outcome_from_json = staticmethod(outcome_from_json)

    def __init__(
        self,
        redis_url: str | None = None,
        *,
        redis_client: Any | None = None,
        key_prefix: str = "ff:checkpoint:milestone:",
        ttl_seconds: int = 86400,
    ) -> None:
        self._redis_url = redis_url
        self._client: Any | None = redis_client
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds
        self._memory_fallback = InMemoryMilestoneCheckpointStore()
        self._redis_failed = False
        self._lock = asyncio.Lock()

    async def _get_client(self) -> Any | None:
        if self._redis_failed:
            return None
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is not None:
                return self._client
            if self._redis_failed:
                return None
            try:
                import redis.asyncio as aioredis

                from src.shared_kernel.config import get_settings

                url = self._redis_url or get_settings().redis_url
                client = aioredis.from_url(url, decode_responses=True)
                await client.ping()
                self._client = client
                return self._client
            except Exception as exc:
                logger.warning(
                    "redis_checkpoint_store_connect_error: %s. Falling back to in-memory store.",
                    exc,
                )
                self._redis_failed = True
                return None

    async def get_checkpoint(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached checkpoint payload by key, falling back to memory on Redis error."""
        client = await self._get_client()
        if client is not None:
            try:
                full_key = f"{self._key_prefix}{key}"
                raw = await client.get(full_key)
                if raw is not None:
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    return json.loads(raw)  # type: ignore[no-any-return]
                return None
            except Exception as exc:
                logger.warning(
                    "redis_checkpoint_get_error: %s. Falling back to in-memory store.",
                    exc,
                )
        return await self._memory_fallback.get_checkpoint(key)

    async def set_checkpoint(
        self,
        key: str,
        payload: dict[str, Any] | MilestoneDecompositionOutcome,
    ) -> None:
        """Persist checkpoint payload under key with TTL, falling back to memory on Redis error."""
        if isinstance(payload, MilestoneDecompositionOutcome):
            serialized = serialize_outcome(payload)
        elif isinstance(payload, dict):
            serialized = dict(payload)
        else:
            raise TypeError(f"Unsupported payload type for set_checkpoint: {type(payload)}")

        json_str = json.dumps(serialized, ensure_ascii=False)
        client = await self._get_client()
        if client is not None:
            try:
                full_key = f"{self._key_prefix}{key}"
                await client.set(full_key, json_str, ex=self._ttl_seconds)
                # Mirror in memory fallback so fallback has consistent state
                await self._memory_fallback.set_checkpoint(key, serialized)
                return
            except Exception as exc:
                logger.warning(
                    "redis_checkpoint_set_error: %s. Falling back to in-memory store.",
                    exc,
                )
        await self._memory_fallback.set_checkpoint(key, serialized)

    async def get_outcome(
        self,
        key: str,
        milestone: Milestone | None = None,
    ) -> MilestoneDecompositionOutcome | None:
        """Retrieve and deserialize outcome from checkpoint, or None if not found."""
        data = await self.get_checkpoint(key)
        if data is None:
            return None
        return deserialize_outcome(data, milestone=milestone)

    async def set_outcome(
        self,
        key: str,
        outcome: MilestoneDecompositionOutcome,
    ) -> None:
        """Persist MilestoneDecompositionOutcome directly to checkpoint."""
        await self.set_checkpoint(key, outcome)

    async def clear(self) -> None:
        """Clear all milestone checkpoints in Redis matching key_prefix and memory fallback."""
        client = await self._get_client()
        if client is not None:
            try:
                keys = await client.keys(f"{self._key_prefix}*")
                if keys:
                    await client.delete(*keys)
            except Exception:
                pass
        self._memory_fallback.clear()

    async def close(self) -> None:
        """Close the underlying Redis client connection if opened."""
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None
