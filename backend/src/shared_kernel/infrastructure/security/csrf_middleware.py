"""Defense-in-depth CSRF protection middleware for cookie-authenticated endpoints (AUD-HIGH-01).

Threat model & invariants:
- Safe HTTP methods (GET, HEAD, OPTIONS, TRACE) are never blocked so SSE streams,
  WebCal ICS feeds, and Google OAuth GET callbacks (protected by HMAC + Redis GETDEL state)
  operate normally.
- Strictly scoped provider webhooks authenticated via cryptographic signatures/headers
  (billing HMAC-SHA256 webhook and Google Calendar push webhook) are exempt.
- Any state-changing request carrying ``access_token`` or ``refresh_token`` cookies MUST
  pass strict origin verification:
  1. Reject explicit ``Sec-Fetch-Site: cross-site`` even if Origin/Referer were missing/forged.
  2. Validate ``Origin`` (or fallback ``Referer`` origin when ``Origin`` is absent) against
     the server-configured allowlist (``settings.csrf_trusted_origin_set``).
  3. Fail closed (403 ``CSRF_VALIDATION_FAILED``) when BOTH ``Origin`` and ``Referer`` are
     absent on cookie-authenticated state-changing requests.
  4. Never trust ``Host``, ``X-Forwarded-Host``, or ``X-Forwarded-Proto`` headers to expand
     the trusted origin allowlist.
- Non-browser API requests using ``Authorization: Bearer`` with NO auth cookies are allowed
  without browser CSRF checks.
- Unauthenticated browser requests to cookie-issuing auth endpoints (e.g. ``/api/v1/auth/login``)
  are also validated whenever browser origin/fetch-metadata headers are present, preventing
  cross-site Login CSRF.
"""

from collections.abc import Iterable

import structlog
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.shared_kernel.config import get_settings, normalize_origin

_logger = structlog.get_logger(__name__)

SAFE_HTTP_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

AUTH_COOKIE_NAMES: frozenset[str] = frozenset({"access_token", "refresh_token"})

# Strictly scoped provider webhooks authenticated by provider signatures/channel headers.
EXEMPT_WEBHOOK_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/account/billing/webhook",
        "/api/v1/calendar/webhooks/google",
    }
)

# Cookie-issuing / session-mutating auth endpoints protected against browser Login CSRF.
COOKIE_AUTH_ENDPOINTS: frozenset[str] = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/google",
        "/api/v1/auth/register",
        "/api/v1/auth/register/verify-otp",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
    }
)


def _extract_headers(scope: Scope) -> dict[str, list[str]]:
    """Decode raw ASGI headers into a lower-cased multi-value mapping."""
    headers: dict[str, list[str]] = {}
    for raw_name, raw_value in scope.get("headers", []):
        name = raw_name.decode("latin-1").lower()
        value = raw_value.decode("latin-1")
        headers.setdefault(name, []).append(value)
    return headers


def _has_auth_cookies(cookie_headers: Iterable[str]) -> bool:
    """Return True if any Cookie header carries a non-empty auth cookie."""
    for header_value in cookie_headers:
        for segment in header_value.split(";"):
            part = segment.strip()
            if not part or "=" not in part:
                continue
            name, _, value = part.partition("=")
            if name.strip() in AUTH_COOKIE_NAMES and value.strip():
                return True
    return False


def _has_bearer_authorization(auth_headers: Iterable[str]) -> bool:
    """Return True if an Authorization header uses the Bearer scheme with a non-empty token."""
    for header_value in auth_headers:
        cleaned = header_value.strip()
        if cleaned.lower().startswith("bearer ") and cleaned[7:].strip():
            return True
    return False


def _normalize_path(raw_path: str) -> str:
    stripped = (raw_path or "").rstrip("/")
    return stripped or "/"


