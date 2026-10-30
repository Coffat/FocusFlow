import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError

from src.account.domain.exceptions.auth_exceptions import InvalidTokenError, TokenExpiredError
from src.shared_kernel.config import get_settings


class JwtTokenProvider:
    """Provides JWT token creation, encoding, decoding, and verification per ADR-008."""

    @staticmethod
    def create_access_token(
        user_id: UUID, email: str, role: str, tier: str, expires_delta: timedelta | None = None
    ) -> str:
        """Create signed JWT Access Token with 15-minute standard expiration."""
        settings = get_settings()
        now = datetime.now(UTC)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.access_token_expire_minutes)

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "tier": tier,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "access",
        }

        return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def decode_access_token(token: str) -> dict[str, Any]:
        """Decode and validate a JWT Access Token signature and expiration."""
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
            token_type = payload.get("type")
            if token_type != "access":
                raise InvalidTokenError("Invalid token type.")
            return payload
        except ExpiredSignatureError as exc:
            raise TokenExpiredError("Access token has expired.") from exc
        except PyJWTError as exc:
            raise InvalidTokenError("Could not validate access token.") from exc

    @staticmethod
    def create_refresh_token() -> str:
        """Generate high-entropy CSPRN string for 7-day Refresh Token."""
        return secrets.token_urlsafe(64)

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Hash raw refresh token with SHA-256 before persisting into Redis."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
