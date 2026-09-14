from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_download_windows_setup():
    response = client.get("/api/download/windows")
    assert response.status_code == 200
    assert response.headers.get("content-disposition") == 'attachment; filename="HSBot_1.0.0_x64-setup.exe"'
    assert int(response.headers.get("content-length", 0)) > 4_000_000


def test_download_alias_endpoints():
    r1 = client.get("/api/download/hsbot-setup.exe")
    assert r1.status_code == 200
    r2 = client.get("/api/download/desktop")
    assert r2.status_code == 200
