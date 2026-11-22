from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal, Protocol
from uuid import UUID

RefreshTokenInspectStatus = Literal[
    "ACTIVE",
    "REUSE_DETECTED",
    "FAMILY_REVOKED",
    "NOT_FOUND",
    "CORRUPTED",
]

RefreshTokenRotateStatus = Literal[
    "ROTATED",
    "REUSE_DETECTED",
    "FAMILY_REVOKED",
    "NOT_FOUND",
    "EXPIRED",
]


@dataclass(frozen=True, slots=True)
class RefreshTokenInspectResult:
    """Result of atomically inspecting a refresh token and detecting reuse."""

    status: RefreshTokenInspectStatus
    user_id: str | None = None
    family_id: str | None = None
    remaining_ttl: int = 0


@dataclass(frozen=True, slots=True)
class RefreshTokenRotateResult:
    """Result of atomically rotating an active refresh token in Redis."""

    status: RefreshTokenRotateStatus
    remaining_ttl: int = 0


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

    async def save_rotated_refresh_token(
        self,
        token_hash: str,
        user_id: str,
        family_id: str,
        expires_days: int | None = None,
    ) -> bool: ...

    async def inspect_refresh_token_atomic(
        self,
        token_hash: str,
    ) -> RefreshTokenInspectResult: ...

    async def rotate_refresh_token_atomic(
        self,
        old_token_hash: str,
        new_token_hash: str,
        user_id: str,
        family_id: str,
        rotated_at: str | None = None,
        max_ttl_seconds: int | None = None,
    ) -> RefreshTokenRotateResult: ...

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

    async def send_overdue_alert_email(
        self,
        to_email: str,
        overdue_task_titles: list[str],
        remaining_reschedule_budget: int,
    ) -> None: ...


class GoogleAuthPort(Protocol):
    """Protocol for verifying Google OAuth identity tokens."""

    def verify_id_token(self, token_str: str) -> dict[str, Any]: ...

    async def verify_access_token(self, access_token_str: str) -> dict[str, Any]: ...
