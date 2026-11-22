"""Unit tests for CSRFProtectionMiddleware and origin normalization (AUD-HIGH-01)."""

import pytest
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

from src.shared_kernel.config import Settings, normalize_origin
from src.shared_kernel.infrastructure.security.csrf_middleware import (
    CSRFProtectionMiddleware,
)


def _build_test_app(trusted_origins: list[str] | None = None) -> FastAPI:
    origins = trusted_origins or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4200",
    ]
    app = FastAPI()
    app.add_middleware(CSRFProtectionMiddleware, trusted_origins=origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["Accept", "Authorization", "Content-Type", "X-Correlation-ID"],
    )

    @app.get("/api/v1/roadmaps/jobs/{job_id}/stream")
    async def sse_stream(job_id: str) -> dict[str, str]:
        return {"stream": job_id}

    @app.get("/api/v1/account/calendar/google/callback")
    async def google_callback() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/auth/login")
    async def login() -> dict[str, str]:
        return {"status": "logged_in"}

    @app.post("/api/v1/tasks")
    async def create_task() -> dict[str, str]:
        return {"status": "created"}

    @app.put("/api/v1/tasks/{task_id}")
    async def put_task(task_id: str) -> dict[str, str]:
        return {"updated": task_id}

    @app.patch("/api/v1/tasks/{task_id}")
    async def patch_task(task_id: str) -> dict[str, str]:
        return {"patched": task_id}

    @app.delete("/api/v1/tasks/{task_id}")
    async def delete_task(task_id: str) -> dict[str, str]:
        return {"deleted": task_id}

    @app.post("/api/v1/account/billing/webhook")
    async def billing_webhook(request: Request) -> dict[str, str]:
        del request
        return {"webhook": "billing"}

    @app.post("/api/v1/calendar/webhooks/google")
    async def google_webhook() -> dict[str, str]:
        return {"webhook": "google"}

    return app


def test_normalize_origin_handles_valid_and_invalid_inputs() -> None:
    assert normalize_origin("http://localhost:3000") == "http://localhost:3000"
    assert normalize_origin("HTTPS://App.FocusFlow.VN:443") == "https://app.focusflow.vn"
    assert normalize_origin("http://example.com:80") == "http://example.com"
    assert (
        normalize_origin("https://app.focusflow.vn/settings?tab=1", allow_url_path=True)
        == "https://app.focusflow.vn"
    )
    assert normalize_origin("https://app.focusflow.vn/settings", allow_url_path=False) is None
    assert normalize_origin("*") is None
    assert normalize_origin("null") is None
    assert normalize_origin("javascript:alert(1)") is None
    assert normalize_origin("https://user:pass@localhost:3000") is None


def test_settings_rejects_wildcard_cors_origins() -> None:
    with pytest.raises(ValueError, match="backend_cors_origins must not contain '\\*'"):
        Settings(backend_cors_origins='["*"]')

    with pytest.raises(ValueError, match="csrf_trusted_origins must not contain '\\*'"):
        Settings(csrf_trusted_origins="*")


