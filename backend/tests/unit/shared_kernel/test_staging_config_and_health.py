"""Unit tests for staging environment guards, readiness summary, and /api/health output."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

import src.main as main_mod
from src.shared_kernel.config import Settings


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
    with caplog.at_level(logging.WARNING, logger="src.shared_kernel.config"):
        cfg = Settings(
            _env_file=None,
            environment="staging",
            debug=False,
            email_backend="smtp",
            email_host="mailpit",
            calendar_webhook_base_url="http://localhost:3000",
        )

    assert cfg.environment == "staging"
    assert cfg.debug is False
    assert any("default secret_key" in rec.message for rec in caplog.records)

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


def test_create_app_staging_disables_docs_and_exposes_non_secret_health_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging create_app() returns 404 for /docs & /redoc and exposes non-secret readiness on /api/health."""
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
    )

    monkeypatch.setattr(main_mod, "get_settings", lambda: staging_settings)
    staging_app = main_mod.create_app()
    client = TestClient(staging_app)

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404

    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    assert secret_embedding not in health_res.text
    assert secret_jwt not in health_res.text

    payload = health_res.json()
    assert payload["status"] == "healthy"
    assert payload["environment"] == "staging"
    assert payload["debug"] is False
    assert payload["readiness"] == {
        "environment": "staging",
        "debug": False,
        "rag_embedding_configured": True,
        "email_backend": "smtp",
        "email_host": "mailpit",
        "calendar_webhook_https_ready": True,
        "secret_key_is_default": False,
    }


def test_create_app_development_keeps_docs_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Development create_app() with debug=True keeps /docs and /redoc accessible."""
    dev_settings = Settings(_env_file=None, environment="development", debug=True)
    monkeypatch.setattr(main_mod, "get_settings", lambda: dev_settings)
    dev_app = main_mod.create_app()
    client = TestClient(dev_app)

    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    assert health_res.json()["environment"] == "development"
    assert health_res.json()["debug"] is True
