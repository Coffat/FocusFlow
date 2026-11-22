"""Unit tests for staging environment guards, readiness summary, and hardened /api/health output."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import src.main as main_mod
from src.shared_kernel.config import Settings
from src.shared_kernel.infrastructure.security.encryption import generate_fernet_key


def test_settings_rejects_debug_true_in_staging_and_production() -> None:
    """Staging and production environments must reject debug=True."""
    with pytest.raises(ValueError, match="debug must be False in staging/production"):
        Settings(_env_file=None, environment="staging", debug=True)

    with pytest.raises(ValueError, match="debug must be False in staging/production"):
        Settings(
            _env_file=None,
            environment="production",
            debug=True,
            secret_key="custom-production-secret-key",
        )


def test_settings_rejects_default_secret_key_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production environment must reject the default JWT secret_key."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="secret_key must not use the default value in production"):
        Settings(_env_file=None, environment="production", debug=False)


def test_settings_rejects_missing_calendar_encryption_key_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production with calendar_provider='google' must fail closed without a valid Fernet key."""
    monkeypatch.delenv("CALENDAR_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("FERNET_KEY", raising=False)
    with pytest.raises(ValueError, match="CALENDAR_ENCRYPTION_KEY"):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            secret_key="custom-production-secret-key",
            calendar_provider="google",
            calendar_encryption_key="",
            fernet_key="",
        )

    valid_cfg = Settings(
        _env_file=None,
        environment="production",
        debug=False,
        secret_key="custom-production-secret-key",
        calendar_provider="google",
        calendar_encryption_key=generate_fernet_key(),
    )
    assert valid_cfg.environment == "production"


def test_settings_staging_allows_default_secret_with_warning_and_readiness_summary(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging allows debug=False with default secret (emitting warning) and returns safe readiness flags."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("EMAIL_BACKEND", raising=False)
    monkeypatch.delenv("EMAIL_HOST", raising=False)
    monkeypatch.delenv("CALENDAR_WEBHOOK_BASE_URL", raising=False)
    monkeypatch.delenv("CALENDAR_PROVIDER", raising=False)
    monkeypatch.delenv("CALENDAR_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("FERNET_KEY", raising=False)
    with caplog.at_level(logging.WARNING, logger="src.shared_kernel.config"):
        cfg = Settings(
            _env_file=None,
            environment="staging",
            debug=False,
            email_backend="smtp",
            email_host="mailpit",
            calendar_provider="google",
            calendar_webhook_base_url="http://localhost:3000",
        )

    assert cfg.environment == "staging"
    assert cfg.debug is False
    assert any("default secret_key" in rec.message for rec in caplog.records)
    assert any("CALENDAR_ENCRYPTION_KEY" in rec.message for rec in caplog.records)

    readiness = cfg.staging_readiness_summary()
    assert readiness == {
        "environment": "staging",
        "debug": False,
        "rag_embedding_configured": False,
        "email_backend": "smtp",
        "email_host": "mailpit",
        "calendar_webhook_https_ready": False,
        "secret_key_is_default": True,
    }


def test_create_app_staging_disables_docs_and_hardens_health_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging create_app() returns 404 for /docs & /redoc and exposes minimal /api/health."""
    secret_embedding = "AIza-super-secret-embedding-key-12345"
    secret_jwt = "super-secret-staging-jwt-key-abcdef"

    staging_settings = Settings(
        _env_file=None,
        environment="staging",
        debug=False,
        secret_key=secret_jwt,
        embedding_api_key=secret_embedding,
        email_backend="smtp",
        email_host="mailpit",
        calendar_webhook_base_url="https://staging.focusflow.vn",
        calendar_encryption_key=generate_fernet_key(),
    )

    monkeypatch.setattr(main_mod, "get_settings", lambda: staging_settings)
    monkeypatch.setattr(main_mod, "check_database_health", AsyncMock(return_value=True))
    monkeypatch.setattr(main_mod, "check_redis_health", AsyncMock(return_value=True))
    probe_spy = AsyncMock()
    monkeypatch.setattr(main_mod, "probe_cobhub_capabilities", probe_spy)

    staging_app = main_mod.create_app()
    client = TestClient(staging_app)

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404

    health_res = client.get("/api/health?probe_ai=true")
    assert health_res.status_code == 200
    assert secret_embedding not in health_res.text
    assert secret_jwt not in health_res.text
    probe_spy.assert_not_awaited()

    payload = health_res.json()
    assert payload == {
        "status": "healthy",
        "database": "ok",
        "redis": "ok",
    }
    for forbidden_key in (
        "ai_gateway",
        "gateway_models",
        "email_host",
        "secret_key_is_default",
        "readiness",
    ):
        assert forbidden_key not in payload


def test_create_app_development_keeps_docs_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Development create_app() with debug=True keeps /docs and /redoc accessible."""
    dev_settings = Settings(_env_file=None, environment="development", debug=True)
    monkeypatch.setattr(main_mod, "get_settings", lambda: dev_settings)
    monkeypatch.setattr(main_mod, "check_database_health", AsyncMock(return_value=True))
    monkeypatch.setattr(main_mod, "check_redis_health", AsyncMock(return_value=True))
    dev_app = main_mod.create_app()
    client = TestClient(dev_app)

    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    assert health_res.json() == {
        "status": "healthy",
        "database": "ok",
        "redis": "ok",
    }
