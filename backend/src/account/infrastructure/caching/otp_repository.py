import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Any

from src.account.infrastructure.caching.redis_client import get_redis_client
from src.shared_kernel.config import get_settings


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
    async def get_raw_session(cls, purpose: str, identifier: str) -> dict[str, Any] | None:
        """Retrieve existing OTP session payload from Redis."""
        client = get_redis_client()
        clean_id = identifier.lower().strip()
        raw_data = await client.get(f"otp:{purpose}:{clean_id}")
        if not raw_data:
            return None
        return json.loads(raw_data)

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
        Verify user-submitted OTP against stored SHA-256 hash.
        Enforces retry limit and deletes key immediately upon success (Anti-Replay).
        """
        settings = get_settings()
        client = get_redis_client()
        clean_id = identifier.lower().strip()
        otp_key = f"otp:{purpose}:{clean_id}"

        raw_data = await client.get(otp_key)
        if not raw_data:
            return False, "Mã xác thực đã hết hạn hoặc không tồn tại. Vui lòng yêu cầu mã mới.", {}

        data = json.loads(raw_data)
        attempts = int(data.get("attempts", 0)) + 1

        # Check brute force limit
        if attempts > settings.otp_max_attempts:
            await client.delete(otp_key)
            return False, "Bạn đã nhập sai quá số lần cho phép. Mã xác thực đã bị hủy.", {}

        user_otp_hash = cls.hash_otp(user_otp)
        is_match = secrets.compare_digest(user_otp_hash, data.get("otp_hash", ""))

        if not is_match:
            # Update attempts while preserving remaining TTL
            ttl = await client.ttl(otp_key)
            if ttl > 0:
                data["attempts"] = attempts
                await client.set(otp_key, json.dumps(data), ex=ttl)
            remaining_attempts = settings.otp_max_attempts - attempts
            if remaining_attempts <= 0:
                await client.delete(otp_key)
                return False, "Bạn đã nhập sai quá số lần cho phép. Mã xác thực đã bị hủy.", {}
            return False, f"Mã xác thực không chính xác. Bạn còn {remaining_attempts} lần thử.", {}

        # Success: consume immediately to prevent replay attack
        await client.delete(otp_key)
        return True, "Xác thực thành công.", data.get("payload", {})

    @classmethod
    async def save_reset_token(cls, token: str, email: str, ttl_seconds: int = 600) -> None:
        """Store single-use password reset token."""
        client = get_redis_client()
        await client.set(f"password_reset_token:{token}", email.lower().strip(), ex=ttl_seconds)

    @classmethod
    async def consume_reset_token(cls, token: str) -> str | None:
        """Retrieve and immediately invalidate single-use password reset token."""
        client = get_redis_client()
        token_key = f"password_reset_token:{token}"
        saved_email = await client.get(token_key)
        if saved_email:
            await client.delete(token_key)
            return str(saved_email)
        return None
