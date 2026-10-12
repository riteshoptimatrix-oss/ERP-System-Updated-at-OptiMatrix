import pytest
from httpx import AsyncClient
from unittest.mock import patch
from app.database.mongodb import mongodb_manager

@pytest.mark.asyncio
async def test_liveness_endpoint(async_client: AsyncClient):
    """
    Test GET /api/v1/health returns 200 OK and healthy status.
    """
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert data["version"] == "0.1.0"
    # Ensure correlation ID is present in headers
    assert "x-correlation-id" in response.headers


@pytest.mark.asyncio
async def test_readiness_endpoint_when_db_connected(async_client: AsyncClient):
    """
    Test GET /api/v1/health/ready returns 200 OK when MongoDB ping succeeds.
    """
    with patch.object(mongodb_manager, "ping", return_value=True):
        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "mongodb" in data["dependencies"]
        assert data["dependencies"]["mongodb"]["status"] == "connected"
        assert data["dependencies"]["mongodb"]["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_readiness_endpoint_when_db_disconnected(async_client: AsyncClient):
    """
    Test GET /api/v1/health/ready returns 503 Service Unavailable when MongoDB ping fails.
    """
    with patch.object(mongodb_manager, "ping", return_value=False):
        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "mongodb" in data["dependencies"]
        assert data["dependencies"]["mongodb"]["status"] == "disconnected"


@pytest.mark.asyncio
async def test_correlation_id_propagation(async_client: AsyncClient):
    """
    Test that incoming X-Correlation-ID is echoed back in the response header.
    """
    custom_id = "test-corr-id-12345"
    response = await async_client.get(
        "/api/v1/health",
        headers={"X-Correlation-ID": custom_id}
    )
    assert response.status_code == 200
    assert response.headers.get("x-correlation-id") == custom_id
