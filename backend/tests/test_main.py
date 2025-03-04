"""Tests for main application functionality."""

import pytest
from httpx import ASGITransport, AsyncClient

from pythmata.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint returns correct status."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_cors_middleware():
    """Test CORS middleware configuration."""
    test_origin = "http://example.com"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": test_origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert response.status_code == 200
        # When allow_credentials is True, the origin is reflected back
        assert response.headers["access-control-allow-origin"] == test_origin
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "GET" in response.headers["access-control-allow-methods"]
        assert "Content-Type" in response.headers["access-control-allow-headers"]
