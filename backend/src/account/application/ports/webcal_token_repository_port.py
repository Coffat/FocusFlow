from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WebcalTokenRecord:
    """Persistence-agnostic representation of a learner's WebCal token record."""

    id: UUID
    user_id: UUID
    token_hash: str
    is_active: bool
    rotated_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WebcalTokenRepositoryPort(Protocol):
    """Repository port for managing SHA-256 hashed WebCal tokens (`webcal_tokens`)."""

    async def get_by_user_id(self, user_id: UUID) -> WebcalTokenRecord | None: ...

    async def get_active_by_token_hash(self, token_hash: str) -> WebcalTokenRecord | None: ...

    async def upsert_token(
        self, user_id: UUID, token_hash: str, now: datetime
    ) -> WebcalTokenRecord: ...

    async def revoke_for_user(self, user_id: UUID, now: datetime) -> bool: ...

    async def touch_last_used(self, token_id: UUID, now: datetime) -> None: ...
