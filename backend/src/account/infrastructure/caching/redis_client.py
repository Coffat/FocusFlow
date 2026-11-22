import asyncio
import json
from datetime import UTC, datetime
from typing import Any, cast

import redis.asyncio as aioredis

from src.account.application.ports.auth_ports import (
    RefreshTokenInspectResult,
    RefreshTokenInspectStatus,
    RefreshTokenRotateResult,
    RefreshTokenRotateStatus,
)
from src.account.domain.exceptions.auth_exceptions import SessionStoreUnavailableError
from src.shared_kernel.config import get_settings

_redis_clients: dict[int, aioredis.Redis] = {}


def get_redis_client() -> aioredis.Redis:
    """Returns a Redis client tied to the current asyncio event loop (prevents closed-loop errors in tests)."""
    settings = get_settings()
    try:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
    except RuntimeError:
        loop_id = 0

    if loop_id not in _redis_clients:
        _redis_clients[loop_id] = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=3.0,
            socket_connect_timeout=3.0,
        )
    return _redis_clients[loop_id]


_SAVE_REFRESH_TOKEN_LUA = """
local ttl = tonumber(ARGV[4])
redis.call('SET', KEYS[1], ARGV[1], 'EX', ttl)
redis.call('SADD', KEYS[2], ARGV[2])
redis.call('EXPIRE', KEYS[2], ttl)
redis.call('SADD', KEYS[3], ARGV[3])
local user_fam_ttl = redis.call('TTL', KEYS[3])
if user_fam_ttl < ttl then
    redis.call('EXPIRE', KEYS[3], ttl)
end
return 1
"""

_ROTATE_IF_FAMILY_ACTIVE_LUA = """
if redis.call('SISMEMBER', KEYS[1], ARGV[1]) == 0 then
    return 0
end
redis.call('SET', KEYS[2], ARGV[2], 'EX', tonumber(ARGV[3]))
redis.call('SADD', KEYS[3], ARGV[4])
redis.call('EXPIRE', KEYS[3], tonumber(ARGV[3]))
return 1
"""

_INSPECT_OR_REVOKE_REUSED_LUA = """
local function revoke_family_atomic(family_id, user_id)
    if family_id and family_id ~= '' then
        local family_key = 'token_family:' .. family_id
        local members = redis.call('SMEMBERS', family_key)
        for _, member_hash in ipairs(members) do
            redis.call('DEL', 'refresh_token:' .. member_hash)
        end
        redis.call('DEL', family_key)
        if user_id and user_id ~= '' then
            redis.call('SREM', 'user_families:' .. user_id, family_id)
        end
    end
end

local active_raw = redis.call('GET', KEYS[1])
if active_raw then
    local ok, data = pcall(cjson.decode, active_raw)
    if not ok or type(data) ~= 'table' or not data['user_id'] or not data['family_id'] then
        return {'CORRUPTED', '', '', 0}
    end
    local user_id = tostring(data['user_id'])
    local family_id = tostring(data['family_id'])
    if redis.call('SISMEMBER', 'user_families:' .. user_id, family_id) == 0 then
        redis.call('DEL', KEYS[1])
        return {'FAMILY_REVOKED', user_id, family_id, 0}
    end
    local tok_ttl = redis.call('TTL', KEYS[1])
    local fam_ttl = redis.call('TTL', 'token_family:' .. family_id)
    local remaining_ttl = 0
    if tok_ttl > 0 and fam_ttl > 0 then
        remaining_ttl = math.min(tok_ttl, fam_ttl)
    elseif tok_ttl > 0 then
        remaining_ttl = tok_ttl
    elseif fam_ttl > 0 then
        remaining_ttl = fam_ttl
    end
    if remaining_ttl <= 0 then
        redis.call('DEL', KEYS[1])
        return {'NOT_FOUND', '', '', 0}
    end
    return {'ACTIVE', user_id, family_id, remaining_ttl}
end

local used_raw = redis.call('GET', KEYS[2])
if used_raw then
    local ok, data = pcall(cjson.decode, used_raw)
    local user_id = ''
    local family_id = ''
    if ok and type(data) == 'table' then
        if data['user_id'] then user_id = tostring(data['user_id']) end
        if data['family_id'] then family_id = tostring(data['family_id']) end
    end
    revoke_family_atomic(family_id, user_id)
    return {'REUSE_DETECTED', user_id, family_id, 0}
end

return {'NOT_FOUND', '', '', 0}
"""

