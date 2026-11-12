from datetime import timedelta
from typing import Any, Protocol
from uuid import UUID


class TokenProviderPort(Protocol):
    """Protocol for JWT and high-entropy token operations."""

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        role: str,
        tier: str,
        expires_delta: timedelta | None = None,
    ) -> str: ...

    def decode_access_token(self, token: str) -> dict[str, Any]: ...

    def create_refresh_token(self) -> str: ...

    def hash_token(self, raw_token: str) -> str: ...


class RefreshTokenRepositoryPort(Protocol):
    """Protocol for Refresh Token Rotation storage in Redis."""

    async def save_refresh_token(
        self,
        token_hash: str,
        user_id: str,
        family_id: str,
        expires_days: int | None = None,
    ) -> None: ...

    async def get_refresh_token(self, token_hash: str) -> dict[str, Any] | None: ...

    async def revoke_refresh_token(self, token_hash: str) -> None: ...

    async def revoke_family(self, family_id: str) -> None: ...

    async def revoke_all_for_user(self, user_id: str) -> None: ...


class OtpRepositoryPort(Protocol):
    """Protocol for OTP lifecycle management in Redis."""

    def generate_otp(self) -> str: ...

    def hash_otp(self, otp_code: str) -> str: ...

    async def get_cooldown_remaining(self, purpose: str, identifier: str) -> int | None: ...

    async def get_raw_session(self, purpose: str, identifier: str) -> dict[str, Any] | None: ...

    async def save_otp(
        self, purpose: str, identifier: str, otp_code: str, payload: dict[str, Any] | None = None
    ) -> None: ...

    async def verify_and_consume_otp(
        self, purpose: str, identifier: str, user_otp: str
    ) -> tuple[bool, str, dict[str, Any]]: ...

    async def save_reset_token(self, token: str, email: str, ttl_seconds: int = 600) -> None: ...

    async def consume_reset_token(self, token: str) -> str | None: ...


class EmailServicePort(Protocol):
    """Protocol for email notifications."""

    async def send_otp_email(self, to_email: str, otp_code: str, purpose: str) -> None: ...


class GoogleAuthPort(Protocol):
    """Protocol for verifying Google OAuth identity tokens."""

    def verify_id_token(self, token_str: str) -> dict[str, Any]: ...

    async def verify_access_token(self, access_token_str: str) -> dict[str, Any]: ...
