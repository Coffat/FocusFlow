from uuid import UUID

from src.account.infrastructure.caching.redis_client import get_redis_client


class RedisOAuthStateStore:
    """Redis-backed one-time nonce store for OAuth state CSRF & replay protection."""

    _KEY_PREFIX = "oauth_state"

    @classmethod
    def _key(cls, nonce: str) -> str:
        return f"{cls._KEY_PREFIX}:{nonce}"

    async def store_nonce(self, nonce: str, user_id: UUID, ttl_seconds: int = 300) -> None:
        client = get_redis_client()
        await client.set(self._key(nonce), str(user_id), ex=ttl_seconds)

    async def consume_nonce(self, nonce: str) -> UUID | None:
        client = get_redis_client()
        raw = await client.getdel(self._key(nonce))
        if not raw:
            return None
        try:
            return UUID(str(raw))
        except ValueError:
            return None
