from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    data = response.json()
    assert data["status"] == "healthy"
    assert "FocusFlow" in data["service"]
    assert "Hexagonal (Ports & Adapters)" in data["architecture"]


def test_bounded_contexts_mounted() -> None:
    for context in ("account", "planning", "execution", "evaluation"):
        res = client.get(f"/api/v1/{context}/status")
        assert res.status_code == 200
        assert res.json() == {"context": context, "status": "ready"}
