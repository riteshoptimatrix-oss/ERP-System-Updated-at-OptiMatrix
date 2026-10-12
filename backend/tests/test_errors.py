import pytest
from httpx import AsyncClient
from fastapi import APIRouter

@pytest.mark.asyncio
async def test_404_not_found(async_client: AsyncClient):
    """
    Test standard 404 response follows the centralized error envelope.
    """
    response = await async_client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == 404
    assert "Not Found" in data["error"]["message"]


@pytest.mark.asyncio
async def test_unhandled_exception_masks_secrets(test_app, async_client: AsyncClient):
    """
    Test unhandled exceptions return 500 without leaking stack traces or internal details.
    """
    mock_router = APIRouter()

    @mock_router.get("/test-crash")
    async def crash_endpoint():
        raise RuntimeError("Internal DB connection secret leaked: secret_pwd_123")

    test_app.include_router(mock_router)

    response = await async_client.get("/test-crash")
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == 500
    # Crucial security check: internal exception message and secret are masked
    assert "secret_pwd_123" not in response.text
    assert "RuntimeError" not in response.text
    assert "An unexpected internal server error occurred" in data["error"]["message"]
