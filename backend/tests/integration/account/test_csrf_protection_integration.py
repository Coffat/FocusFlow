"""Integration tests for CSRF protection, CORS hardening, and refresh cookie path scoping (AUD-HIGH-01)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


def _extract_set_cookie_headers(headers: object) -> list[str]:
    get_list = getattr(headers, "get_list", None)
    if callable(get_list):
        return list(get_list("set-cookie"))
    return []


@pytest.mark.asyncio
async def test_cors_hardening_on_real_app() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Unauthorized credentialed CORS preflight must NOT reflect evil origin
        evil_preflight = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert evil_preflight.headers.get("access-control-allow-origin") is None

        # Authorized Angular origins (localhost:3000 and localhost:4200)
        for origin in ("http://localhost:3000", "http://localhost:4200"):
            ok_preflight = await client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )
            assert ok_preflight.status_code == 200
            assert ok_preflight.headers.get("access-control-allow-origin") == origin
            assert ok_preflight.headers.get("access-control-allow-credentials") == "true"
            allow_methods = ok_preflight.headers.get("access-control-allow-methods", "")
            assert "*" not in allow_methods


@pytest.mark.asyncio
async def test_cookie_auth_csrf_protection_and_refresh_path_lifecycle() -> None:
    trusted_origin = "http://localhost:3000"
    email = f"csrf_{uuid.uuid4().hex[:8]}@focusflow.vn"
    password = "SecurePassword123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register with trusted Origin -> issues cookies with refresh_token Path=/api/v1/auth
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={"full_name": "CSRF Tester", "email": email, "password": password},
            headers={"Origin": trusted_origin, "Sec-Fetch-Site": "same-site"},
        )
        assert reg_resp.status_code == 201, reg_resp.text

        reg_set_cookies = _extract_set_cookie_headers(reg_resp.headers)
        refresh_set_cookie = [h for h in reg_set_cookies if h.startswith("refresh_token=")]
        access_set_cookie = [h for h in reg_set_cookies if h.startswith("access_token=")]
        assert len(refresh_set_cookie) == 1
        assert "Path=/api/v1/auth" in refresh_set_cookie[0]
        assert "HttpOnly" in refresh_set_cookie[0]
        assert len(access_set_cookie) == 1
        assert "Path=/" in access_set_cookie[0]

        # 2. Cross-origin state-changing request with cookies -> 403 CSRF_VALIDATION_FAILED
        evil_origin_resp = await client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": "https://evil.example"},
        )
        assert evil_origin_resp.status_code == 403
        assert evil_origin_resp.json()["code"] == "CSRF_VALIDATION_FAILED"

        # 3. Missing BOTH Origin and Referer on cookie-authenticated POST/PATCH/DELETE -> 403
        missing_post = await client.post("/api/v1/auth/refresh")
        assert missing_post.status_code == 403
        assert missing_post.json()["code"] == "CSRF_VALIDATION_FAILED"

        missing_patch = await client.patch(
            "/api/v1/account/profile",
            json={"full_name": "Should Fail"},
        )
        assert missing_patch.status_code == 403
        assert missing_patch.json()["code"] == "CSRF_VALIDATION_FAILED"

        missing_delete = await client.delete("/api/v1/account/calendar/webcal")
        assert missing_delete.status_code == 403
        assert missing_delete.json()["code"] == "CSRF_VALIDATION_FAILED"

        # 4. Invalid Referer -> 403
        bad_referer = await client.patch(
            "/api/v1/account/profile",
            json={"full_name": "Bad Referer"},
            headers={"Referer": "https://evil.example/phish"},
        )
        assert bad_referer.status_code == 403
        assert bad_referer.json()["code"] == "CSRF_VALIDATION_FAILED"

        # 5. Sec-Fetch-Site: cross-site -> 403 even with trusted Origin
        cross_site = await client.patch(
            "/api/v1/account/profile",
            json={"full_name": "Cross Site"},
            headers={"Origin": trusted_origin, "Sec-Fetch-Site": "cross-site"},
        )
        assert cross_site.status_code == 403
        assert cross_site.json()["code"] == "CSRF_VALIDATION_FAILED"

        # 6. Forged X-Forwarded-Host ignored -> 403
        forged_xfh = await client.patch(
            "/api/v1/account/profile",
            json={"full_name": "Forged Host"},
            headers={
                "Origin": "https://evil.example",
                "X-Forwarded-Host": "evil.example",
                "X-Forwarded-Proto": "https",
            },
        )
        assert forged_xfh.status_code == 403
        assert forged_xfh.json()["code"] == "CSRF_VALIDATION_FAILED"

        # 7. Legitimate Angular authenticated requests (localhost:3000 & localhost:4200) -> allowed
        for allowed_origin in ("http://localhost:3000", "http://localhost:4200"):
            ok_profile = await client.patch(
                "/api/v1/account/profile",
                json={"full_name": "Updated Learner"},
                headers={"Origin": allowed_origin, "Sec-Fetch-Site": "same-site"},
            )
            assert ok_profile.status_code == 200, ok_profile.text

        # 8. Refresh with trusted Origin -> 200 and keeps Path=/api/v1/auth
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": trusted_origin, "Sec-Fetch-Site": "same-site"},
        )
        assert refresh_resp.status_code == 200, refresh_resp.text
        rotated_set_cookies = _extract_set_cookie_headers(refresh_resp.headers)
        rotated_refresh = [h for h in rotated_set_cookies if h.startswith("refresh_token=")]
        assert len(rotated_refresh) == 1
        assert "Path=/api/v1/auth" in rotated_refresh[0]

        # 9. Logout with trusted Origin -> 200 and clears both /api/v1/auth and legacy /
        logout_resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Origin": trusted_origin, "Sec-Fetch-Site": "same-site"},
        )
        assert logout_resp.status_code == 200, logout_resp.text
        logout_set_cookies = _extract_set_cookie_headers(logout_resp.headers)
        cleared_refresh = [h for h in logout_set_cookies if h.startswith("refresh_token=")]
        assert any("Path=/api/v1/auth" in h for h in cleared_refresh)
        assert any("Path=/;" in h or h.endswith("Path=/") for h in cleared_refresh)


@pytest.mark.asyncio
async def test_safe_get_routes_and_provider_webhooks_are_not_blocked_by_csrf() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Safe GET: SSE stream (may return 401/404 without valid user/job, never 403 CSRF)
        sse_resp = await client.get(
            "/api/v1/roadmaps/jobs/00000000-0000-0000-0000-000000000001/stream",
            headers={"Cookie": "access_token=dummy-token"},
        )
        assert (
            sse_resp.status_code != 403 or sse_resp.json().get("code") != "CSRF_VALIDATION_FAILED"
        )

        # Safe GET: Google OAuth callback (cross-site redirect from accounts.google.com)
        oauth_resp = await client.get(
            "/api/v1/account/calendar/google/callback",
            params={"code": "dummy", "state": "dummy"},
            headers={"Cookie": "access_token=dummy-token", "Sec-Fetch-Site": "cross-site"},
        )
        assert (
            oauth_resp.status_code != 403
            or oauth_resp.json().get("code") != "CSRF_VALIDATION_FAILED"
        )

        # Provider webhook: Billing (POST without Origin, no cookies) -> reaches webhook handler
        billing_resp = await client.post(
            "/api/v1/account/billing/webhook",
            json={"event_type": "payment.succeeded"},
        )
        assert billing_resp.status_code in (401, 503)
        assert billing_resp.json().get("code") != "CSRF_VALIDATION_FAILED"

        # Provider webhook: Google Calendar (POST without Origin, no cookies) -> reaches handler
        gcal_resp = await client.post("/api/v1/calendar/webhooks/google")
        assert gcal_resp.status_code == 403
        assert gcal_resp.json().get("code") != "CSRF_VALIDATION_FAILED"
        assert "X-Goog-Channel-ID" in gcal_resp.json().get("detail", "")
