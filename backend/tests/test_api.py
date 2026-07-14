import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx import ASGITransport
from app.main import app
from app.core.config import settings

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    # This assumes a root or health endpoint. If it doesn't exist, we test metrics.
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    assert "fastapi" in response.text or "python" in response.text

@pytest.mark.asyncio
async def test_auth_failure(async_client: AsyncClient):
    response = await async_client.post(f"{settings.API_V1_STR}/auth/login/access-token", data={
        "username": "fake@user.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 400
    assert "Incorrect email or password" in response.json()["detail"]
