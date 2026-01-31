from fastapi.testclient import TestClient


def test_health(http_client: TestClient) -> None:
    """Test that the health endpoint returns OK status."""
    resp = http_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
