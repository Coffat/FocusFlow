import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Any

from src.account.infrastructure.caching.redis_client import get_redis_client
from src.shared_kernel.config import get_settings

_LUA_VERIFY_AND_CONSUME_OTP = """
local raw = redis.call("GET", KEYS[1])
if not raw then
    return {"EXPIRED", "0", ""}
end

local ok, data = pcall(cjson.decode, raw)
if not ok or type(data) ~= "table" then
    redis.call("DEL", KEYS[1])
    return {"EXPIRED", "0", ""}
end

local max_attempts = tonumber(ARGV[2]) or 3
local attempts = (tonumber(data["attempts"]) or 0) + 1
if attempts > max_attempts then
    redis.call("DEL", KEYS[1])
    return {"MAX_ATTEMPTS", "0", ""}
end

local stored_hash = tostring(data["otp_hash"] or "")
local submitted_hash = tostring(ARGV[1] or "")
local is_match = (#stored_hash == #submitted_hash) and (#stored_hash > 0)
if is_match then
    local diff = 0
    for i = 1, #stored_hash do
        if string.byte(stored_hash, i) ~= string.byte(submitted_hash, i) then
            diff = diff + 1
        end
    end
    is_match = (diff == 0)
end

if is_match then
    redis.call("DEL", KEYS[1])
    return {"OK", "0", raw}
end

local remaining = max_attempts - attempts
if remaining <= 0 then
    redis.call("DEL", KEYS[1])
    return {"MAX_ATTEMPTS", "0", ""}
end

data["attempts"] = attempts
local pttl = redis.call("PTTL", KEYS[1])
if pttl > 0 then
    redis.call("SET", KEYS[1], cjson.encode(data), "PX", pttl)
else
    redis.call("DEL", KEYS[1])
    return {"EXPIRED", "0", ""}
end

return {"INVALID", tostring(remaining), ""}
"""


class OtpRepository:
    """Manages secure OTP lifecycle in Redis with SHA-256 hashing, rate limiting, and brute-force protection."""

    @staticmethod
    def generate_otp() -> str:
        """Generate cryptographically secure 6-digit numeric OTP using CSPRNG."""
        code = secrets.randbelow(900000) + 100000
        return str(code)

    @staticmethod
    def hash_otp(otp_code: str) -> str:
        """Hash raw OTP with SHA-256 before persisting into cache (Defense-in-Depth)."""
        return hashlib.sha256(otp_code.strip().encode("utf-8")).hexdigest()

    @classmethod
    async def get_cooldown_remaining(cls, purpose: str, identifier: str) -> int | None:
        """Check if an OTP request is currently rate-limited by cooldown."""
        client = get_redis_client()
        clean_id = identifier.lower().strip()
        cooldown_key = f"otp_cooldown:{purpose}:{clean_id}"
        ttl = await client.ttl(cooldown_key)
        if ttl > 0:
            return ttl
        return None

    @classmethod
    async def set_cooldown(cls, purpose: str, identifier: str) -> None:
        """Establish rate-limiting cooldown key in Redis without persisting an OTP."""
        settings = get_settings()
        client = get_redis_client()
        clean_id = identifier.lower().strip()
        cooldown_key = f"otp_cooldown:{purpose}:{clean_id}"
        await client.set(cooldown_key, "1", ex=settings.otp_cooldown_seconds)

    @classmethod
    async def get_raw_session(cls, purpose: str, identifier: str) -> dict[str, Any] | None:
        """Retrieve existing OTP session payload from Redis."""
        client = get_redis_client()
        clean_id = identifier.lower().strip()
        raw_data = await client.get(f"otp:{purpose}:{clean_id}")
        if not raw_data:
            return None
        parsed: dict[str, Any] = dict(json.loads(raw_data))
        return parsed

    @classmethod
    async def save_otp(
        cls, purpose: str, identifier: str, otp_code: str, payload: dict[str, Any] | None = None
    ) -> None:
        """Store hashed OTP with TTL and establish cooldown key in Redis."""
        settings = get_settings()
        client = get_redis_client()
        clean_id = identifier.lower().strip()
        otp_key = f"otp:{purpose}:{clean_id}"
        cooldown_key = f"otp_cooldown:{purpose}:{clean_id}"

        data = {
            "otp_hash": cls.hash_otp(otp_code),
            "attempts": 0,
            "payload": payload or {},
            "created_at": datetime.now(UTC).isoformat(),
        }

        # 1. Save OTP with TTL (300 seconds per ADR/requirements)
        await client.set(otp_key, json.dumps(data), ex=settings.otp_ttl_seconds)

        # 2. Set rate-limiting cooldown (60 seconds)
        await client.set(cooldown_key, "1", ex=settings.otp_cooldown_seconds)

    @classmethod
    async def verify_and_consume_otp(
        cls, purpose: str, identifier: str, user_otp: str
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        Atomically verify user-submitted OTP against stored SHA-256 hash via Redis Lua.
        Enforces retry limit and deletes key immediately upon success or exhaustion (zero TOCTOU).
        """
        settings = get_settings()
        client = get_redis_client()
        clean_id = identifier.lower().strip()
        otp_key = f"otp:{purpose}:{clean_id}"
        user_otp_hash = cls.hash_otp(user_otp)

        result: Any = await client.eval(
            _LUA_VERIFY_AND_CONSUME_OTP,
            1,
            otp_key,
            user_otp_hash,
            str(settings.otp_max_attempts),
        )
        status_code = str(result[0]) if isinstance(result, (list, tuple)) and result else "EXPIRED"

        if status_code == "OK":
            raw_json = str(result[2]) if len(result) > 2 and result[2] else "{}"
            parsed_raw = json.loads(raw_json)
            payload = parsed_raw.get("payload", {}) if isinstance(parsed_raw, dict) else {}
            if not isinstance(payload, dict):
                payload = {}
            return True, "Xác thực thành công.", payload

        if status_code == "MAX_ATTEMPTS":
            return False, "Bạn đã nhập sai quá số lần cho phép. Mã xác thực đã bị hủy.", {}

        if status_code == "INVALID":
            remaining_attempts = int(result[1]) if len(result) > 1 else 0
            return False, f"Mã xác thực không chính xác. Bạn còn {remaining_attempts} lần thử.", {}

        return False, "Mã xác thực đã hết hạn hoặc không tồn tại. Vui lòng yêu cầu mã mới.", {}

    @classmethod
    async def save_reset_token(cls, token: str, email: str, ttl_seconds: int = 600) -> None:
        """Store single-use password reset token."""
        client = get_redis_client()
        await client.set(f"password_reset_token:{token}", email.lower().strip(), ex=ttl_seconds)

    @classmethod
    async def consume_reset_token(cls, token: str) -> str | None:
        """Atomically retrieve and invalidate single-use password reset token using GETDEL."""
        client = get_redis_client()
        token_key = f"password_reset_token:{token}"
        saved_email = await client.getdel(token_key)
        if saved_email:
            return str(saved_email)
        return None