class CSRFProtectionMiddleware:
    """Pure ASGI defense-in-depth CSRF middleware for cookie-authenticated routes."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        trusted_origins: Iterable[str] | None = None,
        exempt_paths: Iterable[str] | None = None,
    ) -> None:
        self.app = app
        self._explicit_trusted_origins: frozenset[str] | None = None
        if trusted_origins is not None:
            normalized = {
                origin
                for raw in trusted_origins
                if (origin := normalize_origin(raw, allow_url_path=False)) is not None
            }
            self._explicit_trusted_origins = frozenset(normalized)
        self._exempt_paths: frozenset[str] = (
            frozenset(_normalize_path(p) for p in exempt_paths)
            if exempt_paths is not None
            else EXEMPT_WEBHOOK_PATHS
        )

    def _get_trusted_origins(self) -> frozenset[str]:
        if self._explicit_trusted_origins is not None:
            return self._explicit_trusted_origins
        return get_settings().csrf_trusted_origin_set

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "GET")).upper()
        if method in SAFE_HTTP_METHODS:
            await self.app(scope, receive, send)
            return

        path = _normalize_path(str(scope.get("path", "")))
        if path in self._exempt_paths:
            await self.app(scope, receive, send)
            return

        headers = _extract_headers(scope)
        has_auth_cookie = _has_auth_cookies(headers.get("cookie", ()))
        has_bearer = _has_bearer_authorization(headers.get("authorization", ()))
        is_cookie_auth_endpoint = path in COOKIE_AUTH_ENDPOINTS

        if not has_auth_cookie:
            if has_bearer:
                await self.app(scope, receive, send)
                return
            if not is_cookie_auth_endpoint:
                await self.app(scope, receive, send)
                return

        origin_values = headers.get("origin", [])
        referer_values = headers.get("referer", [])
        sec_fetch_site_values = [
            v.strip().lower() for v in headers.get("sec-fetch-site", []) if v.strip()
        ]

        # Unauthenticated non-browser clients (no auth cookies AND no browser Origin/Referer/
        # Sec-Fetch-Site headers) calling cookie-issuing auth endpoints (e.g. CLI login) are allowed.
        if (
            not has_auth_cookie
            and is_cookie_auth_endpoint
            and not origin_values
            and not referer_values
            and not sec_fetch_site_values
        ):
            await self.app(scope, receive, send)
            return

        rejection_reason = self._validate_request_origin(
            origin_values=origin_values,
            referer_values=referer_values,
            sec_fetch_site_values=sec_fetch_site_values,
            trusted_origins=self._get_trusted_origins(),
        )
        if rejection_reason is not None:
            reason_code, detail = rejection_reason
            _logger.warning(
                "csrf_validation_failed",
                method=method,
                path=path,
                reason=reason_code,
                has_auth_cookie=has_auth_cookie,
                has_origin=bool(origin_values),
                has_referer=bool(referer_values),
                sec_fetch_site=sec_fetch_site_values[0] if sec_fetch_site_values else None,
            )
            response = JSONResponse(
                status_code=403,
                content={
                    "code": "CSRF_VALIDATION_FAILED",
                    "detail": detail,
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    def _validate_request_origin(
        *,
        origin_values: list[str],
        referer_values: list[str],
        sec_fetch_site_values: list[str],
        trusted_origins: frozenset[str],
    ) -> tuple[str, str] | None:
        """Return ``(reason_code, detail)`` if the request fails CSRF checks, else ``None``."""
        if any(value == "cross-site" for value in sec_fetch_site_values):
            return (
                "sec_fetch_site_cross_site",
                "Cross-site state-changing request rejected by CSRF protection.",
            )

        if len(origin_values) > 1:
            return (
                "multiple_origin_headers",
                "Multiple Origin headers are not permitted.",
            )

        if len(origin_values) == 1:
            normalized_origin = normalize_origin(origin_values[0], allow_url_path=False)
            if normalized_origin is None or normalized_origin not in trusted_origins:
                return (
                    "untrusted_origin",
                    "Untrusted or invalid Origin header.",
                )
            return None

        if len(referer_values) > 1:
            return (
                "multiple_referer_headers",
                "Multiple Referer headers are not permitted.",
            )

        if len(referer_values) == 1:
            referer_origin = normalize_origin(referer_values[0], allow_url_path=True)
            if referer_origin is None or referer_origin not in trusted_origins:
                return (
                    "untrusted_referer",
                    "Untrusted or invalid Referer header.",
                )
            return None

        return (
            "missing_origin_and_referer",
            "Missing Origin or Referer header on cookie-authenticated request.",
        )
