from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_ready_endpoint():
    response = client.get("/api/health/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "ready" in data


def test_ready_alias_endpoint():
    response = client.get("/api/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