_ROTATE_REFRESH_TOKEN_ATOMIC_LUA = """
local function revoke_family_atomic(family_id, user_id)
    if family_id and family_id ~= '' then
        local family_key = 'token_family:' .. family_id
        local members = redis.call('SMEMBERS', family_key)
        for _, member_hash in ipairs(members) do
            redis.call('DEL', 'refresh_token:' .. member_hash)
        end
        redis.call('DEL', family_key)
        if user_id and user_id ~= '' then
            redis.call('SREM', 'user_families:' .. user_id, family_id)
        end
    end
end

local new_hash = ARGV[1]
local user_id = ARGV[2]
local family_id = ARGV[3]
local rotated_at = ARGV[4]
local max_ttl = tonumber(ARGV[5])

local active_raw = redis.call('GET', KEYS[1])
if not active_raw then
    local used_raw = redis.call('GET', KEYS[2])
    if used_raw then
        local ok, data = pcall(cjson.decode, used_raw)
        local used_user = user_id
        local used_family = family_id
        if ok and type(data) == 'table' then
            if data['user_id'] then used_user = tostring(data['user_id']) end
            if data['family_id'] then used_family = tostring(data['family_id']) end
        end
        revoke_family_atomic(used_family, used_user)
        return {'REUSE_DETECTED', 0}
    end
    if redis.call('SISMEMBER', KEYS[5], family_id) == 0 then
        return {'FAMILY_REVOKED', 0}
    end
    return {'NOT_FOUND', 0}
end

if redis.call('SISMEMBER', KEYS[5], family_id) == 0 then
    redis.call('DEL', KEYS[1])
    return {'FAMILY_REVOKED', 0}
end

local tok_ttl = redis.call('TTL', KEYS[1])
local fam_ttl = redis.call('TTL', KEYS[4])
local remaining_ttl = 0
if tok_ttl > 0 and fam_ttl > 0 then
    remaining_ttl = math.min(tok_ttl, fam_ttl)
elseif tok_ttl > 0 then
    remaining_ttl = tok_ttl
elseif fam_ttl > 0 then
    remaining_ttl = fam_ttl
end
if max_ttl and max_ttl > 0 and remaining_ttl > max_ttl then
    remaining_ttl = max_ttl
end
if remaining_ttl <= 0 then
    redis.call('DEL', KEYS[1])
    return {'EXPIRED', 0}
end

redis.call('DEL', KEYS[1])

local used_payload = cjson.encode({
    family_id = family_id,
    user_id = user_id,
    rotated_at = rotated_at,
    replacement_hash = new_hash,
})
redis.call('SET', KEYS[2], used_payload, 'EX', remaining_ttl)

local new_payload = cjson.encode({
    user_id = user_id,
    family_id = family_id,
})
redis.call('SET', KEYS[3], new_payload, 'EX', remaining_ttl)
redis.call('SADD', KEYS[4], new_hash)
redis.call('EXPIRE', KEYS[4], remaining_ttl)

return {'ROTATED', remaining_ttl}
"""

_REVOKE_TOKEN_AND_FAMILY_LUA = """
local function revoke_family_atomic(family_id, user_id)
    if family_id and family_id ~= '' then
        local family_key = 'token_family:' .. family_id
        local members = redis.call('SMEMBERS', family_key)
        for _, member_hash in ipairs(members) do
            redis.call('DEL', 'refresh_token:' .. member_hash)
        end
        redis.call('DEL', family_key)
        if user_id and user_id ~= '' then
            redis.call('SREM', 'user_families:' .. user_id, family_id)
        end
    end
end

local raw = redis.call('GET', KEYS[1])
if not raw then
    raw = redis.call('GET', KEYS[2])
end
redis.call('DEL', KEYS[1])
if raw then
    local ok, data = pcall(cjson.decode, raw)
    if ok and type(data) == 'table' then
        local fam = data['family_id'] and tostring(data['family_id']) or ''
        local uid = data['user_id'] and tostring(data['user_id']) or ''
        revoke_family_atomic(fam, uid)
    end
end
return 1
"""

