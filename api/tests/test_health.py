def test_health_check(client):
    """Test health endpoint returns 200 and correct structure."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["service"] == "docchat-api"
    assert "dependencies" in data
