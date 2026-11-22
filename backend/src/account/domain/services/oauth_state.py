import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.account.domain.ports.calendar_provider_port import CalendarAuthError

OAUTH_STATE_PURPOSE = "google_calendar_oauth"
OAUTH_STATE_TTL_SECONDS = 300
DEFAULT_RETURN_TO = "/settings"


@dataclass(frozen=True, slots=True)
class VerifiedOAuthState:
    """Verified OAuth CSRF state payload."""

    user_id: UUID
    sync_type: str
    redirect_uri: str
    return_to: str
    nonce: str
    exp: int
    purpose: str


def sanitize_return_to(return_to: str | None) -> str:
    """Allow only safe relative app paths to prevent open redirects."""
    if not return_to:
        return DEFAULT_RETURN_TO
    if (
        return_to.startswith("/")
        and not return_to.startswith("//")
        and "\\" not in return_to
        and "\r" not in return_to
        and "\n" not in return_to
    ):
        return return_to
    return DEFAULT_RETURN_TO


def create_signed_oauth_state(
    *,
    user_id: UUID,
    sync_type: str,
    redirect_uri: str,
    return_to: str | None,
    nonce: str,
    secret_key: str,
    now: datetime,
    ttl_seconds: int = OAUTH_STATE_TTL_SECONDS,
) -> str:
    """Create HMAC-SHA256 signed OAuth state token bound to user, nonce, purpose, and TTL."""
    if not secret_key:
        raise CalendarAuthError("OAuth state signing key is not configured.")
    if not nonce:
        raise CalendarAuthError("OAuth state nonce is required.")

    safe_return_to = sanitize_return_to(return_to)
    payload: dict[str, Any] = {
        "user_id": str(user_id),
        "sync_type": sync_type,
        "redirect_uri": redirect_uri,
        "return_to": safe_return_to,
        "nonce": nonce,
        "exp": int(now.timestamp()) + ttl_seconds,
        "purpose": OAUTH_STATE_PURPOSE,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_signed_oauth_state(
    *,
    state: str,
    secret_key: str,
    now: datetime,
) -> VerifiedOAuthState:
    """Verify HMAC-SHA256 signature, purpose, expiration, and structure of OAuth state."""
    if not state or not secret_key:
        raise CalendarAuthError("Missing OAuth state parameter.")

    parts = state.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise CalendarAuthError("Invalid OAuth state format.")

    payload_b64, provided_sig = parts
    expected_sig = hmac.new(
        secret_key.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise CalendarAuthError("Invalid OAuth state signature.")

    try:
        decoded_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        data = json.loads(decoded_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CalendarAuthError("Malformed OAuth state payload.") from exc

    if not isinstance(data, dict):
        raise CalendarAuthError("Malformed OAuth state payload.")

    purpose = data.get("purpose")
    if purpose != OAUTH_STATE_PURPOSE:
        raise CalendarAuthError("Invalid OAuth state purpose.")

    exp = data.get("exp")
    if not isinstance(exp, int) or isinstance(exp, bool):
        raise CalendarAuthError("Missing or invalid OAuth state expiration.")
    if exp <= int(now.timestamp()):
        raise CalendarAuthError("OAuth state has expired.")

    nonce = data.get("nonce")
    if not isinstance(nonce, str) or not nonce:
        raise CalendarAuthError("Missing OAuth state nonce.")

    raw_user_id = data.get("user_id")
    if not isinstance(raw_user_id, str) or not raw_user_id:
        raise CalendarAuthError("Missing user_id in OAuth state.")
    try:
        parsed_user_id = UUID(raw_user_id)
    except ValueError as exc:
        raise CalendarAuthError("Invalid user_id in OAuth state.") from exc

    sync_type = str(data.get("sync_type") or "two_way")
    redirect_uri = str(data.get("redirect_uri") or "")
    raw_return_to = data.get("return_to")
    safe_return_to = sanitize_return_to(raw_return_to if isinstance(raw_return_to, str) else None)

    return VerifiedOAuthState(
        user_id=parsed_user_id,
        sync_type=sync_type,
        redirect_uri=redirect_uri,
        return_to=safe_return_to,
        nonce=nonce,
        exp=exp,
        purpose=purpose,
    )