_REVOKE_FAMILY_LUA = """
local family_id = ARGV[1]
local user_id = ARGV[2]
local members = redis.call('SMEMBERS', KEYS[1])
for _, member_hash in ipairs(members) do
    local tok_key = 'refresh_token:' .. member_hash
    if user_id == '' then
        local raw = redis.call('GET', tok_key)
        if raw then
            local ok, data = pcall(cjson.decode, raw)
            if ok and type(data) == 'table' and data['user_id'] then
                user_id = tostring(data['user_id'])
            end
        end
    end
    redis.call('DEL', tok_key)
end
redis.call('DEL', KEYS[1])
if user_id ~= '' then
    redis.call('SREM', 'user_families:' .. user_id, family_id)
end
return 1
"""

_VALID_INSPECT_STATUSES: set[str] = {
    "ACTIVE",
    "REUSE_DETECTED",
    "FAMILY_REVOKED",
    "NOT_FOUND",
    "CORRUPTED",
}
_VALID_ROTATE_STATUSES: set[str] = {
    "ROTATED",
    "REUSE_DETECTED",
    "FAMILY_REVOKED",
    "NOT_FOUND",
    "EXPIRED",
}


class RefreshTokenRepository:
    """Manages Refresh Token Rotation (RTR) lifecycle and family revocation in Redis (ADR-008)."""

    @staticmethod
    async def save_refresh_token(
        token_hash: str,
        user_id: str,
        family_id: str,
        expires_days: int | None = None,
    ) -> None:
        settings = get_settings()
        if expires_days is None:
            expires_days = settings.refresh_token_expire_days

        client = get_redis_client()
        data_json = json.dumps({"user_id": user_id, "family_id": family_id})
        ttl_seconds = expires_days * 86400
        await client.eval(
            _SAVE_REFRESH_TOKEN_LUA,
            3,
            f"refresh_token:{token_hash}",
            f"token_family:{family_id}",
            f"user_families:{user_id}",
            data_json,
            token_hash,
            family_id,
            str(ttl_seconds),
        )

    @staticmethod
    async def save_rotated_refresh_token(
        token_hash: str,
        user_id: str,
        family_id: str,
        expires_days: int | None = None,
    ) -> bool:
        """Atomically persist a rotated refresh token ONLY if its family is still active.

        Prevents a concurrent refresh from reviving a session family that was revoked
        (e.g., during password reset or password change).
        """
        settings = get_settings()
        if expires_days is None:
            expires_days = settings.refresh_token_expire_days

        client = get_redis_client()
        ttl_seconds = expires_days * 86400
        data_json = json.dumps({"user_id": user_id, "family_id": family_id})
        try:
            result = await client.eval(
                _ROTATE_IF_FAMILY_ACTIVE_LUA,
                3,
                f"user_families:{user_id}",
                f"refresh_token:{token_hash}",
                f"token_family:{family_id}",
                family_id,
                data_json,
                str(ttl_seconds),
                token_hash,
            )
        except (aioredis.RedisError, OSError) as exc:
            raise SessionStoreUnavailableError() from exc
        return int(result) == 1

    @staticmethod
    async def inspect_refresh_token_atomic(token_hash: str) -> RefreshTokenInspectResult:
        """Atomically inspect a refresh token and immediately revoke its family on reuse.

        - If `refresh_token:{token_hash}` is active and its family is in `user_families:{user_id}`,
          returns status='ACTIVE' with bounded remaining TTL.
        - If inactive AND `used_refresh_token:{token_hash}` exists, atomically revokes the entire
          family and returns status='REUSE_DETECTED'.
        - If neither exists, returns status='NOT_FOUND' without revoking any family.
        """
        client = get_redis_client()
        try:
            raw_result = await client.eval(
                _INSPECT_OR_REVOKE_REUSED_LUA,
                2,
                f"refresh_token:{token_hash}",
                f"used_refresh_token:{token_hash}",
            )
        except (aioredis.RedisError, OSError) as exc:
            raise SessionStoreUnavailableError() from exc

        if not isinstance(raw_result, (list, tuple)) or len(raw_result) < 4:
            raise SessionStoreUnavailableError("Unexpected response from session store.")

        status_raw = str(raw_result[0])
        if status_raw not in _VALID_INSPECT_STATUSES:
            raise SessionStoreUnavailableError("Invalid token status returned by session store.")

        status = cast(RefreshTokenInspectStatus, status_raw)
        user_id = str(raw_result[1]) if raw_result[1] else None
        family_id = str(raw_result[2]) if raw_result[2] else None
        remaining_ttl = int(raw_result[3]) if raw_result[3] else 0
        return RefreshTokenInspectResult(
            status=status,
            user_id=user_id,
            family_id=family_id,
            remaining_ttl=remaining_ttl,
        )

    @staticmethod
    async def rotate_refresh_token_atomic(
        old_token_hash: str,
        new_token_hash: str,
        user_id: str,
        family_id: str,
        rotated_at: str | None = None,
        max_ttl_seconds: int | None = None,
    ) -> RefreshTokenRotateResult:
        """Atomically rotate an active refresh token to a replacement hash in a single Lua script.

        - Verifies `refresh_token:{old_hash}` is still active and `family_id` is in `user_families:{user_id}`.
        - Deletes `refresh_token:{old_hash}` and records `used_refresh_token:{old_hash}` with
          bounded TTL equal to the remaining family TTL (capped at `max_ttl_seconds`).
        - Persists `refresh_token:{new_hash}` with the same bounded remaining TTL (never extends
          session lifetime beyond original family expiry).
        - If a concurrent caller already rotated `old_hash`, detects `used_refresh_token:{old_hash}`,
          immediately revokes the entire family, and returns status='REUSE_DETECTED'.
        """
        settings = get_settings()
        if max_ttl_seconds is None:
            max_ttl_seconds = settings.refresh_token_expire_days * 86400
        if rotated_at is None:
            rotated_at = datetime.now(UTC).isoformat()

        client = get_redis_client()
        try:
            raw_result = await client.eval(
                _ROTATE_REFRESH_TOKEN_ATOMIC_LUA,
                5,
                f"refresh_token:{old_token_hash}",
                f"used_refresh_token:{old_token_hash}",
                f"refresh_token:{new_token_hash}",
                f"token_family:{family_id}",
                f"user_families:{user_id}",
                new_token_hash,
                user_id,
                family_id,
                rotated_at,
                str(max_ttl_seconds),
            )
        except (aioredis.RedisError, OSError) as exc:
            raise SessionStoreUnavailableError() from exc

        if not isinstance(raw_result, (list, tuple)) or len(raw_result) < 2:
            raise SessionStoreUnavailableError("Unexpected rotation response from session store.")

        status_raw = str(raw_result[0])
        if status_raw not in _VALID_ROTATE_STATUSES:
            raise SessionStoreUnavailableError("Invalid rotation status returned by session store.")

        status = cast(RefreshTokenRotateStatus, status_raw)
        remaining_ttl = int(raw_result[1]) if raw_result[1] else 0
        return RefreshTokenRotateResult(status=status, remaining_ttl=remaining_ttl)

    @staticmethod
    async def get_refresh_token(token_hash: str) -> dict[str, Any] | None:
        client = get_redis_client()
        key = f"refresh_token:{token_hash}"
        raw = await client.get(key)
        if raw:
            parsed: dict[str, Any] = dict(json.loads(raw))
            return parsed
        return None

    @staticmethod
    async def revoke_refresh_token(token_hash: str) -> None:
        """Atomically revoke the presented refresh token AND its entire session family (e.g. logout)."""
        client = get_redis_client()
        await client.eval(
            _REVOKE_TOKEN_AND_FAMILY_LUA,
            2,
            f"refresh_token:{token_hash}",
            f"used_refresh_token:{token_hash}",
        )

    @staticmethod
    async def revoke_family(family_id: str, user_id: str | None = None) -> None:
        """Atomically revoke all active tokens in a family and remove it from user_families."""
        client = get_redis_client()
        await client.eval(
            _REVOKE_FAMILY_LUA,
            1,
            f"token_family:{family_id}",
            family_id,
            user_id or "",
        )

    @staticmethod
    async def revoke_all_for_user(user_id: str) -> None:
        """Revoke all refresh tokens and active token families for a user."""
        client = get_redis_client()
        user_families_key = f"user_families:{user_id}"
        families = await client.smembers(user_families_key)
        for fam in families:
            fam_str = fam.decode("utf-8") if isinstance(fam, bytes) else str(fam)
            await RefreshTokenRepository.revoke_family(fam_str, user_id=user_id)
        await client.delete(user_families_key)
