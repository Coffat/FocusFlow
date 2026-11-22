import logging
import time
from typing import Any

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from src.account.domain.exceptions.auth_exceptions import InvalidCredentialsError
from src.shared_kernel.config import get_settings

logger = logging.getLogger(__name__)

_TRUSTED_GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


class GoogleAuthService:
    """Verifies Google OAuth tokens (ID tokens and Access tokens) for SSO."""

    def __init__(self, client_id: str | None = None):
        self._explicit_client_id = client_id

    @property
    def client_id(self) -> str:
        if self._explicit_client_id is not None:
            return self._explicit_client_id.strip()
        return (get_settings().google_client_id or "").strip()

    def _require_client_id(self) -> str:
        cid = self.client_id
        if not cid:
            raise InvalidCredentialsError("Google OAuth client_id is not configured.")
        return cid

    def verify_id_token(self, token_str: str) -> dict[str, Any]:
        """Validates Google ID Token against Google's public JWKs.

        Verifies cryptographic signature, issuer, audience, authorized party (azp),
        expiration, and explicit email_verified=True.
        """
        client_id = self._require_client_id()
        try:
            req_adapter: Any = google_requests.Request()
            payload: dict[str, Any] = dict(
                id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
                    token_str, req_adapter, client_id
                )
            )
            # Ensure issuer is trusted Google authority
            issuer = payload.get("iss", "")
            if issuer not in _TRUSTED_GOOGLE_ISSUERS:
                raise InvalidCredentialsError(f"Invalid Google token issuer: {issuer}")

            # Defense-in-depth: explicitly verify audience and authorized party (azp)
            aud = payload.get("aud")
            azp = payload.get("azp")
            if isinstance(aud, list):
                if client_id not in aud:
                    raise InvalidCredentialsError("Google ID token audience mismatch.")
                if azp != client_id:
                    raise InvalidCredentialsError("Invalid Google token authorized party (azp).")
            elif aud != client_id:
                raise InvalidCredentialsError("Google ID token audience mismatch.")

            if azp is not None and azp != client_id:
                raise InvalidCredentialsError("Invalid Google token authorized party (azp).")

            # Defense-in-depth: explicitly verify expiry claim
            exp = payload.get("exp")
            if exp is None:
                raise InvalidCredentialsError("Google ID token is missing expiration (exp).")
            try:
                exp_ts = int(exp)
            except (TypeError, ValueError) as exc:
                raise InvalidCredentialsError("Google ID token has invalid expiration.") from exc
            if exp_ts <= int(time.time()):
                raise InvalidCredentialsError("Google ID token has expired.")

            # Never default email_verified to True; require strict boolean True
            if payload.get("email_verified") is not True:
                raise InvalidCredentialsError("Google email has not been verified.")

            return payload
        except InvalidCredentialsError:
            raise
        except ValueError as exc:
            logger.warning("Failed to verify Google ID token: %s", exc)
            raise InvalidCredentialsError(f"Google token verification failed: {str(exc)}") from exc
        except Exception as exc:
            logger.error("Unexpected error during Google ID token verification: %s", exc)
            raise InvalidCredentialsError("Unable to verify Google credentials.") from exc

    async def verify_access_token(self, access_token_str: str) -> dict[str, Any]:
        """Validates Google Access Token strictly via tokeninfo (audience/azp/exp/email_verified)
        before enriching profile fields from userinfo.

        Prevents OAuth confused-deputy attacks where an access token issued to another
        Google OAuth client is presented to FocusFlow.
        """
        client_id = self._require_client_id()
        tokeninfo_url = "https://oauth2.googleapis.com/tokeninfo"
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {access_token_str}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Step 1: Verify audience, azp, expiry, and email_verified via tokeninfo
                ti_response = await client.get(
                    tokeninfo_url, params={"access_token": access_token_str}
                )
                if ti_response.status_code != 200:
                    logger.warning("Google tokeninfo returned status %s", ti_response.status_code)
                    raise InvalidCredentialsError("Invalid or expired Google access token.")

                tokeninfo: dict[str, Any] = dict(ti_response.json())

                aud = tokeninfo.get("aud")
                if aud != client_id:
                    raise InvalidCredentialsError("Google access token audience mismatch.")

                azp = tokeninfo.get("azp")
                if azp is not None and azp != client_id:
                    raise InvalidCredentialsError(
                        "Invalid Google access token authorized party (azp)."
                    )

                exp = tokeninfo.get("exp")
                expires_in = tokeninfo.get("expires_in")
                if exp is not None:
                    try:
                        exp_ts = int(exp)
                    except (TypeError, ValueError) as exc:
                        raise InvalidCredentialsError(
                            "Google access token has invalid expiration."
                        ) from exc
                    if exp_ts <= int(time.time()):
                        raise InvalidCredentialsError("Google access token has expired.")
                elif expires_in is not None:
                    try:
                        ttl = int(expires_in)
                    except (TypeError, ValueError) as exc:
                        raise InvalidCredentialsError(
                            "Google access token has invalid expires_in."
                        ) from exc
                    if ttl <= 0:
                        raise InvalidCredentialsError("Google access token has expired.")
                else:
                    raise InvalidCredentialsError("Google access token is missing expiration.")

                ti_verified = tokeninfo.get("email_verified")
                if ti_verified is not True and ti_verified != "true":
                    raise InvalidCredentialsError("Google email has not been verified.")

                # Step 2: Fetch userinfo to enrich name/picture and cross-check sub/email
                ui_response = await client.get(userinfo_url, headers=headers)
                if ui_response.status_code != 200:
                    logger.warning("Google userinfo returned status %s", ui_response.status_code)
                    raise InvalidCredentialsError("Invalid or expired Google access token.")

                userinfo: dict[str, Any] = dict(ui_response.json())
                ui_verified = (
                    userinfo.get("email_verified")
                    if "email_verified" in userinfo
                    else userinfo.get("verified_email")
                )
                if ui_verified is not True:
                    raise InvalidCredentialsError("Google email has not been verified.")

                ti_sub = tokeninfo.get("sub")
                ui_sub = userinfo.get("sub")
                if ti_sub and ui_sub and ti_sub != ui_sub:
                    raise InvalidCredentialsError("Google token subject mismatch.")

                ti_email = str(tokeninfo.get("email") or "").strip().lower()
                ui_email = str(userinfo.get("email") or "").strip().lower()
                if ti_email and ui_email and ti_email != ui_email:
                    raise InvalidCredentialsError("Google token email mismatch.")

                merged: dict[str, Any] = {
                    **tokeninfo,
                    **userinfo,
                    "email": ui_email or ti_email,
                    "email_verified": True,
                }
                return merged
        except InvalidCredentialsError:
            raise
        except httpx.HTTPError as exc:
            logger.error("HTTP error verifying Google access token: %s", exc)
            raise InvalidCredentialsError(
                "Failed to communicate with Google authentication server."
            ) from exc


google_auth_service = GoogleAuthService()
