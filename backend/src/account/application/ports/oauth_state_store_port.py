from typing import Protocol
from uuid import UUID


class OAuthStateStorePort(Protocol):
    """Port for storing and atomically consuming one-time OAuth CSRF state nonces."""

    async def store_nonce(self, nonce: str, user_id: UUID, ttl_seconds: int = 300) -> None: ...

    async def consume_nonce(self, nonce: str) -> UUID | None: ...
