import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_health(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the health endpoint returns ok status."""
    # Set environment to test to skip database connection check in lifespan context manager
    monkeypatch.setenv("ENVIRONMENT", "test")
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
