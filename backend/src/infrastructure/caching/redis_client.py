import asyncio
import json
from typing import Any

import redis.asyncio as aioredis

from src.infrastructure.config import settings

_redis_clients: dict[int, aioredis.Redis] = {}


def get_redis_client() -> aioredis.Redis:
    """Returns a Redis client tied to the current asyncio event loop (prevents closed-loop errors in tests)."""
    try:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
    except RuntimeError:
        loop_id = 0

    if loop_id not in _redis_clients:
        _redis_clients[loop_id] = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=3.0,
            socket_connect_timeout=3.0
        )
    return _redis_clients[loop_id]


class RefreshTokenRepository:
    """Manages Refresh Token Rotation (RTR) lifecycle and family revocation in Redis (ADR-008)."""

    @staticmethod
    async def save_refresh_token(
        token_hash: str,
        user_id: str,
        family_id: str,
        expires_days: int = settings.REFRESH_TOKEN_EXPIRE_DAYS
    ) -> None:
        client = get_redis_client()
        key = f"refresh_token:{token_hash}"
        data = {
            "user_id": user_id,
            "family_id": family_id,
        }
        ttl_seconds = expires_days * 86400
        await client.set(key, json.dumps(data), ex=ttl_seconds)
        # Register in family set
        await client.sadd(f"token_family:{family_id}", token_hash)
        await client.expire(f"token_family:{family_id}", ttl_seconds)

    @staticmethod
    async def get_refresh_token(token_hash: str) -> dict[str, Any] | None:
        client = get_redis_client()
        key = f"refresh_token:{token_hash}"
        raw = await client.get(key)
        if raw:
            return json.loads(raw)
        return None

    @staticmethod
    async def revoke_refresh_token(token_hash: str) -> None:
        client = get_redis_client()
        key = f"refresh_token:{token_hash}"
        await client.delete(key)

    @staticmethod
    async def revoke_family(family_id: str) -> None:
        """Revoke all tokens in family if reuse of an old token is detected."""
        client = get_redis_client()
        family_key = f"token_family:{family_id}"
        tokens = await client.smembers(family_key)
        for t_hash in tokens:
            await client.delete(f"refresh_token:{t_hash}")
        await client.delete(family_key)