def test_settings_csrf_trusted_origins_combines_cors_and_frontend_url() -> None:
    cfg = Settings(
        backend_cors_origins='["http://localhost:3000", "http://localhost:4200"]',
        frontend_url="https://app.focusflow.vn/dashboard",
        csrf_trusted_origins="https://staging.focusflow.vn",
    )
    assert cfg.cors_origins == ["http://localhost:3000", "http://localhost:4200"]
    assert cfg.csrf_trusted_origin_set == frozenset(
        {
            "http://localhost:3000",
            "http://localhost:4200",
            "https://app.focusflow.vn",
            "https://staging.focusflow.vn",
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/tasks"),
        ("PUT", "/api/v1/tasks/123"),
        ("PATCH", "/api/v1/tasks/123"),
        ("DELETE", "/api/v1/tasks/123"),
    ],
)
async def test_rejects_cross_origin_and_missing_origin_on_cookie_requests(
    method: str, path: str
) -> None:
    app = _build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Cross-origin
        evil_resp = await client.request(
            method,
            path,
            headers={
                "Origin": "https://evil.example",
                "Cookie": "access_token=jwt-value",
            },
        )
        assert evil_resp.status_code == 403
        assert evil_resp.json()["code"] == "CSRF_VALIDATION_FAILED"

        # Missing both Origin and Referer
        missing_resp = await client.request(
            method,
            path,
            headers={"Cookie": "access_token=jwt-value"},
        )
        assert missing_resp.status_code == 403
        assert missing_resp.json()["code"] == "CSRF_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_rejects_invalid_referer_and_null_origin_and_sec_fetch_site_cross_site() -> None:
    app = _build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Invalid Referer
        bad_referer = await client.post(
            "/api/v1/tasks",
            headers={
                "Referer": "https://evil.example/attack",
                "Cookie": "access_token=jwt-value",
            },
        )
        assert bad_referer.status_code == 403
        assert bad_referer.json()["code"] == "CSRF_VALIDATION_FAILED"

        # Origin: null (sandboxed iframe)
        null_origin = await client.post(
            "/api/v1/tasks",
            headers={
                "Origin": "null",
                "Cookie": "access_token=jwt-value",
            },
        )
        assert null_origin.status_code == 403
        assert null_origin.json()["code"] == "CSRF_VALIDATION_FAILED"

        # Sec-Fetch-Site: cross-site even with trusted Origin
        cross_site = await client.post(
            "/api/v1/tasks",
            headers={
                "Origin": "http://localhost:3000",
                "Sec-Fetch-Site": "cross-site",
                "Cookie": "access_token=jwt-value",
            },
        )
        assert cross_site.status_code == 403
        assert cross_site.json()["code"] == "CSRF_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_forged_forwarded_headers_are_ignored() -> None:
    app = _build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/tasks",
            headers={
                "Origin": "https://evil.example",
                "Host": "evil.example",
                "X-Forwarded-Host": "evil.example",
                "X-Forwarded-Proto": "https",
                "Cookie": "access_token=jwt-value",
            },
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "CSRF_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_allows_trusted_origin_referer_bearer_and_exempt_routes() -> None:
    app = _build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Trusted Angular Origin (localhost:3000 and localhost:4200)
        for origin in ("http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:4200"):
            ok_resp = await client.post(
                "/api/v1/tasks",
                headers={
                    "Origin": origin,
                    "Sec-Fetch-Site": "same-site",
                    "Cookie": "access_token=jwt-value",
                },
            )
            assert ok_resp.status_code == 200

        # Valid Referer fallback when Origin is absent
        referer_resp = await client.patch(
            "/api/v1/tasks/42",
            headers={
                "Referer": "http://localhost:3000/dashboard",
                "Cookie": "access_token=jwt-value",
            },
        )
        assert referer_resp.status_code == 200

        # Bearer-only request (no auth cookies) allowed without Origin
        bearer_resp = await client.post(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer some-jwt-token"},
        )
        assert bearer_resp.status_code == 200

        # Cookie + Bearer without Origin is STILL rejected (cookie present)
        both_resp = await client.post(
            "/api/v1/tasks",
            headers={
                "Authorization": "Bearer some-jwt-token",
                "Cookie": "access_token=jwt-value",
            },
        )
        assert both_resp.status_code == 403

        # Safe GET routes (SSE, Google OAuth callback) allowed even with cross-site metadata
        sse_resp = await client.get(
            "/api/v1/roadmaps/jobs/job-1/stream",
            headers={"Cookie": "access_token=jwt-value", "Sec-Fetch-Site": "same-origin"},
        )
        assert sse_resp.status_code == 200

        oauth_cb_resp = await client.get(
            "/api/v1/account/calendar/google/callback",
            headers={"Cookie": "access_token=jwt-value", "Sec-Fetch-Site": "cross-site"},
        )
        assert oauth_cb_resp.status_code == 200

        # Provider webhooks exempt without Origin and without cookies
        billing_resp = await client.post("/api/v1/account/billing/webhook")
        assert billing_resp.status_code == 200

        gcal_resp = await client.post("/api/v1/calendar/webhooks/google")
        assert gcal_resp.status_code == 200


@pytest.mark.asyncio
async def test_login_csrf_blocked_when_untrusted_browser_headers_present() -> None:
    app = _build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Browser cross-site login CSRF attempt (no cookies yet)
        evil_login = await client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
        )
        assert evil_login.status_code == 403
        assert evil_login.json()["code"] == "CSRF_VALIDATION_FAILED"

        # Legitimate Angular login
        good_login = await client.post(
            "/api/v1/auth/login",
            headers={"Origin": "http://localhost:3000", "Sec-Fetch-Site": "same-site"},
        )
        assert good_login.status_code == 200


@pytest.mark.asyncio
async def test_cors_preflight_rejects_untrusted_origin_and_allows_trusted_origin() -> None:
    app = _build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Untrusted origin preflight
        evil_preflight = await client.options(
            "/api/v1/tasks",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert evil_preflight.headers.get("access-control-allow-origin") is None

        # Trusted origin preflight
        good_preflight = await client.options(
            "/api/v1/tasks",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert good_preflight.status_code == 200
        assert good_preflight.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert good_preflight.headers.get("access-control-allow-credentials") == "true"
