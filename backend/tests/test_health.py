from fastapi.testclient import TestClient

from src.presentation.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "FocusFlow" in data["service"]
    assert data["architecture"] == "Hexagonal (Ports & Adapters)"
