import logging
from typing import Any

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from src.domain.exceptions.auth_exceptions import InvalidCredentialsError
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)


class GoogleAuthService:
    """Verifies Google OAuth tokens (ID tokens and Access tokens) for SSO."""

    def __init__(self, client_id: str | None = None):
        self.client_id = client_id or settings.GOOGLE_CLIENT_ID

    def verify_id_token(self, token_str: str) -> dict[str, Any]:
        """Validates Google ID Token against Google's public JWKs.

        Args:
            token_str: The raw Google ID Token JWT.

        Returns:
            Dict containing payload with sub, email, name, picture, email_verified.

        Raises:
            InvalidCredentialsError: When token is invalid, expired, or audience mismatches.
        """
        try:
            payload = id_token.verify_oauth2_token(
                token_str,
                google_requests.Request(),
                self.client_id
            )
            # Ensure issuer is trusted Google authority
            issuer = payload.get("iss", "")
            if issuer not in ["accounts.google.com", "https://accounts.google.com"]:
                raise InvalidCredentialsError(f"Invalid Google token issuer: {issuer}")

            return payload
        except ValueError as exc:
            logger.warning(f"Failed to verify Google ID token: {exc}")
            raise InvalidCredentialsError(f"Google token verification failed: {str(exc)}") from exc
        except Exception as exc:
            logger.error(f"Unexpected error during Google ID token verification: {exc}")
            raise InvalidCredentialsError("Unable to verify Google credentials.") from exc

    async def verify_access_token(self, access_token_str: str) -> dict[str, Any]:
        """Validates Google Access Token via Google OAuth2 userinfo endpoint.

        Args:
            access_token_str: The raw Google OAuth2 Access Token.

        Returns:
            Dict containing userinfo with sub, email, name, picture, email_verified.

        Raises:
            InvalidCredentialsError: When access token is rejected by Google.
        """
        url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {access_token_str}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"Google userinfo returned status {response.status_code}")
                    raise InvalidCredentialsError("Invalid or expired Google access token.")
                data = response.json()
                if "email_verified" not in data and "verified_email" in data:
                    data["email_verified"] = data["verified_email"]
                return data
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error verifying Google access token: {exc}")
            raise InvalidCredentialsError("Failed to communicate with Google authentication server.") from exc


google_auth_service = GoogleAuthService()
