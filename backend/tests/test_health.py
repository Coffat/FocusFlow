from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import src.main as main_mod
from src.main import app

client = TestClient(app)


def test_health_check_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_mod, "check_database_health", AsyncMock(return_value=True))
    monkeypatch.setattr(main_mod, "check_redis_health", AsyncMock(return_value=True))

    response = client.get("/api/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert response.json() == {
        "status": "healthy",
        "database": "ok",
        "redis": "ok",
    }


def test_health_check_degraded_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_mod, "check_database_health", AsyncMock(return_value=False))
    monkeypatch.setattr(main_mod, "check_redis_health", AsyncMock(return_value=True))

    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "database": "error",
        "redis": "ok",
    }


def test_bounded_contexts_mounted() -> None:
    for context in ("account", "planning", "execution", "evaluation"):
        res = client.get(f"/api/v1/{context}/status")
        assert res.status_code == 200
        assert res.json() == {"context": context, "status": "ready"}
